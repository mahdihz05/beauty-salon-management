import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation } from "wouter";
import { z } from "zod";
import { api, getApiError } from "../../api/client";
import { SalonLayout } from "../../components/SalonLayout";
import type { City, Salon } from "../../types/salon";

const schema = z.object({
  name: z.string().min(3, "نام سالن را کامل وارد کنید."),
  type: z.enum(["women", "men", "unisex"]),
  description: z.string().min(20, "حداقل ۲۰ حرف درباره سالن بنویسید."),
  branch_name: z.string().min(2, "نام شعبه الزامی است."),
  city: z.number().positive("شهر را انتخاب کنید."),
  address: z.string().min(10, "نشانی کامل را وارد کنید."),
  phone: z.string().min(8, "شماره تماس معتبر وارد کنید."),
});
type FormValues = z.infer<typeof schema>;

export function OnboardingPage() {
  const [, navigate] = useLocation();
  const [serverError, setServerError] = useState("");
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { type: "women", branch_name: "شعبه مرکزی" },
  });
  const cities = useQuery({
    queryKey: ["cities"],
    queryFn: async () => (await api.get<City[]>("/management/cities/")).data,
  });

  async function submit(values: FormValues) {
    setServerError("");
    try {
      const salon = (
        await api.post<Salon>("/management/salons/", {
          name: values.name,
          type: values.type,
          description: values.description,
        })
      ).data;
      await api.post("/management/branches/", {
        salon: salon.id,
        name: values.branch_name,
        city: values.city,
        address: values.address,
        phone: values.phone,
      });
      await api.post(`/management/salons/${salon.id}/submit/`);
      navigate("/salon/dashboard");
    } catch (error) {
      setServerError(getApiError(error));
    }
  }

  return (
    <SalonLayout
      title="ثبت سالن جدید"
      description="اطلاعات پایه را وارد کنید؛ پس از بررسی مدیر منتشر می‌شود."
    >
      <form
        className="panel-form onboarding-form"
        onSubmit={form.handleSubmit(submit)}
      >
        <div className="form-section">
          <div className="form-section-title">
            <span>۱</span>
            <div>
              <h2>اطلاعات سالن</h2>
              <p>نام و نوع فعالیت سالن</p>
            </div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="salon-name">نام سالن</label>
              <input id="salon-name" {...form.register("name")} />
              {form.formState.errors.name && (
                <p className="field-error">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>
            <div className="field">
              <label htmlFor="salon-type">نوع سالن</label>
              <select id="salon-type" {...form.register("type")}>
                <option value="women">زنانه</option>
                <option value="men">مردانه</option>
                <option value="unisex">مشترک</option>
              </select>
            </div>
            <div className="field full">
              <label htmlFor="description">معرفی سالن</label>
              <textarea
                id="description"
                rows={4}
                {...form.register("description")}
              />
              {form.formState.errors.description && (
                <p className="field-error">
                  {form.formState.errors.description.message}
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="form-section">
          <div className="form-section-title">
            <span>۲</span>
            <div>
              <h2>اطلاعات شعبه</h2>
              <p>نشانی و راه ارتباطی</p>
            </div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="branch-name">نام شعبه</label>
              <input id="branch-name" {...form.register("branch_name")} />
            </div>
            <div className="field">
              <label htmlFor="city">شهر</label>
              <select
                id="city"
                defaultValue=""
                {...form.register("city", { valueAsNumber: true })}
              >
                <option value="" disabled>
                  انتخاب شهر
                </option>
                {cities.data?.map((city) => (
                  <option value={city.id} key={city.id}>
                    {city.name}
                  </option>
                ))}
              </select>
              {form.formState.errors.city && (
                <p className="field-error">
                  {form.formState.errors.city.message}
                </p>
              )}
            </div>
            <div className="field full">
              <label htmlFor="address">نشانی کامل</label>
              <input id="address" {...form.register("address")} />
              {form.formState.errors.address && (
                <p className="field-error">
                  {form.formState.errors.address.message}
                </p>
              )}
            </div>
            <div className="field">
              <label htmlFor="branch-phone">شماره تماس</label>
              <input id="branch-phone" dir="ltr" {...form.register("phone")} />
            </div>
          </div>
        </div>
        {serverError && <p className="alert alert-error">{serverError}</p>}
        <button
          className="button button-primary submit-button"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? (
            <LoaderCircle className="spin" />
          ) : (
            <CheckCircle2 />
          )}{" "}
          ثبت و ارسال برای بررسی
        </button>
      </form>
    </SalonLayout>
  );
}
