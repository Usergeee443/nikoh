"use client";

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/Input";
import {
  REGIONS,
  NATIONALITIES,
  PRAYER_LABELS,
  RELIGIOUS_LABELS,
  MARITAL_LABELS,
  EMPLOYMENT_LABELS,
} from "@/lib/utils";
import { ChevronLeft, ChevronRight, Check } from "lucide-react";

type Gender = "MALE" | "FEMALE";
type MaritalStatus = "SINGLE" | "DIVORCED" | "WIDOWED";
type PrayerFrequency = "ALWAYS" | "OFTEN" | "SOMETIMES" | "RARELY" | "NEVER";
type ReligiousLevel = "VERY_RELIGIOUS" | "RELIGIOUS" | "MODERATE" | "NOT_RELIGIOUS";
type EmploymentStatus = "EMPLOYED" | "UNEMPLOYED" | "STUDENT" | "SELF_EMPLOYED" | "RETIRED";

interface ProfileData {
  gender: Gender | "";
  name: string;
  birthYear: string;
  region: string;
  nationality: string;
  maritalStatus: MaritalStatus | "";
  height: string;
  weight: string;
  prayerFrequency: PrayerFrequency | "";
  fasting: boolean | null;
  religiousLevel: ReligiousLevel | "";
  education: string;
  profession: string;
  employmentStatus: EmploymentStatus | "";
  bio: string;
  partnerAgeMin: string;
  partnerAgeMax: string;
  partnerRegion: string;
  partnerReligiousLevel: ReligiousLevel | "";
  partnerMaritalStatus: MaritalStatus | "";
}

