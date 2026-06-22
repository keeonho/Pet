import asyncio, time, logging, random, json, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ChatMemberHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN    = "8563517490:AAGpcFKnMfNmUNGmAoOSk1uMDBWC3Gbfq3Y"
LOG_GROUP_ID = -1003770475873

# IDs yang boleh pakai /broadcast
ADMIN_IDS = {8513979925}

# File penyimpanan group
GROUPS_FILE = "known_groups.json"

def load_groups() -> set:
    if os.path.exists(GROUPS_FILE):
        try:
            return set(json.load(open(GROUPS_FILE)))
        except Exception:
            pass
    return set()

def save_groups():
    try:
        with open(GROUPS_FILE, "w") as f:
            json.dump(list(known_group_chats), f)
    except Exception as e:
        logging.warning(f"Gagal simpan groups: {e}")

# Load saat startup
known_group_chats: set = load_groups()

# File penyimpanan users (private)
USERS_FILE = "known_users.json"

def load_users() -> set:
    if os.path.exists(USERS_FILE):
        try:
            return set(json.load(open(USERS_FILE)))
        except Exception:
            pass
    return set()

def save_users():
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(list(known_user_chats), f)
    except Exception as e:
        logging.warning(f"Gagal simpan users: {e}")

known_user_chats: set = load_users()

def add_user(user_id: int):
    if user_id not in known_user_chats:
        known_user_chats.add(user_id)
        save_users()
PHOTO_AKAD     = "https://files.catbox.moe/j2sywd.jpg"
PHOTO_BUNGA    = "https://files.catbox.moe/u8fwim.jpg"
PHOTO_BUKNIKAH = "https://files.catbox.moe/q9f5cu.jpg"
MC_NAME = "Reverend Carter"

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
wedding_sessions, active_weddings, married_couples = {}, {}, {}

# Respon MC saat pengantin kirim janji - acak tiap pernikahan
MC_REACTIONS_JANJI = [
    "💖 *Sungguh kata-kata yang tulus dan menyentuh hati...*\n🥺 *Beberapa tamu mengusap air mata...*",
    "✨ *Kata-kata penuh cinta yang akan dikenang selamanya...*\n😭 *Ruangan hening, semua terharu...*",
    "💕 *Janji yang keluar dari lubuk hati yang paling dalam...*\n🤧 *Bahkan fotografer pun ikut terharu...*",
    "🌹 *Indah sekali... semua hadirin terpesona...*\n💫 *Momen ini akan dikenang seumur hidup...*",
]
MC_REACTIONS_STICKER = [
    "😄 *MC tersenyum melihat keceriaan pengantin!*",
    "🎉 *Suasana makin meriah!*",
    "😂 *Tamu undangan tertawa bahagia!*",
    "🥳 *Energi bahagia menyebar ke seluruh ruangan!*",
]

async def send_log(bot, text):
    try: await bot.send_message(chat_id=LOG_GROUP_ID, text=text, parse_mode="Markdown")
    except Exception as e: logging.warning(f"Log gagal: {e}")

def fmt_time(): return time.strftime('%d %B %Y  %H:%M')

# =============================================
# WEDDING OFFICIANT CLASS
# =============================================

