import re

from rest_framework.exceptions import ValidationError


def normalize_iranian_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
    if digits.startswith("0098"):
        digits = "0" + digits[4:]
    elif digits.startswith("98"):
        digits = "0" + digits[2:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    if not re.fullmatch(r"09\d{9}", digits):
        raise ValidationError("شماره موبایل باید یک شماره معتبر ایرانی باشد.")
    return digits
