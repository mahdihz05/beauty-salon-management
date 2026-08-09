import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Headphones, LoaderCircle, Send } from "lucide-react";
import { useState } from "react";
import { api, getApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { MobileBottomNav, PublicHeader } from "../components/PublicHeader";
import { formatPersianDateTime } from "../lib/date";
import type { Paginated } from "../types/salon";

interface SupportTicket {
  id: number;
  customer_name: string;
  customer_phone: string;
  subject: string;
  message: string;
  response: string;
  status: "open" | "in_progress" | "resolved" | "closed";
  status_label: string;
  created_at: string;
}

export function SupportTicketsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isAgent = user?.role === "support" || user?.role === "admin";
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const tickets = useQuery({
    queryKey: ["support", "tickets"],
    queryFn: async () =>
      (await api.get<Paginated<SupportTicket>>("/support/tickets/")).data,
  });
  const createTicket = useMutation({
    mutationFn: async () => api.post("/support/tickets/", { subject, message }),
    async onSuccess() {
      setSubject("");
      setMessage("");
      await queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
    },
  });
  const updateTicket = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: string }) =>
      api.patch(`/support/tickets/${id}/`, {
        status,
        response:
          status === "resolved"
            ? "درخواست بررسی و حل شد."
            : "در حال بررسی توسط پشتیبانی",
      }),
    async onSuccess() {
      await queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
    },
  });
  const error = tickets.error || createTicket.error || updateTicket.error;

  return (
    <div className="customer-page">
      <PublicHeader />
      <main className="container my-bookings">
        <div className="page-heading customer-heading">
          <div>
            <p className="eyebrow">مرکز پاسخ‌گویی</p>
            <h1>{isAgent ? "مدیریت تیکت‌های پشتیبانی" : "پشتیبانی"}</h1>
          </div>
          <Headphones size={36} />
        </div>
        {error && <p className="alert alert-error">{getApiError(error)}</p>}
        {!isAgent && (
          <form
            className="checkout-card profile-form"
            onSubmit={(event) => {
              event.preventDefault();
              createTicket.mutate();
            }}
          >
            <label>
              موضوع
              <input
                required
                minLength={3}
                maxLength={180}
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
              />
            </label>
            <label>
              شرح درخواست
              <textarea
                required
                minLength={5}
                maxLength={4000}
                rows={5}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
              />
            </label>
            <button
              className="button button-primary"
              disabled={createTicket.isPending}
            >
              {createTicket.isPending ? (
                <LoaderCircle className="spin" />
              ) : (
                <Send />
              )}{" "}
              ارسال تیکت
            </button>
          </form>
        )}
        <section className="customer-booking-list">
          {tickets.data?.results.map((ticket) => (
            <article className="customer-booking-card" key={ticket.id}>
              <div className="booking-card-top">
                <div>
                  <h2>{ticket.subject}</h2>
                  {isAgent && (
                    <span>{ticket.customer_name || ticket.customer_phone}</span>
                  )}
                </div>
                <b className="booking-status">{ticket.status_label}</b>
              </div>
              <p>{ticket.message}</p>
              <small className="muted">
                ثبت‌شده در {formatPersianDateTime(ticket.created_at)}
              </small>
              {ticket.response && (
                <p className="alert alert-info">{ticket.response}</p>
              )}
              {isAgent &&
                ticket.status !== "resolved" &&
                ticket.status !== "closed" && (
                  <div className="success-actions">
                    <button
                      className="button button-outline"
                      onClick={() =>
                        updateTicket.mutate({
                          id: ticket.id,
                          status: "in_progress",
                        })
                      }
                    >
                      شروع بررسی
                    </button>
                    <button
                      className="button button-primary"
                      onClick={() =>
                        updateTicket.mutate({
                          id: ticket.id,
                          status: "resolved",
                        })
                      }
                    >
                      ثبت به‌عنوان حل‌شده
                    </button>
                  </div>
                )}
            </article>
          ))}
          {!tickets.isLoading && tickets.data?.count === 0 && (
            <div className="summary-empty">
              <Headphones />
              <p>تیکتی ثبت نشده است.</p>
            </div>
          )}
        </section>
      </main>
      {!isAgent && <MobileBottomNav />}
    </div>
  );
}
