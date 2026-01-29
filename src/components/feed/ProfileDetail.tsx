"use client";

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import {
  calculateAge,
  generateGradientFromId,
  MARITAL_LABELS,
  RELIGIOUS_LABELS,
  PRAYER_LABELS,
  EMPLOYMENT_LABELS,
} from "@/lib/utils";
import {
  ArrowLeft,
  MapPin,
  Heart,
  Star,
  Ruler,
  Weight,
  BookOpen,
  Briefcase,
  MessageCircle,
} from "lucide-react";

interface ProfileDetailProps {
  profile: {
    id: string;
    userId: string;
    name: string;
    gender: string;
    birthYear: number;
    region: string;
    nationality: string;
    maritalStatus: string;
    height?: number;
    weight?: number;
    religiousLevel?: string;
    prayerFrequency?: string;
    education?: string;
    profession?: string;
    employmentStatus?: string;
    bio?: string;
    isTop: boolean;
    user: {
      id: string;
    };
  };
  onBack: () => void;
}

export function ProfileDetail({ profile, onBack }: ProfileDetailProps) {
  const { initData, hasActiveTariff, requestsLeft, setTariffInfo } = useAppStore();
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const age = calculateAge(profile.birthYear);
  const gradient = generateGradientFromId(profile.id);

  const handleSendRequest = async () => {
    if (!hasActiveTariff || requestsLeft <= 0) {
      setError("Tarif sotib oling yoki so'rovlar soni tugagan");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initData,
          receiverId: profile.user.id,
          message: message.trim() || null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "So'rov yuborishda xato");
      }

      setIsSent(true);
      setShowRequestModal(false);
      setTariffInfo(hasActiveTariff, requestsLeft - 1);

      // Haptic feedback
      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("success");
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Xatolik yuz berdi";
      setError(errorMessage);
      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen pb-24">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 border-b">
        <div className="flex items-center p-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 rounded-full hover:bg-gray-100"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <h1 className="ml-2 text-lg font-semibold">Profil</h1>
        </div>
      </div>

      {/* Profile Header */}
      <div
        className="h-48 flex items-center justify-center text-white text-6xl font-bold"
        style={{ background: gradient }}
      >
        {profile.name.charAt(0).toUpperCase()}
      </div>

      {/* Profile Info */}
      <div className="p-4 -mt-8">
        <div className="card p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold">{profile.name}</h2>
                {profile.isTop && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-700 text-sm font-medium rounded-full">
                    <Star className="w-4 h-4 fill-current" />
                    TOP
                  </span>
                )}
              </div>
              <p className="text-gray-500 mt-1">
                {age} yosh, {profile.nationality}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-3 text-gray-600">
            <MapPin className="w-5 h-5" />
            <span>{profile.region}</span>
          </div>

          <div className="mt-4 pt-4 border-t">
            <div className="flex flex-wrap gap-2">
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

        {/* Details */}
        <div className="mt-4 space-y-4">
          {/* Jismoniy */}
          {(profile.height || profile.weight) && (
            <div className="card p-4">
              <h3 className="font-semibold mb-3">Jismoniy ko'rsatkichlar</h3>
              <div className="grid grid-cols-2 gap-4">
                {profile.height && (
                  <div className="flex items-center gap-2">
                    <Ruler className="w-5 h-5 text-gray-400" />
                    <span>{profile.height} sm</span>
                  </div>
                )}
                {profile.weight && (
                  <div className="flex items-center gap-2">
                    <Weight className="w-5 h-5 text-gray-400" />
                    <span>{profile.weight} kg</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Diniy */}
          {profile.prayerFrequency && (
            <div className="card p-4">
              <h3 className="font-semibold mb-3">Diniy ma'lumotlar</h3>
              <p className="text-gray-600">
                Namoz: {PRAYER_LABELS[profile.prayerFrequency as keyof typeof PRAYER_LABELS]}
              </p>
            </div>
          )}

          {/* Ta'lim va kasb */}
          {(profile.education || profile.profession) && (
            <div className="card p-4">
              <h3 className="font-semibold mb-3">Ta'lim va kasb</h3>
              <div className="space-y-2">
                {profile.education && (
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-5 h-5 text-gray-400" />
                    <span>{profile.education}</span>
                  </div>
                )}
                {profile.profession && (
                  <div className="flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-gray-400" />
                    <span>{profile.profession}</span>
                  </div>
                )}
                {profile.employmentStatus && (
                  <span className="text-gray-500 text-sm">
                    {EMPLOYMENT_LABELS[profile.employmentStatus as keyof typeof EMPLOYMENT_LABELS]}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Bio */}
          {profile.bio && (
            <div className="card p-4">
              <h3 className="font-semibold mb-3">O'zi haqida</h3>
              <p className="text-gray-600 whitespace-pre-wrap">{profile.bio}</p>
            </div>
          )}
        </div>
      </div>

      {/* Request Modal */}
      {showRequestModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end">
          <div className="bg-white w-full rounded-t-3xl p-4 animate-slide-up safe-area-bottom">
            <div className="w-12 h-1 bg-gray-300 rounded-full mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-4">Taklifnoma yuborish</h3>

            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Xabar qo'shing (ixtiyoriy)"
              maxLength={300}
            />

            {error && (
              <p className="text-red-500 text-sm mt-2">{error}</p>
            )}

            <div className="flex gap-3 mt-4">
              <Button
                variant="secondary"
                onClick={() => setShowRequestModal(false)}
                className="flex-1"
              >
                Bekor qilish
              </Button>
              <Button
                onClick={handleSendRequest}
                isLoading={isLoading}
                className="flex-1"
              >
                Yuborish
              </Button>
            </div>

            <p className="text-center text-gray-500 text-sm mt-3">
              Qolgan so'rovlar: {requestsLeft}
            </p>
          </div>
        </div>
      )}

      {/* Footer Actions */}
      <div className="fixed bottom-20 left-0 right-0 p-4 bg-white/80 backdrop-blur-lg border-t">
        {isSent ? (
          <div className="text-center text-green-600 font-medium py-3">
            Taklifnoma yuborildi!
          </div>
        ) : (
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                // Add to favorites logic
                window.Telegram?.WebApp.HapticFeedback.impactOccurred("light");
              }}
              className="flex-1"
              leftIcon={<Heart className="w-5 h-5" />}
            >
              Saqlash
            </Button>
            <Button
              onClick={() => {
                if (!hasActiveTariff) {
                  setError("Avval tarif sotib oling");
                  return;
                }
                setShowRequestModal(true);
              }}
              className="flex-1"
              leftIcon={<MessageCircle className="w-5 h-5" />}
            >
              Taklifnoma
            </Button>
          </div>
        )}
        {error && !showRequestModal && (
          <p className="text-red-500 text-center text-sm mt-2">{error}</p>
        )}
      </div>
    </div>
  );
}
