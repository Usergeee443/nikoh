"use client";

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/Button";
import { TariffPurchase } from "@/components/tariff/TariffPurchase";
import {
  calculateAge,
  generateGradientFromId,
  MARITAL_LABELS,
  RELIGIOUS_LABELS,
  REGIONS,
} from "@/lib/utils";
import {
  Settings,
  CreditCard,
  ToggleLeft,
  ToggleRight,
  ChevronRight,
  LogOut,
  Shield,
} from "lucide-react";

export function Profile() {
  const { user, initData, setUser, hasActiveTariff, requestsLeft } = useAppStore();
  const [showTariff, setShowTariff] = useState(false);
  const [isActivating, setIsActivating] = useState(false);
  const profile = user?.profile;

  if (!profile) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Profil topilmadi</p>
      </div>
    );
  }

  const age = calculateAge(profile.birthYear);
  const gradient = generateGradientFromId(profile.id);

  const handleToggleActive = async () => {
    setIsActivating(true);

    try {
      const response = await fetch("/api/profile/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initData }),
      });

      if (!response.ok) throw new Error("Xatolik");

      const data = await response.json();
      setUser({
        ...user!,
        profile: data.profile,
      });

      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("success");
    } catch (error) {
      console.error("Toggle xatosi:", error);
      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("error");
    } finally {
      setIsActivating(false);
    }
  };

  if (showTariff) {
    return <TariffPurchase onBack={() => setShowTariff(false)} />;
  }

  return (
    <div className="min-h-screen pb-24">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 p-4 border-b">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Profilim</h1>
          {user?.isAdmin && (
            <a
              href="/admin"
              className="flex items-center gap-1 text-sm text-blue-500"
            >
              <Shield className="w-4 h-4" />
              Admin
            </a>
          )}
        </div>
      </div>

      {/* Profile Header */}
      <div className="p-4">
        <div className="card overflow-hidden">
          <div
            className="h-24 flex items-center justify-center"
            style={{ background: gradient }}
          >
            <span className="text-4xl text-white font-bold">
              {profile.name.charAt(0).toUpperCase()}
            </span>
          </div>

          <div className="p-4 -mt-8">
            <div
              className="w-16 h-16 rounded-full border-4 border-white flex items-center justify-center text-white text-2xl font-bold mx-auto"
              style={{ background: gradient }}
            >
              {profile.name.charAt(0).toUpperCase()}
            </div>

            <div className="text-center mt-3">
              <h2 className="text-xl font-semibold">{profile.name}</h2>
              <p className="text-gray-500">
                {age} yosh, {profile.region}
              </p>
              <div className="flex justify-center gap-2 mt-2">
                <span className="badge badge-primary">
                  {MARITAL_LABELS[profile.maritalStatus as keyof typeof MARITAL_LABELS]}
                </span>
                {profile.religiousLevel && (
                  <span className="badge badge-success">
                    {RELIGIOUS_LABELS[profile.religiousLevel as keyof typeof RELIGIOUS_LABELS]}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tariff Info */}
      <div className="px-4 mb-4">
        <div
          onClick={() => setShowTariff(true)}
          className="card p-4 cursor-pointer hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-medium">Tarif</h3>
                <p className="text-sm text-gray-500">
                  {hasActiveTariff
                    ? `${requestsLeft} ta so'rov qoldi`
                    : "Tarif sotib oling"}
                </p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Profile Status */}
      <div className="px-4 mb-4">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Profilni ko'rsatish</h3>
              <p className="text-sm text-gray-500">
                {profile.isActive
                  ? "Profilingiz boshqalarga ko'rinadi"
                  : "Profilingiz yashirin"}
              </p>
            </div>
            <button
              onClick={handleToggleActive}
              disabled={isActivating || !hasActiveTariff}
              className="p-2 disabled:opacity-50"
            >
              {profile.isActive ? (
                <ToggleRight className="w-10 h-10 text-green-500" />
              ) : (
                <ToggleLeft className="w-10 h-10 text-gray-400" />
              )}
            </button>
          </div>
          {!hasActiveTariff && (
            <p className="text-xs text-orange-500 mt-2">
              Profilni yoqish uchun tarif sotib oling
            </p>
          )}
        </div>
      </div>

      {/* Profile Details */}
      <div className="px-4 space-y-3">
        <div className="card p-4">
          <h3 className="font-medium mb-3">Ma'lumotlar</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Jins</span>
              <span>{profile.gender === "MALE" ? "Erkak" : "Ayol"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Tug'ilgan yil</span>
              <span>{profile.birthYear}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Viloyat</span>
              <span>{profile.region}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Millat</span>
              <span>{profile.nationality}</span>
            </div>
            {profile.height && (
              <div className="flex justify-between">
                <span className="text-gray-500">Bo'y</span>
                <span>{profile.height} sm</span>
              </div>
            )}
            {profile.weight && (
              <div className="flex justify-between">
                <span className="text-gray-500">Vazn</span>
                <span>{profile.weight} kg</span>
              </div>
            )}
          </div>
        </div>

        {profile.bio && (
          <div className="card p-4">
            <h3 className="font-medium mb-2">O'zim haqimda</h3>
            <p className="text-sm text-gray-600">{profile.bio}</p>
          </div>
        )}
      </div>

      {/* Logout */}
      <div className="px-4 mt-6">
        <button
          onClick={() => {
            window.Telegram?.WebApp.close();
          }}
          className="w-full flex items-center justify-center gap-2 py-3 text-red-500"
        >
          <LogOut className="w-5 h-5" />
          <span>Chiqish</span>
        </button>
      </div>
    </div>
  );
}
