"use client";

import { create } from "zustand";
import type { Profile, User } from "@prisma/client";

interface UserWithProfile extends User {
  profile: Profile | null;
}

interface AppState {
  // Foydalanuvchi
  user: UserWithProfile | null;
  setUser: (user: UserWithProfile | null) => void;

  // Telegram WebApp
  telegramUser: {
    id: number;
    first_name?: string;
    last_name?: string;
    username?: string;
  } | null;
  setTelegramUser: (user: AppState["telegramUser"]) => void;
  initData: string | null;
  setInitData: (data: string | null) => void;

  // UI holati
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;

  // O'qilmagan xabarlar soni
  unreadCount: number;
  setUnreadCount: (count: number) => void;

  // Yangi so'rovlar soni
  pendingRequestsCount: number;
  setPendingRequestsCount: (count: number | ((prev: number) => number)) => void;

  // Aktiv tarif
  hasActiveTariff: boolean;
  requestsLeft: number;
  setTariffInfo: (hasActive: boolean, requestsLeft: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Foydalanuvchi
  user: null,
  setUser: (user) => set({ user }),

  // Telegram
  telegramUser: null,
  setTelegramUser: (telegramUser) => set({ telegramUser }),
  initData: null,
  setInitData: (initData) => set({ initData }),

  // UI
  isLoading: true,
  setIsLoading: (isLoading) => set({ isLoading }),

  // Xabarlar
  unreadCount: 0,
  setUnreadCount: (unreadCount) => set({ unreadCount }),

  // So'rovlar
  pendingRequestsCount: 0,
  setPendingRequestsCount: (countOrFn) =>
    set((state) => ({
      pendingRequestsCount:
        typeof countOrFn === "function"
          ? countOrFn(state.pendingRequestsCount)
          : countOrFn,
    })),

  // Tarif
  hasActiveTariff: false,
  requestsLeft: 0,
  setTariffInfo: (hasActiveTariff, requestsLeft) =>
    set({ hasActiveTariff, requestsLeft }),
}));
