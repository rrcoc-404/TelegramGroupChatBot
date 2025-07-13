from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import datetime
from database import get_all_pending_users, approve_user
from config import APPROVAL_MODE
from database import set_toggle, get_toggle
from config import ADMINS, WARN_THRESHOLD
from database import (
    is_admin, get_user_by_username, get_user, set_admin, remove_admin, ban_user, unban_user,
    mute_user, unmute_user, warn_user, reset_warns, get_warns, get_all_admins,
    log_admin_action, get_modhistory, get_admin_log, kick_user, approve_user, reject_user,
    get_all_pending_users, set_welcome, get_welcome, set_pinned, clear_pinned, get_pinned,
    set_user_pinned_msg, get_user_pinned_msg, clear_all_user_pinned_msgs, get_message_by_id,
    get_all_joined_users, delete_message, map_telegram_to_db, get_db_id_from_telegram,
    get_telegram_message_ids_for_db_message, get_toggle, set_toggle
)

def parse_user_arg(arg):
    if arg.startswith("@"):
        target = get_user_by_username(arg)
        if not target:
            return None, None
        return target[0], target[1]
    elif arg.isdigit():
        target = get_user(int(arg))
        if not target:
            return None, None
        return target[0], target[1]
    return None, None

async def adminhelp(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    text = (
        "<b>Admin Commands</b>\n"
        "<code>/ban @username</code> - Ban user (perm)\n"
        "<code>/unban @username</code> - Unban user\n"
        "<code>/mute @username</code> - Mute 1h\n"
        "<code>/unmute @username</code> - Unmute\n"
        "<code>/warn @username</code> - Add a warning (auto-ban at {warns})\n"
        "<code>/resetwarn @username</code> - Clear warns\n"
        "<code>/delete</code> (reply) - Delete message (from all users)\n"
        "<code>/kick @username</code> - Remove user, notifies all\n"
        "<code>/approve @username</code> - Approve pending\n"
        "<code>/approveall</code> - Approve ALL pending users\n"
        "<code>/reject @username</code> - Reject pending\n"
        "<code>/pending</code> - List pending users\n"
        "<code>/pin</code> (reply) - Pin message for all users\n"
        "<code>/unpin</code> - Remove pin\n"
        "<code>/pinned</code> - Show pinned message\n"
        "<code>/modhistory @username</code> - All mod actions for user\n"
        "<code>/togglelinks</code> - Toggle link ban\n"
        "<code>/togglemedia</code> - Toggle media ban\n"
        "<code>/toggleapproval</code> - Toggle approval mode\n"
        "<code>/members</code> - Show current member count\n"
        "<code>/status</code> - Bot stats\n"
        "<code>/setvendor @username</code> - Mark user as vendor\n"
        "<code>/removevendor @username</code> - Remove vendor status\n"
    ).replace("{warns}", str(WARN_THRESHOLD))

    await update.message.reply_html(text)

async def approveall(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    pendings = get_all_pending_users()
    if not pendings:
        await update.message.reply_text("No users pending approval.")
        return
    count = 0
    for u in pendings:
        approve_user(u[0])
        count += 1
    await update.message.reply_text(f"Approved all pending users ({count} total).")

async def toggleapproval(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    current = get_toggle("approval_mode")
    set_toggle("approval_mode", 0 if current else 1)
    state = "ON" if not current else "OFF"
    await update.message.reply_text(f"Approval mode is now {state}.")

async def namehistory(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /namehistory @username or user_id")
        return
    # Get user id
    arg = context.args[0]
    if arg.startswith("@"):
        target = get_user_by_username(arg)
        if not target:
            await update.message.reply_text(f"User {arg} not found.")
            return
        target_id = target[0]
    else:
        try:
            target_id = int(arg)
        except Exception:
            await update.message.reply_text("Invalid user id.")
            return
    hist = get_name_history(target_id, limit=20)
    if not hist:
        await update.message.reply_text("No name history found for this user.")
        return
    lines = []
    for entry in hist:
        dt = datetime.datetime.fromtimestamp(entry[2]).strftime("%Y-%m-%d %H:%M")
        lines.append(f"{dt}: <code>{entry[0]}</code> (@{entry[1] or 'None'})")
    await update.message.reply_html(
        f"<b>Name history for <code>{target_id}</code>:</b>\n" + "\n".join(lines)
    )

async def ban(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    ban_user(target_id)
    log_admin_action(user.id, target_id, "ban", "Permanent ban")
    await update.message.reply_text(
        f"User @{target_username or target_id} has been permanently banned."
    )

async def unban(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    unban_user(target_id)
    log_admin_action(user.id, target_id, "unban", "Unban")
    await update.message.reply_text(
        f"User @{target_username or target_id} has been unbanned."
    )

from database import set_vendor, remove_vendor, is_vendor

async def setvendor(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /setvendor @username or user_id")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    set_vendor(target_id)
    log_admin_action(user.id, target_id, "setvendor", "Marked as vendor")
    await update.message.reply_text(
        f"User @{target_username or target_id} has been marked as a VENDOR."
    )

async def removevendor(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /removevendor @username or user_id")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    remove_vendor(target_id)
    log_admin_action(user.id, target_id, "removevendor", "Vendor role removed")
    await update.message.reply_text(
        f"User @{target_username or target_id} is no longer a VENDOR."
    )

async def mute(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /mute @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    until = int(datetime.datetime.now().timestamp()) + 3600
    mute_user(target_id, until)
    log_admin_action(user.id, target_id, "mute", "Muted 1h")
    await update.message.reply_text(
        f"User @{target_username or target_id} has been muted for 1 hour."
    )

async def unmute(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /unmute @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    unmute_user(target_id)
    log_admin_action(user.id, target_id, "unmute", "Unmute")
    await update.message.reply_text(
        f"User @{target_username or target_id} has been unmuted."
    )

async def warn(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /warn @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    warns = warn_user(target_id)
    log_admin_action(user.id, target_id, "warn", f"Warned, now {warns}")
    msg = f"User @{target_username or target_id} warned. Total warns: {warns}"
    if warns >= WARN_THRESHOLD:
        ban_user(target_id)
        log_admin_action(user.id, target_id, "autoban", f"Auto-banned at {warns} warns")
        msg += f"\nAuto-banned after {warns} warns!"
    await update.message.reply_text(msg)

async def resetwarn(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /resetwarn @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    reset_warns(target_id)
    log_admin_action(user.id, target_id, "resetwarn", "Warns reset")
    await update.message.reply_text(
        f"User @{target_username or target_id}'s warns have been reset."
    )

async def delete(update, context):
    user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message you want to delete with /delete")
        return
    reply_msg = update.message.reply_to_message
    reply_to_id = get_db_id_from_telegram(reply_msg.message_id)
    msg = get_message_by_id(reply_to_id) if reply_to_id else None
    if not msg:
        await update.message.reply_text("Original message not found.")
        return
    if not (is_admin(user.id) or user.id == msg[1]):
        await update.message.reply_text("You can only delete your own messages.")
        return
    delete_message(msg[0])
    log_admin_action(user.id, msg[1], "delete", "Deleted message")
    mapping = get_telegram_message_ids_for_db_message(msg[0])
    for user_id, telegram_msg_id in mapping:
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=telegram_msg_id)
        except Exception:
            pass
    await update.message.reply_text("Message deleted from chat.")

async def kick(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /kick @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    kick_user(target_id)
    log_admin_action(user.id, target_id, "kick", "Removed from chat")
    joined_users = get_all_joined_users()
    for uid in joined_users:
        try:
            await context.bot.send_message(
                uid,
                f"🚫 User @{target_username or target_id} has been kicked from the chat."
            )
        except Exception:
            pass

async def users_list(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return

    user_ids = get_all_joined_users()
    if not user_ids:
        await update.message.reply_text("No users found.")
        return

    lines = []
    for uid in user_ids:
        u = get_user(uid)
        name = u[2]
        username = u[1]
        line = f"<code>{uid}</code>: "
        if username:
            line += f"@{username} ({name})"
        else:
            line += f"{name}"
        lines.append(line)

    await update.message.reply_html("<b>All Users:</b>\n" + "\n".join(lines))

async def pending(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    pendings = get_all_pending_users()
    if not pendings:
        await update.message.reply_text("No users pending approval.")
        return
    lines = []
    for u in pendings:
        lines.append(f"{u[2]} (@{u[1]}) <code>{u[0]}</code>")
    await update.message.reply_html("<b>Pending users:</b>\n" + "\n".join(lines))

async def approve(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /approve @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found or not pending.")
        return
    approve_user(target_id)
    log_admin_action(user.id, target_id, "approve", "User approved")
    from database import get_user, get_all_joined_users, get_welcome
    u = get_user(target_id)
    joined_users = get_all_joined_users()
    welcome = get_welcome()
    count = len(joined_users)
    text = welcome.format(name=u[2], username=u[1] or "N/A", count=count)
    for uid in joined_users:
        try:
            await context.bot.send_message(uid, text)
        except Exception:
            pass
    for admin in ADMINS:
        if admin not in joined_users:
            try:
                await context.bot.send_message(admin, f"User {u[2]} (@{u[1]}) has been approved and joined the chat.")
            except Exception:
                pass

async def reject(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /reject @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found or not pending.")
        return
    reject_user(target_id)
    log_admin_action(user.id, target_id, "reject", "User rejected")
    await update.message.reply_text(f"User @{target_username or target_id} has been rejected.")

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Only admins can pin.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message you want to pin with /pin")
        return
    reply_to_id = get_db_id_from_telegram(update.message.reply_to_message.message_id)
    if not reply_to_id:
        await update.message.reply_text("Could not identify the message to pin.")
        return
    set_pinned(reply_to_id)
    msg = get_message_by_id(reply_to_id)
    uname = msg[8] if msg[8] else "Unknown"
    pin_text = f"<b>Pinned by admin</b>:\n<b>{uname}</b>\n{msg[2]}"
    joined_users = get_all_joined_users()
    for uid in joined_users:
        try:
            mid = get_user_pinned_msg(uid)
            if mid:
                await context.bot.edit_message_text(pin_text, chat_id=uid, message_id=mid, parse_mode="HTML")
            else:
                sent = await context.bot.send_message(uid, pin_text, parse_mode="HTML")
                set_user_pinned_msg(uid, sent.message_id)
        except Exception:
            pass
    await update.message.reply_text("Message pinned and updated for all users.")

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Only admins can unpin.")
        return
    clear_pinned()
    from database import get_all_joined_users, get_user_pinned_msg, clear_all_user_pinned_msgs
    users = get_all_joined_users()
    for uid in users:
        mid = get_user_pinned_msg(uid)
        if mid:
            try:
                await context.bot.edit_message_text("No pinned message.", chat_id=uid, message_id=mid)
            except Exception:
                pass
    clear_all_user_pinned_msgs()
    await update.message.reply_text("Pinned message removed for all users.")

async def pinned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_id = get_pinned()
    if not msg_id:
        await update.message.reply_text("No pinned message.")
        return
    msg = get_message_by_id(msg_id)
    if not msg:
        await update.message.reply_text("Pinned message not found.")
        return
    uname = msg[8] if msg[8] else "Unknown"
    text = f"<b>Pinned by admin</b>:\n<b>{uname}</b>\n{msg[2]}"
    await update.message.reply_html(text)

async def setwelcome(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /setwelcome <message text>")
        return
    text = " ".join(context.args)
    set_welcome(text)
    await update.message.reply_text("Welcome message updated.")

async def auditlog(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    logs = get_admin_log(limit=20)
    text = "<b>Last 20 Admin Actions:</b>\n"
    for l in logs:
        t = datetime.datetime.fromtimestamp(l[2]).strftime("%Y-%m-%d %H:%M")
        text += f"\n<b>{l[0]}</b>: {l[1]} @ {t} (target: {l[3]})"
    await update.message.reply_html(text)

async def modhistory(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /modhistory @username")
        return
    target_id, target_username = parse_user_arg(context.args[0])
    if not target_id:
        await update.message.reply_text(f"User {context.args[0]} not found.")
        return
    logs = get_modhistory(target_id)
    text = f"<b>Last {len(logs)} Moderation Actions for @{target_username or target_id}:</b>\n"
    for l in logs:
        t = datetime.datetime.fromtimestamp(l[2]).strftime("%Y-%m-%d %H:%M")
        text += f"\n<b>{l[0]}</b>: {l[1]} @ {t}"
    await update.message.reply_html(text)

async def admins_list(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    admins = get_all_admins()
    text = "<b>Admins:</b>\n"
    for a in admins:
        text += f"\n{a[1]} (<code>{a[0]}</code>)"
    await update.message.reply_html(text)

async def members(update, context):
    users = get_all_joined_users()
    count = len(users)
    await update.message.reply_text(f"Current chat members: {count}")

async def status(update, context):
    users = get_all_joined_users()
    pendings = get_all_pending_users()
    text = (
        f"Bot is running.\n"
        f"Members: {len(users)}\n"
        f"Pending approvals: {len(pendings)}\n"
    )
    await update.message.reply_text(text)

async def togglelinks(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    current = get_toggle("ban_links")
    set_toggle("ban_links", 0 if current else 1)
    await update.message.reply_text(f"Ban links is now {'ON' if not current else 'OFF'}.")

async def togglemedia(update, context):
    user = update.effective_user
    if not is_admin(user.id):
        return
    current = get_toggle("ban_media")
    set_toggle("ban_media", 0 if current else 1)
    await update.message.reply_text(f"Ban media is now {'ON' if not current else 'OFF'}.")

def register_admin_handlers(app):
    app.add_handler(CommandHandler("adminhelp", adminhelp))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("setvendor", setvendor))
    app.add_handler(CommandHandler("removevendor", removevendor))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("resetwarn", resetwarn))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("toggleapproval", toggleapproval))
    app.add_handler(CommandHandler("approveall", approveall))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("unpin", unpin))
    app.add_handler(CommandHandler("pinned", pinned))
    app.add_handler(CommandHandler("modhistory", modhistory))
    app.add_handler(CommandHandler("admins", admins_list))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(CommandHandler("users", users_list))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("togglelinks", togglelinks))
    app.add_handler(CommandHandler("togglemedia", togglemedia))

