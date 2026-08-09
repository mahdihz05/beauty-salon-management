import { Link } from "wouter";

export function NotFoundPage() {
  return (
    <main className="empty-state container">
      <p className="eyebrow">خطای ۴۰۴</p>
      <h1>صفحه پیدا نشد</h1>
      <Link className="button button-primary" href="/">
        بازگشت به صفحه اصلی
      </Link>
    </main>
  );
}
