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
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    for i in range(H):
        ratio = i / H
        draw.line([(0, i), (W, i)], fill=(
            int(8 + ratio * 12),
            int(8 + ratio * 8),
            int(28 + ratio * 32)
        ))

    draw.rectangle([15, 15, W-15, H-15], outline=(212, 175, 55), width=4)
    draw.rectangle([15, 15, W-15, 145], fill=(15, 55, 115))

    try:
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        font_num = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
    except:
        font_lg = font_md = font_sm = font_num = ImageFont.load_default()

    draw.text((W//2, 80), "Tech News", fill=(255, 255, 255), font=font_lg, anchor="mm")

    draw.ellipse([45, 158, 128, 242], fill=(212, 175, 55))
    draw.ellipse([52, 165, 121, 235], fill=(15, 55, 115))
    draw.text((86, 200), str(number), fill=(212, 175, 55), font=font_num, anchor="mm")

    draw.line([(80, 275), (W-80, 275)], fill=(212, 175, 55), width=2)

    # العنوان - تقسيم السطور
    words = title.split()
    lines, line = [], ""
    for w in words:
        if len(line + w) <= 18:
            line += w + " "
        else:
            lines.append(line.strip())
            line = w + " "
    lines.append(line.strip())

    y = 310
    for l in lines[:3]:
        draw.text((W//2, y), l, fill=(100, 200, 255), font=font_lg, anchor="mm")
        y += 62

    draw.line([(80, 560), (W-80, 560)], fill=(212, 175, 55), width=1)

    # الملخص
    words2 = summary.split()
    lines2, line2 = [], ""
    for w in words2:
        if len(line2 + w) <= 22:
            line2 += w + " "
        else:
            lines2.append(line2.strip())
            line2 = w + " "
    lines2.append(line2.strip())

    y2 = 595
    for l in lines2[:6]:
        draw.text((W//2, y2), l, fill=(200, 200, 210), font=font_md, anchor="mm")
        y2 += 54

    draw.rectangle([15, H-125, W-15, H-15], fill=(15, 55, 115))
    draw.text((W//2, H-85), "#Tech #TechNews #Technology", fill=(212, 175, 55), font=font_sm, anchor="mm")
    draw.text((W//2, H-42), datetime.datetime.now().strftime("%Y/%m/%d"), fill=(160, 160, 160), font=font_sm, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def get_news_and_post(context):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": f"""
اكتب 5 أخبار تقنية مهمة وحديثة (تاريخ اليوم {today}).
لكل خبر اكتب فقط بهذا الشكل الدقيق:
TITLE: [عنوان قصير بالانجليزي - لا يزيد 8 كلمات]
SUMMARY: [ملخص بالانجليزي في 3 جمل قصيرة]
---
        """}]
    )

    response = message.content[0].text
    items = response.strip().split("---")

    for i, item in enumerate(items[:5], 1):
        if "TITLE:" not in item:
            continue
        title, summary = "", ""
        for line in item.strip().split("\n"):
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
        if title and summary:
            img = create_news_image(title, summary, i)
            await context.bot.send_photo(
                chat_id=CHAT_ID,
                photo=img,
                caption=f"🔥 {title}\n\n#TechNews #Technology #AI"
            )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! أنا بوت ذكاء اصطناعي مدعوم بـ Claude 🤖\nاكتب /news للحصول على أخبار التقنية!")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري تجهيز الأخبار...")
    await get_news_and_post(context)

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
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_daily(get_news_and_post, time=datetime.time(0, 0, 0))
    print("البوت يعمل ✅")
    app.run_polling()
