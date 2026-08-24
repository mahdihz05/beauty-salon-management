import { Link } from "wouter";

interface BrandLogoProps {
  className?: string;
  href?: string;
  subtitle?: string;
}

export function BrandLogo({
  className = "",
  href = "/",
  subtitle = "BEAUTY & HAIR SALON",
}: BrandLogoProps) {
  return (
    <Link
      aria-label="Salovina؛ نوبت‌دهی آنلاین آرایشگاه‌ها و سالن‌های زیبایی"
      className={`brand-logo ${className}`.trim()}
      href={href}
    >
      <img
        className="brand-logo-mark"
        src="/brand/salovina-icon-192.png"
        srcSet="/brand/salovina-icon-192.png 192w, /brand/salovina-icon-512.png 512w"
        sizes="(max-width: 700px) 58px, 52px"
        width="192"
        height="192"
        alt=""
        aria-hidden="true"
      />
      <span className="brand-logo-copy">
        <strong>Salovina</strong>
        {subtitle && <small>{subtitle}</small>}
      </span>
    </Link>
  );
}
