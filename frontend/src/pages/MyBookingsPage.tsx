import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  Clock3,
  LoaderCircle,
  MapPin,
  Star,
  UserRound,
  WalletCards,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { api, getApiError } from "../api/client";
import { MobileBottomNav, PublicHeader } from "../components/PublicHeader";
import { formatPersianDate, formatPersianTime } from "../lib/date";
import { faNumber, toman } from "../lib/format";
import type { Booking, Review, Wallet } from "../types/booking";
import type { Paginated } from "../types/salon";

type Tab = "upcoming" | "past" | "cancelled";

const statusLabel: Record<Booking["status"], string> = {
  pending_payment: "در انتظار پرداخت",
  awaiting_verification: "در انتظار تأیید واریز",
  confirmed: "تأییدشده",
  completed: "انجام‌شده",
  cancelled: "لغوشده",
  no_show: "عدم حضور",
};

function ReviewForm({ bookingId }: { bookingId: number }) {
  const queryClient = useQueryClient();
  const [ratings, setRatings] = useState({
    overall: 5,
    quality: 5,
    cleanliness: 5,
    behavior: 5,
    value: 5,
  });
  const [comment, setComment] = useState("");
  const mutation = useMutation({
    mutationFn: async () =>
      (
        await api.post<Review>("/reviews/mine/", {
          booking: bookingId,
          overall_rating: ratings.overall,
          quality_rating: ratings.quality,
          cleanliness_rating: ratings.cleanliness,
          behavior_rating: ratings.behavior,
          value_rating: ratings.value,
          comment,
        })
      ).data,
    async onSuccess() {
      await queryClient.invalidateQueries({ queryKey: ["my-reviews"] });
    },
  });
  if (mutation.isSuccess)
    return (
      <p className="alert alert-success">
        نظر شما ثبت شد و پس از بررسی منتشر می‌شود.
      </p>
    );
  return (
    <form
      className="booking-review-form"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <h4>
        <Star /> ثبت تجربه شما
      </h4>
      <div className="rating-fields">
        {[
          ["overall", "امتیاز کلی"],
          ["quality", "کیفیت خدمات"],
          ["cleanliness", "پاکیزگی"],
          ["behavior", "رفتار پرسنل"],
          ["value", "ارزش در برابر هزینه"],
        ].map(([key, label]) => (
          <label key={key}>
            {label}
            <select
              value={ratings[key as keyof typeof ratings]}
              onChange={(event) =>
                setRatings({ ...ratings, [key]: Number(event.target.value) })
              }
            >
              {[5, 4, 3, 2, 1].map((value) => (
                <option value={value} key={value}>
                  {faNumber.format(value)} ستاره
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      <textarea
        required
        minLength={3}
        maxLength={2000}
        rows={3}
        placeholder="تجربه خود را بنویسید..."
        value={comment}
        onChange={(event) => setComment(event.target.value)}
      />
      {mutation.isError && (
        <p className="alert alert-error">{getApiError(mutation.error)}</p>
      )}
      <button className="button button-primary" disabled={mutation.isPending}>
        {mutation.isPending && <LoaderCircle className="spin" size={17} />} ثبت
        نظر
      </button>
    </form>
  );
}

export function MyBookingsPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("upcoming");
  const [notice, setNotice] = useState("");
  const bookings = useQuery({
    queryKey: ["my-bookings"],
    queryFn: async () =>
      (await api.get<Paginated<Booking>>("/bookings/items/?ordering=-start_at"))
        .data,
  });
  const reviews = useQuery({
    queryKey: ["my-reviews"],
    queryFn: async () =>
      (await api.get<Paginated<Review>>("/reviews/mine/")).data,
  });
  const wallet = useQuery({
    queryKey: ["wallet"],
    queryFn: async () => (await api.get<Wallet>("/payments/wallet/")).data,
  });
  const cancel = useMutation({
    mutationFn: async (id: number) =>
      (
        await api.post<Booking>(`/bookings/items/${id}/cancel/`, {
          reason: "لغو توسط مشتری",
        })
      ).data,
    async onSuccess(result) {
      setNotice(
        result.refund_amount
          ? `${toman(result.refund_amount)} به کیف پول شما بازگشت.`
          : "رزرو با موفقیت لغو شد.",
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["my-bookings"] }),
        queryClient.invalidateQueries({ queryKey: ["wallet"] }),
      ]);
    },
  });
  const filtered = useMemo(
    () =>
      (bookings.data?.results || []).filter((booking) => {
        if (tab === "upcoming")
          return [
            "pending_payment",
            "awaiting_verification",
            "confirmed",
          ].includes(booking.status);
        if (tab === "cancelled") return booking.status === "cancelled";
        return ["completed", "no_show"].includes(booking.status);
      }),
    [bookings.data, tab],
  );
  const reviewedIds = new Set(
    reviews.data?.results.map((review) => review.booking),
  );

  return (
    <div className="customer-page">
      <PublicHeader />
      <main className="my-bookings container">
        <div className="page-heading customer-heading">
          <div>
            <p className="eyebrow">حساب کاربری</p>
            <h1>رزروهای من</h1>
          </div>
          <div className="wallet-pill">
            <WalletCards />
            <span>موجودی کیف پول</span>
            <strong>{toman(wallet.data?.balance || 0)}</strong>
          </div>
        </div>
        <nav className="booking-tabs">
          <button
            className={tab === "upcoming" ? "active" : ""}
            onClick={() => setTab("upcoming")}
          >
            پیش‌رو
          </button>
          <button
            className={tab === "past" ? "active" : ""}
            onClick={() => setTab("past")}
          >
            گذشته
          </button>
          <button
            className={tab === "cancelled" ? "active" : ""}
            onClick={() => setTab("cancelled")}
          >
            لغوشده
          </button>
        </nav>
        {notice && <p className="alert alert-success">{notice}</p>}
        {(bookings.isError || cancel.isError) && (
          <p className="alert alert-error">
            {getApiError(bookings.error || cancel.error)}
          </p>
        )}
        <section className="customer-booking-list">
          {filtered.map((booking) => (
            <article className="customer-booking-card" key={booking.id}>
              <div className="booking-card-top">
                <div>
                  <h2>{booking.salon_name}</h2>
                  <span>{booking.branch_name}</span>
                </div>
                <b className={`booking-status status-${booking.status}`}>
                  {statusLabel[booking.status]}
                </b>
              </div>
              <div className="booking-meta-grid">
                <p>
                  <CalendarDays />
                  {formatPersianDate(booking.start_at, {
                    dateStyle: "long",
                  })}
                </p>
                <p>
                  <Clock3 />
                  {formatPersianTime(booking.start_at)}
                </p>
                <p>
                  <UserRound />
                  {booking.staff_name}
                </p>
                <p>
                  <MapPin />
                  {booking.items.map((item) => item.service_name).join("، ")}
                </p>
              </div>
              <div className="booking-card-bottom">
                <strong>{toman(booking.total_price)}</strong>
                {[
                  "pending_payment",
                  "awaiting_verification",
                  "confirmed",
                ].includes(booking.status) &&
                  new Date(booking.start_at).getTime() - Date.now() >=
                    24 * 60 * 60 * 1000 && (
                    <button
                      className="button reject-button"
                      disabled={cancel.isPending}
                      onClick={() => {
                        if (window.confirm("از لغو این نوبت مطمئن هستید؟"))
                          cancel.mutate(booking.id);
                      }}
                    >
                      <XCircle size={17} /> لغو نوبت
                    </button>
                  )}
              </div>
              {booking.status === "cancelled" &&
                booking.cancellation_reason && (
                  <small className="cancel-reason">
                    علت لغو: {booking.cancellation_reason}
                  </small>
                )}
              {booking.status === "completed" &&
                !reviewedIds.has(booking.id) && (
                  <ReviewForm bookingId={booking.id} />
                )}
              {reviewedIds.has(booking.id) && (
                <p className="reviewed-note">
                  <Star /> نظر شما برای این نوبت ثبت شده است.
                </p>
              )}
            </article>
          ))}
          {!bookings.isLoading && filtered.length === 0 && (
            <div className="summary-empty">
              <CalendarDays />
              <p>رزروی در این بخش ندارید.</p>
            </div>
          )}
        </section>
      </main>
      <MobileBottomNav />
    </div>
  );
}
