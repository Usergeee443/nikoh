"use client";

import { useState, useEffect, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { ProfileCard } from "./ProfileCard";
import { ProfileDetail } from "./ProfileDetail";
import { LoaderSmall, ProfileCardSkeleton } from "@/components/ui/Loader";
import { RefreshCw } from "lucide-react";

interface ProfileData {
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
  bio?: string;
  isTop: boolean;
  user: {
    id: string;
    telegramId: string;
  };
}

export function Feed() {
  const { initData } = useAppStore();
  const [profiles, setProfiles] = useState<ProfileData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<ProfileData | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchProfiles = useCallback(async (pageNum: number, refresh = false) => {
    if (refresh) {
      setIsRefreshing(true);
    }

    try {
      const response = await fetch(
        `/api/feed?initData=${encodeURIComponent(initData || "")}&page=${pageNum}&limit=20`
      );

      if (!response.ok) throw new Error("Feed yuklashda xato");

      const data = await response.json();

      if (refresh || pageNum === 1) {
        setProfiles(data.profiles);
      } else {
        setProfiles((prev) => [...prev, ...data.profiles]);
      }

      setHasMore(pageNum < data.pagination.totalPages);
    } catch (error) {
      console.error("Feed xatosi:", error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [initData]);

  useEffect(() => {
    fetchProfiles(1);
  }, [fetchProfiles]);

  const handleRefresh = () => {
    setPage(1);
    fetchProfiles(1, true);
  };

  const loadMore = () => {
    if (!isLoading && hasMore) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchProfiles(nextPage);
    }
  };

  if (selectedProfile) {
    return (
      <ProfileDetail
        profile={selectedProfile}
        onBack={() => setSelectedProfile(null)}
      />
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 p-4 border-b">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Anketalar</h1>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-full hover:bg-gray-100 transition-colors"
          >
            <RefreshCw
              className={`w-5 h-5 ${isRefreshing ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <ProfileCardSkeleton key={i} />
            ))}
          </div>
        ) : profiles.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-lg font-medium mb-2">Anketalar topilmadi</h3>
            <p className="text-gray-500">
              Hozircha sizga mos anketalar yo'q
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {profiles.map((profile) => (
              <ProfileCard
                key={profile.id}
                profile={profile}
                onClick={() => setSelectedProfile(profile)}
              />
            ))}

            {hasMore && (
              <div className="py-4">
                <button
                  onClick={loadMore}
                  className="w-full py-3 text-blue-500 font-medium"
                >
                  Ko'proq yuklash
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
