import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarOff, CheckCircle2, Clock9, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, getApiError } from "../../api/client";
import { JalaliDatePicker } from "../../components/JalaliDatePicker";
import { SalonLayout } from "../../components/SalonLayout";
import {
  dateFromIso,
  formatPersianDateTime,
  localIsoDate,
  toLocalIsoDate,
} from "../../lib/date";
import type { Branch, BranchClosure, Paginated } from "../../types/salon";

const days = [
  "شنبه",
  "یکشنبه",
  "دوشنبه",
  "سه‌شنبه",
  "چهارشنبه",
  "پنجشنبه",
  "جمعه",
];
type WorkingWindow = { start: string; end: string };
type WorkingHours = Record<string, WorkingWindow[]>;

function defaultHours(): WorkingHours {
  return Object.fromEntries(
    days.map((_, index) => [
      String(index),
      index !== 6 ? [{ start: "09:00", end: "20:00" }] : [],
    ]),
  );
}

function normalizeHours(value?: Branch["working_hours"]): WorkingHours {
  const fallback = defaultHours();
  if (!value) return fallback;
  return Object.fromEntries(
    days.map((_, index) => {
      const item = value[String(index)];
      const normalized = Array.isArray(item)
        ? typeof item[0] === "string"
          ? [{ start: item[0], end: item[1] as string }]
          : (item as WorkingWindow[])
        : item?.is_open
          ? [{ start: item.start, end: item.end }]
          : item
            ? []
            : fallback[String(index)];
      return [String(index), normalized];
    }),
  );
}

function nextDate(value: string) {
  const date = dateFromIso(value);
  date.setDate(date.getDate() + 1);
  return toLocalIsoDate(date);
}

function toIso(date: string, time: string) {
  return `${date}T${time}:00+03:30`;
}

