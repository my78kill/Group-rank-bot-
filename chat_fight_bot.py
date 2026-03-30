import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes

# Config / messages
MESSAGES = {
    "not_in_group": "This command only works in groups!",
    "no_messages_yet": "No messages recorded yet!",
    "rank_header": "Your rank"
}
TOP_USERS_COUNT = 10  # dummy, just for placeholders

# DB-less dummy functions
def increment_message_count(user_data, group_id):
    pass

def get_top_users(group_id, limit=10, period='overall'):
    return []

def get_user_rank(user_id, group_id, period='overall'):
    return None

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Add to Group", url="https://t.me/ChatFightBot?startgroup=true"),
            InlineKeyboardButton("📊 Leaderboard", callback_data="show_leaderboard")
        ],
        [
            InlineKeyboardButton("Groups Ranking", callback_data="groups_ranking"),
            InlineKeyboardButton("In-Group Ranking", callback_data="ingroup_ranking")
        ],
        [
            InlineKeyboardButton("Channel", url="https://t.me/Titanic_bots"),
            InlineKeyboardButton("Owner", url="https://t.me/hacker_unity_212")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot_info = (
        "🤖 <b>ChatFight Bot</b>\n\n"
        "Welcome to ChatFight Bot! (DB-less version)\n\n"
        "Features like message counting and leaderboards are disabled in this version."
    )
    await update.message.reply_text(bot_info, reply_markup=reply_markup, parse_mode='HTML')

# Rank command
async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ranking feature is disabled in this version.")

# Top command
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Leaderboard feature is disabled in this version.")

# Ranking command
async def ranking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("All leaderboards are disabled in this version.")

# Main
async def main():
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("rank", rank_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("ranking", ranking_command))

    print("Bot started (DB-less version)...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
