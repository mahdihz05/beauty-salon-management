# Salovina — Multi-branch Salon Booking and Management

A React/TypeScript frontend and Django REST API for customer booking, salon operations and platform administration. The product UI is Persian-first and RTL; this engineering overview is English-first. The detailed Persian installation, demo and operations guide is retained below.

**Status:** a demo-oriented implementation with mock SMS/payment integrations, not a certified production service. The existing guide documents a demo endpoint; its availability and deployed configuration were not verified in this documentation review. Demo OTP codes are displayed on the login screen and must not be exposed in production.

## Architecture and Engineering Evidence

```text
React / TypeScript / Vite / TanStack Query
                    |
             Django REST API
                    |
       +------------+------------+
       |            |            |
 PostgreSQL      Media       SMS/payment
 (SQLite dev)    files        adapters
```

The backend separates accounts, salons, bookings, payments, notifications, reviews and reporting. The key review targets are domain rules and server-side boundaries, not just dashboard screens:

| Concern | Mechanism and source |
|---|---|
| Availability calculation | The [booking engine](backend/bookings/engine.py) intersects configured branch opening windows with staff shifts, excludes closures/time off/active bookings, accounts for preparation buffers, and sums staff-specific service durations. |
| Competing bookings | Hold creation uses `transaction.atomic`, locks a stable staff row with `select_for_update`, then rechecks availability before writing a ten-minute hold. Service price/duration are snapshotted into booking items. This is an inspectable concurrency mechanism, not a load-test result or a guarantee of equivalent SQLite/PostgreSQL locking behavior. |
| Scoped permissions | [Account permissions](backend/accounts/permissions.py) resolve branch access through salon ownership or active memberships; management checks distinguish branch managers from other members. [Salon permissions](backend/salons/permissions.py) check ownership/admin access. These files are review entry points, not a complete authorization audit. |
| Payment and wallet transitions | [Payment services](backend/payments/services.py) use atomic operations and row locks for payment confirmation, refunds and settlements. Current manual booking methods are in-person payment and card-transfer verification; the [gateway adapter](backend/payments/providers.py) implements only a mock provider. |

## Verification Status

As of October 2, 2026, no GitHub Actions workflows were present in the inspected tree and the repository Actions API returned zero runs. No passing-current-HEAD test result is claimed. The inspected source commit was `5568d9b336fe385d0f149413e69c4fd719ec97a6`.

[quality-check.ps1](quality-check.ps1) defines local checks for Ruff, backend pytest, Django system/migration/schema checks, deployment settings checks, frontend lint/typecheck/tests/format/build, npm audit and Playwright. It is a check runner, not evidence that those checks have passed. Neither it nor application, build, smoke or deployment commands were executed for this README update. The older test count in the Persian guide is historical documentation, not a recounted or passing suite at this commit.

## Local Development

Use a disposable local environment, not an existing production database. Requirements documented by the project are Python 3.12+, Node.js 24+ and Microsoft Edge for the current Playwright configuration.

From the repository root on Windows:

```powershell
.\setup.ps1
.\start-dev.ps1
```

Setup prepares dependencies, migrations and demo/showcase data. The development launcher selects free frontend/backend ports. Manual commands, local API/Swagger routes, environment examples and quality-check instructions are preserved in the Persian guide below.

## Demo and Production Boundaries

Before real customer use: replace mock SMS/payment providers; disable demo OTP display; remove or replace demo accounts/data; configure strong secrets, allowed hosts, CSRF/CORS and HTTPS; persist media; arrange recurring booking tasks, monitoring and tested backups; and confirm cancellation, refund, commission and settlement policies. A settings check alone does not establish operational readiness.

The [PostgreSQL migration guide](docs/POSTGRESQL_MIGRATION.md) requires maintenance mode, database/media backups, record comparison and smoke checks. Its exported data contains customer information and must remain protected. No migration, export or deployment was performed in this review.

See also the [delivery checklist](docs/DELIVERY_CHECKLIST.md), [requirements audit](docs/REQUIREMENTS_AUDIT.md) and [user guide](docs/USER_GUIDE.md). These are project documentation, not independent production acceptance evidence.

