# راهنمای استقرار روی هاست اشتراکی

این خروجی برای هاست اشتراکی دارای Python 3.10 یا جدیدتر و پشتیبانی WSGI/Passenger آماده شده است. فایل build شده React داخل بسته قرار دارد؛ بنابراین اجرای دائمی Node.js لازم نیست. اگر قرار است React روی خود هاست دوباره build شود، Node.js باید نسخه `20.19+` یا `22.12+` داشته باشد.

## ساختار پیشنهادی در cPanel

- Application root: `apps/salovina`
- Application URL: دامنه یا زیردامنه اصلی پروژه
- Startup file: `salovina_wsgi.py`
- Entry point: `application`
- Python version: ترجیحاً 3.12؛ حداقل 3.10

React و API هر دو از یک دامنه سرو می‌شوند. مسیر API برابر `/api/` است و نیازی به اجرای یک Node process جداگانه وجود ندارد.

## مراحل نصب روی هاست

1. فایل `salovina-cpanel.tar.gz` را مستقیماً داخل Application root یعنی `apps/salovina` آپلود و Extract کنید؛ Application URL روی `saloniva.ir` باقی می‌ماند و Application root جابه‌جا نمی‌شود.
2. یک Python Application با startup file و entry point بالا بسازید و وارد Terminal همان virtualenv شوید.
3. فرمان زیر را در ریشه پروژه اجرا کنید؛ فایل `.env`، Secret Key و مسیرهای داده به‌صورت خودکار ساخته می‌شوند:

```bash
bash deploy-shared-host.sh
```

این فرمان وابستگی‌های production را نصب، migration و collectstatic را اجرا و Passenger را برای restart علامت‌گذاری می‌کند. چون frontend از قبل build شده، npm روی هاست اجرا نمی‌شود.

فرانت‌اند فقط روی سیستم محلی build می‌شود و این اسکریپت هیچ‌وقت npm را روی هاست اجرا نمی‌کند.

## کنترل بعد از نصب

این نشانی‌ها باید پاسخ درست بدهند:

- `/` رابط React
- `/api/health/` پاسخ سلامت SQLite
- `/api/docs/` مستندات API
- `/django-admin/` مدیریت داخلی Django
- یک مسیر عمیق مانند `/salons/demo-rose-gold` بدون خطای 404

## نکات ضروری هاست اشتراکی

- فایل `.env`، دیتابیس و پوشه media نباید داخل `public_html` قابل دانلود باشند.
- SSL دامنه باید فعال باشد. اگر هاست خودش redirect به HTTPS را انجام می‌دهد ولی حلقه redirect ایجاد شد، مقدار `DJANGO_SECURE_SSL_REDIRECT=false` بگذارید؛ کوکی‌های امن همچنان در production فعال‌اند.
- `SERVE_MEDIA_FILES=true` برای سازگاری عمومی فعال شده است. اگر کنترل پنل امکان Alias برای `/media/` دارد، سرو مستقیم وب‌سرور سریع‌تر است و می‌توان این مقدار را `false` کرد.
- SQLite به سرور دیتابیس جدا نیاز ندارد و تنظیم WAL/IMMEDIATE برای هم‌زمانی محدود فعال است. برای ترافیک نوشتن سنگین یا چندین worker پرتعداد، مهاجرت به PostgreSQL توصیه می‌شود؛ برای مقیاس معمول هاست اشتراکی همین تنظیم قابل استفاده است.
- پیش از انتشار عمومی، `OTP_PROVIDER=mock` و `PAYMENT_PROVIDER=mock` باید با سرویس پیامک و درگاه واقعی کارفرما جایگزین شوند؛ در حالت mock پرداخت بانکی و پیامک واقعی انجام نمی‌شود.
- از فایل SQLite و پوشه media به‌صورت روزانه backup بگیرید.

## اجرای جایگزین با Gunicorn

اگر هاست به‌جای Passenger فرمان اجرا می‌گیرد:

```bash
cd backend
gunicorn config.wsgi:application --bind 127.0.0.1:$PORT --workers 1 --timeout 120
```

برای SQLite یک worker انتخاب شده تا فشار نوشتن هم‌زمان در هاست اشتراکی کنترل شود.
