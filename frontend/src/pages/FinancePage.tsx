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
import { SalonLayout } from "../components/SalonLayout";
import { useAuth } from "../auth/useAuth";
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
interface FinanceDetail {
  id: number;
  name: string;
  totals: Omit<
    SalonFinanceSummary,
    "id" | "name" | "branch_count" | "settled_amount" | "requested_amount"
  >;
  branches: Array<{
    id: number;
    name: string;
    payment_count: number;
    gross_revenue: number;
    refunded_amount: number;
    commission: number;
    net_revenue: number;
  }>;
  settlements: Settlement[];
}
export function FinancePage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [salonId, setSalonId] = useState<number | null>(null);
  const [settlementForm, setSettlementForm] = useState({
    amount: "",
    bank_account: "",
  });
  const [filters, setFilters] = useState({
    branch: "",
    method: "",
    status: "",
    source: "",
    date_from: "",
    date_to: "",
    search: "",
  });
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value),
  );
  if (salonId) params.set("salon", String(salonId));
  const salonSummaries = useQuery({
    queryKey: ["finance", "salons"],
    queryFn: async () =>
      (await api.get<Paginated<SalonFinanceSummary>>("/payments/salons/")).data,
  });
  const payments = useQuery({
    queryKey: ["finance", "payments", salonId, filters],
    queryFn: async () =>
      (await api.get<Paginated<Payment>>(`/payments/?${params.toString()}`))
        .data,
  });
  const detail = useQuery({
    queryKey: ["finance", "detail", salonId, filters],
    enabled: Boolean(salonId),
    queryFn: async () =>
      (
        await api.get<FinanceDetail>(
          `/payments/salons/${salonId}/?${params.toString()}`,
        )
      ).data,
  });
  const settlements = useQuery({
    queryKey: ["finance", "settlements", salonId],
    queryFn: async () =>
      (
        await api.get<Paginated<Settlement>>(
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
  const requestSettlement = useMutation({
    mutationFn: async () =>
      api.post("/payments/settlements/", {
        salon: salonId,
        amount: Number(settlementForm.amount),
        bank_account: settlementForm.bank_account,
      }),
    async onSuccess() {
      setSettlementForm({ amount: "", bank_account: "" });
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
    verifyTransfer.error ||
    detail.error ||
    requestSettlement.error;

  const content = (
    <div className="admin-embedded-page finance-page">
      <div className="admin-module-intro">
        <BadgeDollarSign size={30} />
        <p>کنترل درخواست‌های تسویه و مشاهده همه پرداخت‌های سامانه</p>
      </div>
      {error && <p className="alert alert-error">{getApiError(error)}</p>}

      <section className="panel-card finance-section">
        <h2>فیلتر و خروجی</h2>
        <div className="finance-filter-grid">
          <input
            className="finance-filter-search"
            placeholder="جستجوی مشتری یا شماره رزرو"
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
          <select
            value={filters.branch}
            onChange={(e) => setFilters({ ...filters, branch: e.target.value })}
          >
            <option value="">همه شعب</option>
            {detail.data?.branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
          <select
            value={filters.method}
            onChange={(e) => setFilters({ ...filters, method: e.target.value })}
          >
            <option value="">همه روش‌ها</option>
            <option value="in_person">حضوری</option>
            <option value="card_to_card">کارت‌به‌کارت</option>
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">همه وضعیت‌ها</option>
            <option value="pending">در انتظار</option>
            <option value="paid">پرداخت‌شده</option>
            <option value="failed">ردشده</option>
            <option value="refunded">بازپرداخت</option>
          </select>
          <select
            value={filters.source}
            onChange={(e) => setFilters({ ...filters, source: e.target.value })}
          >
            <option value="">همه منشأها</option>
            <option value="online">آنلاین</option>
            <option value="walk_in">حضوری</option>
          </select>
          <label>
            <span>از تاریخ</span>
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) =>
                setFilters({ ...filters, date_from: e.target.value })
              }
            />
          </label>
          <label>
            <span>تا تاریخ</span>
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) =>
                setFilters({ ...filters, date_to: e.target.value })
              }
            />
          </label>
          <button
            className="button button-outline"
            onClick={async () => {
              const response = await api.get(
                `/payments/export.csv?${params.toString()}`,
                { responseType: "blob" },
              );
              const url = URL.createObjectURL(response.data);
              const link = document.createElement("a");
              link.href = url;
              link.download = "finance.csv";
              link.click();
              URL.revokeObjectURL(url);
            }}
          >
            خروجی CSV
          </button>
        </div>
      </section>

      <section className="panel-card finance-section">
        <h2>سالن‌ها</h2>
        <div className="report-metrics finance-salon-grid">
          {salonSummaries.data?.results.map((salon) => (
            <button
              className={salonId === salon.id ? "selected" : ""}
              key={salon.id}
              onClick={() => setSalonId(salonId === salon.id ? null : salon.id)}
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

      {detail.data && (
        <section className="panel-card finance-section">
          <h2>جزئیات {detail.data.name}</h2>
          <div className="report-metrics finance-salon-grid">
            {detail.data.branches.map((branch) => (
              <button
                key={branch.id}
                onClick={() =>
                  setFilters({ ...filters, branch: String(branch.id) })
                }
              >
                <strong>{branch.name}</strong>
                <span>{branch.payment_count} تراکنش</span>
                <b>{money(branch.net_revenue)}</b>
                <small>
                  ناخالص {money(branch.gross_revenue)} · بازپرداخت{" "}
                  {money(branch.refunded_amount)} · کارمزد{" "}
                  {money(branch.commission)}
                </small>
              </button>
            ))}
          </div>
        </section>
      )}

      {auth.user?.role === "salon_owner" && (
        <section className="panel-card finance-section">
          <h2>درخواست تسویه</h2>
          <form
            className="finance-settlement-form"
            onSubmit={(event) => {
              event.preventDefault();
              requestSettlement.mutate();
            }}
          >
            <input
              required
              type="number"
              min="1"
              placeholder="مبلغ"
              value={settlementForm.amount}
              onChange={(e) =>
                setSettlementForm({ ...settlementForm, amount: e.target.value })
              }
            />
            <input
              required
              dir="ltr"
              placeholder="شماره شبا"
              value={settlementForm.bank_account}
              onChange={(e) =>
                setSettlementForm({
                  ...settlementForm,
                  bank_account: e.target.value,
                })
              }
            />
            <button
              className="button button-primary"
              disabled={!salonId || requestSettlement.isPending}
            >
              ثبت درخواست برای سالن انتخاب‌شده
            </button>
          </form>
        </section>
      )}

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
              {settlements.data?.results.map((item) => (
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
                    {item.status === "requested" &&
                      auth.user?.role === "admin" && (
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
        <div className="finance-mobile-list" aria-label="درخواست‌های تسویه">
          {settlements.data?.results.map((item) => (
            <article className="finance-mobile-card" key={item.id}>
              <header>
                <strong>{item.owner_name || item.owner_phone}</strong>
                <span
                  className={`status-badge ${item.status === "paid" ? "success" : item.status === "rejected" ? "error" : "pending"}`}
                >
                  {item.status === "paid"
                    ? "پرداخت‌شده"
                    : item.status === "rejected"
                      ? "ردشده"
                      : "در انتظار"}
                </span>
              </header>
              <dl>
                <div>
                  <dt>مبلغ</dt>
                  <dd>{money(item.amount)}</dd>
                </div>
                <div>
                  <dt>حساب مقصد</dt>
                  <dd dir="ltr">{item.bank_account}</dd>
                </div>
              </dl>
              {item.status === "requested" && auth.user?.role === "admin" && (
                <div className="finance-actions">
                  <button
                    className="button button-primary"
                    disabled={processSettlement.isPending}
                    onClick={() =>
                      processSettlement.mutate({ id: item.id, status: "paid" })
                    }
                  >
                    <CheckCircle2 /> تأیید
                  </button>
                  <button
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
            </article>
          ))}
        </div>
        {!settlements.isLoading && settlements.data?.count === 0 && (
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
        <div className="finance-mobile-list" aria-label="آخرین پرداخت‌ها">
          {payments.data?.results.map((item) => (
            <article className="finance-mobile-card" key={item.id}>
              <header>
                <strong>رزرو #{item.booking}</strong>
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
              </header>
              <p>
                {item.salon_name} / {item.branch_name}
              </p>
              <dl>
                <div>
                  <dt>مشتری</dt>
                  <dd dir="ltr">{item.customer_phone}</dd>
                </div>
                <div>
                  <dt>مبلغ</dt>
                  <dd>{money(item.amount)}</dd>
                </div>
                <div>
                  <dt>روش</dt>
                  <dd>
                    {item.method === "in_person" || item.method === "cash"
                      ? "حضوری"
                      : item.method === "card_to_card"
                        ? "کارت‌به‌کارت"
                        : item.method === "wallet"
                          ? "کیف پول"
                          : "آنلاین"}
                  </dd>
                </div>
                <div>
                  <dt>زمان</dt>
                  <dd>{formatPersianDateTime(item.created_at)}</dd>
                </div>
              </dl>
              {item.method === "card_to_card" && item.status === "pending" && (
                <div className="finance-actions">
                  <button
                    className="button button-primary"
                    onClick={() =>
                      verifyTransfer.mutate({ id: item.id, status: "paid" })
                    }
                  >
                    <CheckCircle2 /> تأیید رسید
                  </button>
                  <button
                    className="button button-outline"
                    onClick={() =>
                      verifyTransfer.mutate({ id: item.id, status: "failed" })
                    }
                  >
                    <XCircle /> رد رسید
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
  return auth.user?.role === "admin" ? (
    <AdminLayout title="مالی و تسویه‌ها">{content}</AdminLayout>
  ) : (
    <SalonLayout
      title="مالی و تسویه‌ها"
      description="گزارش تفصیلی سالن و شعب مجاز"
    >
      {content}
    </SalonLayout>
  );
}
