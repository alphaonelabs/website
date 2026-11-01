import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string

from .forms import (
    QuizForm,
    QuizOptionFormSet,
    QuizQuestionForm,
    TakeQuizForm,
)
from .models import Quiz, QuizQuestion, UserQuiz


@login_required
def quiz_list(request):
    """Display a list of quizzes created by the user and quizzes shared with them."""
    user_created_quizzes = Quiz.objects.filter(creator=request.user).order_by("-created_at")

    # Find quizzes shared with this user via attempts
    shared_quizzes = (
        Quiz.objects.filter(user_quizzes__user=request.user)
        .exclude(creator=request.user)
        .distinct()
        .order_by("-created_at")
    )

    # Find public quizzes
    public_quizzes = (
        Quiz.objects.filter(status="published", allow_anonymous=True)
        .exclude(Q(creator=request.user) | Q(id__in=shared_quizzes))
        .order_by("-created_at")[:10]
    )  # Show only 10 recent public quizzes

    context = {
        "user_created_quizzes": user_created_quizzes,
        "shared_quizzes": shared_quizzes,
        "public_quizzes": public_quizzes,
    }

    return render(request, "web/quiz/quiz_list.html", context)


@login_required
def create_quiz(request):
    """Create a new quiz."""
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.creator = request.user
            quiz.share_code = get_random_string(8)
            quiz.save()
            messages.success(request, "Quiz created successfully. Now add some questions!")
            return redirect("quiz_detail", quiz_id=quiz.id)
    else:
        form = QuizForm()

    return render(request, "web/quiz/quiz_form.html", {"form": form, "title": "Create Quiz"})


@login_required
def update_quiz(request, quiz_id):
    """Update an existing quiz."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to edit this quiz.")

    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "Quiz updated successfully.")
            return redirect("quiz_detail", quiz_id=quiz.id)
    else:
        form = QuizForm(instance=quiz)

    return render(request, "web/quiz/quiz_form.html", {"form": form, "quiz": quiz, "title": "Edit Quiz"})


@login_required
def quiz_detail(request, quiz_id):
    """Display quiz details, questions, and management options."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check permissions
    is_owner = quiz.creator == request.user
    can_view = is_owner or quiz.status == "published"

    if not can_view:
        return HttpResponseForbidden("You don't have permission to view this quiz.")

    # Get questions with option counts
    questions = quiz.questions.annotate(option_count=Count("options")).order_by("order")

    # Get attempts by this user
    user_attempts = UserQuiz.objects.filter(quiz=quiz, user=request.user).order_by("-start_time")

    # For quiz owners, get overall stats
    if is_owner:
        total_attempts = UserQuiz.objects.filter(quiz=quiz).count()
        average_score = UserQuiz.objects.filter(quiz=quiz).exclude(score=None).values_list("score", flat=True)
        if average_score:
            average_score = sum(average_score) / len(average_score)
        else:
            average_score = 0
    else:
        total_attempts = None
        average_score = None

    context = {
        "quiz": quiz,
        "questions": questions,
        "is_owner": is_owner,
        "user_attempts": user_attempts,
        "total_attempts": total_attempts,
        "average_score": average_score,
        "share_url": request.build_absolute_uri(reverse("quiz_take_shared", kwargs={"share_code": quiz.share_code})),
    }

    return render(request, "web/quiz/quiz_detail.html", context)


