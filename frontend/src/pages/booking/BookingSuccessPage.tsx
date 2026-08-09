import { useQuery } from "@tanstack/react-query";
import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  MapPin,
  UserRound,
} from "lucide-react";
import { Link, useRoute } from "wouter";
import { api, getApiError } from "../../api/client";
import { BookingShell } from "../../components/BookingShell";
import { formatPersianDate, formatPersianTime } from "../../lib/date";
import { toman } from "../../lib/format";
import type { Booking } from "../../types/booking";

export function BookingSuccessPage() {
  const [, params] = useRoute("/booking/success/:bookingId");
  const id = params?.bookingId;
  const booking = useQuery({
    queryKey: ["booking", id],
    enabled: Boolean(id),
    queryFn: async () =>
      (await api.get<Booking>(`/bookings/items/${id}/`)).data,
  });

  return (
    <BookingShell step={3} backHref="/">
      <main className="booking-main narrow container">
        {booking.isError && (
          <p className="alert alert-error">{getApiError(booking.error)}</p>
        )}
        {booking.data && (
          <section className="booking-success">
            <CheckCircle2 />
            <p>رزرو با موفقیت انجام شد</p>
            <h1>نوبت شما قطعی شد!</h1>
            <span>
              کد پیگیری رزرو: ST-{String(booking.data.id).padStart(6, "0")}
            </span>
            <div className="success-ticket">
              <h2>{booking.data.salon_name}</h2>
              <p>
                <CalendarDays />
                {formatPersianDate(booking.data.start_at, {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>
              <p>
                <Clock3 /> ساعت {formatPersianTime(booking.data.start_at)}
              </p>
              <p>
                <UserRound /> {booking.data.staff_name}
              </p>
              <p>
                <MapPin /> {booking.data.branch_name}
              </p>
              <ul>
                {booking.data.items.map((item) => (
                  <li key={item.id}>
                    <span>{item.service_name}</span>
                    <strong>{toman(item.price)}</strong>
                  </li>
                ))}
              </ul>
            </div>
            <div className="success-actions">
              <Link className="button button-primary" href="/account/bookings">
                مشاهده رزروهای من
              </Link>
              <Link className="button button-secondary" href="/">
                بازگشت به صفحه اصلی
              </Link>
            </div>
          </section>
        )}
      </main>
    </BookingShell>
  );
}
