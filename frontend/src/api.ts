import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
export const api = axios.create({ baseURL });

export const tokens = {
  get access() { return localStorage.getItem("ff_access"); },
  get refresh() { return localStorage.getItem("ff_refresh"); },
  set(access: string, refresh: string) { localStorage.setItem("ff_access", access); localStorage.setItem("ff_refresh", refresh); },
  clear() { localStorage.removeItem("ff_access"); localStorage.removeItem("ff_refresh"); },
};

api.interceptors.request.use((cfg) => {
  if (tokens.access) cfg.headers.Authorization = `Bearer ${tokens.access}`;
  return cfg;
});

let refreshing: Promise<string> | null = null;

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const isAuthCall = original?.url?.includes("/auth/");
    if (error.response?.status === 401 && original && !original._retry && !isAuthCall && tokens.refresh) {
      original._retry = true;
      try {
        refreshing ??= axios
          .post(`${baseURL}/auth/refresh`, { refresh_token: tokens.refresh })
          .then((r) => { tokens.set(r.data.access_token, r.data.refresh_token); return r.data.access_token as string; })
          .finally(() => { refreshing = null; });
        const token = await refreshing;
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        tokens.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(e: unknown): string {
  const err = e as AxiosError<{ detail?: string | { msg: string; loc: string[] }[] }>;
  const d = err.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => `${x.loc.slice(1).join(".")}: ${x.msg}`).join("; ");
  return err.message || "Something went wrong";
}
