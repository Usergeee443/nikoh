import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData } from "@/lib/telegram";

// Sevimlilarni olish
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const initData = searchParams.get("initData");

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

    const favorites = await db.favorite.findMany({
      where: { userId: user.id },
      include: {
        favorite: {
          include: { profile: true },
        },
      },
      orderBy: { createdAt: "desc" },
    });

    const serializedFavorites = favorites.map((f) => ({
      ...f,
      favorite: {
        ...f.favorite,
        telegramId: f.favorite.telegramId.toString(),
      },
    }));

    return NextResponse.json({ favorites: serializedFavorites });
  } catch (error) {
    console.error("Favorites xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}

// Sevimliga qo'shish/o'chirish
export async function POST(request: NextRequest) {
  try {
    const { initData, favoriteUserId } = await request.json();

    if (!initData || !favoriteUserId) {
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
    });

    if (!user) {
      return NextResponse.json(
        { error: "Foydalanuvchi topilmadi" },
        { status: 404 }
      );
    }

    // O'zini sevimliga qo'sha olmaydi
    if (user.id === favoriteUserId) {
      return NextResponse.json(
        { error: "O'zingizni sevimliga qo'sha olmaysiz" },
        { status: 400 }
      );
    }

    // Mavjud ekanligini tekshirish
    const existingFavorite = await db.favorite.findUnique({
      where: {
        userId_favoriteId: {
          userId: user.id,
          favoriteId: favoriteUserId,
        },
      },
    });

    if (existingFavorite) {
      // O'chirish
      await db.favorite.delete({
        where: { id: existingFavorite.id },
      });

      return NextResponse.json({
        message: "Sevimlilardan o'chirildi",
        isFavorite: false,
      });
    } else {
      // Qo'shish
      await db.favorite.create({
        data: {
          userId: user.id,
          favoriteId: favoriteUserId,
        },
      });

      return NextResponse.json({
        message: "Sevimlilarga qo'shildi",
        isFavorite: true,
      });
    }
  } catch (error) {
    console.error("Favorite action xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
