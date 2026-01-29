"use client";

import { calculateAge, generateGradientFromId, MARITAL_LABELS, RELIGIOUS_LABELS } from "@/lib/utils";
import { MapPin, Star } from "lucide-react";

interface ProfileCardProps {
  profile: {
    id: string;
    userId: string;
    name: string;
    gender: string;
    birthYear: number;
    region: string;
    maritalStatus: string;
    religiousLevel?: string;
    bio?: string;
    isTop: boolean;
  };
  onClick: () => void;
}

export function ProfileCard({ profile, onClick }: ProfileCardProps) {
  const age = calculateAge(profile.birthYear);
  const gradient = generateGradientFromId(profile.id);

  return (
    <div
      onClick={onClick}
      className="card overflow-hidden cursor-pointer hover:shadow-md transition-shadow animate-fade-in"
    >
      <div className="flex">
        {/* Avatar */}
        <div
          className="w-24 h-24 flex-shrink-0 flex items-center justify-center text-white text-3xl font-semibold"
          style={{ background: gradient }}
        >
          {profile.name.charAt(0).toUpperCase()}
        </div>

        {/* Info */}
        <div className="flex-1 p-3">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-lg">{profile.name}</h3>
                {profile.isTop && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
                    <Star className="w-3 h-3 fill-current" />
                    TOP
                  </span>
                )}
              </div>
              <p className="text-gray-500 text-sm">
                {age} yosh, {MARITAL_LABELS[profile.maritalStatus as keyof typeof MARITAL_LABELS]}
              </p>
            </div>
          </div>

          <div className="mt-2 flex items-center gap-1 text-gray-500 text-sm">
            <MapPin className="w-4 h-4" />
            <span>{profile.region}</span>
          </div>

          {profile.religiousLevel && (
            <div className="mt-1 text-sm text-gray-500">
              {RELIGIOUS_LABELS[profile.religiousLevel as keyof typeof RELIGIOUS_LABELS]}
            </div>
          )}

          {profile.bio && (
            <p className="mt-2 text-sm text-gray-600 line-clamp-2">
              {profile.bio}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
