import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  BadgeDollarSign,
  CheckCircle2,
  LoaderCircle,
  XCircle,
} from "lucide-react";
import { api, getApiError } from "../api/client";
import { AdminLayout } from "../components/AdminLayout";
import { formatPersianDateTime } from "../lib/date";
import type { Payment, Settlement } from "../types/booking";
import type { Paginated } from "../types/salon";

const money = (value: number) =>
  `${new Intl.NumberFormat("fa-IR").format(value)} تومان`;
interface SalonFinanceSummary {
  id: number;
  name: string;
  branch_count: number;
  gross_revenue: number;
  refunded_amount: number;
  commission: number;
  net_revenue: number;
  settled_amount: number;
  requested_amount: number;
  payment_count: number;
}
export function FinancePage() {
  const queryClient = useQueryClient();
  const [salonId, setSalonId] = useState<number | null>(null);
  const salonSummaries = useQuery({
    queryKey: ["finance", "salons"],
    queryFn: async () =>
      (await api.get<SalonFinanceSummary[]>("/payments/salons/")).data,
  });
  const payments = useQuery({
    queryKey: ["finance", "payments", salonId],
    queryFn: async () =>
      (
        await api.get<Paginated<Payment>>(
          `/payments/${salonId ? `?booking__branch__salon=${salonId}` : ""}`,
        )
      ).data,
  });
  const settlements = useQuery({
    queryKey: ["finance", "settlements", salonId],
    queryFn: async () =>
      (
        await api.get<Settlement[]>(
          `/payments/settlements/${salonId ? `?salon=${salonId}` : ""}`,
        )
      ).data,
  });
  const processSettlement = useMutation({
    mutationFn: async ({
      id,
      status,
    }: {
      id: number;
      status: "paid" | "rejected";
    }) => api.post(`/payments/settlements/${id}/process/`, { status }),
    async onSuccess() {
      await queryClient.invalidateQueries({
        queryKey: ["finance", "settlements"],
      });
    },
  });
  const verifyTransfer = useMutation({
    mutationFn: async ({
      id,
      status,
    }: {
      id: number;
      status: "paid" | "failed";
    }) => api.post(`/payments/${id}/verify-transfer/`, { status }),
    async onSuccess() {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["finance", "payments"] }),
        queryClient.invalidateQueries({ queryKey: ["finance", "salons"] }),
      ]);
    },
  });
  const error =
    salonSummaries.error ||
    payments.error ||
    settlements.error ||
    processSettlement.error ||
    verifyTransfer.error;

  return (
    <AdminLayout title="مالی و تسویه‌ها">
      <div className="admin-embedded-page finance-page">
        <div className="admin-module-intro">
          <BadgeDollarSign size={30} />
          <p>کنترل درخواست‌های تسویه و مشاهده همه پرداخت‌های سامانه</p>
        </div>
        {error && <p className="alert alert-error">{getApiError(error)}</p>}

        <section className="panel-card finance-section">
          <h2>سالن‌ها</h2>
          <div className="report-metrics finance-salon-grid">
            {salonSummaries.data?.map((salon) => (
              <button
                className={salonId === salon.id ? "selected" : ""}
                key={salon.id}
                onClick={() =>
                  setSalonId(salonId === salon.id ? null : salon.id)
                }
              >
                <strong>{salon.name}</strong>
                <span>
                  {salon.branch_count} شعبه · {salon.payment_count} پرداخت
                </span>
                <b>{money(salon.net_revenue)}</b>
                <small>
                  ناخالص {money(salon.gross_revenue)} · کارمزد{" "}
                  {money(salon.commission)}
                </small>
              </button>
            ))}
          </div>
        </section>

        <section className="panel-card finance-section">
          <h2>درخواست‌های تسویه</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>مالک</th>
                  <th>مبلغ</th>
                  <th>حساب مقصد</th>
                  <th>وضعیت</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                {settlements.data?.map((item) => (
                  <tr key={item.id}>
                    <td>{item.owner_name || item.owner_phone}</td>
                    <td>{money(item.amount)}</td>
                    <td dir="ltr">{item.bank_account}</td>
                    <td>
                      <span
                        className={`status-badge ${item.status === "paid" ? "success" : item.status === "rejected" ? "error" : "pending"}`}
                      >
                        {item.status === "paid"
                          ? "پرداخت‌شده"
                          : item.status === "rejected"
                            ? "ردشده"
                            : "در انتظار"}
                      </span>
                    </td>
                    <td>
                      {item.status === "requested" && (
                        <div className="finance-actions">
                          <button
                            aria-label="تأیید تسویه"
                            className="button button-primary"
                            disabled={processSettlement.isPending}
                            onClick={() =>
                              processSettlement.mutate({
                                id: item.id,
                                status: "paid",
                              })
                            }
                          >
                            <CheckCircle2 /> تأیید
                          </button>
                          <button
                            aria-label="رد تسویه"
                            className="button button-outline"
                            disabled={processSettlement.isPending}
                            onClick={() =>
                              processSettlement.mutate({
                                id: item.id,
                                status: "rejected",
                              })
                            }
                          >
                            <XCircle /> رد
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!settlements.isLoading && settlements.data?.length === 0 && (
            <p className="muted">درخواست تسویه‌ای ثبت نشده است.</p>
          )}
        </section>

        <section className="panel-card finance-section">
          <h2>آخرین پرداخت‌ها</h2>
          {payments.isLoading && <LoaderCircle className="spin" />}
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>رزرو</th>
                  <th>سالن / شعبه</th>
                  <th>مشتری</th>
                  <th>مبلغ</th>
                  <th>روش</th>
                  <th>وضعیت</th>
                  <th>زمان</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                {payments.data?.results.map((item) => (
                  <tr key={item.id}>
                    <td>#{item.booking}</td>
                    <td>
                      {item.salon_name} / {item.branch_name}
                    </td>
                    <td dir="ltr">{item.customer_phone}</td>
                    <td>{money(item.amount)}</td>
                    <td>
                      {item.method === "in_person" || item.method === "cash"
                        ? "حضوری"
                        : item.method === "card_to_card"
                          ? "کارت‌به‌کارت"
                          : item.method === "wallet"
                            ? "کیف پول"
                            : "آنلاین"}
                    </td>
                    <td>
                      <span
                        className={`status-badge ${item.status === "paid" ? "success" : item.status === "pending" ? "pending" : "error"}`}
                      >
                        {item.status === "paid"
                          ? "موفق"
                          : item.status === "pending"
                            ? "در انتظار"
                            : item.status === "refunded"
                              ? "بازپرداخت"
                              : "ناموفق"}
                      </span>
                    </td>
                    <td>{formatPersianDateTime(item.created_at)}</td>
                    <td>
                      {item.method === "card_to_card" &&
                        item.status === "pending" && (
                          <div className="finance-actions">
                            <button
                              aria-label="تأیید رسید"
                              onClick={() =>
                                verifyTransfer.mutate({
                                  id: item.id,
                                  status: "paid",
                                })
                              }
                            >
                              <CheckCircle2 />
                            </button>
                            <button
                              aria-label="رد رسید"
                              onClick={() =>
                                verifyTransfer.mutate({
                                  id: item.id,
                                  status: "failed",
                                })
                              }
                            >
                              <XCircle />
                            </button>
                          </div>
                        )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AdminLayout>
  );
}
