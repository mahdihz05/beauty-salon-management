import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, CheckCircle2, LoaderCircle, Plus, Tags } from "lucide-react";
import { useState } from "react";
import { api, getApiError } from "../../api/client";
import { JalaliDateTimePicker } from "../../components/JalaliDatePicker";
import { SalonLayout } from "../../components/SalonLayout";
import {
  formatPersianDateTime,
  localDateTimeInput,
  localIsoDate,
} from "../../lib/date";
import { faNumber, toman } from "../../lib/format";
import type { DiscountCode, NotificationLog } from "../../types/booking";
import type { Paginated, Salon } from "../../types/salon";

export function PromotionsPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    code: "",
    type: "percent",
    value: 10,
    starts_at: localDateTimeInput(new Date()),
    ends_at: localDateTimeInput(new Date(Date.now() + 30 * 86_400_000)),
  });
  const salons = useQuery({
    queryKey: ["salon", "owned"],
    queryFn: async () =>
      (await api.get<Paginated<Salon>>("/management/salons/")).data,
  });
  const discounts = useQuery({
    queryKey: ["salon", "discounts"],
    queryFn: async () =>
      (await api.get<Paginated<DiscountCode>>("/bookings/discounts/")).data,
  });
  const logs = useQuery({
    queryKey: ["salon", "notifications"],
    queryFn: async () =>
      (
        await api.get<Paginated<NotificationLog>>(
          "/notifications/logs/?ordering=-created_at",
        )
      ).data,
  });
  const create = useMutation({
    mutationFn: () =>
      api.post("/bookings/discounts/", {
        ...form,
        salon: salons.data?.results[0]?.id,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
      }),
    async onSuccess() {
      setShowForm(false);
      await queryClient.invalidateQueries({ queryKey: ["salon", "discounts"] });
    },
  });
  return (
    <SalonLayout
      title="تخفیف و اطلاع‌رسانی"
      description="مدیریت کمپین‌ها و تاریخچه پیام‌های رزرو"
      action={
        <button
          className="button button-primary"
          onClick={() => setShowForm(!showForm)}
        >
          <Plus /> کد جدید
        </button>
      }
    >
      {showForm && (
        <form
          className="promotion-form"
          onSubmit={(event) => {
            event.preventDefault();
            create.mutate();
          }}
        >
          <label>
            کد
            <input
              required
              dir="ltr"
              value={form.code}
              onChange={(event) =>
                setForm({ ...form, code: event.target.value.toUpperCase() })
              }
            />
          </label>
          <label>
            نوع
            <select
              value={form.type}
              onChange={(event) =>
                setForm({ ...form, type: event.target.value })
              }
            >
              <option value="percent">درصدی</option>
              <option value="fixed">مبلغ ثابت</option>
            </select>
          </label>
          <label>
            مقدار
            <input
              required
              min={1}
              type="number"
              value={form.value}
              onChange={(event) =>
                setForm({ ...form, value: Number(event.target.value) })
              }
            />
          </label>
          <label className="jalali-field-label">
            شروع
            <JalaliDateTimePicker
              value={form.starts_at}
              min={`${localIsoDate()}T00:00`}
              required
              onChange={(starts_at) => setForm({ ...form, starts_at })}
            />
          </label>
          <label className="jalali-field-label">
            پایان
            <JalaliDateTimePicker
              value={form.ends_at}
              min={form.starts_at}
              required
              onChange={(ends_at) => setForm({ ...form, ends_at })}
            />
          </label>
          <button className="button button-primary" disabled={create.isPending}>
            {create.isPending && <LoaderCircle className="spin" />} ذخیره کد
          </button>
        </form>
      )}
      {create.isError && (
        <p className="alert alert-error">{getApiError(create.error)}</p>
      )}
      <div className="promotion-layout">
        <section className="panel-card">
          <h2>
            <Tags /> کدهای تخفیف
          </h2>
          <div className="discount-list">
            {discounts.data?.results.map((item) => (
              <article key={item.id}>
                <div>
                  <strong dir="ltr">{item.code}</strong>
                  <span>
                    {item.type === "percent"
                      ? `${faNumber.format(item.value)}٪`
                      : toman(item.value)}
                  </span>
                </div>
                <small>
                  {item.salon_name} · {faNumber.format(item.used_count)} بار
                  استفاده
                </small>
                <small>
                  اعتبار: {formatPersianDateTime(item.starts_at)} تا{" "}
                  {formatPersianDateTime(item.ends_at)}
                </small>
              </article>
            ))}
          </div>
        </section>
        <section className="panel-card">
          <h2>
            <BellRing /> تاریخچه پیامک
          </h2>
          <div className="notification-list">
            {logs.data?.results.map((item) => (
              <article key={item.id}>
                <CheckCircle2 />
                <div>
                  <strong>
                    {item.event_label} ·{" "}
                    {item.customer_name || item.customer_phone}
                  </strong>
                  <p>{item.message}</p>
                  <small>{formatPersianDateTime(item.created_at)}</small>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </SalonLayout>
  );
}
