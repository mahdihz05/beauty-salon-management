# رابط کاربری نوبت‌آرا

فرانت‌اند نوبت‌آرا با React 19، TypeScript و Vite پیاده‌سازی شده و تمام صفحات عمومی، حساب مشتری، رزرو، پنل سالن و پنل مدیر کل را پوشش می‌دهد.

## فرمان‌ها

```powershell
npm install
npm run dev
npm run typecheck
npm run lint
npm test
npm run format:check
npm run build
npm run test:e2e
```

در حالت توسعه، درخواست‌های `/api` و `/media` توسط Vite به بک‌اند هدایت می‌شوند. آدرس قابل‌تنظیم پروکسی از متغیر `VITE_DEV_API_PROXY` و آدرس API مستقیم از `VITE_API_URL` خوانده می‌شود.

دارایی‌های برند در `public/brand/` و کد برنامه در `src/` قرار دارند. آزمون‌های مرورگری در `e2e/` نگهداری می‌شوند.

راهنمای کامل نصب، نقش‌ها، داده دمو، کنترل کیفیت و استقرار در [README ریشه پروژه](../README.md) قرار دارد.
