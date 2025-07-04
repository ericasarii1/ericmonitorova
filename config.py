import logging, os, asyncio
from telegram import (
    Update, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, constants
)
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters,
    ContextTypes, ChatMemberHandler, CallbackContext
)
from datetime import datetime, timedelta

# KONFIGURASI
BOT_TOKEN = "ISI_TOKEN_BOT_KAMU"
GRUP_UTAMA_ID = -1001234567890     # ID Grup Umum
GRUP_ADMIN_ID = -1009876543210     # ID Grup Admin Privat
TOPIK_LOG_ID = 1000                # ID topik log utama
TOPIK_STAT_ID = 1001               # ID topik statistik
TOPIK_VIDEO_ID = 1002              # ID topik obrolan video
TOPIK_PESANPANJANG_ID = 1003       # ID topik pesan panjang

# Logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Statistik sementara
statistik = {
    "join": 0, "left": 0, "kick": 0,
    "mute": 0, "unmute": 0, "ban": 0, "unban": 0,
    "video_started": 0, "video_ended": 0,
    "pesan_panjang": 0, "pesan_total": 0
}

def mention_user(user):
    return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

# Handler anggota masuk/keluar
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    old = member.old_chat_member
    new = member.new_chat_member
    user = member.from_user
    target = member.new_chat_member.user

    if update.chat_member.chat.id != GRUP_UTAMA_ID:
        return

    action = None
    if old.status == "left" and new.status == "member":
        action = f"👋 {mention_user(target)} Join Grup"
        statistik["join"] += 1
    elif old.status in ["member", "restricted"] and new.status == "left":
        action = f"👋 {mention_user(target)} Keluar dari Grup"
        statistik["left"] += 1
    elif old.status in ["member", "restricted"] and new.status == "kicked":
        action = f"⛔ {mention_user(target)} di-Kick oleh {mention_user(user)}"
        statistik["kick"] += 1
    elif old.status == "member" and new.status == "restricted":
        action = f"🔇 {mention_user(target)} di-Mute oleh {mention_user(user)}"
        statistik["mute"] += 1
    elif old.status == "restricted" and new.status == "member":
        action = f"🔊 {mention_user(target)} di-Unmute oleh {mention_user(user)}"
        statistik["unmute"] += 1
    elif old.status != "kicked" and new.status == "kicked":
        action = f"🚫 {mention_user(target)} di-Ban oleh {mention_user(user)}"
        statistik["ban"] += 1
    elif old.status == "kicked" and new.status == "member":
        action = f"✅ {mention_user(target)} di-Unban oleh {mention_user(user)}"
        statistik["unban"] += 1

    if action:
        await context.bot.send_message(
            chat_id=GRUP_ADMIN_ID,
            message_thread_id=TOPIK_LOG_ID,
            text=action,
            parse_mode=constants.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📍 Lihat di Grup", url=f"https://t.me/c/{str(GRUP_UTAMA_ID)[4:]}/1")]
            ])
        )

# Handler pesan
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GRUP_UTAMA_ID:
        return

    statistik["pesan_total"] += 1

    if update.message and update.message.text and len(update.message.text) > 800:
        statistik["pesan_panjang"] += 1
        await context.bot.send_message(
            chat_id=GRUP_ADMIN_ID,
            message_thread_id=TOPIK_PESANPANJANG_ID,
            text=f"📄 Pesan panjang dari {mention_user(update.effective_user)}\nJumlah karakter: {len(update.message.text)}",
            parse_mode=constants.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📍 Lihat Pesan", url=update.message.link)]
            ])
        )

# Handler obrolan video
async def on_videochat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GRUP_UTAMA_ID:
        return

    if update.message.video_chat_started:
        statistik["video_started"] += 1
        await context.bot.send_message(
            chat_id=GRUP_ADMIN_ID,
            message_thread_id=TOPIK_VIDEO_ID,
            text="🎥 Obrolan Video Dimulai!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📍 Lihat Grup", url=f"https://t.me/c/{str(GRUP_UTAMA_ID)[4:]}/1")]
            ])
        )
    elif update.message.video_chat_ended:
        statistik["video_ended"] += 1
        await context.bot.send_message(
            chat_id=GRUP_ADMIN_ID,
            message_thread_id=TOPIK_VIDEO_ID,
            text="📴 Obrolan Video Selesai!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📍 Lihat Grup", url=f"https://t.me/c/{str(GRUP_UTAMA_ID)[4:]}/1")]
            ])
        )

# Statistik reset otomatis jam 00:00 WIB
async def reset_statistik():
    while True:
        now = datetime.utcnow() + timedelta(hours=7)
        target = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        msg = (
            f"📊 Statistik Harian Grup\n"
            f"👥 Join: {statistik['join']}\n"
            f"🚪 Keluar: {statistik['left']}\n"
            f"⛔ Kick: {statistik['kick']}\n"
            f"🔇 Mute: {statistik['mute']}\n"
            f"🔊 Unmute: {statistik['unmute']}\n"
            f"🚫 Ban: {statistik['ban']}\n"
            f"✅ Unban: {statistik['unban']}\n"
            f"🎥 Video Start: {statistik['video_started']}\n"
            f"📴 Video End: {statistik['video_ended']}\n"
            f"📄 Pesan Panjang: {statistik['pesan_panjang']}\n"
            f"💬 Pesan Total: {statistik['pesan_total']}"
        )
        await app.bot.send_message(
            chat_id=GRUP_ADMIN_ID,
            message_thread_id=TOPIK_STAT_ID,
            text=msg
        )
        for key in statistik:
            statistik[key] = 0

# Mulai bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.CHAT_MEMBER))
app.add_handler(MessageHandler(filters.ALL & ~filters.StatusUpdate.ALL, on_message))
app.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_STARTED, on_videochat))
app.add_handler(MessageHandler(filters.StatusUpdate.VIDEO_CHAT_ENDED, on_videochat))

# Jalankan
app.job_queue.run_once(lambda c: asyncio.create_task(reset_statistik()), 1)
app.run_polling()
