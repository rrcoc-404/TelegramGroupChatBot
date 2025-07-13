from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import datetime
from config import ADMINS
from database import (
    add_user, remove_user, is_joined, is_pending, get_user, get_user_by_username,
    is_admin, get_welcome, get_all_joined_users, is_vendor, get_toggle
)
import time
from collections import deque

JOIN_RATE_LIMIT = 10
JOIN_RATE_WINDOW = 30
JOIN_COOLDOWN = 120
join_timestamps = deque()
join_cooldown_until = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await detect_name_change(user, context)
    await update.message.reply_text(
        f"👋 Welcome, {user.full_name}! Use /join to enter the chatroom."
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global join_cooldown_until
    user = update.effective_user

    now = time.time()
    if now < join_cooldown_until:
        await update.message.reply_text("🚫 Too many join requests. Please try again in a minute.")
        return
    while join_timestamps and join_timestamps[0] < now - JOIN_RATE_WINDOW:
        join_timestamps.popleft()
    join_timestamps.append(now)
    if len(join_timestamps) >= JOIN_RATE_LIMIT:
        join_cooldown_until = now + JOIN_COOLDOWN
        await update.message.reply_text("🚫 Too many join requests. Join is temporarily locked. Try again in 2 minutes.")
        return

    await detect_name_change(user, context)
    approval_mode = get_toggle("approval_mode")
    add_user(user.id, user.username or "", user.full_name, approval_mode=approval_mode)
    if approval_mode:
        await update.message.reply_text(
            "✅ You have requested to join. Please wait for admin approval."
        )
        from config import ADMINS  # important if needed for runtime changes
        for admin_id in ADMINS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🕐 New join request: {user.full_name} (@{user.username or 'No username'}) <code>{user.id}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        joined_users = get_all_joined_users()
        welcome = get_welcome()
        count = len(joined_users)
        text = welcome.format(name=user.full_name, username=user.username or "N/A", count=count)
        for uid in joined_users:
            try:
                await context.bot.send_message(uid, text)
            except Exception:
                pass

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await detect_name_change(user, context)
    remove_user(user.id)
    await update.message.reply_text("❎ You have left the chatroom.")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if context.args:
        if not is_admin(user.id):
            await update.message.reply_text("Only admins can view other users' profiles.")
            return
        target = context.args[0]
        if target.startswith("@"):
            u = get_user_by_username(target)
        else:
            try:
                u = get_user(int(target))
            except Exception:
                u = None
        if not u:
            await update.message.reply_text("User not found.")
            return
    else:
        u = get_user(user.id)
        if not u:
            await update.message.reply_text("Profile not found.")
            return

    joined = "Yes" if u[7] else "No"
    pending = "Yes" if u[9] else "No"
    join_time = (
        datetime.datetime.fromtimestamp(u[8]).strftime("%Y-%m-%d %H:%M")
        if u[8] else "Unknown"
    )
    admin = "✅" if u[3] else "❌"
    banned = (
        f"Until {datetime.datetime.fromtimestamp(u[4])}" if u[4] else "No"
    )
    muted = (
        f"Until {datetime.datetime.fromtimestamp(u[5])}" if u[5] else "No"
    )
    warns = u[6]
    vendor = "✅" if is_vendor(u[0]) else "❌"
    text = (
        f"<b>User Profile</b>\n"
        f"ID: <code>{u[0]}</code>\n"
        f"Name: <code>{u[2]}</code>\n"
        f"Username: @{u[1] if u[1] else 'None'}\n"
        f"Admin: {admin}\n"
        f"Vendor: {vendor}\n"
        f"Warns: {warns}\n"
        f"Banned: {banned}\n"
        f"Muted: {muted}\n"
        f"Joined: {joined}\n"
        f"Pending: {pending}\n"
        f"Join time: {join_time}"
    )
    await update.message.reply_html(text)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>Available Commands:</b>\n"
        "<code>/start</code> - Start or reset\n"
        "<code>/join</code> - Request to join the chatroom\n"
        "<code>/leave</code> - Exit the chatroom\n"
        "<code>/profile</code> - Show your info\n"
        "<code>/help</code> - This help\n"
        "\nAfter joining, just send messages to chat!"
    )
    await update.message.reply_html(text)

async def detect_name_change(user, context):
    from database import get_user, add_user, add_name_history, get_name_history
    u = get_user(user.id)
    changed = False
    notice = ""
    if u:
        if u[2] != user.full_name:
            changed = True
            notice += f"Name change: <code>{u[2]}</code> → <code>{user.full_name}</code>\n"
        if (u[1] or "") != (user.username or ""):
            changed = True
            notice += f"Username change: <code>@{u[1] or 'None'}</code> → <code>@{user.username or 'None'}</code>\n"
    if changed:
        add_user(user.id, user.username or "", user.full_name)
        add_name_history(user.id, user.full_name, user.username or "")
        history = get_name_history(user.id, limit=10)
        history_lines = []
        for entry in history:
            dt = datetime.datetime.fromtimestamp(entry[2]).strftime("%Y-%m-%d %H:%M")
            history_lines.append(f"{dt}: <code>{entry[0]}</code> (@{entry[1] or 'None'})")
        alert = (
            f"🕵️‍♂️ <b>Name/username change detected</b> for <code>{user.id}</code>:\n"
            f"{notice}\n"
            "<b>Last 10 names/usernames:</b>\n" +
            "\n".join(history_lines)
        )
        from config import ADMINS
        for admin_id in ADMINS:
            try:
                await context.bot.send_message(admin_id, alert, parse_mode="HTML")
            except Exception:
                pass

def register_user_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("help", help_cmd))

