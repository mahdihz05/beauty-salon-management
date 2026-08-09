import { useQuery } from "@tanstack/react-query";
import { Check, Clock3, Plus, Scissors } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useRoute } from "wouter";
import { api, getApiError } from "../../api/client";
import { BookingShell } from "../../components/BookingShell";
import { bookingDraft } from "../../lib/booking-draft";
import { faNumber, toman } from "../../lib/format";
import type { PublicBranch, PublicBranchService } from "../../types/public";

export function ServiceSelectionPage() {
  const [, params] = useRoute("/booking/:branchId/services");
  const branchId = Number(params?.branchId);
  const requested = Number(
    new URLSearchParams(window.location.search).get("service"),
  );
  const previous = bookingDraft.get();
  const [selected, setSelected] = useState<number[]>(() =>
    previous?.branchId === branchId
      ? previous.serviceIds
      : requested
        ? [requested]
        : [],
  );
  const branch = useQuery({
    queryKey: ["public", "branch", branchId],
    enabled: Number.isFinite(branchId),
    queryFn: async () =>
      (await api.get<PublicBranch>(`/public/branches/${branchId}/`)).data,
  });
  const grouped = useMemo(() => {
    const groups = new Map<string, PublicBranchService[]>();
    branch.data?.services.forEach((service) =>
      groups.set(service.category_name, [
        ...(groups.get(service.category_name) || []),
        service,
      ]),
    );
    return [...groups.entries()];
  }, [branch.data]);
  const selectedServices =
    branch.data?.services.filter((item) => selected.includes(item.id)) || [];
  const total = selectedServices.reduce((sum, item) => sum + item.price, 0);
  function toggle(id: number) {
    setSelected((items) =>
      items.includes(id) ? items.filter((item) => item !== id) : [...items, id],
    );
  }
  function persist() {
    bookingDraft.set({ branchId, serviceIds: selected });
  }

  return (
    <BookingShell step={1} backHref="/salons">
      <main className="booking-main container">
        <div className="booking-heading">
          <p>مرحله اول از سه</p>
          <h1>انتخاب خدمات</h1>
          <span>{branch.data?.name}</span>
        </div>
        {branch.isError && (
          <p className="alert alert-error">{getApiError(branch.error)}</p>
        )}
        <div className="booking-layout">
          <section className="service-selection-list">
            {grouped.map(([category, services]) => (
              <div className="select-category" key={category}>
                <h2>{category}</h2>
                {services.map((service) => {
                  const active = selected.includes(service.id);
                  return (
                    <button
                      className={`select-service-card ${active ? "selected" : ""}`}
                      onClick={() => toggle(service.id)}
                      key={service.id}
                    >
                      <span className="select-icon">
                        {active ? <Check /> : <Plus />}
                      </span>
                      <div>
                        <h3>{service.service_name}</h3>
                        <p>
                          {service.description || "خدمت تخصصی با بهترین کیفیت"}
                        </p>
                        <small>
                          <Clock3 /> {faNumber.format(service.duration_minutes)}{" "}
                          دقیقه
                        </small>
                      </div>
                      <strong>
                        {service.price_type === "starting_from" && "از "}
                        {toman(service.price)}
                      </strong>
                    </button>
                  );
                })}
              </div>
            ))}
          </section>
          <aside className="booking-summary">
            <h2>خلاصه رزرو</h2>
            {selectedServices.length ? (
              <ul>
                {selectedServices.map((service) => (
                  <li key={service.id}>
                    <span>{service.service_name}</span>
                    <strong>{toman(service.price)}</strong>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="summary-empty">
                <Scissors />
                <p>هنوز خدمتی انتخاب نشده</p>
              </div>
            )}
            <div className="summary-total">
              <span>مجموع خدمات</span>
              <strong>{toman(total)}</strong>
            </div>
            <Link
              className={`button button-primary ${selected.length ? "" : "disabled"}`}
              href={selected.length ? `/booking/${branchId}/datetime` : "#"}
              onClick={persist}
            >
              ادامه و انتخاب زمان
            </Link>
          </aside>
        </div>
      </main>
    </BookingShell>
  );
}
