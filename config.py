import logging, datetime, asyncio
from telegram import (
    Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler,
    ChatMemberHandler, filters, CallbackContext, CommandHandler
)

# ================== KONFIGURASI ===================
BOT_TOKEN = "ISI_TOKEN_BOT_MU"
ID_GRUP_UTAMA = -1001234567890   # Ganti dengan grup publik
ID_GRUP_ADMIN = -1009876543210   # Ganti dengan grup admin
TOPIK_LOG = 1234                 # ID topik/thread untuk laporan log
TOPIK_STAT = 5678                # ID topik/thread untuk statistik
# ==================================================

logging.basicConfig(level=logging.INFO)

# ======== LOGIK PEMBENTUK MENTION & LINK =========
def mention(user):
    if user.username:
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

def msg_link(chat_id, msg_id):
    return f"https://t.me/c/{str(chat_id)[4:]}/{msg_id}"

# ========== HANDLER PERUBAHAN STATUS MEMBER ==========
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    old = member.old_chat_member
    new = member.new_chat_member

    if update.chat.id != ID_GRUP_UTAMA:
        return

    user = new.user
    actor = member.from_user
    teks = ""
    action = None

    if old.status in ['left', 'kicked'] and new.status == 'member':
        teks = f"👋 {mention(user)} bergabung ke grup."
    elif new.status == 'left':
        teks = f"👋 {mention(user)} keluar dari grup."
    elif new.status == 'kicked':
        teks = f"🔨 {mention(user)} di-*ban* oleh {mention(actor)}."
    elif new.status == 'restricted' and new.can_send_messages is False:
        teks = f"🔇 {mention(user)} di-*mute* oleh {mention(actor)}."
    elif old.status == 'restricted' and old.can_send_messages is False and new.can_send_messages:
        teks = f"🔊 {mention(user)} di-*unmute* oleh {mention(actor)}."
    elif old.status == 'kicked' and new.status == 'member':
        teks = f"🔓 {mention(user)} di-*unban* oleh {mention(actor)}."
    elif old.status == 'kicked' and new.status == 'restricted':
        teks = f"⚠️ {mention(user)} di-*unkick* oleh {mention(actor)}."

    if teks:
        await context.bot.send_message(
            chat_id=ID_GRUP_ADMIN,
            message_thread_id=TOPIK_LOG,
            text=teks,
            parse_mode='HTML',
            disable_web_page_preview=True
        )

# ========== PEMANTAU PESAN ==========
async def pesan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != ID_GRUP_UTAMA:
        return

    user = msg.from_user
    teks = ""
    kategori = None

    if msg.video_chat_started:
        teks = f"📢 {mention(user)} memulai obrolan video."
    elif msg.video_chat_ended:
        teks = f"📴 Obrolan video berakhir."
    elif msg.sticker:
        kategori = "stiker"
    elif msg.photo:
        kategori = "gambar"
    elif msg.video:
        kategori = "video"
    elif msg.audio or msg.voice:
        kategori = "audio"

    if teks:
        await context.bot.send_message(
            chat_id=ID_GRUP_ADMIN,
            message_thread_id=TOPIK_LOG,
            text=teks + f"\n<a href='{msg_link(msg.chat.id, msg.message_id)}'>🔗 Ke pesan</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif kategori:
        await context.bot.send_message(
            chat_id=ID_GRUP_ADMIN,
            message_thread_id=TOPIK_LOG,
            text=f"📦 {mention(user)} mengirim {kategori}\n<a href='{msg_link(msg.chat.id, msg.message_id)}'>🔗 Ke pesan</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )

# ========== PERINTAH RESET STAT ==========
stats = {
    "pesan": 0, "stiker": 0, "gambar": 0,
    "video": 0, "audio": 0
}

async def stat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != ID_GRUP_UTAMA:
        return

    stats["pesan"] += 1
    if msg.sticker: stats["stiker"] += 1
    if msg.photo: stats["gambar"] += 1
    if msg.video: stats["video"] += 1
    if msg.audio or msg.voice: stats["audio"] += 1

async def reset_stat(context: CallbackContext):
    teks = (
        f"📊 Statistik Harian Grup:\n"
        f"🗨️ Pesan: {stats['pesan']}\n"
        f"🎭 Stiker: {stats['stiker']}\n"
        f"🖼️ Gambar: {stats['gambar']}\n"
        f"🎞️ Video: {stats['video']}\n"
        f"🎵 Audio: {stats['audio']}"
    )
    await context.bot.send_message(
        chat_id=ID_GRUP_ADMIN,
        message_thread_id=TOPIK_STAT,
        text=teks
    )
    for k in stats: stats[k] = 0

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ID_GRUP_ADMIN:
        await reset_stat(context)
        await update.message.reply_text("Statistik berhasil direset.")

# ========== INISIALISASI ==========
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(ChatMemberHandler(status_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL, pesan_handler))
    app.add_handler(MessageHandler(filters.ALL, stat_handler))
    app.add_handler(CommandHandler("resetstat", cmd_reset))

    job = app.job_queue
    job.run_daily(reset_stat, time=datetime.time(hour=17, minute=0))  # WIB jam 00:00 (UTC+7)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
