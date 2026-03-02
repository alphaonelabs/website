import json
import logging
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from PIL import Image, UnidentifiedImageError
from python_avatars import (
    AccessoryType,
    Avatar,
    AvatarStyle,
    ClothingType,
    EyebrowType,
    EyeType,
    FacialHairType,
    HairType,
    MouthType,
    NoseType,
    SkinColor,
)

from .forms import AvatarForm

# Add logger configuration
logger = logging.getLogger(__name__)

# Constants for avatar upload validation
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_DIMENSION = 4096  # Max width/height in pixels
ALLOWED_IMAGE_FORMATS = ["JPEG", "PNG", "GIF", "WEBP"]


@login_required
def set_avatar_as_profile_pic(request):
    """Set the current avatar as the user's profile picture."""
    if request.method == "POST":
        profile = request.user.profile
        if profile.custom_avatar and profile.custom_avatar.svg:
            try:
                # Create a unique filename for the SVG
                import uuid

                filename = f"avatar_{uuid.uuid4().hex[:8]}.svg"

                # Delete old profile picture if it exists
                if profile.avatar:
                    profile.avatar.delete(save=False)

                # Save the SVG directly
                svg_file = ContentFile(profile.custom_avatar.svg.encode("utf-8"), name=filename)
                profile.avatar.save(filename, svg_file, save=True)

                messages.success(request, "Avatar set as profile picture successfully!")
            except Exception:
                logger.exception("Error setting profile picture")
                messages.error(request, "Error setting profile picture: An internal error occurred")
        else:
            messages.error(request, "No avatar available to set as profile picture.")
    return redirect("profile")


@login_required
def customize_avatar(request):
    """View for customizing user avatar."""
    profile = request.user.profile

    # Generate initial avatar if none exists
    if not profile.custom_avatar:
        from .models import Avatar as AvatarModel

        avatar = AvatarModel(
            style="circle",
            background_color="#FFFFFF",
            top="short_flat",
            eyebrows="default",
            eyes="default",
            nose="default",
            mouth="default",
            facial_hair="none",
            skin_color="light",
            hair_color="#000000",
            accessory="none",
            clothing="hoodie",
            clothing_color="#0000FF",
        )
        avatar.save()
        profile.custom_avatar = avatar
        profile.save()

    if request.method == "POST":
        form = AvatarForm(request.POST)
        if form.is_valid():
            # Get or create avatar instance
            avatar = profile.custom_avatar if profile.custom_avatar else Avatar()

            # Update avatar fields from form
            for field in form.cleaned_data:
                setattr(avatar, field, form.cleaned_data[field])

            # Save avatar (this will also generate the SVG)
            avatar.save()

            # Link avatar to profile if not already linked
            if not profile.custom_avatar:
                profile.custom_avatar = avatar
                profile.save()

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "avatar_svg": avatar.svg})
            return redirect("profile")
    else:
        # Initialize form with current avatar values if it exists
        initial_data = {}
        if profile.custom_avatar:
            for field in AvatarForm.base_fields:
                initial_data[field] = getattr(profile.custom_avatar, field)
        form = AvatarForm(initial=initial_data)

    # Get available options from python_avatars
    avatar_options = {
        "styles": [style.name.lower() for style in AvatarStyle],
        "hair_styles": [style.name.lower() for style in HairType],
        "eyebrow_types": [style.name.lower() for style in EyebrowType],
        "eye_types": [style.name.lower() for style in EyeType],
        "nose_types": [style.name.lower() for style in NoseType],
        "mouth_types": [style.name.lower() for style in MouthType],
        "facial_hair_types": [style.name.lower() for style in FacialHairType],
        "skin_colors": [color.name.lower() for color in SkinColor],
        "accessory_types": [acc.name.lower() for acc in AccessoryType],
        "clothing_types": [clothing.name.lower() for clothing in ClothingType],
    }

    return render(
        request,
        "avatar/customize.html",
        {
            "form": form,
            "avatar_options": avatar_options,
            "current_avatar": profile.custom_avatar.svg if profile.custom_avatar else None,
        },
    )


