import {
  Bell,
  CalendarDays,
  Heart,
  Home,
  Search,
  UserRound,
} from "lucide-react";
import { Link, useLocation } from "wouter";
import { useAuth } from "../auth/useAuth";
import { BrandLogo } from "./BrandLogo";

export function PublicHeader() {
  const [location] = useLocation();
  const { user } = useAuth();
  return (
    <header className="public-header">
      <div className="public-header-inner container">
        <nav>
          <Link
            className={location === "/salons" ? "active" : ""}
            href="/salons"
          >
            اکسپلور
          </Link>
          <Link href="/account/bookings">نوبت‌های من</Link>
          <Link href="/favorites">علاقه‌مندی‌ها</Link>
          <Link href="/account/support">پشتیبانی</Link>
        </nav>
        <BrandLogo className="public-logo" />
        <div className="header-actions">
          <Link aria-label="جستجو" href="/salons">
            <Search />
          </Link>
          <button aria-label="اعلان‌ها">
            <Bell />
          </button>
          <Link
            className="header-avatar"
            aria-label="پروفایل"
            href={user ? "/account/profile" : "/login"}
          >
            {user?.name?.charAt(0) || <UserRound />}
          </Link>
        </div>
      </div>
    </header>
  );
}

export function MobileBottomNav() {
  const [location] = useLocation();
  const items = [
    { href: "/", label: "خانه", icon: Home },
    { href: "/account/bookings", label: "رزروهای من", icon: CalendarDays },
    { href: "/favorites", label: "علاقه‌مندی‌ها", icon: Heart },
    { href: "/account/profile", label: "پروفایل", icon: UserRound },
  ];
  return (
    <nav className="customer-mobile-nav">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Link
            className={location === item.href ? "active" : ""}
            href={item.href}
            key={item.href}
          >
            <Icon />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