@login_required
def add_question(request, quiz_id):
    """Add a question to a quiz."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to edit this quiz.")

    # Calculate the next order value
    next_order = 1
    if quiz.questions.exists():
        next_order = quiz.questions.order_by("-order").first().order + 1

    if request.method == "POST":
        form = QuizQuestionForm(request.POST, request.FILES)
        # Set the quiz ID explicitly in the form data
        form.instance.quiz_id = quiz.id
        formset = QuizOptionFormSet(request.POST, request.FILES, prefix="options")

        # Validate form and formset
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()

        if form_valid and formset_valid:
            try:
                with transaction.atomic():
                    # Save the question
                    question = form.save(commit=False)
                    question.quiz = quiz
                    question.order = next_order
                    question.save()

                    # Save the options
                    formset.instance = question

                    for i, option_form in enumerate(formset):
                        if option_form.cleaned_data and not option_form.cleaned_data.get("DELETE", False):
                            option = option_form.save(commit=False)
                            option.question = question
                            option.order = i  # Set order value based on position in the formset
                            option.save()

                messages.success(request, "Question added successfully.")

                # Redirect based on the button clicked
                if "save_and_add" in request.POST:
                    return redirect("add_question", quiz_id=quiz.id)
                else:
                    return redirect("quiz_detail", quiz_id=quiz.id)
            except Exception as e:
                print(e)
                # Re-raise the exception
                raise
    else:
        form = QuizQuestionForm()
        formset = QuizOptionFormSet(prefix="options")

    return render(
        request,
        "web/quiz/question_form.html",
        {"form": form, "formset": formset, "quiz": quiz, "title": "Add Question"},
    )


@login_required
def edit_question(request, question_id):
    """Edit an existing question."""
    question = get_object_or_404(QuizQuestion, id=question_id)
    quiz = question.quiz

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to edit this question.")

    if request.method == "POST":
        form = QuizQuestionForm(request.POST, instance=question)
        formset = QuizOptionFormSet(request.POST, instance=question, prefix="options")

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()

            messages.success(request, "Question updated successfully.")
            return redirect("quiz_detail", quiz_id=quiz.id)
    else:
        form = QuizQuestionForm(instance=question)
        formset = QuizOptionFormSet(instance=question, prefix="options")

    return render(
        request,
        "web/quiz/question_form.html",
        {"form": form, "formset": formset, "quiz": quiz, "question": question, "title": "Edit Question"},
    )


@login_required
def delete_question(request, question_id):
    """Delete a question from a quiz."""
    question = get_object_or_404(QuizQuestion, id=question_id)
    quiz = question.quiz

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to delete this question.")

    if request.method == "POST":
        quiz_id = quiz.id
        question.delete()

        # Re-order the remaining questions
        for i, q in enumerate(quiz.questions.order_by("order")):
            q.order = i + 1
            q.save()

        messages.success(request, "Question deleted successfully.")
        return redirect("quiz_detail", quiz_id=quiz_id)

    return render(request, "web/quiz/delete_question.html", {"question": question, "quiz": quiz})


@login_required
def delete_quiz(request, quiz_id):
    """Delete an entire quiz."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if user can delete this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to delete this quiz.")

    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Quiz deleted successfully.")
        return redirect("quiz_list")

    return render(request, "web/quiz/delete_quiz.html", {"quiz": quiz})


def take_quiz_shared(request, share_code):
    """Allow anyone with the share code to take the quiz."""
    quiz = get_object_or_404(Quiz, share_code=share_code)

    # Check if quiz is available
    if quiz.status != "published":
        messages.error(request, "This quiz is not currently available.")
        return redirect("index")

    # Check if anonymous users are allowed
    if not quiz.allow_anonymous and not request.user.is_authenticated:
        messages.error(request, "You must be logged in to take this quiz.")
        return redirect("account_login")

    return _process_quiz_taking(request, quiz)


