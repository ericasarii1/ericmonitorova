import logging
from telegram import Update, MessageEntity, ChatMemberUpdated, ChatPermissions, ChatAction, constants
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes,
    ChatMemberHandler
)
from datetime import datetime
from collections import defaultdict

# === KONFIGURASI BOT ===
BOT_TOKEN = "ISI_TOKEN_BOT_KAMU"
GROUP_UTAMA_ID = -1001234567890  # ID grup publik
GROUP_ADMIN_ID = -1009876543210  # ID grup admin privat
TOPIK_LOG_ID = 123  # ID topik untuk log

# === LOGGING AKTIF ===
logging.basicConfig(level=logging.INFO)

# === VARIABEL UNTUK STATISTIK ===
statistik = defaultdict(int)

# === FORMAT WAKTU ===
def waktu_id():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# === KIRIM LOG KE TOPIK GRUP ADMIN ===
async def kirim_log(context: ContextTypes.DEFAULT_TYPE, isi: str, link: str = None):
    try:
        text = f"📌 <b>LOG GRUP</b>\n🕒 {waktu_id()}\n{isi}"
        if link:
            text += f"\n🔗 <a href='{link}'>Lihat Pesan</a>"
        await context.bot.send_message(
            chat_id=GROUP_ADMIN_ID,
            message_thread_id=TOPIK_LOG_ID,
            text=text,
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logging.warning(f"Gagal kirim log: {e}")

# === DETEKSI JOIN/LEFT/KICK/ETC ===
async def monitor_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != GROUP_UTAMA_ID:
        return

    link = msg.link if hasattr(msg, "link") else f"https://t.me/c/{str(GROUP_UTAMA_ID)[4:]}/{msg.message_id}"

    if msg.new_chat_members:
        for member in msg.new_chat_members:
            await kirim_log(context, f"➕ <b>{member.mention_html()}</b> bergabung ke grup.", link)
            statistik["join"] += 1

    elif msg.left_chat_member:
        await kirim_log(context, f"➖ <b>{msg.left_chat_member.mention_html()}</b> keluar dari grup.", link)
        statistik["leave"] += 1

# === DETEKSI TIPE PESAN UNTUK STATISTIK ===
async def handle_pesan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != GROUP_UTAMA_ID:
        return

    link = f"https://t.me/c/{str(GROUP_UTAMA_ID)[4:]}/{msg.message_id}"

    if msg.text and any(e.type == MessageEntity.URL for e in msg.entities or []):
        await kirim_log(context, f"🔗 <b>{msg.from_user.mention_html()}</b> mengirim tautan.", link)
        statistik["link"] += 1

    elif msg.photo:
        await kirim_log(context, f"🖼️ <b>{msg.from_user.mention_html()}</b> mengirim foto.", link)
        statistik["foto"] += 1

    elif msg.video:
        await kirim_log(context, f"🎞️ <b>{msg.from_user.mention_html()}</b> mengirim video.", link)
        statistik["video"] += 1

    elif msg.sticker:
        await kirim_log(context, f"🎭 <b>{msg.from_user.mention_html()}</b> mengirim stiker.", link)
        statistik["stiker"] += 1

    elif msg.voice or msg.audio:
        await kirim_log(context, f"🎵 <b>{msg.from_user.mention_html()}</b> mengirim audio.", link)
        statistik["audio"] += 1

    elif msg.animation:
        await kirim_log(context, f"🌀 <b>{msg.from_user.mention_html()}</b> mengirim GIF/animasi.", link)
        statistik["animasi"] += 1

    statistik["pesan"] += 1

# === DETEKSI PERUBAHAN STATUS (KICK, BAN, MUTE, ETC) ===
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status: ChatMemberUpdated = update.chat_member
    user = status.new_chat_member.user
    admin = status.from_user
    link = f"https://t.me/c/{str(GROUP_UTAMA_ID)[4:]}/{status.message.message_id}" if hasattr(status, "message") else ""

    lama = status.old_chat_member.status
    baru = status.new_chat_member.status

    tindakan = ""
    if lama in ["member", "restricted"] and baru == "kicked":
        tindakan = f"🚫 <b>{user.mention_html()}</b> di-<b>kick</b> oleh {admin.mention_html()}."
        statistik["kick"] += 1
    elif lama != "banned" and baru == "banned":
        tindakan = f"🔨 <b>{user.mention_html()}</b> di-<b>ban</b> oleh {admin.mention_html()}."
        statistik["ban"] += 1
    elif lama == "banned" and baru in ["member", "restricted"]:
        tindakan = f"♻️ <b>{user.mention_html()}</b> di-<b>unban</b> oleh {admin.mention_html()}."
        statistik["unban"] += 1
    elif lama == "restricted" and baru == "member":
        tindakan = f"🔈 <b>{user.mention_html()}</b> di-<b>unmute</b> oleh {admin.mention_html()}."
        statistik["unmute"] += 1
    elif lama == "member" and baru == "restricted":
        tindakan = f"🔇 <b>{user.mention_html()}</b> di-<b>mute</b> oleh {admin.mention_html()}."
        statistik["mute"] += 1

    if tindakan:
        await kirim_log(context, tindakan, link)

# === OBROLAN VIDEO ===
async def handle_videochat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != GROUP_UTAMA_ID:
        return

    link = f"https://t.me/c/{str(GROUP_UTAMA_ID)[4:]}/{msg.message_id}"

    if msg.video_chat_started:
        await kirim_log(context, "🎥 <b>Obrolan video</b> dimulai!", link)

    if msg.video_chat_ended:
        await kirim_log(context, "📴 <b>Obrolan video</b> telah selesai.", link)

# === PERINTAH /statistik ===
async def statistik_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ADMIN_ID:
        return
    teks = "\n".join([f"• {k}: {v}" for k, v in statistik.items()])
    await update.message.reply_text(f"📊 Statistik Grup:\n{teks}")

# === JALANKAN BOT ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, monitor_member))
    app.add_handler(MessageHandler(filters.ALL & filters.Chat(GROUP_UTAMA_ID), handle_pesan))
    app.add_handler(ChatMemberHandler(handle_status, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.VideoChatStarted() | filters.VideoChatEnded(), handle_videochat))
    app.add_handler(CommandHandler("statistik", statistik_cmd))

    app.run_polling()
