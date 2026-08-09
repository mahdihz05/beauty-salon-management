import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BadgeDollarSign,
  Building2,
  CalendarCheck,
  CreditCard,
  LoaderCircle,
  Scissors,
  Star,
  UserRound,
  UsersRound,
} from "lucide-react";
import { useState } from "react";
import { Link, useRoute } from "wouter";
import { api, getApiError } from "../../api/client";
import { AdminLayout } from "../../components/AdminLayout";
import { StatusBadge } from "../../components/StatusBadge";
import {
  formatPersianDate,
  formatPersianDateTime,
  formatPersianTime,
} from "../../lib/date";
import { faNumber, toman } from "../../lib/format";
import type { AdminSalonOverview } from "../../types/admin";

type DetailTab =
  | "bookings"
  | "customers"
  | "payments"
  | "services"
  | "staff"
  | "reviews"
  | "discounts";

const paymentType = { deposit: "بیعانه", full: "کامل", remainder: "مانده" };
const paymentMethod = { online: "آنلاین", cash: "نقدی", wallet: "کیف پول" };

export function AdminSalonDetailPage() {
  const [, route] = useRoute("/admin/salons/:salonId");
  const salonId = Number(route?.salonId);
  const [tab, setTab] = useState<DetailTab>("bookings");
  const overview = useQuery({
    queryKey: ["admin", "salon-overview", salonId],
    enabled: Number.isFinite(salonId),
    queryFn: async () =>
      (
        await api.get<AdminSalonOverview>(
          `/admin-panel/salons/${salonId}/overview/`,
        )
      ).data,
  });

  if (overview.isLoading) {
    return (
      <AdminLayout title="اطلاعات کامل سالن">
        <div className="page-loader">
          <LoaderCircle className="spin" /> در حال دریافت اطلاعات سالن...
        </div>
      </AdminLayout>
    );
  }
  if (overview.isError || !overview.data) {
    return (
      <AdminLayout title="اطلاعات کامل سالن">
        <p className="alert alert-error">{getApiError(overview.error)}</p>
      </AdminLayout>
    );
  }

  const data = overview.data;
  const { salon, metrics } = data;
  const tabs: Array<{ id: DetailTab; label: string; count: number }> = [
    { id: "bookings", label: "نوبت‌ها", count: data.bookings.length },
    { id: "customers", label: "مشتریان", count: data.customers.length },
    { id: "payments", label: "پرداخت‌ها", count: data.payments.length },
    { id: "services", label: "خدمات", count: data.services.length },
    { id: "staff", label: "پرسنل", count: data.staff.length },
    { id: "reviews", label: "نظرات", count: data.reviews.length },
    { id: "discounts", label: "تخفیف‌ها", count: data.discounts.length },
  ];

  return (
    <AdminLayout title={`نظارت کامل: ${salon.name}`}>
      <Link className="admin-back-link" href="/admin/salons">
        <ArrowRight size={17} /> بازگشت به همه سالن‌ها
      </Link>

      <section className="admin-salon-identity">
        <div>
          <span className="admin-salon-icon">
            <Building2 />
          </span>
          <div>
            <div className="admin-salon-title-row">
              <h2>{salon.name}</h2>
              <StatusBadge status={salon.status} label={salon.status_label} />
            </div>
            <p>{salon.description || "برای این سالن توضیحی ثبت نشده است."}</p>
          </div>
        </div>
        <dl>
          <div>
            <dt>مالک سالن</dt>
            <dd>{salon.owner_name || "بدون نام"}</dd>
          </div>
          <div>
            <dt>موبایل مالک</dt>
            <dd dir="ltr">{salon.owner_phone}</dd>
          </div>
          <div>
            <dt>نوع سالن</dt>
            <dd>{salon.type_label}</dd>
          </div>
          <div>
            <dt>امتیاز</dt>
            <dd>
              {faNumber.format(salon.rating_average)} از ۵ ·{" "}
              {faNumber.format(salon.review_count)} نظر
            </dd>
          </div>
          <div>
            <dt>تاریخ عضویت</dt>
            <dd>{formatPersianDate(salon.created_at)}</dd>
          </div>
        </dl>
      </section>

      <section className="admin-salon-metrics">
        <article>
          <CalendarCheck />
          <span>کل نوبت‌ها</span>
          <strong>{faNumber.format(metrics.booking_count)}</strong>
          <small>{faNumber.format(metrics.completed_count)} انجام‌شده</small>
        </article>
        <article>
          <UsersRound />
          <span>مشتریان یکتا</span>
          <strong>{faNumber.format(metrics.customer_count)}</strong>
          <small>{faNumber.format(metrics.confirmed_count)} نوبت قطعی</small>
        </article>
        <article>
          <BadgeDollarSign />
          <span>فروش انجام‌شده</span>
          <strong>{toman(metrics.gross_revenue)}</strong>
          <small>بر پایه نوبت‌های تکمیل‌شده</small>
        </article>
        <article>
          <CreditCard />
          <span>پرداخت موفق</span>
          <strong>{toman(metrics.paid_revenue)}</strong>
          <small>{faNumber.format(metrics.payment_count)} تراکنش</small>
        </article>
        <article>
          <Building2 />
          <span>شعب فعال و غیرفعال</span>
          <strong>{faNumber.format(metrics.branch_count)}</strong>
          <small>همه شعب سالن</small>
        </article>
        <article>
          <Scissors />
          <span>خدمات قابل ارائه</span>
          <strong>{faNumber.format(metrics.service_count)}</strong>
          <small>{faNumber.format(metrics.staff_count)} نفر پرسنل</small>
        </article>
        <article>
          <Star />
          <span>نظرات مشتریان</span>
          <strong>{faNumber.format(metrics.review_count)}</strong>
          <small>{faNumber.format(metrics.cancelled_count)} نوبت لغوشده</small>
        </article>
        <article>
          <UserRound />
          <span>عدم حضور</span>
          <strong>{faNumber.format(metrics.no_show_count)}</strong>
          <small>{toman(metrics.refunded_amount)} بازپرداخت</small>
        </article>
      </section>

      <section className="admin-branch-section admin-section">
        <h2>شعب و اطلاعات تماس</h2>
        <div className="admin-branch-grid">
          {data.branches.map((branch) => (
            <article key={branch.id}>
              <div>
                <Building2 />
                <strong>{branch.name}</strong>
              </div>
              <p>
                {branch.city_name} · {branch.address}
              </p>
              <small dir="ltr">{branch.phone}</small>
              <StatusBadge
                status={branch.is_active ? "approved" : "suspended"}
                label={branch.is_active ? "فعال" : "غیرفعال"}
              />
            </article>
          ))}
        </div>
      </section>

      <nav className="admin-detail-tabs" aria-label="بخش‌های اطلاعات سالن">
        {tabs.map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? "active" : ""}
            onClick={() => setTab(item.id)}
          >
            {item.label} <span>{faNumber.format(item.count)}</span>
          </button>
        ))}
      </nav>

      <section className="admin-detail-content">
        {tab === "bookings" && (
          <DataTable
            headers={[
              "شناسه",
              "مشتری",
              "شعبه",
              "خدمت",
              "پرسنل",
              "تاریخ مراجعه",
              "مبلغ",
              "وضعیت",
            ]}
          >
            {data.bookings.map((booking) => (
              <tr key={booking.id}>
                <td>#{faNumber.format(booking.id)}</td>
                <td dir="ltr">
                  {data.customers.find((item) => item.id === booking.customer)
                    ?.phone || booking.customer}
                </td>
                <td>{booking.branch_name}</td>
                <td>
                  {booking.items.map((item) => item.service_name).join("، ")}
                </td>
                <td>{booking.staff_name}</td>
                <td>
                  {formatPersianDate(booking.start_at)} ·{" "}
                  {formatPersianTime(booking.start_at)}
                </td>
                <td>{toman(booking.total_price)}</td>
                <td>
                  <StatusBadge
                    status={booking.status}
                    label={booking.status_label}
                  />
                </td>
              </tr>
            ))}
          </DataTable>
        )}
        {tab === "customers" && (
          <DataTable
            headers={[
              "نام مشتری",
              "شماره موبایل",
              "کل نوبت",
              "انجام‌شده",
              "مجموع خرید",
              "آخرین مراجعه",
            ]}
          >
            {data.customers.map((customer) => (
              <tr key={customer.id}>
                <td>{customer.name || "بدون نام"}</td>
                <td dir="ltr">{customer.phone}</td>
                <td>{faNumber.format(customer.booking_count)}</td>
                <td>{faNumber.format(customer.completed_count)}</td>
                <td>{toman(customer.total_spent)}</td>
                <td>
                  {customer.last_booking_at
                    ? formatPersianDateTime(customer.last_booking_at)
                    : "—"}
                </td>
              </tr>
            ))}
          </DataTable>
        )}
        {tab === "payments" && (
          <DataTable
            headers={[
              "شناسه",
              "رزرو",
              "مشتری",
              "شعبه",
              "نوع",
              "روش",
              "مبلغ",
              "زمان",
              "وضعیت",
            ]}
          >
            {data.payments.map((payment) => (
              <tr key={payment.id}>
                <td>#{faNumber.format(payment.id)}</td>
                <td>#{faNumber.format(payment.booking)}</td>
                <td dir="ltr">{payment.customer_phone}</td>
                <td>{payment.branch_name}</td>
                <td>{paymentType[payment.type]}</td>
                <td>{paymentMethod[payment.method]}</td>
                <td>{toman(payment.amount)}</td>
                <td>
                  {formatPersianDateTime(payment.paid_at || payment.created_at)}
                </td>
                <td>
                  <StatusBadge
                    status={payment.status}
                    label={
                      payment.status === "paid"
                        ? "موفق"
                        : payment.status === "pending"
                          ? "در انتظار"
                          : payment.status === "refunded"
                            ? "بازپرداخت"
                            : "ناموفق"
                    }
                  />
                </td>
              </tr>
            ))}
          </DataTable>
        )}
        {tab === "services" && (
          <DataTable
            headers={[
              "خدمت",
              "دسته‌بندی",
              "شعبه",
              "قیمت",
              "مدت",
              "نوع قیمت",
              "وضعیت",
            ]}
          >
            {data.services.map((service) => (
              <tr key={service.id}>
                <td>{service.service_name}</td>
                <td>{service.category_name}</td>
                <td>{service.branch_name}</td>
                <td>{toman(service.price)}</td>
                <td>{faNumber.format(service.duration_minutes)} دقیقه</td>
                <td>{service.price_type_label}</td>
                <td>{service.is_active ? "فعال" : "غیرفعال"}</td>
              </tr>
            ))}
          </DataTable>
        )}
        {tab === "staff" && (
          <DataTable headers={["نام", "شعبه", "سابقه", "معرفی", "وضعیت"]}>
            {data.staff.map((person) => (
              <tr key={person.id}>
                <td>{person.full_name}</td>
                <td>{person.branch_name}</td>
                <td>{faNumber.format(person.experience_years)} سال</td>
                <td>{person.bio || "—"}</td>
                <td>{person.is_active ? "فعال" : "غیرفعال"}</td>
              </tr>
            ))}
          </DataTable>
        )}
        {tab === "reviews" && (
          <DataTable
            headers={["مشتری", "پرسنل", "امتیاز", "نظر", "تاریخ", "وضعیت"]}
          >
            {data.reviews.map((review) => (
              <tr key={review.id}>
                <td>{review.customer_name}</td>
                <td>{review.staff_name || "—"}</td>
                <td>{faNumber.format(review.overall_rating)} از ۵</td>
                <td>{review.comment}</td>
                <td>{formatPersianDateTime(review.created_at)}</td>
                <td>
                  <StatusBadge
                    status={review.status}
                    label={review.status_label}
                  />
                </td>
              </tr>
            ))}
          </DataTable>
        )}
        {tab === "discounts" && (
          <DataTable
            headers={[
              "کد",
              "نوع",
              "مقدار",
              "استفاده",
              "شروع",
              "پایان",
              "وضعیت",
            ]}
          >
            {data.discounts.map((discount) => (
              <tr key={discount.id}>
                <td dir="ltr">{discount.code}</td>
                <td>{discount.type_label}</td>
                <td>
                  {discount.type === "percent"
                    ? `${faNumber.format(discount.value)}٪`
                    : toman(discount.value)}
                </td>
                <td>{faNumber.format(discount.used_count)}</td>
                <td>{formatPersianDateTime(discount.starts_at)}</td>
                <td>{formatPersianDateTime(discount.ends_at)}</td>
                <td>{discount.is_active ? "فعال" : "غیرفعال"}</td>
              </tr>
            ))}
          </DataTable>
        )}
      </section>
    </AdminLayout>
  );
}

function DataTable({
  headers,
  children,
}: {
  headers: string[];
  children: React.ReactNode;
}) {
  return (
    <div className="admin-table-wrap admin-overview-table">
      <table className="admin-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
