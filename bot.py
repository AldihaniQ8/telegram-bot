import os
import io
import datetime
import anthropic
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def create_news_image(title, summary, number):
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), color=(10, 10, 30))
    draw = ImageDraw.Draw(img)

    # خلفية متدرجة
    for i in range(H):
        r = int(10 + (i / H) * 20)
        g = int(10 + (i / H) * 10)
        b = int(30 + (i / H) * 40)
        draw.line([(0, i), (W, i)], fill=(r, g, b))

    # إطار خارجي
    draw.rectangle([20, 20, W-20, H-20], outline=(100, 200, 255), width=3)

    # شريط علوي
    draw.rectangle([20, 20, W-20, 130], fill=(0, 100, 200))
    draw.text((W//2, 75), "🌐 أخبار التقنية", fill="white", anchor="mm")

    # رقم الخبر
    draw.ellipse([40, 150, 110, 220], fill=(0, 150, 255))
    draw.text((75, 185), str(number), fill="white", anchor="mm")

    # العنوان
    draw.text((W//2, 290), title[:40], fill=(100, 220, 255), anchor="mm")
    if len(title) > 40:
        draw.text((W//2, 340), title[40:80], fill=(100, 220, 255), anchor="mm")

    # خط فاصل
    draw.line([(80, 400), (W-80, 400)], fill=(0, 150, 255), width=2)

    # الملخص
    words = summary.split()
    lines = []
    line = ""
    for word in words:
        if len(line + word) < 28:
            line += word + " "
        else:
            lines.append(line.strip())
            line = word + " "
    lines.append(line.strip())

    y = 440
    for l in lines[:8]:
        draw.text((W//2, y), l, fill=(200, 200, 200), anchor="mm")
        y += 55

    # شريط سفلي
    draw.rectangle([20, H-120, W-20, H-20], fill=(0, 50, 100))
    draw.text((W//2, H-80), "#تقنية  #أخبار_التقنية  #تكنولوجيا", fill=(100, 200, 255), anchor="mm")
    draw.text((W//2, H-40), datetime.datetime.now().strftime("%Y/%m/%d"), fill=(150, 150, 150), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! أنا بوت ذكاء اصطناعي مدعوم بـ Claude 🤖\nسأرسل لك أخبار التقنية يومياً كصور جاهزة للانستغرام!")

async def get_news_and_post(context):
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": """
اكتب 5 أخبار تقنية حديثة. لكل خبر اكتب بهذا الشكل فقط:
TITLE: [عنوان الخبر بالعربي - لا يزيد عن 60 حرف]
SUMMARY: [ملخص الخبر بالعربي في 3 جمل قصيرة]
---
        """}]
    )
    
    response = message.content[0].text
    news_items = response.strip().split("---")
    
    for i, item in enumerate(news_items[:5], 1):
        if "TITLE:" not in item:
            continue
        lines = item.strip().split("\n")
        title = ""
        summary = ""
        for line in lines:
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
        
        if title and summary:
            img = create_news_image(title, summary, i)
            await context.bot.send_photo(
                chat_id=CHAT_ID,
                photo=img,
                caption=f"🔥 {title}\n\n#تقنية #أخبار_التقنية #تكنولوجيا"
            )

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

async def send_news_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري تجهيز الأخبار...")
    await get_news_and_post(context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", send_news_now))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    job_queue.run_daily(get_news_and_post, time=datetime.time(0, 0, 0))

    print("البوت يعمل ✅")
    app.run_polling()