## License

No project software license has been declared. Licensing remains an explicit owner decision; public repository visibility does not grant reuse rights.

## Persian Product and Operations Guide

<div align="center" dir="rtl">
  <img src="frontend/public/brand/salovina-logo.png" width="180" alt="لوگوی Salovina" />
  <h1>Salovina</h1>
  <p><strong>سامانه نوبت‌دهی آنلاین و مدیریت آرایشگاه‌ها و سالن‌های زیبایی</strong></p>
  <p>فارسی، راست‌چین، واکنش‌گرا و مناسب مدیریت چندسالن، چندشعبه و چندنقش</p>
</div>

## معرفی

Salovina یک پلتفرم کامل برای جستجو و رزرو آنلاین خدمات زیبایی، مدیریت عملیات سالن و نظارت مرکزی بر کل سامانه است. محصول از سه فضای اصلی تشکیل شده است:

- تجربه عمومی و حساب مشتری برای جستجو، رزرو، پرداخت، لغو، کیف پول، نظر و پشتیبانی؛
- پنل سالن برای مالک، مدیر شعبه، پذیرش و آرایشگر با دسترسی‌های تفکیک‌شده؛
- پنل مدیر کل برای مشاهده همه سالن‌ها، جزئیات مشتریان و نوبت‌ها، درآمد، تنظیمات مرکزی، نظرات، مالی و پشتیبانی.

نسخه نمایشی آنلاین:

