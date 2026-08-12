import { Link } from "wouter";

interface BrandLogoProps {
  className?: string;
  href?: string;
  subtitle?: string;
}

export function BrandLogo({
  className = "",
  href = "/",
  subtitle = "NOBATARA",
}: BrandLogoProps) {
  return (
    <Link
      aria-label="نوبت‌آرا؛ نوبت‌دهی آنلاین آرایشگاه‌ها و سالن‌های زیبایی"
      className={`brand-logo ${className}`.trim()}
      href={href}
    >
      <img
        className="brand-logo-mark"
        src="/brand/nobatara-icon-192.png"
        width="192"
        height="192"
        alt=""
        aria-hidden="true"
      />
      <span className="brand-logo-copy">
        <strong>نوبت‌آرا</strong>
        {subtitle && <small>{subtitle}</small>}
      </span>
    </Link>
  );
}
