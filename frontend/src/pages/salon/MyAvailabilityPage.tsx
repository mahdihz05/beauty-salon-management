import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock9, CalendarOff } from "lucide-react";
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
    mutationFn: async ({ id, duration }: { id: number; duration: number }) =>
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
                const current = shifts.data?.results.find(
                  (item) => item.day_of_week === index,
                );
                return (
                  <form
                    className="weekly-hours-row"
                    key={day}
                    onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      const isOff = form.get("is_off") === "on";
                      saveShift.mutate({
                        id: current?.id ?? 0,
                        staff: profile.id,
                        day_of_week: index,
                        start_time: isOff
                          ? null
                          : String(form.get("start_time")),
                        end_time: isOff ? null : String(form.get("end_time")),
                        is_off: isOff,
                      });
                    }}
                  >
                    <strong>{day}</strong>
                    <input
                      name="start_time"
                      type="time"
                      defaultValue={current?.start_time?.slice(0, 5) ?? "09:00"}
                    />
                    <input
                      name="end_time"
                      type="time"
                      defaultValue={current?.end_time?.slice(0, 5) ?? "18:00"}
                    />
                    <label>
                      <input
                        name="is_off"
                        type="checkbox"
                        defaultChecked={current?.is_off ?? false}
                      />{" "}
                      تعطیل
                    </label>
                    <button className="button button-outline">
                      <CheckCircle2 size={16} /> ذخیره
                    </button>
                  </form>
                );
              })}
            </div>
          </section>
          <section className="availability-card">
            <h2>مدت اختصاصی خدمات</h2>
            {services.data?.results.map((service) => (
              <form
                className="weekly-hours-row"
                key={service.id}
                onSubmit={(event) => {
                  event.preventDefault();
                  const duration = Number(
                    new FormData(event.currentTarget).get("duration"),
                  );
                  saveDuration.mutate({ id: service.id, duration });
                }}
              >
                <strong>{service.service_name}</strong>
                <input
                  name="duration"
                  type="number"
                  min="5"
                  defaultValue={service.duration_override_minutes ?? 30}
                />
                <span>دقیقه</span>
                <button className="button button-outline">ذخیره</button>
              </form>
            ))}
          </section>
          <section className="availability-card">
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
              <p key={item.id}>
                {new Date(item.starts_at).toLocaleString("fa-IR")} تا{" "}
                {new Date(item.ends_at).toLocaleString("fa-IR")} — {item.reason}
              </p>
            ))}
          </section>
        </>
      )}
    </SalonLayout>
  );
}
