import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarDays, Clock3, LoaderCircle, UserRound } from "lucide-react";
import { useMemo, useState } from "react";
import { useLocation, useRoute } from "wouter";
import { api, getApiError } from "../../api/client";
import { useAuth } from "../../auth/useAuth";
import { BookingShell } from "../../components/BookingShell";
import { JalaliDatePicker } from "../../components/JalaliDatePicker";
import { bookingDraft } from "../../lib/booking-draft";
import {
  dateFromIso,
  formatPersianDate,
  formatPersianTime,
  localIsoDate,
  toLocalIsoDate,
} from "../../lib/date";
import { faNumber, toman } from "../../lib/format";
import type { AvailableSlot, Booking } from "../../types/booking";
import type { PublicBranch } from "../../types/public";

function isoDate(date: Date) {
  return toLocalIsoDate(date);
}
function faDate(date: Date) {
  return formatPersianDate(date, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function DateTimeSelectionPage() {
  const [, params] = useRoute("/booking/:branchId/datetime");
  const [, navigate] = useLocation();
  const { user } = useAuth();
  const branchId = Number(params?.branchId);
  const draft = bookingDraft.get();
  const dates = useMemo(
    () =>
      Array.from({ length: 10 }, (_, index) => {
        const date = new Date();
        date.setDate(date.getDate() + index + 1);
        return date;
      }),
    [],
  );
  const [date, setDate] = useState(dates[0]);
  const [staff, setStaff] = useState<number | "">(draft?.slot?.staff_id || "");
  const [selected, setSelected] = useState<AvailableSlot | null>(
    draft?.slot || null,
  );
  const branch = useQuery({
    queryKey: ["public", "branch", branchId],
    queryFn: async () =>
      (await api.get<PublicBranch>(`/public/branches/${branchId}/`)).data,
  });
  const serviceIds = draft?.branchId === branchId ? draft.serviceIds : [];
  const paramsQuery = new URLSearchParams({
    branch: String(branchId),
    services: serviceIds.join(","),
    date: isoDate(date),
  });
  if (staff) paramsQuery.set("staff", String(staff));
  const slots = useQuery({
    queryKey: ["availability", paramsQuery.toString()],
    enabled: serviceIds.length > 0,
    queryFn: async () =>
      (await api.get<AvailableSlot[]>(`/bookings/availability/?${paramsQuery}`))
        .data,
  });
  const hold = useMutation({
    mutationFn: async (slot: AvailableSlot) =>
      (
        await api.post<Booking>("/bookings/holds/", {
          branch: branchId,
          service_ids: serviceIds,
          staff_id: slot.staff_id,
          start_at: slot.start_at,
        })
      ).data,
    onSuccess(booking) {
      navigate(`/booking/checkout?booking=${booking.id}`);
    },
  });
  function continueBooking() {
    if (!selected) return;
    bookingDraft.set({ branchId, serviceIds, slot: selected });
    if (!user) {
      navigate(
        `/login?next=${encodeURIComponent(`/booking/${branchId}/datetime`)}`,
      );
      return;
    }
    hold.mutate(selected);
  }

  if (!serviceIds.length) {
    navigate(`/booking/${branchId}/services`);
    return null;
  }
  return (
    <BookingShell step={2} backHref={`/booking/${branchId}/services`}>
      <main className="booking-main container">
        <div className="booking-heading">
          <p>مرحله دوم از سه</p>
          <h1>انتخاب تاریخ و زمان</h1>
          <span>{branch.data?.name}</span>
        </div>
        <div className="booking-layout">
          <section className="datetime-card">
            <h2>
              <CalendarDays /> تاریخ مراجعه
            </h2>
            <div className="date-strip">
              {dates.map((item) => (
                <button
                  className={isoDate(item) === isoDate(date) ? "selected" : ""}
                  onClick={() => {
                    setDate(item);
                    setSelected(null);
                  }}
                  key={isoDate(item)}
                >
                  {faDate(item)}
                </button>
              ))}
            </div>
            <div className="booking-date-picker">
              <span>یا انتخاب از تقویم هجری شمسی</span>
              <JalaliDatePicker
                value={isoDate(date)}
                min={localIsoDate(1)}
                ariaLabel="انتخاب تاریخ شمسی مراجعه"
                onChange={(value) => {
                  setDate(dateFromIso(value));
                  setSelected(null);
                }}
              />
            </div>
            <div className="staff-select">
              <UserRound />
              <label>
                انتخاب آرایشگر
                <select
                  value={staff}
                  onChange={(event) => {
                    setStaff(
                      event.target.value ? Number(event.target.value) : "",
                    );
                    setSelected(null);
                  }}
                >
                  <option value="">هر آرایشگر آزاد</option>
                  {branch.data?.staff.map((person) => (
                    <option value={person.id} key={person.id}>
                      {person.full_name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <h2>
              <Clock3 /> ساعت‌های آزاد
            </h2>
            {slots.isError && (
              <p className="alert alert-error">{getApiError(slots.error)}</p>
            )}
            <div className="time-grid">
              {slots.isLoading ? (
                <LoaderCircle className="spin" />
              ) : (
                slots.data?.map((slot) => (
                  <button
                    className={
                      selected?.start_at === slot.start_at &&
                      selected.staff_id === slot.staff_id
                        ? "selected"
                        : ""
                    }
                    onClick={() => setSelected(slot)}
                    key={`${slot.start_at}-${slot.staff_id}`}
                  >
                    <strong>{formatPersianTime(slot.start_at)}</strong>
                    <small>{slot.staff_name}</small>
                  </button>
                ))
              )}
            </div>
            {!slots.isLoading && slots.data?.length === 0 && (
              <div className="summary-empty">
                <Clock3 />
                <p>در این روز زمان آزادی وجود ندارد.</p>
              </div>
            )}
          </section>
          <aside className="booking-summary">
            <h2>زمان انتخابی</h2>
            {selected ? (
              <div className="selected-slot-summary">
                <p>
                  <CalendarDays /> {faDate(date)}
                </p>
                <p>
                  <Clock3 /> ساعت {formatPersianTime(selected.start_at)}
                </p>
                <p>
                  <UserRound /> {selected.staff_name}
                </p>
                <span>{faNumber.format(selected.duration_minutes)} دقیقه</span>
                <strong>{toman(selected.total_price)}</strong>
              </div>
            ) : (
              <div className="summary-empty">
                <Clock3 />
                <p>یک ساعت آزاد انتخاب کنید.</p>
              </div>
            )}
            {hold.isError && (
              <p className="alert alert-error">{getApiError(hold.error)}</p>
            )}
            <button
              className="button button-primary"
              disabled={!selected || hold.isPending}
              onClick={continueBooking}
            >
              {hold.isPending && <LoaderCircle className="spin" size={18} />}{" "}
              ادامه و ثبت موقت
            </button>
            <small className="hold-note">
              پس از انتخاب، زمان به مدت ۱۰ دقیقه برای شما نگه داشته می‌شود.
            </small>
          </aside>
        </div>
      </main>
    </BookingShell>
  );
}
