# انتقال production از SQLite به PostgreSQL

۱. پیش از انتقال، برنامه را موقتاً در حالت نگهداری قرار دهید و از SQLite و Media نسخه پشتیبان بگیرید.

۲. با تنظیمات فعلی SQLite خروجی داده بسازید:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py dumpdata `
  --natural-foreign --natural-primary `
  --exclude contenttypes --exclude auth.permission `
  --indent 2 --output salovina-data.json
```

۳. PostgreSQL و کاربر اختصاصی بسازید و `DATABASE_URL` را در فایل env سرور قرار دهید:

```text
DATABASE_URL=postgresql://salovina:STRONG_PASSWORD@127.0.0.1:5432/salovina
```

۴. migrationها و داده‌ها را وارد کنید:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py migrate --noinput
backend\.venv\Scripts\python.exe backend\manage.py loaddata salovina-data.json
```

۵. شمار رکوردهای کاربران، سالن‌ها، رزروها و پرداخت‌ها را با SQLite مقایسه کنید، smoke test را اجرا کنید و سپس سرویس را باز کنید.

فایل خروجی شامل اطلاعات مشتریان است؛ پس از انتقال باید از سرور حذف یا در فضای رمزگذاری‌شده نگهداری شود.
