import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Profil uchun gradient rang generatsiya qilish
export function generateGradientFromId(id: string): string {
  const colors = [
    ["#667eea", "#764ba2"],
    ["#f093fb", "#f5576c"],
    ["#4facfe", "#00f2fe"],
    ["#43e97b", "#38f9d7"],
    ["#fa709a", "#fee140"],
    ["#a8edea", "#fed6e3"],
    ["#ff9a9e", "#fecfef"],
    ["#ffecd2", "#fcb69f"],
    ["#a1c4fd", "#c2e9fb"],
    ["#d4fc79", "#96e6a1"],
  ];

  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }

  const index = Math.abs(hash) % colors.length;
  return `linear-gradient(135deg, ${colors[index][0]} 0%, ${colors[index][1]} 100%)`;
}

// Yosh hisoblash
export function calculateAge(birthYear: number): number {
  return new Date().getFullYear() - birthYear;
}

// Vaqt formatlash
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days} kun oldin`;
  if (hours > 0) return `${hours} soat oldin`;
  if (minutes > 0) return `${minutes} daqiqa oldin`;
  return "Hozirgina";
}

// Chat muddati
export function getChatTimeRemaining(expiresAt: Date): string {
  const now = new Date();
  const diff = expiresAt.getTime() - now.getTime();

  if (diff <= 0) return "Muddati tugagan";

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

  if (days > 0) return `${days} kun ${hours} soat qoldi`;
  return `${hours} soat qoldi`;
}

// Tarif ma'lumotlari
export const TARIFF_INFO = {
  KUMUSH: {
    name: "Kumush",
    price: 50000,
    requests: 5,
    listingDays: 10,
    topDays: 0,
    color: "#C0C0C0",
  },
  OLTIN: {
    name: "Oltin",
    price: 100000,
    requests: 10,
    listingDays: 15,
    topDays: 7,
    color: "#FFD700",
  },
  VIP: {
    name: "VIP",
    price: 250000,
    requests: 20,
    listingDays: 30,
    topDays: 15,
    color: "#9333EA",
  },
} as const;

// Viloyatlar
export const REGIONS = [
  "Toshkent shahri",
  "Toshkent viloyati",
  "Andijon",
  "Buxoro",
  "Farg'ona",
  "Jizzax",
  "Xorazm",
  "Namangan",
  "Navoiy",
  "Qashqadaryo",
  "Qoraqalpog'iston",
  "Samarqand",
  "Sirdaryo",
  "Surxondaryo",
] as const;

// Millatlar
export const NATIONALITIES = [
  "O'zbek",
  "Qoraqalpoq",
  "Tojik",
  "Qozoq",
  "Qirg'iz",
  "Turkman",
  "Rus",
  "Koreys",
  "Boshqa",
] as const;

// Namoz ma'lumotlari
export const PRAYER_LABELS = {
  ALWAYS: "Doim o'qiyman",
  OFTEN: "Ko'pincha o'qiyman",
  SOMETIMES: "Ba'zan o'qiyman",
  RARELY: "Kamdan-kam",
  NEVER: "O'qimayman",
} as const;

// Diniylik darajasi
export const RELIGIOUS_LABELS = {
  VERY_RELIGIOUS: "Juda diniy",
  RELIGIOUS: "Diniy",
  MODERATE: "O'rtacha",
  NOT_RELIGIOUS: "Diniy emas",
} as const;

// Oilaviy holat
export const MARITAL_LABELS = {
  SINGLE: "Turmush qurmagan",
  DIVORCED: "Ajrashgan",
  WIDOWED: "Beva",
} as const;

// Ish holati
export const EMPLOYMENT_LABELS = {
  EMPLOYED: "Ishlayman",
  UNEMPLOYED: "Ishsiz",
  STUDENT: "Talaba",
  SELF_EMPLOYED: "O'z ishim",
  RETIRED: "Nafaqada",
} as const;
