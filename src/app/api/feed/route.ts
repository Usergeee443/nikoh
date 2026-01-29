import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData } from "@/lib/telegram";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const initData = searchParams.get("initData");
    const page = parseInt(searchParams.get("page") || "1");
    const limit = parseInt(searchParams.get("limit") || "20");

    if (!initData) {
      return NextResponse.json(
        { error: "initData talab qilinadi" },
        { status: 400 }
      );
    }

    // Telegram ma'lumotlarini tekshirish
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

    // Foydalanuvchini topish
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

    // Qarama-qarshi jinsni aniqlash
    const oppositeGender = user.profile.gender === "MALE" ? "FEMALE" : "MALE";

    // Faol profillarni olish (TOP birinchi, keyin yangi)
    const profiles = await db.profile.findMany({
      where: {
        gender: oppositeGender,
        isActive: true,
        isComplete: true,
        userId: { not: user.id },
        user: { isBlocked: false },
      },
      include: {
        user: {
          select: {
            id: true,
            telegramId: true,
            username: true,
            firstName: true,
            lastName: true,
            tariffs: {
              where: {
                isActive: true,
                listingExpires: { gte: new Date() },
              },
              orderBy: { createdAt: "desc" },
              take: 1,
            },
          },
        },
      },
      orderBy: [{ activatedAt: "desc" }],
      skip: (page - 1) * limit,
      take: limit,
    });

    // TOP profillarni ajratib olish va birinchi qo'yish
    const now = new Date();
    const topProfiles = profiles.filter((p) => {
      const tariff = p.user.tariffs[0];
      return tariff?.topExpires && new Date(tariff.topExpires) > now;
    });

    const regularProfiles = profiles.filter((p) => {
      const tariff = p.user.tariffs[0];
      return !tariff?.topExpires || new Date(tariff.topExpires) <= now;
    });

    const sortedProfiles = [...topProfiles, ...regularProfiles];

    // Jami sonni olish
    const total = await db.profile.count({
      where: {
        gender: oppositeGender,
        isActive: true,
        isComplete: true,
        userId: { not: user.id },
        user: { isBlocked: false },
      },
    });

    // Serialization
    const serializedProfiles = sortedProfiles.map((profile) => {
      const tariff = profile.user.tariffs[0];
      const isTop = tariff?.topExpires && new Date(tariff.topExpires) > now;

      return {
        ...profile,
        user: {
          ...profile.user,
          telegramId: profile.user.telegramId.toString(),
          tariffs: undefined,
        },
        isTop,
      };
    });

    return NextResponse.json({
      profiles: serializedProfiles,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    console.error("Feed xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
