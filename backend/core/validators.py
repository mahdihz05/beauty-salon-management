from django.conf import settings
from django.core.exceptions import ValidationError


def validate_image_size(file) -> None:
    max_bytes = int(getattr(settings, "MAX_IMAGE_UPLOAD_BYTES", 5 * 1024 * 1024))
    if file.size > max_bytes:
        raise ValidationError("حجم تصویر نباید بیشتر از ۵ مگابایت باشد.")
