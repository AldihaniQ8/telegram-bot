import os
import io
import datetime
import anthropic
from PIL import Image, ImageDraw
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def wrap_text(text, max_chars=22):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        if len(line + word) <= max_chars:
            line += word + " "
        else:
            if line:
                lines.append(line.strip())
            line = word + " "
    if line:
        lines.append(line.strip())
    return lines

def create_news_image(title, summary, number):
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # خلفية متدرجة داكنة
    for i in range(H):
        ratio = i / H
        r = int(5 + ratio * 15)
        g = int(5 + ratio * 10)
        b = int(25 + ratio * 35)
        draw.line([(0, i), (W, i)], fill=(r, g, b))

    # إطار خارجي ذهبي
    draw.rectangle([15, 15, W-15, H-15], outline=(212, 175, 55), width=4)
    draw.rectangle([22, 22, W-22, H-22], outline=(212, 175, 55), width=1)

    # شريط علوي
    draw.rectangle([15, 15, W-15, 140], fill=(20, 60, 120))

    # نجوم زخرفية
    for x in [60, 100, W-100, W-60]:
        draw.ellipse([x-5, 70-5, x+5, 70+5], fill=(212, 175, 55))

    # رقم الخبر - دائرة
    draw.ellipse([45, 160, 125, 240], fill=(212, 175, 55))
    draw.ellipse([50, 165, 120, 235], fill=(20, 60, 120))

    # خط فاصل تحت الرقم
    draw.line([(80, 270), (W-80, 270)], fill=(212, 175, 55), width=2)

    # نقاط زخرفية
    for x in [80, W//2, W-80]:
        draw.ellipse([x-4, 290-4, x+4, 290+4], fill=(212, 175, 55))

    # خط فاصل قبل الملخص
    draw.line([(80, 560), (W-80, 560)], fill=(212, 175, 55), width=1)

    # شريط سفلي
    draw.rectangle([15, H-130, W-15, H-15], fill=(20, 60, 120))
    draw.line([(80, H-140), (W-80, H-140)], fill=(212, 175, 55), width=1)

    # حفظ الصورة الأساسية بدون نص
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf, title, summary, number

async def send_news_image(context_or_bot, chat_id, title, summary, number):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import arabic_reshaper
        from bidi.algorithm import get_display

        W, H = 1080, 1080
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        for i in range(H):
            ratio = i / H
            r = int(5 + ratio * 15)
            g = int(5 + ratio * 10)
            b = int(25 + ratio * 35)
            draw.line([(0, i), (W, i)], fill=(r, g, b))

        draw.rectangle([15, 15, W-15, H-15], outline=(212, 175, 55), width=4)
        draw.rectangle([15, 15, W-15, 140], fill=(20, 60, 120))
        draw.ellipse([45, 160, 125, 240], fill=(212, 175, 55))
        draw.ellipse([50, 165, 120, 235], fill=(20, 60, 120))
        draw.line([(80, 270), (W-80, 270)], fill=(212, 175, 55), width=2)
        draw.line([(80, 560), (W-80, 560)], fill=(212, 175, 55), width=1)
        draw.rectangle([15, H-130, W-15, H-15], fill=(20, 60, 120))

        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
            font_num = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            font_title = font_body = font_num = font_small = ImageFont.load_default()

        reshaped_header = get_display(arabic_reshaper.reshape("أخبار التقنية"))
        draw.text((W//2, 77), reshaped_header, fill=(255, 255, 255), font=font_title, anchor="mm")

        draw.text((85, 200), str(number), fill=(212, 175, 55), font=font_num, anchor="mm")

        reshaped_title = get_display(arabic_reshaper.reshape(title))
        title_lines = wrap_text(reshaped_title, 20)
        y = 320
        for line in title_lines[:3]:
            draw.text((W//2, y), line, fill=(100, 200, 255), font=font_title, anchor="mm")
            y += 60

        reshaped_summary = get_display(arabic_reshaper.reshape(summary))
        summary_lines = wrap_text(reshaped_summary, 24)
        y = 600
        for line in summary_lines[:6]:
            draw.text((W//2, y), line, fill=(200, 200, 200), font=font_body, anchor="mm")
            y += 50

        tags = get_display(arabic_reshaper.reshape("#تقنية  #أخبار_التقنية  #تكنولوجيا"))
        draw.text((W//2, H-90), tags, fill=(212, 175, 55), font=font_small, anchor="mm")

        date_str = datetime.datetime.now().strftime("%Y/%m/%d")
        draw.text((W//2, H-45), date_str, fill=(150, 150, 150), font=font_small, anchor="mm")

    except Exception:
        W, H = 1080, 1080
        img = Image.new("RGB", (W, H), color=(10, 10, 30))
        draw = ImageDraw.Draw(img)
        draw.rectangle([15, 15, W-15, H-15], outline=(212, 175, 55), width=4)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    bot = context_or_bot if hasattr(context_or_bot, 'send_photo') else context_or_bot.bot
    await bot.send_photo(
        chat_id=chat_id,
        photo=buf,
        caption=f"🔥 {title}\n\n#تقنية #أخبار_التقنية #تكنولوجيا"
    )

async def get_news_and_post(context):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"ابحث عن أحدث 5 أخبار تقنية اليوم {today} وأعطني لكل خبر:\nTITLE: [العنوان]\nSUMMARY: [ملخص 3 جمل]\n---"}]
    )

    response = ""
    for block in message.content:
        if hasattr(block, 'text'):
            response += block.text

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
            await send_news_image(context, CHAT_ID, title, summary, i)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! أنا بوت ذكاء اصطناعي مدعوم بـ Claude 🤖\nاكتب /news للحصول على أحدث أخبار التقنية كصور!")

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
    job_queue = app.job_queue
    job_queue.run_daily(get_news_and_post, time=datetime.time(0, 0, 0))
    print("البوت يعمل ✅")
    app.run_polling()
