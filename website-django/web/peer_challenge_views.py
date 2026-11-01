from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import PeerChallengeForm, PeerChallengeInvitationForm
from .models import PeerChallenge, PeerChallengeInvitation, UserQuiz


@login_required
def challenge_list(request):
    """Display a list of peer challenges created by the user and challenges they've been invited to."""
    # Challenges created by the user
    user_created_challenges = PeerChallenge.objects.filter(creator=request.user).order_by("-created_at")

    # Challenges the user has been invited to
    invitations = (
        PeerChallengeInvitation.objects.filter(participant=request.user, status__in=["pending", "accepted"])
        .select_related("challenge", "challenge__quiz", "challenge__creator")
        .order_by("-created_at")
    )

    # Completed challenges
    completed_challenges = (
        PeerChallengeInvitation.objects.filter(
            participant=request.user,
            status="completed",
            user_quiz__isnull=False,  # Make sure there's an associated user quiz
        )
        .select_related("challenge", "challenge__quiz", "challenge__creator", "user_quiz")
        .order_by("-updated_at")
    )

    # Debug logging
    print(f"Total completed challenges: {completed_challenges.count()}")
    for challenge in completed_challenges:
        print(
            f"Challenge: {challenge.challenge.title}, "
            f"Updated at: {challenge.updated_at}, "
            f"User Quiz: {challenge.user_quiz_id}"
        )

    context = {
        "user_created_challenges": user_created_challenges,
        "invitations": invitations,
        "completed_challenges": completed_challenges,
    }

    return render(request, "web/peer_challenges/challenge_list.html", context)


@login_required
def create_challenge(request):
    """Create a new peer challenge."""
    if request.method == "POST":
        form = PeerChallengeForm(request.POST, user=request.user)
        invitation_form = PeerChallengeInvitationForm(request.POST)

        if form.is_valid() and invitation_form.is_valid():
            with transaction.atomic():
                # Create the challenge
                challenge = form.save(commit=False)
                challenge.creator = request.user
                challenge.status = "active"
                challenge.save()

                # Get participants from the form
                participants = invitation_form.cleaned_data.get("participants")
                message = invitation_form.cleaned_data.get("message", "")

                # Create invitations for each participant
                for participant in participants:
                    if participant != request.user:  # Don't invite yourself
                        PeerChallengeInvitation.objects.create(
                            challenge=challenge, participant=participant, message=message, status="pending"
                        )

            messages.success(request, "Challenge created and invitations sent!")
            return redirect("peer_challenge_detail", challenge_id=challenge.id)
    else:
        form = PeerChallengeForm(user=request.user)
        invitation_form = PeerChallengeInvitationForm()

    context = {
        "form": form,
        "invitation_form": invitation_form,
    }

    return render(request, "web/peer_challenges/create_challenge.html", context)


@login_required
def peer_challenge_detail(request, challenge_id):
    """Display details of a peer challenge, including invitations and progress."""
    challenge = get_object_or_404(PeerChallenge, id=challenge_id)

    # Check if the user is allowed to view this challenge
    if (
        challenge.creator != request.user
        and not PeerChallengeInvitation.objects.filter(challenge=challenge, participant=request.user).exists()
    ):
        return HttpResponseForbidden("You don't have permission to view this challenge.")

    # Get invitations for this challenge
    invitations = PeerChallengeInvitation.objects.filter(challenge=challenge)

    # Process invitations to add the correct answer count
    for invitation in invitations:
        if invitation.status == "completed" and invitation.user_quiz:
            total_questions = invitation.user_quiz.quiz.questions.count()
            score_percentage = invitation.user_quiz.score or 0
            # Calculate correct answer count based on percentage
            invitation.correct_answer_count = int(round((score_percentage / 100) * total_questions))

    # Get user's invitation if they are a participant
    user_invitation = None
    if request.user != challenge.creator:
        user_invitation = PeerChallengeInvitation.objects.filter(challenge=challenge, participant=request.user).first()

    # Check if the challenge has expired
    is_expired = challenge.expires_at and challenge.expires_at < timezone.now()
    if is_expired and challenge.status != "completed":
        challenge.status = "completed"
        challenge.save()

    # Calculate leaderboard if the challenge is completed
    leaderboard = None
    if challenge.status == "completed" or is_expired:
        leaderboard = calculate_leaderboard(challenge)

    context = {
        "challenge": challenge,
        "invitations": invitations,
        "user_invitation": user_invitation,
        "is_expired": is_expired,
        "leaderboard": leaderboard,
    }

    return render(request, "web/peer_challenges/challenge_detail.html", context)


