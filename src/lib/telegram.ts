import { Bot } from "grammy";
import crypto from "crypto";

const bot = new Bot(process.env.TELEGRAM_BOT_TOKEN!);

// Telegram WebApp ma'lumotlarini tekshirish
export function validateTelegramWebAppData(initData: string): boolean {
  try {
    const urlParams = new URLSearchParams(initData);
    const hash = urlParams.get("hash");

    // hash va signature ni olib tashlash
    urlParams.delete("hash");
    urlParams.delete("signature");

    const dataCheckString = Array.from(urlParams.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, value]) => `${key}=${value}`)
      .join("\n");

    const secretKey = crypto
      .createHmac("sha256", "WebAppData")
      .update(process.env.TELEGRAM_BOT_TOKEN!)
      .digest();

    const calculatedHash = crypto
      .createHmac("sha256", secretKey)
      .update(dataCheckString)
      .digest("hex");

    const isValid = calculatedHash === hash;

    if (!isValid) {
      console.log("Hash validation failed:", {
        calculated: calculatedHash,
        received: hash,
      });
    }

    return isValid;
  } catch (error) {
    console.error("Validation error:", error);
    return false;
  }
}

// initData dan foydalanuvchi ma'lumotlarini olish
export function parseTelegramInitData(initData: string) {
  const urlParams = new URLSearchParams(initData);
  const userStr = urlParams.get("user");
  if (!userStr) return null;

  try {
    return JSON.parse(userStr) as {
      id: number;
      first_name?: string;
      last_name?: string;
      username?: string;
      language_code?: string;
    };
  } catch {
    return null;
  }
}

// Xabar yuborish
export async function sendTelegramMessage(chatId: number | bigint, text: string) {
  try {
    await bot.api.sendMessage(Number(chatId), text, {
      parse_mode: "HTML",
    });
    return true;
  } catch (error) {
    console.error("Telegram xabar yuborishda xato:", error);
    return false;
  }
}

// Bildirishnoma yuborish - yangi so'rov
export async function notifyNewRequest(
  receiverTelegramId: number | bigint,
  senderName: string
) {
  const text = `💌 <b>Yangi taklifnoma!</b>\n\n${senderName} sizga taklifnoma yubordi.\n\nKo'rish uchun ilovaga kiring.`;
  return sendTelegramMessage(receiverTelegramId, text);
}

// Bildirishnoma yuborish - so'rov qabul qilindi
export async function notifyRequestAccepted(
  senderTelegramId: number | bigint,
  receiverName: string
) {
  const text = `✅ <b>Taklifnoma qabul qilindi!</b>\n\n${receiverName} taklifnomangizni qabul qildi.\n\nEndi suhbatlashishingiz mumkin!`;
  return sendTelegramMessage(senderTelegramId, text);
}

// Bildirishnoma yuborish - yangi xabar
export async function notifyNewMessage(
  receiverTelegramId: number | bigint,
  senderName: string
) {
  const text = `💬 <b>Yangi xabar!</b>\n\n${senderName} sizga xabar yubordi.`;
  return sendTelegramMessage(receiverTelegramId, text);
}

// Admin bildirishnomasi - yangi to'lov
export async function notifyAdminNewPayment(
  userId: string,
  userName: string,
  tariffType: string,
  amount: number
) {
  const adminIds = process.env.ADMIN_TELEGRAM_IDS?.split(",").map((id) =>
    parseInt(id.trim())
  ) || [];

  const text = `💰 <b>Yangi to'lov so'rovi!</b>\n\nFoydalanuvchi: ${userName}\nTarif: ${tariffType}\nSumma: ${amount.toLocaleString()} so'm\n\nID: ${userId}`;

  for (const adminId of adminIds) {
    await sendTelegramMessage(adminId, text);
  }
}

export { bot };
