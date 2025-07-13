import time
from database import warn_user, mute_user, ban_user, log_admin_action, get_user
from utils import is_admin

# --- Flood/Spam Detection ---
      #Modify to your spec 
FLOOD_WINDOW = 6      # seconds
FLOOD_LIMIT = 4       # messages per window
DUP_WINDOW = 15       # seconds
WARN_LIMIT = 3        # warnings before auto-mute
BAN_LIMIT = 5         # warnings before auto-ban

USER_MSG_TIMES = {}   
USER_LAST_MSG = {}    

def check_flood(user_id):
    now = time.time()
    if user_id not in USER_MSG_TIMES:
        USER_MSG_TIMES[user_id] = []
    USER_MSG_TIMES[user_id] = [t for t in USER_MSG_TIMES[user_id] if now - t < FLOOD_WINDOW]
    USER_MSG_TIMES[user_id].append(now)
    return len(USER_MSG_TIMES[user_id]) > FLOOD_LIMIT

def check_duplicate(user_id, text):
    now = time.time()
    last = USER_LAST_MSG.get(user_id)
    USER_LAST_MSG[user_id] = (text, now)
    if not last:
        return False
    last_text, last_time = last
    return text == last_text and (now - last_time < DUP_WINDOW)

async def handle_anti_spam(update, context):
    user = update.effective_user
    if is_admin(user.id):
        return False  
    msg_text = update.message.text or update.message.caption or ""
    flood = check_flood(user.id)
    duplicate = check_duplicate(user.id, msg_text)
    user_db = get_user(user.id)
    warns = user_db[6] if user_db else 0

    if flood or duplicate:
        warn_user(user.id)
        log_admin_action(0, user.id, "autowarn", f"Flood/dup: {msg_text[:20]}")
        await update.message.reply_text("⚠️ Spam detected. You have been warned!")
        warns += 1
        if warns == WARN_LIMIT:
            mute_user(user.id, int(time.time()) + 3600)
            log_admin_action(0, user.id, "automute", "Auto-muted (3 warns)")
            await update.message.reply_text("🔇 Auto-muted for 1 hour (3 warnings).")
        elif warns == BAN_LIMIT:
            ban_user(user.id, int(time.time()) + 86400)
            log_admin_action(0, user.id, "autoban", "Auto-banned (5 warns)")
            await update.message.reply_text("⛔ Auto-banned for 24 hours (5 warnings).")
        return True  
    return False  



