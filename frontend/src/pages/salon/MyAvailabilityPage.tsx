import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock9, CalendarOff, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { api, getApiError } from "../../api/client";
import { SalonLayout } from "../../components/SalonLayout";
import type {
  Paginated,
  Staff,
  StaffService,
  StaffShift,
  StaffTimeOff,
} from "../../types/salon";

const days = [
  "شنبه",
  "یکشنبه",
  "دوشنبه",
  "سه‌شنبه",
  "چهارشنبه",
  "پنجشنبه",
  "جمعه",
];

export function MyAvailabilityPage() {
  const queryClient = useQueryClient();
  const [timeOff, setTimeOff] = useState({
    starts_at: "",
    ends_at: "",
    reason: "",
  });
  const staffQuery = useQuery({
    queryKey: ["my-staff-profile"],
    queryFn: async () =>
      (await api.get<Paginated<Staff>>("/management/staff/")).data,
  });
  const profile = staffQuery.data?.results[0];
  const shifts = useQuery({
    queryKey: ["my-shifts", profile?.id],
    enabled: Boolean(profile),
    queryFn: async () =>
      (
        await api.get<Paginated<StaffShift>>(
          `/management/staff-shifts/?staff=${profile!.id}`,
        )
      ).data,
  });
  const services = useQuery({
    queryKey: ["my-services", profile?.id],
    enabled: Boolean(profile),
    queryFn: async () =>
      (
        await api.get<Paginated<StaffService>>(
          `/management/staff-services/?staff=${profile!.id}`,
        )
      ).data,
  });
  const timeOffs = useQuery({
    queryKey: ["my-time-offs", profile?.id],
    enabled: Boolean(profile),
    queryFn: async () =>
      (
        await api.get<Paginated<StaffTimeOff>>(
          `/management/staff-time-offs/?staff=${profile!.id}`,
        )
      ).data,
  });
  const saveShift = useMutation({
    mutationFn: async (value: Omit<StaffShift, "day_label">) =>
      value.id
        ? api.patch(`/management/staff-shifts/${value.id}/`, value)
        : api.post("/management/staff-shifts/", value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-shifts"] }),
  });
  const saveDuration = useMutation({
    mutationFn: async ({
      id,
      duration,
    }: {
      id: number;
      duration: number | null;
    }) =>
      api.patch(`/management/staff-services/${id}/`, {
        duration_override_minutes: duration,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["my-services"] }),
  });
  const addTimeOff = useMutation({
    mutationFn: async () =>
      api.post("/management/staff-time-offs/", {
        ...timeOff,
        staff: profile!.id,
      }),
    async onSuccess() {
      setTimeOff({ starts_at: "", ends_at: "", reason: "" });
      await queryClient.invalidateQueries({ queryKey: ["my-time-offs"] });
    },
  });
  const deleteShift = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/management/staff-shifts/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["my-shifts"] }),
  });
  const deleteTimeOff = useMutation({
    mutationFn: async (id: number) =>
      api.delete(`/management/staff-time-offs/${id}/`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["my-time-offs"] }),
  });
  const error =
    staffQuery.error ||
    shifts.error ||
    services.error ||
    timeOffs.error ||
    saveShift.error ||
    saveDuration.error ||
    addTimeOff.error;

  return (
    <SalonLayout
      title="زمان‌های من"
      description="ساعت کاری، مرخصی و مدت خدمات خود را تعیین کنید."
    >
      {error && <p className="alert alert-error">{getApiError(error)}</p>}
      {!staffQuery.isLoading && !profile && (
        <p className="alert alert-error">
          پروفایل آرایشگر به این حساب متصل نشده است.
        </p>
      )}
      {profile && (
        <>
          <section className="availability-card">
            <div className="availability-heading">
              <Clock9 />
              <h2>برنامه هفتگی</h2>
            </div>
            <div className="weekly-hours-list">
              {days.map((day, index) => {
                const current =
                  shifts.data?.results.filter(
                    (item) => item.day_of_week === index && !item.is_off,
                  ) ?? [];
                return (
                  <div className="staff-day-card" key={day}>
                    <strong className="staff-day-title">{day}</strong>
                    {current.map((window) => (
                      <form
                        className="weekly-hours-row staff-window-row"
                        key={window.id}
                        onSubmit={(event) => {
                          event.preventDefault();
                          const form = new FormData(event.currentTarget);
                          saveShift.mutate({
                            ...window,
                            start_time: String(form.get("start_time")),
                            end_time: String(form.get("end_time")),
                          });
                        }}
                      >
                        <input
                          name="start_time"
                          type="time"
                          defaultValue={window.start_time?.slice(0, 5)}
                          required
                        />
                        <input
                          name="end_time"
                          type="time"
                          defaultValue={window.end_time?.slice(0, 5)}
                          required
                        />
                        <button className="button button-outline">
                          <CheckCircle2 size={16} /> ذخیره
                        </button>
                        <button
                          type="button"
                          className="button button-outline"
                          onClick={() => deleteShift.mutate(window.id)}
                        >
                          <Trash2 size={16} /> حذف
                        </button>
                      </form>
                    ))}
                    <form
                      className="weekly-hours-row staff-window-row staff-window-add-row"
                      onSubmit={(event) => {
                        event.preventDefault();
                        const form = new FormData(event.currentTarget);
                        saveShift.mutate({
                          id: 0,
                          staff: profile.id,
                          day_of_week: index,
                          start_time: String(form.get("start_time")),
                          end_time: String(form.get("end_time")),
                          is_off: false,
                        });
                      }}
                    >
                      <input
                        name="start_time"
                        type="time"
                        defaultValue="09:00"
                        required
                      />
                      <input
                        name="end_time"
                        type="time"
                        defaultValue="13:00"
                        required
                      />
                      <button className="button button-outline">
                        <Plus size={16} /> افزودن بازه
                      </button>
                    </form>
                  </div>
                );
              })}
            </div>
          </section>
          <section className="availability-card staff-duration-section">
            <h2>مدت اختصاصی خدمات</h2>
            {services.data?.results.map((service) => (
              <form
                className="weekly-hours-row staff-duration-row"
                key={service.id}
                onSubmit={(event) => {
                  event.preventDefault();
                  const raw = String(
                    new FormData(event.currentTarget).get("duration") ?? "",
                  );
                  const duration = raw ? Number(raw) : null;
                  saveDuration.mutate({ id: service.id, duration });
                }}
              >
                <strong>{service.service_name}</strong>
                <span>مدت پایه: {service.base_duration_minutes} دقیقه</span>
                <input
                  name="duration"
                  type="number"
                  min="5"
                  defaultValue={service.duration_override_minutes ?? ""}
                  placeholder={String(service.base_duration_minutes)}
                />
                <span>
                  مدت مؤثر: {service.effective_duration_minutes} دقیقه
                </span>
                <button className="button button-outline">ذخیره</button>
                <button
                  type="button"
                  className="button button-outline"
                  onClick={() =>
                    saveDuration.mutate({ id: service.id, duration: null })
                  }
                >
                  استفاده از مدت پایه
                </button>
              </form>
            ))}
          </section>
          <section className="availability-card staff-timeoff-section">
            <div className="availability-heading">
              <CalendarOff />
              <h2>مرخصی</h2>
            </div>
            <form
              className="form-grid"
              onSubmit={(event) => {
                event.preventDefault();
                addTimeOff.mutate();
              }}
            >
              <label>
                شروع
                <input
                  required
                  type="datetime-local"
                  value={timeOff.starts_at}
                  onChange={(event) =>
                    setTimeOff({ ...timeOff, starts_at: event.target.value })
                  }
                />
              </label>
              <label>
                پایان
                <input
                  required
                  type="datetime-local"
                  value={timeOff.ends_at}
                  onChange={(event) =>
                    setTimeOff({ ...timeOff, ends_at: event.target.value })
                  }
                />
              </label>
              <label>
                توضیح
                <input
                  value={timeOff.reason}
                  onChange={(event) =>
                    setTimeOff({ ...timeOff, reason: event.target.value })
                  }
                />
              </label>
              <button className="button button-primary">ثبت مرخصی</button>
            </form>
            {timeOffs.data?.results.map((item) => (
              <article className="staff-timeoff-item" key={item.id}>
                <span>
                  {new Date(item.starts_at).toLocaleString("fa-IR")} تا{" "}
                  {new Date(item.ends_at).toLocaleString("fa-IR")} —{" "}
                  {item.reason}
                </span>
                <button
                  className="button button-outline"
                  onClick={() => deleteTimeOff.mutate(item.id)}
                >
                  <Trash2 size={15} /> حذف
                </button>
              </article>
            ))}
          </section>
        </>
      )}
    </SalonLayout>
  );
}
