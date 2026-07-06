// Central Axios client + typed API wrappers.
import axios, { AxiosInstance } from 'axios';
import type {
  Camera,
  DashboardStats,
  Threat,
  ThreatExplanation,
  User,
  Zone,
} from '@/types';

const BASE = import.meta.env.VITE_API_BASE_URL || '';

export const http: AxiosInstance = axios.create({
  baseURL: `${BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

// Attach bearer token from localStorage on every request.
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, attempt a one-time refresh, else redirect to login.
http.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token');
      if (refresh && !error.config._retry) {
        error.config._retry = true;
        try {
          const { data } = await axios.post(`${BASE}/api/v1/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return http(error.config);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  },
);

// ---- Auth ----
export const authApi = {
  async login(username: string, password: string) {
    const form = new URLSearchParams({ username, password });
    const { data } = await axios.post(`${BASE}/api/v1/auth/login`, form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
  },
  me: () => http.get<User>('/auth/me').then((r) => r.data),
  logout() {
    localStorage.clear();
  },
};

// ---- Cameras ----
export const cameraApi = {
  list: () => http.get<Camera[]>('/cameras').then((r) => r.data),
  create: (payload: Partial<Camera>) =>
    http.post<Camera>('/cameras', payload).then((r) => r.data),
  update: (id: string, payload: Partial<Camera>) =>
    http.patch<Camera>(`/cameras/${id}`, payload).then((r) => r.data),
  remove: (id: string) => http.delete(`/cameras/${id}`),
  start: (id: string) => http.post(`/cameras/${id}/start`),
  stop: (id: string) => http.post(`/cameras/${id}/stop`),
};

// ---- Threats ----
export const threatApi = {
  list: (params: Record<string, unknown> = {}) =>
    http.get<Threat[]>('/threats', { params }).then((r) => r.data),
  acknowledge: (id: number) =>
    http.post<Threat>(`/threats/${id}/acknowledge`).then((r) => r.data),
  explain: (id: number) =>
    http.get<ThreatExplanation>(`/threats/${id}/explain`).then((r) => r.data),
};

// ---- Zones ----
export const zoneApi = {
  list: (cameraId?: string) =>
    http
      .get<Zone[]>('/zones', { params: cameraId ? { camera_id: cameraId } : {} })
      .then((r) => r.data),
  create: (payload: Partial<Zone>) =>
    http.post<Zone>('/zones', payload).then((r) => r.data),
  remove: (zoneId: string) => http.delete(`/zones/${zoneId}`),
};

// ---- Analytics ----
export const analyticsApi = {
  dashboard: () =>
    http.get<DashboardStats>('/analytics/dashboard').then((r) => r.data),
  reportUrl: (start: number, end: number, fmt: 'pdf' | 'xlsx', cameraId?: string) => {
    const p = new URLSearchParams({ start: String(start), end: String(end), fmt });
    if (cameraId) p.set('camera_id', cameraId);
    return `${BASE}/api/v1/analytics/report?${p.toString()}`;
  },
};
