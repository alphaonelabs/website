import base64
import json
from datetime import timedelta
from html import unescape
from urllib.parse import urlparse

import bleach
from cryptography.fernet import Fernet
from defusedxml import ElementTree as SafeElementTree
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import PeerMessage

MESSAGE_RETENTION_DAYS = 7


def sanitize_svg(svg_content: str) -> str:
    """Sanitize SVG content using a DOM-based allowlist strategy."""
    if not svg_content:
        return ""

    allowed_tags = {
        "svg",
        "g",
        "path",
        "circle",
        "rect",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "defs",
        "linearGradient",
        "radialGradient",
        "stop",
        "clipPath",
        "mask",
        "title",
        "desc",
    }
    disallowed_tags = {
        "script",
        "iframe",
        "object",
        "embed",
        "foreignObject",
        "link",
        "meta",
        "base",
        "style",
        "animate",
        "set",
        "use",
    }
    allowed_attrs = {
        "id",
        "class",
        "viewBox",
        "width",
        "height",
        "x",
        "y",
        "cx",
        "cy",
        "r",
        "rx",
        "ry",
        "d",
        "fill",
        "fill-rule",
        "fill-opacity",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-opacity",
        "opacity",
        "transform",
        "preserveAspectRatio",
        "points",
        "x1",
        "x2",
        "y1",
        "y2",
        "gradientUnits",
        "gradientTransform",
        "offset",
        "stop-color",
        "stop-opacity",
        "clip-path",
        "mask",
        "role",
        "aria-label",
        "focusable",
        "xmlns",
        "version",
        "href",
        "src",
    }

    def local_name(name: str) -> str:
        return name.split("}", 1)[1] if name.startswith("{") else name

    def is_safe_uri(value: str) -> bool:
        decoded = unescape((value or "").strip())
        if not decoded:
            return False
        if decoded.startswith("#"):
            return True
        parsed = urlparse(decoded)
        scheme = (parsed.scheme or "").lower()
        if scheme in {"http", "https"}:
            return True
        return scheme == "data" and decoded.lower().startswith("data:image/")

    try:
        root = SafeElementTree.fromstring(svg_content)
    except Exception:
        return ""

    if local_name(root.tag) != "svg":
        return ""

    parent_map = {child: parent for parent in root.iter() for child in parent}

    for element in list(root.iter()):
        tag_name = local_name(element.tag)
        if tag_name in disallowed_tags or tag_name not in allowed_tags:
            parent = parent_map.get(element)
            if parent is not None:
                parent.remove(element)
            continue

        for attribute_name in list(element.attrib.keys()):
            attr_name = local_name(attribute_name)
            attr_name_lower = attr_name.lower()

            if attr_name_lower.startswith("on"):
                element.attrib.pop(attribute_name, None)
                continue

            if attr_name_lower in {"style", "xmlns:xlink", "xlink:href"}:
                element.attrib.pop(attribute_name, None)
                continue

            if attr_name not in allowed_attrs:
                element.attrib.pop(attribute_name, None)
                continue

            if attr_name in {"href", "src"} and not is_safe_uri(element.attrib.get(attribute_name, "")):
                element.attrib.pop(attribute_name, None)

    serialized_svg = SafeElementTree.tostring(root, encoding="unicode")
    cleaned_svg = bleach.clean(
        serialized_svg,
        tags=allowed_tags,
        attributes={"*": list(allowed_attrs)},
        protocols=["http", "https", "data"],
        strip=True,
    )
    return cleaned_svg.strip()


