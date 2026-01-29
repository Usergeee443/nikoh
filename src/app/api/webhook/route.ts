import { NextRequest, NextResponse } from "next/server";
import { Bot, webhookCallback } from "grammy";
import { db } from "@/lib/db";
import { TARIFF_INFO } from "@/lib/utils";

const bot = new Bot(process.env.TELEGRAM_BOT_TOKEN!);

// /start buyrug'i
bot.command("start", async (ctx) => {
  const miniAppUrl = process.env.NEXT_PUBLIC_MINI_APP_URL;

  await ctx.reply(
    "Assalomu alaykum! 👋\n\nNikoh - halal yo'l bilan juftlik topish platformasi.\n\nQuyidagi tugmani bosib ilovaga kiring:",
    {
      reply_markup: {
        inline_keyboard: [
          [
            {
              text: "📱 Ilovaga kirish",
              web_app: { url: miniAppUrl || "" },
            },
          ],
        ],
      },
    }
  );
});

// /help buyrug'i
bot.command("help", async (ctx) => {
  await ctx.reply(
    "🆘 Yordam\n\n" +
      "Nikoh ilovasi orqali siz:\n" +
      "• Halal yo'l bilan juftlik qidirishingiz\n" +
      "• Taklifnomalar yuborishingiz\n" +
      "• Suhbatlashishingiz mumkin\n\n" +
      "Savollaringiz bo'lsa, @nikoh_support ga murojaat qiling."
  );
});

// Rasmni qabul qilish (to'lov cheki)
bot.on("message:photo", async (ctx) => {
  const userId = ctx.from.id;

  // Foydalanuvchini topish
  const user = await db.user.findUnique({
    where: { telegramId: BigInt(userId) },
  });

  if (!user) {
    await ctx.reply("Avval ilovaga kiring va ro'yxatdan o'ting.");
    return;
  }

  // Kutilayotgan to'lovni topish
  const pendingPayment = await db.paymentRequest.findFirst({
    where: {
      userId: user.id,
      status: "PENDING",
    },
    orderBy: { createdAt: "desc" },
  });

  if (!pendingPayment) {
    await ctx.reply(
      "Sizda kutilayotgan to'lov yo'q.\n\nTo'lov qilish uchun ilovadan tarif tanlang."
    );
    return;
  }

  // Rasmni saqlash
  const photo = ctx.message.photo[ctx.message.photo.length - 1];
  await db.paymentRequest.update({
    where: { id: pendingPayment.id },
    data: { receiptFileId: photo.file_id },
  });

  await ctx.reply(
    "✅ Chek qabul qilindi!\n\n" +
      "To'lovingiz tekshirilmoqda. Tasdiqlanganidan so'ng sizga xabar beramiz."
  );
});

// Webhook handler
const handler = webhookCallback(bot, "std/http");

export async function POST(request: NextRequest) {
  try {
    return await handler(request);
  } catch (error) {
    console.error("Webhook xatosi:", error);
    return NextResponse.json({ ok: true });
  }
}

export async function GET() {
  return NextResponse.json({ status: "Bot is running" });
}