@login_required
def accept_invitation(request, invitation_id):
    """Accept a peer challenge invitation."""
    invitation = get_object_or_404(PeerChallengeInvitation, id=invitation_id, participant=request.user)

    if invitation.status != "pending":
        messages.error(request, "This invitation is no longer pending.")
        return redirect("challenge_list")

    invitation.status = "accepted"
    invitation.save()

    messages.success(request, f"You've accepted the challenge: {invitation.challenge.title}")
    return redirect("take_challenge", invitation_id=invitation.id)


@login_required
def decline_invitation(request, invitation_id):
    """Decline a peer challenge invitation."""
    invitation = get_object_or_404(PeerChallengeInvitation, id=invitation_id, participant=request.user)

    if invitation.status != "pending":
        messages.error(request, "This invitation is no longer pending.")
        return redirect("challenge_list")

    messages.success(request, f"You've declined the challenge: {invitation.challenge.title}")
    return redirect("challenge_list")


@login_required
def take_challenge(request, invitation_id):
    """Take the quiz associated with a peer challenge."""
    invitation = get_object_or_404(PeerChallengeInvitation, id=invitation_id, participant=request.user)
    challenge = invitation.challenge

    # Debug logging
    print(f"User {request.user.username} taking challenge {challenge.id}: {challenge.title}")

    # Check if the challenge is still active
    if challenge.status != "active" and not challenge.is_expired:
        messages.error(request, "This challenge is no longer active.")
        return redirect("challenge_list")

    # Check if the user has already completed this challenge
    if invitation.status == "completed":
        messages.info(request, "You've already completed this challenge.")
        return redirect("peer_challenge_detail", challenge_id=challenge.id)

    # If user already started a user_quiz for this challenge, redirect to results
    if invitation.user_quiz and invitation.user_quiz.completed:
        return redirect("quiz_results", user_quiz_id=invitation.user_quiz.id)

    # Mark the invitation as accepted if it's still pending
    if invitation.status == "pending":
        invitation.status = "accepted"
        invitation.save()

    # Take the quiz - make sure we do a fresh attempt
    quiz = challenge.quiz

    # Store the invitation ID in the session so we can associate it with the UserQuiz after completion
    request.session["active_challenge_invitation_id"] = invitation_id

    # Redirect to the quiz taking page
    return redirect("take_quiz", quiz_id=quiz.id)


@login_required
def complete_challenge(request, user_quiz_id):
    """Complete a peer challenge after taking the quiz."""
    user_quiz = get_object_or_404(UserQuiz, id=user_quiz_id, user=request.user)

    # Debug logging
    print(f"Completing challenge for user quiz {user_quiz_id}")
    print(f"User quiz details: completed={user_quiz.completed}, score={user_quiz.score}")

    # Find the invitation associated with this quiz
    invitation = PeerChallengeInvitation.objects.filter(
        participant=request.user,
        challenge__quiz=user_quiz.quiz,
        status__in=["pending", "accepted"],  # Only update pending or accepted invitations
    ).first()

    # Debug logging
    if not invitation:
        print(f"No invitation found for user {request.user} and quiz {user_quiz.quiz}")
        # Try to find by any status just for debugging
        all_invitations = PeerChallengeInvitation.objects.filter(
            participant=request.user, challenge__quiz=user_quiz.quiz
        )
        if all_invitations.exists():
            print(f"Found invitations with different statuses: {[inv.status for inv in all_invitations]}")

        messages.error(request, "No associated challenge found for this quiz attempt.")
        return redirect("quiz_results", user_quiz_id=user_quiz.id)

    # Debug logging
    print(f"Found invitation: {invitation.id}, current status: {invitation.status}")

    # Update the invitation with the quiz results
    invitation.user_quiz = user_quiz
    invitation.status = "completed"
    invitation.save()

    # Check if all invitations are completed to update challenge status
    challenge = invitation.challenge
    pending_invitations = PeerChallengeInvitation.objects.filter(
        challenge=challenge, status__in=["pending", "accepted"]
    ).exists()

    # Debug logging
    print(f"Pending invitations for challenge {challenge.id}: {pending_invitations}")

    if not pending_invitations:
        challenge.status = "completed"
        challenge.save()

    messages.success(request, f"You've completed the challenge: {challenge.title}")
    return redirect("peer_challenge_detail", challenge_id=challenge.id)


