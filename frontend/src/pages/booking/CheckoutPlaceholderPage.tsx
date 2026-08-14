import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CalendarDays,
  Clock3,
  CreditCard,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useLocation } from "wouter";
import { api, getApiError } from "../../api/client";
import { BookingShell } from "../../components/BookingShell";
import { bookingDraft } from "../../lib/booking-draft";
import { formatPersianDateTime, formatPersianTime } from "../../lib/date";
import { toman } from "../../lib/format";
import type { Booking, Payment } from "../../types/booking";

export function CheckoutPlaceholderPage() {
  const [, navigate] = useLocation();
  const id = new URLSearchParams(window.location.search).get("booking");
  const [paymentType, setPaymentType] = useState<"deposit" | "full">("deposit");
  const [paymentMethod, setPaymentMethod] = useState<
    "in_person" | "card_to_card"
  >("in_person");
  const [trackingCode, setTrackingCode] = useState("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [discountCode, setDiscountCode] = useState("");
  const booking = useQuery({
    queryKey: ["booking", id],
    enabled: Boolean(id),
    queryFn: async () =>
      (await api.get<Booking>(`/bookings/items/${id}/`)).data,
  });
  const payment = useMutation({
    mutationFn: async () => {
      const formData = new FormData();
      formData.set("booking", String(Number(id)));
      formData.set("type", paymentType);
      formData.set("method", paymentMethod);
      formData.set("discount_code", discountCode);
      if (trackingCode) formData.set("tracking_code", trackingCode);
      if (receipt) formData.set("receipt", receipt);
      return (await api.post<Payment>("/payments/submit/", formData)).data;
    },
    onSuccess(result) {
      bookingDraft.clear();
      navigate(`/booking/success/${result.booking}?payment=${result.id}`);
    },
  });

  return (
    <BookingShell
      step={3}
      backHref={booking.data ? `/booking/${booking.data.branch}/datetime` : "/"}
    >
      <main className="booking-main container checkout-page">
        <div className="booking-heading">
          <p>مرحله سوم از سه</p>
          <h1>تأیید نهایی و پرداخت امن</h1>
          <span>جزئیات نوبت را بررسی و روش پرداخت را انتخاب کنید.</span>
        </div>
        {!id && <p className="alert alert-error">شناسه رزرو ارسال نشده است.</p>}
        {booking.isError && (
          <p className="alert alert-error">{getApiError(booking.error)}</p>
        )}
        {booking.data && (
          <div className="checkout-layout">
            <section className="checkout-details">
              <div className="hold-banner">
                <ShieldCheck />
                <div>
                  <strong>زمان رزرو برای شما نگه داشته شده است</strong>
                  <span>
                    مهلت پرداخت تا ساعت{" "}
                    {formatPersianTime(booking.data.hold_expires_at || "")}
                  </span>
                </div>
              </div>
              <div className="checkout-card">
                <h2>جزئیات نوبت</h2>
                <p>
                  <CalendarDays />
                  {formatPersianDateTime(booking.data.start_at)}
                </p>
                <p>
                  <UserRound /> {booking.data.staff_name}
                </p>
                <p>
                  <Clock3 /> {booking.data.salon_name}،{" "}
                  {booking.data.branch_name}
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
              <div className="checkout-card">
                <h2>روش پرداخت</h2>
                <label
                  className={`payment-option ${paymentMethod === "in_person" ? "selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="payment-method"
                    checked={paymentMethod === "in_person"}
                    onChange={() => setPaymentMethod("in_person")}
                  />
                  <span>
                    <strong>پرداخت حضوری</strong>
                    <small>مبلغ در زمان مراجعه به سالن پرداخت می‌شود.</small>
                  </span>
                </label>
                <label
                  className={`payment-option ${paymentMethod === "card_to_card" ? "selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="payment-method"
                    checked={paymentMethod === "card_to_card"}
                    onChange={() => setPaymentMethod("card_to_card")}
                  />
                  <span>
                    <strong>کارت‌به‌کارت</strong>
                    <small>رسید برای مدیر سالن ارسال و بررسی می‌شود.</small>
                  </span>
                </label>
                {paymentMethod === "card_to_card" && (
                  <div className="form-grid">
                    <label>
                      کد پیگیری
                      <input
                        dir="ltr"
                        value={trackingCode}
                        onChange={(event) =>
                          setTrackingCode(event.target.value)
                        }
                      />
                    </label>
                    <label>
                      تصویر رسید
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(event) =>
                          setReceipt(event.target.files?.[0] ?? null)
                        }
                      />
                    </label>
                  </div>
                )}
                <h3>مبلغ رزرو</h3>
                <label
                  className={`payment-option ${paymentType === "deposit" ? "selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="payment"
                    checked={paymentType === "deposit"}
                    onChange={() => setPaymentType("deposit")}
                  />
                  <span>
                    <strong>پرداخت بیعانه</strong>
                    <small>مانده مبلغ در آرایشگاه پرداخت می‌شود.</small>
                  </span>
                  <b>{toman(booking.data.deposit_amount)}</b>
                </label>
                <label
                  className={`payment-option ${paymentType === "full" ? "selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="payment"
                    checked={paymentType === "full"}
                    onChange={() => setPaymentType("full")}
                  />
                  <span>
                    <strong>پرداخت کامل</strong>
                    <small>در مراجعه نیازی به پرداخت مجدد نیست.</small>
                  </span>
                  <b>{toman(booking.data.total_price)}</b>
                </label>
              </div>
              <div className="checkout-card discount-entry">
                <h2>کد تخفیف دارید؟</h2>
                <input
                  value={discountCode}
                  onChange={(event) =>
                    setDiscountCode(event.target.value.toUpperCase())
                  }
                  placeholder="کد تخفیف را وارد کنید"
                  dir="ltr"
                  maxLength={32}
                />
                <small>
                  تخفیف معتبر هنگام پرداخت به‌صورت خودکار محاسبه می‌شود.
                </small>
              </div>
            </section>
            <aside className="checkout-total">
              <CreditCard />
              <h2>خلاصه پرداخت</h2>
              <div>
                <span>مبلغ خدمات</span>
                <strong>{toman(booking.data.total_price)}</strong>
              </div>
              <div className="payable-row">
                <span>مبلغ قابل پرداخت</span>
                <strong>
                  {toman(
                    paymentType === "deposit"
                      ? booking.data.deposit_amount
                      : booking.data.total_price,
                  )}
                </strong>
              </div>
              {payment.isError && (
                <p className="alert alert-error">
                  {getApiError(payment.error)}
                </p>
              )}
              <button
                className="button button-primary"
                disabled={payment.isPending}
                onClick={() => payment.mutate()}
              >
                {payment.isPending ? (
                  <LoaderCircle className="spin" size={18} />
                ) : (
                  <LockKeyhole size={18} />
                )}
                ثبت روش پرداخت و نوبت
              </button>
              <small>
                در کارت‌به‌کارت، ارسال رسید در مهلت ده دقیقه برای حفظ نوبت
                الزامی است.
              </small>
            </aside>
          </div>
        )}
      </main>
    </BookingShell>
  );
}
