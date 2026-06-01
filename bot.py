import os
import asyncio
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! أنا بوت ذكاء اصطناعي مدعوم بـ Claude 🤖")

async def get_news_and_post(context):
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": """
اكتب أحدث 5 أخبار تقنية اليوم وصمم لكل خبر بوست لمنصات التواصل الاجتماعي:

━━━━━━━━━━━━━━━━
🔥 [عنوان الخبر]
━━━━━━━━━━━━━━━━
📌 التفاصيل:
[ملخص 2-3 جمل]
💡 لماذا يهمك؟
[الأهمية]
#تقنية #تكنولوجيا #أخبار_التقنية
        """}]
    )
    response = message.content[0].text
    await context.bot.send_message(chat_id=CHAT_ID, text=response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text("⏳ جاري المعالجة...")
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": user_message}]
        )
        response = message.content[0].text
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    job_queue.run_daily(get_news_and_post, time=__import__('datetime').time(0, 0, 0))

    print("البوت يعمل ✅")
    app.run_polling()

