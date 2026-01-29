import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTelegramWebAppData, parseTelegramInitData } from "@/lib/telegram";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const initData = searchParams.get("initData");
    const type = searchParams.get("type") || "stats";

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

    // Admin ekanligini tekshirish
    const user = await db.user.findUnique({
      where: { telegramId: BigInt(telegramUser.id) },
    });

    if (!user?.isAdmin) {
      return NextResponse.json(
        { error: "Ruxsat yo'q" },
        { status: 403 }
      );
    }

    if (type === "stats") {
      const [totalUsers, activeProfiles, totalRequests, totalChats, pendingPayments] =
        await Promise.all([
          db.user.count(),
          db.profile.count({ where: { isActive: true } }),
          db.matchRequest.count(),
          db.chat.count(),
          db.paymentRequest.count({ where: { status: "PENDING" } }),
        ]);

      return NextResponse.json({
        stats: {
          totalUsers,
          activeProfiles,
          totalRequests,
          totalChats,
          pendingPayments,
        },
      });
    }

    if (type === "payments") {
      const payments = await db.paymentRequest.findMany({
        where: { status: "PENDING" },
        include: {
          user: {
            include: { profile: true },
          },
        },
        orderBy: { createdAt: "desc" },
      });

      const serializedPayments = payments.map((p) => ({
        ...p,
        user: {
          ...p.user,
          telegramId: p.user.telegramId.toString(),
        },
      }));

      return NextResponse.json({ payments: serializedPayments });
    }

    if (type === "users") {
      const users = await db.user.findMany({
        include: { profile: true },
        orderBy: { createdAt: "desc" },
        take: 100,
      });

      const serializedUsers = users.map((u) => ({
        ...u,
        telegramId: u.telegramId.toString(),
      }));

      return NextResponse.json({ users: serializedUsers });
    }

    return NextResponse.json({ error: "Noto'g'ri tur" }, { status: 400 });
  } catch (error) {
    console.error("Admin xatosi:", error);
    return NextResponse.json({ error: "Server xatosi" }, { status: 500 });
  }
}
