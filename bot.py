"""
Telegram SMS Bot — Render Web Service / Webhook starter
Python 3.10+
"""
import os
import logging
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()
OTP_GROUP_URL = os.getenv("OTP_GROUP_URL", "").strip()
SUPPORT_URL = os.getenv("SUPPORT_URL", "").strip()
DB_PATH = os.getenv("DB_PATH", "/tmp/sms_bot.db")
PORT = int(os.getenv("PORT", "10000"))
PUBLIC_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

try:
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW else 0
except ValueError:
    ADMIN_ID = 0

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("sms-bot")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, created_at TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            endpoint TEXT DEFAULT '', price TEXT DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            service TEXT NOT NULL, phone TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL
        )""")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('announcement','')")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('default_rate','')")
        con.commit()


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_ID and user_id == ADMIN_ID)


def main_keyboard(user_id: int):
    rows = [
        [InlineKeyboardButton("📲 Get Number", callback_data="get_number"),
         InlineKeyboardButton("👥 OTP Group", callback_data="otp_group")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile"),
         InlineKeyboardButton("🛟 Support", callback_data="support")],
        [InlineKeyboardButton("🔢 Prefix", callback_data="prefix")],
    ]
    if is_admin(user_id):
        rows.append([InlineKeyboardButton("🛡 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def back_keyboard(user_id: int):
    rows = [[InlineKeyboardButton("⬅️ Main Menu", callback_data="home")]]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        con.execute(
            "INSERT INTO users(user_id,username,first_name,created_at) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name",
            (user.id, user.username or "", user.first_name or "", now),
        )
        con.commit()
    await update.effective_message.reply_text(
        "🤖 *SMS Bot*\\n\\nWelcome! Neeche menu se option select karein.",
        reply_markup=main_keyboard(user.id), parse_mode="Markdown",
    )


async def show_home(query, user_id):
    await query.edit_message_text(
        "🤖 *SMS Bot*\\n\\nApna option select karein:",
        reply_markup=main_keyboard(user_id), parse_mode="Markdown",
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id, action = query.from_user.id, query.data

    if action == "home":
        return await show_home(query, user_id)

    if action == "get_number":
        return await query.edit_message_text(
            "📲 *Get Number*\\n\\nLamix API abhi connect nahi hui. Official API documentation "
            "ke mutabiq integration add karni hogi.",
            reply_markup=back_keyboard(user_id), parse_mode="Markdown")

    if action == "otp_group":
        if OTP_GROUP_URL:
            return await query.edit_message_text(
                "OTP Group join karne ke liye neeche click karein.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👥 Join OTP Group", url=OTP_GROUP_URL)],
                    [InlineKeyboardButton("⬅️ Main Menu", callback_data="home")]
                ]))
        return await query.edit_message_text("OTP_GROUP_URL set nahi hai.",
                                             reply_markup=back_keyboard(user_id))

    if action == "profile":
        with db() as con:
            u = con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
            count = con.execute("SELECT COUNT(*) AS n FROM orders WHERE user_id=?", (user_id,)).fetchone()["n"]
        username = ("@" + u["username"]) if u and u["username"] else "Not set"
        return await query.edit_message_text(
            f"👤 *My Profile*\\n\\nUser ID: `{user_id}`\\nUsername: {username}\\n"
            f"Account: Active\\nOrders: {count}\\n\\n"
            "💳 Virtual Wallet: real balance/payment ledger abhi configure nahi hai.",
            reply_markup=back_keyboard(user_id), parse_mode="Markdown")

    if action == "support":
        if SUPPORT_URL:
            return await query.edit_message_text("Support se rabta karein:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛟 Contact Support", url=SUPPORT_URL)],
                    [InlineKeyboardButton("⬅️ Main Menu", callback_data="home")]
                ]))
        return await query.edit_message_text("SUPPORT_URL set nahi hai.",
                                             reply_markup=back_keyboard(user_id))

    if action == "prefix":
        with db() as con:
            rows = con.execute("SELECT name,price FROM servers WHERE enabled=1 ORDER BY id").fetchall()
        body = "\\n".join(f"• {r['name']} — {r['price'] or 'Rate not set'}" for r in rows)
        msg = "🔢 *Prefixes / Servers*\\n\\n" + body if rows else "Abhi koi prefix/server add nahi hua."
        return await query.edit_message_text(msg, reply_markup=back_keyboard(user_id), parse_mode="Markdown")

    if action == "admin":
        if not is_admin(user_id):
            return await query.edit_message_text("⛔ Access denied.", reply_markup=back_keyboard(user_id))
        return await query.edit_message_text(
            "🛡 *Admin Panel*\\n\\n/addserver NAME | PRICE\\n/setrate RATE\\n"
            "/disableserver ID\\n/stats",
            reply_markup=back_keyboard(user_id), parse_mode="Markdown")

    if action.startswith("admin_") and not is_admin(user_id):
        return await query.edit_message_text("⛔ Access denied.", reply_markup=back_keyboard(user_id))


async def addserver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.effective_message.reply_text("⛔ Access denied.")
    raw = " ".join(context.args)
    if "|" not in raw:
        return await update.effective_message.reply_text("Format: /addserver NAME | PRICE")
    name, price = [x.strip() for x in raw.split("|", 1)]
    if not name:
        return await update.effective_message.reply_text("Server name required.")
    with db() as con:
        con.execute("INSERT INTO servers(name,price) VALUES(?,?)", (name, price))
        con.commit()
    await update.effective_message.reply_text(f"✅ Server added: {name} — {price}")


async def setrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.effective_message.reply_text("⛔ Access denied.")
    if len(context.args) != 1:
        return await update.effective_message.reply_text("Format: /setrate RATE")
    with db() as con:
        con.execute("UPDATE settings SET value=? WHERE key='default_rate'", (context.args[0],))
        con.commit()
    await update.effective_message.reply_text(f"✅ Default rate saved: {context.args[0]}")


async def disable_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.effective_message.reply_text("⛔ Access denied.")
    if len(context.args) != 1 or not context.args[0].isdigit():
        return await update.effective_message.reply_text("Format: /disableserver ID")
    with db() as con:
        cur = con.execute("UPDATE servers SET enabled=0 WHERE id=?", (int(context.args[0]),))
        con.commit()
    await update.effective_message.reply_text("✅ Server disabled." if cur.rowcount else "Server ID not found.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.effective_message.reply_text("⛔ Access denied.")
    with db() as con:
        users = con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        servers = con.execute("SELECT COUNT(*) n FROM servers WHERE enabled=1").fetchone()["n"]
        orders = con.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
    await update.effective_message.reply_text(
        f"📊 Stats\\nUsers: {users}\\nEnabled servers: {servers}\\nOrders recorded: {orders}")


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing. Render Environment mein BOT_TOKEN set karein.")
    if not PUBLIC_URL:
        raise SystemExit("RENDER_EXTERNAL_URL missing. Render Web Service par deploy karein.")
    if not ADMIN_ID:
        log.warning("ADMIN_ID missing/invalid: admin panel will not be available.")
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addserver", addserver))
    app.add_handler(CommandHandler("setrate", setrate))
    app.add_handler(CommandHandler("disableserver", disable_server))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(callback_handler))

    webhook_path = WEBHOOK_SECRET or BOT_TOKEN.split(":")[0]
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=webhook_path,
        webhook_url=f"{PUBLIC_URL}/{webhook_path}",
        secret_token=WEBHOOK_SECRET or None,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
