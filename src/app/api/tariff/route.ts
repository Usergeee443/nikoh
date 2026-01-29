import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData, notifyAdminNewPayment } from "@/lib/telegram";
import { TARIFF_INFO } from "@/lib/utils";

// To'lov so'rovini yaratish
export async function POST(request: NextRequest) {
  try {
    const { initData, tariffType, receiptFileId } = await request.json();

    if (!initData || !tariffType) {
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

    // Tarif ma'lumotlarini olish
    const tariff = TARIFF_INFO[tariffType as keyof typeof TARIFF_INFO];
    if (!tariff) {
      return NextResponse.json(
        { error: "Noto'g'ri tarif turi" },
        { status: 400 }
      );
    }

    // Kutilayotgan to'lov borligini tekshirish
    const pendingPayment = await db.paymentRequest.findFirst({
      where: {
        userId: user.id,
        status: "PENDING",
      },
    });

    if (pendingPayment) {
      return NextResponse.json(
        { error: "Sizda kutilayotgan to'lov bor" },
        { status: 400 }
      );
    }

    // To'lov so'rovini yaratish
    const paymentRequest = await db.paymentRequest.create({
      data: {
        userId: user.id,
        tariffType: tariffType,
        amount: tariff.price,
        receiptFileId: receiptFileId || null,
      },
    });

    // Adminlarga bildirishnoma
    notifyAdminNewPayment(
      user.id,
      user.profile?.name || user.firstName || "Foydalanuvchi",
      tariff.name,
      tariff.price
    );

    return NextResponse.json({
      paymentRequest,
      message: "To'lov so'rovi yaratildi",
    });
  } catch (error) {
    console.error("To'lov so'rovi xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}

// Tariflarni olish
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

    // Aktiv tariflar
    const activeTariffs = await db.userTariff.findMany({
      where: {
        userId: user.id,
        isActive: true,
        listingExpires: { gte: new Date() },
      },
      orderBy: { createdAt: "desc" },
    });

    // Kutilayotgan to'lovlar
    const pendingPayments = await db.paymentRequest.findMany({
      where: {
        userId: user.id,
        status: "PENDING",
      },
      orderBy: { createdAt: "desc" },
    });

    return NextResponse.json({
      activeTariffs,
      pendingPayments,
      tariffInfo: TARIFF_INFO,
    });
  } catch (error) {
    console.error("Tarif olish xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
