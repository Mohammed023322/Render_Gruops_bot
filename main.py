import json
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ConversationHandler, ContextTypes

TOKEN = "8060609250:AAEe47qcmRTlA4TETGG5DjJODbjc0-pvI-0"
JSON_FILE = "responses.json"

def load_responses():
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_responses(data):
    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

async def is_admin(update: Update) -> bool:
    chat_member = await update.effective_chat.get_member(update.effective_user.id)
    return chat_member.status in ["administrator", "creator"]

async def add_start(update, context):
    if not await is_admin(update):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return ConversationHandler.END

    await update.message.reply_text("🔹 أرسل الكلمة المفتاحية:")
    return "KEYWORD"

async def receive_keyword(update, context):
    context.user_data["keyword"] = update.message.text.strip()
    await update.message.reply_text("🔹 الآن، أرسل الرد (نص، صورة، أو فيديو مع نص):")
    return "RESPONSE"

async def receive_response(update, context):
    keyword = context.user_data.get("keyword")
    text_content = update.message.caption if update.message.caption else update.message.text

    if update.message.text:
        response_type = "text"
        content = update.message.text.strip()
    elif update.message.photo:
        response_type = "photo"
        content = update.message.photo[-1].file_id
    elif update.message.video:
        response_type = "video"
        content = update.message.video.file_id
    else:
        await update.message.reply_text("❌ نوع الرد غير مدعوم.")
        return "RESPONSE"

    data = load_responses()
    data[keyword] = {
        "type": response_type,
        "content": content,
        "text": text_content.strip() if text_content else ""
    }

    save_responses(data)
    await update.message.reply_text(f"✅ تم حفظ الرد لكلمة: {keyword}")
    return ConversationHandler.END

async def message_handler(update, context):
    if update.message.text:
        text = update.message.text.lower()
    else:
        return

    data = load_responses()
    for keyword, response in data.items():
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, text):
            response_type = response["type"]
            content = response["content"]
            additional_text = response["text"]
            
            if response_type == "text":
                await update.message.reply_text(additional_text)
            elif response_type == "photo":
                await update.message.reply_photo(content, caption=additional_text if additional_text else None)
            elif response_type == "video":
                await update.message.reply_video(content, caption=additional_text if additional_text else None)
            break

async def list_responses(update, context):
    data = load_responses()
    if not data:
        await update.message.reply_text("❌ لا توجد ردود محفوظة.")
        return
    
    message = "✅ الردود المحفوظة:\n"
    for keyword, response in data.items():
        message += f"- {keyword}: {response['type']}\n"
    
    await update.message.reply_text(message)

async def delete_response(update, context):
    if not await is_admin(update):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط.")
        return

    text = update.message.text.strip().lower()
    keyword_match = re.search(r"^حذف (.+)", text)
    if not keyword_match:
        await update.message.reply_text("❌ يجب أن تحدد الكلمة التي تريد حذفها. مثال: حذف كلمة")
        return

    keyword = keyword_match.group(1).strip()
    data = load_responses()

    if keyword in data:
        del data[keyword]
        save_responses(data)
        await update.message.reply_text(f"✅ تم حذف الرد للكلمة: {keyword}")
    else:
        await update.message.reply_text(f"❌ لا توجد ردود محفوظة لهذه الكلمة: {keyword}")

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^اضف$") & filters.TEXT, add_start)],
        states={
            "KEYWORD": [MessageHandler(filters.TEXT, receive_keyword)],
            "RESPONSE": [MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, receive_response)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.Regex("^اضف$|^حذف .*|^ردود$"), message_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^حذف .*"), delete_response))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^ردود$"), list_responses))
    
    app.run_polling()

if __name__ == "__main__":
    main()