@login_required
@require_POST
def mark_messages_read(request):
    """
    AJAX endpoint to mark messages from a specific sender as read.

    Expects JSON body with 'username' field identifying the sender.
    Updates is_read=True and read_at timestamp for matching messages.

    Returns:
        JsonResponse with success status or error details.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    username = data.get("username")
    if not username:
        return JsonResponse({"success": False, "error": "No username provided"}, status=400)
    User = get_user_model()
    try:
        sender = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    PeerMessage.objects.filter(sender=sender, receiver=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return JsonResponse({"success": True})


def get_message_retention_cutoff():
    """Return the datetime cutoff for message retention based on MESSAGE_RETENTION_DAYS."""
    return timezone.now() - timedelta(days=MESSAGE_RETENTION_DAYS)


def cleanup_expired_peer_messages() -> int:
    """Delete direct messages older than MESSAGE_RETENTION_DAYS and return deleted count."""
    cutoff = get_message_retention_cutoff()
    expired_qs = PeerMessage.objects.filter(created_at__lt=cutoff)
    deleted_count = expired_qs.delete()[0]
    return deleted_count


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
    """Encrypt a message using the master Fernet key."""
    return master_fernet.encrypt(message.encode("utf-8"))


def decrypt_message(token: bytes) -> str:
    """Decrypt a Fernet-encrypted token using the master key."""
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
    from django.contrib.auth import get_user_model

    User = get_user_model()
    cleanup_expired_peer_messages()
    # Handle POST for sending a message from dashboard chat
    if request.method == "POST":
        recipient_identifier = request.POST.get("recipient")
        message_text = request.POST.get("message")
        if not recipient_identifier or not message_text:
            messages.error(request, "Both recipient and message are required.")
            return redirect("messaging_dashboard")
        try:
            recipient = User.objects.get(username=recipient_identifier)
        except User.DoesNotExist:
            messages.error(request, "Recipient not found.")
            return redirect("messaging_dashboard")
        encrypted_message, encrypted_key = encrypt_message_with_random_key(message_text)
        PeerMessage.objects.create(
            sender=request.user, receiver=recipient, content=encrypted_message, encrypted_key=encrypted_key
        )
        messages.success(request, "Message sent successfully!")
        return redirect("messaging_dashboard")

    # now = timezone.now()  # Removed unused variable
    # Get all users the current user has messaged or received from
    sent_users = PeerMessage.objects.filter(sender=request.user).values_list("receiver", flat=True)
    received_users = PeerMessage.objects.filter(receiver=request.user).values_list("sender", flat=True)
    user_ids = set(list(sent_users) + list(received_users))
    user_ids.discard(request.user.id)

    users = User.objects.filter(id__in=user_ids).select_related("profile")
    users_by_id = {user.id: user for user in users}

    all_messages = (
        PeerMessage.objects.filter(
            models.Q(sender=request.user, receiver_id__in=user_ids)
            | models.Q(receiver=request.user, sender_id__in=user_ids)
        )
        .select_related("sender", "receiver")
        .order_by("created_at")
    )

    messages_by_other_user_id = {}
    current_user_id = request.user.id
    for msg in all_messages:
        other_user_id = msg.receiver_id if msg.sender_id == current_user_id else msg.sender_id
        messages_by_other_user_id.setdefault(other_user_id, []).append(msg)

    unread_counts = dict(
        PeerMessage.objects.filter(sender_id__in=user_ids, receiver=request.user, is_read=False)
        .values_list("sender_id")
        .annotate(unread=models.Count("id"))
    )

    people = []
    for uid in user_ids:
        user = users_by_id.get(uid)
        if not user:
            continue
        # Get avatar URL or fallback
        avatar_url = None
        if hasattr(user, "profile"):
            if getattr(user.profile, "custom_avatar", None) and getattr(user.profile.custom_avatar, "svg", None):
                # Custom SVG avatar (render as data URI)
                svg = user.profile.custom_avatar.svg
                sanitized_svg = sanitize_svg(svg)
                if sanitized_svg:
                    encoded_svg = base64.b64encode(sanitized_svg.encode("utf-8")).decode("ascii")
                    avatar_url = f"data:image/svg+xml;base64,{encoded_svg}"
            elif getattr(user.profile, "avatar", None):
                if user.profile.avatar:
                    avatar_url = user.profile.avatar.url

        msgs = messages_by_other_user_id.get(uid, [])
        msg_list = []
        for msg in msgs:
            try:
                decrypted_message = decrypt_message_with_random_key(msg.content, msg.encrypted_key)
            except Exception:
                decrypted_message = "[Error decrypting message]"
            msg_list.append(
                {
                    "id": msg.id,
                    "sender": msg.sender.username,
                    "content": decrypted_message,
                    "sent_at": msg.created_at,
                    "starred": msg.starred,
                }
            )
        has_unread = unread_counts.get(uid, 0) > 0
        people.append(
            {
                "username": user.username,
                "display_name": user.get_full_name() or user.username,
                "avatar_url": avatar_url,
                "messages": msg_list,
                "has_unread": has_unread,
            }
        )
    people = [person for person in people if person["messages"]]
    people.sort(key=lambda person: person["messages"][-1]["sent_at"], reverse=True)
    # For legacy: keep inbox_count for header
    all_received = PeerMessage.objects.filter(receiver=request.user)
    inbox_count = all_received.count()
    context = {
        "people": people,
        "inbox_count": inbox_count,
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
        return redirect("messaging_dashboard")

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
@require_POST
def toggle_star_message(request, message_id):
    """Toggle the starred status of a message owned by the current user."""
    message = get_object_or_404(PeerMessage, Q(sender=request.user) | Q(receiver=request.user), id=message_id)
    message.starred = not message.starred
    message.save(update_fields=["starred"])
    return JsonResponse({"success": True, "message_id": message.id, "starred": message.starred})
