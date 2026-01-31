import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData } from "@/lib/telegram";

export async function POST(request: NextRequest) {
  try {
    const { initData } = await request.json();

    if (!initData) {
      return NextResponse.json(
        { error: "initData talab qilinadi" },
        { status: 400 }
      );
    }

    // Telegram ma'lumotlarini tekshirish
    // Development rejimida validatsiyani o'tkazib yuborish mumkin
    const isDev = process.env.NODE_ENV === "development";
    const isValid = validateTelegramWebAppData(initData);

    if (!isValid && !isDev) {
      return NextResponse.json(
        { error: "Noto'g'ri Telegram ma'lumotlari" },
        { status: 401 }
      );
    }

    if (!isValid && isDev) {
      console.log("⚠️ Development: Telegram validatsiya o'tkazib yuborildi");
    }

    // Foydalanuvchi ma'lumotlarini olish
    const telegramUser = parseTelegramInitData(initData);
    if (!telegramUser) {
      return NextResponse.json(
        { error: "Foydalanuvchi ma'lumotlari topilmadi" },
        { status: 400 }
      );
    }

    // Admin ekanligini tekshirish
    const adminIds = process.env.ADMIN_TELEGRAM_IDS?.split(",").map((id) =>
      parseInt(id.trim())
    ) || [];
    const isAdmin = adminIds.includes(telegramUser.id);

    // Foydalanuvchini topish yoki yaratish
    let user = await db.user.findUnique({
      where: { telegramId: BigInt(telegramUser.id) },
      include: { profile: true },
    });

    if (!user) {
      // Yangi foydalanuvchi yaratish
      user = await db.user.create({
        data: {
          telegramId: BigInt(telegramUser.id),
          username: telegramUser.username,
          firstName: telegramUser.first_name,
          lastName: telegramUser.last_name,
          isAdmin,
        },
        include: { profile: true },
      });
    } else {
      // Mavjud foydalanuvchini yangilash
      user = await db.user.update({
        where: { id: user.id },
        data: {
          username: telegramUser.username,
          firstName: telegramUser.first_name,
          lastName: telegramUser.last_name,
          isAdmin: isAdmin || user.isAdmin,
        },
        include: { profile: true },
      });
    }

    // Bloklangan ekanligini tekshirish
    if (user.isBlocked) {
      return NextResponse.json(
        { error: "Sizning hisobingiz bloklangan" },
        { status: 403 }
      );
    }

    // Qo'shimcha ma'lumotlarni olish
    const [unreadCount, pendingRequestsCount, activeTariff] = await Promise.all([
      // O'qilmagan xabarlar soni
      db.message.count({
        where: {
          chat: {
            OR: [{ user1Id: user.id }, { user2Id: user.id }],
            isActive: true,
          },
          senderId: { not: user.id },
          isRead: false,
        },
      }),
      // Kutilayotgan so'rovlar soni
      db.matchRequest.count({
        where: {
          receiverId: user.id,
          status: "PENDING",
        },
      }),
      // Aktiv tarif
      db.userTariff.findFirst({
        where: {
          userId: user.id,
          isActive: true,
          listingExpires: { gte: new Date() },
        },
        orderBy: { createdAt: "desc" },
      }),
    ]);

    // BigInt ni string ga aylantirish
    const serializedUser = {
      ...user,
      telegramId: user.telegramId.toString(),
    };

    return NextResponse.json({
      user: serializedUser,
      unreadCount,
      pendingRequestsCount,
      hasActiveTariff: !!activeTariff,
      requestsLeft: activeTariff?.requestsLeft || 0,
    });
  } catch (error) {
    console.error("Auth xatosi:", error);
    return NextResponse.json(
      { error: "Server xatosi" },
      { status: 500 }
    );
  }
}
