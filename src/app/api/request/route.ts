import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData, notifyNewRequest, notifyRequestAccepted } from "@/lib/telegram";

// So'rov yuborish
export async function POST(request: NextRequest) {
  try {
    const { initData, receiverId, message } = await request.json();

    if (!initData || !receiverId) {
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

    // Yuboruvchini topish
    const sender = await db.user.findUnique({
      where: { telegramId: BigInt(telegramUser.id) },
      include: { profile: true },
    });

    if (!sender || !sender.profile) {
      return NextResponse.json(
        { error: "Profilingiz topilmadi" },
        { status: 404 }
      );
    }

    // Aktiv tarifni tekshirish
    const activeTariff = await db.userTariff.findFirst({
      where: {
        userId: sender.id,
        isActive: true,
        listingExpires: { gte: new Date() },
        requestsLeft: { gt: 0 },
      },
    });

    if (!activeTariff) {
      return NextResponse.json(
        { error: "Aktiv tarif yoki so'rov qolmagan" },
        { status: 403 }
      );
    }

    // Qabul qiluvchini tekshirish
    const receiver = await db.user.findUnique({
      where: { id: receiverId },
      include: { profile: true },
    });

    if (!receiver || !receiver.profile) {
      return NextResponse.json(
        { error: "Qabul qiluvchi topilmadi" },
        { status: 404 }
      );
    }

    // Mavjud so'rovni tekshirish
    const existingRequest = await db.matchRequest.findUnique({
      where: {
        senderId_receiverId: {
          senderId: sender.id,
          receiverId: receiver.id,
        },
      },
    });

    if (existingRequest) {
      return NextResponse.json(
        { error: "So'rov allaqachon yuborilgan" },
        { status: 400 }
      );
    }

    // So'rovni yaratish va tarifni yangilash
    const [matchRequest] = await db.$transaction([
      db.matchRequest.create({
        data: {
          senderId: sender.id,
          receiverId: receiver.id,
          message: message || null,
        },
      }),
      db.userTariff.update({
        where: { id: activeTariff.id },
        data: { requestsLeft: activeTariff.requestsLeft - 1 },
      }),
    ]);

    // Bildirishnoma yuborish
    notifyNewRequest(receiver.telegramId, sender.profile.name);

    return NextResponse.json({
      request: matchRequest,
      requestsLeft: activeTariff.requestsLeft - 1,
    });
  } catch (error) {
    console.error("So'rov yuborish xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}

// So'rovlarni olish
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const initData = searchParams.get("initData");
    const type = searchParams.get("type") || "received"; // received | sent

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

    const requests = await db.matchRequest.findMany({
      where:
        type === "received"
          ? { receiverId: user.id, status: "PENDING" }
          : { senderId: user.id },
      include: {
        sender: {
          include: { profile: true },
        },
        receiver: {
          include: { profile: true },
        },
      },
      orderBy: { createdAt: "desc" },
    });

    const serializedRequests = requests.map((req) => ({
      ...req,
      sender: {
        ...req.sender,
        telegramId: req.sender.telegramId.toString(),
      },
      receiver: {
        ...req.receiver,
        telegramId: req.receiver.telegramId.toString(),
      },
    }));

    return NextResponse.json({ requests: serializedRequests });
  } catch (error) {
    console.error("So'rovlar olish xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}

// So'rovga javob berish (accept/reject)
export async function PUT(request: NextRequest) {
  try {
    const { initData, requestId, action } = await request.json();

    if (!initData || !requestId || !action) {
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

    const matchRequest = await db.matchRequest.findUnique({
      where: { id: requestId },
      include: {
        sender: { include: { profile: true } },
      },
    });

    if (!matchRequest || matchRequest.receiverId !== user.id) {
      return NextResponse.json(
        { error: "So'rov topilmadi" },
        { status: 404 }
      );
    }

    if (matchRequest.status !== "PENDING") {
      return NextResponse.json(
        { error: "So'rov allaqachon qayta ishlangan" },
        { status: 400 }
      );
    }

    if (action === "accept") {
      // So'rovni qabul qilish va chat yaratish
      const expiresAt = new Date();
      expiresAt.setDate(expiresAt.getDate() + 7); // 7 kunlik chat

      const [updatedRequest, chat] = await db.$transaction([
        db.matchRequest.update({
          where: { id: requestId },
          data: { status: "ACCEPTED" },
        }),
        db.chat.create({
          data: {
            requestId,
            user1Id: matchRequest.senderId,
            user2Id: matchRequest.receiverId,
            expiresAt,
          },
        }),
      ]);

      // Bildirishnoma
      notifyRequestAccepted(
        matchRequest.sender.telegramId,
        user.profile?.name || "Foydalanuvchi"
      );

      return NextResponse.json({
        request: updatedRequest,
        chat,
        message: "So'rov qabul qilindi, chat yaratildi",
      });
    } else if (action === "reject") {
      const updatedRequest = await db.matchRequest.update({
        where: { id: requestId },
        data: { status: "REJECTED" },
      });

      return NextResponse.json({
        request: updatedRequest,
        message: "So'rov rad etildi",
      });
    }

    return NextResponse.json({ error: "Noto'g'ri amal" }, { status: 400 });
  } catch (error) {
    console.error("So'rov javob xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
