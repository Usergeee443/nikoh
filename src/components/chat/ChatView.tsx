"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { LoaderSmall } from "@/components/ui/Loader";
import { generateGradientFromId, getChatTimeRemaining } from "@/lib/utils";
import { ArrowLeft, Send, Clock } from "lucide-react";

interface Message {
  id: string;
  content: string;
  senderId: string;
  isRead: boolean;
  createdAt: string;
}

interface ChatViewProps {
  chatId: string;
  onBack: () => void;
}

export function ChatView({ chatId, onBack }: ChatViewProps) {
  const { initData, user } = useAppStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [partner, setPartner] = useState<{
    id: string;
    profile: { name: string };
  } | null>(null);
  const [expiresAt, setExpiresAt] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [newMessage, setNewMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchChat = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/chat?initData=${encodeURIComponent(initData || "")}&chatId=${chatId}`
      );

      if (!response.ok) throw new Error("Chatni yuklashda xato");

      const data = await response.json();
      setMessages(data.chat.messages);
      setPartner(data.partner);
      setExpiresAt(new Date(data.chat.expiresAt));
    } catch (error) {
      console.error("Chat xatosi:", error);
    } finally {
      setIsLoading(false);
    }
  }, [initData, chatId]);

  useEffect(() => {
    fetchChat();
  }, [fetchChat]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Polling for new messages
  useEffect(() => {
    const interval = setInterval(fetchChat, 5000);
    return () => clearInterval(interval);
  }, [fetchChat]);

  const handleSend = async () => {
    if (!newMessage.trim() || isSending) return;

    setIsSending(true);
    const messageContent = newMessage.trim();
    setNewMessage("");

    // Optimistic update
    const optimisticMessage: Message = {
      id: `temp-${Date.now()}`,
      content: messageContent,
      senderId: user?.id || "",
      isRead: false,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMessage]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          initData,
          chatId,
          content: messageContent,
        }),
      });

      if (!response.ok) throw new Error("Xabar yuborishda xato");

      const data = await response.json();

      // Replace optimistic message with real one
      setMessages((prev) =>
        prev.map((m) => (m.id === optimisticMessage.id ? data.message : m))
      );

      window.Telegram?.WebApp.HapticFeedback.impactOccurred("light");
    } catch (error) {
      console.error("Xabar yuborish xatosi:", error);
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== optimisticMessage.id));
      setNewMessage(messageContent);
      window.Telegram?.WebApp.HapticFeedback.notificationOccurred("error");
    } finally {
      setIsSending(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoaderSmall />
      </div>
    );
  }

  const gradient = partner ? generateGradientFromId(partner.id) : "";
  const isExpired = expiresAt ? expiresAt < new Date() : false;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-lg z-10 border-b">
        <div className="flex items-center gap-3 p-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 rounded-full hover:bg-gray-100"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>

          {partner && (
            <>
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                style={{ background: gradient }}
              >
                {partner.profile.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="font-semibold truncate">
                  {partner.profile.name}
                </h1>
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Clock className="w-3 h-3" />
                  <span>
                    {expiresAt
                      ? getChatTimeRemaining(expiresAt)
                      : "Yuklanmoqda..."}
                  </span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 pb-24">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">👋</div>
            <p className="text-gray-500">Suhbatni boshlang!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((message) => {
              const isOwn = message.senderId === user?.id;

              return (
                <div
                  key={message.id}
                  className={`flex ${isOwn ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-2 rounded-2xl ${
                      isOwn
                        ? "bg-blue-500 text-white rounded-br-md"
                        : "bg-gray-100 text-gray-900 rounded-bl-md"
                    }`}
                  >
                    <p className="whitespace-pre-wrap break-words">
                      {message.content}
                    </p>
                    <p
                      className={`text-xs mt-1 ${
                        isOwn ? "text-blue-100" : "text-gray-400"
                      }`}
                    >
                      {new Date(message.createdAt).toLocaleTimeString("uz-UZ", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="fixed bottom-20 left-0 right-0 bg-white border-t p-4">
        {isExpired ? (
          <div className="text-center text-gray-500 py-2">
            Suhbat muddati tugagan
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSend()}
              placeholder="Xabar yozing..."
              className="input flex-1"
              maxLength={1000}
            />
            <button
              onClick={handleSend}
              disabled={!newMessage.trim() || isSending}
              className="p-3 bg-blue-500 text-white rounded-xl disabled:opacity-50 transition-opacity"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
