import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData } from "@/lib/telegram";

// Profil yaratish/yangilash
export async function POST(request: NextRequest) {
  try {
    const { initData, profile } = await request.json();

    if (!initData || !profile) {
      return NextResponse.json(
        { error: "Ma'lumotlar yetarli emas" },
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
    });

    if (!user) {
      return NextResponse.json(
        { error: "Foydalanuvchi topilmadi" },
        { status: 404 }
      );
    }

    // Profilni yaratish yoki yangilash
    const profileData = {
      gender: profile.gender,
      name: profile.name,
      birthYear: profile.birthYear,
      region: profile.region,
      nationality: profile.nationality,
      maritalStatus: profile.maritalStatus,
      height: profile.height || null,
      weight: profile.weight || null,
      prayerFrequency: profile.prayerFrequency || null,
      fasting: profile.fasting,
      religiousLevel: profile.religiousLevel || null,
      education: profile.education || null,
      profession: profile.profession || null,
      employmentStatus: profile.employmentStatus || null,
      bio: profile.bio || null,
      partnerAgeMin: profile.partnerAgeMin || null,
      partnerAgeMax: profile.partnerAgeMax || null,
      partnerRegion: profile.partnerRegion || null,
      partnerReligiousLevel: profile.partnerReligiousLevel || null,
      partnerMaritalStatus: profile.partnerMaritalStatus || null,
      isComplete: true,
    };

    const updatedProfile = await db.profile.upsert({
      where: { userId: user.id },
      create: {
        userId: user.id,
        ...profileData,
      },
      update: profileData,
    });

    const userWithProfile = await db.user.findUnique({
      where: { id: user.id },
      include: { profile: true },
    });

    const serializedUser = {
      ...userWithProfile,
      telegramId: userWithProfile!.telegramId.toString(),
    };

    return NextResponse.json({ user: serializedUser, profile: updatedProfile });
  } catch (error) {
    console.error("Profil xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}

// Profilni olish
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("userId");

    if (!userId) {
      return NextResponse.json(
        { error: "userId talab qilinadi" },
        { status: 400 }
      );
    }

    const profile = await db.profile.findUnique({
      where: { userId },
      include: {
        user: {
          select: {
            id: true,
            telegramId: true,
            username: true,
            firstName: true,
            lastName: true,
            createdAt: true,
          },
        },
      },
    });

    if (!profile) {
      return NextResponse.json(
        { error: "Profil topilmadi" },
        { status: 404 }
      );
    }

    // Aktiv tarif va TOP holatini tekshirish
    const activeTariff = await db.userTariff.findFirst({
      where: {
        userId: profile.userId,
        isActive: true,
        listingExpires: { gte: new Date() },
      },
    });

    const isTop = activeTariff?.topExpires
      ? new Date(activeTariff.topExpires) > new Date()
      : false;

    return NextResponse.json({
      profile: {
        ...profile,
        user: {
          ...profile.user,
          telegramId: profile.user.telegramId.toString(),
        },
      },
      isTop,
      hasActiveTariff: !!activeTariff,
    });
  } catch (error) {
    console.error("Profil olish xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
