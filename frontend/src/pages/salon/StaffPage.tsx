import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  BriefcaseBusiness,
  LoaderCircle,
  Plus,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api, getApiError } from "../../api/client";
import { SalonLayout } from "../../components/SalonLayout";
import { faNumber } from "../../lib/format";
import type { Branch, Paginated, Staff } from "../../types/salon";

const schema = z.object({
  branch: z.number().positive("شعبه را انتخاب کنید."),
  first_name: z.string().min(2, "نام الزامی است."),
  last_name: z.string().min(2, "نام خانوادگی الزامی است."),
  experience_years: z.number().min(0).max(70),
  bio: z.string().optional(),
});
type StaffForm = z.infer<typeof schema>;

export function StaffPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const form = useForm<StaffForm>({
    resolver: zodResolver(schema),
    defaultValues: { experience_years: 0 },
  });
  const branches = useQuery({
    queryKey: ["management", "branches"],
    queryFn: async () =>
      (await api.get<Paginated<Branch>>("/management/branches/")).data,
  });
  const staff = useQuery({
    queryKey: ["management", "staff"],
    queryFn: async () =>
      (await api.get<Paginated<Staff>>("/management/staff/")).data,
  });
  const mutation = useMutation({
    mutationFn: async (values: StaffForm) =>
      (await api.post<Staff>("/management/staff/", values)).data,
    async onSuccess() {
      await queryClient.invalidateQueries({
        queryKey: ["management", "staff"],
      });
      setShowForm(false);
      form.reset({
        branch: branches.data?.results[0]?.id,
        experience_years: 0,
      });
    },
  });

  return (
    <SalonLayout
      title="پرسنل شما"
      description="مدیریت آرایشگران، مهارت‌ها و برنامه کاری"
      action={
        <button
          className="button button-primary"
          onClick={() => setShowForm(true)}
        >
          <Plus size={19} /> افزودن پرسنل
        </button>
      }
    >
      {showForm && (
        <form
          className="quick-form"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
        >
          <div className="quick-form-head">
            <div>
              <h2>پرسنل جدید</h2>
              <p>اطلاعات حرفه‌ای آرایشگر را ثبت کنید.</p>
            </div>
            <button
              type="button"
              className="text-button"
              onClick={() => setShowForm(false)}
            >
              بستن
            </button>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>شعبه</label>
              <select {...form.register("branch", { valueAsNumber: true })}>
                <option value="">انتخاب شعبه</option>
                {branches.data?.results.map((branch) => (
                  <option value={branch.id} key={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>نام</label>
              <input {...form.register("first_name")} />
            </div>
            <div className="field">
              <label>نام خانوادگی</label>
              <input {...form.register("last_name")} />
            </div>
            <div className="field">
              <label>سابقه (سال)</label>
              <input
                type="number"
                {...form.register("experience_years", { valueAsNumber: true })}
              />
            </div>
            <div className="field full">
              <label>معرفی کوتاه</label>
              <textarea rows={3} {...form.register("bio")} />
            </div>
          </div>
          {mutation.isError && (
            <p className="alert alert-error">{getApiError(mutation.error)}</p>
          )}
          <button
            className="button button-primary"
            disabled={mutation.isPending}
          >
            {mutation.isPending && <LoaderCircle className="spin" size={18} />}{" "}
            ذخیره پرسنل
          </button>
        </form>
      )}
      {staff.isError && (
        <p className="alert alert-error">{getApiError(staff.error)}</p>
      )}
      <section className="staff-grid">
        {staff.data?.results.map((person) => (
          <article className="staff-card" key={person.id}>
            <div className="staff-avatar">
              {person.photo ? (
                <img src={person.photo} alt={person.full_name} />
              ) : (
                <UserRound />
              )}
            </div>
            <div className="staff-info">
              <div className="staff-name">
                <h2>{person.full_name}</h2>
                {person.is_active && <BadgeCheck size={18} />}
              </div>
              <p>{person.branch_name}</p>
              <span>
                <BriefcaseBusiness size={15} />{" "}
                {faNumber.format(person.experience_years)} سال سابقه
              </span>
              <p className="staff-bio">
                {person.bio || "اطلاعات معرفی هنوز تکمیل نشده است."}
              </p>
            </div>
            <span
              className={`status-badge ${person.is_active ? "success" : "neutral"}`}
            >
              {person.is_active ? "فعال" : "غیرفعال"}
            </span>
          </article>
        ))}
        {!staff.isLoading && staff.data?.count === 0 && (
          <div className="panel-empty full-grid">
            <UserRound size={36} />
            <h2>پرسنلی ثبت نشده است</h2>
            <p>اعضای تیم سالن را اضافه کنید.</p>
          </div>
        )}
      </section>
    </SalonLayout>
  );
}