@login_required
def take_quiz(request, quiz_id):
    """Take a quiz as an authenticated user."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if quiz is available
    if quiz.status != "published":
        messages.error(request, "This quiz is not currently available.")
        return redirect("quiz_list")

    return _process_quiz_taking(request, quiz)


def _process_quiz_taking(request, quiz):
    """Helper function to process quiz taking for both routes."""
    # Check if the quiz has questions
    if not quiz.questions.exists():
        messages.error(request, "This quiz does not have any questions yet.")
        return redirect("quiz_list")

    # Get the questions in the correct order
    questions = list(quiz.questions.order_by("order"))

    # Shuffle questions if quiz settings require it
    if quiz.randomize_questions:
        random.shuffle(questions)

    # Create a new UserQuiz attempt record
    user = request.user if request.user.is_authenticated else None

    # Check if user has already reached max attempts
    if user and quiz.max_attempts > 0:
        attempt_count = UserQuiz.objects.filter(quiz=quiz, user=user).count()
        if attempt_count >= quiz.max_attempts:
            messages.error(
                request, f"You have reached the maximum number of attempts ({quiz.max_attempts}) for this quiz."
            )
            return redirect("quiz_detail", quiz_id=quiz.id)

    user_quiz = UserQuiz(quiz=quiz, user=user)
    user_quiz.save()

    # Prepare questions and options for display
    prepared_questions = []
    for question in questions:
        q_dict = {
            "id": question.id,
            "text": question.text,
            "question_type": question.question_type,
            "explanation": question.explanation,
            "points": question.points,
        }

        # Get options but create new objects that don't have is_correct attribute at all
        options = list(question.options.all())

        # Shuffle options if quiz has option randomization setting
        if quiz.randomize_questions:
            random.shuffle(options)
        # Create plain dictionaries instead of objects to ensure no is_correct data reaches the template
        # This is the most definitive way to prevent any trace of correctness information
        clean_options = []
        for option in options:
            # Only include the minimal data needed for display - deliberately excluding is_correct
            clean_option = {"id": option.id, "text": option.text, "order": option.order}
            clean_options.append(clean_option)

        q_dict["options"] = clean_options
        prepared_questions.append(q_dict)

    if request.method == "POST":
        form = TakeQuizForm(request.POST, quiz=quiz)

        if form.is_valid():
            # Process answers
            answers = {}
            score = 0
            total_points = 0

            for question in prepared_questions:
                q_id = str(question["id"])
                question_obj = QuizQuestion.objects.get(id=question["id"])
                total_points += question_obj.points

                if question_obj.question_type == "multiple":
                    user_answer = form.cleaned_data.get(f"question_{q_id}", None)

                    # Handle case when user_answer is a list (multiple selections)
                    if isinstance(user_answer, list):
                        user_answer_ids = [int(ans) for ans in user_answer] if user_answer else []
                        correct_options = list(
                            question_obj.options.filter(is_correct=True).values_list("id", flat=True)
                        )

                        # Check if all user answers are in correct options AND all correct options are selected
                        is_correct = False
                        if user_answer_ids and correct_options:
                            # For strict checking: all correct options must be selected and no incorrect ones
                            is_correct = set(user_answer_ids) == set(correct_options)

                        answers[q_id] = {
                            "user_answer": user_answer,
                            "correct_answer": correct_options,
                            "is_correct": is_correct,
                        }
                    # Handle case when user_answer is a single value (e.g., from radio button)
                    else:
                        user_answer_id = int(user_answer) if user_answer is not None else None
                        correct_options = list(
                            question_obj.options.filter(is_correct=True).values_list("id", flat=True)
                        )

                        answers[q_id] = {
                            "user_answer": user_answer,
                            "correct_answer": correct_options[0] if correct_options else None,
                            "is_correct": user_answer_id in correct_options if user_answer_id is not None else False,
                        }

                    if answers[q_id]["is_correct"]:
                        score += question_obj.points

                elif question_obj.question_type == "true_false":
                    user_answer = form.cleaned_data.get(f"question_{q_id}", None)
                    correct_answer = question_obj.options.filter(is_correct=True).first()

                    # For true/false, the view is receiving the option ID, not the text
                    correct_id = str(correct_answer.id) if correct_answer else None

                    answers[q_id] = {
                        "user_answer": user_answer,
                        "correct_answer": correct_id,
                        "is_correct": user_answer == correct_id if user_answer else False,
                    }

                    if answers[q_id]["is_correct"]:
                        score += question_obj.points

                elif question_obj.question_type == "short":
                    user_answer = form.cleaned_data.get(f"question_{q_id}", "")
                    answers[q_id] = {
                        "user_answer": user_answer,
                        "is_graded": False,  # Short answers need manual grading
                    }

            # Calculate percentage score
            percentage = (score / total_points * 100) if total_points > 0 else 0

            # Update the UserQuiz record
            user_quiz.answers = json.dumps(answers)
            user_quiz.score = percentage
            user_quiz.end_time = timezone.now()
            user_quiz.completed = True
            user_quiz.save()

            # Redirect to results page
            return redirect("quiz_results", user_quiz_id=user_quiz.id)
    else:
        form = TakeQuizForm(quiz=quiz)

    context = {
        "quiz": quiz,
        "questions": prepared_questions,
        "form": form,
        "user_quiz_id": user_quiz.id,
        "user_quiz": user_quiz,
        "time_limit": quiz.time_limit,
    }

    return render(request, "web/quiz/take_quiz.html", context)


def quiz_results(request, user_quiz_id):
    """Display the results of a quiz attempt."""
    user_quiz = get_object_or_404(UserQuiz, id=user_quiz_id)
    quiz = user_quiz.quiz

    # Check permissions
    if user_quiz.user and user_quiz.user != request.user and quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to view these results.")

    # If quiz is still in progress, redirect to take it
    if not user_quiz.completed:
        if quiz.share_code:
            return redirect("quiz_take_shared", share_code=quiz.share_code)
        else:
            return redirect("take_quiz", quiz_id=quiz.id)

    # Parse the answers JSON
    answers = json.loads(user_quiz.answers) if user_quiz.answers else {}

    # Calculate stats
    total_questions = quiz.questions.count()

    # Only count questions that have actual answers (not empty or None)
    questions_attempted = 0
    for q_id, ans_data in answers.items():
        # For multiple choice and true/false questions
        if ans_data.get("user_answer") not in [None, "", [], {}]:
            questions_attempted += 1
    correct_count = sum(1 for ans in answers.values() if ans.get("is_correct", False))

    # Calculate duration
    if user_quiz.start_time and user_quiz.end_time:
        duration_seconds = (user_quiz.end_time - user_quiz.start_time).total_seconds()
        minutes, seconds = divmod(int(duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            duration = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            duration = f"{minutes}m {seconds}s"
        else:
            duration = f"{seconds}s"
    else:
        duration = "N/A"

    # Get the questions with their correct answers
    questions = []
    for question in quiz.questions.order_by("order"):
        q_dict = {
            "id": question.id,
            "text": question.text,
            "question_type": question.question_type,
            "explanation": question.explanation,
            "points": question.points,
        }

        if question.question_type == "multiple":
            q_dict["options"] = list(question.options.all())
            q_dict["correct_options"] = list(question.options.filter(is_correct=True))

        elif question.question_type == "true_false":
            q_dict["options"] = list(question.options.all())
            q_dict["correct_option"] = question.options.filter(is_correct=True).first()

        # Add user's answer if available
        q_id = str(question.id)
        if q_id in answers:
            q_dict["user_answer"] = answers[q_id].get("user_answer")
            q_dict["is_correct"] = answers[q_id].get("is_correct", False)

        questions.append(q_dict)

    # Get all questions for the quiz to display in the questions section
    all_quiz_questions = []
    for question in quiz.questions.order_by("order"):
        q_info = {
            "id": question.id,
            "text": question.text,
            "question_type": question.question_type,
            "type_display": question.get_question_type_display(),
            "explanation": question.explanation,
            "options": list(question.options.all()) if question.question_type != "short" else None,
        }
        all_quiz_questions.append(q_info)

    # Update quiz completion status and score
    user_quiz.completed = True
    user_quiz.end_time = timezone.now()  # Ensure end_time is set if not already
    user_quiz.save()

    # Check if this quiz is associated with a challenge
    challenge_invitation = None
    if request.user.is_authenticated:
        from .models import PeerChallengeInvitation

        # First try to find an invitation that's already associated with this user_quiz
        challenge_invitation = PeerChallengeInvitation.objects.filter(
            user_quiz=user_quiz, participant=request.user
        ).first()

        # If not found, look for an invitation for this quiz
        if not challenge_invitation:
            challenge_invitation = PeerChallengeInvitation.objects.filter(
                participant=request.user, challenge__quiz=quiz
            ).first()

    # Get user attempts count for this quiz
    user_attempts = 0
    if request.user.is_authenticated:
        user_attempts = UserQuiz.objects.filter(quiz=quiz, user=request.user).count()

    context = {
        "user_quiz": user_quiz,
        "quiz": quiz,
        "questions": questions,
        "all_quiz_questions": all_quiz_questions,
        "show_answers": quiz.creator == request.user,
        "is_owner": quiz.creator == request.user,
        "is_creator": quiz.creator == request.user,
        "total_questions": total_questions,
        "questions_attempted": questions_attempted,
        "correct_count": correct_count,
        "duration": duration,
        "answers": answers,
        "challenge_invitation": challenge_invitation,
        "user_attempts": user_attempts,
    }

    return render(request, "web/quiz/quiz_results.html", context)


@login_required
def grade_short_answer(request, user_quiz_id, question_id):
    """Allow quiz creator to grade short answer questions."""
    user_quiz = get_object_or_404(UserQuiz, id=user_quiz_id)
    question = get_object_or_404(QuizQuestion, id=question_id)

    # Check permissions
    if question.quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to grade this answer.")

    if request.method == "POST":
        # Get the points awarded
        points_awarded = float(request.POST.get("points_awarded", 0))
        if points_awarded < 0:
            points_awarded = 0
        if points_awarded > question.points:
            points_awarded = question.points

        # Update the answers JSON
        answers = json.loads(user_quiz.answers) if user_quiz.answers else {}
        q_id = str(question.id)

        if q_id in answers:
            answers[q_id]["is_graded"] = True
            answers[q_id]["points_awarded"] = points_awarded
            answers[q_id]["is_correct"] = points_awarded == question.points

            # Calculate new total score
            total_points = sum(q.points for q in user_quiz.quiz.questions.all())
            current_score = sum(
                (
                    answers.get(str(q.id), {}).get("points_awarded", 0)
                    if answers.get(str(q.id), {}).get("is_graded", False)
                    else (question.points if answers.get(str(q.id), {}).get("is_correct", False) else 0)
                )
                for q in user_quiz.quiz.questions.all()
            )

            # Update the UserQuiz record
            user_quiz.answers = json.dumps(answers)
            user_quiz.score = (current_score / total_points * 100) if total_points > 0 else 0
            user_quiz.save()

            messages.success(
                request, f"Answer graded successfully. Awarded {points_awarded} out of {question.points} points."
            )

        return redirect("quiz_results", user_quiz_id=user_quiz.id)

    # Get the current answer
    answers = json.loads(user_quiz.answers) if user_quiz.answers else {}
    q_id = str(question.id)
    answer = answers.get(q_id, {}).get("user_answer", "")

    context = {
        "user_quiz": user_quiz,
        "question": question,
        "answer": answer,
    }

    return render(request, "web/quiz/grade_short_answer.html", context)


@login_required
def quiz_analytics(request, quiz_id):
    """Show detailed analytics for a quiz creator."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check permissions
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to view analytics for this quiz.")

    # Get all attempts
    attempts = UserQuiz.objects.filter(quiz=quiz, completed=True).order_by("-end_time")

    # Calculate overall statistics
    total_attempts = attempts.count()
    average_score = attempts.exclude(score=None).values_list("score", flat=True)
    if average_score:
        average_score = sum(average_score) / len(average_score)
    else:
        average_score = 0

    # Calculate pass rate
    pass_count = attempts.filter(score__gte=quiz.passing_score).count()
    pass_rate = (pass_count / total_attempts * 100) if total_attempts > 0 else 0

    # We're not using JavaScript calculation anymore, so we don't need to prepare timing data

    # Calculate average time on the server side
    avg_time_seconds = 0
    time_tracking_attempts = 0

    for attempt in attempts:
        if attempt.start_time and attempt.end_time:
            duration = (attempt.end_time - attempt.start_time).total_seconds()
            if 0 < duration < 24 * 60 * 60:  # Exclude outliers (more than a day)
                avg_time_seconds += duration
                time_tracking_attempts += 1

    if time_tracking_attempts > 0:
        avg_time_seconds = avg_time_seconds / time_tracking_attempts
        minutes, seconds = divmod(int(avg_time_seconds), 60)
        hours, minutes = divmod(minutes, 60)

        # Format the average time in a user-friendly way
        if hours > 0:
            avg_time = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            avg_time = f"{minutes}m {seconds}s"
        else:
            avg_time = f"{seconds}s"  # Always show seconds even if it's 0
    else:
        avg_time = "N/A"

    # Analyze performance by question
    questions = quiz.questions.all()
    question_stats = {}

    for question in questions:
        question_stats[question.id] = {
            "text": question.text,
            "correct_count": 0,
            "attempt_count": 0,
            "success_rate": 0,
            "type": question.question_type,
        }

    for attempt in attempts:
        if not attempt.answers:
            continue

        answers = json.loads(attempt.answers)
        for q_id, answer_data in answers.items():
            q_id = int(q_id)
            if q_id in question_stats:
                question_stats[q_id]["attempt_count"] += 1
                if answer_data.get("is_correct", False):
                    question_stats[q_id]["correct_count"] += 1

    # Calculate success rates
    for q_id in question_stats:
        stats = question_stats[q_id]
        if stats["attempt_count"] > 0:
            stats["success_rate"] = (stats["correct_count"] / stats["attempt_count"]) * 100
            stats["correct_rate"] = stats["success_rate"]  # For template compatibility

    # Get user performance statistics
    user_performances = []
    user_attempt_dict = {}

    for attempt in attempts:
        user_id = attempt.user.id
        if user_id not in user_attempt_dict:
            user_attempt_dict[user_id] = {
                "user": attempt.user,
                "attempts": 0,
                "best_score": 0,
                "total_score": 0,
            }

        user_data = user_attempt_dict[user_id]
        user_data["attempts"] += 1
        if attempt.score is not None:
            user_data["total_score"] += attempt.score
            if attempt.score > user_data["best_score"]:
                user_data["best_score"] = attempt.score

    for user_id, data in user_attempt_dict.items():
        if data["attempts"] > 0:
            data["avg_score"] = data["total_score"] / data["attempts"]
            user_performances.append(data)

    # Sort by best score
    user_performances.sort(key=lambda x: x["best_score"], reverse=True)

    # Score distribution data for chart
    score_ranges = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0,
    }

    for attempt in attempts:
        if attempt.score is not None:
            if attempt.score <= 20:
                score_ranges["0-20"] += 1
            elif attempt.score <= 40:
                score_ranges["21-40"] += 1
            elif attempt.score <= 60:
                score_ranges["41-60"] += 1
            elif attempt.score <= 80:
                score_ranges["61-80"] += 1
            else:
                score_ranges["81-100"] += 1

    # Prepare chart data in the format expected by the template
    # Score distribution data for chart
    score_distribution = {"labels": list(score_ranges.keys()), "data": list(score_ranges.values())}

    # Question performance data
    question_performance = {
        "labels": [f"Q{i + 1}" for i, q in enumerate(question_stats.values())],
        "data": [q["success_rate"] for q in question_stats.values()],
    }

    # Time chart data - attempts over time by month
    time_data = {}
    for attempt in attempts:
        if attempt.end_time:
            month_year = attempt.end_time.strftime("%b %Y")
            if month_year in time_data:
                time_data[month_year] += 1
            else:
                time_data[month_year] = 1

    # If no data, provide at least one month
    if not time_data:
        current_month = timezone.now().strftime("%b %Y")
        time_data[current_month] = 0

    time_chart = {"labels": list(time_data.keys()), "data": list(time_data.values())}

    # Preprocess recent attempts to ensure duration is calculated
    recent_attempts = attempts[:20]  # Limit to 20 most recent attempts
    for attempt in recent_attempts:
        # Explicitly set time_taken for display in template
        if attempt.start_time and attempt.end_time:
            duration_seconds = (attempt.end_time - attempt.start_time).total_seconds()
            if duration_seconds < 60:
                attempt.time_taken = f"{int(duration_seconds)}s"
            else:
                minutes, seconds = divmod(int(duration_seconds), 60)
                if minutes < 60:
                    attempt.time_taken = f"{minutes}m {seconds}s"
                else:
                    hours, minutes = divmod(minutes, 60)
                    attempt.time_taken = f"{hours}h {minutes}m {seconds}s"
        else:
            attempt.time_taken = "N/A"

    # Create context with all required data
    context = {
        "quiz": quiz,
        "total_attempts": total_attempts,
        "avg_score": average_score,
        "pass_rate": pass_rate,
        "avg_time": avg_time,  # Server-side calculation
        "question_analysis": [stats for stats in question_stats.values()],
        "question_stats": question_stats,
        "recent_attempts": recent_attempts,
        "user_performances": user_performances[:10],  # Top 10 performers
        "score_distribution": score_distribution,
        "question_performance": question_performance,
        "time_chart": time_chart,
    }

    # All context variables are set correctly

    return render(request, "web/quiz/quiz_analytics.html", context)
