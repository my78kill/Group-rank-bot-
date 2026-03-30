import os
import asyncio
import sqlite3
from datetime import date, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes

# Config / messages
MESSAGES = {
    "not_in_group": "This command only works in groups!",
    "no_messages_yet": "No messages recorded yet!",
    "rank_header": "Your rank"
}
TOP_USERS_COUNT = 10  # max users to show

# Check if DB is usable
DB_PATH = "chat_counts.db"
USE_DB = os.path.exists(DB_PATH)

# -------------------------------
# Database functions (if DB available)
# -------------------------------
if USE_DB:
    def init_db():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Overall messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                message_count INTEGER DEFAULT 0,
                group_id INTEGER NOT NULL,
                UNIQUE(user_id, group_id)
            )
        ''')
        # Daily messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_daily_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                message_count INTEGER DEFAULT 0,
                group_id INTEGER NOT NULL,
                date DATE NOT NULL,
                UNIQUE(user_id, group_id, date)
            )
        ''')
        # Weekly messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_weekly_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                message_count INTEGER DEFAULT 0,
                group_id INTEGER NOT NULL,
                week_start_date DATE NOT NULL,
                UNIQUE(user_id, group_id, week_start_date)
            )
        ''')
        conn.commit()
        conn.close()

    def increment_message_count(user_data, group_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        try:
            cursor.execute('''
                INSERT INTO user_messages (user_id, username, first_name, last_name, message_count, group_id)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_id, group_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    message_count=message_count+1
            ''', (user_data.id, user_data.username, user_data.first_name, user_data.last_name, group_id))
            
            cursor.execute('''
                INSERT INTO user_daily_messages (user_id, username, first_name, last_name, message_count, group_id, date)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(user_id, group_id, date) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    message_count=message_count+1
            ''', (user_data.id, user_data.username, user_data.first_name, user_data.last_name, group_id, today))
            
            cursor.execute('''
                INSERT INTO user_weekly_messages (user_id, username, first_name, last_name, message_count, group_id, week_start_date)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(user_id, group_id, week_start_date) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    message_count=message_count+1
            ''', (user_data.id, user_data.username, user_data.first_name, user_data.last_name, group_id, week_start))
            
            conn.commit()
        except Exception as e:
            print(f"DB Error: {e}")
        finally:
            conn.close()

    def get_top_users(group_id, limit=10, period='overall'):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if period == 'daily':
            cursor.execute('''
                SELECT username, first_name, last_name, message_count
                FROM user_daily_messages
                WHERE group_id=? AND date=date('now')
                ORDER BY message_count DESC
                LIMIT ?
            ''', (group_id, limit))
        elif period == 'weekly':
            week_start = date.today() - timedelta(days=date.today().weekday())
            cursor.execute('''
                SELECT username, first_name, last_name, message_count
                FROM user_weekly_messages
                WHERE group_id=? AND week_start_date=?
                ORDER BY message_count DESC
                LIMIT ?
            ''', (group_id, week_start, limit))
        else:  # overall
            cursor.execute('''
                SELECT username, first_name, last_name, message_count
                FROM user_messages
                WHERE group_id=?
                ORDER BY message_count DESC
                LIMIT ?
            ''', (group_id, limit))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_user_rank(user_id, group_id, period='overall'):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if period == 'daily':
            cursor.execute('SELECT message_count FROM user_daily_messages WHERE user_id=? AND group_id=? AND date=date("now")', (user_id, group_id))
        elif period == 'weekly':
            week_start = date.today() - timedelta(days=date.today().weekday())
            cursor.execute('SELECT message_count FROM user_weekly_messages WHERE user_id=? AND group_id=? AND week_start_date=?', (user_id, group_id, week_start))
        else:
            cursor.execute('SELECT message_count FROM user_messages WHERE user_id=? AND group_id=?', (user_id, group_id))
        res = cursor.fetchone()
        if not res:
            conn.close()
            return None
        msg_count = res[0]
        if period == 'daily':
            cursor.execute('SELECT COUNT(*) FROM user_daily_messages WHERE group_id=? AND date=date("now") AND message_count>?', (group_id, msg_count))
        elif period == 'weekly':
            week_start = date.today() - timedelta(days=date.today().weekday())
            cursor.execute('SELECT COUNT(*) FROM user_weekly_messages WHERE group_id=? AND week_start_date=? AND message_count>?', (group_id, week_start, msg_count))
        else:
            cursor.execute('SELECT COUNT(*) FROM user_messages WHERE group_id=? AND message_count>?', (group_id, msg_count))
        rank = cursor.fetchone()[0] + 1
        conn.close()
        return rank, msg_count

else:
    # Dummy DB-less fallback
    def init_db(): pass
    def increment_message_count(user_data, group_id): pass
    def get_top_users(group_id, limit=10, period='overall'): return []
    def get_user_rank(user_id, group_id, period='overall'): return None

# -------------------------------
# Bot Commands
# -------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Add to Group", url="https://t.me/ChatFightBot?startgroup=true"),
         InlineKeyboardButton("📊 Leaderboard", callback_data="show_leaderboard")],
        [InlineKeyboardButton("Groups Ranking", callback_data="groups_ranking"),
         InlineKeyboardButton("In-Group Ranking", callback_data="ingroup_ranking")],
        [InlineKeyboardButton("Channel", url="https://t.me/Titanic_bots"),
         InlineKeyboardButton("Owner", url="https://t.me/hacker_unity_212")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot_info = "🤖 <b>ChatFight Bot</b>\n\nWelcome to ChatFight Bot!\nDB features are enabled." if USE_DB else \
               "🤖 <b>ChatFight Bot</b>\n\nDB is unavailable. Counting messages is disabled."
    await update.message.reply_text(bot_info, reply_markup=reply_markup, parse_mode='HTML')

async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if not USE_DB:
        await update.message.reply_text("Ranking feature is disabled (DB missing).")
        return
    res = get_user_rank(user.id, chat_id)
    if res:
        rank, count = res
        await update.message.reply_text(f"{MESSAGES['rank_header']}: #{rank} ({count} messages)")
    else:
        await update.message.reply_text(MESSAGES['no_messages_yet'])

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not USE_DB:
        await update.message.reply_text("Leaderboard is disabled (DB missing).")
        return
    top_users = get_top_users(chat_id, TOP_USERS_COUNT)
    if not top_users:
        await update.message.reply_text(MESSAGES['no_messages_yet'])
        return
    text = "\n".join([f"{i+1}. {u[1] or u[0] or 'Unknown'} - {u[3]} messages" for i, u in enumerate(top_users)])
    await update.message.reply_text(f"Top Users:\n{text}")

async def ranking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("All-time leaderboards command (DB-dependent).")

# -------------------------------
# Main
# -------------------------------
async def main():
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is missing in environment!")
        return
    if USE_DB:
        init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("rank", rank_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("ranking", ranking_command))
    print("Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
