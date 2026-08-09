import { useQuery } from "@tanstack/react-query";
import {
  CalendarCheck,
  CircleDollarSign,
  Scissors,
  UsersRound,
} from "lucide-react";
import { Link } from "wouter";
import { api, getApiError } from "../../api/client";
import { SalonLayout } from "../../components/SalonLayout";
import { StatusBadge } from "../../components/StatusBadge";
import { faNumber, toman } from "../../lib/format";
import type { ReportSummary } from "../../types/booking";
import type { BranchService, Paginated, Salon, Staff } from "../../types/salon";

export function DashboardPage() {
  const salons = useQuery({
    queryKey: ["management", "salons"],
    queryFn: async () =>
      (await api.get<Paginated<Salon>>("/management/salons/")).data,
  });
  const services = useQuery({
    queryKey: ["management", "branch-services"],
    queryFn: async () =>
      (await api.get<Paginated<BranchService>>("/management/branch-services/"))
        .data,
  });
  const staff = useQuery({
    queryKey: ["management", "staff"],
    queryFn: async () =>
      (await api.get<Paginated<Staff>>("/management/staff/")).data,
  });
  const salon = salons.data?.results[0];
  const today = new Date().toISOString().slice(0, 10);
  const report = useQuery({
    queryKey: ["management", "today-report", today],
    enabled: Boolean(salon),
    queryFn: async () =>
      (
        await api.get<ReportSummary>(
          `/reports/summary/?date_from=${today}&date_to=${today}`,
        )
      ).data,
  });
  const error = salons.error || services.error || staff.error || report.error;

  return (
    <SalonLayout
      title="سلام، روز بخیر!"
      description="خلاصه وضعیت امروز سالن شما"
      action={
        !salon ? (
          <Link className="button button-primary" href="/salon/onboarding">
            ثبت سالن
          </Link>
        ) : undefined
      }
    >
      {error && <p className="alert alert-error">{getApiError(error)}</p>}
      {salon && (
        <section className="salon-summary-card">
          <div>
            <p className="muted">سالن فعال</p>
            <h2>{salon.name}</h2>
          </div>
          <StatusBadge status={salon.status} label={salon.status_label} />
        </section>
      )}
      <section className="stat-grid" aria-label="آمار امروز">
        <article className="stat-card">
          <span>
            <CalendarCheck />
          </span>
          <div>
            <p>نوبت‌های امروز</p>
            <strong>{faNumber.format(report.data?.booking_count ?? 0)}</strong>
            <small>
              {faNumber.format(report.data?.completed_count ?? 0)} انجام‌شده
            </small>
          </div>
        </article>
        <article className="stat-card">
          <span>
            <CircleDollarSign />
          </span>
          <div>
            <p>درآمد امروز</p>
            <strong>{toman(report.data?.gross_revenue ?? 0)}</strong>
            <small>خالص {toman(report.data?.net_revenue ?? 0)}</small>
          </div>
        </article>
        <article className="stat-card">
          <span>
            <Scissors />
          </span>
          <div>
            <p>خدمات فعال</p>
            <strong>{faNumber.format(services.data?.count ?? 0)}</strong>
            <small>
              <Link href="/salon/services">مدیریت خدمات</Link>
            </small>
          </div>
        </article>
        <article className="stat-card">
          <span>
            <UsersRound />
          </span>
          <div>
            <p>پرسنل فعال</p>
            <strong>
              {faNumber.format(
                staff.data?.results.filter((item) => item.is_active).length ??
                  0,
              )}
            </strong>
            <small>
              <Link href="/salon/staff">مدیریت پرسنل</Link>
            </small>
          </div>
        </article>
      </section>
      {!salons.isLoading && !salon && (
        <section className="panel-empty">
          <Scissors size={36} />
          <h2>هنوز سالنی ثبت نشده است</h2>
          <p>اطلاعات سالن و شعبه خود را تکمیل کنید تا پنل فعال شود.</p>
          <Link className="button button-primary" href="/salon/onboarding">
            شروع ثبت سالن
          </Link>
        </section>
      )}
    </SalonLayout>
  );
}
