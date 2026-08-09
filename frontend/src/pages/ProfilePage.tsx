import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { LoaderCircle, LogOut, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation } from "wouter";
import { z } from "zod";
import { api, getApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { BrandLogo } from "../components/BrandLogo";
import type { User } from "../types/auth";

const profileSchema = z.object({
  name: z.string().min(3, "نام و نام خانوادگی را کامل وارد کنید."),
  email: z.union([z.literal(""), z.string().email("ایمیل معتبر وارد کنید.")]),
  gender: z.enum(["woman", "man", "not_specified"]),
});
type ProfileForm = z.infer<typeof profileSchema>;

export function ProfilePage() {
  const auth = useAuth();
  const [, navigate] = useLocation();
  const [message, setMessage] = useState("");
  const form = useForm<ProfileForm>({ resolver: zodResolver(profileSchema) });
  const userQuery = useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<User>("/auth/me/")).data,
    initialData: auth.user ?? undefined,
  });
  const mutation = useMutation({
    mutationFn: async (values: ProfileForm) =>
      (
        await api.patch<User>("/auth/me/", {
          name: values.name,
          profile: { email: values.email, gender: values.gender },
        })
      ).data,
    onSuccess(user) {
      auth.setUser(user);
      setMessage("اطلاعات شما با موفقیت ذخیره شد.");
    },
  });

  useEffect(() => {
    if (userQuery.data) {
      form.reset({
        name: userQuery.data.name,
        email: userQuery.data.profile?.email ?? "",
        gender: userQuery.data.profile?.gender ?? "not_specified",
      });
    }
  }, [form, userQuery.data]);

  async function logout() {
    await auth.logout();
    navigate("/");
  }

  return (
    <main className="profile-page">
      <header className="simple-header">
        <BrandLogo className="brand-mark" />
      </header>
      <section className="profile-card container">
        <div className="profile-heading">
          <span className="avatar-placeholder">
            <UserRound aria-hidden="true" />
          </span>
          <div>
            <p className="eyebrow">حساب کاربری</p>
            <h1>اطلاعات شخصی</h1>
            <p className="muted">{auth.user?.phone}</p>
          </div>
        </div>
        {userQuery.isError ? (
          <p className="alert alert-error">{getApiError(userQuery.error)}</p>
        ) : (
          <form
            className="profile-form"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          >
            <div className="field">
              <label htmlFor="name">نام و نام خانوادگی</label>
              <input id="name" {...form.register("name")} />
              {form.formState.errors.name && (
                <p className="field-error">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>
            <div className="field">
              <label htmlFor="email">ایمیل (اختیاری)</label>
              <input
                id="email"
                dir="ltr"
                type="email"
                {...form.register("email")}
              />
              {form.formState.errors.email && (
                <p className="field-error">
                  {form.formState.errors.email.message}
                </p>
              )}
            </div>
            <div className="field">
              <label htmlFor="gender">جنسیت</label>
              <select id="gender" {...form.register("gender")}>
                <option value="not_specified">ترجیح می‌دهم نگویم</option>
                <option value="woman">زن</option>
                <option value="man">مرد</option>
              </select>
            </div>
            {mutation.isError && (
              <p className="alert alert-error">{getApiError(mutation.error)}</p>
            )}
            {message && <p className="alert alert-success">{message}</p>}
            <div className="form-actions">
              <button
                className="button button-primary"
                disabled={mutation.isPending}
              >
                {mutation.isPending && (
                  <LoaderCircle className="spin" size={18} />
                )}{" "}
                ذخیره تغییرات
              </button>
              <button
                className="button button-outline"
                type="button"
                onClick={logout}
              >
                <LogOut size={18} /> خروج
              </button>
            </div>
          </form>
        )}
      </section>
    </main>
  );
}