export function Onboarding() {
  const { user, setUser, initData } = useAppStore();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<ProfileData>({
    gender: "",
    name: user?.firstName || "",
    birthYear: "",
    region: "",
    nationality: "",
    maritalStatus: "",
    height: "",
    weight: "",
    prayerFrequency: "",
    fasting: null,
    religiousLevel: "",
    education: "",
    profession: "",
    employmentStatus: "",
    bio: "",
    partnerAgeMin: "",
    partnerAgeMax: "",
    partnerRegion: "",
    partnerReligiousLevel: "",
    partnerMaritalStatus: "",
  });

  const updateField = (field: keyof ProfileData, value: string | boolean | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const validateStep = (): boolean => {
    switch (step) {
      case 1:
        if (!formData.gender || !formData.name || !formData.birthYear || !formData.region || !formData.nationality || !formData.maritalStatus) {
          setError("Barcha maydonlarni to'ldiring");
          return false;
        }
        const year = parseInt(formData.birthYear);
        if (year < 1960 || year > 2006) {
          setError("Tug'ilgan yil noto'g'ri");
          return false;
        }
        break;
      case 2:
        // Bo'yi va vazni ixtiyoriy
        break;
      case 3:
        if (!formData.religiousLevel) {
          setError("Diniylik darajasini tanlang");
          return false;
        }
        break;
      case 4:
        // Ixtiyoriy
        break;
      case 5:
        // Ixtiyoriy
        break;
    }
    return true;
  };

  const nextStep = () => {
    if (validateStep()) {
      setStep((prev) => Math.min(prev + 1, 5));
    }
  };

  const prevStep = () => {
    setStep((prev) => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (!validateStep()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initData,
          profile: {
            ...formData,
            birthYear: parseInt(formData.birthYear),
            height: formData.height ? parseInt(formData.height) : null,
            weight: formData.weight ? parseInt(formData.weight) : null,
            partnerAgeMin: formData.partnerAgeMin ? parseInt(formData.partnerAgeMin) : null,
            partnerAgeMax: formData.partnerAgeMax ? parseInt(formData.partnerAgeMax) : null,
          },
        }),
      });

      if (!response.ok) {
        throw new Error("Profilni saqlashda xatolik");
      }

      const data = await response.json();
      setUser(data.user);
    } catch (err) {
      console.error(err);
      setError("Xatolik yuz berdi. Qayta urinib ko'ring");
    } finally {
      setIsLoading(false);
    }
  };

  const currentYear = new Date().getFullYear();
  const birthYearOptions = Array.from({ length: 47 }, (_, i) => {
    const year = currentYear - 18 - i;
    return { value: year.toString(), label: year.toString() };
  });

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-lg font-semibold">Profil yaratish</h1>
          <span className="text-sm text-gray-500">{step}/5</span>
        </div>
        <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${(step / 5) * 100}%` }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 overflow-y-auto">
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-xl text-sm">
            {error}
          </div>
        )}

        {/* Step 1 - Shaxsiy ma'lumotlar */}
        {step === 1 && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-xl font-semibold mb-4">Shaxsiy ma'lumotlar</h2>

            {/* Jins */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Jinsingiz
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => updateField("gender", "MALE")}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    formData.gender === "MALE"
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200"
                  }`}
                >
                  <span className="text-2xl">👨</span>
                  <p className="mt-1 font-medium">Erkak</p>
                </button>
                <button
                  type="button"
                  onClick={() => updateField("gender", "FEMALE")}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    formData.gender === "FEMALE"
                      ? "border-pink-500 bg-pink-50"
                      : "border-gray-200"
                  }`}
                >
                  <span className="text-2xl">👩</span>
                  <p className="mt-1 font-medium">Ayol</p>
                </button>
              </div>
            </div>

            <Input
              label="Ismingiz"
              value={formData.name}
              onChange={(e) => updateField("name", e.target.value)}
              placeholder="Ismingizni kiriting"
            />

            <Select
              label="Tug'ilgan yilingiz"
              value={formData.birthYear}
              onChange={(e) => updateField("birthYear", e.target.value)}
              options={birthYearOptions}
              placeholder="Yilni tanlang"
            />

            <Select
              label="Viloyatingiz"
              value={formData.region}
              onChange={(e) => updateField("region", e.target.value)}
              options={REGIONS.map((r) => ({ value: r, label: r }))}
              placeholder="Viloyatni tanlang"
            />

            <Select
              label="Millatingiz"
              value={formData.nationality}
              onChange={(e) => updateField("nationality", e.target.value)}
              options={NATIONALITIES.map((n) => ({ value: n, label: n }))}
              placeholder="Millatni tanlang"
            />

            <Select
              label="Oilaviy holatingiz"
              value={formData.maritalStatus}
              onChange={(e) => updateField("maritalStatus", e.target.value)}
              options={Object.entries(MARITAL_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
              placeholder="Tanlang"
            />
          </div>
        )}

        {/* Step 2 - Jismoniy ma'lumotlar */}
        {step === 2 && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-xl font-semibold mb-4">Jismoniy ma'lumotlar</h2>
            <p className="text-gray-500 text-sm mb-4">
              Bu maydonlar ixtiyoriy, lekin profilingizni to'liqroq qiladi
            </p>

            <Input
              label="Bo'yingiz (sm)"
              type="number"
              value={formData.height}
              onChange={(e) => updateField("height", e.target.value)}
              placeholder="Masalan: 175"
              min={100}
              max={250}
            />

            <Input
              label="Vazningiz (kg)"
              type="number"
              value={formData.weight}
              onChange={(e) => updateField("weight", e.target.value)}
              placeholder="Masalan: 70"
              min={30}
              max={200}
            />
          </div>
        )}

        {/* Step 3 - Diniy ma'lumotlar */}
        {step === 3 && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-xl font-semibold mb-4">Diniy ma'lumotlar</h2>

            <Select
              label="Namoz o'qishingiz"
              value={formData.prayerFrequency}
              onChange={(e) => updateField("prayerFrequency", e.target.value)}
              options={Object.entries(PRAYER_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
              placeholder="Tanlang"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ro'za tutasizmi?
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => updateField("fasting", true)}
                  className={`p-3 rounded-xl border-2 transition-all ${
                    formData.fasting === true
                      ? "border-green-500 bg-green-50"
                      : "border-gray-200"
                  }`}
                >
                  Ha
                </button>
                <button
                  type="button"
                  onClick={() => updateField("fasting", false)}
                  className={`p-3 rounded-xl border-2 transition-all ${
                    formData.fasting === false
                      ? "border-gray-500 bg-gray-50"
                      : "border-gray-200"
                  }`}
                >
                  Yo'q
                </button>
              </div>
            </div>

            <Select
              label="Diniylik darajangiz"
              value={formData.religiousLevel}
              onChange={(e) => updateField("religiousLevel", e.target.value)}
              options={Object.entries(RELIGIOUS_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
              placeholder="Tanlang"
            />
          </div>
        )}

        {/* Step 4 - Ta'lim va kasb */}
        {step === 4 && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-xl font-semibold mb-4">Ta'lim va kasb</h2>

            <Input
              label="Ta'limingiz"
              value={formData.education}
              onChange={(e) => updateField("education", e.target.value)}
              placeholder="Masalan: Oliy ma'lumotli"
            />

            <Input
              label="Kasbingiz"
              value={formData.profession}
              onChange={(e) => updateField("profession", e.target.value)}
              placeholder="Masalan: Dasturchi"
            />

            <Select
              label="Ish holatingiz"
              value={formData.employmentStatus}
              onChange={(e) => updateField("employmentStatus", e.target.value)}
              options={Object.entries(EMPLOYMENT_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
              placeholder="Tanlang"
            />

            <Textarea
              label="O'zingiz haqingizda"
              value={formData.bio}
              onChange={(e) => updateField("bio", e.target.value)}
              placeholder="O'zingiz haqingizda qisqacha yozing..."
              maxLength={500}
            />
          </div>
        )}

        {/* Step 5 - Partner talablari */}
        {step === 5 && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-xl font-semibold mb-4">Partner talablari</h2>
            <p className="text-gray-500 text-sm mb-4">
              Qanday juftlik qidirayotganingizni belgilang
            </p>

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Yoshi (dan)"
                type="number"
                value={formData.partnerAgeMin}
                onChange={(e) => updateField("partnerAgeMin", e.target.value)}
                placeholder="18"
                min={18}
                max={80}
              />
              <Input
                label="Yoshi (gacha)"
                type="number"
                value={formData.partnerAgeMax}
                onChange={(e) => updateField("partnerAgeMax", e.target.value)}
                placeholder="40"
                min={18}
                max={80}
              />
            </div>

            <Select
              label="Viloyati"
              value={formData.partnerRegion}
              onChange={(e) => updateField("partnerRegion", e.target.value)}
              options={[
                { value: "", label: "Farqi yo'q" },
                ...REGIONS.map((r) => ({ value: r, label: r })),
              ]}
            />

            <Select
              label="Diniylik darajasi"
              value={formData.partnerReligiousLevel}
              onChange={(e) => updateField("partnerReligiousLevel", e.target.value)}
              options={[
                { value: "", label: "Farqi yo'q" },
                ...Object.entries(RELIGIOUS_LABELS).map(([value, label]) => ({
                  value,
                  label,
                })),
              ]}
            />

            <Select
              label="Oilaviy holati"
              value={formData.partnerMaritalStatus}
              onChange={(e) => updateField("partnerMaritalStatus", e.target.value)}
              options={[
                { value: "", label: "Farqi yo'q" },
                ...Object.entries(MARITAL_LABELS).map(([value, label]) => ({
                  value,
                  label,
                })),
              ]}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t safe-area-bottom">
        <div className="flex gap-3">
          {step > 1 && (
            <Button
              variant="secondary"
              onClick={prevStep}
              leftIcon={<ChevronLeft className="w-5 h-5" />}
              className="flex-1"
            >
              Orqaga
            </Button>
          )}
          {step < 5 ? (
            <Button
              onClick={nextStep}
              rightIcon={<ChevronRight className="w-5 h-5" />}
              className="flex-1"
            >
              Keyingi
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              isLoading={isLoading}
              leftIcon={<Check className="w-5 h-5" />}
              className="flex-1"
            >
              Yakunlash
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
