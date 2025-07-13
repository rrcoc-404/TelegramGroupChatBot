from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
import re
import datetime
from database import (
    add_message, get_message_by_id, get_all_joined_users, get_user,
    is_joined, is_pending, get_toggle, warn_user, ban_user, reset_warns, map_telegram_to_db,
    get_db_id_from_telegram
)
from database import is_vendor
from config import ADMINS, WARN_THRESHOLD

def has_link(text):
    return bool(re.search(r'https?://|www\.', text or ""))

async def broadcast_new_message(context, msg_id):
    msg = get_message_by_id(msg_id)
    if not msg:
        return
    
    uname = msg[8] or msg[3] or "Unknown"
    body = msg[2] or ""
    user_id = msg[1]
    vendor_badge = ""
    if is_vendor(user_id):
        vendor_badge = " <b>[VENDOR]</b>"  # Or use an emoji like " 🟡" or " 🛒"
    text = f"<b>{uname}</b>{vendor_badge}"

    
    if msg[5]:
        rep = get_message_by_id(msg[5])
        if rep:
            reply_type = rep[3]
            # Smart reply preview
            if reply_type == "text":
                preview = rep[2][:30] if rep[2] else "[Text]"
            elif reply_type == "photo":
                preview = "[Photo]"
            elif reply_type == "video":
                preview = "[Video]"
            elif reply_type == "animation":
                preview = "[GIF]"
            elif reply_type == "sticker":
                preview = "[Sticker]"
            elif reply_type == "voice":
                preview = "[Voice]"
            else:
                preview = "[Media]"
            text += f"\n<blockquote>↪ {rep[8] or 'Unknown'}: {preview}</blockquote>"
    text += f"\n{body}"

    joined_users = get_all_joined_users()
    for uid in joined_users:
        try:
            sent = None
            if msg[4] and msg[3] == "photo":
                sent = await context.bot.send_photo(uid, msg[4], caption=text, parse_mode="HTML")
            elif msg[4] and msg[3] == "video":
                sent = await context.bot.send_video(uid, msg[4], caption=text, parse_mode="HTML")
            elif msg[4] and msg[3] == "animation":
                sent = await context.bot.send_animation(uid, msg[4], caption=text, parse_mode="HTML")
            elif msg[4] and msg[3] == "sticker":
                sent = await context.bot.send_sticker(uid, msg[4])
            elif msg[4] and msg[3] == "voice":
                sent = await context.bot.send_voice(uid, msg[4], caption=text, parse_mode="HTML")
            else:
                sent = await context.bot.send_message(uid, text, parse_mode="HTML")
            if sent:
                map_telegram_to_db(sent.message_id, msg[0], uid)
        except Exception:
            pass

user_last_msg_time = {}

def check_spam(user_id):
    now = datetime.datetime.now().timestamp()
    last = user_last_msg_time.get(user_id, 0)
    if now - last < 1.5:
        return True
    user_last_msg_time[user_id] = now
    return False

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in ADMINS:
        pass
    else:
        if check_spam(user.id):
            await update.message.reply_text("🛑 Slow down!")
            return
        if not is_joined(user.id) or is_pending(user.id):
            await update.message.reply_text("You are not approved to chat. Use /join.")
            return
        u = get_user(user.id)
        now = int(datetime.datetime.now().timestamp())
        if u[4] and u[4] > now:
            await update.message.reply_text("You are banned.")
            return
        if u[5] and u[5] > now:
            await update.message.reply_text("You are muted.")
            return
        if get_toggle("ban_links") and has_link(update.message.text):
            warns = warn_user(user.id)
            if warns >= WARN_THRESHOLD:
                ban_user(user.id)
                await update.message.reply_text(f"Links are not allowed! You have been auto-banned.")
            else:
                await update.message.reply_text(f"Links are not allowed! Warned ({warns}/{WARN_THRESHOLD}).")
            return

    reply_to = None
    if update.message.reply_to_message:
        reply_to = get_db_id_from_telegram(update.message.reply_to_message.message_id)
    msg_id = add_message(user.id, update.message.text, "text", None, reply_to)
    await update.message.delete()
    context.application.create_task(broadcast_new_message(context, msg_id))

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in ADMINS:
        pass
    else:
        if not is_joined(user.id) or is_pending(user.id):
            return
        if get_toggle("ban_media"):
            warns = warn_user(user.id)
            if warns >= WARN_THRESHOLD:
                ban_user(user.id)
                await update.message.reply_text(f"Media is not allowed! You have been auto-banned.")
            else:
                await update.message.reply_text(f"Media is not allowed! Warned ({warns}/{WARN_THRESHOLD}).")
            await update.message.delete()
            return
    media_type, media_id, caption = None, None, update.message.caption or ""
    if update.message.photo:
        media_type = "photo"
        media_id = update.message.photo[-1].file_id
    elif update.message.video:
        media_type = "video"
        media_id = update.message.video.file_id
    elif update.message.voice:
        media_type = "voice"
        media_id = update.message.voice.file_id
    elif update.message.animation:
        media_type = "animation"
        media_id = update.message.animation.file_id
    else:
        return
    reply_to = None
    if update.message.reply_to_message:
        reply_to = get_db_id_from_telegram(update.message.reply_to_message.message_id)
    msg_id = add_message(user.id, caption, media_type, media_id, reply_to)
    await update.message.delete()
    context.application.create_task(broadcast_new_message(context, msg_id))

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in ADMINS:
        pass
    else:
        if not is_joined(user.id) or is_pending(user.id):
            return
        if get_toggle("ban_media"):
            warns = warn_user(user.id)
            if warns >= WARN_THRESHOLD:
                ban_user(user.id)
                await update.message.reply_text(f"Stickers are not allowed! You have been auto-banned.")
            else:
                await update.message.reply_text(f"Stickers are not allowed! Warned ({warns}/{WARN_THRESHOLD}).")
            await update.message.delete()
            return
    media_type = "sticker"
    media_id = update.message.sticker.file_id
    reply_to = None
    if update.message.reply_to_message:
        reply_to = get_db_id_from_telegram(update.message.reply_to_message.message_id)
    msg_id = add_message(user.id, "", media_type, media_id, reply_to)
    await update.message.delete()
    context.application.create_task(broadcast_new_message(context, msg_id))

def register_chat_handlers(app):
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.VOICE | filters.ANIMATION,
        handle_media
    ))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