export function AvailabilityPage() {
  const queryClient = useQueryClient();
  const [branchId, setBranchId] = useState("");
  const [hours, setHours] = useState<WorkingHours>(defaultHours);
  const [saved, setSaved] = useState(false);
  const [closure, setClosure] = useState({
    date: localIsoDate(1),
    fullDay: true,
    start: "09:00",
    end: "12:00",
    reason: "",
  });
  const branches = useQuery({
    queryKey: ["management", "branches"],
    queryFn: async () =>
      (await api.get<Paginated<Branch>>("/management/branches/")).data,
  });
  const selectedBranch = useMemo(
    () => branches.data?.results.find((item) => item.id === Number(branchId)),
    [branchId, branches.data?.results],
  );
  const closures = useQuery({
    queryKey: ["management", "branch-closures", branchId],
    enabled: Boolean(branchId),
    queryFn: async () =>
      (
        await api.get<Paginated<BranchClosure>>(
          `/management/branch-closures/?branch=${branchId}&ordering=-starts_at`,
        )
      ).data,
  });

  useEffect(() => {
    if (!branchId && branches.data?.results[0]) {
      setBranchId(String(branches.data.results[0].id));
    }
  }, [branchId, branches.data?.results]);

  useEffect(() => {
    setHours(normalizeHours(selectedBranch?.working_hours));
    setSaved(false);
  }, [selectedBranch]);

  const hoursMutation = useMutation({
    mutationFn: async () =>
      api.patch(`/management/branches/${branchId}/`, { working_hours: hours }),
    async onSuccess() {
      setSaved(true);
      await queryClient.invalidateQueries({
        queryKey: ["management", "branches"],
      });
    },
  });
  const closureMutation = useMutation({
    mutationFn: async () => {
      const startsAt = closure.fullDay
        ? toIso(closure.date, "00:00")
        : toIso(closure.date, closure.start);
      const endsAt = closure.fullDay
        ? toIso(nextDate(closure.date), "00:00")
        : toIso(closure.date, closure.end);
      return api.post("/management/branch-closures/", {
        branch: Number(branchId),
        starts_at: startsAt,
        ends_at: endsAt,
        reason: closure.reason,
      });
    },
    async onSuccess() {
      setClosure({
        date: localIsoDate(1),
        fullDay: true,
        start: "09:00",
        end: "12:00",
        reason: "",
      });
      await queryClient.invalidateQueries({
        queryKey: ["management", "branch-closures", branchId],
      });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/management/branch-closures/${id}/`),
    async onSuccess() {
      await queryClient.invalidateQueries({
        queryKey: ["management", "branch-closures", branchId],
      });
    },
  });
  const error =
    branches.error ||
    closures.error ||
    hoursMutation.error ||
    closureMutation.error ||
    deleteMutation.error;

  return (
    <SalonLayout
      title="ساعات قابل رزرو"
      description="ساعات کاری هفتگی و تعطیلی‌های موقت هر شعبه را مدیریت کنید."
    >
      {error && <p className="alert alert-error">{getApiError(error)}</p>}
      <section className="availability-branch-card">
        <label htmlFor="availability-branch">شعبه موردنظر</label>
        <select
          id="availability-branch"
          value={branchId}
          onChange={(event) => setBranchId(event.target.value)}
        >
          {branches.data?.results.map((branch) => (
            <option value={branch.id} key={branch.id}>
              {branch.salon_name} — {branch.name}
            </option>
          ))}
        </select>
      </section>

      <section
        className="availability-card"
        aria-labelledby="weekly-hours-title"
      >
        <div className="availability-heading">
          <span>
            <Clock9 />
          </span>
          <div>
            <h2 id="weekly-hours-title">برنامه هفتگی رزرو</h2>
            <p>در روزهای بسته هیچ زمان رزروی به مشتری نمایش داده نمی‌شود.</p>
          </div>
        </div>
        <div className="weekly-hours-list">
          {days.map((day, index) => {
            const windows = hours[String(index)];
            const isOpen = windows.length > 0;
            return (
              <div
                className={`weekly-hours-row ${isOpen ? "" : "closed"}`}
                key={day}
              >
                <label className="day-switch">
                  <input
                    type="checkbox"
                    checked={isOpen}
                    onChange={(event) => {
                      setSaved(false);
                      setHours({
                        ...hours,
                        [String(index)]: event.target.checked
                          ? [{ start: "09:00", end: "20:00" }]
                          : [],
                      });
                    }}
                  />
                  <span>{day}</span>
                </label>
                {isOpen ? (
                  <div>
                    {windows.map((window, windowIndex) => (
                      <div
                        className="weekly-time-range"
                        key={`${day}-${windowIndex}`}
                      >
                        <label>
                          از{" "}
                          <input
                            type="time"
                            value={window.start}
                            onChange={(event) => {
                              const next = [...windows];
                              next[windowIndex] = {
                                ...window,
                                start: event.target.value,
                              };
                              setSaved(false);
                              setHours({ ...hours, [String(index)]: next });
                            }}
                          />
                        </label>
                        <label>
                          تا{" "}
                          <input
                            type="time"
                            value={window.end}
                            onChange={(event) => {
                              const next = [...windows];
                              next[windowIndex] = {
                                ...window,
                                end: event.target.value,
                              };
                              setSaved(false);
                              setHours({ ...hours, [String(index)]: next });
                            }}
                          />
                        </label>
                        <button
                          type="button"
                          className="button button-outline"
                          onClick={() => {
                            setSaved(false);
                            setHours({
                              ...hours,
                              [String(index)]: windows.filter(
                                (_, i) => i !== windowIndex,
                              ),
                            });
                          }}
                        >
                          حذف
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      className="button button-outline"
                      onClick={() => {
                        setSaved(false);
                        setHours({
                          ...hours,
                          [String(index)]: [
                            ...windows,
                            { start: "14:00", end: "20:00" },
                          ],
                        });
                      }}
                    >
                      افزودن بازه
                    </button>
                  </div>
                ) : (
                  <strong className="closed-label">بسته</strong>
                )}
              </div>
            );
          })}
        </div>
        <button
          className="button button-primary availability-save"
          disabled={!branchId || hoursMutation.isPending}
          onClick={() => hoursMutation.mutate()}
        >
          <CheckCircle2 size={18} /> ذخیره برنامه هفتگی
        </button>
        {saved && <p className="inline-success">برنامه هفتگی ذخیره شد.</p>}
      </section>

      <section className="availability-card" aria-labelledby="closure-title">
        <div className="availability-heading">
          <span>
            <CalendarOff />
          </span>
          <div>
            <h2 id="closure-title">تعطیلی یا بستن ساعات خاص</h2>
            <p>برای مناسبت، تعمیرات یا هر توقف موقت یک بازه بسته ثبت کنید.</p>
          </div>
        </div>
        <form
          className="closure-form"
          onSubmit={(event) => {
            event.preventDefault();
            closureMutation.mutate();
          }}
        >
          <label className="jalali-field-label">
            تاریخ
            <JalaliDatePicker
              value={closure.date}
              min={localIsoDate()}
              required
              ariaLabel="تاریخ تعطیلی شعبه"
              onChange={(date) => setClosure({ ...closure, date })}
            />
          </label>
          <label className="full-day-check">
            <input
              type="checkbox"
              checked={closure.fullDay}
              onChange={(event) =>
                setClosure({ ...closure, fullDay: event.target.checked })
              }
            />{" "}
            تعطیلی کل روز
          </label>
          {!closure.fullDay && (
            <>
              <label>
                از ساعت
                <input
                  required
                  type="time"
                  value={closure.start}
                  onChange={(event) =>
                    setClosure({ ...closure, start: event.target.value })
                  }
                />
              </label>
              <label>
                تا ساعت
                <input
                  required
                  type="time"
                  value={closure.end}
                  onChange={(event) =>
                    setClosure({ ...closure, end: event.target.value })
                  }
                />
              </label>
            </>
          )}
          <label className="closure-reason">
            علت یا توضیح
            <input
              value={closure.reason}
              placeholder="مثلاً تعطیلی مناسبتی"
              onChange={(event) =>
                setClosure({ ...closure, reason: event.target.value })
              }
            />
          </label>
          <button
            className="button button-primary"
            disabled={!branchId || closureMutation.isPending}
          >
            <CalendarOff size={18} /> ثبت بازه بسته
          </button>
        </form>
        <div className="closure-list">
          <h3>بازه‌های ثبت‌شده</h3>
          {closures.data?.results.map((item) => (
            <article key={item.id}>
              <div>
                <strong>{formatPersianDateTime(item.starts_at)}</strong>
                <span>تا {formatPersianDateTime(item.ends_at)}</span>
                {item.reason && <small>{item.reason}</small>}
              </div>
              <button
                aria-label="حذف بازه بسته"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(item.id)}
              >
                <Trash2 />
              </button>
            </article>
          ))}
          {!closures.isLoading && closures.data?.count === 0 && (
            <p className="panel-empty compact">
              هنوز بازه بسته‌ای ثبت نشده است.
            </p>
          )}
        </div>
      </section>
    </SalonLayout>
  );
}
