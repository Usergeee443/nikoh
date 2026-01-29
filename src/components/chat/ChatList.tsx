"use client";

import { useState, useEffect, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { ChatView } from "./ChatView";
import { LoaderSmall } from "@/components/ui/Loader";
import { generateGradientFromId, formatRelativeTime, getChatTimeRemaining } from "@/lib/utils";
import { Clock } from "lucide-react";

interface ChatData {
  id: string;
  isActive: boolean;
  expiresAt: string;
  createdAt: string;
  partner: {
    id: string;
    profile: {
      name: string;
    };
  };
  lastMessage?: {
    content: string;
    createdAt: string;
    senderId: string;
  };
  unreadCount: number;
}

export function ChatList() {
  const { initData, setUnreadCount } = useAppStore();
  const [chats, setChats] = useState<ChatData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);

  const fetchChats = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/chat?initData=${encodeURIComponent(initData || "")}`
      );

      if (!response.ok) throw new Error("Chatlarni yuklashda xato");

      const data = await response.json();
      setChats(data.chats);

      // Jami o'qilmagan xabarlarni hisoblash
      const totalUnread = data.chats.reduce(
        (sum: number, chat: ChatData) => sum + chat.unreadCount,
        0
      );
      setUnreadCount(totalUnread);
    } catch (error) {
      console.error("Chatlar xatosi:", error);
    } finally {
      setIsLoading(false);
    }
  }, [initData, setUnreadCount]);

  useEffect(() => {
    fetchChats();
  }, [fetchChats]);

  if (selectedChatId) {
    return (
      <ChatView
        chatId={selectedChatId}
        onBack={() => {
          setSelectedChatId(null);
          fetchChats();
        }}
      />
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 p-4 border-b">
        <h1 className="text-xl font-semibold">Suhbatlar</h1>
      </div>

      {/* Content */}
      <div>
        {isLoading ? (
          <LoaderSmall />
        ) : chats.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="text-6xl mb-4">💬</div>
            <h3 className="text-lg font-medium mb-2">Suhbatlar yo'q</h3>
            <p className="text-gray-500">
              Taklifnomangiz qabul qilinganda suhbat boshlanadi
            </p>
          </div>
        ) : (
          <div>
            {chats.map((chat) => {
              const gradient = generateGradientFromId(chat.partner.id);
              const isExpired = new Date(chat.expiresAt) < new Date();

              return (
                <div
                  key={chat.id}
                  onClick={() => !isExpired && setSelectedChatId(chat.id)}
                  className={`flex items-center gap-3 p-4 border-b transition-colors ${
                    isExpired
                      ? "opacity-50 cursor-not-allowed"
                      : "hover:bg-gray-50 cursor-pointer"
                  }`}
                >
                  {/* Avatar */}
                  <div className="relative">
                    <div
                      className="w-14 h-14 rounded-full flex items-center justify-center text-white text-xl font-semibold"
                      style={{ background: gradient }}
                    >
                      {chat.partner.profile.name.charAt(0).toUpperCase()}
                    </div>
                    {chat.unreadCount > 0 && (
                      <span className="absolute -top-1 -right-1 w-5 h-5 bg-blue-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                        {chat.unreadCount > 9 ? "9+" : chat.unreadCount}
                      </span>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold truncate">
                        {chat.partner.profile.name}
                      </h3>
                      {chat.lastMessage && (
                        <span className="text-xs text-gray-400">
                          {formatRelativeTime(new Date(chat.lastMessage.createdAt))}
                        </span>
                      )}
                    </div>

                    {chat.lastMessage ? (
                      <p
                        className={`text-sm truncate ${
                          chat.unreadCount > 0
                            ? "text-gray-900 font-medium"
                            : "text-gray-500"
                        }`}
                      >
                        {chat.lastMessage.content}
                      </p>
                    ) : (
                      <p className="text-sm text-gray-400 italic">
                        Xabar yo'q
                      </p>
                    )}

                    {/* Chat expiry */}
                    <div className="flex items-center gap-1 mt-1">
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span
                        className={`text-xs ${
                          isExpired ? "text-red-500" : "text-gray-400"
                        }`}
                      >
                        {getChatTimeRemaining(new Date(chat.expiresAt))}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
