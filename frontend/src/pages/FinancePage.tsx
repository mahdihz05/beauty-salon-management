import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeDollarSign,
  CheckCircle2,
  LoaderCircle,
  XCircle,
} from "lucide-react";
import { api, getApiError } from "../api/client";
import { PublicHeader } from "../components/PublicHeader";
import { formatPersianDateTime } from "../lib/date";
import type { Payment, Settlement } from "../types/booking";
import type { Paginated } from "../types/salon";

const money = (value: number) =>
  `${new Intl.NumberFormat("fa-IR").format(value)} تومان`;
export function FinancePage() {
  const queryClient = useQueryClient();
  const payments = useQuery({
    queryKey: ["finance", "payments"],
    queryFn: async () => (await api.get<Paginated<Payment>>("/payments/")).data,
  });
  const settlements = useQuery({
    queryKey: ["finance", "settlements"],
    queryFn: async () =>
      (await api.get<Settlement[]>("/payments/settlements/")).data,
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
  const error = payments.error || settlements.error || processSettlement.error;

  return (
    <div className="customer-page finance-page">
      <PublicHeader />
      <main className="container my-bookings">
        <div className="page-heading customer-heading">
          <div>
            <p className="eyebrow">کنترل عملیات مالی</p>
            <h1>پرداخت‌ها و تسویه‌ها</h1>
          </div>
          <BadgeDollarSign size={38} />
        </div>
        {error && <p className="alert alert-error">{getApiError(error)}</p>}

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
                      {item.method === "cash"
                        ? "نقدی"
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