@login_required
def upload_avatar_photo(request: HttpRequest) -> JsonResponse:
    """AJAX endpoint for uploading avatar photo from camera capture."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

    avatar_file = request.FILES.get("avatar")
    if not avatar_file:
        return JsonResponse({"success": False, "error": "No image provided"}, status=400)

    # Validate file size first (fast check)
    if avatar_file.size > MAX_AVATAR_SIZE:
        return JsonResponse(
            {"success": False, "error": f"Image too large (max {MAX_AVATAR_SIZE // (1024 * 1024)}MB)"}, status=400
        )

    # Validate file type using magic bytes (more secure than content_type)
    try:
        avatar_file.seek(0)
        img = Image.open(avatar_file)
        image_format = img.format  # Cache format before verify
        img.verify()  # Verify it's a valid image (makes img unusable)

        if image_format not in ALLOWED_IMAGE_FORMATS:
            return JsonResponse(
                {"success": False, "error": f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_FORMATS)}"},
                status=400,
            )

        # Reopen image to get dimensions (verify() leaves image unusable)
        avatar_file.seek(0)
        img = Image.open(avatar_file)

        # Validate dimensions to prevent resource exhaustion
        if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
            return JsonResponse(
                {"success": False, "error": f"Image dimensions too large (max {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}px)"},
                status=400,
            )

        avatar_file.seek(0)  # Reset for later use
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid or corrupted image file"}, status=400)

    profile = request.user.profile

    # Capture old file references before modifying (for deletion after commit)
    old_custom_avatar = profile.custom_avatar if profile.custom_avatar else None
    old_avatar = profile.avatar if profile.avatar else None

    try:
        with transaction.atomic():
            # Clear custom avatar if set (so uploaded photo takes precedence)
            if old_custom_avatar:
                profile.custom_avatar = None
                profile.save(update_fields=["custom_avatar"])

            # Clear old avatar reference (file deleted after commit)
            if old_avatar:
                profile.avatar = None
                profile.save(update_fields=["avatar"])

            # Save new avatar
            profile.avatar = avatar_file
            profile.save(update_fields=["avatar"])

            def delete_old_files():
                try:
                    if old_custom_avatar:
                        old_custom_avatar.delete()
                    if old_avatar:
                        old_avatar.delete(save=False)
                except Exception:
                    logger.exception("Error deleting old avatar files")

            transaction.on_commit(delete_old_files)

        avatar_url = f"{profile.avatar.url}?t={int(time.time())}"
        return JsonResponse({"success": True, "avatar_url": avatar_url})
    except Exception:
        logger.exception("Error uploading avatar photo")
        return JsonResponse({"success": False, "error": "Upload failed"}, status=500)


@login_required
def preview_avatar(request):
    """AJAX endpoint for previewing avatar changes."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            avatar = Avatar(
                style=getattr(AvatarStyle, data.get("style", "CIRCLE").upper(), AvatarStyle.CIRCLE),
                background_color=data.get("background_color", "#FFFFFF"),
                top=getattr(HairType, data.get("top", "SHORT_FLAT").upper(), HairType.SHORT_FLAT),
                eyebrows=getattr(EyebrowType, data.get("eyebrows", "DEFAULT").upper(), EyebrowType.DEFAULT),
                eyes=getattr(EyeType, data.get("eyes", "DEFAULT").upper(), EyeType.DEFAULT),
                nose=getattr(NoseType, data.get("nose", "DEFAULT").upper(), NoseType.DEFAULT),
                mouth=getattr(MouthType, data.get("mouth", "DEFAULT").upper(), MouthType.DEFAULT),
                facial_hair=getattr(FacialHairType, data.get("facial_hair", "NONE").upper(), FacialHairType.NONE),
                skin_color=getattr(SkinColor, data.get("skin_color", "LIGHT").upper(), SkinColor.LIGHT),
                hair_color=data.get("hair_color", "#000000"),
                accessory=getattr(AccessoryType, data.get("accessory", "NONE").upper(), AccessoryType.NONE),
                clothing=getattr(ClothingType, data.get("clothing", "HOODIE").upper(), ClothingType.HOODIE),
                clothing_color=data.get("clothing_color", "#0000FF"),
            )
            return JsonResponse({"success": True, "avatar_svg": avatar.render()})
        except Exception:
            logger.exception("Error in preview_avatar")
            return JsonResponse({"success": False, "error": "An internal error occurred"}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)
