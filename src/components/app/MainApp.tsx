"use client";

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Feed } from "@/components/feed/Feed";
import { Requests } from "@/components/request/Requests";
import { ChatList } from "@/components/chat/ChatList";
import { Profile } from "@/components/profile/Profile";
import { Home, Heart, MessageCircle, User } from "lucide-react";
import { cn } from "@/lib/utils";

type Tab = "feed" | "requests" | "chats" | "profile";

export function MainApp() {
  const [activeTab, setActiveTab] = useState<Tab>("feed");
  const { unreadCount, pendingRequestsCount } = useAppStore();

  const tabs = [
    {
      id: "feed" as Tab,
      label: "Bosh sahifa",
      icon: Home,
      badge: 0,
    },
    {
      id: "requests" as Tab,
      label: "So'rovlar",
      icon: Heart,
      badge: pendingRequestsCount,
    },
    {
      id: "chats" as Tab,
      label: "Chatlar",
      icon: MessageCircle,
      badge: unreadCount,
    },
    {
      id: "profile" as Tab,
      label: "Profil",
      icon: User,
      badge: 0,
    },
  ];

  return (
    <div className="min-h-screen pb-20">
      {/* Content */}
      <div className="animate-fade-in">
        {activeTab === "feed" && <Feed />}
        {activeTab === "requests" && <Requests />}
        {activeTab === "chats" && <ChatList />}
        {activeTab === "profile" && <Profile />}
      </div>

      {/* Tab Bar */}
      <div className="tab-bar">
        <div className="flex justify-around items-center">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn("tab-item relative", isActive ? "active" : "inactive")}
              >
                <div className="relative">
                  <Icon className="w-6 h-6" />
                  {tab.badge > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                      {tab.badge > 9 ? "9+" : tab.badge}
                    </span>
                  )}
                </div>
                <span className="text-xs mt-1">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
