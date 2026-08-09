import random
from datetime import time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from accounts.models import BranchMembership, CustomerProfile, FavoriteSalon, User
from bookings.models import Booking, BookingItem, DiscountCode, DiscountRedemption
from core.models import AuditLog, SupportTicket
from notifications.models import Notification
from payments.models import Payment, Settlement, Wallet, WalletTransaction
from reviews.models import Review
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

FIRST_NAMES = (
    "سارا",
    "نگار",
    "مریم",
    "نازنین",
    "الهام",
    "مهسا",
    "آرزو",
    "ریحانه",
    "علی",
    "امیر",
    "رضا",
    "سامان",
    "کیان",
    "پارسا",
)
LAST_NAMES = (
    "احمدی",
    "محمدی",
    "کریمی",
    "رضایی",
    "مرادی",
    "حسینی",
    "قاسمی",
    "اکبری",
    "صادقی",
    "کاظمی",
)
SALON_WORDS = (
    "آریانا",
    "رویال",
    "ماه‌چهره",
    "دلسا",
    "آفرودیت",
    "مانلی",
    "چهره‌نو",
    "ژینو",
    "هلیا",
    "رونیکا",
    "آرتین",
    "پادرا",
)
CITY_DATA = (
    ("تهران", "tehran", ("سعادت‌آباد", "پاسداران", "ونک", "نیاوران")),
    ("کرج", "karaj", ("عظیمیه", "گوهردشت", "مهرشهر")),
    ("مشهد", "mashhad", ("سجاد", "احمدآباد", "قاسم‌آباد")),
    ("اصفهان", "isfahan", ("مرداویج", "جلفا", "خانه اصفهان")),
    ("شیراز", "shiraz", ("معالی‌آباد", "فرهنگ‌شهر", "قدوسی")),
    ("تبریز", "tabriz", ("ولیعصر", "ائل‌گلی", "آبرسان")),
    ("رشت", "rasht", ("گلسار", "منظریه", "معلم")),
    ("اهواز", "ahvaz", ("کیانپارس", "زیتون", "گلستان")),
)
SERVICE_CATALOG = {
    "مو و کوتاهی": ("کوتاهی حرفه‌ای", "براشینگ", "کراتین", "اکستنشن مو", "شینیون"),
    "رنگ و لایت": ("رنگ کامل", "بالیاژ", "هایلایت", "مش", "ریشه‌گیری"),
    "ناخن": ("مانیکور", "پدیکور", "کاشت ناخن", "ترمیم کاشت", "ژلیش"),
    "پوست و زیبایی": ("پاکسازی پوست", "فیشیال", "آبرسانی", "میکرودرم", "ماساژ صورت"),
    "آرایش": ("میکاپ روز", "میکاپ عروس", "گریم", "آرایش چشم", "کانتورینگ"),
    "ابرو و مژه": ("اصلاح ابرو", "لیفت ابرو", "کاشت مژه", "لیفت مژه", "رنگ ابرو"),
    "پیرایش مردانه": ("اصلاح کلاسیک", "فید", "اصلاح ریش", "پاکسازی مردانه", "استایل داماد"),
    "مراقبت مو": ("ویتامینه مو", "پلکس‌تراپی", "بوتاکس مو", "اسکالپ", "پروتئین‌تراپی"),
    "اپیلاسیون": ("اپیلاسیون کامل", "وکس صورت", "وکس دست", "وکس پا", "اصلاح بدن"),
    "ماساژ": ("ماساژ ریلکسی", "ماساژ سوئدی", "ماساژ سر و گردن", "ماساژ پا", "سنگ داغ"),
    "خدمات کودک": ("کوتاهی کودک", "بافت کودک", "استایل جشن", "ناخن کودک", "گریم کودک"),
    "بافت مو": ("بافت ساده", "بافت آفریقایی", "بافت فرانسوی", "بافت هلندی", "بافت مجلسی"),
}