**[http://141.11.1.223:8020/](http://141.11.1.223:8020/)**

> نسخه آنلاین برای ارزیابی پروژه است. پیامک OTP و درگاه پرداخت فعلاً Mock هستند و داده‌های موجود جنبه نمایشی دارند.

## قابلیت‌های اصلی

### قواعد قطعی رزرو و زمان‌بندی

- ساعات هر شعبه و ساعات شخصی هر آرایشگر می‌توانند شامل چند بازه در یک روز باشند؛ اسلات‌ها فقط از تقاطع این بازه‌ها و پس از کسر تعطیلی، مرخصی، رزرو قبلی و buffer ساخته می‌شوند.
- مدت پایه خدمت در سطح شعبه توسط مالک یا مدیر همان شعبه تعیین می‌شود. آرایشگر فقط مدت اختصاصی خدمات تخصیص‌یافته به خودش را تغییر می‌دهد و می‌تواند به مدت پایه بازگردد.
- مدت رزرو چندخدمتی جمع مدت مؤثر همه خدمات است. قیمت و مدت هر قلم هنگام رزرو snapshot می‌شود.
- Hold آنلاین دقیقاً ۱۰ دقیقه اعتبار دارد. منشأ `online` یا `walk_in` تغییرناپذیر است و حساب کاری آرایشگر امکان ساخت رزرو مشتری‌محور ندارد.
- روش‌های رزرو جدید فقط «پرداخت حضوری» و «کارت‌به‌کارت» هستند. پرداخت حضوری رزرو را قطعی و مبلغ را تا مراجعه وصول‌نشده نگه می‌دارد؛ کارت‌به‌کارت تا تأیید رسید در انتظار بررسی می‌ماند.
- فقط مشتری رزرو، مالک سالن و مدیر همان شعبه می‌توانند تا ۲۴ ساعت مانده به شروع، نوبت را لغو کنند. پذیرش فقط نوبت آنلاین قطعی را پذیرش می‌کند.
- مالی ابتدا بر اساس سالن و سپس شعبه نمایش داده می‌شود و فیلتر تاریخ، روش، وضعیت، منشأ، جستجو و CSV دارد. مدیر شعبه فقط شعب تعیین‌شده را می‌بیند؛ درخواست تسویه فقط برای مالک و پردازش آن فقط برای مدیر کل است.

### مشتری

- جستجو و فیلتر سالن بر اساس شهر، منطقه، دسته‌بندی و نوع سالن؛
- مشاهده پروفایل سالن، گالری، خدمات، پرسنل، امتیاز و آدرس ثابت؛
- انتخاب چند خدمت، آرایشگر، تاریخ هجری شمسی و ساعت آزاد؛
- رزرو موقت، پرداخت کامل یا بیعانه و ثبت کد تخفیف؛
- مشاهده و لغو نوبت، کیف پول، بازپرداخت و ثبت نظر؛
- علاقه‌مندی‌ها، پروفایل و ثبت/پیگیری تیکت پشتیبانی.

### سالن و شعبه

- داشبورد عملیاتی، تقویم نوبت‌ها و ثبت نوبت حضوری/تلفنی؛
- مدیریت خدمات، قیمت، مدت، پرسنل، مهارت، شیفت و مرخصی؛
- تعیین ساعات قابل رزرو و ثبت تعطیلی روزانه یا بازه‌ای؛
- مدیریت مشتریان، تخفیف‌ها، پیامک‌ها و گزارش‌های درآمد؛
- کنترل انجام خدمت، عدم حضور، لغو و دریافت مانده نقدی؛
- گزارش رزرو، درآمد، کارمزد و خدمات پرفروش با خروجی CSV.

### مدیریت مرکزی

- داشبورد و آمار کل سامانه؛
- مشاهده همه سالن‌ها و جزئیات شعب، مشتریان، نوبت‌ها، پرداخت و درآمد هر سالن؛
- تأیید، رد یا تعلیق سالن؛
- مدیریت شهر، منطقه، دسته‌بندی و نظرات؛
- تب یکپارچه مالی و تسویه؛
- تب یکپارچه پشتیبانی و مدیریت تیکت‌ها.

## فناوری و معماری

| لایه | فناوری |
| --- | --- |
| رابط کاربری | React 19، TypeScript، Vite، TanStack Query |
| بک‌اند | Django 5.2، Django REST Framework |
| احراز هویت | OTP، JWT Access/Refresh و محدودسازی نرخ درخواست |
| پایگاه داده | PostgreSQL در production؛ SQLite فقط برای توسعه و بسته سبک آزمایشی |
| فایل‌ها | ذخیره محلی Media با کنترل نوع و سقف حجم |
| API | OpenAPI و Swagger |
| استقرار | Gunicorn، WhiteNoise، Passenger/cPanel یا سرویس systemd |
| آزمون | Django Test، Ruff، Vitest، Oxlint، TypeScript و Playwright |

```text
React / TypeScript
        │
        ▼
Django REST API ───── JWT / OTP
        │
        ├── PostgreSQL / SQLite توسعه
        ├── Media files
        ├── SMS provider adapter
        └── Payment provider adapter
```

## نقش‌ها و سطح دسترسی

| نقش | محدوده دسترسی |
| --- | --- |
| مدیر کل | دسترسی سراسری به آمار، سالن‌ها، جزئیات داده‌ها، تنظیمات، نظرات، مالی و پشتیبانی |
| مالک سالن | مدیریت کامل همه شعب متعلق به سالن خود |
| مدیر شعبه | مدیریت عملیات و گزارش‌های همان شعبه |
| پذیرش | تقویم شعبه، پذیرش نوبت آنلاین، ثبت نوبت حضوری و دریافت پرداخت در محل؛ بدون مجوز لغو یا تغییر منشأ رزرو |
| آرایشگر | مشاهده نوبت‌ها و مدیریت شیفت، مرخصی و مدت اختصاصی خدمات خودش؛ بدون دسترسی به تنظیمات سالن |
| مشتری | اطلاعات، رزروها، پرداخت‌ها، نظرات و تیکت‌های شخصی |

نقش‌های مستقل مالی و پشتیبانی حذف شده‌اند و امکانات آن‌ها به‌صورت دو تب داخل پنل مدیر کل قرار دارند.

## حساب‌های نمایشی

ورود برنامه با کد یک‌بارمصرف است. در محیط دمو، کد ۶ رقمی بعد از درخواست روی همان صفحه نمایش داده می‌شود.

| نقش | شماره موبایل | مسیر اصلی |
| --- | --- | --- |
| مدیر کل | `09120000001` | `/admin/dashboard` |
| مالک سالن | `09120000002` | `/salon/dashboard` |
| مشتری | `09120000003` | `/` |
| مدیر شعبه | `09120000006` | `/salon/dashboard` |
| پذیرش | `09120000007` | `/salon/calendar` |
| آرایشگر | `09120000008` | `/salon/calendar` |

حساب‌های قدیمی `09120000004` و `09120000005` برای حفظ داده‌های قبلی به نقش مدیر کل تبدیل شده‌اند. برای بررسی محصول از حساب اصلی مدیر کل استفاده شود.

کد تخفیف نمونه: `DEMO20`

## پیش‌نیاز توسعه

- Python 3.12 یا جدیدتر؛
- Node.js 24 یا جدیدتر؛
- Microsoft Edge برای آزمون‌های Playwright در تنظیمات فعلی پروژه.

## نصب خودکار در ویندوز

از ریشه پروژه اجرا کنید:

```powershell
.\setup.ps1
```

این اسکریپت محیط مجازی Python، وابستگی‌های بک‌اند و فرانت‌اند، migrationها و داده‌های دمو/نمایشی را آماده می‌کند.

## اجرای محلی

```powershell
.\start-dev.ps1
```

اسکریپت به‌صورت خودکار پورت آزاد انتخاب می‌کند. محدوده پیش‌فرض:

- فرانت‌اند: `5173` تا `5180`؛
- بک‌اند: `8000` تا `8010`.

مسیرهای محلی مهم:

- API: `http://127.0.0.1:8000/api/`
- Swagger: `http://127.0.0.1:8000/api/docs/`
- مدیریت داخلی Django: `http://127.0.0.1:8000/django-admin/`

## اجرای دستی

### بک‌اند

```powershell
backend\.venv\Scripts\python.exe backend\manage.py migrate --noinput
backend\.venv\Scripts\python.exe backend\manage.py seed_demo
backend\.venv\Scripts\python.exe backend\manage.py seed_showcase
backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

### فرانت‌اند

```powershell
npm --prefix frontend install
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

## داده نمایشی

فرمان `seed_showcase` به‌صورت پیش‌فرض دیتاست جمع‌وجور و طبیعی شامل ۱۲۰ مشتری، ۱۲ سالن نمایشی، ۲۴ شعبه و حدود ۴۸۰ رزرو می‌سازد. همراه سه سالن اصلی دمو، محیط نهایی تقریباً ۱۵ سالن و نزدیک ۵۰۰ رزرو دارد. برای مشاهده اثر پاک‌سازی ایمن بدون تغییر داده از `seed_showcase --reset-showcase --dry-run` و برای جایگزینی رکوردهای نشان‌دار از `seed_showcase --reset-showcase` استفاده کنید. سالن یا رزروی که داده بدون نشانگر showcase داشته باشد حفظ می‌شود.

## کنترل کیفیت

اجرای همه بررسی‌ها:

```powershell
.\quality-check.ps1
```

این چرخه شامل موارد زیر است:

- Ruff و تست‌های Django؛
- Django system check و migration drift؛
- اعتبارسنجی OpenAPI و production check؛
- Oxlint، TypeScript، Vitest و Prettier؛
- build تولیدی و npm audit؛
- سناریوهای واقعی Playwright در اندازه دسکتاپ، تبلت ۷۶۸ پیکسل و موبایل؛ همراه با کنترل بیرون‌زدگی افقی صفحات عمومی و پنل‌ها.

شمار **۱۰۱ تست** از مستندات قبلی پروژه نقل شده است؛ این عدد شمارش مجدد یا نتیجه اجرای موفق در HEAD فعلی نیست. مجموعه مرورگری سناریوهای مشتری، رزرو و پرداخت، مالک، مدیر کل، پذیرش، آرایشگر، ساعات رزرو و واکنش‌گرایی دارد؛ موفقیت این سناریوها در این بازبینی اجرا یا تأیید نشده است.

## کارهای زمان‌بندی‌شده

فرمان زیر Holdهای منقضی را آزاد و یادآوری نوبت‌های نزدیک را پردازش می‌کند:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py process_booking_tasks
```

در محیط production آن را هر ۱۵ دقیقه با cron یا Task Scheduler اجرا کنید.

## تنظیمات محیط

نمونه‌ها:

- توسعه: [`backend/.env.example`](backend/.env.example)
- production: [`backend/.env.production.example`](backend/.env.production.example)
- فرانت‌اند: [`frontend/.env.example`](frontend/.env.example)

در production حداقل این موارد باید تنظیم شوند:

- `DJANGO_SECRET_KEY` قوی و منحصربه‌فرد؛
- `DJANGO_DEBUG=false`؛
- دامنه‌های مجاز، CSRF و CORS؛
- آدرس `DATABASE_URL` برای PostgreSQL و مسیر پایدار Media؛
- سرویس پیامک واقعی و غیرفعال‌کردن نمایش OTP دمو؛
- سرویس پرداخت واقعی؛
- HTTPS و پشتیبان‌گیری منظم.

## استقرار

### هاست اشتراکی

```powershell
.\build-deployment-package.ps1
```

خروجی ZIP در پوشه نادیده‌گرفته‌شده `deployment-build/` ساخته می‌شود. راهنمای cPanel و Passenger در [`docs/SHARED_HOSTING.md`](docs/SHARED_HOSTING.md) قرار دارد.

### سرور فعلی دمو

- آدرس: `http://141.11.1.223:8020/`
- Nginx روی پورت عمومی `8020` با gzip، keep-alive و cache فایل‌های استاتیک؛
- Gunicorn داخلی روی `127.0.0.1:8021` با دو worker و threadهای هم‌زمان؛
- دیتابیس پایدار خارج از مسیر Git؛
- build فرانت‌اند و media مستقیماً توسط Nginx ارائه می‌شوند و فقط API به Django می‌رود؛
- نمونه تنظیمات پایدار Nginx و systemd در پوشه `deployment/` نگهداری می‌شود.

## ساختار پروژه

```text
beauty-salon-management/
├── backend/                 Django REST API و PostgreSQL/SQLite توسعه
├── frontend/                React / TypeScript
├── docs/                    راهنماهای فنی و تحویل
├── delivery/                خروجی قابل‌ارسال برای کارفرما
├── deployment/              تنظیمات Nginx و systemd سرور VPS
├── build-deployment-package.ps1
├── quality-check.ps1
├── setup.ps1
└── start-dev.ps1
```

## مستندات

- [PDF معرفی و دسترسی نسخه نمایشی](delivery/NobatAra-Employer-Preview-Guide.pdf)
- [راهنمای کاربری](docs/USER_GUIDE.md)
- [چک‌لیست تحویل](docs/DELIVERY_CHECKLIST.md)
- [ممیزی نیازمندی‌ها](docs/REQUIREMENTS_AUDIT.md)
- [نگاشت صفحات طراحی](docs/DESIGN_MAPPING.md)
- [راهنمای هاست اشتراکی](docs/SHARED_HOSTING.md)
- [راهنمای مهاجرت production به PostgreSQL](docs/POSTGRESQL_MIGRATION.md)
- [برنامه پیاده‌سازی](IMPLEMENTATION_PLAN.md)

## موارد دمو که پیش از بهره‌برداری باید تغییر کنند

- اتصال سرویس پیامک واقعی و حذف نمایش کد OTP؛
- اتصال درگاه پرداخت واقعی؛
- تنظیم دامنه و SSL؛
- جایگزینی حساب‌ها و داده‌های آزمایشی؛
- تأیید قوانین کارمزد، بیعانه، لغو، بازپرداخت و تسویه؛
- تکمیل اطلاعات حقوقی، تماس و محتوای برند؛
- نهایی‌سازی cron، backup، پایش خطا و چرخش کلیدهای امنیتی.

جزئیات این موارد در PDF تحویل کارفرما آمده است.
