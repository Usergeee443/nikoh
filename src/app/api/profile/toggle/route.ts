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

    if (!user || !user.profile) {
      return NextResponse.json(
        { error: "Profil topilmadi" },
        { status: 404 }
      );
    }

    // Aktiv tarifni tekshirish
    const activeTariff = await db.userTariff.findFirst({
      where: {
        userId: user.id,
        isActive: true,
        listingExpires: { gte: new Date() },
      },
    });

    // Profil yoqish uchun tarif kerak
    if (!user.profile.isActive && !activeTariff) {
      return NextResponse.json(
        { error: "Profilni yoqish uchun tarif sotib oling" },
        { status: 403 }
      );
    }

    const updatedProfile = await db.profile.update({
      where: { userId: user.id },
      data: {
        isActive: !user.profile.isActive,
        activatedAt: !user.profile.isActive ? new Date() : user.profile.activatedAt,
      },
    });

    return NextResponse.json({ profile: updatedProfile });
  } catch (error) {
    console.error("Toggle xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
