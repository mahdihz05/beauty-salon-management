from django.conf import settings
from django.db import models

from core.validators import validate_image_size


class City(models.Model):
    name = models.CharField("نام شهر", max_length=100, unique=True)
    slug = models.SlugField("شناسه URL", max_length=120, unique=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"

    def __str__(self) -> str:
        return self.name


class District(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField("نام منطقه", max_length=100)
    slug = models.SlugField("شناسه URL", max_length=120)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        ordering = ("city__name", "name")
        constraints = [
            models.UniqueConstraint(fields=("city", "slug"), name="unique_district_slug_per_city")
        ]
        verbose_name = "منطقه"
        verbose_name_plural = "مناطق"

    def __str__(self) -> str:
        return f"{self.city}، {self.name}"


class Salon(models.Model):
    class Type(models.TextChoices):
        WOMEN = "women", "زنانه"
        MEN = "men", "مردانه"
        UNISEX = "unisex", "مشترک"

    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        PENDING = "pending", "در انتظار بررسی"
        APPROVED = "approved", "تأییدشده"
        REJECTED = "rejected", "ردشده"
        SUSPENDED = "suspended", "تعلیق‌شده"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_salons"
    )
    name = models.CharField("نام سالن", max_length=180)
    slug = models.SlugField("شناسه URL", max_length=200, unique=True)
    type = models.CharField("نوع سالن", max_length=12, choices=Type.choices)
    description = models.TextField("معرفی", blank=True)
    status = models.CharField(
        "وضعیت", max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    rejection_reason = models.TextField("علت رد", blank=True)
    rating_average = models.DecimalField(
        "میانگین امتیاز", max_digits=3, decimal_places=2, default=0
    )
    review_count = models.PositiveIntegerField("تعداد نظر", default=0)
    is_featured = models.BooleanField("پیشنهاد ویژه", default=False, db_index=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "سالن"
        verbose_name_plural = "سالن‌ها"

    def __str__(self) -> str:
        return self.name


class Branch(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField("نام شعبه", max_length=120, default="شعبه مرکزی")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="branches")
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, related_name="branches", null=True, blank=True
    )
    address = models.TextField("نشانی")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    phone = models.CharField("تلفن", max_length=16)
    working_hours = models.JSONField("ساعات کاری", default=dict, blank=True)
    amenities = models.JSONField("امکانات", default=list, blank=True)
    slot_interval_minutes = models.PositiveSmallIntegerField("گام تقویم", default=15)
    preparation_buffer_minutes = models.PositiveSmallIntegerField("زمان آماده‌سازی", default=10)
    deposit_percent = models.PositiveSmallIntegerField("درصد بیعانه", default=20)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        ordering = ("salon__name", "name")
        constraints = [
            models.UniqueConstraint(fields=("salon", "name"), name="unique_branch_name_per_salon"),
            models.CheckConstraint(
                condition=models.Q(deposit_percent__lte=100), name="branch_deposit_percent_lte_100"
            ),
        ]
        verbose_name = "شعبه"
        verbose_name_plural = "شعبه‌ها"

    def __str__(self) -> str:
        return f"{self.salon} - {self.name}"


class BranchClosure(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="closures")
    starts_at = models.DateTimeField("شروع تعطیلی")
    ends_at = models.DateTimeField("پایان تعطیلی")
    reason = models.CharField("علت", max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-starts_at",)
        indexes = [models.Index(fields=("branch", "starts_at", "ends_at"))]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="branch_closure_ends_after_start",
            )
        ]
        verbose_name = "تعطیلی شعبه"
        verbose_name_plural = "تعطیلی‌های شعبه"

    def __str__(self) -> str:
        return f"{self.branch}: {self.starts_at:%Y-%m-%d %H:%M}"


class SalonImage(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="salons/gallery/%Y/%m/", validators=(validate_image_size,))
    alt_text = models.CharField("متن جایگزین", max_length=180, blank=True)
    is_cover = models.BooleanField("تصویر اصلی", default=False)
    sort_order = models.PositiveSmallIntegerField("ترتیب", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "تصویر سالن"
        verbose_name_plural = "تصاویر سالن"

    def __str__(self) -> str:
        return self.alt_text or f"تصویر {self.salon}"


class ServiceCategory(models.Model):
    name = models.CharField("نام دسته‌بندی", max_length=120)
    slug = models.SlugField("شناسه URL", max_length=140, unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="children", null=True, blank=True
    )
    icon = models.CharField("نام آیکن", max_length=60, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "دسته‌بندی خدمت"
        verbose_name_plural = "دسته‌بندی خدمات"

    def __str__(self) -> str:
        return self.name


class Service(models.Model):
    salon = models.ForeignKey(
        Salon,
        on_delete=models.CASCADE,
        related_name="services",
        null=True,
        blank=True,
        help_text="خالی بودن سالن یعنی خدمت مرکزی سامانه است.",
    )
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    name = models.CharField("نام خدمت", max_length=150)
    description = models.TextField("توضیحات", blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category__sort_order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("salon", "category", "name"), name="unique_service_per_salon_category"
            )
        ]
        verbose_name = "خدمت"
        verbose_name_plural = "خدمات"

    def __str__(self) -> str:
        return self.name


class BranchService(models.Model):
    class PriceType(models.TextChoices):
        FIXED = "fixed", "ثابت"
        STARTING_FROM = "starting_from", "شروع از"

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="branch_services")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="branch_services")
    price = models.PositiveBigIntegerField("قیمت (تومان)")
    price_type = models.CharField(
        "نوع قیمت", max_length=16, choices=PriceType.choices, default=PriceType.FIXED
    )
    duration_minutes = models.PositiveSmallIntegerField("مدت (دقیقه)")
    preparation_buffer_minutes = models.PositiveSmallIntegerField(
        "زمان آماده‌سازی اختصاصی", null=True, blank=True
    )
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("service__category__sort_order", "service__name")
        constraints = [
            models.UniqueConstraint(fields=("branch", "service"), name="unique_service_per_branch"),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gt=0),
                name="branch_service_duration_positive",
            ),
        ]
        verbose_name = "خدمت شعبه"
        verbose_name_plural = "خدمات شعبه"

    def __str__(self) -> str:
        return f"{self.branch}: {self.service}"


