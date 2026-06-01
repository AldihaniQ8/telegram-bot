import os
import io
import datetime
import urllib.request
import anthropic
import feedparser
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

FONT_URL = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf"
FONT_PATH = "/tmp/Cairo-Bold.ttf"

def download_font():
    if not os.path.exists(FONT_PATH):
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)

def get_real_news():
    feeds = [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
    ]
    news = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                news.append({
                    "title": entry.title,
                    "summary": entry.get("summary", "")[:300]
                })
        except:
            continue
    return news[:5]

def translate_and_format(title, summary):
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": f"""
ترجم هذا الخبر للعربي:
العنوان: {title}
المحتوى: {summary}

اكتب فقط:
TITLE: [العنوان المترجم - لا يزيد 6 كلمات]
SUMMARY: [ملخص بالعربي في جملتين فقط - لا يزيد 20 كلمة]
        """}]
    )
    response = msg.content[0].text
    t, s = "", ""
    for line in response.strip().split("\n"):
        if line.startswith("TITLE:"):
            t = line.replace("TITLE:", "").strip()
        elif line.startswith("SUMMARY:"):
            s = line.replace("SUMMARY:", "").strip()
    return t, s

def wrap_arabic(text, font, max_width):
    import arabic_reshaper
    from bidi.algorithm import get_display
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = line + w + " "
        reshaped = get_display(arabic_reshaper.reshape(test))
        bbox = font.getbbox(reshaped)
        if bbox[2] - bbox[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(get_display(arabic_reshaper.reshape(line.strip())))
            line = w + " "
    if line:
        lines.append(get_display(arabic_reshaper.reshape(line.strip())))
    return lines

def create_news_image(title, summary, number):
    import arabic_reshaper
    from bidi.algorithm import get_display

    download_font()
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

    draw.rectangle([15, 15, W-15, H-15], outline=(212, 175, 55), width=5)
    draw.rectangle([15, 15, W-15, 160], fill=(15, 55, 115))

    try:
        font_header = ImageFont.truetype(FONT_PATH, 58)
        font_title  = ImageFont.truetype(FONT_PATH, 52)
        font_body   = ImageFont.truetype(FONT_PATH, 42)
        font_num    = ImageFont.truetype(FONT_PATH, 62)
        font_small  = ImageFont.truetype(FONT_PATH, 36)
    except:
        font_header = font_title = font_body = font_num = font_small = ImageFont.load_default()

    header = get_display(arabic_reshaper.reshape("أخبار التقنية"))
    draw.text((W//2, 88), header, fill=(255, 255, 255), font=font_header, anchor="mm")

    draw.ellipse([48, 175, 148, 275], fill=(212, 175, 55))
    draw.ellipse([55, 182, 141, 268], fill=(15, 55, 115))
    draw.text((97, 225), str(number), fill=(212, 175, 55), font=font_num, anchor="mm")

    draw.line([(80, 305), (W-80, 305)], fill=(212, 175, 55), width=3)

    title_lines = wrap_arabic(title, font_title, W - 200)
    y = 345
    for line in title_lines[:3]:
        draw.text((W//2, y), line, fill=(100, 210, 255), font=font_title, anchor="mm")
        y += 72

    draw.line([(80, 580), (W-80, 580)], fill=(212, 175, 55), width=2)

    summary_lines = wrap_arabic(summary, font_body, W - 160)
    y2 = 625
    for line in summary_lines[:5]:
        draw.text((W//2, y2), line, fill=(210, 210, 220), font=font_body, anchor="mm")
        y2 += 65

    draw.rectangle([15, H-145, W-15, H-15], fill=(15, 55, 115))
    draw.line([(80, H-150), (W-80, H-150)], fill=(212, 175, 55), width=2)

    tags = get_display(arabic_reshaper.reshape("#تقنية  #أخبار_التقنية  #تكنولوجيا"))
    draw.text((W//2, H-100), tags, fill=(212, 175, 55), font=font_small, anchor="mm")
    draw.text((W//2, H-50), datetime.datetime.now().strftime("%Y/%m/%d"), fill=(160, 160, 160), font=font_small, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def get_news_and_post(context):
    news_list = get_real_news()
    if not news_list:
        await context.bot.send_message(chat_id=CHAT_ID, text="⚠️ تعذر جلب الأخبار الآن.")
        return
    for i, news in enumerate(news_list[:5], 1):
        title, summary = translate_and_format(news["title"], news["summary"])
        if title and summary:
            img = create_news_image(title, summary, i)
            await context.bot.send_photo(
                chat_id=CHAT_ID,
                photo=img,
                caption=f"🔥 {title}\n\n#تقنية #أخبار_التقنية #تكنولوجيا"
            )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! أنا بوت أخبار التقنية 🤖\nاكتب /news للحصول على أحدث الأخبار!")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري جلب أحدث الأخبار...")
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
        await update.message.reply_text(message.content[0].text)
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