class Command(BaseCommand):
    help = "Create a large, deterministic and relational showcase dataset."

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=600)
        parser.add_argument("--salons", type=int, default=48)
        parser.add_argument("--bookings-per-branch", type=int, default=36)

    @transaction.atomic
    def handle(self, *args, **options):
        customer_count = max(100, min(options["customers"], 2_000))
        salon_count = max(12, min(options["salons"], 100))
        bookings_per_branch = max(20, min(options["bookings_per_branch"], 80))
        self._merge_legacy_demo_category()
        marker = AuditLog.objects.filter(action="showcase.seed_completed").first()
        if marker:
            self._ensure_product_salon_coverage()
            self._ensure_service_coverage()
            self.stdout.write(
                self.style.WARNING(
                    "Showcase data already exists; no duplicate records were created."
                )
            )
            self._print_summary()
            return

        rng = random.Random(14050516)
        now = timezone.now()
        cities, districts = self._create_locations()
        categories, services = self._create_catalog()
        self._merge_legacy_demo_category()
        users = self._create_users(customer_count, salon_count, rng)
        customers = users["customers"]
        salons, branches, staff_by_branch = self._create_salons(
            salon_count=salon_count,
            owners=users["owners"],
            managers=users["managers"],
            receptionists=users["receptionists"],
            staff_users=users["staff"],
            cities=cities,
            districts=districts,
            categories=categories,
            services=services,
            rng=rng,
            now=now,
        )
        wallets = self._create_wallets(customers, users["owners"], rng)
        discounts = self._create_discounts(salons, now)
        self._create_bookings(
            branches=branches,
            staff_by_branch=staff_by_branch,
            customers=customers,
            wallets=wallets,
            discounts=discounts,
            bookings_per_branch=bookings_per_branch,
            now=now,
            rng=rng,
        )
        self._ensure_product_salon_coverage()
        self._ensure_service_coverage()
        self._create_social_and_support(customers, salons, users["admin"], rng)
        self._create_settlements(users["owners"], wallets, rng)
        AuditLog.objects.create(
            actor=users["admin"],
            action="showcase.seed_completed",
            target_type="database",
            target_id="showcase-v1",
            metadata={
                "customers": customer_count,
                "salons": salon_count,
                "bookings_per_branch": bookings_per_branch,
            },
        )
        self.stdout.write(self.style.SUCCESS("Large showcase dataset is ready."))
        self._print_summary()

    def _create_locations(self):
        cities = []
        districts = []
        for city_name, city_slug, district_names in CITY_DATA:
            city, _ = City.objects.get_or_create(
                slug=city_slug, defaults={"name": city_name, "is_active": True}
            )
            cities.append(city)
            for index, district_name in enumerate(district_names, start=1):
                district, _ = District.objects.get_or_create(
                    city=city,
                    slug=f"{city_slug}-district-{index}",
                    defaults={"name": district_name, "is_active": True},
                )
                districts.append(district)
        return cities, districts

    def _create_catalog(self):
        categories = []
        services = []
        for category_index, (category_name, service_names) in enumerate(
            SERVICE_CATALOG.items(), start=1
        ):
            category, _ = ServiceCategory.objects.get_or_create(
                slug=f"showcase-category-{category_index}",
                defaults={
                    "name": category_name,
                    "icon": "sparkles",
                    "sort_order": category_index,
                },
            )
            categories.append(category)
            for service_name in service_names:
                service, _ = Service.objects.get_or_create(
                    salon=None,
                    category=category,
                    name=service_name,
                    defaults={"description": f"خدمت تخصصی {service_name} با رزرو آنلاین"},
                )
                services.append(service)
        return categories, services

    @staticmethod
    def _merge_legacy_demo_category():
        legacy = ServiceCategory.objects.filter(slug="demo-hair").first()
        target = ServiceCategory.objects.filter(slug="showcase-category-1").first()
        if not legacy or not target:
            return
        legacy.services.update(category=target)
        legacy.delete()

    def _create_users(self, customer_count, salon_count, rng):
        specs = []
        for index in range(customer_count):
            specs.append(
                (
                    f"0991{index:07d}",
                    f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                    User.Role.CUSTOMER,
                )
            )
        role_specs = (
            ("owners", "0992", User.Role.SALON_OWNER, salon_count),
            ("managers", "0993", User.Role.BRANCH_MANAGER, salon_count * 2),
            ("receptionists", "0994", User.Role.RECEPTIONIST, salon_count * 2),
            ("staff", "0995", User.Role.STAFF, salon_count * 6),
        )
        role_phones = {}
        for key, prefix, role, count in role_specs:
            phones = []
            for index in range(count):
                phone = f"{prefix}{index:07d}"
                phones.append(phone)
                specs.append(
                    (
                        phone,
                        f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                        role,
                    )
                )
            role_phones[key] = phones
        User.objects.bulk_create(
            [User(phone=phone, name=name, role=role, password="!") for phone, name, role in specs],
            ignore_conflicts=True,
            batch_size=500,
        )
        user_map = User.objects.in_bulk(
            [phone for phone, _name, _role in specs], field_name="phone"
        )
        customer_phones = [f"0991{index:07d}" for index in range(customer_count)]
        customers = [user_map[phone] for phone in customer_phones]
        existing_profiles = set(
            CustomerProfile.objects.filter(user__in=customers).values_list("user_id", flat=True)
        )
        CustomerProfile.objects.bulk_create(
            [
                CustomerProfile(
                    user=customer,
                    email=f"customer{index + 1}@example.com",
                    gender=(
                        CustomerProfile.Gender.WOMAN
                        if index % 3
                        else CustomerProfile.Gender.MAN
                    ),
                )
                for index, customer in enumerate(customers)
                if customer.id not in existing_profiles
            ],
            batch_size=500,
        )
        admin = User.objects.filter(role=User.Role.ADMIN).first()
        return {
            "customers": customers,
            "owners": [user_map[phone] for phone in role_phones["owners"]],
            "managers": [user_map[phone] for phone in role_phones["managers"]],
            "receptionists": [user_map[phone] for phone in role_phones["receptionists"]],
            "staff": [user_map[phone] for phone in role_phones["staff"]],
            "admin": admin,
        }

    def _create_salons(
        self,
        *,
        salon_count,
        owners,
        managers,
        receptionists,
        staff_users,
        cities,
        districts,
        categories,
        services,
        rng,
        now,
    ):
        salons = []
        branches = []
        staff_by_branch = {}
        working_hours = {
            str(day): {"start": "09:00", "end": "21:00", "is_open": day != 6}
            for day in range(7)
        }
        for salon_index in range(salon_count):
            salon_type = (Salon.Type.WOMEN, Salon.Type.MEN, Salon.Type.UNISEX)[salon_index % 3]
            salon, _ = Salon.objects.get_or_create(
                slug=f"showcase-salon-{salon_index + 1}",
                defaults={
                    "owner": owners[salon_index],
                    "name": f"سالن {SALON_WORDS[salon_index % len(SALON_WORDS)]} {salon_index + 1}",
                    "type": salon_type,
                    "description": "مجموعه حرفه‌ای زیبایی با تیم مجرب، رزرو فوری و خدمات متنوع.",
                    "status": Salon.Status.APPROVED,
                    "rating_average": "4.40",
                    "review_count": 20,
                    "is_featured": salon_index % 5 == 0,
                },
            )
            salons.append(salon)
            self._attach_image(salon, salon_index)
            for branch_number in range(2):
                branch_index = salon_index * 2 + branch_number
                city = cities[branch_index % len(cities)]
                city_districts = [district for district in districts if district.city_id == city.id]
                district = city_districts[branch_index % len(city_districts)]
                branch, _ = Branch.objects.get_or_create(
                    salon=salon,
                    name=f"شعبه {district.name}",
                    defaults={
                        "city": city,
                        "district": district,
                        "address": (
                            f"{city.name}، {district.name}، خیابان نمونه، "
                            f"پلاک {branch_index + 10}"
                        ),
                        "phone": f"0218{branch_index:07d}",
                        "working_hours": working_hours,
                        "amenities": ["رزرو آنلاین", "پارکینگ", "پذیرایی", "وای‌فای"],
                        "latitude": f"35.{7000000 + branch_index:07d}",
                        "longitude": f"51.{3000000 + branch_index:07d}",
                        "deposit_percent": 20,
                    },
                )
                branches.append(branch)
                selected_services = self._services_for_salon(
                    services, salon_type, branch_index, count=8
                )
                branch_services = []
                for service_index, service in enumerate(selected_services):
                    branch_service, _ = BranchService.objects.get_or_create(
                        branch=branch,
                        service=service,
                        defaults={
                            "price": 250_000 + ((branch_index + service_index) % 12) * 95_000,
                            "duration_minutes": (45, 60, 75, 90, 120)[service_index % 5],
                            "price_type": (
                                BranchService.PriceType.STARTING_FROM
                                if service_index % 4 == 0
                                else BranchService.PriceType.FIXED
                            ),
                        },
                    )
                    branch_services.append(branch_service)
                branch_staff = []
                for staff_number in range(3):
                    staff_user = staff_users[branch_index * 3 + staff_number]
                    first_name, last_name = staff_user.name.split(" ", 1)
                    staff, _ = Staff.objects.get_or_create(
                        user=staff_user,
                        defaults={
                            "branch": branch,
                            "first_name": first_name,
                            "last_name": last_name,
                            "bio": "متخصص خدمات زیبایی و دارای سابقه حرفه‌ای.",
                            "experience_years": 2 + (staff_number + branch_index) % 12,
                        },
                    )
                    branch_staff.append(staff)
                    BranchMembership.objects.get_or_create(
                        user=staff_user,
                        branch=branch,
                        defaults={"role": BranchMembership.Role.STAFF},
                    )
                    for day in range(7):
                        StaffShift.objects.get_or_create(
                            staff=staff,
                            day_of_week=day,
                            defaults={
                                "start_time": time(9 + staff_number),
                                "end_time": time(20),
                                "is_off": day == 6,
                            },
                        )
                    for branch_service in branch_services[
                        staff_number : staff_number + 6
                    ]:
                        StaffService.objects.get_or_create(
                            staff=staff, branch_service=branch_service
                        )
                staff_by_branch[branch.id] = branch_staff
                BranchMembership.objects.get_or_create(
                    user=managers[branch_index],
                    branch=branch,
                    defaults={"role": BranchMembership.Role.MANAGER},
                )
                BranchMembership.objects.get_or_create(
                    user=receptionists[branch_index],
                    branch=branch,
                    defaults={"role": BranchMembership.Role.RECEPTIONIST},
                )
                if branch_index % 4 == 0:
                    StaffTimeOff.objects.get_or_create(
                        staff=branch_staff[0],
                        starts_at=now - timedelta(days=45 - branch_index % 10),
                        defaults={
                            "ends_at": now - timedelta(days=44 - branch_index % 10),
                            "reason": "مرخصی ثبت‌شده در داده نمایشی",
                        },
                    )
        return salons, branches, staff_by_branch

    @staticmethod
    def _services_for_salon(services, salon_type, offset, count):
        if salon_type == Salon.Type.MEN:
            men_categories = {"پیرایش مردانه", "پوست و زیبایی", "مراقبت مو", "ماساژ"}
            preferred = [
                service for service in services if service.category.name in men_categories
            ]
        elif salon_type == Salon.Type.WOMEN:
            preferred = [
                service for service in services if service.category.name != "پیرایش مردانه"
            ]
        else:
            preferred = list(services)
        return [preferred[(offset * 3 + index) % len(preferred)] for index in range(count)]

    def _attach_image(self, salon, index):
        if salon.images.exists():
            return
        image_path = (
            Path(settings.BASE_DIR).parent
            / "frontend"
            / "public"
            / "images"
            / f"salon-{index % 12 + 1:02d}.jpg"
        )
        if not image_path.exists():
            return
        with image_path.open("rb") as image_file:
            image = SalonImage(salon=salon, alt_text=f"نمای {salon.name}", is_cover=True)
            image.image.save(f"showcase-{salon.slug}.jpg", File(image_file), save=True)

    @staticmethod
    def _create_wallets(customers, owners, rng):
        all_users = customers + owners
        Wallet.objects.bulk_create(
            [Wallet(user=user, balance=rng.randrange(0, 2_000_001, 50_000)) for user in all_users],
            ignore_conflicts=True,
            batch_size=500,
        )
        return {
            wallet.user_id: wallet
            for wallet in Wallet.objects.filter(user__in=all_users).select_related("user")
        }

    @staticmethod
    def _create_discounts(salons, now):
        discounts = {}
        for index, salon in enumerate(salons):
            discount, _ = DiscountCode.objects.get_or_create(
                code=f"SHOW{index + 1:03d}",
                defaults={
                    "salon": salon,
                    "type": DiscountCode.Type.PERCENT,
                    "value": 10 + index % 3 * 5,
                    "minimum_purchase": 300_000,
                    "maximum_discount": 250_000,
                    "usage_limit": 500,
                    "starts_at": now - timedelta(days=30),
                    "ends_at": now + timedelta(days=365),
                },
            )
            discounts[salon.id] = discount
        return discounts

    def _create_bookings(
        self,
        *,
        branches,
        staff_by_branch,
        customers,
        wallets,
        discounts,
        bookings_per_branch,
        now,
        rng,
    ):
        bookings = []
        booking_meta = []
        for branch_index, branch in enumerate(branches):
            branch_services = list(branch.branch_services.select_related("service"))
            branch_staff = staff_by_branch[branch.id]
            for booking_index in range(bookings_per_branch):
                customer_offset = branch_index * bookings_per_branch + booking_index
                customer = customers[customer_offset % len(customers)]
                staff = branch_staff[booking_index % len(branch_staff)]
                branch_service = branch_services[booking_index % len(branch_services)]
                if booking_index < bookings_per_branch * 2 // 3:
                    day_offset = -(1 + booking_index // 5)
                    status = (
                        Booking.Status.COMPLETED,
                        Booking.Status.COMPLETED,
                        Booking.Status.COMPLETED,
                        Booking.Status.CANCELLED,
                        Booking.Status.NO_SHOW,
                    )[booking_index % 5]
                else:
                    day_offset = 1 + (booking_index - bookings_per_branch * 2 // 3) // 5
                    status = (
                        Booking.Status.CONFIRMED
                        if booking_index % 5
                        else Booking.Status.PENDING_PAYMENT
                    )
                start = (now + timedelta(days=day_offset)).replace(
                    hour=9 + booking_index % 5 * 2,
                    minute=staff.id % 3 * 15,
                    second=0,
                    microsecond=0,
                )
                discount = discounts[branch.salon_id] if booking_index % 9 == 0 else None
                discount_amount = min(branch_service.price // 10, 150_000) if discount else 0
                booking = Booking(
                    customer=customer,
                    branch=branch,
                    staff=staff,
                    status=status,
                    start_at=start,
                    end_at=start + timedelta(minutes=branch_service.duration_minutes),
                    total_price=branch_service.price,
                    deposit_amount=branch_service.price // 5,
                    discount_code=discount,
                    discount_amount=discount_amount,
                    notes=f"showcase-seed:{branch.id}:{booking_index}",
                    hold_expires_at=(
                        now + timedelta(minutes=10)
                        if status == Booking.Status.PENDING_PAYMENT
                        else None
                    ),
                    cancelled_at=(
                        now - timedelta(days=1)
                        if status == Booking.Status.CANCELLED
                        else None
                    ),
                    cancellation_reason=(
                        "لغو نمونه توسط مشتری" if status == Booking.Status.CANCELLED else ""
                    ),
                )
                bookings.append(booking)
                booking_meta.append((branch_service, discount))
        Booking.objects.bulk_create(bookings, batch_size=500)

        items = []
        payments = []
        reviews = []
        notifications = []
        redemptions = []
        wallet_transactions = []
        for index, (booking, (branch_service, discount)) in enumerate(
            zip(bookings, booking_meta, strict=True)
        ):
            items.append(
                BookingItem(
                    booking=booking,
                    branch_service=branch_service,
                    staff=booking.staff,
                    price=branch_service.price,
                    duration_minutes=branch_service.duration_minutes,
                )
            )
            payable = booking.total_price - booking.discount_amount
            if booking.status in {Booking.Status.COMPLETED, Booking.Status.CONFIRMED}:
                full_payment = booking.status == Booking.Status.COMPLETED or index % 2 == 0
                payments.append(
                    Payment(
                        booking=booking,
                        amount=payable if full_payment else booking.deposit_amount,
                        type=Payment.Type.FULL if full_payment else Payment.Type.DEPOSIT,
                        status=Payment.Status.PAID,
                        gateway_ref=f"showcase-paid-{booking.id}",
                        paid_at=booking.start_at - timedelta(days=2),
                    )
                )
                notifications.append(
                    Notification(
                        recipient=booking.customer,
                        booking=booking,
                        event=Notification.Event.BOOKING_CONFIRMED,
                        channel=Notification.Channel.SMS,
                        status=Notification.Status.SENT,
                        message=f"رزرو شما در {booking.branch.salon.name} تأیید شد.",
                        provider_ref=f"showcase-sms-{booking.id}",
                        sent_at=booking.start_at - timedelta(days=2),
                    )
                )
            elif booking.status == Booking.Status.NO_SHOW:
                payments.append(
                    Payment(
                        booking=booking,
                        amount=booking.deposit_amount,
                        type=Payment.Type.DEPOSIT,
                        status=Payment.Status.PAID,
                        gateway_ref=f"showcase-noshow-{booking.id}",
                        paid_at=booking.start_at - timedelta(days=2),
                    )
                )
            elif booking.status == Booking.Status.CANCELLED:
                payments.append(
                    Payment(
                        booking=booking,
                        amount=booking.deposit_amount,
                        type=Payment.Type.DEPOSIT,
                        status=Payment.Status.REFUNDED,
                        gateway_ref=f"showcase-refund-{booking.id}",
                        paid_at=booking.start_at - timedelta(days=3),
                    )
                )
                notifications.append(
                    Notification(
                        recipient=booking.customer,
                        booking=booking,
                        event=Notification.Event.BOOKING_CANCELLED,
                        channel=Notification.Channel.SMS,
                        status=Notification.Status.SENT,
                        message="رزرو شما لغو شد و نتیجه بازپرداخت ثبت گردید.",
                        provider_ref=f"showcase-cancel-{booking.id}",
                        sent_at=booking.cancelled_at,
                    )
                )
            if booking.status == Booking.Status.COMPLETED and index % 2 == 0:
                rating = 4 + index % 2
                reviews.append(
                    Review(
                        booking=booking,
                        customer=booking.customer,
                        salon=booking.branch.salon,
                        staff=booking.staff,
                        overall_rating=rating,
                        quality_rating=5,
                        cleanliness_rating=4 + index % 2,
                        behavior_rating=5,
                        value_rating=4,
                        comment=rng.choice(
                            (
                                "کیفیت خدمات عالی بود و دوباره مراجعه می‌کنم.",
                                "پرسنل خوش‌برخورد و محیط بسیار تمیز بود.",
                                "رزرو دقیق و بدون معطلی انجام شد.",
                                "از نتیجه کار و برخورد مجموعه راضی بودم.",
                            )
                        ),
                        status=(
                            Review.Status.PENDING if index % 11 == 0 else Review.Status.PUBLISHED
                        ),
                    )
                )
            if discount:
                redemptions.append(
                    DiscountRedemption(
                        discount=discount,
                        booking=booking,
                        customer=booking.customer,
                        amount=booking.discount_amount,
                    )
                )
            if booking.status == Booking.Status.COMPLETED:
                owner_wallet = wallets[booking.branch.salon.owner_id]
                wallet_transactions.append(
                    WalletTransaction(
                        wallet=owner_wallet,
                        amount=payable * 90 // 100,
                        type=WalletTransaction.Type.SALON_EARNING,
                        related_booking=booking,
                        description="درآمد سالن از رزرو تکمیل‌شده",
                    )
                )
        BookingItem.objects.bulk_create(items, batch_size=500)
        Payment.objects.bulk_create(payments, batch_size=500)
        Notification.objects.bulk_create(notifications, batch_size=500)
        Review.objects.bulk_create(reviews, batch_size=500)
        DiscountRedemption.objects.bulk_create(redemptions, batch_size=500)
        WalletTransaction.objects.bulk_create(wallet_transactions, batch_size=500)
        for salon in Salon.objects.filter(slug__startswith="showcase-salon-"):
            refresh_salon_rating(salon)

    @staticmethod
    def _create_social_and_support(customers, salons, support, rng):
        favorites = []
        for customer_index, customer in enumerate(customers):
            for offset in range(3):
                favorites.append(
                    FavoriteSalon(
                        user=customer,
                        salon=salons[(customer_index + offset * 7) % len(salons)],
                    )
                )
        FavoriteSalon.objects.bulk_create(favorites, ignore_conflicts=True, batch_size=500)
        tickets = []
        for index, customer in enumerate(customers[: min(180, len(customers))]):
            status = (
                SupportTicket.Status.OPEN,
                SupportTicket.Status.IN_PROGRESS,
                SupportTicket.Status.RESOLVED,
            )[index % 3]
            tickets.append(
                SupportTicket(
                    customer=customer,
                    assigned_to=support if status != SupportTicket.Status.OPEN else None,
                    subject=rng.choice(
                        (
                            "تغییر زمان نوبت",
                            "پیگیری بازپرداخت",
                            "پرسش درباره کد تخفیف",
                            "اصلاح اطلاعات حساب",
                        )
                    ),
                    message="این یک درخواست نمونه برای بررسی عملکرد واحد پشتیبانی است.",
                    response=(
                        "درخواست بررسی و پاسخ مناسب برای مشتری ثبت شد."
                        if status == SupportTicket.Status.RESOLVED
                        else ""
                    ),
                    status=status,
                )
            )
        SupportTicket.objects.bulk_create(tickets, batch_size=200)

    @staticmethod
    def _ensure_product_salon_coverage(minimum_salons=24):
        salons = list(
            Salon.objects.filter(
                slug__startswith="showcase-salon-", status=Salon.Status.APPROVED
            ).prefetch_related("branches")
        )
        services = Service.objects.filter(
            salon__isnull=True, category__slug__startswith="showcase-category-"
        ).select_related("category")
        for service in services:
            existing_salon_ids = set(
                service.branch_services.values_list("branch__salon_id", flat=True)
            )
            candidates = [salon for salon in salons if salon.id not in existing_salon_ids]
            needed = max(0, minimum_salons - len(existing_salon_ids))
            for salon in candidates[:needed]:
                branch = next(iter(salon.branches.all()))
                BranchService.objects.get_or_create(
                    branch=branch,
                    service=service,
                    defaults={
                        "price": 280_000 + (service.id % 14) * 85_000,
                        "duration_minutes": (45, 60, 75, 90)[service.id % 4],
                        "price_type": BranchService.PriceType.FIXED,
                    },
                )

    @staticmethod
    def _ensure_service_coverage():
        branch_services = (
            BranchService.objects.select_related("branch__salon", "service")
            .annotate(
                customer_count=Count("booking_items__booking__customer", distinct=True)
            )
            .filter(customer_count__lt=3)
        )
        customers = list(User.objects.filter(role=User.Role.CUSTOMER).order_by("id")[:30])
        now = timezone.now()
        for branch_service in branch_services:
            branch = branch_service.branch
            staff = branch.staff.first()
            if not staff:
                phone = f"0996{branch.id:07d}"
                staff_user, created = User.objects.get_or_create(
                    phone=phone,
                    defaults={
                        "name": f"متخصص {branch.name}",
                        "role": User.Role.STAFF,
                        "password": "!",
                    },
                )
                if created:
                    CustomerProfile.objects.filter(user=staff_user).delete()
                staff, _ = Staff.objects.get_or_create(
                    user=staff_user,
                    defaults={
                        "branch": branch,
                        "first_name": "متخصص",
                        "last_name": branch.name,
                        "experience_years": 6,
                        "bio": "پرسنل تکمیلی داده نمایشی",
                    },
                )
                BranchMembership.objects.get_or_create(
                    user=staff_user,
                    branch=branch,
                    defaults={"role": BranchMembership.Role.STAFF},
                )
                for day in range(7):
                    StaffShift.objects.get_or_create(
                        staff=staff,
                        day_of_week=day,
                        defaults={"start_time": time(9), "end_time": time(20)},
                    )
            StaffService.objects.get_or_create(staff=staff, branch_service=branch_service)
            existing_customer_ids = set(
                branch_service.booking_items.values_list(
                    "booking__customer_id", flat=True
                )
            )
            eligible_customers = [
                customer for customer in customers if customer.id not in existing_customer_ids
            ]
            needed = 3 - branch_service.customer_count
            for index in range(needed):
                customer = eligible_customers[
                    (branch_service.id + index) % len(eligible_customers)
                ]
                start = (now - timedelta(days=200 + branch_service.id + index)).replace(
                    hour=11 + index * 2,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                booking = Booking.objects.create(
                    customer=customer,
                    branch=branch,
                    staff=staff,
                    status=Booking.Status.COMPLETED,
                    start_at=start,
                    end_at=start + timedelta(minutes=branch_service.duration_minutes),
                    total_price=branch_service.price,
                    deposit_amount=branch_service.price // 5,
                    notes=f"showcase-coverage:{branch_service.id}:{index}",
                )
                BookingItem.objects.create(
                    booking=booking,
                    branch_service=branch_service,
                    staff=staff,
                    price=branch_service.price,
                    duration_minutes=branch_service.duration_minutes,
                )
                Payment.objects.create(
                    booking=booking,
                    amount=branch_service.price,
                    type=Payment.Type.FULL,
                    status=Payment.Status.PAID,
                    gateway_ref=f"showcase-coverage-{booking.id}",
                    paid_at=start - timedelta(days=1),
                )
                Review.objects.create(
                    booking=booking,
                    customer=customer,
                    salon=branch.salon,
                    staff=staff,
                    overall_rating=5,
                    quality_rating=5,
                    cleanliness_rating=5,
                    behavior_rating=5,
                    value_rating=4,
                    comment="خدمت باکیفیت و تجربه رضایت‌بخشی بود.",
                    status=Review.Status.PUBLISHED,
                )
                Notification.objects.create(
                    recipient=customer,
                    booking=booking,
                    event=Notification.Event.BOOKING_CONFIRMED,
                    status=Notification.Status.SENT,
                    message=f"رزرو شما در {branch.salon.name} تأیید شد.",
                    provider_ref=f"showcase-coverage-sms-{booking.id}",
                    sent_at=start - timedelta(days=1),
                )
            refresh_salon_rating(branch.salon)

    @staticmethod
    def _create_settlements(owners, wallets, rng):
        settlements = []
        for index, owner in enumerate(owners):
            settlements.append(
                Settlement(
                    wallet=wallets[owner.id],
                    amount=500_000 + index % 8 * 250_000,
                    status=(
                        Settlement.Status.REQUESTED,
                        Settlement.Status.PAID,
                        Settlement.Status.REJECTED,
                    )[index % 3],
                    bank_account=f"IR{rng.randrange(10**23, 10**24 - 1)}",
                    note="تسویه نمونه داده نمایشی",
                    processed_at=timezone.now() if index % 3 else None,
                )
            )
        Settlement.objects.bulk_create(settlements, batch_size=200)

    def _print_summary(self):
        models = (
            User,
            City,
            District,
            Salon,
            Branch,
            ServiceCategory,
            Service,
            BranchService,
            Staff,
            Booking,
            Payment,
            Review,
            Notification,
            SupportTicket,
            FavoriteSalon,
            WalletTransaction,
            Settlement,
        )
        self.stdout.write("\nDatabase summary:")
        for model in models:
            self.stdout.write(f"- {model._meta.label}: {model.objects.count():,}")