class WeddingOfficiant:
    def __init__(self, bot, chat_id, session):
        self.bot, self.chat_id, self.data = bot, chat_id, session
        self.saksi_ids, self.saksi_names = [], []
        self.need_saksi = 3
        self.active = True
        self.witness_msg_id = None

        # Untuk menunggu input interaktif
        self.waiting_for = None       # "janji_1" | "janji_2" | "sticker_1" | "sticker_2"
        self.input_received = asyncio.Event()
        self.input_value = None       # isi pesan yang diterima

        # Tombol konfirmasi per fase
        self.confirm_event = asyncio.Event()
        self.confirm_user_id = None

    # ──────────────────────────────────────
    # SEND / EDIT dengan flood protection
    # ──────────────────────────────────────

    async def send(self, text, photo=None, reply_markup=None):
        for attempt in range(3):
            try:
                if photo:
                    return await self.bot.send_photo(chat_id=self.chat_id, photo=photo, caption=text, parse_mode="Markdown", reply_markup=reply_markup)
                return await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
            except Exception as e:
                if "Flood" in str(e) or "retry" in str(e).lower():
                    wait = int(''.join(filter(str.isdigit, str(e))) or 30)
                    logging.warning(f"Flood {wait}s..."); await asyncio.sleep(wait)
                else:
                    logging.error(f"send error: {e}"); return None
        return None

    async def edit(self, msg_id, text, reply_markup=None):
        for attempt in range(3):
            try:
                await self.bot.edit_message_text(chat_id=self.chat_id, message_id=msg_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
                return
            except Exception as e:
                if "Flood" in str(e) or "retry" in str(e).lower():
                    wait = int(''.join(filter(str.isdigit, str(e))) or 30)
                    await asyncio.sleep(wait)
                else:
                    logging.warning(f"edit error: {e}"); return

    # ──────────────────────────────────────
    # HELPER: tunggu input dengan timeout
    # ──────────────────────────────────────

    async def wait_input(self, waiting_for: str, timeout: int = 60):
        """Tunggu input dari pengantin. Return value atau None kalau timeout."""
        self.waiting_for = waiting_for
        self.input_received.clear()
        self.input_value = None
        try:
            await asyncio.wait_for(self.input_received.wait(), timeout=timeout)
            return self.input_value
        except asyncio.TimeoutError:
            return None
        finally:
            self.waiting_for = None

    async def wait_confirm(self, user_id: int, timeout: int = 60):
        """Tunggu tombol konfirmasi dari user tertentu."""
        self.confirm_event.clear()
        self.confirm_user_id = user_id
        try:
            await asyncio.wait_for(self.confirm_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self.confirm_user_id = None

    def receive_input(self, waiting_for: str, value):
        """Dipanggil dari msg_handler saat ada input masuk."""
        if self.waiting_for == waiting_for:
            self.input_value = value
            self.input_received.set()

    def receive_confirm(self, user_id: int):
        """Dipanggil dari callback_handler saat tombol konfirmasi dipencet."""
        if self.confirm_user_id == user_id:
            self.confirm_event.set()

    # ──────────────────────────────────────
    # MAIN RUN
    # ──────────────────────────────────────

    async def run(self):
        await self.phase_pembukaan()
        await self.phase_persiapan()
        await self.phase_kedatangan_tamu()
        await self.phase_prosesi_masuk()
        await self.phase_sambutan_mc()
        await self.phase_doa_pembuka()
        await self.phase_kata_sambutan_ortu()
        await self.phase_ijab_kabul_interaktif()    # ← pengantin 1 & 2 ketik janji
        await self.phase_tunggu_saksi()
        if not self.active: return
        await self.phase_pengumuman_sah()
        await self.phase_tukar_cincin_interaktif()  # ← pengantin pencet tombol konfirmasi
        await self.phase_ciuman_pertama_interaktif()# ← pengantin pencet tombol
        await self.phase_sticker_pengantin()        # ← pengantin kirim sticker/foto reaksi
        await self.phase_doa_penutup()
        await self.phase_foto_resmi()
        await self.phase_lempar_bunga()
        await self.phase_ucapan_selamat()
        await self.phase_resepsi()
        await self.phase_potong_kue_interaktif()    # ← kedua pengantin pencet tombol bareng
        await self.phase_tarian_pengantin()
        await self.phase_pelepasan()
        await self.phase_sertifikat()

    # ──────────────────────────────────────
    # FASE-FASE
    # ──────────────────────────────────────

    async def phase_pembukaan(self):
        base = (
            "🎺 *SELAMAT DATANG DI ACARA PERNIKAHAN* 🎺\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💒 *{self.data['requester_name']}* & *{self.data['partner_name']}* 💒\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 {fmt_time()}\n📍 {self.data['group_title']}\n"
            f"🎤 MC & Penghulu: *{MC_NAME}*\n\n"
            "🎵 *A Thousand Years — Christina Perri*\n"
        )
        msg = await self.send(base)
        if not msg: return
        for s in ["🕯️ Lilin altar dinyalakan...", "🌹 Kelopak mawar ditaburkan...", "🎻 Musik mulai mengalun...", "💐 Dekorasi tertata indah...", "✅ *Venue siap! Acara dimulai!*"]:
            await asyncio.sleep(3)
            await self.edit(msg.message_id, base + "\n" + s)
        await asyncio.sleep(4)

    async def phase_persiapan(self):
        await self.send(
            "🪞 *PERSIAPAN PENGANTIN* 🪞\n\n"
            f"💍 *{self.data['requester_name']}* sedang bersiap bersama sahabat-sahabatnya\n"
            "   _Terlihat gugup namun bahagia..._\n\n"
            f"💍 *{self.data['partner_name']}* sedang bersiap dengan busana pilihan mereka\n"
            "   _Terlihat begitu bersinar, penuh kebahagiaan..._\n\n"
            "💍 Cincin pernikahan sudah siap di atas bantal beludru merah\n"
            "📸 Fotografer mempersiapkan kamera\n"
            "🎥 Videografer memposisikan diri di sudut terbaik"
        )
        await asyncio.sleep(8)

    async def phase_kedatangan_tamu(self):
        msg = await self.send("👥 *TAMU UNDANGAN BERDATANGAN* 👥\n\n🚗 Tamu mulai berdatangan...")
        if not msg: return
        base = "👥 *TAMU UNDANGAN BERDATANGAN* 👥\n\n"
        for t in ["👨‍👩‍👧 Keluarga pengantin 1 tiba...", "👨‍👩‍👦 Keluarga pengantin 2 tiba...", "🎩 Sahabat-sahabat dekat tiba...", "👴👵 Para sesepuh tiba...", "✅ *Semua tamu telah hadir!*"]:
            await asyncio.sleep(3)
            await self.edit(msg.message_id, base + t)
        await asyncio.sleep(4)

    async def phase_prosesi_masuk(self):
        await self.send(
            "🎵 *PROSESI PENGANTIN MASUK* 🎵\n\n"
            "🎼 _A Thousand Years — Christina Perri_\n\n"
            f"🎙️ *{MC_NAME}:* \"Hadirin sekalian, mohon berdiri!\"\n\n"
            f"💍 *{self.data['requester_name'].upper()}* melangkah masuk\n"
            "   Didampingi kedua orang tuanya\n"
            "   Berdiri tegap di depan altar\n\n"
            "⏳ *Semua mata tertuju ke pintu masuk...*\n\n"
            f"💍 *{self.data['partner_name'].upper()}* melangkah masuk!\n"
            "   Busana pilihan berkilauan indah\n"
            "   Memegang buket bunga segar\n\n"
            "😭 *Air mata kebahagiaan mengalir...*\n"
            "👏 *Tepuk tangan meriah memenuhi ruangan!*",
            photo=PHOTO_BUNGA
        )
        await asyncio.sleep(12)

    async def phase_sambutan_mc(self):
        await self.send(
            f"🎙️ *SAMBUTAN {MC_NAME.upper()}* 🎙️\n\n"
            "\"Yang kami hormati para sesepuh, keluarga besar,\n"
            "dan tamu undangan yang berbahagia...\n\n"
            "Puji syukur atas kehadiran kita semua di momen sakral ini.\n\n"
            "Kita berkumpul untuk menyaksikan bersatunya dua insan\n"
            "yang telah memilih untuk mengarungi kehidupan bersama.\n\n"
            "Semoga pernikahan ini menjadi ikatan suci yang diberkahi\n"
            "dan menjadi fondasi keluarga yang bahagia dan harmonis.\"\n\n"
            "👏 *Para tamu memberikan tepuk tangan hangat...*"
        )
        await asyncio.sleep(10)

    async def phase_doa_pembuka(self):
        await self.send(
            "🕊️ *MOMEN HENING & REFLEKSI* 🕊️\n\n"
            f"🎙️ *{MC_NAME}:* \"Marilah kita hening sejenak...\"\n\n"
            "🤝 *Seluruh hadirin menundukkan kepala...*\n\n"
            "\"Semoga perjalanan cinta ini membawa kebahagiaan,\n"
            "kesetiaan, dan kedamaian bagi keduanya\n"
            "dan semua orang di sekitar mereka.\"\n\n"
            "💕 *Seluruh hadirin menyambut dengan hangat...*"
        )
        await asyncio.sleep(10)

    async def phase_kata_sambutan_ortu(self):
        await self.send(
            "👨‍👩‍👧 *KATA SAMBUTAN ORANG TUA* 👨‍👩‍👧\n\n"
            f"👨 *Orang Tua {self.data['requester_name']}:*\n"
            f"\"Anakku, hari ini kami melepasmu kepada {self.data['partner_name']} dengan penuh keikhlasan.\n"
            "Jaga dan cintai mereka sepenuh hatimu.\"\n"
            "😢 _Suara bergetar menahan haru..._\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👩 *Orang Tua {self.data['partner_name']}:*\n"
            "\"Anakku sayang, kamu adalah cahaya hidup kami.\n"
            f"Pergilah bersama {self.data['requester_name']}, bangun keluarga yang bahagia.\"\n"
            "😭 _Air mata tidak bisa dibendung lagi..._\n\n"
            "👏 *Tepuk tangan haru dari seluruh tamu*"
        )
        await asyncio.sleep(12)

    async def phase_ijab_kabul_interaktif(self):
        """Fase ikrar janji — pengantin harus ketik janji mereka sendiri."""
        await self.send(
            "📜 *PROSESI IKRAR & JANJI* 📜\n\n"
            "🎵 _Musik berhenti. Suasana hening dan khidmat..._\n\n"
            f"🎙️ *{MC_NAME}:*\n"
            "\"Kini tibalah saat yang paling sakral.\n"
            "Mohon kepada seluruh hadirin untuk menjaga kekhusyukan.\"\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            photo=PHOTO_AKAD
        )
        await asyncio.sleep(5)

        # ── Pengantin 1 ketik janji ──
        await self.send(
            f"💍 *{self.data['requester_name'].upper()}, GILIRANMU!*\n\n"
            f"🎙️ *{MC_NAME}:*\n"
            f"\"Saudara {self.data['requester_name']}, ucapkanlah ikrar pernikahanmu\n"
            f"kepada {self.data['partner_name']} dengan sepenuh hati.\"\n\n"
            "📝 *Ketik ikrar/janjimu sekarang!*\n"
            "_(Contoh: Aku berjanji akan mencintaimu selamanya...)_\n\n"
            "⏳ Waktu: 2 menit"
        )
        janji_pria = await self.wait_input("janji_1", timeout=120)
        if janji_pria:
            await self.send(
                f"💍 *{self.data['requester_name']}:*\n"
                f"_{janji_pria}_\n\n"
                f"{random.choice(MC_REACTIONS_JANJI)}"
            )
        else:
            await self.send(
                f"💍 *{self.data['requester_name']}:*\n"
                "\"Aku berjanji akan mencintaimu, menjagamu,\n"
                "dan bersamamu dalam suka maupun duka, selamanya.\"\n\n"
                "_(Tidak ada respon, MC melanjutkan...)_"
            )
        await asyncio.sleep(5)

        # ── Pengantin 2 ketik janji ──
        await self.send(
            f"💍 *{self.data['partner_name'].upper()}, GILIRANMU!*\n\n"
            f"🎙️ *{MC_NAME}:*\n"
            f"\"Saudara {self.data['partner_name']}, ucapkanlah ikrar pernikahanmu\n"
            f"kepada {self.data['requester_name']} dengan sepenuh hati.\"\n\n"
            "📝 *Ketik ikrar/janjimu sekarang!*\n"
            "_(Contoh: Aku berjanji akan setia dan mendukungmu...)_\n\n"
            "⏳ Waktu: 2 menit"
        )
        janji_wanita = await self.wait_input("janji_2", timeout=120)
        if janji_wanita:
            await self.send(
                f"💍 *{self.data['partner_name']}:*\n"
                f"_{janji_wanita}_\n\n"
                f"{random.choice(MC_REACTIONS_JANJI)}"
            )
        else:
            await self.send(
                f"💍 *{self.data['partner_name']}:*\n"
                "\"Aku berjanji akan setia, mendukung, dan mencintaimu\n"
                "dengan sepenuh jiwa ragaku, selamanya.\"\n\n"
                "_(Tidak ada respon, MC melanjutkan...)_"
            )
        await asyncio.sleep(5)

    async def phase_tunggu_saksi(self):
        keyboard = [[InlineKeyboardButton("✅ SAH! Saya Menjadi Saksi", callback_data=f"saksi_{self.data['wedding_key']}")]]
        msg = await self.send(self._saksi_teks(), reply_markup=InlineKeyboardMarkup(keyboard))
        if msg: self.witness_msg_id = msg.message_id
        start = time.time()
        while time.time() - start < 120:
            if len(self.saksi_ids) >= self.need_saksi: break
            await asyncio.sleep(2)
        if len(self.saksi_ids) < self.need_saksi:
            if self.witness_msg_id:
                await self.edit(self.witness_msg_id,
                    f"⏰ *WAKTU SAKSI HABIS!*\n\nHanya {len(self.saksi_ids)} dari {self.need_saksi} saksi.\n\n"
                    "💔 Pernikahan dibatalkan. Coba lagi nanti.")
            self.active = False

    def _saksi_teks(self):
        t = (
            "⚖️ *PERNYATAAN SAKSI* ⚖️\n\n"
            f"🎙️ *{MC_NAME}:*\n"
            f"\"Pernikahan ini memerlukan *{self.need_saksi} saksi*!\n"
            "Tekan tombol di bawah untuk menjadi saksi!\"\n\n⏰ Waktu: 2 menit\n\n"
        )
        for i in range(self.need_saksi):
            t += f"👤 Saksi {i+1}: ✅ *{self.saksi_names[i]}* — SAH!\n" if i < len(self.saksi_names) else f"👤 Saksi {i+1}: _menunggu..._\n"
        t += f"\n⏳ *{len(self.saksi_ids)}/{self.need_saksi} saksi*"
        return t

    async def add_saksi(self, user_id, name):
        if user_id in self.saksi_ids or user_id in (self.data['requester_id'], self.data['partner_id']): return False
        self.saksi_ids.append(user_id)
        self.saksi_names.append(name)
        keyboard = [[InlineKeyboardButton("✅ SAH! Saya Menjadi Saksi", callback_data=f"saksi_{self.data['wedding_key']}")]]
        if self.witness_msg_id: await self.edit(self.witness_msg_id, self._saksi_teks(), reply_markup=InlineKeyboardMarkup(keyboard))
        return True

    async def phase_pengumuman_sah(self):
        await self.send(
            "🎺🎺🎺 *PENGUMUMAN RESMI* 🎺🎺🎺\n\n"
            f"🎙️ *{MC_NAME}:*\n\n"
            "*DENGAN INI SAYA NYATAKAN BAHWA:*\n\n"
            f"💍 *{self.data['requester_name'].upper()}*\n"
            "            dan\n"
            f"💍 *{self.data['partner_name'].upper()}*\n\n"
            "✨ *TELAH RESMI MENJADI* ✨\n"
            "💒 *PASANGAN RESMI!* 💒\n\n"
            f"📅 Berlaku sejak: *{fmt_time()}*\n\n"
            "🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊\n"
            "👏 *TEPUK TANGAN MERIAH!* 👏\n"
            "🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊"
        )
        await asyncio.sleep(8)

    async def phase_tukar_cincin_interaktif(self):
        """Pengantin harus pencet tombol konfirmasi saat pasang cincin."""
        await self.send(
            "💍 *PROSESI PERTUKARAN CINCIN* 💍\n\n"
            f"🎙️ *{MC_NAME}:* \"Kini saatnya pertukaran cincin!\"\n\n"
            "🎵 _Can't Help Falling in Love — Elvis_\n\n"
            f"💍 Cincin dikeluarkan dari bantal beludru merah...\n"
            f"✨ Berkilauan di bawah sorotan lampu altar..."
        )
        await asyncio.sleep(5)

        # Pengantin 1 pasang cincin
        kb = [[InlineKeyboardButton("💍 Saya pasangkan cincin!", callback_data=f"confirm_{self.data['wedding_key']}_{self.data['requester_id']}")]]
        await self.send(
            f"💍 *{self.data['requester_name']}*, saatnya kamu memasangkan cincin!\n\n"
            f"🎙️ *{MC_NAME}:* \"Ambil cincin itu, dan pasangkan ke jari manis {self.data['partner_name']}...\"\n\n"
            "👇 *Tekan tombol saat kamu sudah siap!*\n⏳ Waktu: 1 menit",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        confirmed = await self.wait_confirm(self.data['requester_id'], timeout=60)
        if confirmed:
            await self.send(
                f"💍 *{self.data['requester_name']}* memasangkan cincin ke jari manis *{self.data['partner_name']}*...\n\n"
                f"🎙️ *{self.data['requester_name']}:*\n"
                f"\"Dengan cincin ini, aku mengikatmu {self.data['partner_name']}.\n"
                "Terimalah ini sebagai tanda cinta abadieku.\"\n\n"
                "💕 *Tamu terharu menyaksikan...*"
            )
        else:
            await self.send(f"💍 *{self.data['requester_name']}* memasangkan cincin ke jari manis *{self.data['partner_name']}*... _(lanjut otomatis)_")
        await asyncio.sleep(5)

        # Pengantin 2 pasang cincin
        kb2 = [[InlineKeyboardButton("💍 Saya pasangkan cincin!", callback_data=f"confirm_{self.data['wedding_key']}_{self.data['partner_id']}")]]
        await self.send(
            f"💍 *{self.data['partner_name']}*, sekarang giliranmu!\n\n"
            f"🎙️ *{MC_NAME}:* \"Ambil cincin itu, dan pasangkan ke jari manis {self.data['requester_name']}...\"\n\n"
            "👇 *Tekan tombol saat kamu sudah siap!*\n⏳ Waktu: 1 menit",
            reply_markup=InlineKeyboardMarkup(kb2)
        )
        confirmed2 = await self.wait_confirm(self.data['partner_id'], timeout=60)
        if confirmed2:
            await self.send(
                f"💍 *{self.data['partner_name']}* memasangkan cincin ke jari manis *{self.data['requester_name']}*...\n\n"
                f"🎙️ *{self.data['partner_name']}:*\n"
                f"\"Dengan cincin ini, aku berjanji setia padamu {self.data['requester_name']}.\n"
                "Untuk selamanya.\"\n\n"
                "😍 *Semua tamu berdiri bertepuk tangan!*"
            )
        else:
            await self.send(f"💍 *{self.data['partner_name']}* memasangkan cincin ke jari manis *{self.data['requester_name']}*... _(lanjut otomatis)_")
        await asyncio.sleep(5)

        await self.send("💑 *CINCIN TELAH TERPASANG DI KEDUA JARI!* 💑\n\n🎉🎊💕 *Tepuk tangan meriah!* 💕🎊🎉")
        await asyncio.sleep(5)

    async def phase_ciuman_pertama_interaktif(self):
        """Kedua pengantin harus pencet tombol bersamaan."""
        kb_pria = [[InlineKeyboardButton("💋 Aku siap!", callback_data=f"confirm_{self.data['wedding_key']}_{self.data['requester_id']}")]]
        kb_wanita = [[InlineKeyboardButton("💋 Aku siap!", callback_data=f"confirm_{self.data['wedding_key']}_{self.data['partner_id']}")]]

        await self.send(
            "💋 *CIUMAN PERTAMA PENGANTIN* 💋\n\n"
            f"🎙️ *{MC_NAME}:*\n"
            "\"Dan kini... momen yang paling ditunggu-tunggu!\"\n\n"
            "🎵 _Perfect — Ed Sheeran_\n\n"
            f"👀 *Seluruh tamu menahan nafas...*\n\n"
            f"🎙️ *{MC_NAME}:*\n"
            f"\"*{self.data['requester_name']}* dan *{self.data['partner_name']}*,\ntekan tombol kalian saat kalian siap!\""
        )
        await asyncio.sleep(3)

        await self.send(
            f"💍 *{self.data['requester_name']}* — tekan tombol saat siap!\n⏳ Waktu: 1 menit",
            reply_markup=InlineKeyboardMarkup(kb_pria)
        )
        confirmed_pria = await self.wait_confirm(self.data['requester_id'], timeout=60)

        await self.send(
            f"💍 *{self.data['partner_name']}* — sekarang giliranmu! Tekan tombol saat siap!\n⏳ Waktu: 1 menit",
            reply_markup=InlineKeyboardMarkup(kb_wanita)
        )
        confirmed_wanita = await self.wait_confirm(self.data['partner_id'], timeout=60)

        if confirmed_pria and confirmed_wanita:
            await self.send(
                f"😍💋💕 *CIUMAN PERTAMA SEBAGAI PASANGAN RESMI!* 💕💋😍\n\n"
                "🎉 *SELURUH TAMU BERSORAK GEMBIRA!!!* 🎉\n"
                "👏👏👏 *TEPUK TANGAN PALING MERIAH!* 👏👏👏\n\n"
                "🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉"
            )
        else:
            await self.send(
                "😍💋 *Ciuman pertama pengantin!* 💋😍\n\n"
                "🎉 *SELURUH TAMU BERSORAK!* 🎉"
            )
        await asyncio.sleep(6)

    async def phase_sticker_pengantin(self):
        """Pengantin kirim sticker/foto reaksi mereka."""
        await self.send(
            "🤳 *EKSPRESI PENGANTIN!* 🤳\n\n"
            f"🎙️ *{MC_NAME}:*\n"
            "\"Bagaimana perasaan kalian berdua sekarang?\n"
            "Tunjukkan ekspresi kalian! Kirim sticker atau foto!\"\n\n"
            f"👇 *{self.data['requester_name']} & {self.data['partner_name']}*\n"
            "Kirim sticker atau foto reaksi kalian!\n"
            "⏳ Waktu: 1 menit masing-masing"
        )
        await asyncio.sleep(3)

        # Tunggu sticker/foto dari pengantin 1
        await self.send(f"💍 *{self.data['requester_name']}*, kirim sticker atau foto ekspresimu sekarang! ⏳ 1 menit")
        sticker_pria = await self.wait_input("sticker_1", timeout=60)
        if sticker_pria:
            await self.send(f"🎙️ *{MC_NAME}:* {random.choice(MC_REACTIONS_STICKER)}\n_{sticker_pria}_" if isinstance(sticker_pria, str) else f"🎙️ *{MC_NAME}:* {random.choice(MC_REACTIONS_STICKER)}")
        else:
            await self.send(f"😊 *{self.data['requester_name']}* tersenyum bahagia! _(tidak ada respon, lanjut)_")
        await asyncio.sleep(3)

        # Tunggu sticker/foto dari pengantin 2
        await self.send(f"💍 *{self.data['partner_name']}*, sekarang giliranmu! Kirim sticker atau foto ekspresimu! ⏳ 1 menit")
        sticker_wanita = await self.wait_input("sticker_2", timeout=60)
        if sticker_wanita:
            await self.send(f"🎙️ *{MC_NAME}:* {random.choice(MC_REACTIONS_STICKER)}\n_{sticker_wanita}_" if isinstance(sticker_wanita, str) else f"🎙️ *{MC_NAME}:* {random.choice(MC_REACTIONS_STICKER)}")
        else:
            await self.send(f"😍 *{self.data['partner_name']}* bersinar bahagia! _(tidak ada respon, lanjut)_")
        await asyncio.sleep(3)

    async def phase_doa_penutup(self):
        await self.send(
            "🕊️ *PENUTUP UPACARA* 🕊️\n\n"
            f"🎙️ *{MC_NAME}:* \"Marilah kita hening sejenak untuk menutup upacara ini...\"\n\n"
            "\"Semoga cinta yang telah disaksikan hari ini\n"
            f"senantiasa tumbuh dan menjadi berkah bagi\n"
            f"*{self.data['requester_name']}* dan *{self.data['partner_name']}*,\n"
            "keluarga, dan semua yang menyayangi mereka.\"\n\n"
            "💕 *Seluruh hadirin menyambut dengan hangat...*"
        )
        await asyncio.sleep(8)

    async def phase_foto_resmi(self):
        await self.send(
            "📸 *SESI FOTO RESMI* 📸\n\n"
            "📷 Foto resmi kedua mempelai...\n"
            "📷 Foto bersama kedua keluarga besar...\n"
            "📷 Foto bersama para saksi...\n"
            "📷 Foto bersama seluruh tamu...\n\n"
            "🌸 *Momen indah ini akan dikenang selamanya* 🌸"
        )
        await asyncio.sleep(8)

    async def phase_lempar_bunga(self):
        await self.send(
            "💐 *PROSESI LEMPAR BUKET BUNGA* 💐\n\n"
            f"💍 *{self.data['partner_name']}* berbalik membelakangi tamu...\n\n"
            "🎙️ *\"3... 2... 1...\"*\n\n"
            "💐 *BUKET BUNGA DILEMPAR!* 💐\n\n"
            "🙋 *Para tamu berebut menangkap bunga...*\n\n"
            "🎉 *Beruntunglah yang menangkapnya — calon pengantin berikutnya!* 🎉"
        )
        await asyncio.sleep(8)

    async def phase_ucapan_selamat(self):
        await self.send(
            "🥂 *UCAPAN SELAMAT* 🥂\n\n"
            "💬 *Antrean panjang tamu yang ingin bersalaman...*\n\n"
            "👴 *Sesepuh:* \"Selamat ya nak, semoga langgeng!\"\n"
            f"👩 *Sahabat:* \"Finally nikah juga! Selamat bestie! 😭\"\n"
            f"👦 *Teman:* \"Bro, akhirnya! Gas punya anak! 😂\"\n"
            "👶 *Anak kecil:* \"Tante cantik! Om ganteng!\"\n\n"
            f"💑 *{self.data['requester_name']} & {self.data['partner_name']}*\nmenyambut semua tamu dengan senyum hangat 💕"
        )
        await asyncio.sleep(10)

    async def phase_resepsi(self):
        await self.send(
            "🍽️ *JAMUAN MAKAN RESEPSI* 🍽️\n\n"
            "🍛 Nasi Tumpeng Kuning\n🍗 Ayam Bakar Bumbu Rempah\n"
            "🥩 Rendang Sapi\n🥗 Sayur Lodeh\n🍢 Sate Lilit\n\n"
            "🍰 Es Teler · Klepon · Kue Lapis\n"
            "🥤 Es Cendol · Jus Alpukat\n\n"
            "🍽️ *Selamat menikmati hidangan!* 🍽️"
        )
        await asyncio.sleep(10)

    async def phase_potong_kue_interaktif(self):
        """Kedua pengantin harus pencet tombol potong kue."""
        await self.send(
            "🎂 *PROSESI POTONG KUE PENGANTIN* 🎂\n\n"
            "🎵 _Happy Together_\n\n"
            "🎂 Kue pengantin 5 tingkat dihias bunga segar\n"
            "dipindahkan ke tengah ruangan...\n\n"
            f"🎙️ *{MC_NAME}:* \"Kedua mempelai, silakan maju ke tengah!\""
        )
        await asyncio.sleep(5)

        kb_pria = [[InlineKeyboardButton("🎂 Potong kue!", callback_data=f"confirm_{self.data['wedding_key']}_{self.data['requester_id']}")]]
        kb_wanita = [[InlineKeyboardButton("🎂 Potong kue!", callback_data=f"confirm_{self.data['wedding_key']}_{self.data['partner_id']}")]]

        await self.send(
            f"🎙️ *{MC_NAME}:* \"*{self.data['requester_name']}* dan *{self.data['partner_name']}*,\n"
            "pegang pisau bersama dan tekan tombol kalian!\"\n\n"
            f"💍 *{self.data['requester_name']}* — tekan tombolmu!\n⏳ Waktu: 1 menit",
            reply_markup=InlineKeyboardMarkup(kb_pria)
        )
        await self.wait_confirm(self.data['requester_id'], timeout=60)

        await self.send(
            f"💍 *{self.data['partner_name']}* — sekarang tekan tombolmu!\n⏳ Waktu: 1 menit",
            reply_markup=InlineKeyboardMarkup(kb_wanita)
        )
        await self.wait_confirm(self.data['partner_id'], timeout=60)

        await self.send(
            "🎂✂️ *KUE DIPOTONG BERSAMA!* ✂️🎂\n\n"
            "🎉 *KONFETI BETERBANGAN!!!* 🎉\n\n"
            f"🍰 *{self.data['requester_name']}* menyuapkan kue ke *{self.data['partner_name']}*... 💕\n"
            f"🍰 *{self.data['partner_name']}* membalas menyuapkan kue... 😍\n\n"
            "📸 *Fotografer mengabadikan momen manis ini!* 📸"
        )
        await asyncio.sleep(8)

    async def phase_tarian_pengantin(self):
        await self.send(
            "💃🕺 *TARIAN PERTAMA PENGANTIN* 💃🕺\n\n"
            "🎵 _Perfect — Ed Sheeran_\n\n"
            "💡 Spotlight menyoroti pasangan di tengah lantai...\n\n"
            f"💑 *{self.data['requester_name']} & {self.data['partner_name']}* berdansa perlahan...\n\n"
            "_I found a love, for me..._\n"
            "_Darling just dive right in, follow my lead..._\n\n"
            "🥺 *Para tamu menyaksikan dengan mata berkaca-kaca...*\n"
            "👏 *Satu per satu tamu ikut ke lantai dansa!*"
        )
        await asyncio.sleep(12)

    async def phase_pelepasan(self):
        await self.send(
            "🚗 *PROSESI PELEPASAN PENGANTIN* 🚗\n\n"
            "🌸 *Tamu berbaris di sepanjang jalan keluar...*\n"
            "🌸 *Masing-masing memegang kelopak bunga*\n\n"
            f"💑 *{self.data['requester_name']} & {self.data['partner_name']}*\n"
            "berjalan melewati lautan tamu...\n\n"
            "🌸 *Hujan kelopak bunga mengiringi langkah mereka...*\n\n"
            "🚗 *Mobil pengantin dihias indah telah menanti...*\n"
            "🎊 *Kaleng-kaleng berisik diikat di belakang mobil!*\n\n"
            "🚗💨 *Mobil pengantin perlahan melaju...*\n\n"
            "\"SELAMAT JALAN PENGANTIN BARU!!!\"\n"
            "\"SEMOGA BAHAGIA SELALU!!!\"\n\n"
            "🎉🎊💕🌸💐🎊🎉"
        )
        await asyncio.sleep(10)

    async def phase_sertifikat(self):
        saksi_list = "\n".join([f"   Saksi {i+1}: {n} ✅" for i, n in enumerate(self.saksi_names[:3])])
        await self.send(
            "📜 *SERTIFIKAT PERNIKAHAN RESMI* 📜\n"
            "═══════════════════════════════════════\n\n"
            f"💍 *PENGANTIN 1*\n   Nama: {self.data['requester_name']}\n   ID: `{self.data['requester_id']}`\n\n"
            f"💍 *PENGANTIN 2*\n   Nama: {self.data['partner_name']}\n   ID: `{self.data['partner_id']}`\n\n"
            "═══════════════════════════════════════\n"
            f"💒 *DATA PERNIKAHAN*\n   Tanggal: {fmt_time()}\n"
            f"   Tempat: {self.data['group_title']}\n   MC & Officiant: {MC_NAME}\n\n"
            f"👥 *SAKSI-SAKSI:*\n{saksi_list}\n\n"
            "═══════════════════════════════════════\n"
            f"🖋️ Tertanda,\n   *{MC_NAME}*\n   Wedding Organizer & MC\n\n"
            "🌟 *SELAMAT MENEMPUH HIDUP BARU!* 🌟\n"
            "💝 Semoga bahagia selalu! 💝",
            photo=PHOTO_BUKNIKAH
        )

# =============================================
# BACKGROUND RUNNER
# =============================================

async def run_wedding(bot, chat_id, session, wedding_key):
    logging.info(f"Wedding START: {wedding_key}")
    officiant = WeddingOfficiant(bot, chat_id, session)
    active_weddings[wedding_key] = officiant
    try:
        await officiant.run()
        if officiant.active:
            married_couples[f"{session['requester_id']}_{session['partner_id']}"] = {
                "partner1_name": session["requester_name"], "partner1_id": session["requester_id"],
                "partner2_name": session["partner_name"], "partner2_id": session["partner_id"],
                "group_id": session["group_id"], "group_title": session["group_title"],
                "witnesses": officiant.saksi_names, "date": time.time()
            }
            await send_log(bot,
                f"✅ *PERNIKAHAN SELESAI!*\n\n"
                f"💍 {session['requester_name']} & 💍 {session['partner_name']}\n"
                f"👥 Saksi: {', '.join(officiant.saksi_names)}\n📅 {fmt_time()}"
            )
    except Exception as e:
        logging.error(f"Wedding ERROR: {e}", exc_info=True)
        try: await bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")
        except: pass
    finally:
        active_weddings.pop(wedding_key, None)

# =============================================
# COMMANDS
# =============================================

def add_group(chat_id: int):
    """Tambah group ke daftar dan simpan ke file."""
    if chat_id not in known_group_chats:
        known_group_chats.add(chat_id)
        save_groups()

async def on_chat_member_update(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Deteksi saat bot di-add/remove dari group."""
    result = update.my_chat_member
    if not result:
        return
    chat = update.effective_chat
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status

    if chat.type in ("group", "supergroup"):
        if new_status in ("member", "administrator") and old_status in ("left", "kicked"):
            # Bot baru di-add ke group
            add_group(chat.id)
            logging.info(f"Bot di-add ke group: {chat.title} ({chat.id})")
            try:
                await ctx.bot.send_message(
                    chat_id=chat.id,
                    text="💒 *Wedding Bot siap!* Gunakan /nikah untuk memulai pernikahan virtual.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        elif new_status in ("left", "kicked"):
            # Bot di-remove dari group — hapus dari daftar
            known_group_chats.discard(chat.id)
            save_groups()
            logging.info(f"Bot di-remove dari group: {chat.title} ({chat.id})")

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Cek admin
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Kamu tidak punya akses broadcast."); return

    # Harus reply ke pesan
    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text(
            "📢 *Cara pakai /broadcast:*\n\n"
            "Reply ke pesan yang mau di-broadcast, lalu ketik /broadcast\n"
            "Support: teks, foto, video, dokumen, stiker, dll.",
            parse_mode="Markdown"
        ); return

    group_targets = set(known_group_chats)
    group_targets.discard(LOG_GROUP_ID)
    user_targets = set(known_user_chats)
    user_targets.discard(user.id)  # jangan kirim ke diri sendiri

    total_groups = len(group_targets)
    total_users = len(user_targets)
    total_all = total_groups + total_users

    if total_all == 0:
        await update.message.reply_text("⚠️ Belum ada target broadcast."); return

    status_msg = await update.message.reply_text(
        f"📢 *Broadcasting...*\n\n"
        f"👥 {total_users} users + 💬 {total_groups} groups\n"
        f"📨 Total target: {total_all}",
        parse_mode="Markdown"
    )

    sukses_u, gagal_u = 0, 0
    for uid in user_targets:
        try:
            await _forward_preserve(ctx.bot, reply, uid)
            sukses_u += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            gagal_u += 1
            logging.warning(f"Broadcast gagal ke user {uid}: {e}")

    sukses_g, gagal_g = 0, 0
    for gid in group_targets:
        try:
            await _forward_preserve(ctx.bot, reply, gid)
            sukses_g += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            gagal_g += 1
            logging.warning(f"Broadcast gagal ke group {gid}: {e}")

    sukses_total = sukses_u + sukses_g
    gagal_total  = gagal_u + gagal_g

    await status_msg.edit_text(
        f"📢 *Broadcast selesai!*\n\n"
        f"👥 *Users:* ✅ {sukses_u} sukses | ❌ {gagal_u} gagal\n"
        f"💬 *Groups:* ✅ {sukses_g} sukses | ❌ {gagal_g} gagal\n\n"
        f"📊 *Total:* {sukses_total}/{total_all} terkirim",
        parse_mode="Markdown"
    )
    await send_log(ctx.bot,
        f"📢 *BROADCAST DIKIRIM*\n\n"
        f"👤 Oleh: {user.first_name} (`{user.id}`)\n"
        f"👥 Users: ✅{sukses_u}/❌{gagal_u} | 💬 Groups: ✅{sukses_g}/❌{gagal_g}\n"
        f"📊 Total terkirim: {sukses_total}/{total_all}\n📅 {fmt_time()}"
    )


async def _forward_preserve(bot, msg, chat_id: int):
    """Forward pesan dengan preserve formatting & media."""
    # Sticker
    if msg.sticker:
        await bot.send_sticker(chat_id=chat_id, sticker=msg.sticker.file_id)
        return
    # Animasi (GIF)
    if msg.animation:
        await bot.send_animation(chat_id=chat_id, animation=msg.animation.file_id,
            caption=msg.caption, caption_entities=msg.caption_entities)
        return
    # Video note (bulat)
    if msg.video_note:
        await bot.send_video_note(chat_id=chat_id, video_note=msg.video_note.file_id)
        return
    # Voice
    if msg.voice:
        await bot.send_voice(chat_id=chat_id, voice=msg.voice.file_id,
            caption=msg.caption, caption_entities=msg.caption_entities)
        return
    # Photo
    if msg.photo:
        await bot.send_photo(chat_id=chat_id, photo=msg.photo[-1].file_id,
            caption=msg.caption, caption_entities=msg.caption_entities)
        return
    # Video
    if msg.video:
        await bot.send_video(chat_id=chat_id, video=msg.video.file_id,
            caption=msg.caption, caption_entities=msg.caption_entities)
        return
    # Audio
    if msg.audio:
        await bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id,
            caption=msg.caption, caption_entities=msg.caption_entities)
        return
    # Document
    if msg.document:
        await bot.send_document(chat_id=chat_id, document=msg.document.file_id,
            caption=msg.caption, caption_entities=msg.caption_entities)
        return
    # Teks biasa (preserve bold/italic/link dll via entities)
    if msg.text:
        await bot.send_message(chat_id=chat_id, text=msg.text,
            entities=msg.entities)
        return


async def cmd_broadcastforward(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Kamu tidak punya akses broadcast."); return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text(
            "📨 *Cara pakai /broadcastforward:*\n\n"
            "Reply ke pesan yang mau di-forward, lalu ketik /broadcastforward\n"
            "Pesan akan terlihat sebagai 'Diteruskan dari...' oleh penerima.",
            parse_mode="Markdown"
        ); return

    from_chat_id = reply.chat_id
    message_id   = reply.message_id

    group_targets = set(known_group_chats)
    group_targets.discard(LOG_GROUP_ID)
    user_targets = set(known_user_chats)
    user_targets.discard(user.id)

    total_groups = len(group_targets)
    total_users  = len(user_targets)
    total_all    = total_groups + total_users

    if total_all == 0:
        await update.message.reply_text("⚠️ Belum ada target broadcast."); return

    status_msg = await update.message.reply_text(
        f"📨 *Forward broadcasting...*\n\n"
        f"👥 {total_users} users + 💬 {total_groups} groups\n"
        f"📨 Total target: {total_all}\n"
        f"⏳ Jeda lebih besar untuk menghindari gagal...",
        parse_mode="Markdown"
    )

    sukses_u, gagal_u = 0, 0
    for uid in user_targets:
        try:
            await ctx.bot.forward_message(chat_id=uid, from_chat_id=from_chat_id, message_id=message_id)
            sukses_u += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            gagal_u += 1
            logging.warning(f"Broadcastforward gagal ke user {uid}: {e}")

    sukses_g, gagal_g = 0, 0
    for gid in group_targets:
        try:
            await ctx.bot.forward_message(chat_id=gid, from_chat_id=from_chat_id, message_id=message_id)
            sukses_g += 1
            await asyncio.sleep(1.5)
        except Exception as e:
            gagal_g += 1
            logging.warning(f"Broadcastforward gagal ke group {gid}: {e}")

    sukses_total = sukses_u + sukses_g
    gagal_total  = gagal_u + gagal_g

    await status_msg.edit_text(
        f"📨 *Forward broadcast selesai!*\n\n"
        f"👥 *Users:* ✅ {sukses_u} sukses | ❌ {gagal_u} gagal\n"
        f"💬 *Groups:* ✅ {sukses_g} sukses | ❌ {gagal_g} gagal\n\n"
        f"📊 *Total:* {sukses_total}/{total_all} terkirim",
        parse_mode="Markdown"
    )
    await send_log(ctx.bot,
        f"📨 *FORWARD BROADCAST DIKIRIM*\n\n"
        f"👤 Oleh: {user.first_name} (`{user.id}`)\n"
        f"👥 Users: ✅{sukses_u}/❌{gagal_u} | 💬 Groups: ✅{sukses_g}/❌{gagal_g}\n"
        f"📊 Total terkirim: {sukses_total}/{total_all}\n📅 {fmt_time()}"
    )


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    bot_info = await ctx.bot.get_me()
    bot_username = bot_info.username

    await send_log(ctx.bot,
        f"👋 *USER BARU MEMULAI BOT!*\n\n"
        f"👤 Nama: {user.first_name}\n"
        f"🔖 Username: @{user.username or 'tidak ada'}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📅 {fmt_time()}"
    )

    kb = [
        [InlineKeyboardButton("💒 Mulai Nikah", callback_data="mulai_nikah")],
        [InlineKeyboardButton("📋 Panduan", callback_data="panduan"), InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("💍 Daftar Pasangan", callback_data="daftar_pasangan")],
        [InlineKeyboardButton("➕ Tambahkan Bot ke Group", url=f"https://t.me/{bot_username}?startgroup=true")]
    ]
    await update.message.reply_text(
        "💒 *WEDDING ORGANIZER BOT* 💒\n\n"
        f"🎤 MC & Penghulu: *{MC_NAME}*\n\n"
        "✨ Layanan pernikahan virtual interaktif!\n"
        "• Pengantin ketik janji mereka sendiri\n"
        "• Tombol konfirmasi di setiap fase penting\n"
        "• Kirim sticker/foto ekspresi\n"
        "• 3 saksi wajib menyatakan SAH\n"
        "• Sertifikat & foto resmi digital\n\n"
        "👇 Tambahkan bot ke group untuk mulai!",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )


async def cmd_nikah(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user, chat = update.effective_user, update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("❌ Gunakan di dalam *group*!", parse_mode="Markdown"); return
    if chat.type in ("group", "supergroup"):
        add_group(chat.id)
    for w in active_weddings.values():
        if w.chat_id == chat.id:
            await update.message.reply_text("❌ Masih ada pernikahan berlangsung! Tunggu selesai."); return
    wedding_sessions[user.id] = {
        "state": "awaiting_bride", "requester_id": user.id,
        "requester_name": user.first_name, "requester_username": user.username or "",
        "group_id": chat.id, "group_title": chat.title or "Group", "timestamp": time.time()
    }
    kb = [[InlineKeyboardButton("❌ Batalkan", callback_data="cancel_nikah")]]
    await update.message.reply_text(
        "💒 *LAYANAN PERNIKAHAN* 💒\n\n"
        f"💍 *Pengantin 1:* {user.first_name}\n\n"
        "Mention atau ketik username calon pengantin 2.\n"
        "Contoh: `@username`",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )

async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in wedding_sessions:
        del wedding_sessions[uid]
        await update.message.reply_text("❌ *Pernikahan dibatalkan.*", parse_mode="Markdown")
    else:
        await update.message.reply_text("Tidak ada sesi aktif untukmu.")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *PANDUAN WEDDING BOT* 📖\n\n"
        "• /nikah — Mulai proses pernikahan\n"
        "• /cancel — Batalkan sesi\n"
        "• /listcouples — Daftar pasangan\n"
        "• /statuswedding — Status bot\n\n"
        "*Alur interaktif:*\n"
        "1. /nikah → ketik @username calon pengantin 2\n"
        "2. Pengantin 2 tekan tombol *Terima*\n"
        "3. Saat ikrar — kedua pengantin *ketik janji* mereka\n"
        "4. Saat fase cincin & kue — tekan *tombol konfirmasi*\n"
        "5. Kirim *sticker/foto* ekspresi saat diminta\n"
        "6. 3 orang tekan tombol *SAH* sebagai saksi\n"
        "7. Sertifikat diterbitkan 🎉\n\n"
        "_Kalau tidak respon dalam batas waktu, bot lanjut otomatis._",
        parse_mode="Markdown"
    )

async def cmd_listcouples(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    couples = [v for v in married_couples.values() if v.get("group_id") == update.effective_chat.id]
    if not couples:
        await update.message.reply_text("💔 Belum ada pasangan yang menikah di group ini."); return
    teks = f"💒 *DAFTAR PASANGAN MENIKAH*\n\n*Total: {len(couples)}*\n\n"
    for i, c in enumerate(couples, 1):
        teks += f"*{i}.* 💍 {c['partner1_name']} & 💍 {c['partner2_name']}\n   📅 {time.strftime('%d %B %Y', time.localtime(c['date']))}\n\n"
    await update.message.reply_text(teks, parse_mode="Markdown")

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    total_dm     = len(known_user_chats)
    total_groups = len(known_group_chats)

    # Hitung total member dari semua group
    total_group_members = 0
    for gid in list(known_group_chats):
        try:
            count = await ctx.bot.get_chat_member_count(gid)
            total_group_members += max(0, count - 1)  # kurangi bot itu sendiri
        except Exception:
            pass

    total_reach = total_dm + total_group_members

    await update.message.reply_text(
        f"📊 *STATUS WEDDING BOT* 📊\n\n"
        f"👥 Users DM: {total_dm}\n"
        f"💬 Groups: {total_groups} ({total_group_members:,} member)\n"
        f"📡 *Total jangkauan: {total_reach:,} users*\n\n"
        f"💒 Sesi menunggu: {len(wedding_sessions)}\n"
        f"🎭 Pernikahan aktif: {len(active_weddings)}\n"
        f"💒 Total pasangan: {len(married_couples)}\n\n"
        f"🟢 Sistem: AKTIF\n🎤 MC: {MC_NAME}", parse_mode="Markdown"
    )

# =============================================
# MESSAGE HANDLER — tangkap janji & sticker
# =============================================

async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text.strip() if update.message.text else None
    has_sticker = update.message.sticker is not None
    has_photo = update.message.photo is not None

    # Track semua group yang bot ada di dalamnya
    if update.effective_chat.type in ("group", "supergroup"):
        add_group(chat_id)
    elif update.effective_chat.type == "private":
        add_user(chat_id)

    # Cari wedding aktif di group ini
    for wedding in active_weddings.values():
        if wedding.chat_id != chat_id or not wedding.active: continue

        # Tangkap janji pengantin 1
        if wedding.waiting_for == "janji_1" and user.id == wedding.data['requester_id'] and text:
            wedding.receive_input("janji_1", text); return

        # Tangkap janji pengantin 2
        if wedding.waiting_for == "janji_2" and user.id == wedding.data['partner_id'] and text:
            wedding.receive_input("janji_2", text); return

        # Tangkap sticker/foto pengantin 1
        if wedding.waiting_for == "sticker_1" and user.id == wedding.data['requester_id']:
            if has_sticker: wedding.receive_input("sticker_1", "🎭 *[Sticker dikirim]*"); return
            if has_photo: wedding.receive_input("sticker_1", "📸 *[Foto dikirim]*"); return
            if text: wedding.receive_input("sticker_1", text); return

        # Tangkap sticker/foto pengantin 2
        if wedding.waiting_for == "sticker_2" and user.id == wedding.data['partner_id']:
            if has_sticker: wedding.receive_input("sticker_2", "🎭 *[Sticker dikirim]*"); return
            if has_photo: wedding.receive_input("sticker_2", "📸 *[Foto dikirim]*"); return
            if text: wedding.receive_input("sticker_2", text); return

        # Saksi via teks SAH
        if text and text.upper() == "SAH":
            added = await wedding.add_saksi(user.id, user.first_name)
            if not added: await update.message.reply_text("⚠️ Kamu sudah saksi atau kamu adalah pengantin!")
            return

    # Input username calon pengantin 2
    if text and user.id in wedding_sessions:
        data = wedding_sessions[user.id]
        if data["state"] == "awaiting_bride":
            await handle_bride_input(update, ctx, user.id, text, data)

async def handle_bride_input(update, ctx, user_id, text, data):
    bride_username = None
    if update.message.entities:
        for ent in update.message.entities:
            if ent.type == "mention":
                bride_username = text[ent.offset + 1: ent.offset + ent.length]; break
    if not bride_username: bride_username = text.lstrip("@").strip()
    if not bride_username:
        await update.message.reply_text("❌ Username tidak boleh kosong!"); return
    data["partner_username"] = bride_username.lower()
    data["state"] = "awaiting_response"
    kb = [[
        InlineKeyboardButton("✅ Ya, saya terima", callback_data=f"terima_{user_id}"),
        InlineKeyboardButton("❌ Tidak, saya tolak", callback_data=f"tolak_{user_id}")
    ]]
    await update.message.reply_text(
        f"💒 *PENGAJUAN PERNIKAHAN* 💒\n\n"
        f"💍 *Pengantin 1:* {data['requester_name']}\n"
        f"💍 *Calon Pengantin 2:* @{bride_username}\n\n"
        f"@{bride_username}, apakah kamu menerima lamaran ini?\n\n"
        f"_Hanya @{bride_username} yang bisa menjawab._",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )
    wedding_sessions[user_id] = data

# =============================================
# CALLBACK HANDLER
# =============================================

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query, user, data = update.callback_query, update.callback_query.from_user, update.callback_query.data
    await query.answer()

    if data == "mulai_nikah":
        await query.message.reply_text("Ketik /nikah untuk memulai! 💒"); return
    if data == "panduan":
        await query.message.reply_text("Ketik /help untuk panduan lengkap! 📖"); return
    if data == "status":
        await query.message.reply_text(f"Sesi: {len(wedding_sessions)} | Aktif: {len(active_weddings)} | Pasangan: {len(married_couples)}"); return
    if data == "daftar_pasangan":
        couples = [v for v in married_couples.values() if v.get("group_id") == query.message.chat_id]
        await query.message.reply_text("💔 Belum ada pasangan." if not couples else "💒 *DAFTAR PASANGAN*\n\n" + "\n".join([f"💍 {c['partner1_name']} & 💍 {c['partner2_name']}" for c in couples]), parse_mode="Markdown"); return
    if data == "cancel_nikah":
        wedding_sessions.pop(user.id, None)
        await query.message.reply_text("❌ Pernikahan dibatalkan."); return

    # Terima / Tolak lamaran
    if data.startswith("terima_") or data.startswith("tolak_"):
        action = data.split("_")[0]
        requester_id = int(data.split("_")[1])
        session = wedding_sessions.get(requester_id)
        if not session or session.get("state") != "awaiting_response":
            await query.answer("❌ Sesi sudah tidak aktif.", show_alert=True); return
        bride_username = session.get("partner_username", "").lower()
        if (user.username or "").lower() != bride_username:
            await query.answer(f"⛔ Hanya @{bride_username} yang bisa menjawab!", show_alert=True); return
        if action == "tolak":
            wedding_sessions.pop(requester_id, None)
            await query.edit_message_text(f"💔 *{user.first_name}* menolak lamaran dari *{session['requester_name']}*.\n\n😢 Semoga tetap berteman baik!", parse_mode="Markdown"); return
        chat_id = query.message.chat_id
        for w in active_weddings.values():
            if w.chat_id == chat_id:
                await query.answer("❌ Masih ada pernikahan aktif di group ini!", show_alert=True); return
        session["partner_id"] = user.id
        session["partner_name"] = user.first_name
        wedding_sessions.pop(requester_id, None)
        wedding_key = f"{chat_id}_{int(time.time())}"
        session["wedding_key"] = wedding_key
        await query.edit_message_text(
            f"💒 *{user.first_name} menerima lamaran {session['requester_name']}!* 💒\n\n"
            "🎬 Pernikahan interaktif segera dimulai!\n"
            "⏳ Pengantin & tamu siap berpartisipasi ya! 🎊",
            parse_mode="Markdown"
        )
        await send_log(ctx.bot,
            f"💒 *PERNIKAHAN DIMULAI!*\n\n"
            f"💍 {session['requester_name']} (ID: `{session['requester_id']}`)\n"
            f"💍 {session['partner_name']} (ID: `{session['partner_id']}`)\n"
            f"📍 {session['group_title']} (`{session['group_id']}`)\n📅 {fmt_time()}"
        )
        asyncio.get_running_loop().create_task(run_wedding(ctx.bot, chat_id, session, wedding_key))
        return

    # Tombol konfirmasi pengantin (cincin, ciuman, kue)
    if data.startswith("confirm_"):
        parts = data.split("_")
        # format: confirm_{wedding_key}_{user_id}
        # wedding_key bisa mengandung _ jadi ambil dari belakang
        target_user_id = int(parts[-1])
        wedding_key = "_".join(parts[1:-1])
        if user.id != target_user_id:
            await query.answer("⛔ Tombol ini bukan untukmu!", show_alert=True); return
        if wedding_key in active_weddings:
            active_weddings[wedding_key].receive_confirm(user.id)
            await query.answer("✅ Siap!", show_alert=False)
        return

    # Tombol SAH saksi
    if data.startswith("saksi_"):
        wkey = data[len("saksi_"):]
        if wkey not in active_weddings:
            await query.answer("⚠️ Pernikahan sudah selesai.", show_alert=True); return
        added = await active_weddings[wkey].add_saksi(user.id, user.first_name)
        await query.answer("⚠️ Kamu sudah saksi atau kamu pengantin!" if not added else f"✅ {user.first_name} dicatat sebagai saksi!", show_alert=not added)

# =============================================
# MAIN
# =============================================

def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("broadcastforward", cmd_broadcastforward))
    app.add_handler(ChatMemberHandler(on_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("nikah", cmd_nikah))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("listcouples", cmd_listcouples))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, msg_handler))
    print(f"🚀 Wedding Bot jalan! MC: {MC_NAME}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
