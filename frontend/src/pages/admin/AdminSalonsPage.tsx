import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, LoaderCircle, Search, X } from "lucide-react";
import { useState } from "react";
import { Link } from "wouter";
import { api, getApiError } from "../../api/client";
import { AdminLayout } from "../../components/AdminLayout";
import { StatusBadge } from "../../components/StatusBadge";
import type { Paginated, Salon } from "../../types/salon";

export function AdminSalonsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const salons = useQuery({
    queryKey: ["admin", "salons", statusFilter, search],
    queryFn: async () =>
      (
        await api.get<Paginated<Salon>>(
          `/admin-panel/salons/?${new URLSearchParams({
            ...(statusFilter ? { status: statusFilter } : {}),
            ...(search ? { search } : {}),
            ordering: "name",
            page_size: "100",
          })}`,
        )
      ).data,
  });
  const mutation = useMutation({
    mutationFn: async ({
      id,
      action,
      reason,
    }: {
      id: number;
      action: "approve" | "reject";
      reason?: string;
    }) =>
      (
        await api.post<Salon>(
          `/admin-panel/salons/${id}/${action}/`,
          reason ? { reason } : {},
        )
      ).data,
    async onSuccess() {
      await queryClient.invalidateQueries({ queryKey: ["admin"] });
      setRejecting(null);
      setReason("");
    },
  });

  return (
    <AdminLayout title="بررسی سالن‌ها">
      <div className="admin-toolbar">
        <div className="search-box">
          <Search size={18} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="نام سالن، مالک یا شماره موبایل"
            aria-label="جستجوی سالن"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="">همه وضعیت‌ها</option>
          <option value="pending">در انتظار بررسی</option>
          <option value="approved">تأییدشده</option>
          <option value="rejected">ردشده</option>
          <option value="suspended">تعلیق‌شده</option>
        </select>
      </div>
      {salons.isError && (
        <p className="alert alert-error">{getApiError(salons.error)}</p>
      )}
      {mutation.isError && (
        <p className="alert alert-error">{getApiError(mutation.error)}</p>
      )}
      <section className="review-grid">
        {salons.data?.results.map((salon) => (
          <article className="review-card" key={salon.id}>
            <div className="review-card-head">
              <div>
                <h2>{salon.name}</h2>
                <p>
                  {salon.type_label} ·{" "}
                  {salon.branches[0]?.city_name || "شهر ثبت نشده"}
                </p>
              </div>
              <StatusBadge status={salon.status} label={salon.status_label} />
            </div>
            <p className="review-description">
              {salon.description || "توضیحی ثبت نشده است."}
            </p>
            <dl>
              <div>
                <dt>تعداد شعب</dt>
                <dd>{salon.branches.length}</dd>
              </div>
              <div>
                <dt>شماره تماس</dt>
                <dd>{salon.branches[0]?.phone || "-"}</dd>
              </div>
            </dl>
            <Link
              className="button button-outline admin-salon-details-link"
              href={`/admin/salons/${salon.id}`}
            >
              مشاهده اطلاعات کامل سالن
            </Link>
            {salon.status === "pending" && (
              <div className="review-actions">
                <button
                  className="button approve-button"
                  disabled={mutation.isPending}
                  onClick={() =>
                    mutation.mutate({ id: salon.id, action: "approve" })
                  }
                >
                  {mutation.isPending ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <Check size={17} />
                  )}{" "}
                  تأیید سالن
                </button>
                <button
                  className="button reject-button"
                  onClick={() => setRejecting(salon.id)}
                >
                  <X size={17} /> رد درخواست
                </button>
              </div>
            )}
            {rejecting === salon.id && (
              <form
                className="reject-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  mutation.mutate({ id: salon.id, action: "reject", reason });
                }}
              >
                <label>علت رد درخواست</label>
                <textarea
                  value={reason}
                  minLength={5}
                  required
                  onChange={(event) => setReason(event.target.value)}
                  rows={3}
                />
                <button className="button reject-button">ثبت رد درخواست</button>
              </form>
            )}
          </article>
        ))}
      </section>
    </AdminLayout>
  );
}
