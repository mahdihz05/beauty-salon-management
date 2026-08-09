import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  CheckCircle2,
  Clock3,
  Scissors,
  Store,
  UsersRound,
} from "lucide-react";
import { Link } from "wouter";
import { api, getApiError } from "../../api/client";
import { AdminLayout } from "../../components/AdminLayout";
import { StatusBadge } from "../../components/StatusBadge";
import { faNumber } from "../../lib/format";
import type { Paginated, Salon } from "../../types/salon";

interface AdminStats {
  users: number;
  salons: number;
  pending_salons: number;
  approved_salons: number;
  branches: number;
  services: number;
}

export function AdminDashboardPage() {
  const stats = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: async () =>
      (await api.get<AdminStats>("/admin-panel/dashboard/")).data,
  });
  const pending = useQuery({
    queryKey: ["admin", "pending-salons"],
    queryFn: async () =>
      (await api.get<Paginated<Salon>>("/admin-panel/salons/?status=pending"))
        .data,
  });
  const cards = [
    { label: "کاربران", value: stats.data?.users, icon: UsersRound },
    { label: "کل سالن‌ها", value: stats.data?.salons, icon: Store },
    {
      label: "در انتظار بررسی",
      value: stats.data?.pending_salons,
      icon: Clock3,
    },
    {
      label: "سالن‌های تأییدشده",
      value: stats.data?.approved_salons,
      icon: CheckCircle2,
    },
    { label: "شعب فعال", value: stats.data?.branches, icon: Building2 },
    { label: "خدمات ثبت‌شده", value: stats.data?.services, icon: Scissors },
  ];
  return (
    <AdminLayout title="داشبورد مدیریت">
      {stats.isError && (
        <p className="alert alert-error">{getApiError(stats.error)}</p>
      )}
      <section className="admin-stat-grid">
        {cards.map(({ label, value, icon: Icon }) => (
          <article className="admin-stat" key={label}>
            <span>
              <Icon />
            </span>
            <p>{label}</p>
            <strong>{faNumber.format(value ?? 0)}</strong>
          </article>
        ))}
      </section>
      <section className="admin-section">
        <div className="section-heading">
          <div>
            <h2>درخواست‌های جدید</h2>
            <p>سالن‌های منتظر بررسی و انتشار</p>
          </div>
          <Link href="/admin/salons">مشاهده همه</Link>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>نام سالن</th>
                <th>نوع</th>
                <th>شعبه</th>
                <th>وضعیت</th>
              </tr>
            </thead>
            <tbody>
              {pending.data?.results.slice(0, 5).map((salon) => (
                <tr key={salon.id}>
                  <td>
                    <strong>{salon.name}</strong>
                  </td>
                  <td>{salon.type_label}</td>
                  <td>{faNumber.format(salon.branches.length)}</td>
                  <td>
                    <StatusBadge
                      status={salon.status}
                      label={salon.status_label}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AdminLayout>
  );
}
