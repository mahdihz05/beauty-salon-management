import {
  CalendarDays,
  Clock9,
  ChartNoAxesCombined,
  LayoutDashboard,
  LogOut,
  Scissors,
  Settings,
  UsersRound,
  ContactRound,
  BadgePercent,
  BadgeDollarSign,
} from "lucide-react";
import type { PropsWithChildren } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "../auth/useAuth";
import type { UserRole } from "../types/auth";
import { BrandLogo } from "./BrandLogo";

const navigation: Array<{
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  roles: UserRole[];
}> = [
  {
    href: "/salon/dashboard",
    label: "داشبورد",
    icon: LayoutDashboard,
    roles: ["salon_owner", "branch_manager"],
  },
  {
    href: "/salon/calendar",
    label: "تقویم نوبت‌ها",
    icon: CalendarDays,
    roles: ["salon_owner", "branch_manager", "receptionist", "staff"],
  },
  {
    href: "/salon/availability",
    label: "ساعات رزرو",
    icon: Clock9,
    roles: ["salon_owner", "branch_manager"],
  },
  {
    href: "/salon/my-availability",
    label: "زمان‌های من",
    icon: Clock9,
    roles: ["staff"],
  },
  {
    href: "/salon/services",
    label: "خدمات",
    icon: Scissors,
    roles: ["salon_owner", "branch_manager"],
  },
  {
    href: "/salon/staff",
    label: "پرسنل",
    icon: UsersRound,
    roles: ["salon_owner", "branch_manager"],
  },
  {
    href: "/salon/customers",
    label: "مشتریان",
    icon: ContactRound,
    roles: ["salon_owner", "branch_manager"],
  },
  {
    href: "/salon/promotions",
    label: "تخفیف و پیامک",
    icon: BadgePercent,
    roles: ["salon_owner"],
  },
  {
    href: "/salon/finance",
    label: "مالی و تسویه",
    icon: BadgeDollarSign,
    roles: ["salon_owner", "branch_manager"],
  },
  {
    href: "/salon/reports",
    label: "گزارش‌ها",
    icon: ChartNoAxesCombined,
    roles: ["salon_owner", "branch_manager"],
  },
];

interface SalonLayoutProps extends PropsWithChildren {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function SalonLayout({
  title,
  description,
  action,
  children,
}: SalonLayoutProps) {
  const [location, navigate] = useLocation();
  const auth = useAuth();
  const allowedNavigation = navigation.filter(
    (item) => auth.user && item.roles.includes(auth.user.role),
  );

  async function logout() {
    await auth.logout();
    navigate("/");
  }

  return (
    <div className="panel-shell">
      <aside className="panel-sidebar">
        <BrandLogo
          className="panel-brand"
          href="/salon/dashboard"
          subtitle="مدیریت سالن"
        />
        <nav aria-label="منوی پنل سالن">
          {allowedNavigation.map(({ href, label, icon: Icon }) => (
            <Link
              className={`panel-nav-item ${location === href ? "active" : ""}`}
              href={href}
              key={href}
            >
              <Icon size={20} aria-hidden="true" /> {label}
            </Link>
          ))}
        </nav>
        <div className="panel-user">
          <span className="mini-avatar">
            {auth.user?.name?.charAt(0) || "م"}
          </span>
          <div>
            <strong>{auth.user?.name || "مدیر سالن"}</strong>
            <small>{auth.user?.phone}</small>
          </div>
          <button aria-label="خروج" onClick={logout}>
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <div className="panel-main">
        <header className="panel-mobile-header">
          <BrandLogo
            className="panel-brand"
            href="/salon/dashboard"
            subtitle=""
          />
          <button aria-label="تنظیمات">
            <Settings size={22} />
          </button>
        </header>
        <main className="panel-content">
          <div className="page-heading">
            <div>
              <h1>{title}</h1>
              {description && <p>{description}</p>}
            </div>
            {action}
          </div>
          {children}
        </main>
        <nav className="panel-mobile-nav" aria-label="منوی پایین پنل">
          {allowedNavigation.slice(0, 4).map(({ href, label, icon: Icon }) => (
            <Link
              className={location === href ? "active" : ""}
              href={href}
              key={href}
            >
              <Icon size={20} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}
