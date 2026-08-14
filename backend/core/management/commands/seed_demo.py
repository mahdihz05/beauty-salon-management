from datetime import time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import (
    BranchMembership,
    CustomerProfile,
    FavoriteSalon,
    OTPChallenge,
    User,
)
from bookings.models import Booking, BookingItem, DiscountCode, DiscountRedemption
from core.models import AuditLog, SupportTicket
from notifications.models import Notification
from payments.models import Payment, Settlement, Wallet, WalletTransaction
from reviews.models import Review, ReviewImage
from reviews.services import refresh_salon_rating
from salons.models import (
    Branch,
    BranchService,
    City,
    District,
    Salon,
    SalonImage,
    Service,
    ServiceCategory,
    Staff,
    StaffService,
    StaffShift,
    StaffTimeOff,
)


class Command(BaseCommand):
    help = "Create an idempotent employer-ready demo dataset and role accounts."

    def handle(self, *args, **options):
        password = "Demo@12345"
        users = {}
        user_specs = {
            "admin": ("09120000001", "مدیر سامانه", User.Role.ADMIN),
            "owner": ("09120000002", "مالک سالن دمو", User.Role.SALON_OWNER),
            "customer": ("09120000003", "مشتری دمو", User.Role.CUSTOMER),
            "manager": ("09120000006", "مدیر شعبه دمو", User.Role.BRANCH_MANAGER),
            "receptionist": ("09120000007", "پذیرش شعبه دمو", User.Role.RECEPTIONIST),
            "staff": ("09120000008", "آرایشگر دمو", User.Role.STAFF),
        }
        for key, (phone, name, role) in user_specs.items():
            user, _ = User.objects.get_or_create(phone=phone, defaults={"name": name, "role": role})
            user.name = name
            user.role = role
            user.set_password(password)
            if key == "admin":
                user.is_staff = True
                user.is_superuser = True
            user.save()
            users[key] = user

        # Demo seeding also resets the mock-login window so repeated local QA
        # runs remain deterministic without weakening production throttling.
        OTPChallenge.objects.filter(
            phone__in=[phone for phone, _name, _role in user_specs.values()]
        ).delete()

        city, _ = City.objects.get_or_create(name="تهران", defaults={"slug": "tehran"})
        district, _ = District.objects.get_or_create(
            city=city, slug="saadat-abad", defaults={"name": "سعادت‌آباد"}
        )
        salon, _ = Salon.objects.get_or_create(
            slug="demo-rose-gold",
            defaults={
                "owner": users["owner"],
                "name": "سالن رزگلد",
                "type": Salon.Type.WOMEN,
                "description": "سالن تخصصی زیبایی با تیم حرفه‌ای و امکان رزرو آنلاین.",
                "status": Salon.Status.APPROVED,
                "is_featured": True,
            },
        )
        branch, _ = Branch.objects.get_or_create(
            salon=salon,
            name="شعبه سعادت‌آباد",
            defaults={
                "city": city,
                "district": district,
                "address": "تهران، سعادت‌آباد، میدان کاج",
                "phone": "02122334455",
                "amenities": ["پارکینگ", "پذیرایی", "وای‌فای"],
                "deposit_percent": 20,
            },
        )
        branch.working_hours = {
            str(day): {"start": "09:00", "end": "20:00", "is_open": day != 6} for day in range(7)
        }
        branch.latitude = "35.7851000"
        branch.longitude = "51.3755000"
        branch.save(update_fields=("working_hours", "latitude", "longitude", "updated_at"))
        category, _ = ServiceCategory.objects.get_or_create(
            slug="showcase-category-1", defaults={"name": "مو و کوتاهی"}
        )
        service_specs = (("کوتاهی و براشینگ", 450_000, 60), ("رنگ و لایت", 1_200_000, 120))
        branch_services = []
        for service_name, price, duration in service_specs:
            service, _ = Service.objects.get_or_create(
                salon=salon, category=category, name=service_name
            )
            branch_service, _ = BranchService.objects.get_or_create(
                branch=branch,
                service=service,
                defaults={"price": price, "duration_minutes": duration},
            )
            branch_services.append(branch_service)
        staff, _ = Staff.objects.get_or_create(
            branch=branch,
            first_name="سارا",
            last_name="احمدی",
            defaults={"experience_years": 8, "bio": "متخصص رنگ و کوتاهی"},
        )
        if staff.user_id != users["staff"].id:
            staff.user = users["staff"]
            staff.save(update_fields=("user", "updated_at"))
        BranchMembership.objects.update_or_create(
            user=users["manager"],
            branch=branch,
            defaults={"role": BranchMembership.Role.MANAGER, "is_active": True},
        )
        BranchMembership.objects.update_or_create(
            user=users["receptionist"],
            branch=branch,
            defaults={"role": BranchMembership.Role.RECEPTIONIST, "is_active": True},
        )
        BranchMembership.objects.update_or_create(
            user=users["staff"],
            branch=branch,
            defaults={"role": BranchMembership.Role.STAFF, "is_active": True},
        )
        for branch_service in branch_services:
            StaffService.objects.get_or_create(staff=staff, branch_service=branch_service)
        for day in range(7):
            StaffShift.objects.get_or_create(
                staff=staff,
                day_of_week=day,
                defaults={"start_time": time(9), "end_time": time(20)},
            )

        now = timezone.now()
        StaffTimeOff.objects.get_or_create(
            staff=staff,
            starts_at=(now - timedelta(days=20)).replace(
                hour=12, minute=0, second=0, microsecond=0
            ),
            defaults={
                "ends_at": (now - timedelta(days=20)).replace(
                    hour=16, minute=0, second=0, microsecond=0
                ),
                "reason": "مرخصی نمونه ثبت‌شده",
            },
        )
        booking_specs = (
            (now - timedelta(days=5), Booking.Status.COMPLETED, branch_services[0]),
            (now - timedelta(days=2), Booking.Status.COMPLETED, branch_services[1]),
            (now + timedelta(days=2), Booking.Status.CONFIRMED, branch_services[0]),
        )
        completed = None
        confirmed = None
        for start, booking_status, branch_service in booking_specs:
            start = start.replace(hour=10, minute=0, second=0, microsecond=0)
            booking, created = Booking.objects.get_or_create(
                customer=users["customer"],
                branch=branch,
                staff=staff,
                start_at=start,
                defaults={
                    "status": booking_status,
                    "source": (
                        Booking.Source.WALK_IN if start.day % 2 == 0 else Booking.Source.ONLINE
                    ),
                    "end_at": start + timedelta(minutes=branch_service.duration_minutes),
                    "total_price": branch_service.price,
                    "deposit_amount": branch_service.price // 5,
                    "notes": "demo-seed",
                },
            )
            if created:
                BookingItem.objects.create(
                    booking=booking,
                    branch_service=branch_service,
                    staff=staff,
                    price=branch_service.price,
                    duration_minutes=branch_service.duration_minutes,
                )
            if booking_status in (Booking.Status.COMPLETED, Booking.Status.CONFIRMED):
                Payment.objects.get_or_create(
                    booking=booking,
                    type=Payment.Type.FULL,
                    defaults={
                        "amount": booking.total_price,
                        "status": Payment.Status.PAID,
                        "paid_at": start - timedelta(days=1),
                        "gateway_ref": f"demo-{booking.pk}",
                    },
                )
            if booking_status == Booking.Status.COMPLETED:
                completed = booking
            elif booking_status == Booking.Status.CONFIRMED:
                confirmed = booking

        if completed:
            review, _ = Review.objects.get_or_create(
                booking=completed,
                defaults={
                    "customer": users["customer"],
                    "salon": salon,
                    "staff": staff,
                    "overall_rating": 5,
                    "quality_rating": 5,
                    "cleanliness_rating": 5,
                    "behavior_rating": 5,
                    "value_rating": 5,
                    "comment": "تجربه بسیار خوبی بود و حتماً دوباره رزرو می‌کنم.",
                    "status": Review.Status.PUBLISHED,
                },
            )
            if review.staff_id != staff.id:
                review.staff = staff
                review.value_rating = 5
                review.save(update_fields=("staff", "value_rating", "updated_at"))
            refresh_salon_rating(salon)
        discount, _ = DiscountCode.objects.get_or_create(
            code="DEMO20",
            defaults={
                "salon": salon,
                "type": DiscountCode.Type.PERCENT,
                "value": 20,
                "maximum_discount": 200_000,
                "starts_at": now - timedelta(days=1),
                "ends_at": now + timedelta(days=365),
            },
        )

        if completed:
            DiscountRedemption.objects.get_or_create(
                booking=completed,
                defaults={
                    "discount": discount,
                    "customer": users["customer"],
                    "amount": 50_000,
                },
            )
        if confirmed:
            Notification.objects.get_or_create(
                recipient=users["customer"],
                booking=confirmed,
                event=Notification.Event.BOOKING_CONFIRMED,
                channel=Notification.Channel.SMS,
                defaults={
                    "status": Notification.Status.SENT,
                    "message": "نوبت شما در سالن رزگلد با موفقیت ثبت شد.",
                    "provider_ref": "demo-sms-confirmed",
                    "sent_at": now,
                },
            )

        FavoriteSalon.objects.get_or_create(user=users["customer"], salon=salon)
        customer_profile, _ = CustomerProfile.objects.get_or_create(user=users["customer"])
        customer_profile.email = "customer@example.com"
        customer_profile.gender = customer_profile.Gender.WOMAN
        customer_profile.save(update_fields=("email", "gender", "updated_at"))

        customer_wallet, _ = Wallet.objects.get_or_create(
            user=users["customer"], defaults={"balance": 180_000}
        )
        WalletTransaction.objects.get_or_create(
            wallet=customer_wallet,
            related_booking=None,
            type=WalletTransaction.Type.ADJUSTMENT,
            description="اعتبار هدیه حساب دمو",
            defaults={"amount": 180_000},
        )
        owner_wallet, _ = Wallet.objects.get_or_create(
            user=users["owner"], defaults={"balance": 2_400_000}
        )
        WalletTransaction.objects.get_or_create(
            wallet=owner_wallet,
            related_booking=completed,
            type=WalletTransaction.Type.SALON_EARNING,
            defaults={
                "amount": 1_080_000,
                "salon": salon,
                "description": "درآمد نمونه رزرو تکمیل‌شده",
            },
        )
        Settlement.objects.get_or_create(
            wallet=owner_wallet,
            salon=salon,
            amount=750_000,
            bank_account="IR820540102680020817909002",
            defaults={"status": Settlement.Status.REQUESTED},
        )

        SupportTicket.objects.get_or_create(
            customer=users["customer"],
            subject="پرسش درباره تغییر زمان نوبت",
            defaults={
                "assigned_to": users["admin"],
                "message": "برای تغییر زمان نوبت آینده به راهنمایی نیاز دارم.",
                "response": "درخواست شما دریافت شد و در حال بررسی است.",
                "status": SupportTicket.Status.IN_PROGRESS,
            },
        )
        AuditLog.objects.get_or_create(
            actor=users["admin"],
            action="demo.data_seeded",
            target_type="salons.salon",
            target_id=str(salon.pk),
            defaults={"metadata": {"source": "seed_demo"}},
        )

        extra_salon_specs = (
            (
                "demo-gentlemen-club",
                "پیرایش مردانه جنتلمن",
                Salon.Type.MEN,
                "شعبه ونک",
                "ونک، خیابان ملاصدرا",
                "02188776655",
                "اصلاح و استایل مو",
                380_000,
                "salon-02.jpg",
            ),
            (
                "demo-aria-beauty",
                "مرکز زیبایی آریا",
                Salon.Type.UNISEX,
                "شعبه پاسداران",
                "پاسداران، بوستان پنجم",
                "02122558877",
                "پاکسازی و مراقبت پوست",
                690_000,
                "salon-03.jpg",
            ),
        )
        for index, (
            slug,
            name,
            salon_type,
            branch_name,
            address,
            phone,
            service_name,
            price,
            image_name,
        ) in enumerate(extra_salon_specs, start=2):
            extra_salon, _ = Salon.objects.get_or_create(
                slug=slug,
                defaults={
                    "owner": users["owner"],
                    "name": name,
                    "type": salon_type,
                    "description": "مجموعه حرفه‌ای با رزرو آنلاین و خدمات تخصصی.",
                    "status": Salon.Status.APPROVED,
                    "is_featured": True,
                    "rating_average": "4.50",
                    "review_count": 12 + index,
                },
            )
            extra_branch, _ = Branch.objects.get_or_create(
                salon=extra_salon,
                name=branch_name,
                defaults={
                    "city": city,
                    "district": district,
                    "address": address,
                    "phone": phone,
                    "working_hours": branch.working_hours,
                    "amenities": ["رزرو آنلاین", "پذیرایی"],
                },
            )
            extra_service, _ = Service.objects.get_or_create(
                salon=extra_salon,
                category=category,
                name=service_name,
                defaults={"description": "خدمت تخصصی قابل رزرو آنلاین"},
            )
            BranchService.objects.get_or_create(
                branch=extra_branch,
                service=extra_service,
                defaults={"price": price, "duration_minutes": 60},
            )
            self._attach_demo_image(extra_salon, image_name, f"نمای {name}")

        self._attach_demo_image(salon, "salon-01.jpg", "نمای سالن رزگلد")
        if completed and not ReviewImage.objects.filter(review=completed.review).exists():
            image_path = self._demo_image_path("salon-04.jpg")
            if image_path.exists():
                with image_path.open("rb") as image_file:
                    review_image = ReviewImage(review=completed.review)
                    review_image.image.save("demo-review.jpg", File(image_file), save=True)

        self.stdout.write(self.style.SUCCESS("Demo data is ready. Password: Demo@12345"))

    @staticmethod
    def _demo_image_path(filename: str) -> Path:
        return Path(settings.BASE_DIR).parent / "frontend" / "public" / "images" / filename

    def _attach_demo_image(self, salon: Salon, filename: str, alt_text: str) -> None:
        if salon.images.exists():
            return
        image_path = self._demo_image_path(filename)
        if not image_path.exists():
            return
        with image_path.open("rb") as image_file:
            salon_image = SalonImage(salon=salon, alt_text=alt_text, is_cover=True)
            salon_image.image.save(f"demo-{salon.slug}.jpg", File(image_file), save=True)
