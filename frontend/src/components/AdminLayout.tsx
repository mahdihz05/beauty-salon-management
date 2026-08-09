import {
  Building2,
  BadgeDollarSign,
  Headphones,
  LayoutDashboard,
  ListTree,
  LogOut,
  MapPinned,
  MessageSquareText,
} from "lucide-react";
import type { PropsWithChildren } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "../auth/useAuth";
import { BrandLogo } from "./BrandLogo";

const links = [
  { href: "/admin/dashboard", label: "نمای کلی", icon: LayoutDashboard },
  { href: "/admin/salons", label: "همه سالن‌ها", icon: Building2 },
  { href: "/admin/settings", label: "شهرها و دسته‌بندی", icon: MapPinned },
  { href: "/admin/reviews", label: "مدیریت نظرات", icon: MessageSquareText },
  { href: "/admin/finance", label: "مالی و تسویه", icon: BadgeDollarSign },
  { href: "/admin/support", label: "پشتیبانی", icon: Headphones },
];

export function AdminLayout({
  children,
  title,
}: PropsWithChildren<{ title: string }>) {
  const [location, navigate] = useLocation();
  const auth = useAuth();
  async function logout() {
    await auth.logout();
    navigate("/");
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <BrandLogo
          className="panel-brand"
          href="/admin/dashboard"
          subtitle="مدیریت مرکزی"
        />
        <nav>
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              className={`panel-nav-item ${location === href || location.startsWith(`${href}/`) ? "active" : ""}`}
              href={href}
              key={href}
            >
              <Icon size={20} /> {label}
            </Link>
          ))}
        </nav>
        <button className="admin-logout" onClick={logout}>
          <LogOut size={18} /> خروج از حساب
        </button>
      </aside>
      <main className="admin-main">
        <header>
          <div>
            <ListTree size={22} />
            <span>پنل مدیریت سامانه</span>
          </div>
          <strong>{auth.user?.name || "مدیر کل"}</strong>
        </header>
        <div className="admin-content">
          <div className="page-heading">
            <div>
              <h1>{title}</h1>
              <p>کنترل و نظارت بر اطلاعات سامانه</p>
            </div>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
