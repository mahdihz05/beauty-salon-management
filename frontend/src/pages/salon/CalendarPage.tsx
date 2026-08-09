import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  MoreHorizontal,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { api, getApiError } from "../../api/client";
import { useAuth } from "../../auth/useAuth";
import { JalaliDatePicker } from "../../components/JalaliDatePicker";
import { SalonLayout } from "../../components/SalonLayout";
import { StatusBadge } from "../../components/StatusBadge";
import {
  formatPersianDate,
  formatPersianDateTime,
  formatPersianTime,
  localIsoDate,
} from "../../lib/date";
import { faNumber, toman } from "../../lib/format";
import type { AvailableSlot, Booking } from "../../types/booking";
import type {
  Branch,
  BranchService,
  Paginated,
  Staff,
} from "../../types/salon";

export function CalendarPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showManual, setShowManual] = useState(false);
  const [manualForm, setManualForm] = useState({
    branch: "",
    service: "",
    staff: "",
    customer_phone: "",
    customer_name: "",
    date: localIsoDate(1),
    start_at: "",
  });
  const todayIso = localIsoDate();
  const bookings = useQuery({
    queryKey: ["salon", "bookings", todayIso],
    queryFn: async () =>
      (
        await api.get<Paginated<Booking>>(
          `/bookings/items/?start_date=${todayIso}&end_date=${todayIso}&ordering=start_at`,
        )
      ).data,
  });
  const branches = useQuery({
    queryKey: ["management", "branches"],
    queryFn: async () =>
      (await api.get<Paginated<Branch>>("/management/branches/")).data,
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
  const availabilityQuery = new URLSearchParams({
    branch: manualForm.branch,
    services: manualForm.service,
    date: manualForm.date,
  });
  if (manualForm.staff) availabilityQuery.set("staff", manualForm.staff);
  const manualSlots = useQuery({
    queryKey: ["manual-booking-slots", availabilityQuery.toString()],
    enabled: Boolean(
      manualForm.branch && manualForm.service && manualForm.date,
    ),
    queryFn: async () =>
      (
        await api.get<AvailableSlot[]>(
          `/bookings/availability/?${availabilityQuery}`,
        )
      ).data,
  });
  const selectedManualSlot = manualSlots.data?.find(
    (slot) => `${slot.start_at}|${slot.staff_id}` === manualForm.start_at,
  );
  const manualMutation = useMutation({
    mutationFn: async () =>
      api.post("/bookings/manual/", {
        branch: Number(manualForm.branch),
        service_ids: [Number(manualForm.service)],
        staff_id: selectedManualSlot?.staff_id,
        customer_phone: manualForm.customer_phone,
        customer_name: manualForm.customer_name,
        start_at: selectedManualSlot?.start_at,
      }),
    async onSuccess() {
      setShowManual(false);
      setManualForm({
        branch: "",
        service: "",
        staff: "",
        customer_phone: "",
        customer_name: "",
        date: localIsoDate(1),
        start_at: "",
      });
      await queryClient.invalidateQueries({ queryKey: ["salon", "bookings"] });
    },
  });
  const statusMutation = useMutation({
    mutationFn: async ({
      booking,
      status,
    }: {
      booking: Booking;
      status: string;
    }) => {
      if (status === "completed" && booking.remaining_amount > 0) {
        await api.post("/payments/remainder/", {
          booking: booking.id,
          method: "cash",
        });
      }
      return api.post(`/bookings/items/${booking.id}/set-status/`, { status });
    },
    async onSuccess() {
      await queryClient.invalidateQueries({ queryKey: ["salon", "bookings"] });
    },
  });
  const todayCount = bookings.data?.count ?? 0;

  return (
    <SalonLayout
      title="تقویم نوبت‌ها"
      description={`${faNumber.format(todayCount)} نوبت برای امروز`}
      action={
        user?.role !== "staff" ? (
          <button
            className="button button-primary manual-booking-toggle"
            onClick={() => setShowManual((value) => !value)}
          >
            <CalendarDays size={18} /> ثبت نوبت حضوری
          </button>
        ) : undefined
      }
    >
      {(bookings.isError ||
        statusMutation.isError ||
        manualMutation.isError ||
        manualSlots.isError) && (
        <p className="alert alert-error">
          {getApiError(
            bookings.error ||
              statusMutation.error ||
              manualMutation.error ||
              manualSlots.error,
          )}
        </p>
      )}
      {manualMutation.isSuccess && (
        <p className="alert alert-success">نوبت حضوری با موفقیت ثبت شد.</p>
      )}
      {showManual && (
        <form
          className="checkout-card manual-booking-form"
          onSubmit={(event) => {
            event.preventDefault();
            manualMutation.mutate();
          }}
        >
          <div className="manual-form-heading">
            <span>
              <CalendarDays />
            </span>
            <div>
              <h2>اطلاعات نوبت حضوری</h2>
              <p>مشخصات مشتری، خدمت و زمان مراجعه را کامل کنید.</p>
            </div>
          </div>
          <label>
            شعبه
            <select
              required
              value={manualForm.branch}
              onChange={(event) =>
                setManualForm({
                  ...manualForm,
                  branch: event.target.value,
                  service: "",
                  staff: "",
                  start_at: "",
                })
              }
            >
              <option value="">انتخاب شعبه</option>
              {branches.data?.results.map((branch) => (
                <option value={branch.id} key={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            خدمت
            <select
              required
              value={manualForm.service}
              onChange={(event) =>
                setManualForm({
                  ...manualForm,
                  service: event.target.value,
                  start_at: "",
                })
              }
            >
              <option value="">انتخاب خدمت</option>
              {services.data?.results
                .filter((item) => item.branch === Number(manualForm.branch))
                .map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.service_name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            آرایشگر
            <select
              value={manualForm.staff}
              onChange={(event) =>
                setManualForm({
                  ...manualForm,
                  staff: event.target.value,
                  start_at: "",
                })
              }
            >
              <option value="">هر آرایشگر آزاد</option>
              {staff.data?.results
                .filter((item) => item.branch === Number(manualForm.branch))
                .map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.full_name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            شماره مشتری
            <input
              required
              inputMode="numeric"
              pattern="09[0-9]{9}"
              placeholder="09123456789"
              value={manualForm.customer_phone}
              onChange={(event) =>
                setManualForm({
                  ...manualForm,
                  customer_phone: event.target.value,
                })
              }
            />
          </label>
          <label>
            نام مشتری
            <input
              value={manualForm.customer_name}
              onChange={(event) =>
                setManualForm({
                  ...manualForm,
                  customer_name: event.target.value,
                })
              }
            />
          </label>
          <label className="jalali-field-label">
            تاریخ مراجعه
            <JalaliDatePicker
              min={localIsoDate(0)}
              value={manualForm.date}
              required
              ariaLabel="انتخاب تاریخ شمسی مراجعه"
              onChange={(date) =>
                setManualForm({
                  ...manualForm,
                  date,
                  start_at: "",
                })
              }
            />
          </label>
          <label>
            ساعت آزاد
            <select
              required
              disabled={!manualSlots.data || manualSlots.isLoading}
              value={manualForm.start_at}
              onChange={(event) =>
                setManualForm({
                  ...manualForm,
                  start_at: event.target.value,
                })
              }
            >
              <option value="">
                {manualSlots.isLoading
                  ? "در حال دریافت زمان‌ها..."
                  : manualSlots.data?.length
                    ? "انتخاب ساعت آزاد"
                    : "زمان آزادی یافت نشد"}
              </option>
              {manualSlots.data?.map((slot) => (
                <option
                  value={`${slot.start_at}|${slot.staff_id}`}
                  key={`${slot.start_at}-${slot.staff_id}`}
                >
                  {formatPersianTime(slot.start_at)} — {slot.staff_name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button button-primary manual-submit"
            disabled={manualMutation.isPending || !selectedManualSlot}
          >
            <CheckCircle2 size={18} /> ثبت نوبت حضوری
          </button>
        </form>
      )}
      <section className="calendar-board">
        <div className="calendar-day-head">
          <div>
            <span>امروز</span>
            <strong>
              {formatPersianDate(new Date(), {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </strong>
          </div>
          <div>
            <Clock3 /> ساعت کاری ۹ تا ۲۰
          </div>
        </div>
        <div className="appointment-list">
          {bookings.data?.results.map((booking) => (
            <article className="appointment-card" key={booking.id}>
              <time>{formatPersianTime(booking.start_at)}</time>
              <span className="appointment-line" />
              <div className="appointment-main">
                <div className="appointment-title">
                  <h3>
                    {booking.items.map((item) => item.service_name).join("، ")}
                  </h3>
                  <StatusBadge
                    status={
                      booking.status === "confirmed"
                        ? "approved"
                        : booking.status
                    }
                    label={booking.status_label}
                  />
                </div>
                <p>
                  <UserRound size={15} /> {booking.staff_name} ·{" "}
                  {booking.salon_name}
                </p>
                <small>
                  {formatPersianDateTime(booking.start_at)} ·{" "}
                  {toman(booking.total_price)}
                </small>
              </div>
              <div className="appointment-actions">
                {booking.status === "confirmed" && (
                  <button
                    title="ثبت انجام خدمت"
                    onClick={() =>
                      statusMutation.mutate({
                        booking,
                        status: "completed",
                      })
                    }
                  >
                    <CheckCircle2 />
                  </button>
                )}
                <button title="بیشتر">
                  <MoreHorizontal />
                </button>
              </div>
            </article>
          ))}
          {!bookings.isLoading && bookings.data?.count === 0 && (
            <div className="panel-empty">
              <CalendarDays />
              <h2>نوبتی ثبت نشده است</h2>
              <p>نوبت‌های آنلاین و حضوری در این تقویم نمایش داده می‌شوند.</p>
            </div>
          )}
        </div>
      </section>
    </SalonLayout>
  );
}
