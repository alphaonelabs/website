from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from .models import PeerMessage

# Initialize Fernet with the master key from settings
master_fernet = Fernet(settings.SECURE_MESSAGE_KEY)

# --- Envelope Encryption Utility Functions ---


def encrypt_message_with_random_key(message: str) -> tuple[str, str]:
    """
    Encrypts a message using a randomly generated key (data key), then encrypts that key with the master key.
    Returns a tuple: (encrypted_message, encrypted_random_key)
    Both are returned as UTF-8 decoded strings.
    """
    random_key = Fernet.generate_key()  # Generate a random key for this message.
    f_random = Fernet(random_key)  # Create a Fernet instance with the random key.
    encrypted_message = f_random.encrypt(message.encode("utf-8"))
    encrypted_random_key = master_fernet.encrypt(random_key)
    return encrypted_message.decode("utf-8"), encrypted_random_key.decode("utf-8")


def decrypt_message_with_random_key(encrypted_message: str, encrypted_random_key: str) -> str:
    """
    Decrypts a message that was encrypted with a random key.
    First, decrypts the random key using the master key, then decrypts the message using that random key.
    """
    random_key = master_fernet.decrypt(encrypted_random_key.encode("utf-8"))
    f_random = Fernet(random_key)
    plaintext = f_random.decrypt(encrypted_message.encode("utf-8"))
    return plaintext.decode("utf-8")


# --- Simple Encryption Utility Functions (if needed) ---
def encrypt_message(message: str) -> bytes:
    return master_fernet.encrypt(message.encode("utf-8"))


def decrypt_message(token: bytes) -> str:
    return master_fernet.decrypt(token).decode("utf-8")


def send_secure_teacher_message(email_to: str, message: str):
    """
    Encrypts a teacher message using simple encryption and sends an email notification.
    Uses the teacher_message.html email template.
    """
    encrypted_message = encrypt_message(message)
    context = {"encrypted_message": encrypted_message.decode("utf-8")}
    subject = "New Secure Message"
    message_body = render_to_string("web/emails/teacher_message.html", context)
    send_mail(subject, message_body, settings.DEFAULT_FROM_EMAIL, [email_to])


# --- Secure Messaging Views Using Envelope Encryption ---


@login_required
def messaging_dashboard(request):
    """
    Renders a messaging dashboard that doubles as the inbox.
    It immediately displays all messages (decrypted) for the logged-in user,
    marks them as read, and computes an expiration countdown (messages expire 7 days after creation).
    """
    messages_qs = PeerMessage.objects.filter(receiver=request.user).order_by("created_at")
    message_list = []
    now = timezone.now()
    for msg in messages_qs:
        # Mark message as read and update read receipt
        if not msg.is_read:
            msg.is_read = True
            msg.read_at = now
            msg.save(update_fields=["is_read", "read_at"])
        try:
            decrypted_message = decrypt_message_with_random_key(msg.content, msg.encrypted_key)
        except Exception:
            decrypted_message = "[Error decrypting message]"
        expires_at = msg.created_at + timezone.timedelta(days=7)
        time_remaining = expires_at - now
        days = time_remaining.days
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        expiration_str = f"{days}d {hours}h {minutes}m"
        message_list.append(
            {
                "id": msg.id,
                "sender": msg.sender.username,
                "content": decrypted_message,
                "sent_at": msg.created_at,
                "expires_in": expiration_str,
                "starred": msg.starred,
            }
        )
    context = {
        "messages": message_list,
        "inbox_count": len(message_list),
    }
    return render(request, "web/messaging/dashboard.html", context)


@login_required
def compose_message(request):
    """
    Renders a compose message page.
    On POST, processes sending the message using envelope encryption and redirects back.
    Expects 'recipient' and 'message' fields.
    """
    if request.method == "POST":
        recipient_identifier = request.POST.get("recipient")
        message_text = request.POST.get("message")
        if not recipient_identifier or not message_text:
            messages.error(request, "Both recipient and message are required.")
            return redirect("compose_message")

        User = get_user_model()
        try:
            recipient = User.objects.get(username=recipient_identifier)
        except User.DoesNotExist:
            messages.error(request, "Recipient not found.")
            return redirect("compose_message")

        encrypted_message, encrypted_key = encrypt_message_with_random_key(message_text)
        PeerMessage.objects.create(
            sender=request.user, receiver=recipient, content=encrypted_message, encrypted_key=encrypted_key
        )
        messages.success(request, "Message sent successfully!")
        return redirect("compose_message")

    return render(request, "web/messaging/compose.html")


@login_required
def send_encrypted_message(request):
    """
    API view to send an encrypted message via POST using envelope encryption.
    Expects 'recipient' and 'message' fields.
    """
    if request.method == "POST":
        message_text = request.POST.get("message")
        recipient_identifier = request.POST.get("recipient")
        if not message_text or not recipient_identifier:
            return JsonResponse({"error": "Recipient and message are required."}, status=400)

        User = get_user_model()
        try:
            recipient = User.objects.get(username=recipient_identifier)
        except User.DoesNotExist:
            return JsonResponse({"error": "Recipient not found."}, status=404)

        encrypted_message, encrypted_key = encrypt_message_with_random_key(message_text)
        message_instance = PeerMessage.objects.create(
            sender=request.user, receiver=recipient, content=encrypted_message, encrypted_key=encrypted_key
        )
        return JsonResponse({"status": "success", "message_id": message_instance.id})
    return JsonResponse({"error": "Invalid method."}, status=405)


@login_required
def inbox(request):
    """
    Renders an inbox page displaying decrypted messages for the logged-in user.
    Also computes an expiration countdown (messages expire 7 days after creation).
    """
    messages_qs = PeerMessage.objects.filter(receiver=request.user).order_by("created_at")
    message_list = []
    now = timezone.now()
    for msg in messages_qs:
        # Mark message as read and update read receipt
        if not msg.is_read:
            msg.is_read = True
            msg.read_at = now
            msg.save(update_fields=["is_read", "read_at"])
        try:
            decrypted_message = decrypt_message_with_random_key(msg.content, msg.encrypted_key)
        except Exception:
            decrypted_message = "[Error decrypting message]"
        expires_at = msg.created_at + timezone.timedelta(days=7)
        time_remaining = expires_at - now
        days = time_remaining.days
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        expiration_str = f"{days}d {hours}h {minutes}m"
        message_list.append(
            {
                "id": msg.id,
                "sender": msg.sender.username,
                "content": decrypted_message,
                "sent_at": msg.created_at.isoformat(),
                "expires_in": expiration_str,
                "starred": msg.starred,
                "is_read": msg.is_read,
            }
        )
    return render(request, "web/peer/inbox.html", {"messages": message_list})


@login_required
def download_message(request, message_id):
    """
    Decrypts and returns a message as a plain text file download.
    When the message is downloaded, it is deleted from the server (unless it is starred).
    """
    message = get_object_or_404(PeerMessage, id=message_id, receiver=request.user)
    try:
        decrypted_message = decrypt_message_with_random_key(message.content, message.encrypted_key)
    except Exception:
        decrypted_message = "[Error decrypting message]"
    response = HttpResponse(decrypted_message, content_type="text/plain")
    response["Content-Disposition"] = f'attachment; filename="message_{message_id}.txt"'
    # Delete the message after download if it's not starred.
    if not message.starred:
        message.delete()
    return response


@login_required
def toggle_star_message(request, message_id):
    message = get_object_or_404(PeerMessage, id=message_id, receiver=request.user)
    message.starred = not message.starred
    message.save(update_fields=["starred"])
    return redirect("messaging_dashboard")
