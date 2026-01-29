"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/Button";
import { LoaderSmall } from "@/components/ui/Loader";
import { TARIFF_INFO } from "@/lib/utils";
import {
  ArrowLeft,
  Users,
  CreditCard,
  MessageCircle,
  Heart,
  Check,
  X,
  Ban,
  Unlock,
} from "lucide-react";
import { useRouter } from "next/navigation";

interface Stats {
  totalUsers: number;
  activeProfiles: number;
  totalRequests: number;
  totalChats: number;
  pendingPayments: number;
}

interface PaymentRequest {
  id: string;
  tariffType: string;
  amount: number;
  status: string;
  createdAt: string;
  user: {
    id: string;
    telegramId: string;
    firstName?: string;
    profile?: {
      name: string;
    };
  };
}

interface UserData {
  id: string;
  telegramId: string;
  firstName?: string;
  isBlocked: boolean;
  profile?: {
    name: string;
  };
}

export default function AdminPage() {
  const { user, initData } = useAppStore();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"stats" | "payments" | "users">("stats");
  const [stats, setStats] = useState<Stats | null>(null);
  const [payments, setPayments] = useState<PaymentRequest[]>([]);
  const [users, setUsers] = useState<UserData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.isAdmin) {
      router.push("/");
      return;
    }

    fetchData();
  }, [user, router, activeTab]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/admin?initData=${encodeURIComponent(initData || "")}&type=${activeTab}`
      );

      if (!response.ok) throw new Error();

      const data = await response.json();

      if (activeTab === "stats") {
        setStats(data.stats);
      } else if (activeTab === "payments") {
        setPayments(data.payments);
      } else {
        setUsers(data.users);
      }
    } catch (error) {
      console.error("Admin data xatosi:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePaymentAction = async (paymentId: string, action: "approve" | "reject") => {
    setActionLoading(paymentId);

    try {
      const response = await fetch("/api/admin/payment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initData,
          paymentId,
          action,
        }),
      });

      if (!response.ok) throw new Error();

      setPayments((prev) => prev.filter((p) => p.id !== paymentId));
    } catch (error) {
      console.error("Payment action xatosi:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleUserAction = async (userId: string, action: "block" | "unblock") => {
    setActionLoading(userId);

    try {
      const response = await fetch("/api/admin/user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initData,
          userId,
          action,
        }),
      });

      if (!response.ok) throw new Error();

      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId ? { ...u, isBlocked: action === "block" } : u
        )
      );
    } catch (error) {
      console.error("User action xatosi:", error);
    } finally {
      setActionLoading(null);
    }
  };

  if (!user?.isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen pb-20">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 border-b">
        <div className="flex items-center p-4">
          <button
            onClick={() => router.push("/")}
            className="p-2 -ml-2 rounded-full hover:bg-gray-100"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <h1 className="ml-2 text-lg font-semibold">Admin Panel</h1>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          {[
            { id: "stats", label: "Statistika" },
            { id: "payments", label: "To'lovlar" },
            { id: "users", label: "Foydalanuvchilar" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 py-3 text-center font-medium transition-colors ${
                activeTab === tab.id
                  ? "text-blue-500 border-b-2 border-blue-500"
                  : "text-gray-500"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <LoaderSmall />
        ) : (
          <>
            {/* Stats */}
            {activeTab === "stats" && stats && (
              <div className="grid grid-cols-2 gap-4">
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <Users className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{stats.totalUsers}</p>
                      <p className="text-sm text-gray-500">Foydalanuvchilar</p>
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                      <Users className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{stats.activeProfiles}</p>
                      <p className="text-sm text-gray-500">Faol profillar</p>
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-pink-100 rounded-full flex items-center justify-center">
                      <Heart className="w-5 h-5 text-pink-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{stats.totalRequests}</p>
                      <p className="text-sm text-gray-500">Taklifnomalar</p>
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                      <MessageCircle className="w-5 h-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{stats.totalChats}</p>
                      <p className="text-sm text-gray-500">Chatlar</p>
                    </div>
                  </div>
                </div>

                <div className="card p-4 col-span-2">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                      <CreditCard className="w-5 h-5 text-yellow-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{stats.pendingPayments}</p>
                      <p className="text-sm text-gray-500">Kutilayotgan to'lovlar</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Payments */}
            {activeTab === "payments" && (
              <div className="space-y-3">
                {payments.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-gray-500">Kutilayotgan to'lovlar yo'q</p>
                  </div>
                ) : (
                  payments.map((payment) => (
                    <div key={payment.id} className="card p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-semibold">
                            {payment.user.profile?.name || payment.user.firstName}
                          </h3>
                          <p className="text-sm text-gray-500">
                            ID: {payment.user.telegramId}
                          </p>
                        </div>
                        <span className="badge badge-warning">Kutilmoqda</span>
                      </div>

                      <div className="flex items-center justify-between mb-3">
                        <span>
                          {TARIFF_INFO[payment.tariffType as keyof typeof TARIFF_INFO]?.name}
                        </span>
                        <span className="font-semibold">
                          {payment.amount.toLocaleString()} so'm
                        </span>
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handlePaymentAction(payment.id, "reject")}
                          isLoading={actionLoading === payment.id}
                          leftIcon={<X className="w-4 h-4" />}
                          className="flex-1"
                        >
                          Rad etish
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handlePaymentAction(payment.id, "approve")}
                          isLoading={actionLoading === payment.id}
                          leftIcon={<Check className="w-4 h-4" />}
                          className="flex-1"
                        >
                          Tasdiqlash
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Users */}
            {activeTab === "users" && (
              <div className="space-y-3">
                {users.map((u) => (
                  <div key={u.id} className="card p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold">
                          {u.profile?.name || u.firstName || "Noma'lum"}
                        </h3>
                        <p className="text-sm text-gray-500">ID: {u.telegramId}</p>
                      </div>

                      <Button
                        variant={u.isBlocked ? "primary" : "danger"}
                        size="sm"
                        onClick={() =>
                          handleUserAction(u.id, u.isBlocked ? "unblock" : "block")
                        }
                        isLoading={actionLoading === u.id}
                        leftIcon={
                          u.isBlocked ? (
                            <Unlock className="w-4 h-4" />
                          ) : (
                            <Ban className="w-4 h-4" />
                          )
                        }
                      >
                        {u.isBlocked ? "Ochish" : "Bloklash"}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
