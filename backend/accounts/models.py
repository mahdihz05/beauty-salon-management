from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from core.validators import validate_image_size


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone: str, password: str | None = None, **extra_fields):
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "مشتری"
        SALON_OWNER = "salon_owner", "مالک سالن"
        BRANCH_MANAGER = "branch_manager", "مدیر شعبه"
        RECEPTIONIST = "receptionist", "پذیرش"
        STAFF = "staff", "آرایشگر"
        ADMIN = "admin", "مدیر کل"
        SUPPORT = "support", "پشتیبانی"
        FINANCE = "finance", "مالی"

    username = None
    phone = models.CharField("شماره موبایل", max_length=11, unique=True, db_index=True)
    name = models.CharField("نام و نام خانوادگی", max_length=150, blank=True)
    role = models.CharField(
        "نقش", max_length=24, choices=Role.choices, default=Role.CUSTOMER, db_index=True
    )
    phone_verified_at = models.DateTimeField("زمان تأیید موبایل", null=True, blank=True)
    created_at = models.DateTimeField("زمان عضویت", auto_now_add=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []
    objects = UserManager()

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self) -> str:
        return self.name or self.phone


class CustomerProfile(models.Model):
    class Gender(models.TextChoices):
        WOMAN = "woman", "زن"
        MAN = "man", "مرد"
        NOT_SPECIFIED = "not_specified", "ترجیح می‌دهم نگویم"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    email = models.EmailField("ایمیل", blank=True)
    birth_date = models.DateField("تاریخ تولد", null=True, blank=True)
    gender = models.CharField(
        "جنسیت", max_length=16, choices=Gender.choices, default=Gender.NOT_SPECIFIED
    )
    avatar = models.ImageField(
        "تصویر", upload_to="customers/avatars/", blank=True, validators=(validate_image_size,)
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پروفایل مشتری"
        verbose_name_plural = "پروفایل مشتریان"

    def __str__(self) -> str:
        return str(self.user)


class OTPChallenge(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "login", "ورود"

    phone = models.CharField("شماره موبایل", max_length=11, db_index=True)
    purpose = models.CharField(max_length=16, choices=Purpose.choices, default=Purpose.LOGIN)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    consumed_at = models.DateTimeField(null=True, blank=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("phone", "purpose", "-created_at"))]
        verbose_name = "کد یک‌بارمصرف"
        verbose_name_plural = "کدهای یک‌بارمصرف"

    def __str__(self) -> str:
        return f"{self.phone} - {self.created_at:%Y-%m-%d %H:%M}"


class BranchMembership(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "مدیر شعبه"
        RECEPTIONIST = "receptionist", "پذیرش"
        STAFF = "staff", "آرایشگر"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="branch_memberships")
    branch = models.ForeignKey(
        "salons.Branch", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "branch"), name="unique_user_branch_membership")
        ]
        verbose_name = "دسترسی شعبه"
        verbose_name_plural = "دسترسی‌های شعبه"

    def __str__(self) -> str:
        return f"{self.user} - {self.branch}"


class FavoriteSalon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_salons")
    salon = models.ForeignKey("salons.Salon", on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "salon"), name="unique_favorite_salon")
        ]
        verbose_name = "سالن مورد علاقه"
        verbose_name_plural = "سالن‌های مورد علاقه"

    def __str__(self) -> str:
        return f"{self.user} - {self.salon}"
