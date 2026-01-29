"use client";

import { useState, useEffect, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/Button";
import { LoaderSmall } from "@/components/ui/Loader";
import { calculateAge, generateGradientFromId, formatRelativeTime } from "@/lib/utils";
import { Check, X, ChevronRight } from "lucide-react";

interface RequestData {
  id: string;
  message?: string;
  status: string;
  createdAt: string;
  sender: {
    id: string;
    profile: {
      name: string;
      birthYear: number;
      region: string;
    };
  };
  receiver: {
    id: string;
    profile: {
      name: string;
      birthYear: number;
      region: string;
    };
  };
}

export function Requests() {
  const { initData, setPendingRequestsCount } = useAppStore();
  const [activeTab, setActiveTab] = useState<"received" | "sent">("received");
  const [requests, setRequests] = useState<RequestData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchRequests = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/request?initData=${encodeURIComponent(initData || "")}&type=${activeTab}`
      );

      if (!response.ok) throw new Error("So'rovlarni yuklashda xato");

      const data = await response.json();
      setRequests(data.requests);

      if (activeTab === "received") {
        setPendingRequestsCount(data.requests.filter((r: RequestData) => r.status === "PENDING").length);
      }
    } catch (error) {
      console.error("So'rovlar xatosi:", error);
    } finally {
      setIsLoading(false);
    }
  }, [initData, activeTab, setPendingRequestsCount]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleAction = async (requestId: string, action: "accept" | "reject") => {
    setActionLoading(requestId);

    try {
      const response = await fetch("/api/request", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initData,
          requestId,
          action,
        }),
      });

      if (!response.ok) throw new Error("Amal bajarishda xato");

      // Ro'yxatdan olib tashlash
      setRequests((prev) => prev.filter((r) => r.id !== requestId));
      setPendingRequestsCount((prev: number) => Math.max(0, prev - 1));

      window.Telegram?.WebApp.HapticFeedback.notificationOccurred(
        action === "accept" ? "success" : "warning"
      );
    } catch (error) {
      console.error("Amal xatosi:", error);
      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("error");
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PENDING":
        return <span className="badge badge-warning">Kutilmoqda</span>;
      case "ACCEPTED":
        return <span className="badge badge-success">Qabul qilindi</span>;
      case "REJECTED":
        return <span className="badge badge-error">Rad etildi</span>;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 border-b">
        <div className="p-4">
          <h1 className="text-xl font-semibold">So'rovlar</h1>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab("received")}
            className={`flex-1 py-3 text-center font-medium transition-colors ${
              activeTab === "received"
                ? "text-blue-500 border-b-2 border-blue-500"
                : "text-gray-500"
            }`}
          >
            Kelgan
          </button>
          <button
            onClick={() => setActiveTab("sent")}
            className={`flex-1 py-3 text-center font-medium transition-colors ${
              activeTab === "sent"
                ? "text-blue-500 border-b-2 border-blue-500"
                : "text-gray-500"
            }`}
          >
            Yuborilgan
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <LoaderSmall />
        ) : requests.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">
              {activeTab === "received" ? "📨" : "📤"}
            </div>
            <h3 className="text-lg font-medium mb-2">
              {activeTab === "received"
                ? "Yangi so'rovlar yo'q"
                : "Yuborilgan so'rovlar yo'q"}
            </h3>
            <p className="text-gray-500">
              {activeTab === "received"
                ? "Sizga hali hech kim so'rov yubormagan"
                : "Siz hali hech kimga so'rov yubormadingiz"}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {requests.map((request) => {
              const profile =
                activeTab === "received"
                  ? request.sender.profile
                  : request.receiver.profile;
              const gradient = generateGradientFromId(
                activeTab === "received" ? request.sender.id : request.receiver.id
              );
              const age = calculateAge(profile.birthYear);

              return (
                <div
                  key={request.id}
                  className="card p-4 animate-fade-in"
                >
                  <div className="flex items-start gap-3">
                    {/* Avatar */}
                    <div
                      className="w-14 h-14 rounded-full flex items-center justify-center text-white text-xl font-semibold flex-shrink-0"
                      style={{ background: gradient }}
                    >
                      {profile.name.charAt(0).toUpperCase()}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold truncate">{profile.name}</h3>
                        {activeTab === "sent" && getStatusBadge(request.status)}
                      </div>
                      <p className="text-gray-500 text-sm">
                        {age} yosh, {profile.region}
                      </p>
                      {request.message && (
                        <p className="text-gray-600 text-sm mt-1 line-clamp-2">
                          "{request.message}"
                        </p>
                      )}
                      <p className="text-gray-400 text-xs mt-1">
                        {formatRelativeTime(new Date(request.createdAt))}
                      </p>
                    </div>
                  </div>

                  {/* Actions for received requests */}
                  {activeTab === "received" && request.status === "PENDING" && (
                    <div className="flex gap-2 mt-4">
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleAction(request.id, "reject")}
                        isLoading={actionLoading === request.id}
                        leftIcon={<X className="w-4 h-4" />}
                        className="flex-1"
                      >
                        Rad etish
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleAction(request.id, "accept")}
                        isLoading={actionLoading === request.id}
                        leftIcon={<Check className="w-4 h-4" />}
                        className="flex-1"
                      >
                        Qabul qilish
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
