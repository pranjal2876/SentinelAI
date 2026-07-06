// Auth state (Zustand) — persists nothing beyond localStorage tokens.
import { create } from 'zustand';
import { authApi } from '@/services/api';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  fetchMe: () => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  async login(username, password) {
    await authApi.login(username, password);
    const user = await authApi.me();
    set({ user });
  },
  async fetchMe() {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ user: null, loading: false });
      return;
    }
    try {
      const user = await authApi.me();
      set({ user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
  logout() {
    authApi.logout();
    set({ user: null });
  },
}));
