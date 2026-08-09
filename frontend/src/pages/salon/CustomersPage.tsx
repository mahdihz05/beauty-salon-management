import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Search, UserRound } from "lucide-react";
import { useState } from "react";
import { api, getApiError } from "../../api/client";
import { SalonLayout } from "../../components/SalonLayout";
import { formatPersianDate } from "../../lib/date";
import { faNumber, toman } from "../../lib/format";
import type { CustomerSummary } from "../../types/booking";
import type { Paginated } from "../../types/salon";

export function CustomersPage() {
  const [search, setSearch] = useState("");
  const customers = useQuery({
    queryKey: ["salon", "customers", search],
    queryFn: async () =>
      (
        await api.get<Paginated<CustomerSummary>>(
          `/bookings/customers/?ordering=-last_booking_at&search=${encodeURIComponent(search)}`,
        )
      ).data,
  });
  return (
    <SalonLayout
      title="مشتریان"
      description="سوابق مراجعه و ارزش خرید مشتریان سالن"
    >
      <div className="admin-toolbar">
        <div className="search-box">
          <Search />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="نام یا شماره موبایل"
          />
        </div>
      </div>
      {customers.isError && (
        <p className="alert alert-error">{getApiError(customers.error)}</p>
      )}
      <section className="customer-management-grid">
        {customers.data?.results.map((customer) => (
          <article key={customer.id}>
            <span className="customer-avatar">
              <UserRound />
            </span>
            <div>
              <h2>{customer.name || "مشتری بدون نام"}</h2>
              <p dir="ltr">{customer.phone}</p>
            </div>
            <dl>
              <div>
                <dt>تعداد نوبت</dt>
                <dd>{faNumber.format(customer.booking_count)}</dd>
              </div>
              <div>
                <dt>خرید ثبت‌شده</dt>
                <dd>{toman(customer.total_spent)}</dd>
              </div>
            </dl>
            <small>
              <CalendarDays /> آخرین نوبت:{" "}
              {customer.last_booking_at
                ? formatPersianDate(customer.last_booking_at, {
                    dateStyle: "medium",
                  })
                : "—"}
            </small>
          </article>
        ))}
      </section>
    </SalonLayout>
  );
}
