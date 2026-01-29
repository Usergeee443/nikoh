import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData, notifyNewMessage } from "@/lib/telegram";

// Chatlarni olish
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const initData = searchParams.get("initData");
    const chatId = searchParams.get("chatId");

    if (!initData) {
      return NextResponse.json(
        { error: "initData talab qilinadi" },
        { status: 400 }
      );
    }

    const isValid = validateTelegramWebAppData(initData);
    if (!isValid) {
      return NextResponse.json(
        { error: "Noto'g'ri Telegram ma'lumotlari" },
        { status: 401 }
      );
    }

    const telegramUser = parseTelegramInitData(initData);
    if (!telegramUser) {
      return NextResponse.json(
        { error: "Foydalanuvchi topilmadi" },
        { status: 400 }
      );
    }

    const user = await db.user.findUnique({
      where: { telegramId: BigInt(telegramUser.id) },
    });

    if (!user) {
      return NextResponse.json(
        { error: "Foydalanuvchi topilmadi" },
        { status: 404 }
      );
    }

    // Bitta chatni olish
    if (chatId) {
      const chat = await db.chat.findFirst({
        where: {
          id: chatId,
          OR: [{ user1Id: user.id }, { user2Id: user.id }],
        },
        include: {
          user1: { include: { profile: true } },
          user2: { include: { profile: true } },
          messages: {
            orderBy: { createdAt: "asc" },
            take: 100,
          },
        },
      });

      if (!chat) {
        return NextResponse.json(
          { error: "Chat topilmadi" },
          { status: 404 }
        );
      }

      // O'qilmagan xabarlarni o'qilgan deb belgilash
      await db.message.updateMany({
        where: {
          chatId,
          senderId: { not: user.id },
          isRead: false,
        },
        data: { isRead: true },
      });

      const partner = chat.user1Id === user.id ? chat.user2 : chat.user1;

      return NextResponse.json({
        chat: {
          ...chat,
          user1: {
            ...chat.user1,
            telegramId: chat.user1.telegramId.toString(),
          },
          user2: {
            ...chat.user2,
            telegramId: chat.user2.telegramId.toString(),
          },
        },
        partner: {
          ...partner,
          telegramId: partner.telegramId.toString(),
        },
      });
    }

    // Barcha chatlarni olish
    const chats = await db.chat.findMany({
      where: {
        OR: [{ user1Id: user.id }, { user2Id: user.id }],
      },
      include: {
        user1: { include: { profile: true } },
        user2: { include: { profile: true } },
        messages: {
          orderBy: { createdAt: "desc" },
          take: 1,
        },
      },
      orderBy: { createdAt: "desc" },
    });

    // Har bir chat uchun o'qilmagan xabarlar sonini hisoblash
    const chatsWithUnread = await Promise.all(
      chats.map(async (chat) => {
        const unreadCount = await db.message.count({
          where: {
            chatId: chat.id,
            senderId: { not: user.id },
            isRead: false,
          },
        });

        const partner = chat.user1Id === user.id ? chat.user2 : chat.user1;

        return {
          ...chat,
          user1: {
            ...chat.user1,
            telegramId: chat.user1.telegramId.toString(),
          },
          user2: {
            ...chat.user2,
            telegramId: chat.user2.telegramId.toString(),
          },
          partner: {
            ...partner,
            telegramId: partner.telegramId.toString(),
          },
          unreadCount,
          lastMessage: chat.messages[0] || null,
        };
      })
    );

    return NextResponse.json({ chats: chatsWithUnread });
  } catch (error) {
    console.error("Chat olish xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}

// Xabar yuborish
export async function POST(request: NextRequest) {
  try {
    const { initData, chatId, content } = await request.json();

    if (!initData || !chatId || !content?.trim()) {
      return NextResponse.json(
        { error: "Ma'lumotlar yetarli emas" },
        { status: 400 }
      );
    }

    const isValid = validateTelegramWebAppData(initData);
    if (!isValid) {
      return NextResponse.json(
        { error: "Noto'g'ri Telegram ma'lumotlari" },
        { status: 401 }
      );
    }

    const telegramUser = parseTelegramInitData(initData);
    if (!telegramUser) {
      return NextResponse.json(
        { error: "Foydalanuvchi topilmadi" },
        { status: 400 }
      );
    }

    const user = await db.user.findUnique({
      where: { telegramId: BigInt(telegramUser.id) },
      include: { profile: true },
    });

    if (!user) {
      return NextResponse.json(
        { error: "Foydalanuvchi topilmadi" },
        { status: 404 }
      );
    }

    // Chatni tekshirish
    const chat = await db.chat.findFirst({
      where: {
        id: chatId,
        OR: [{ user1Id: user.id }, { user2Id: user.id }],
        isActive: true,
        expiresAt: { gte: new Date() },
      },
      include: {
        user1: { include: { profile: true } },
        user2: { include: { profile: true } },
      },
    });

    if (!chat) {
      return NextResponse.json(
        { error: "Chat topilmadi yoki muddati tugagan" },
        { status: 404 }
      );
    }

    // Xabarni yaratish
    const message = await db.message.create({
      data: {
        chatId,
        senderId: user.id,
        content: content.trim(),
      },
    });

    // Qabul qiluvchiga bildirishnoma
    const receiver = chat.user1Id === user.id ? chat.user2 : chat.user1;
    notifyNewMessage(receiver.telegramId, user.profile?.name || "Foydalanuvchi");

    return NextResponse.json({ message });
  } catch (error) {
    console.error("Xabar yuborish xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
