import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { authStorage } from "../lib/auth-storage";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
  timeout: 15_000,
  headers: { Accept: "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const access = authStorage.getTokens()?.access;
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshRequest: Promise<string> | null = null;

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const request = error.config as
    (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
  const refresh = authStorage.getTokens()?.refresh;
  if (
    error.response?.status !== 401 ||
    !request ||
    request._retried ||
    !refresh
  ) {
    return Promise.reject(error);
  }

  request._retried = true;
  refreshRequest ??= axios
    .post<{ access: string; refresh?: string }>(
      `${api.defaults.baseURL}/auth/token/refresh/`,
      { refresh },
    )
    .then(({ data }) => {
      authStorage.setTokens({
        access: data.access,
        refresh: data.refresh ?? refresh,
      });
      return data.access;
    })
    .catch((refreshError) => {
      authStorage.clear();
      throw refreshError;
    })
    .finally(() => {
      refreshRequest = null;
    });

  request.headers.Authorization = `Bearer ${await refreshRequest}`;
  return api(request);
});

export function getApiError(error: unknown): string {
  if (!axios.isAxiosError(error)) return "خطایی رخ داد؛ دوباره تلاش کنید.";
  const data = error.response?.data as Record<string, unknown> | undefined;
  const detail = data?.detail;
  if (Array.isArray(detail)) return String(detail[0]);
  if (typeof detail === "string") return detail;
  if (data) {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return String(first[0]);
    if (typeof first === "string") return first;
  }
  return "ارتباط با سرور برقرار نشد؛ دوباره تلاش کنید.";
}
