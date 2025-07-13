import nest_asyncio
nest_asyncio.apply()
import asyncio
from telegram.ext import ApplicationBuilder
from config import BOT_TOKEN, AUTO_POSTS
from database import init_db, get_all_joined_users
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers
from handlers.chat import register_chat_handlers

init_db()

async def autopost_loop(app):
    if not AUTO_POSTS:
        return
    from telegram.error import TelegramError
    while True:
        for post in AUTO_POSTS:
            users = get_all_joined_users()
            for uid in users:
                try:
                    await app.bot.send_message(uid, post["text"])
                except TelegramError:
                    pass
            await asyncio.sleep(post.get("interval_minutes", 60) * 60)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    register_admin_handlers(app)
    register_user_handlers(app)
    register_chat_handlers(app)
    asyncio.create_task(autopost_loop(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

