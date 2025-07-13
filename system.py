from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database import get_all_joined_users, get_user
from utils import is_admin

import datetime

LOCKDOWN = False
SILENT = False
PINNED_NOTICE = None

async def send_welcome(user_id, context):
    user = get_user(user_id)
    text = f"👋 <b>Welcome</b> {user[2]} (@{user[1]}) to the chatroom!"
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

async def send_goodbye(user_id, context):
    user = get_user(user_id)
    text = f"👋 <b>{user[2]}</b> (@{user[1]}) has left the chatroom."
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

async def lockdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global LOCKDOWN
    user = update.effective_user
    if not is_admin(user.id):
        return
    LOCKDOWN = True
    text = "🚨 <b>Chatroom is now in lockdown! Only admins can send messages.</b>"
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global LOCKDOWN
    user = update.effective_user
    if not is_admin(user.id):
        return
    LOCKDOWN = False
    text = "✅ <b>Lockdown lifted! Everyone can chat again.</b>"
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

def is_lockdown():
    return LOCKDOWN

async def silent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SILENT
    user = update.effective_user
    if not is_admin(user.id):
        return
    SILENT = True
    text = "🔕 <b>Silent mode enabled!</b> Only admins may speak (for announcements)."
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

async def unsilent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SILENT
    user = update.effective_user
    if not is_admin(user.id):
        return
    SILENT = False
    text = "🔔 <b>Silent mode disabled.</b> Everyone may speak again."
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

def is_silent():
    return SILENT

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PINNED_NOTICE
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /pin <notice>")
        return
    PINNED_NOTICE = " ".join(context.args)
    text = f"📌 <b>Pinned Notice:</b>\n{PINNED_NOTICE}"
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PINNED_NOTICE
    user = update.effective_user
    if not is_admin(user.id):
        return
    PINNED_NOTICE = None
    text = "📌 <b>Pinned Notice has been removed.</b>"
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

def get_pinned_notice():
    return PINNED_NOTICE

async def motd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /motd <message>")
        return
    text = "💡 <b>Message of the Day:</b>\n" + " ".join(context.args)
    for uid in get_all_joined_users():
        try:
            await context.bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass

def register_system_handlers(app):
    app.add_handler(CommandHandler("lockdown", lockdown))
    app.add_handler(CommandHandler("unlock", unlock))
    app.add_handler(CommandHandler("silent", silent))
    app.add_handler(CommandHandler("unsilent", unsilent))
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("unpin", unpin))
    app.add_handler(CommandHandler("motd", motd))

