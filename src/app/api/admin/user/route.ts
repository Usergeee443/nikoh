import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData } from "@/lib/telegram";

export async function POST(request: NextRequest) {
  try {
    const { initData, userId, action } = await request.json();

    if (!initData || !userId || !action) {
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

    // Admin ekanligini tekshirish
    const admin = await db.user.findUnique({
      where: { telegramId: BigInt(telegramUser.id) },
    });

    if (!admin?.isAdmin) {
      return NextResponse.json(
        { error: "Ruxsat yo'q" },
        { status: 403 }
      );
    }

    // Foydalanuvchini topish
    const user = await db.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      return NextResponse.json(
        { error: "Foydalanuvchi topilmadi" },
        { status: 404 }
      );
    }

    // O'zini bloklashga ruxsat bermash
    if (user.id === admin.id) {
      return NextResponse.json(
        { error: "O'zingizni bloklashingiz mumkin emas" },
        { status: 400 }
      );
    }

    if (action === "block") {
      await db.user.update({
        where: { id: userId },
        data: { isBlocked: true },
      });

      // Profilni ham o'chirish
      await db.profile.update({
        where: { userId },
        data: { isActive: false },
      });

      return NextResponse.json({ message: "Foydalanuvchi bloklandi" });
    } else if (action === "unblock") {
      await db.user.update({
        where: { id: userId },
        data: { isBlocked: false },
      });

      return NextResponse.json({ message: "Foydalanuvchi blokdan chiqarildi" });
    }

    return NextResponse.json({ error: "Noto'g'ri amal" }, { status: 400 });
  } catch (error) {
    console.error("User action xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
