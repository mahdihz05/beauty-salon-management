import { ArrowRight } from "lucide-react";
import type { PropsWithChildren } from "react";
import { Link } from "wouter";

export function BookingShell({
  children,
  step,
  backHref,
}: PropsWithChildren<{ step: number; backHref: string }>) {
  return (
    <div className="booking-page">
      <header className="booking-header">
        <Link aria-label="بازگشت" href={backHref}>
          <ArrowRight />
        </Link>
        <Link className="booking-logo" href="/">
          استیچ
        </Link>
        <span>رزرو آنلاین</span>
      </header>
      <div className="booking-progress">
        <span className={step >= 1 ? "active" : ""}>۱. خدمات</span>
        <i />
        <span className={step >= 2 ? "active" : ""}>۲. زمان</span>
        <i />
        <span className={step >= 3 ? "active" : ""}>۳. پرداخت</span>
      </div>
      {children}
    </div>
  );
}
