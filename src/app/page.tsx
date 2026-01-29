"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { Loader } from "@/components/ui/Loader";
import { Onboarding } from "@/components/onboarding/Onboarding";
import { MainApp } from "@/components/app/MainApp";

export default function Home() {
  const {
    user,
    setUser,
    setTelegramUser,
    setInitData,
    isLoading,
    setIsLoading,
    setUnreadCount,
    setPendingRequestsCount,
    setTariffInfo,
  } = useAppStore();

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initApp = async () => {
      try {
        // Telegram WebApp ni tekshirish
        const tg = window.Telegram?.WebApp;
        if (!tg) {
          setError("Bu ilova faqat Telegram orqali ochiladi");
          setIsLoading(false);
          return;
        }

        // WebApp ni kengaytirish
        tg.ready();
        tg.expand();

        // Telegram foydalanuvchi ma'lumotlarini olish
        const telegramUser = tg.initDataUnsafe.user;
        if (!telegramUser) {
          setError("Telegram foydalanuvchi ma'lumotlari topilmadi");
          setIsLoading(false);
          return;
        }

        setTelegramUser(telegramUser);
        setInitData(tg.initData);

        // Serverda autentifikatsiya
        const response = await fetch("/api/auth", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ initData: tg.initData }),
        });

        if (!response.ok) {
          throw new Error("Autentifikatsiya xatosi");
        }

        const data = await response.json();
        setUser(data.user);
        setUnreadCount(data.unreadCount || 0);
        setPendingRequestsCount(data.pendingRequestsCount || 0);
        setTariffInfo(data.hasActiveTariff || false, data.requestsLeft || 0);
      } catch (err) {
        console.error("Xato:", err);
        setError("Ilovani yuklashda xatolik yuz berdi");
      } finally {
        setIsLoading(false);
      }
    };

    initApp();
  }, [
    setUser,
    setTelegramUser,
    setInitData,
    setIsLoading,
    setUnreadCount,
    setPendingRequestsCount,
    setTariffInfo,
  ]);

  if (isLoading) {
    return <Loader />;
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <div className="text-6xl mb-4">😔</div>
          <h1 className="text-xl font-semibold mb-2">Xatolik</h1>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  // Onboarding - profil to'ldirilmagan
  if (!user?.profile?.isComplete) {
    return <Onboarding />;
  }

  // Asosiy ilova
  return <MainApp />;
}
