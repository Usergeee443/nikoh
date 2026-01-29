import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData, sendTelegramMessage } from "@/lib/telegram";
import { TARIFF_INFO } from "@/lib/utils";

export async function POST(request: NextRequest) {
  try {
    const { initData, paymentId, action } = await request.json();

    if (!initData || !paymentId || !action) {
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

    // To'lovni topish
    const payment = await db.paymentRequest.findUnique({
      where: { id: paymentId },
      include: { user: true },
    });

    if (!payment) {
      return NextResponse.json(
        { error: "To'lov topilmadi" },
        { status: 404 }
      );
    }

    if (action === "approve") {
      // Tarif ma'lumotlarini olish
      const tariff = TARIFF_INFO[payment.tariffType as keyof typeof TARIFF_INFO];

      // Tarif muddatlarini hisoblash
      const listingExpires = new Date();
      listingExpires.setDate(listingExpires.getDate() + tariff.listingDays);

      let topExpires = null;
      if (tariff.topDays > 0) {
        topExpires = new Date();
        topExpires.setDate(topExpires.getDate() + tariff.topDays);
      }

      // To'lovni tasdiqlash va tarifni yaratish
      await db.$transaction([
        db.paymentRequest.update({
          where: { id: paymentId },
          data: { status: "APPROVED" },
        }),
        db.userTariff.create({
          data: {
            userId: payment.userId,
            tariffType: payment.tariffType,
            requestsLeft: tariff.requests,
            listingExpires,
            topExpires,
          },
        }),
      ]);

      // Foydalanuvchiga xabar
      sendTelegramMessage(
        payment.user.telegramId,
        `✅ <b>To'lovingiz tasdiqlandi!</b>\n\n${tariff.name} tarifi faollashtirildi.\n\nSizda ${tariff.requests} ta taklifnoma bor.`
      );

      return NextResponse.json({ message: "To'lov tasdiqlandi" });
    } else if (action === "reject") {
      await db.paymentRequest.update({
        where: { id: paymentId },
        data: { status: "REJECTED" },
      });

      // Foydalanuvchiga xabar
      sendTelegramMessage(
        payment.user.telegramId,
        "❌ <b>To'lovingiz rad etildi</b>\n\nIltimos, to'g'ri chek yuborin yoki qo'llab-quvvatlash xizmatiga murojaat qiling."
      );

      return NextResponse.json({ message: "To'lov rad etildi" });
    }

    return NextResponse.json({ error: "Noto'g'ri amal" }, { status: 400 });
  } catch (error) {
    console.error("Payment action xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
