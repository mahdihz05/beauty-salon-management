import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  CheckCircle2,
  LoaderCircle,
  Smartphone,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation } from "wouter";
import { z } from "zod";
import { api, getApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import type { AuthResponse, User } from "../types/auth";

const phoneSchema = z.object({
  phone: z
    .string()
    .regex(/^(?:\+98|0098|0)?9\d{9}$/, "شماره موبایل معتبر وارد کنید."),
});
const codeSchema = z.object({
  code: z.string().regex(/^\d{6}$/, "کد ۶ رقمی را کامل وارد کنید."),
});
type PhoneForm = z.infer<typeof phoneSchema>;
type CodeForm = z.infer<typeof codeSchema>;

function homeForUser(user: User, isNewUser: boolean) {
  if (isNewUser) return "/account/profile";
  switch (user.role) {
    case "admin":
      return "/admin/dashboard";
    case "salon_owner":
    case "branch_manager":
      return "/salon/dashboard";
    case "receptionist":
    case "staff":
      return "/salon/calendar";
    case "finance":
      return "/finance/payments";
    case "support":
      return "/support/tickets";
    default:
      return "/";
  }
}

export function LoginPage() {
  const [, navigate] = useLocation();
  const nextPath = new URLSearchParams(window.location.search).get("next");
  const auth = useAuth();
  const [phone, setPhone] = useState("");
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [serverError, setServerError] = useState("");
  const phoneForm = useForm<PhoneForm>({ resolver: zodResolver(phoneSchema) });
  const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });

  async function sendCode(values: PhoneForm) {
    setServerError("");
    try {
      const { data } = await api.post<{ debug_code?: string }>(
        "/auth/otp/request/",
        values,
      );
      setPhone(values.phone);
      setDebugCode(data.debug_code ?? null);
    } catch (error) {
      setServerError(getApiError(error));
    }
  }

  async function verifyCode(values: CodeForm) {
    setServerError("");
    try {
      const { data } = await api.post<AuthResponse>("/auth/otp/verify/", {
        phone,
        code: values.code,
      });
      auth.login(data);
      navigate(nextPath || homeForUser(data.user, data.is_new_user));
    } catch (error) {
      setServerError(getApiError(error));
    }
  }

  function editPhone() {
    setPhone("");
    setDebugCode(null);
    setServerError("");
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <a className="brand-mark" href="/">
          استیچ
        </a>
        {!phone ? (
          <>
            <span className="auth-icon">
              <Smartphone aria-hidden="true" />
            </span>
            <h1 id="login-title">ورود یا ثبت‌نام</h1>
            <p className="muted">برای ادامه شماره موبایل خود را وارد کنید.</p>
            <form onSubmit={phoneForm.handleSubmit(sendCode)} noValidate>
              <label htmlFor="phone">شماره موبایل</label>
              <input
                id="phone"
                inputMode="tel"
                dir="ltr"
                autoComplete="tel"
                placeholder="0912 123 4567"
                aria-invalid={Boolean(phoneForm.formState.errors.phone)}
                {...phoneForm.register("phone")}
              />
              {phoneForm.formState.errors.phone && (
                <p className="field-error">
                  {phoneForm.formState.errors.phone.message}
                </p>
              )}
              {serverError && (
                <p className="alert alert-error">{serverError}</p>
              )}
              <button
                className="button button-primary button-block"
                disabled={phoneForm.formState.isSubmitting}
              >
                {phoneForm.formState.isSubmitting && (
                  <LoaderCircle className="spin" size={18} />
                )}
                دریافت کد ورود
              </button>
            </form>
          </>
        ) : (
          <>
            <span className="auth-icon">
              <CheckCircle2 aria-hidden="true" />
            </span>
            <h1 id="login-title">تأیید شماره موبایل</h1>
            <p className="muted">
              کد ارسال‌شده به <bdi>{phone}</bdi> را وارد کنید.
            </p>
            {debugCode && (
              <p className="alert alert-info">
                کد محیط توسعه: <bdi>{debugCode}</bdi>
              </p>
            )}
            <form onSubmit={codeForm.handleSubmit(verifyCode)} noValidate>
              <label htmlFor="code">کد ۶ رقمی</label>
              <input
                id="code"
                className="otp-input"
                inputMode="numeric"
                dir="ltr"
                maxLength={6}
                autoComplete="one-time-code"
                autoFocus
                aria-invalid={Boolean(codeForm.formState.errors.code)}
                {...codeForm.register("code")}
              />
              {codeForm.formState.errors.code && (
                <p className="field-error">
                  {codeForm.formState.errors.code.message}
                </p>
              )}
              {serverError && (
                <p className="alert alert-error">{serverError}</p>
              )}
              <button
                className="button button-primary button-block"
                disabled={codeForm.formState.isSubmitting}
              >
                {codeForm.formState.isSubmitting && (
                  <LoaderCircle className="spin" size={18} />
                )}
                ورود به استیچ
              </button>
              <button className="text-button" type="button" onClick={editPhone}>
                <ArrowRight size={16} /> اصلاح شماره موبایل
              </button>
            </form>
          </>
        )}
      </section>
    </main>
  );
}