@login_required
def leaderboard(request, challenge_id):
    """Display the leaderboard for a completed challenge."""
    challenge = get_object_or_404(PeerChallenge, id=challenge_id)

    # Check if the user is allowed to view this challenge
    if (
        challenge.creator != request.user
        and not PeerChallengeInvitation.objects.filter(challenge=challenge, participant=request.user).exists()
    ):
        return HttpResponseForbidden("You don't have permission to view this leaderboard.")

    # Get all invitations regardless of status for debug info
    all_invitations = PeerChallengeInvitation.objects.filter(challenge=challenge).select_related(
        "participant", "user_quiz"
    )

    # Calculate leaderboard data
    leaderboard_data = calculate_leaderboard(challenge)

    # Add debug information
    debug_info = {
        "total_invitations": all_invitations.count(),
        "completed_invitations": all_invitations.filter(status="completed").count(),
        "invitations_with_quiz": all_invitations.filter(user_quiz__isnull=False).count(),
        "completed_quizzes": all_invitations.filter(user_quiz__isnull=False, user_quiz__completed=True).count(),
        "challenge_status": challenge.status,
    }

    context = {
        "challenge": challenge,
        "leaderboard": leaderboard_data,
        "debug_info": debug_info,
        "has_entries": len(leaderboard_data) > 0,
    }

    return render(request, "web/peer_challenges/leaderboard.html", context)


def calculate_leaderboard(challenge):
    """Helper function to calculate leaderboard data for a challenge."""
    # First check if there are any invitations with a user_quiz, regardless of status
    all_invitations_with_quiz = PeerChallengeInvitation.objects.filter(
        challenge=challenge, user_quiz__isnull=False
    ).select_related("participant", "user_quiz")

    # If the quiz has been taken but the status wasn't updated, update it now
    for invitation in all_invitations_with_quiz:
        if invitation.user_quiz.completed and invitation.status != "completed":
            invitation.status = "completed"
            invitation.save()

    # Now get all completed invitations
    invitations = PeerChallengeInvitation.objects.filter(
        challenge=challenge, status="completed", user_quiz__isnull=False, participant__profile__is_profile_public=True
    ).select_related("participant", "user_quiz")

    leaderboard_data = []

    for invitation in invitations:
        user_quiz = invitation.user_quiz
        participant = invitation.participant

        # Calculate score and other metrics
        total_questions = user_quiz.quiz.questions.count()
        score_percentage = user_quiz.score or 0

        # Calculate correct answer count based on percentage
        correct_count = int(round((score_percentage / 100) * total_questions)) if total_questions > 0 else 0

        # Get raw completion time
        raw_completion_time = user_quiz.end_time - user_quiz.start_time if user_quiz.end_time else None

        # Format completion time without decimal points
        formatted_completion_time = None
        if raw_completion_time:
            total_seconds = int(raw_completion_time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                formatted_completion_time = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                formatted_completion_time = f"{minutes}m {seconds}s"
            else:
                formatted_completion_time = f"{seconds}s"

        leaderboard_data.append(
            {
                "participant": participant,
                "score": score_percentage,
                "total_questions": total_questions,
                "correct_count": correct_count,
                "percentage": score_percentage,
                "completion_time": formatted_completion_time,
                "raw_completion_time": raw_completion_time,  # Keep raw time for sorting
                "completed_at": user_quiz.end_time,
            }
        )

    # Sort by score (descending) and then by completion time (ascending)
    leaderboard_data.sort(key=lambda x: (-x["score"], x["raw_completion_time"] or timezone.timedelta(days=999)))

    # Add rank
    for i, entry in enumerate(leaderboard_data):
        entry["rank"] = i + 1

    return leaderboard_data


@login_required
def submit_to_leaderboard(request, user_quiz_id):
    """Submit a completed quiz to the peer challenge leaderboard."""
    user_quiz = get_object_or_404(UserQuiz, id=user_quiz_id, user=request.user)

    # Find the invitation associated with this quiz
    invitation = PeerChallengeInvitation.objects.filter(
        participant=request.user, challenge__quiz=user_quiz.quiz
    ).first()

    if not invitation:
        messages.error(request, "No associated challenge found for this quiz attempt.")
        return redirect("quiz_results", user_quiz_id=user_quiz_id)

    # If the user has already completed this challenge, redirect to the leaderboard
    if invitation.status == "completed":
        messages.info(request, "Your results are already on the challenge leaderboard.")
        return redirect("challenge_leaderboard", challenge_id=invitation.challenge.id)

    # Update the invitation with the quiz results
    invitation.user_quiz = user_quiz
    invitation.status = "completed"
    invitation.save()

    # Check if all invitations are completed to update challenge status
    challenge = invitation.challenge
    pending_invitations = PeerChallengeInvitation.objects.filter(
        challenge=challenge, status__in=["pending", "accepted"]
    ).exists()

    if not pending_invitations:
        challenge.status = "completed"
        challenge.save()

    messages.success(request, "Your results have been submitted to the challenge leaderboard!")

    # Redirect to the challenge leaderboard
    return redirect("challenge_leaderboard", challenge_id=invitation.challenge.id)