class Staff(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="staff")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="staff_profile",
        null=True,
        blank=True,
    )
    first_name = models.CharField("نام", max_length=80)
    last_name = models.CharField("نام خانوادگی", max_length=100)
    photo = models.ImageField(
        "تصویر", upload_to="staff/photos/", blank=True, validators=(validate_image_size,)
    )
    bio = models.TextField("معرفی", blank=True)
    experience_years = models.PositiveSmallIntegerField("سال تجربه", default=0)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("first_name", "last_name")
        verbose_name = "آرایشگر"
        verbose_name_plural = "پرسنل"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return self.full_name


class StaffShift(models.Model):
    class Day(models.IntegerChoices):
        SATURDAY = 0, "شنبه"
        SUNDAY = 1, "یکشنبه"
        MONDAY = 2, "دوشنبه"
        TUESDAY = 3, "سه‌شنبه"
        WEDNESDAY = 4, "چهارشنبه"
        THURSDAY = 5, "پنجشنبه"
        FRIDAY = 6, "جمعه"

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="shifts")
    day_of_week = models.PositiveSmallIntegerField("روز هفته", choices=Day.choices)
    start_time = models.TimeField("شروع", null=True, blank=True)
    end_time = models.TimeField("پایان", null=True, blank=True)
    is_off = models.BooleanField("تعطیل", default=False)

    class Meta:
        ordering = ("day_of_week", "start_time")
        constraints = [
            models.UniqueConstraint(fields=("staff", "day_of_week"), name="unique_staff_day_shift")
        ]
        verbose_name = "شیفت آرایشگر"
        verbose_name_plural = "شیفت‌های آرایشگر"

    def __str__(self) -> str:
        return f"{self.staff} - {self.get_day_of_week_display()}"


class StaffTimeOff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="time_offs")
    starts_at = models.DateTimeField("شروع مرخصی")
    ends_at = models.DateTimeField("پایان مرخصی")
    reason = models.CharField("علت", max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-starts_at",)
        verbose_name = "مرخصی آرایشگر"
        verbose_name_plural = "مرخصی‌های آرایشگر"

    def __str__(self) -> str:
        return f"{self.staff}: {self.starts_at:%Y-%m-%d}"


class StaffService(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="staff_services")
    branch_service = models.ForeignKey(
        BranchService, on_delete=models.CASCADE, related_name="staff_services"
    )
    price_override = models.PositiveBigIntegerField("قیمت اختصاصی", null=True, blank=True)
    duration_override_minutes = models.PositiveSmallIntegerField(
        "مدت اختصاصی", null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("staff", "branch_service"), name="unique_service_per_staff"
            )
        ]
        verbose_name = "مهارت آرایشگر"
        verbose_name_plural = "مهارت‌های آرایشگر"

    def __str__(self) -> str:
        return f"{self.staff}: {self.branch_service.service}"
