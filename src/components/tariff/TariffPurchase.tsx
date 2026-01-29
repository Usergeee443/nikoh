"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/Button";
import { LoaderSmall } from "@/components/ui/Loader";
import { TARIFF_INFO } from "@/lib/utils";
import { ArrowLeft, Check, Star, Zap, Crown, Copy, Clock } from "lucide-react";

interface TariffPurchaseProps {
  onBack: () => void;
}

type TariffType = "KUMUSH" | "OLTIN" | "VIP";

export function TariffPurchase({ onBack }: TariffPurchaseProps) {
  const { initData, setTariffInfo } = useAppStore();
  const [selectedTariff, setSelectedTariff] = useState<TariffType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTariffs, setActiveTariffs] = useState<unknown[]>([]);
  const [pendingPayments, setPendingPayments] = useState<unknown[]>([]);
  const [showPaymentInfo, setShowPaymentInfo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const fetchTariffs = async () => {
      try {
        const response = await fetch(
          `/api/tariff?initData=${encodeURIComponent(initData || "")}`
        );
        if (!response.ok) throw new Error();

        const data = await response.json();
        setActiveTariffs(data.activeTariffs);
        setPendingPayments(data.pendingPayments);
      } catch {
        console.error("Tarif yuklash xatosi");
      } finally {
        setIsLoading(false);
      }
    };

    fetchTariffs();
  }, [initData]);

  const handlePurchase = async () => {
    if (!selectedTariff) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/tariff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initData,
          tariffType: selectedTariff,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Xatolik yuz berdi");
      }

      setSuccess(true);
      setShowPaymentInfo(false);

      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("success");
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Xatolik yuz berdi";
      setError(errorMessage);
      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyCardNumber = () => {
    const cardNumber = process.env.NEXT_PUBLIC_PAYMENT_CARD_NUMBER || "8600 1234 5678 9012";
    navigator.clipboard.writeText(cardNumber.replace(/\s/g, ""));
    window.Telegram?.WebApp.HapticFeedback.notificationOccurred("success");
  };

  const tariffs: { type: TariffType; icon: typeof Star }[] = [
    { type: "KUMUSH", icon: Star },
    { type: "OLTIN", icon: Zap },
    { type: "VIP", icon: Crown },
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoaderSmall />
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4">
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="text-xl font-semibold mb-2">So'rov yuborildi!</h2>
        <p className="text-gray-500 text-center mb-6">
          To'lovingiz tekshirilgandan so'ng tarif faollashtiriladi
        </p>
        <Button onClick={onBack}>Orqaga</Button>
      </div>
    );
  }

  if (showPaymentInfo && selectedTariff) {
    const tariff = TARIFF_INFO[selectedTariff];

    return (
      <div className="min-h-screen">
        <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 border-b">
          <div className="flex items-center p-4">
            <button
              onClick={() => setShowPaymentInfo(false)}
              className="p-2 -ml-2 rounded-full hover:bg-gray-100"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <h1 className="ml-2 text-lg font-semibold">To'lov</h1>
          </div>
        </div>

        <div className="p-4 space-y-4">
          <div className="card p-4">
            <h3 className="font-semibold mb-2">Tanlangan tarif</h3>
            <div className="flex items-center justify-between">
              <span>{tariff.name}</span>
              <span className="font-semibold">
                {tariff.price.toLocaleString()} so'm
              </span>
            </div>
          </div>

          <div className="card p-4">
            <h3 className="font-semibold mb-3">Karta raqami</h3>
            <div className="flex items-center justify-between bg-gray-50 p-3 rounded-xl">
              <div>
                <p className="font-mono text-lg">8600 1234 5678 9012</p>
                <p className="text-sm text-gray-500">NIKOH APP</p>
              </div>
              <button
                onClick={copyCardNumber}
                className="p-2 bg-white rounded-lg shadow-sm"
              >
                <Copy className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>

          <div className="card p-4">
            <h3 className="font-semibold mb-2">Qanday to'lash kerak?</h3>
            <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
              <li>Yuqoridagi karta raqamiga pul o'tkazing</li>
              <li>Chekni saqlang</li>
              <li>Botga chekni yuboring</li>
              <li>To'lov tasdiqlanguncha kuting</li>
            </ol>
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-600 rounded-xl text-sm">
              {error}
            </div>
          )}

          <Button
            onClick={handlePurchase}
            isLoading={isSubmitting}
            className="w-full"
          >
            To'lovni tasdiqladim
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 border-b">
        <div className="flex items-center p-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 rounded-full hover:bg-gray-100"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <h1 className="ml-2 text-lg font-semibold">Tariflar</h1>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Pending Payment Warning */}
        {pendingPayments.length > 0 && (
          <div className="card p-4 bg-yellow-50 border-yellow-200">
            <div className="flex items-center gap-2 text-yellow-700">
              <Clock className="w-5 h-5" />
              <span className="font-medium">To'lovingiz tekshirilmoqda</span>
            </div>
          </div>
        )}

        {/* Tariff Cards */}
        {tariffs.map(({ type, icon: Icon }) => {
          const tariff = TARIFF_INFO[type];
          const isSelected = selectedTariff === type;

          return (
            <div
              key={type}
              onClick={() => setSelectedTariff(type)}
              className={`card p-4 cursor-pointer transition-all ${
                isSelected
                  ? "ring-2 ring-blue-500 shadow-md"
                  : "hover:shadow-md"
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center"
                  style={{ backgroundColor: `${tariff.color}20` }}
                >
                  <Icon className="w-6 h-6" style={{ color: tariff.color }} />
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-lg">{tariff.name}</h3>
                    <span className="font-bold text-lg">
                      {tariff.price.toLocaleString()} so'm
                    </span>
                  </div>

                  <ul className="mt-2 space-y-1">
                    <li className="flex items-center gap-2 text-sm text-gray-600">
                      <Check className="w-4 h-4 text-green-500" />
                      {tariff.requests} ta taklifnoma
                    </li>
                    <li className="flex items-center gap-2 text-sm text-gray-600">
                      <Check className="w-4 h-4 text-green-500" />
                      {tariff.listingDays} kun e'lon
                    </li>
                    {tariff.topDays > 0 && (
                      <li className="flex items-center gap-2 text-sm text-gray-600">
                        <Check className="w-4 h-4 text-green-500" />
                        {tariff.topDays} kun TOP
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          );
        })}

        {/* Purchase Button */}
        <Button
          onClick={() => setShowPaymentInfo(true)}
          disabled={!selectedTariff || pendingPayments.length > 0}
          className="w-full"
        >
          Sotib olish
        </Button>
      </div>
    </div>
  );
}
