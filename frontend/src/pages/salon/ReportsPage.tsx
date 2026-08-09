import { useQuery } from "@tanstack/react-query";
import {
  CalendarCheck,
  Download,
  ReceiptText,
  TrendingUp,
  WalletCards,
} from "lucide-react";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, getApiError } from "../../api/client";
import { JalaliDatePicker } from "../../components/JalaliDatePicker";
import { SalonLayout } from "../../components/SalonLayout";
import { formatPersianDate, toLocalIsoDate } from "../../lib/date";
import { faNumber, toman } from "../../lib/format";
import type { ReportSummary } from "../../types/booking";

export function ReportsPage() {
  const today = new Date();
  const monthAgo = new Date(Date.now() - 29 * 86_400_000);
  const [range, setRange] = useState({
    from: toLocalIsoDate(monthAgo),
    to: toLocalIsoDate(today),
  });
  const query = `date_from=${range.from}&date_to=${range.to}`;
  const report = useQuery({
    queryKey: ["salon", "reports", range],
    queryFn: async () =>
      (await api.get<ReportSummary>(`/reports/summary/?${query}`)).data,
  });
  async function downloadCsv() {
    const response = await api.get(`/reports/financial.csv?${query}`, {
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data as Blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "financial-report.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }
  const data = report.data;
  return (
    <SalonLayout
      title="گزارش‌های مالی"
      description="تحلیل درآمد، رزروها و خدمات پرفروش"
      action={
        <button className="button button-outline" onClick={downloadCsv}>
          <Download /> خروجی CSV
        </button>
      }
    >
      <div className="report-filters">
        <label className="jalali-field-label">
          از تاریخ
          <JalaliDatePicker
            value={range.from}
            max={range.to}
            ariaLabel="انتخاب تاریخ شمسی شروع گزارش"
            onChange={(from) => setRange({ ...range, from })}
          />
        </label>
        <label className="jalali-field-label">
          تا تاریخ
          <JalaliDatePicker
            value={range.to}
            min={range.from}
            max={toLocalIsoDate(today)}
            ariaLabel="انتخاب تاریخ شمسی پایان گزارش"
            onChange={(to) => setRange({ ...range, to })}
          />
        </label>
      </div>
      {report.isError && (
        <p className="alert alert-error">{getApiError(report.error)}</p>
      )}
      {data && (
        <>
          <section className="report-metrics">
            <article>
              <span>
                <WalletCards />
              </span>
              <div>
                <small>درآمد خالص</small>
                <strong>{toman(data.net_revenue)}</strong>
              </div>
              <em>پس از کارمزد</em>
            </article>
            <article>
              <span>
                <ReceiptText />
              </span>
              <div>
                <small>فروش ناخالص</small>
                <strong>{toman(data.gross_revenue)}</strong>
              </div>
              <em>کارمزد {toman(data.commission)}</em>
            </article>
            <article>
              <span>
                <CalendarCheck />
              </span>
              <div>
                <small>کل رزروها</small>
                <strong>{faNumber.format(data.booking_count)}</strong>
              </div>
              <em>{faNumber.format(data.completed_count)} انجام‌شده</em>
            </article>
            <article>
              <span>
                <TrendingUp />
              </span>
              <div>
                <small>میانگین هر رزرو</small>
                <strong>{toman(data.average_booking_value)}</strong>
              </div>
              <em>{faNumber.format(data.cancelled_count)} لغوشده</em>
            </article>
          </section>
          <div className="report-charts">
            <section className="report-chart-card">
              <h2>روند درآمد</h2>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={data.daily}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) =>
                      formatPersianDate(value, {
                        day: "numeric",
                        month: "short",
                      })
                    }
                  />
                  <YAxis
                    tickFormatter={(value) =>
                      faNumber.format(Number(value) / 1000)
                    }
                  />
                  <Tooltip formatter={(value) => toman(Number(value))} />
                  <Line
                    dataKey="revenue"
                    stroke="#a67618"
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </section>
            <section className="report-chart-card">
              <h2>خدمات پرفروش</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.top_services} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" />
                  <YAxis dataKey="service_name" type="category" width={80} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#d4af37" radius={[5, 5, 5, 5]} />
                </BarChart>
              </ResponsiveContainer>
            </section>
          </div>
        </>
      )}
    </SalonLayout>
  );
}
