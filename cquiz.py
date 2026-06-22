import logging
import random
import asyncio
import html
import pytz
import httpx
import operator

from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PollAnswerHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter

# ==================== CONFIG ====================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN          = "8632410832:AAG2sdo4ZEYs-cquyRpSe89YEjS9fxVY3Q4"
CARPETS_TOKEN  = "7827651899:AAEfAKBZob6zQxU7nLqa66hs4ALwo8637R0"  # Bot Carpets, untuk kirim notif
OWNER_ID     = 8513979925
OWNER_ID2    = 6234545645
OWNER_IDS    = {OWNER_ID, OWNER_ID2}

SUPABASE_URL = "https://rtqxkdbslgtoyvouepqa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0cXhrZGJzbGd0b3l2b3VlcHFhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDk5ODkwNCwiZXhwIjoyMDk2NTc0OTA0fQ.dJGXkqiQyEsu2_eYLvIZnQ3SWQBY6u0zpRr0YmaY41E"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

GAME_GROUP_ID    = -1003803754738
COIN_PER_CORRECT = 20
IDOL_COIN        = 200  # hadiah tebak idol/lagu/emoji

WIB = pytz.timezone('Asia/Jakarta')

# ==================== FIFA CONFIG ====================
FIFA_GROUP_ID       = -1003803754738  # TODO: ganti dengan group FIFA khusus
FIFA_API_KEY        = "ed93c6bc75c04528962a591b5030a20d"
FIFA_API_BASE       = "https://api.football-data.org/v4"
FIFA_COIN_REWARD    = 200
FIFA_MAX_PREDICTORS = 100
FIFA_EVENT_ACTIVE   = False  # toggle via /fifaon /fifaoff
FIFA_BOT_USERNAME   = "CarpetsQuizBot"  # username bot tanpa @

# FIFA in-memory state
_fifa_announce_msgs: dict = {}  # {match_id: msg_id} buat edit counter
_fifa_live_scores: dict   = {}  # {match_id: {"home_g":0,"away_g":0}} buat deteksi gol
_fifa_result_done: set    = set()  # match_id yang sudah di-announce hasilnya
# _fifa_scheduled dipindah ke Supabase tabel fifa_scheduled

# ==================== STATE ====================
_active_session: dict = {}
_math_session: dict   = {}
_quiz_session: dict   = {}

# Koin tracking — tidak ada DB call saat game berlangsung.
# Semua koin dikumpulkan di sini, baru di-flush ke DB saat /sendnotif.
# Format: { user_id: {"name": str, "coins": int} }
_notif_scores: dict = {}

# ==================== HTTP ====================
_http: httpx.AsyncClient = None

async def get_client():
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(20.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
    return _http

async def sb(method: str, table: str, params: dict = None, data: dict = None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    client = await get_client()
    try:
        if method == "GET":
            r = await client.get(url, params=params)
        elif method == "POST":
            r = await client.post(url, json=data)
        elif method == "PATCH":
            r = await client.patch(url, params=params, json=data)
        elif method == "DELETE":
            r = await client.delete(url, params=params)
        else:
            return None
        if r.status_code in (200, 201, 204):
            return r.json() if r.content and r.status_code != 204 else []
        logger.error(f"SB {method} {table}: {r.status_code} {r.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"HTTP {table}: {e}")
        return None

async def sb_upsert(table: str, data: dict):
    """Upsert ke Supabase (insert or update on conflict)"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    client = await get_client()
    headers = {**client.headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
    try:
        r = await client.post(url, json=data, headers=headers)
        if r.status_code in (200, 201, 204):
            return True
        logger.error(f"SB upsert {table}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        logger.error(f"SB upsert {table}: {e}")
    return False

# ==================== HELPERS ====================
def now_wib():
    return datetime.now(WIB)

def get_user_display(user) -> str:
    name = html.escape(user.first_name or "")
    return f"@{user.username}" if user.username else name

def track_coins(user_id: int, coins: int, user_display: str = ""):
    """
    Hanya catat koin ke memori — TIDAK ada DB call.
    DB di-update sekaligus saat /sendnotif dipanggil.
    """
    if user_id not in _notif_scores:
        _notif_scores[user_id] = {"name": user_display, "coins": 0}
    _notif_scores[user_id]["coins"] += coins
    if user_display:
        _notif_scores[user_id]["name"] = user_display

async def flush_coins_to_db() -> tuple[int, int]:
    """
    Flush semua koin yang terkumpul di _notif_scores ke Supabase.
    Ambil current coins per user lalu PATCH dengan nilai baru.
    Returns (success_count, fail_count).
    """
    if not _notif_scores:
        return 0, 0

    success = 0
    fail = 0

    # Ambil semua user sekaligus dengan IN filter
    user_ids = list(_notif_scores.keys())
    id_str = "(" + ",".join(str(uid) for uid in user_ids) + ")"

    rows = await sb("GET", "users", {
        "user_id": f"in.{id_str}",
        "select": "user_id,koin",
        "limit": str(len(user_ids) + 10)
    })

    # Buat map user_id -> current coins
    current_coins: dict[int, int] = {}
    if rows:
        for row in rows:
            current_coins[int(row["user_id"])] = row.get("koin", 0) or 0

    # PATCH satu per satu tapi tanpa GET — data sudah ada
    for user_id, data in _notif_scores.items():
        earned = data["coins"]
        if earned <= 0:
            continue
        base = current_coins.get(user_id, 0)
        result = await sb("PATCH", "users",
                          {"user_id": f"eq.{user_id}"},
                          {"koin": base + earned})
        if result is not None:
            success += 1
        else:
            fail += 1
        await asyncio.sleep(0.05)  # throttle tipis biar ga spam

    return success, fail

async def safe_send(context, text: str, **kwargs):
    for _ in range(3):
        try:
            return await context.bot.send_message(
                GAME_GROUP_ID, text,
                parse_mode=ParseMode.HTML,
                **kwargs
            )
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except Exception as e:
            logger.error(f"safe_send error: {e}")
            break

async def safe_send_photo(context, photo, caption: str):
    for _ in range(3):
        try:
            return await context.bot.send_photo(
                GAME_GROUP_ID, photo,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except Exception as e:
            logger.error(f"safe_send_photo error: {e}")
            break

# ==================== MATH GENERATOR ====================
def generate_math_questions(n: int = 20) -> list:
    """Soal matematika sederhana (level SD-SMP bawah): +, -, x saja, angka kecil"""
    ops = [
        ('+', operator.add),
        ('-', operator.sub),
        ('x', operator.mul),
    ]
    questions = []
    for _ in range(n):
        op_sym, op_fn = random.choice(ops)
        if op_sym == 'x':
            a = random.randint(2, 9)
            b = random.randint(2, 9)
        elif op_sym == '-':
            a = random.randint(5, 50)
            b = random.randint(1, a)
        else:
            a = random.randint(5, 50)
            b = random.randint(5, 50)
        answer = op_fn(a, b)

        wrongs = set()
        while len(wrongs) < 3:
            delta = random.choice([-5, -3, -2, -1, 1, 2, 3, 5])
            w = answer + delta
            if w != answer and w > 0:
                wrongs.add(w)

        options = [str(answer)] + [str(w) for w in list(wrongs)[:3]]
        random.shuffle(options)
        correct_idx = options.index(str(answer))

        questions.append({
            "q": f"{a} {op_sym} {b}",
            "a": str(answer),
            "options": options,
            "correct_idx": correct_idx
        })
    return questions

# ==================== QUESTION BANKS ====================
def make_quiz_questions(raw: list) -> list:
    result = []
    for item in raw:
        options = item["opts"][:]
        random.shuffle(options)
        correct_idx = options.index(item["a"])
        result.append({"q": item["q"], "a": item["a"], "options": options, "correct_idx": correct_idx})
    return result

# MATEMATIKA — level SMP mudah
MATEMATIKA_BANK = [
    {"q": "Berapa hasil dari 12 + 15?", "a": "27", "opts": ["27", "25", "29", "26"]},
    {"q": "Berapa hasil dari 30 - 14?", "a": "16", "opts": ["16", "14", "18", "17"]},
    {"q": "Berapa hasil dari 7 x 8?", "a": "56", "opts": ["56", "54", "58", "48"]},
    {"q": "Berapa hasil dari 48 ÷ 6?", "a": "8", "opts": ["8", "7", "9", "6"]},
    {"q": "Berapa nilai dari 5²?", "a": "25", "opts": ["25", "10", "20", "15"]},
    {"q": "Berapa nilai dari √49?", "a": "7", "opts": ["7", "6", "8", "9"]},
    {"q": "Berapa hasil dari 9 x 6?", "a": "54", "opts": ["54", "56", "52", "63"]},
    {"q": "Berapa hasil dari 100 ÷ 4?", "a": "25", "opts": ["25", "20", "30", "24"]},
    {"q": "Berapa hasil dari 13 + 28?", "a": "41", "opts": ["41", "39", "43", "40"]},
    {"q": "Berapa hasil dari 50 - 23?", "a": "27", "opts": ["27", "25", "29", "28"]},
    {"q": "Berapa nilai dari 4³?", "a": "64", "opts": ["64", "48", "16", "12"]},
    {"q": "Berapa hasil dari 6 x 7?", "a": "42", "opts": ["42", "40", "44", "36"]},
    {"q": "Berapa hasil dari 72 ÷ 8?", "a": "9", "opts": ["9", "8", "10", "7"]},
    {"q": "Berapa nilai dari √81?", "a": "9", "opts": ["9", "8", "7", "10"]},
    {"q": "Berapa hasil dari 15 x 4?", "a": "60", "opts": ["60", "55", "65", "54"]},
    {"q": "Berapa hasil dari 17 + 16?", "a": "33", "opts": ["33", "31", "35", "34"]},
    {"q": "Berapa hasil dari 45 - 18?", "a": "27", "opts": ["27", "25", "29", "26"]},
    {"q": "Berapa hasil dari 3 x 12?", "a": "36", "opts": ["36", "33", "39", "34"]},
    {"q": "Berapa hasil dari 60 ÷ 5?", "a": "12", "opts": ["12", "10", "15", "11"]},
    {"q": "Berapa nilai dari 2⁵?", "a": "32", "opts": ["32", "16", "64", "10"]},
]

# IPA — mudah, level SMP bawah
IPA_BANK = [
    {"q": "Hewan yang berkembang biak dengan bertelur disebut?", "a": "Ovipar", "opts": ["Ovipar", "Vivipar", "Ovovivipar", "Partenogenesis"]},
    {"q": "Bagian tumbuhan yang berfungsi menyerap air adalah?", "a": "Akar", "opts": ["Akar", "Batang", "Daun", "Bunga"]},
    {"q": "Proses tumbuhan membuat makanan sendiri disebut?", "a": "Fotosintesis", "opts": ["Fotosintesis", "Respirasi", "Transpirasi", "Fermentasi"]},
    {"q": "Hewan pemakan daging disebut?", "a": "Karnivora", "opts": ["Karnivora", "Herbivora", "Omnivora", "Insektivora"]},
    {"q": "Hewan pemakan tumbuhan disebut?", "a": "Herbivora", "opts": ["Herbivora", "Karnivora", "Omnivora", "Detritivora"]},
    {"q": "Organ pernapasan pada ikan adalah?", "a": "Insang", "opts": ["Insang", "Paru-paru", "Kulit", "Trakea"]},
    {"q": "Organ pencernaan yang menghasilkan enzim amilase adalah?", "a": "Mulut", "opts": ["Mulut", "Lambung", "Usus halus", "Hati"]},
    {"q": "Gaya yang menarik benda ke bawah disebut?", "a": "Gravitasi", "opts": ["Gravitasi", "Gaya magnet", "Gaya gesek", "Gaya pegas"]},
    {"q": "Benda yang dapat ditarik magnet disebut?", "a": "Feromagnetik", "opts": ["Feromagnetik", "Diamagnetik", "Paramagnetik", "Non-magnetik"]},
    {"q": "Air mendidih pada suhu berapa derajat Celsius?", "a": "100°C", "opts": ["100°C", "90°C", "80°C", "110°C"]},
    {"q": "Satuan energi dalam SI adalah?", "a": "Joule", "opts": ["Joule", "Watt", "Newton", "Pascal"]},
    {"q": "Planet yang paling dekat dengan Matahari adalah?", "a": "Merkurius", "opts": ["Merkurius", "Venus", "Bumi", "Mars"]},
    {"q": "Lapisan atmosfer paling bawah tempat kita hidup adalah?", "a": "Troposfer", "opts": ["Troposfer", "Stratosfer", "Mesosfer", "Termosfer"]},
    {"q": "Gas yang dihasilkan tumbuhan saat fotosintesis adalah?", "a": "Oksigen", "opts": ["Oksigen", "Karbon dioksida", "Nitrogen", "Hidrogen"]},
    {"q": "Makhluk hidup yang paling kecil adalah?", "a": "Bakteri", "opts": ["Bakteri", "Virus", "Jamur", "Protozoa"]},
    {"q": "Tulang yang melindungi otak adalah?", "a": "Tengkorak", "opts": ["Tengkorak", "Tulang rusuk", "Tulang belakang", "Tulang dada"]},
    {"q": "Bunyi yang frekuensinya di atas 20.000 Hz disebut?", "a": "Ultrasonik", "opts": ["Ultrasonik", "Infrasonik", "Audiosonik", "Megasonik"]},
    {"q": "Benda padat yang berubah menjadi cair disebut?", "a": "Mencair", "opts": ["Mencair", "Membeku", "Menguap", "Mengembun"]},
    {"q": "Contoh hewan melata (reptil) adalah?", "a": "Buaya", "opts": ["Buaya", "Katak", "Salamander", "Axolotl"]},
    {"q": "Hewan yang dapat terbang dan berdarah panas adalah?", "a": "Burung", "opts": ["Burung", "Kelelawar", "Kupu-kupu", "Capung"]},
]

# IPS — Indonesia, mudah
IPS_BANK = [
    {"q": "Ibu kota negara Indonesia adalah?", "a": "Jakarta", "opts": ["Jakarta", "Surabaya", "Bandung", "Medan"]},
    {"q": "Pulau terbesar di Indonesia adalah?", "a": "Kalimantan", "opts": ["Kalimantan", "Sumatera", "Papua", "Jawa"]},
    {"q": "Mata uang Indonesia adalah?", "a": "Rupiah", "opts": ["Rupiah", "Ringgit", "Baht", "Peso"]},
    {"q": "Suku asli Jawa Barat adalah?", "a": "Sunda", "opts": ["Sunda", "Jawa", "Batak", "Betawi"]},
    {"q": "Bahasa nasional Indonesia adalah?", "a": "Bahasa Indonesia", "opts": ["Bahasa Indonesia", "Bahasa Jawa", "Bahasa Melayu", "Bahasa Betawi"]},
    {"q": "Gunung tertinggi di Jawa adalah?", "a": "Semeru", "opts": ["Semeru", "Merapi", "Rinjani", "Bromo"]},
    {"q": "Danau terbesar di Indonesia adalah?", "a": "Danau Toba", "opts": ["Danau Toba", "Danau Poso", "Danau Maninjau", "Danau Ranau"]},
    {"q": "Tarian tradisional dari Bali adalah?", "a": "Tari Kecak", "opts": ["Tari Kecak", "Tari Saman", "Tari Piring", "Tari Jaipong"]},
    {"q": "Rumah adat dari Jawa Tengah adalah?", "a": "Joglo", "opts": ["Joglo", "Rumah Gadang", "Tongkonan", "Honai"]},
    {"q": "Pahlawan Nasional yang disebut 'Ayah Bangsa' adalah?", "a": "Ir. Soekarno", "opts": ["Ir. Soekarno", "Mohammad Hatta", "Soeharto", "Sultan Agung"]},
    {"q": "Proklamasi kemerdekaan Indonesia dibacakan pada tanggal?", "a": "17 Agustus 1945", "opts": ["17 Agustus 1945", "18 Agustus 1945", "17 Juli 1945", "15 Agustus 1945"]},
    {"q": "Negara tetangga Indonesia di sebelah utara Kalimantan adalah?", "a": "Malaysia", "opts": ["Malaysia", "Filipina", "Brunei Darussalam", "Singapura"]},
    {"q": "Laut yang berada di sebelah utara pulau Jawa adalah?", "a": "Laut Jawa", "opts": ["Laut Jawa", "Laut Banda", "Laut Flores", "Laut Sulawesi"]},
    {"q": "Selat yang memisahkan Jawa dan Sumatera adalah?", "a": "Selat Sunda", "opts": ["Selat Sunda", "Selat Malaka", "Selat Bali", "Selat Lombok"]},
    {"q": "Indonesia terletak di antara dua samudra, yaitu?", "a": "Samudra Hindia dan Samudra Pasifik", "opts": ["Samudra Hindia dan Samudra Pasifik", "Samudra Atlantik dan Samudra Arktik", "Samudra Hindia dan Samudra Atlantik", "Samudra Pasifik dan Samudra Arktik"]},
    {"q": "Indonesia terletak di antara dua benua, yaitu?", "a": "Asia dan Australia", "opts": ["Asia dan Australia", "Asia dan Afrika", "Asia dan Eropa", "Australia dan Amerika"]},
    {"q": "Suku terbesar di Sumatera Utara adalah?", "a": "Batak", "opts": ["Batak", "Melayu", "Minangkabau", "Aceh"]},
    {"q": "Makanan khas dari Padang, Sumatera Barat adalah?", "a": "Rendang", "opts": ["Rendang", "Gudeg", "Pempek", "Sate"]},
    {"q": "Hari Kemerdekaan Indonesia diperingati tiap tanggal?", "a": "17 Agustus", "opts": ["17 Agustus", "17 Juli", "17 Oktober", "17 September"]},
    {"q": "Presiden pertama Indonesia adalah?", "a": "Ir. Soekarno", "opts": ["Ir. Soekarno", "Mohammad Hatta", "Soeharto", "Habibie"]},
]

# SEJARAH — mudah
SEJARAH_BANK = [
    {"q": "Siapa yang menulis teks proklamasi kemerdekaan Indonesia?", "a": "Soekarno-Hatta", "opts": ["Soekarno-Hatta", "Soeharto", "Ahmad Subardjo", "Sayuti Melik"]},
    {"q": "Kerajaan Hindu tertua di Indonesia adalah?", "a": "Kutai", "opts": ["Kutai", "Sriwijaya", "Majapahit", "Mataram"]},
    {"q": "Kerajaan Majapahit berpusat di?", "a": "Jawa Timur", "opts": ["Jawa Timur", "Jawa Tengah", "Jawa Barat", "Sumatera"]},
    {"q": "Siapa Patih Kerajaan Majapahit yang terkenal?", "a": "Gajah Mada", "opts": ["Gajah Mada", "Ken Arok", "Raden Wijaya", "Hayam Wuruk"]},
    {"q": "Kerajaan Islam pertama di Indonesia adalah?", "a": "Samudera Pasai", "opts": ["Samudera Pasai", "Demak", "Aceh", "Ternate"]},
    {"q": "Sumpah Pemuda diikrarkan pada tanggal?", "a": "28 Oktober 1928", "opts": ["28 Oktober 1928", "17 Agustus 1945", "20 Mei 1908", "1 Juni 1945"]},
    {"q": "Siapa penemu telepon?", "a": "Alexander Graham Bell", "opts": ["Alexander Graham Bell", "Thomas Edison", "Nikola Tesla", "Marconi"]},
    {"q": "Perang Dunia II berakhir pada tahun?", "a": "1945", "opts": ["1945", "1944", "1946", "1943"]},
    {"q": "Siapa penemu lampu pijar?", "a": "Thomas Edison", "opts": ["Thomas Edison", "Alexander Graham Bell", "Nikola Tesla", "James Watt"]},
    {"q": "Kerajaan Sriwijaya berpusat di?", "a": "Sumatera Selatan", "opts": ["Sumatera Selatan", "Sumatera Utara", "Kalimantan", "Jawa"]},
    {"q": "Bangsa yang pertama kali menjajah Indonesia adalah?", "a": "Portugis", "opts": ["Portugis", "Belanda", "Spanyol", "Inggris"]},
    {"q": "Bangsa Eropa yang paling lama menjajah Indonesia adalah?", "a": "Belanda", "opts": ["Belanda", "Portugis", "Inggris", "Spanyol"]},
    {"q": "Organisasi pergerakan nasional pertama di Indonesia adalah?", "a": "Budi Utomo", "opts": ["Budi Utomo", "Sarekat Islam", "Indische Partij", "PKI"]},
    {"q": "Budi Utomo didirikan pada tanggal?", "a": "20 Mei 1908", "opts": ["20 Mei 1908", "28 Oktober 1908", "17 Agustus 1908", "1 Juni 1908"]},
    {"q": "Siapa penemu hukum gravitasi?", "a": "Isaac Newton", "opts": ["Isaac Newton", "Albert Einstein", "Galileo Galilei", "Johannes Kepler"]},
    {"q": "Revolusi Industri pertama terjadi di negara?", "a": "Inggris", "opts": ["Inggris", "Perancis", "Amerika", "Jerman"]},
    {"q": "Perang Dunia I berlangsung dari tahun?", "a": "1914-1918", "opts": ["1914-1918", "1939-1945", "1910-1915", "1916-1920"]},
    {"q": "Siapa pencetus teori evolusi?", "a": "Charles Darwin", "opts": ["Charles Darwin", "Gregor Mendel", "Louis Pasteur", "Lamarck"]},
    {"q": "Candi Borobudur dibangun oleh kerajaan?", "a": "Syailendra", "opts": ["Syailendra", "Majapahit", "Sanjaya", "Sriwijaya"]},
    {"q": "Candi Prambanan dibangun untuk memuja dewa?", "a": "Trimurti (Brahma, Wisnu, Siwa)", "opts": ["Trimurti (Brahma, Wisnu, Siwa)", "Buddha", "Wisnu saja", "Siwa saja"]},
]

# ENGLISH — level SMP, tidak terlalu sulit
ENGLISH_BANK = [
    {"q": "What is the past tense of 'go'?", "a": "went", "opts": ["went", "goed", "gone", "going"]},
    {"q": "What is the plural of 'child'?", "a": "children", "opts": ["children", "childs", "childrens", "child"]},
    {"q": "Choose the correct sentence:", "a": "She doesn't like coffee.", "opts": ["She doesn't like coffee.", "She don't like coffee.", "She not like coffee.", "She isn't like coffee."]},
    {"q": "What does 'beautiful' mean in Indonesian?", "a": "Cantik/Indah", "opts": ["Cantik/Indah", "Baik", "Pintar", "Kuat"]},
    {"q": "What is the past tense of 'eat'?", "a": "ate", "opts": ["ate", "eated", "eaten", "eating"]},
    {"q": "Fill in: 'I ___ watching TV right now.'", "a": "am", "opts": ["am", "is", "are", "be"]},
    {"q": "What is the opposite of 'hot'?", "a": "cold", "opts": ["cold", "warm", "cool", "freeze"]},
    {"q": "What is the plural of 'mouse'?", "a": "mice", "opts": ["mice", "mouses", "mouse", "mices"]},
    {"q": "What does 'happy' mean in Indonesian?", "a": "Bahagia/Senang", "opts": ["Bahagia/Senang", "Sedih", "Marah", "Takut"]},
    {"q": "Choose the correct sentence:", "a": "They are playing football.", "opts": ["They are playing football.", "They is playing football.", "They am playing football.", "They playing football."]},
    {"q": "What is the past tense of 'buy'?", "a": "bought", "opts": ["bought", "buyed", "buy", "buys"]},
    {"q": "What does 'dangerous' mean?", "a": "Berbahaya", "opts": ["Berbahaya", "Aman", "Biasa", "Cantik"]},
    {"q": "Fill in: 'He ___ a student.'", "a": "is", "opts": ["is", "am", "are", "be"]},
    {"q": "What is the antonym of 'big'?", "a": "small", "opts": ["small", "tall", "long", "wide"]},
    {"q": "What does 'quickly' mean?", "a": "Dengan cepat", "opts": ["Dengan cepat", "Dengan lambat", "Dengan keras", "Dengan halus"]},
    {"q": "Choose the correct form: 'She ___ to school every day.'", "a": "goes", "opts": ["goes", "go", "going", "gone"]},
    {"q": "What is the plural of 'tooth'?", "a": "teeth", "opts": ["teeth", "tooths", "tooth", "teethes"]},
    {"q": "What does 'library' mean in Indonesian?", "a": "Perpustakaan", "opts": ["Perpustakaan", "Toko buku", "Laboratorium", "Kelas"]},
    {"q": "What is the past tense of 'run'?", "a": "ran", "opts": ["ran", "runned", "run", "runs"]},
    {"q": "Choose the correct question: '_____ your name?'", "a": "What is", "opts": ["What is", "What are", "How is", "Who is"]},
]

# SCIENCE — mudah, SMP
SCIENCE_BANK = [
    {"q": "Planet apa yang dijuluki 'Planet Merah'?", "a": "Mars", "opts": ["Mars", "Venus", "Saturnus", "Jupiter"]},
    {"q": "Berapa planet yang ada di tata surya kita?", "a": "8", "opts": ["8", "9", "7", "10"]},
    {"q": "Apa yang menyebabkan terjadinya siang dan malam?", "a": "Rotasi Bumi", "opts": ["Rotasi Bumi", "Revolusi Bumi", "Rotasi Bulan", "Revolusi Bulan"]},
    {"q": "Apa yang menyebabkan terjadinya pergantian musim?", "a": "Revolusi Bumi", "opts": ["Revolusi Bumi", "Rotasi Bumi", "Revolusi Bulan", "Rotasi Bulan"]},
    {"q": "Planet terbesar di tata surya adalah?", "a": "Jupiter", "opts": ["Jupiter", "Saturnus", "Uranus", "Neptunus"]},
    {"q": "Bintang terdekat dengan Bumi adalah?", "a": "Matahari", "opts": ["Matahari", "Sirius", "Proxima Centauri", "Alpha Centauri"]},
    {"q": "Berapa lama Bumi mengelilingi Matahari?", "a": "365 hari", "opts": ["365 hari", "24 jam", "30 hari", "12 bulan (365 hari)"]},
    {"q": "Cahaya Matahari sampai ke Bumi dalam waktu sekitar?", "a": "8 menit", "opts": ["8 menit", "8 jam", "8 detik", "8 hari"]},
    {"q": "Planet yang dikenal dengan cincinnya adalah?", "a": "Saturnus", "opts": ["Saturnus", "Jupiter", "Uranus", "Neptunus"]},
    {"q": "Gerhana Matahari terjadi karena?", "a": "Bulan menutupi Matahari", "opts": ["Bulan menutupi Matahari", "Bumi menutupi Bulan", "Awan menutupi Matahari", "Matahari tertutup debu"]},
    {"q": "Apa nama proses air laut menguap menjadi awan?", "a": "Evaporasi", "opts": ["Evaporasi", "Kondensasi", "Presipitasi", "Transpirasi"]},
    {"q": "Air hujan terjadi dari proses?", "a": "Kondensasi uap air", "opts": ["Kondensasi uap air", "Penguapan air laut", "Pemanasan bumi", "Pembekuan air"]},
    {"q": "Satuan jarak yang digunakan dalam astronomi adalah?", "a": "Tahun cahaya", "opts": ["Tahun cahaya", "Kilometer", "Meter", "Mil"]},
    {"q": "Lapisan bumi paling luar disebut?", "a": "Kerak bumi", "opts": ["Kerak bumi", "Mantel bumi", "Inti bumi", "Litosfer"]},
    {"q": "Gempa bumi yang berasal dari dasar laut dapat menyebabkan?", "a": "Tsunami", "opts": ["Tsunami", "Banjir biasa", "Angin topan", "Longsor"]},
    {"q": "Energi panas bumi disebut energi?", "a": "Geothermal", "opts": ["Geothermal", "Solar", "Angin", "Hidro"]},
    {"q": "Gas terbanyak di atmosfer Bumi adalah?", "a": "Nitrogen", "opts": ["Nitrogen", "Oksigen", "Karbon dioksida", "Hidrogen"]},
    {"q": "Fenomena bintang jatuh sebenarnya adalah?", "a": "Meteor yang terbakar di atmosfer", "opts": ["Meteor yang terbakar di atmosfer", "Bintang yang jatuh ke bumi", "Asteroid besar", "Planet kecil"]},
    {"q": "Bulan tidak memiliki?", "a": "Atmosfer dan air", "opts": ["Atmosfer dan air", "Gravitasi", "Permukaan padat", "Kawah"]},
    {"q": "Laut dalam di dunia yang paling dalam adalah?", "a": "Palung Mariana", "opts": ["Palung Mariana", "Laut Merah", "Samudra Arktik", "Laut Kaspia"]},
]

# KIMIA — mudah, level SMP
KIMIA_BANK = [
    {"q": "Rumus kimia air adalah?", "a": "H₂O", "opts": ["H₂O", "CO₂", "NaCl", "O₂"]},
    {"q": "Rumus kimia garam dapur adalah?", "a": "NaCl", "opts": ["NaCl", "KCl", "H₂O", "CO₂"]},
    {"q": "Rumus kimia karbon dioksida adalah?", "a": "CO₂", "opts": ["CO₂", "CO", "O₂", "N₂"]},
    {"q": "Unsur dengan lambang Fe adalah?", "a": "Besi", "opts": ["Besi", "Emas", "Tembaga", "Seng"]},
    {"q": "Unsur dengan lambang Au adalah?", "a": "Emas", "opts": ["Emas", "Besi", "Perak", "Tembaga"]},
    {"q": "Unsur dengan lambang O adalah?", "a": "Oksigen", "opts": ["Oksigen", "Osmium", "Selenium", "Nitrogen"]},
    {"q": "Unsur dengan lambang H adalah?", "a": "Hidrogen", "opts": ["Hidrogen", "Helium", "Hafnium", "Holmium"]},
    {"q": "Larutan yang memiliki pH kurang dari 7 bersifat?", "a": "Asam", "opts": ["Asam", "Basa", "Netral", "Alkali"]},
    {"q": "Larutan yang memiliki pH lebih dari 7 bersifat?", "a": "Basa", "opts": ["Basa", "Asam", "Netral", "Garam"]},
    {"q": "Larutan netral memiliki pH?", "a": "7", "opts": ["7", "1", "14", "0"]},
    {"q": "Kertas lakmus yang berubah menjadi merah menandakan?", "a": "Larutan asam", "opts": ["Larutan asam", "Larutan basa", "Larutan netral", "Larutan garam"]},
    {"q": "Unsur dengan lambang C adalah?", "a": "Karbon", "opts": ["Karbon", "Kalsium", "Klorin", "Kobalt"]},
    {"q": "Unsur dengan lambang Na adalah?", "a": "Natrium", "opts": ["Natrium", "Nitrogen", "Nikel", "Neon"]},
    {"q": "Rumus kimia oksigen adalah?", "a": "O₂", "opts": ["O₂", "O", "O₃", "2O"]},
    {"q": "Proses perubahan gula menjadi alkohol oleh ragi disebut?", "a": "Fermentasi", "opts": ["Fermentasi", "Oksidasi", "Reduksi", "Hidrolisis"]},
    {"q": "Campuran gula dengan air adalah contoh dari?", "a": "Larutan", "opts": ["Larutan", "Suspensi", "Koloid", "Campuran heterogen"]},
    {"q": "Unsur dengan lambang Cu adalah?", "a": "Tembaga", "opts": ["Tembaga", "Emas", "Besi", "Perak"]},
    {"q": "Contoh perubahan kimia adalah?", "a": "Besi berkarat", "opts": ["Besi berkarat", "Es mencair", "Gula larut", "Air menguap"]},
    {"q": "Rumus kimia gula (glukosa) adalah?", "a": "C₆H₁₂O₆", "opts": ["C₆H₁₂O₆", "C₁₂H₂₂O₁₁", "CH₄", "C₂H₅OH"]},
    {"q": "Massa atom relatif (Ar) Oksigen adalah?", "a": "16", "opts": ["16", "8", "32", "14"]},
]

# BIOLOGI — mudah, SMP
BIOLOGI_BANK = [
    {"q": "Sel yang memiliki dinding sel adalah sel?", "a": "Tumbuhan", "opts": ["Tumbuhan", "Hewan", "Bakteri", "Jamur"]},
    {"q": "Organel yang menghasilkan energi pada sel disebut?", "a": "Mitokondria", "opts": ["Mitokondria", "Ribosom", "Nukleus", "Kloroplas"]},
    {"q": "Organel yang mengandung klorofil adalah?", "a": "Kloroplas", "opts": ["Kloroplas", "Mitokondria", "Vakuola", "Ribosom"]},
    {"q": "DNA terdapat di dalam?", "a": "Nukleus", "opts": ["Nukleus", "Ribosom", "Mitokondria", "Membran sel"]},
    {"q": "Jaringan yang berfungsi menghantarkan impuls listrik adalah?", "a": "Jaringan saraf", "opts": ["Jaringan saraf", "Jaringan otot", "Jaringan epitel", "Jaringan ikat"]},
    {"q": "Organ yang memompa darah ke seluruh tubuh adalah?", "a": "Jantung", "opts": ["Jantung", "Paru-paru", "Hati", "Ginjal"]},
    {"q": "Organ yang menyaring darah adalah?", "a": "Ginjal", "opts": ["Ginjal", "Hati", "Limpa", "Pankreas"]},
    {"q": "Organ yang menghasilkan empedu adalah?", "a": "Hati", "opts": ["Hati", "Ginjal", "Pankreas", "Lambung"]},
    {"q": "Proses pembelahan sel secara tidak langsung disebut?", "a": "Mitosis", "opts": ["Mitosis", "Meiosis", "Amitosis", "Osmosis"]},
    {"q": "Golongan darah yang disebut donor universal adalah?", "a": "O", "opts": ["O", "A", "B", "AB"]},
    {"q": "Golongan darah yang disebut resipien universal adalah?", "a": "AB", "opts": ["AB", "O", "A", "B"]},
    {"q": "Hewan yang termasuk amfibi adalah?", "a": "Katak", "opts": ["Katak", "Buaya", "Ular", "Kadal"]},
    {"q": "Proses masuknya air dari konsentrasi tinggi ke rendah melalui membran disebut?", "a": "Osmosis", "opts": ["Osmosis", "Difusi", "Imbibisi", "Plasmolisis"]},
    {"q": "Vitamin yang larut dalam air adalah?", "a": "Vitamin C", "opts": ["Vitamin C", "Vitamin A", "Vitamin D", "Vitamin E"]},
    {"q": "Sistem organ yang bertanggung jawab atas pernapasan adalah?", "a": "Sistem pernapasan", "opts": ["Sistem pernapasan", "Sistem pencernaan", "Sistem sirkulasi", "Sistem ekskresi"]},
    {"q": "Bagian sel yang mengatur semua aktivitas sel adalah?", "a": "Nukleus", "opts": ["Nukleus", "Sitoplasma", "Membran sel", "Ribosom"]},
    {"q": "Enzim yang terdapat di ludah berfungsi memecah?", "a": "Karbohidrat/Pati", "opts": ["Karbohidrat/Pati", "Protein", "Lemak", "Serat"]},
    {"q": "Hewan yang berkembang biak dengan melahirkan disebut?", "a": "Vivipar", "opts": ["Vivipar", "Ovipar", "Ovovivipar", "Partenogenesis"]},
    {"q": "Contoh hewan vivipar adalah?", "a": "Sapi", "opts": ["Sapi", "Ayam", "Buaya", "Penyu"]},
    {"q": "Hormon yang mengatur kadar gula darah adalah?", "a": "Insulin", "opts": ["Insulin", "Adrenalin", "Tiroksin", "Kortisol"]},
]

# FISIKA — mudah, SMP
FISIKA_BANK = [
    {"q": "Satuan massa dalam SI adalah?", "a": "Kilogram (kg)", "opts": ["Kilogram (kg)", "Gram (g)", "Ton (t)", "Pon (lb)"]},
    {"q": "Satuan panjang dalam SI adalah?", "a": "Meter (m)", "opts": ["Meter (m)", "Sentimeter (cm)", "Kilometer (km)", "Inci (in)"]},
    {"q": "Satuan waktu dalam SI adalah?", "a": "Sekon (s)", "opts": ["Sekon (s)", "Menit (min)", "Jam (h)", "Hari (d)"]},
    {"q": "Satuan suhu dalam SI adalah?", "a": "Kelvin (K)", "opts": ["Kelvin (K)", "Celsius (°C)", "Fahrenheit (°F)", "Reamur (°R)"]},
    {"q": "Rumus kecepatan adalah?", "a": "v = s/t", "opts": ["v = s/t", "v = t/s", "v = s x t", "v = s + t"]},
    {"q": "Rumus gaya (hukum Newton II) adalah?", "a": "F = m x a", "opts": ["F = m x a", "F = m + a", "F = m/a", "F = a/m"]},
    {"q": "Benda yang diam atau bergerak lurus beraturan jika tidak ada gaya net adalah hukum Newton ke?", "a": "I", "opts": ["I", "II", "III", "IV"]},
    {"q": "Aksi dan reaksi adalah bunyi hukum Newton ke?", "a": "III", "opts": ["III", "I", "II", "IV"]},
    {"q": "Satuan gaya dalam SI adalah?", "a": "Newton (N)", "opts": ["Newton (N)", "Joule (J)", "Pascal (Pa)", "Watt (W)"]},
    {"q": "Rumus tekanan adalah?", "a": "P = F/A", "opts": ["P = F/A", "P = A/F", "P = F x A", "P = F + A"]},
    {"q": "Alat untuk mengukur suhu adalah?", "a": "Termometer", "opts": ["Termometer", "Barometer", "Anemometer", "Higrometer"]},
    {"q": "Alat untuk mengukur tekanan udara adalah?", "a": "Barometer", "opts": ["Barometer", "Termometer", "Manometer", "Anemometer"]},
    {"q": "Energi yang dimiliki benda karena ketinggiannya adalah energi?", "a": "Potensial gravitasi", "opts": ["Potensial gravitasi", "Kinetik", "Kimia", "Listrik"]},
    {"q": "Energi yang dimiliki benda karena geraknya adalah energi?", "a": "Kinetik", "opts": ["Kinetik", "Potensial", "Kimia", "Listrik"]},
    {"q": "Rumus energi kinetik adalah?", "a": "Ek = ½mv²", "opts": ["Ek = ½mv²", "Ek = mgh", "Ek = mv", "Ek = mv²"]},
    {"q": "Pelangi terbentuk karena cahaya matahari mengalami?", "a": "Dispersi", "opts": ["Dispersi", "Refleksi", "Refraksi", "Difraksi"]},
    {"q": "Bunyi tidak dapat merambat melalui?", "a": "Ruang hampa", "opts": ["Ruang hampa", "Udara", "Air", "Benda padat"]},
    {"q": "Alat untuk mengukur arus listrik adalah?", "a": "Amperemeter", "opts": ["Amperemeter", "Voltmeter", "Ohmmeter", "Wattmeter"]},
    {"q": "Alat untuk mengukur tegangan listrik adalah?", "a": "Voltmeter", "opts": ["Voltmeter", "Amperemeter", "Ohmmeter", "Wattmeter"]},
    {"q": "Magnet selalu memiliki berapa kutub?", "a": "2 (utara dan selatan)", "opts": ["2 (utara dan selatan)", "1", "3", "4"]},
]

# BAHASA INDONESIA — mudah, SMP
BAHASA_INDONESIA_BANK = [
    {"q": "Kalimat yang menyatakan perintah disebut kalimat?", "a": "Imperatif", "opts": ["Imperatif", "Deklaratif", "Interogatif", "Eksklamatif"]},
    {"q": "Kalimat yang berisi pertanyaan disebut kalimat?", "a": "Interogatif", "opts": ["Interogatif", "Imperatif", "Deklaratif", "Eksklamatif"]},
    {"q": "Imbuhan 'me-' dalam kata 'membaca' adalah?", "a": "Awalan (prefiks)", "opts": ["Awalan (prefiks)", "Akhiran (sufiks)", "Sisipan (infiks)", "Konfiks"]},
    {"q": "Sinonim dari kata 'besar' adalah?", "a": "Raksasa / Agung", "opts": ["Raksasa / Agung", "Kecil", "Tipis", "Sempit"]},
    {"q": "Antonim dari kata 'panas' adalah?", "a": "Dingin", "opts": ["Dingin", "Hangat", "Sejuk", "Suam-suam"]},
    {"q": "Kata yang memiliki makna kiasan disebut?", "a": "Makna konotatif", "opts": ["Makna konotatif", "Makna denotatif", "Makna leksikal", "Makna gramatikal"]},
    {"q": "Kata 'matahari' dalam kalimat 'Ia adalah matahari keluarga' bermakna?", "a": "Konotatif", "opts": ["Konotatif", "Denotatif", "Leksikal", "Gramatikal"]},
    {"q": "Ejaan yang benar dari kata yang bermakna 'izin/perizinan' adalah?", "a": "Izin", "opts": ["Izin", "Ijin", "Idzin", "Ijein"]},
    {"q": "Penulisan huruf kapital yang benar untuk nama orang adalah?", "a": "Siti Rahayu", "opts": ["Siti Rahayu", "siti rahayu", "SITI RAHAYU", "Siti rahayu"]},
    {"q": "Kata 'berlari' mendapat awalan?", "a": "ber-", "opts": ["ber-", "me-", "pe-", "ter-"]},
    {"q": "Bagian karangan yang berisi inti pembahasan disebut?", "a": "Isi/Batang tubuh", "opts": ["Isi/Batang tubuh", "Pendahuluan", "Penutup", "Kesimpulan"]},
    {"q": "Paragraf yang kalimat utamanya ada di awal disebut?", "a": "Deduktif", "opts": ["Deduktif", "Induktif", "Campuran", "Deskriptif"]},
    {"q": "Paragraf yang kalimat utamanya ada di akhir disebut?", "a": "Induktif", "opts": ["Induktif", "Deduktif", "Campuran", "Naratif"]},
    {"q": "Kalimat 'Adik memakan nasi' merupakan kalimat?", "a": "Aktif", "opts": ["Aktif", "Pasif", "Majemuk", "Tunggal"]},
    {"q": "Kalimat 'Nasi dimakan adik' merupakan kalimat?", "a": "Pasif", "opts": ["Pasif", "Aktif", "Majemuk", "Tunggal"]},
    {"q": "Kata 'indah', 'cantik', 'permai' adalah contoh kata?", "a": "Sinonim", "opts": ["Sinonim", "Antonim", "Homofon", "Homonim"]},
    {"q": "Peribahasa 'Ada gula ada semut' bermakna?", "a": "Dimana ada kesenangan pasti ada yang mendatangi", "opts": ["Dimana ada kesenangan pasti ada yang mendatangi", "Semut suka gula", "Jangan serakah", "Bekerja keras"]},
    {"q": "Kata ganti orang pertama jamak adalah?", "a": "Kami / Kita", "opts": ["Kami / Kita", "Aku / Saya", "Dia / Ia", "Mereka"]},
    {"q": "Kata depan yang menyatakan tempat adalah?", "a": "Di", "opts": ["Di", "Ke", "Dari", "Untuk"]},
    {"q": "Penulisan yang benar untuk menyatakan pukul adalah?", "a": "pukul 08.00", "opts": ["pukul 08.00", "jam 08:00", "pkl 08,00", "Pukul 08.00"]},
]

# IBU KOTA — mudah, negara terkenal
IBU_KOTA_BANK = [
    {"q": "Ibu kota negara Jepang adalah?", "a": "Tokyo", "opts": ["Tokyo", "Osaka", "Kyoto", "Hiroshima"]},
    {"q": "Ibu kota negara Korea Selatan adalah?", "a": "Seoul", "opts": ["Seoul", "Busan", "Incheon", "Daejeon"]},
    {"q": "Ibu kota negara China adalah?", "a": "Beijing", "opts": ["Beijing", "Shanghai", "Guangzhou", "Shenzhen"]},
    {"q": "Ibu kota negara Amerika Serikat adalah?", "a": "Washington D.C.", "opts": ["Washington D.C.", "New York", "Los Angeles", "Chicago"]},
    {"q": "Ibu kota negara Inggris adalah?", "a": "London", "opts": ["London", "Manchester", "Birmingham", "Liverpool"]},
    {"q": "Ibu kota negara Prancis adalah?", "a": "Paris", "opts": ["Paris", "Lyon", "Marseille", "Bordeaux"]},
    {"q": "Ibu kota negara Australia adalah?", "a": "Canberra", "opts": ["Canberra", "Sydney", "Melbourne", "Brisbane"]},
    {"q": "Ibu kota negara Brasil adalah?", "a": "Brasilia", "opts": ["Brasilia", "São Paulo", "Rio de Janeiro", "Salvador"]},
    {"q": "Ibu kota negara India adalah?", "a": "New Delhi", "opts": ["New Delhi", "Mumbai", "Kolkata", "Chennai"]},
    {"q": "Ibu kota negara Rusia adalah?", "a": "Moskow", "opts": ["Moskow", "St. Petersburg", "Novosibirsk", "Yekaterinburg"]},
    {"q": "Ibu kota negara Jerman adalah?", "a": "Berlin", "opts": ["Berlin", "Munich", "Hamburg", "Frankfurt"]},
    {"q": "Ibu kota negara Italia adalah?", "a": "Roma", "opts": ["Roma", "Milan", "Naples", "Turin"]},
    {"q": "Ibu kota negara Spanyol adalah?", "a": "Madrid", "opts": ["Madrid", "Barcelona", "Seville", "Valencia"]},
    {"q": "Ibu kota negara Malaysia adalah?", "a": "Kuala Lumpur", "opts": ["Kuala Lumpur", "Johor Bahru", "Penang", "Putrajaya"]},
    {"q": "Ibu kota negara Thailand adalah?", "a": "Bangkok", "opts": ["Bangkok", "Chiang Mai", "Pattaya", "Phuket"]},
    {"q": "Ibu kota negara Vietnam adalah?", "a": "Hanoi", "opts": ["Hanoi", "Ho Chi Minh City", "Da Nang", "Hue"]},
    {"q": "Ibu kota negara Mesir adalah?", "a": "Kairo", "opts": ["Kairo", "Alexandria", "Luxor", "Aswan"]},
    {"q": "Ibu kota negara Arab Saudi adalah?", "a": "Riyadh", "opts": ["Riyadh", "Jeddah", "Makkah", "Madinah"]},
    {"q": "Ibu kota negara Filipina adalah?", "a": "Manila", "opts": ["Manila", "Cebu", "Davao", "Quezon City"]},
    {"q": "Ibu kota negara Turki adalah?", "a": "Ankara", "opts": ["Ankara", "Istanbul", "Izmir", "Antalya"]},
]

# BENDERA — mudah, negara umum
BENDERA_BANK = [
    {"q": "🇮🇩 Bendera ini milik negara?", "a": "Indonesia", "opts": ["Indonesia", "Monaco", "Polandia", "Singapura"]},
    {"q": "🇯🇵 Bendera ini milik negara?", "a": "Jepang", "opts": ["Jepang", "China", "Korea", "Bangladesh"]},
    {"q": "🇺🇸 Bendera ini milik negara?", "a": "Amerika Serikat", "opts": ["Amerika Serikat", "Inggris", "Perancis", "Australia"]},
    {"q": "🇬🇧 Bendera ini milik negara?", "a": "Inggris", "opts": ["Inggris", "Australia", "Selandia Baru", "Amerika"]},
    {"q": "🇧🇷 Bendera ini milik negara?", "a": "Brasil", "opts": ["Brasil", "Argentina", "Bolivia", "Kolombia"]},
    {"q": "🇨🇳 Bendera ini milik negara?", "a": "China", "opts": ["China", "Vietnam", "Korea", "Jepang"]},
    {"q": "🇰🇷 Bendera ini milik negara?", "a": "Korea Selatan", "opts": ["Korea Selatan", "Korea Utara", "Jepang", "China"]},
    {"q": "🇩🇪 Bendera ini milik negara?", "a": "Jerman", "opts": ["Jerman", "Belgia", "Austria", "Swiss"]},
    {"q": "🇫🇷 Bendera ini milik negara?", "a": "Perancis", "opts": ["Perancis", "Italia", "Belanda", "Belgia"]},
    {"q": "🇮🇹 Bendera ini milik negara?", "a": "Italia", "opts": ["Italia", "Perancis", "Meksiko", "Irlandia"]},
    {"q": "🇦🇺 Bendera ini milik negara?", "a": "Australia", "opts": ["Australia", "Selandia Baru", "Fiji", "Papua Nugini"]},
    {"q": "🇸🇦 Bendera ini milik negara?", "a": "Arab Saudi", "opts": ["Arab Saudi", "Pakistan", "Iran", "Afghanistan"]},
    {"q": "🇲🇾 Bendera ini milik negara?", "a": "Malaysia", "opts": ["Malaysia", "Indonesia", "Filipina", "Brunei"]},
    {"q": "🇸🇬 Bendera ini milik negara?", "a": "Singapura", "opts": ["Singapura", "Korea Selatan", "Taiwan", "Thailand"]},
    {"q": "🇹🇭 Bendera ini milik negara?", "a": "Thailand", "opts": ["Thailand", "Kamboja", "Laos", "Myanmar"]},
    {"q": "🇻🇳 Bendera ini milik negara?", "a": "Vietnam", "opts": ["Vietnam", "China", "Korea Utara", "Albania"]},
    {"q": "🇵🇭 Bendera ini milik negara?", "a": "Filipina", "opts": ["Filipina", "Kuba", "Puerto Riko", "Indonesia"]},
    {"q": "🇳🇱 Bendera ini milik negara?", "a": "Belanda", "opts": ["Belanda", "Perancis", "Rusia", "Kroasia"]},
    {"q": "🇨🇦 Bendera ini milik negara?", "a": "Kanada", "opts": ["Kanada", "Amerika Serikat", "Inggris", "Swiss"]},
    {"q": "🇲🇽 Bendera ini milik negara?", "a": "Meksiko", "opts": ["Meksiko", "Italia", "Nigeria", "Togo"]},
]

# GEOGRAFI DUNIA — mudah
GEOGRAFI_BANK = [
    {"q": "Benua terluas di dunia adalah?", "a": "Asia", "opts": ["Asia", "Afrika", "Amerika", "Eropa"]},
    {"q": "Benua terkecil di dunia adalah?", "a": "Australia", "opts": ["Australia", "Eropa", "Antartika", "Amerika Selatan"]},
    {"q": "Sungai terpanjang di dunia adalah?", "a": "Nil", "opts": ["Nil", "Amazon", "Yangtze", "Mississippi"]},
    {"q": "Gunung tertinggi di dunia adalah?", "a": "Everest", "opts": ["Everest", "K2", "Kilimanjaro", "Elbrus"]},
    {"q": "Samudra terluas di dunia adalah?", "a": "Samudra Pasifik", "opts": ["Samudra Pasifik", "Samudra Atlantik", "Samudra Hindia", "Samudra Arktik"]},
    {"q": "Gurun terluas di dunia adalah?", "a": "Sahara", "opts": ["Sahara", "Gobi", "Arab", "Kalahari"]},
    {"q": "Negara terluas di dunia adalah?", "a": "Rusia", "opts": ["Rusia", "Kanada", "Amerika Serikat", "China"]},
    {"q": "Negara terkecil di dunia adalah?", "a": "Vatikan", "opts": ["Vatikan", "Monako", "San Marino", "Nauru"]},
    {"q": "Negara dengan penduduk terbanyak di dunia adalah?", "a": "India", "opts": ["India", "China", "Amerika Serikat", "Indonesia"]},
    {"q": "Danau terbesar di dunia adalah?", "a": "Laut Kaspia", "opts": ["Laut Kaspia", "Superior", "Victoria", "Baikal"]},
    {"q": "Air terjun tertinggi di dunia adalah?", "a": "Angel Falls (Venezuela)", "opts": ["Angel Falls (Venezuela)", "Niagara", "Victoria", "Iguazu"]},
    {"q": "Bagian Bumi yang disebut 'paru-paru dunia' adalah?", "a": "Hutan Amazon", "opts": ["Hutan Amazon", "Hutan Kalimantan", "Hutan Kongo", "Hutan Siberia"]},
    {"q": "Kutub Utara Bumi terletak di?", "a": "Samudra Arktik", "opts": ["Samudra Arktik", "Benua Antartika", "Greenland", "Kanada"]},
    {"q": "Kutub Selatan Bumi terletak di?", "a": "Antartika", "opts": ["Antartika", "Argentina", "Chili", "Samudra Selatan"]},
    {"q": "Garis khatulistiwa (ekuator) membagi Bumi menjadi?", "a": "Belahan utara dan selatan", "opts": ["Belahan utara dan selatan", "Belahan timur dan barat", "4 bagian", "8 bagian"]},
    {"q": "Garis bujur 0° disebut juga garis?", "a": "Greenwich", "opts": ["Greenwich", "Khatulistiwa", "Ekuator", "Balik"]},
    {"q": "Negara kepulauan terbesar di dunia adalah?", "a": "Indonesia", "opts": ["Indonesia", "Filipina", "Jepang", "Inggris"]},
    {"q": "Benua yang seluruhnya tertutup es adalah?", "a": "Antartika", "opts": ["Antartika", "Arktik", "Greenland", "Islandia"]},
    {"q": "Titik terendah di permukaan Bumi adalah?", "a": "Laut Mati", "opts": ["Laut Mati", "Palung Mariana", "Danau Baikal", "Danau Toba"]},
    {"q": "Jumlah benua di dunia adalah?", "a": "7", "opts": ["7", "5", "6", "8"]},
]

# FILM & HIBURAN — lebih mudah/umum
FILM_HIBURAN_BANK = [
    {"q": "Siapa pemeran Iron Man dalam Marvel Cinematic Universe?", "a": "Robert Downey Jr.", "opts": ["Robert Downey Jr.", "Chris Evans", "Chris Hemsworth", "Mark Ruffalo"]},
    {"q": "Siapa pemeran Captain America dalam MCU?", "a": "Chris Evans", "opts": ["Chris Evans", "Robert Downey Jr.", "Chris Hemsworth", "Jeremy Renner"]},
    {"q": "Siapa pemeran Thor dalam MCU?", "a": "Chris Hemsworth", "opts": ["Chris Hemsworth", "Chris Evans", "Robert Downey Jr.", "Tom Hiddleston"]},
    {"q": "Film animasi tentang ikan yang mencari anaknya yang hilang?", "a": "Finding Nemo", "opts": ["Finding Nemo", "Finding Dory", "Shark Tale", "The Little Mermaid"]},
    {"q": "Film animasi tentang mainan yang hidup adalah?", "a": "Toy Story", "opts": ["Toy Story", "A Bug's Life", "Monsters Inc.", "Cars"]},
    {"q": "Film animasi Pixar tentang monster yang menakuti anak-anak adalah?", "a": "Monsters Inc.", "opts": ["Monsters Inc.", "Toy Story", "Up", "Brave"]},
    {"q": "Siapa penyanyi lagu 'Shape of You'?", "a": "Ed Sheeran", "opts": ["Ed Sheeran", "Justin Bieber", "Bruno Mars", "Harry Styles"]},
    {"q": "Siapa penyanyi lagu 'Blinding Lights'?", "a": "The Weeknd", "opts": ["The Weeknd", "Bruno Mars", "Justin Bieber", "Ed Sheeran"]},
    {"q": "Siapa penyanyi lagu 'Bad Guy'?", "a": "Billie Eilish", "opts": ["Billie Eilish", "Ariana Grande", "Dua Lipa", "Taylor Swift"]},
    {"q": "Film superhero tentang manusia laba-laba adalah?", "a": "Spider-Man", "opts": ["Spider-Man", "Batman", "Ant-Man", "The Flash"]},
    {"q": "Film tentang manusia kelelawar dari Gotham adalah?", "a": "Batman", "opts": ["Batman", "Spider-Man", "Iron Man", "Hawkeye"]},
    {"q": "Siapa penyanyi lagu 'Baby' feat. Ludacris?", "a": "Justin Bieber", "opts": ["Justin Bieber", "Nick Jonas", "Bruno Mars", "Ed Sheeran"]},
    {"q": "Film animasi tentang putri salju yang terlelap karena apel beracun?", "a": "Snow White", "opts": ["Snow White", "Cinderella", "Sleeping Beauty", "Rapunzel"]},
    {"q": "Film animasi tentang gadis yang kehilangan sepatu kacanya?", "a": "Cinderella", "opts": ["Cinderella", "Snow White", "Tangled", "Brave"]},
    {"q": "Siapa penyanyi lagu 'Dynamite' (BTS)?", "a": "BTS", "opts": ["BTS", "EXO", "BLACKPINK", "NCT"]},
    {"q": "Siapa penyanyi lagu 'DDU-DU DDU-DU'?", "a": "BLACKPINK", "opts": ["BLACKPINK", "TWICE", "aespa", "NewJeans"]},
    {"q": "Film tentang penyihir dari Hogwarts adalah?", "a": "Harry Potter", "opts": ["Harry Potter", "Narnia", "Lord of the Rings", "Percy Jackson"]},
    {"q": "Siapa penulis seri novel Harry Potter?", "a": "J.K. Rowling", "opts": ["J.K. Rowling", "J.R.R. Tolkien", "C.S. Lewis", "Roald Dahl"]},
    {"q": "Film animasi 2013 tentang dua putri Arendelle adalah?", "a": "Frozen", "opts": ["Frozen", "Brave", "Tangled", "Moana"]},
    {"q": "Siapa penyanyi lagu 'Anti-Hero'?", "a": "Taylor Swift", "opts": ["Taylor Swift", "Ariana Grande", "Dua Lipa", "Billie Eilish"]},
]

# TEKNOLOGI — lebih mudah/umum
TEKNOLOGI_BANK = [
    {"q": "Siapa pendiri Facebook?", "a": "Mark Zuckerberg", "opts": ["Mark Zuckerberg", "Elon Musk", "Jeff Bezos", "Steve Jobs"]},
    {"q": "Siapa pendiri Apple?", "a": "Steve Jobs", "opts": ["Steve Jobs", "Bill Gates", "Elon Musk", "Mark Zuckerberg"]},
    {"q": "Siapa pendiri Microsoft?", "a": "Bill Gates", "opts": ["Bill Gates", "Steve Jobs", "Elon Musk", "Jeff Bezos"]},
    {"q": "Siapa pendiri Amazon?", "a": "Jeff Bezos", "opts": ["Jeff Bezos", "Elon Musk", "Bill Gates", "Mark Zuckerberg"]},
    {"q": "Apa kepanjangan dari WWW?", "a": "World Wide Web", "opts": ["World Wide Web", "World Wide Wire", "Web Wide World", "Wireless World Web"]},
    {"q": "Apa kepanjangan dari HTTP?", "a": "HyperText Transfer Protocol", "opts": ["HyperText Transfer Protocol", "HyperText Transport Protocol", "High Transfer Text Protocol", "HyperText Transmission Protocol"]},
    {"q": "Apa kepanjangan dari HTML?", "a": "HyperText Markup Language", "opts": ["HyperText Markup Language", "HyperText Marking Language", "High Text Markup Language", "HyperText Making Language"]},
    {"q": "Apa kepanjangan dari CPU?", "a": "Central Processing Unit", "opts": ["Central Processing Unit", "Computer Processing Unit", "Central Program Unit", "Core Processing Unit"]},
    {"q": "Apa kepanjangan dari RAM?", "a": "Random Access Memory", "opts": ["Random Access Memory", "Read Access Memory", "Random Allocated Memory", "Remote Access Memory"]},
    {"q": "Sistem operasi buatan Apple untuk iPhone adalah?", "a": "iOS", "opts": ["iOS", "Android", "Windows", "HarmonyOS"]},
    {"q": "Sistem operasi smartphone paling populer di dunia adalah?", "a": "Android", "opts": ["Android", "iOS", "Windows Phone", "BlackBerry OS"]},
    {"q": "Apa kepanjangan dari AI?", "a": "Artificial Intelligence", "opts": ["Artificial Intelligence", "Automated Intelligence", "Artificial Integration", "Advanced Intelligence"]},
    {"q": "Siapa pendiri Tesla?", "a": "Elon Musk", "opts": ["Elon Musk", "Jeff Bezos", "Bill Gates", "Steve Jobs"]},
    {"q": "Platform video streaming terbesar di dunia adalah?", "a": "YouTube", "opts": ["YouTube", "Netflix", "TikTok", "Twitch"]},
    {"q": "Mesin pencari terbesar di dunia adalah?", "a": "Google", "opts": ["Google", "Bing", "Yahoo", "DuckDuckGo"]},
    {"q": "Aplikasi pesan instan yang paling banyak digunakan di Indonesia adalah?", "a": "WhatsApp", "opts": ["WhatsApp", "Telegram", "Line", "BBM"]},
    {"q": "Apa kepanjangan dari USB?", "a": "Universal Serial Bus", "opts": ["Universal Serial Bus", "United Serial Bus", "Universal System Bus", "Unified Serial Bus"]},
    {"q": "Bahasa pemrograman yang digunakan untuk membuat halaman web adalah?", "a": "HTML", "opts": ["HTML", "Python", "Java", "C++"]},
    {"q": "Siapa yang menciptakan World Wide Web?", "a": "Tim Berners-Lee", "opts": ["Tim Berners-Lee", "Bill Gates", "Steve Jobs", "Linus Torvalds"]},
    {"q": "Apa nama sistem operasi open-source yang populer untuk server?", "a": "Linux", "opts": ["Linux", "Windows", "macOS", "Android"]},
]

SUBJECT_BANKS = {
    "matematika": MATEMATIKA_BANK,
    "ipa":        IPA_BANK,
    "ips":        IPS_BANK,
    "sejarah":    SEJARAH_BANK,
    "english":    ENGLISH_BANK,
    "science":    SCIENCE_BANK,
    "kimia":      KIMIA_BANK,
    "biologi":    BIOLOGI_BANK,
    "fisika":     FISIKA_BANK,
    "bahasa":     BAHASA_INDONESIA_BANK,
    "ibukota":    IBU_KOTA_BANK,
    "bendera":    BENDERA_BANK,
    "geografi":   GEOGRAFI_BANK,
    "film":       FILM_HIBURAN_BANK,
    "teknologi":  TEKNOLOGI_BANK,
}

def get_subject_questions(subject: str, n: int = 20) -> list:
    bank = SUBJECT_BANKS.get(subject, [])
    if not bank:
        return []
    selected = random.sample(bank, min(n, len(bank)))
    return make_quiz_questions(selected)

# ==================== OWNER COMMANDS ====================

async def cmd_start_idol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Reply ke foto dulu!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /startidol <jawaban>")
        return
    if _active_session.get("active"):
        await update.message.reply_text("Masih ada game aktif! Tutup dulu dengan /endgame")
        return

    answer = " ".join(context.args).lower()
    photo = update.message.reply_to_message.photo[-1].file_id

    _active_session.update({
        "active": True,
        "game_type": "tebak_gambar",
        "answer": answer,
        "answered": set(),
    })
    await safe_send_photo(context, photo,
        f"🖼️ <b>Tebak Gambar!</b>\n\n"
        f"Apa ini? Ketik jawabanmu!\n"
        f"Jawaban benar = <b>+{IDOL_COIN} koin</b>\n\n"
        f"<i>Siapa cepat dia yang menang!</i>"
    )
    await update.message.reply_text("Tebak Gambar dimulai!")

async def cmd_start_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    if not context.args:
        await update.message.reply_html("Usage: <code>/startsong jawaban | lirik</code>")
        return
    if _active_session.get("active"):
        await update.message.reply_text("Masih ada game aktif!")
        return

    full = " ".join(context.args)
    if "|" not in full:
        await update.message.reply_html("Format: <code>/startsong jawaban | lirik lagu</code>")
        return

    parts = full.split("|", 1)
    answer = parts[0].strip().lower()
    lyric = parts[1].strip()

    _active_session.update({
        "active": True,
        "game_type": "quiz_song",
        "answer": answer,
        "answered": set(),
    })
    await safe_send(context,
        f"🎵 <b>TEBAK LAGU!</b>\n\n"
        f"<i>\"{html.escape(lyric)}\"</i>\n\n"
        f"Lagu apa ini? Ketik jawabanmu!\n"
        f"Jawaban benar = <b>+{IDOL_COIN} koin</b>\n\n"
        f"<i>Siapa cepat dia yang menang!</i>"
    )
    await update.message.reply_text("Tebak Lagu dimulai!")

async def cmd_start_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    if not context.args:
        await update.message.reply_html("Usage: <code>/startemoji jawaban | emoji</code>")
        return
    if _active_session.get("active"):
        await update.message.reply_text("Masih ada game aktif!")
        return

    full = " ".join(context.args)
    if "|" not in full:
        await update.message.reply_html("Format: <code>/startemoji jawaban | 🎭🎬</code>")
        return

    parts = full.split("|", 1)
    answer = parts[0].strip().lower()
    emoji_str = parts[1].strip()

    _active_session.update({
        "active": True,
        "game_type": "tebak_emoji",
        "answer": answer,
        "answered": set(),
    })
    await safe_send(context,
        f"🤔 <b>TEBAK EMOJI!</b>\n\n"
        f"<b>{html.escape(emoji_str)}</b>\n\n"
        f"Kira-kira apa ini? Ketik jawabanmu!\n"
        f"Jawaban benar = <b>+{IDOL_COIN} koin</b>\n\n"
        f"<i>Siapa cepat dia yang menang!</i>"
    )
    await update.message.reply_text("Tebak Emoji dimulai!")

# ==================== MATH RACE ====================
async def cmd_start_math(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    if _math_session.get("active"):
        await update.message.reply_text("Math Race sedang berlangsung!")
        return

    questions = generate_math_questions(20)
    _math_session.update({
        "active": True,
        "questions": questions,
        "current": 0,
        "scores": {},
        "voted": set(),
        "poll_id": None,
        "poll_msg_id": None,
    })

    await safe_send(context,
        f"🔢 <b>MATH RACE!</b>\n\n"
        f"20 soal matematika akan ditampilkan!\n"
        f"Setiap jawaban benar = <b>+{COIN_PER_CORRECT} koin</b>\n\n"
        f"Bersiap... 🏁"
    )
    await asyncio.sleep(2)
    await send_next_math_question(context)

async def send_next_math_question(context):
    idx = _math_session.get("current", 0)
    questions = _math_session.get("questions", [])
    if idx >= len(questions):
        await end_math_race(context)
        return

    q = questions[idx]
    _math_session["voted"] = set()

    try:
        msg = await context.bot.send_poll(
            GAME_GROUP_ID,
            question=f"Soal {idx+1}/20: {q['q']} = ?",
            options=q["options"],
            type="quiz",
            correct_option_id=q["correct_idx"],
            open_period=15,
            is_anonymous=False,
        )
        _math_session["poll_id"] = msg.poll.id
        _math_session["poll_msg_id"] = msg.message_id
        _math_session["correct_idx"] = q["correct_idx"]
    except Exception as e:
        logger.error(f"Send poll error: {e}")
        return

    await asyncio.sleep(16)
    _math_session["current"] = idx + 1
    await send_next_math_question(context)

async def end_math_race(context):
    _math_session["active"] = False
    scores = _math_session.get("scores", {})
    if not scores:
        await safe_send(context, "🔢 Math Race selesai! Tidak ada yang menjawab 😢")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["count"], reverse=True)
    lines = ""
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_scores[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines += f"{medal} {data['name']} — {data['count']} benar (+{data['count'] * COIN_PER_CORRECT} koin)\n"

    await safe_send(context,
        f"🔢 <b>Math Race Selesai!</b>\n\n"
        f"<b>Hasil:</b>\n{lines}"
    )

# ==================== SUBJECT QUIZ ====================
async def cmd_start_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    if not context.args:
        await update.message.reply_html(
            "Usage: <code>/startquiz [subjek]</code>\n"
            "Subjek: matematika, ipa, ips, sejarah, english, science, kimia, biologi, fisika, bahasa, ibukota, bendera, geografi, film, teknologi"
        )
        return
    if _quiz_session.get("active"):
        await update.message.reply_text("Quiz sedang berlangsung!")
        return

    subject = context.args[0].lower()
    questions = get_subject_questions(subject)
    if not questions:
        await update.message.reply_text(f"Subjek '{subject}' tidak ditemukan!")
        return

    subject_labels = {
        "matematika": "🧮 Matematika",
        "ipa": "🔬 IPA",
        "ips": "🌍 IPS",
        "sejarah": "📜 Sejarah",
        "english": "🇬🇧 English",
        "science": "🧬 Science",
        "kimia": "⚗️ Kimia",
        "biologi": "🧫 Biologi",
        "fisika": "⚡ Fisika",
        "bahasa": "📝 Bahasa Indonesia",
        "ibukota": "🏙️ Tebak Ibu Kota",
        "bendera": "🚩 Tebak Bendera",
        "geografi": "🗺️ Geografi Dunia",
        "film": "🎬 Film & Hiburan",
        "teknologi": "💻 Teknologi",
    }
    label = subject_labels.get(subject, subject.capitalize())

    _quiz_session.update({
        "active": True,
        "subject": subject,
        "label": label,
        "questions": questions,
        "current": 0,
        "scores": {},
        "voted": set(),
        "poll_id": None,
    })

    await safe_send(context,
        f"{label}\n\n"
        f"20 soal akan ditampilkan!\n"
        f"Setiap jawaban benar = <b>+{COIN_PER_CORRECT} koin</b>\n\n"
        f"Bersiap... 🏁"
    )
    await asyncio.sleep(2)
    await send_next_quiz_question(context)

async def send_next_quiz_question(context):
    idx = _quiz_session.get("current", 0)
    questions = _quiz_session.get("questions", [])
    if idx >= len(questions):
        await end_quiz(context)
        return

    q = questions[idx]
    _quiz_session["voted"] = set()

    try:
        msg = await context.bot.send_poll(
            GAME_GROUP_ID,
            question=f"Soal {idx+1}/20: {q['q']}",
            options=q["options"],
            type="quiz",
            correct_option_id=q["correct_idx"],
            open_period=15,
            is_anonymous=False,
        )
        _quiz_session["poll_id"] = msg.poll.id
        _quiz_session["correct_idx"] = q["correct_idx"]
    except Exception as e:
        logger.error(f"Send quiz poll error: {e}")
        return

    await asyncio.sleep(16)
    _quiz_session["current"] = idx + 1
    await send_next_quiz_question(context)

async def end_quiz(context):
    label = _quiz_session.get("label", "Quiz")
    scores = _quiz_session.get("scores", {})
    _quiz_session["active"] = False

    if not scores:
        await safe_send(context, f"{label} selesai! Tidak ada yang menjawab 😢")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["count"], reverse=True)
    lines = ""
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_scores[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines += f"{medal} {data['name']} — {data['count']} benar (+{data['count'] * COIN_PER_CORRECT} koin)\n"

    await safe_send(context,
        f"🏁 <b>{label} Selesai!</b>\n\n"
        f"<b>Hasil:</b>\n{lines}"
    )

# ==================== POLL ANSWER HANDLER ====================
async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    if not poll_answer:
        return

    user_id = poll_answer.user.id
    user_display = get_user_display(poll_answer.user)

    # Math Race
    if _math_session.get("active") and poll_answer.poll_id == _math_session.get("poll_id"):
        if user_id in _math_session["voted"]:
            return
        _math_session["voted"].add(user_id)
        if poll_answer.option_ids and poll_answer.option_ids[0] == _math_session["correct_idx"]:
            if user_id not in _math_session["scores"]:
                _math_session["scores"][user_id] = {"name": user_display, "count": 0}
            _math_session["scores"][user_id]["count"] += 1
            track_coins(user_id, COIN_PER_CORRECT, user_display)
        return

    # Subject Quiz
    if _quiz_session.get("active") and poll_answer.poll_id == _quiz_session.get("poll_id"):
        if user_id in _quiz_session["voted"]:
            return
        _quiz_session["voted"].add(user_id)
        if poll_answer.option_ids and poll_answer.option_ids[0] == _quiz_session["correct_idx"]:
            if user_id not in _quiz_session["scores"]:
                _quiz_session["scores"][user_id] = {"name": user_display, "count": 0}
            _quiz_session["scores"][user_id]["count"] += 1
            track_coins(user_id, COIN_PER_CORRECT, user_display)
        return

# ==================== MESSAGE HANDLER ====================
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    user = msg.from_user
    text = msg.text.strip()
    user_display = get_user_display(user)

    if not _active_session.get("active"):
        return
    if user.id in _active_session["answered"]:
        return

    answer = _active_session.get("answer", "")
    if text.lower().strip() != answer:
        return

    _active_session["answered"].add(user.id)
    track_coins(user.id, IDOL_COIN, user_display)

    game_type = _active_session.get("game_type", "quiz")
    type_labels = {
        "tebak_gambar": "🖼️ Tebak Gambar",
        "quiz_song":    "🎵 Tebak Lagu",
        "tebak_emoji":  "🤔 Tebak Emoji",
    }
    type_label = type_labels.get(game_type, "🎮 Game")
    _active_session.clear()

    try:
        await msg.reply_html(
            f"✅ <b>{user_display} BENAR!</b>\n"
            f"+{IDOL_COIN} koin Carpets! 🎉"
        )
    except: pass

    await safe_send(context,
        f"🏁 <b>{type_label} — SELESAI!</b>\n\n"
        f"🎊 Dijawab oleh <b>{user_display}</b>!\n"
        f"+{IDOL_COIN} koin Carpets! 🎉"
    )

# ==================== END GAME ====================
async def cmd_end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    ended = []
    if _active_session.get("active"):
        _active_session.clear()
        ended.append("Game aktif")
    if _math_session.get("active"):
        _math_session["active"] = False
        ended.append("Math Race")
    if _quiz_session.get("active"):
        _quiz_session["active"] = False
        ended.append("Subject Quiz")
    if ended:
        await update.message.reply_text(f"Game dihentikan: {', '.join(ended)}")
    else:
        await update.message.reply_text("Tidak ada game aktif.")

# ==================== SEND NOTIF ====================
async def cmd_send_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Kirim notifikasi + flush koin ke DB sekaligus.
    Semua koin yang terkumpul selama game baru di-update ke Supabase di sini,
    bukan saat game berlangsung — supaya request ke DB tidak membludak.
    """
    if update.effective_user.id not in OWNER_IDS:
        return

    if not _notif_scores:
        await update.message.reply_text("Belum ada data koin. Belum ada yang main hari ini.")
        return

    total_players = len(_notif_scores)
    await update.message.reply_text(
        f"⏳ Memproses {total_players} pemain...\n"
        f"(update koin ke DB + kirim notif)"
    )

    # Step 1: Flush semua koin ke DB sekaligus
    db_ok, db_fail = await flush_coins_to_db()

    # Step 2: Kirim notif via bot Carpets
    from telegram import Bot as TelegramBot
    carpets_bot = TelegramBot(token=CARPETS_TOKEN)

    notif_ok = 0
    notif_fail = 0
    for user_id, data in _notif_scores.items():
        name = data["name"]
        coins = data["coins"]
        if coins <= 0:
            continue
        try:
            await carpets_bot.send_message(
                user_id,
                f"🎉 <b>Hasil Game Carpets Quiz Hari Ini!</b>\n\n"
                f"Halo {html.escape(name)}!\n"
                f"Total koin yang kamu dapatkan dari semua game hari ini:\n\n"
                f"🪙 <b>+{coins} koin Carpets</b>\n\n"
                f"Makasih udah ikutan main! Sampai besok 😊",
                parse_mode=ParseMode.HTML
            )
            notif_ok += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Gagal kirim notif ke {user_id}: {e}")
            notif_fail += 1

    await update.message.reply_html(
        f"✅ <b>Selesai!</b>\n\n"
        f"💾 DB update: <b>{db_ok} berhasil</b>, {db_fail} gagal\n"
        f"📨 Notif terkirim: <b>{notif_ok} berhasil</b>, {notif_fail} gagal"
    )

async def cmd_reset_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset data notif scores (untuk reset harian)"""
    if update.effective_user.id not in OWNER_IDS:
        return
    _notif_scores.clear()
    await update.message.reply_text("Data skor notif direset.")

# ==================== HELP ====================
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        await update.message.reply_html(
            "🎮 <b>Carpets Quiz Bot</b>\n\n"
            "Game yang tersedia:\n"
            "🖼️ Tebak Gambar\n"
            "🎵 Tebak Lagu\n"
            "🤔 Tebak Emoji\n"
            "🔢 Math Race\n"
            "🧮 Matematika / 🔬 IPA / 🌍 IPS / 📜 Sejarah\n"
            "🇬🇧 English / 🧬 Science / ⚗️ Kimia / 🧫 Biologi\n"
            "⚡ Fisika / 📝 Bahasa Indonesia\n"
            "🏙️ Ibu Kota / 🚩 Bendera / 🗺️ Geografi / 🎬 Film / 💻 Teknologi\n\n"
            f"Setiap jawaban benar = <b>+{COIN_PER_CORRECT} koin Carpets</b>"
        )
        return

    await update.message.reply_html(
        "🎮 <b>Owner Commands — Carpets Quiz</b>\n\n"
        "<b>Tebak Gambar:</b>\n"
        "<code>/startidol jawaban</code> — reply ke gambar\n\n"
        "<b>Tebak Lagu:</b>\n"
        "<code>/startsong jawaban | lirik</code>\n\n"
        "<b>Tebak Emoji:</b>\n"
        "<code>/startemoji jawaban | 🎭🎬</code>\n\n"
        "<b>Math Race (20 soal):</b>\n"
        "<code>/startmath</code>\n\n"
        "<b>Quiz (20 soal):</b>\n"
        "<code>/startquiz matematika</code>\n"
        "<code>/startquiz ipa</code>\n"
        "<code>/startquiz ips</code>\n"
        "<code>/startquiz sejarah</code>\n"
        "<code>/startquiz english</code>\n"
        "<code>/startquiz science</code>\n"
        "<code>/startquiz kimia</code>\n"
        "<code>/startquiz biologi</code>\n"
        "<code>/startquiz fisika</code>\n"
        "<code>/startquiz bahasa</code>\n"
        "<code>/startquiz ibukota</code>\n"
        "<code>/startquiz bendera</code>\n"
        "<code>/startquiz geografi</code>\n"
        "<code>/startquiz film</code>\n"
        "<code>/startquiz teknologi</code>\n\n"
        "<b>Lainnya:</b>\n"
        "<code>/endgame</code> — tutup game aktif\n"
        "<code>/sendnotif</code> — update koin ke DB + kirim notif ke semua pemain\n"
        "<code>/resetnotif</code> — reset data notif harian"
    )


# ==================== FIFA WORLD CUP PREDICTION ====================

async def fifa_fetch_today_matches() -> list:
    url = f"{FIFA_API_BASE}/competitions/WC/matches"
    # Pakai UTC range biar match dini hari (WIB) ga kelewat
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    date_from = now_utc.strftime("%Y-%m-%d")
    date_to   = (now_utc + timedelta(days=1)).strftime("%Y-%m-%d")
    params = {"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED,TIMED"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"X-Auth-Token": FIFA_API_KEY}, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("matches", [])
    except Exception as e:
        logger.error(f"FIFA fetch error: {e}")
    return []

async def fifa_fetch_match_result(match_id: int, context=None) -> dict:
    url = f"{FIFA_API_BASE}/matches/{match_id}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"X-Auth-Token": FIFA_API_KEY}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                result = data.get("match") or data
                logger.info(f"FIFA fetch {match_id}: keys={list(result.keys()) if isinstance(result, dict) else type(result)}, status={result.get('status') if isinstance(result, dict) else 'N/A'}")
                return result
            else:
                msg = f"❌ FIFA API non-200\nMatch ID: <code>{match_id}</code>\nStatus: <code>{r.status_code}</code>\nBody: <code>{r.text[:300]}</code>"
                logger.error(msg)
                if context:
                    await notify_owner(context, msg)
    except Exception as e:
        msg = f"❌ FIFA fetch exception\nMatch ID: <code>{match_id}</code>\nError: <code>{e}</code>"
        logger.error(msg)
        if context:
            await notify_owner(context, msg)
    return {}

def fifa_parse_kickoff_wib(utc_str: str):
    import re
    utc_str = re.sub(r"\+00:00$", "", utc_str).replace("Z", "")
    dt = datetime.fromisoformat(utc_str).replace(tzinfo=pytz.utc)
    return dt.astimezone(WIB)

async def fifa_schedule_match(context, match: dict):
    match_id  = match["id"]
    home      = match["homeTeam"]["name"]
    away      = match["awayTeam"]["name"]
    kickoff   = fifa_parse_kickoff_wib(match["utcDate"])
    now       = datetime.now(WIB)
    announce_time = kickoff - timedelta(hours=2)
    if announce_time <= now:
        if now < kickoff:
            announce_time = now + timedelta(seconds=5)
        else:
            return
    job_data = {"match_id": match_id, "home": home, "away": away, "kickoff": kickoff}
    # Cancel job lama sebelum schedule ulang — cegah duplikat kalau /fifaon dipanggil >1x
    for jname in [f"fifa_announce_{match_id}", f"fifa_close_{match_id}", f"fifa_result_{match_id}", f"fifa_live_{match_id}"]:
        for old_job in context.job_queue.get_jobs_by_name(jname):
            old_job.schedule_removal()
    context.job_queue.run_once(fifa_announce_job, when=(announce_time - now).total_seconds(), data=job_data, name=f"fifa_announce_{match_id}")
    context.job_queue.run_once(fifa_close_job, when=(kickoff - now).total_seconds(), data=job_data, name=f"fifa_close_{match_id}")
    result_time = kickoff + timedelta(hours=2)
    context.job_queue.run_once(fifa_result_job, when=(result_time - now).total_seconds(), data=job_data, name=f"fifa_result_{match_id}")
    # Live score polling — mulai pas kickoff, tiap 2 menit, stop otomatis pas FINISHED
    context.job_queue.run_repeating(fifa_livescore_job, interval=120, first=(kickoff - now).total_seconds(), data=job_data, name=f"fifa_live_{match_id}")
    await sb_upsert("fifa_scheduled", {"match_id": match_id, "home": home, "away": away, "kickoff": kickoff.isoformat()})
    logger.info(f"FIFA scheduled: {home} vs {away} kickoff {kickoff.strftime('%H:%M WIB')}")

async def fifa_announce_job(context):
    if not FIFA_EVENT_ACTIVE:
        return
    data        = context.job.data
    match_id    = data["match_id"]
    home        = data["home"]
    away        = data["away"]
    kickoff     = data["kickoff"]
    kickoff_str = kickoff.strftime("%H:%M WIB")
    home_safe   = home.replace(" ", "_")
    away_safe   = away.replace(" ", "_")
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"⚽ {home}", url=f"https://t.me/{FIFA_BOT_USERNAME}?start=fifa_{match_id}_{home_safe}"),
        InlineKeyboardButton(f"⚽ {away}", url=f"https://t.me/{FIFA_BOT_USERNAME}?start=fifa_{match_id}_{away_safe}"),
    ]])
    try:
        msg = await context.bot.send_message(
            FIFA_GROUP_ID,
            f"🏆 <b>FIFA World Cup 2026 — Prediksi Match!</b>\n\n"
            f"⚽ <b>{home}</b> vs <b>{away}</b>\n"
            f"🕐 Kickoff: <b>{kickoff_str}</b>\n\n"
            f"Tebak siapa yang menang dan dapatkan <b>🪙 {FIFA_COIN_REWARD} koin!</b>\n"
            f"Max <b>{FIFA_MAX_PREDICTORS} orang</b> bisa ikut.\n\n"
            f"👥 <b>0 orang</b> sudah memilih\n\n"
            f"⬇️ Tekan tombol untuk tebak di bot!",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        _fifa_announce_msgs[match_id] = msg.message_id
    except Exception as e:
        logger.error(f"FIFA announce error: {e}")

async def fifa_close_job(context):
    if not FIFA_EVENT_ACTIVE:
        return
    data     = context.job.data
    home     = data["home"]
    away     = data["away"]
    match_id = data["match_id"]
    count_res = await sb("GET", "wc_predictions", {"match_id": f"eq.{match_id}", "select": "user_id"})
    count = len([r for r in (count_res or []) if r.get("user_id", 0) != 0])
    try:
        await context.bot.send_message(
            FIFA_GROUP_ID,
            f"🔒 <b>Prediksi ditutup!</b>\n\n"
            f"⚽ <b>{home}</b> vs <b>{away}</b> — kickoff sekarang!\n"
            f"👥 Total {count} orang ikut tebak.\n\n"
            f"Pantau hasilnya, pemenang dapat 🪙 <b>{FIFA_COIN_REWARD} koin!</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"FIFA close error: {e}")
    # Tandai match sebagai closed dengan dummy user_id=0
    await sb("POST", "wc_predictions", data={"match_id": match_id, "user_id": 0, "user_name": "_closed_", "predicted": "_closed_", "rewarded": False})

async def fifa_result_job(context):
    if not FIFA_EVENT_ACTIVE:
        return
    data     = context.job.data
    match_id = data["match_id"]
    if match_id in _fifa_result_done:
        return
    home     = data["home"]
    away     = data["away"]
    match_data = await fifa_fetch_match_result(match_id, context)
    status     = match_data.get("status", "")
    if status not in ("FINISHED", "AWARDED"):
        context.job_queue.run_once(fifa_result_job, when=1800, data=data, name=f"fifa_result_retry_{match_id}")
        return
    score     = match_data.get("score", {})
    full_time = score.get("fullTime") or {}
    home_g_raw = full_time.get("home")
    away_g_raw = full_time.get("away")
    # API FIFA kadang return null score walau status sudah FINISHED — retry kalau skor belum siap
    if home_g_raw is None or away_g_raw is None:
        context.job_queue.run_once(fifa_result_job, when=900, data=data, name=f"fifa_result_retry_{match_id}")
        await notify_owner(context, f"⚠️ Match <code>{match_id}</code> ({home} vs {away}) FINISHED tapi skor masih null — retry 15 mnt")
        return
    home_g = int(home_g_raw)
    away_g = int(away_g_raw)
    # Gunakan nama canonical dari fifa_scheduled agar konsisten dengan nama di tombol prediksi
    sched_rows = await sb("GET", "fifa_scheduled", {"match_id": f"eq.{match_id}"}) or []
    canonical_home = sched_rows[0]["home"] if sched_rows else home
    canonical_away = sched_rows[0]["away"] if sched_rows else away
    if home_g > away_g:
        winner = canonical_home
        result_str = f"{canonical_home} menang {home_g}-{away_g}"
    elif away_g > home_g:
        winner = canonical_away
        result_str = f"{canonical_away} menang {away_g}-{home_g}"
    else:
        winner = "draw"
        result_str = f"Seri {home_g}-{away_g}"
    preds = await sb("GET", "wc_predictions", {"match_id": f"eq.{match_id}", "rewarded": "eq.false"})
    preds = [p for p in (preds or []) if p.get("user_id", 0) != 0]
    winners = [p for p in preds if p.get("predicted") == winner]
    if winners:
        user_ids = [p["user_id"] for p in winners]
        id_str   = "(" + ",".join(str(uid) for uid in user_ids) + ")"
        rows = await sb("GET", "users", {"user_id": f"in.{id_str}", "select": "user_id,koin"})
        coins_map = {int(r["user_id"]): (r.get("koin") or 0) for r in (rows or [])}
        for uid in user_ids:
            new_koin = coins_map.get(uid, 0) + FIFA_COIN_REWARD
            await sb("PATCH", "users", {"user_id": f"eq.{uid}"}, {"koin": new_koin})
            await asyncio.sleep(0.05)
    for p in preds:
        await sb("PATCH", "wc_predictions", {"match_id": f"eq.{match_id}", "user_id": f"eq.{p['user_id']}"}, {"rewarded": True})
    from telegram import Bot as TelegramBot
    carpets_bot = TelegramBot(token=CARPETS_TOKEN)
    for p in winners:
        try:
            await carpets_bot.send_message(
                p["user_id"],
                f"🏆 <b>Prediksi kamu BENAR!</b>\n\n"
                f"⚽ {home} vs {away}\n"
                f"📊 Hasil: {result_str}\n\n"
                f"🪙 <b>+{FIFA_COIN_REWARD} koin</b> sudah masuk ke akun Carpets kamu!",
                parse_mode=ParseMode.HTML
            )
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"FIFA notif winner error {p['user_id']}: {e}")
    _fifa_result_done.add(match_id)
    try:
        result_emoji = "🤝" if winner == "draw" else "🏆"
        await context.bot.send_message(
            FIFA_GROUP_ID,
            f"{result_emoji} <b>Hasil Match!</b>\n\n"
            f"⚽ <b>{home}</b> vs <b>{away}</b>\n"
            f"📊 {result_str}\n\n"
            f"🎯 {len(winners)}/{len(preds)} orang tebak benar\n"
            + (f"🪙 Masing-masing dapat <b>+{FIFA_COIN_REWARD} koin!</b>" if winners else "😔 Tidak ada yang tebak benar, tidak ada koin."),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"FIFA result announce error: {e}")

async def fifa_update_group_counter(context, match_id: int, home: str, away: str, kickoff_str: str):
    """Edit pesan announce di group — update counter orang yang udah milih"""
    msg_id = _fifa_announce_msgs.get(match_id)
    if not msg_id:
        return
    try:
        count_res = await sb("GET", "wc_predictions", {"match_id": f"eq.{match_id}", "select": "user_id"})
        total = len([r for r in (count_res or []) if r.get("user_id", 0) != 0])
        home_safe = home.replace(" ", "_")
        away_safe = away.replace(" ", "_")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"⚽ {home}", url=f"https://t.me/{FIFA_BOT_USERNAME}?start=fifa_{match_id}_{home_safe}"),
            InlineKeyboardButton(f"⚽ {away}", url=f"https://t.me/{FIFA_BOT_USERNAME}?start=fifa_{match_id}_{away_safe}"),
        ]])
        count_line = (f"🔥 <b>PENUH! {total}/{FIFA_MAX_PREDICTORS} orang</b> sudah memilih"
                      if total >= FIFA_MAX_PREDICTORS
                      else f"👥 <b>{total} orang</b> sudah memilih")
        await context.bot.edit_message_text(
            chat_id=FIFA_GROUP_ID,
            message_id=msg_id,
            text=(
                f"🏆 <b>FIFA World Cup 2026 — Prediksi Match!</b>\n\n"
                f"⚽ <b>{home}</b> vs <b>{away}</b>\n"
                f"🕐 Kickoff: <b>{kickoff_str}</b>\n\n"
                f"Tebak siapa yang menang dan dapatkan <b>🪙 {FIFA_COIN_REWARD} koin!</b>\n"
                f"Max <b>{FIFA_MAX_PREDICTORS} orang</b> bisa ikut.\n\n"
                f"{count_line}\n\n"
                f"⬇️ Tekan tombol untuk tebak di bot!"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning(f"FIFA edit counter error: {e}")

async def fifa_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start dari tombol URL di group"""
    msg  = update.message
    user = msg.from_user
    args = context.args
    if not args or not args[0].startswith("fifa_"):
        await cmd_help(update, context)
        return
    if not FIFA_EVENT_ACTIVE:
        await msg.reply_html("⏰ Event prediksi FIFA tidak aktif sekarang.")
        return
    payload = args[0][5:]
    parts   = payload.split("_", 1)
    if len(parts) != 2:
        await msg.reply_text("Link tidak valid.")
        return
    try:
        match_id = int(parts[0])
    except ValueError:
        await msg.reply_text("Link tidak valid.")
        return
    predicted = parts[1].replace("_", " ")
    user_id   = user.id
    user_name = get_user_display(user)
    closed = await sb("GET", "wc_predictions", {"match_id": f"eq.{match_id}", "user_id": "eq.0", "select": "user_id"})
    if closed:
        await msg.reply_html("⏰ <b>Prediksi sudah ditutup!</b>\n\nKickoff sudah dimulai.")
        return
    existing = await sb("GET", "wc_predictions", {"match_id": f"eq.{match_id}", "user_id": f"eq.{user_id}", "select": "predicted"})
    if existing:
        prev = existing[0].get("predicted", "")
        await msg.reply_html(f"⚠️ Kamu sudah tebak: <b>{prev}</b>\n\nTidak bisa ganti pilihan.")
        return
    count_res = await sb("GET", "wc_predictions", {"match_id": f"eq.{match_id}", "select": "user_id"})
    current_count = len([r for r in (count_res or []) if r.get("user_id", 0) != 0])
    if current_count >= FIFA_MAX_PREDICTORS:
        await msg.reply_html(f"😔 Slot prediksi sudah penuh! (<b>{FIFA_MAX_PREDICTORS}/{FIFA_MAX_PREDICTORS}</b>)")
        return
    await sb("POST", "wc_predictions", data={"match_id": match_id, "user_id": user_id, "user_name": user_name, "predicted": predicted, "rewarded": False})
    new_count = current_count + 1
    await msg.reply_html(
        f"✅ <b>Prediksi berhasil dicatat!</b>\n\n"
        f"⚽ Pilihanmu: <b>{predicted}</b>\n"
        f"🪙 Kalau bener dapat <b>+{FIFA_COIN_REWARD} koin</b>!\n\n"
        f"👥 {new_count}/{FIFA_MAX_PREDICTORS} slot terisi"
    )
    # Cari data match buat update counter
    jobs = context.job_queue.get_jobs_by_name(f"fifa_close_{match_id}")
    if jobs:
        jdata = jobs[0].data
        ko_str = jdata["kickoff"].strftime("%H:%M WIB")
        await fifa_update_group_counter(context, match_id, jdata["home"], jdata["away"], ko_str)
    if new_count >= FIFA_MAX_PREDICTORS:
        try:
            await context.bot.send_message(
                FIFA_GROUP_ID,
                f"🔥 <b>Prediksi sudah PENUH! {FIFA_MAX_PREDICTORS}/{FIFA_MAX_PREDICTORS}</b>\n\nSlot habis. Pantau hasilnya! 🏆",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"FIFA full announce error: {e}")

async def notify_owner(context, text: str):
    """Kirim pesan debug/error ke PM owner"""
    for oid in OWNER_IDS:
        try:
            await context.bot.send_message(oid, f"🔧 <b>[FIFA DEBUG]</b>\n\n{text}", parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"notify_owner failed for {oid}: {e}")

async def fifa_livescore_job(context):
    """Poll skor tiap 2 menit selama match berlangsung, announce ke group kalau ada gol"""
    if not FIFA_EVENT_ACTIVE:
        return
    data     = context.job.data
    match_id = data["match_id"]
    home     = data["home"]
    away     = data["away"]
    match_data = await fifa_fetch_match_result(match_id, context)

    if not match_data:
        msg = f"⚠️ <code>fifa_livescore_job</code> — match_data kosong!\nMatch ID: <code>{match_id}</code>\n{home} vs {away}"
        logger.error(msg)
        await notify_owner(context, msg)
        return

    status = match_data.get("status", "")
    score      = match_data.get("score", {})
    full_time  = score.get("fullTime", {})
    home_g     = full_time.get("home") or 0
    away_g     = full_time.get("away") or 0

    await notify_owner(context,
        f"📡 Live poll: <b>{home} vs {away}</b>\n"
        f"Status: <code>{status}</code>\n"
        f"Skor: <b>{home_g} - {away_g}</b>\n"
        f"Prev: {_fifa_live_scores.get(match_id, 'belum ada')}"
    )

    # Stop job kalau match selesai
    if status in ("FINISHED", "AWARDED", "CANCELLED", "POSTPONED"):
        context.job.schedule_removal()
        await notify_owner(context, f"🏁 Match <b>{home} vs {away}</b> status: <code>{status}</code> — trigger result job")
        if status in ("FINISHED", "AWARDED"):
            for job in context.job_queue.get_jobs_by_name(f"fifa_result_{match_id}"):
                job.schedule_removal()
            await fifa_result_job(context)
        return

    if status not in ("IN_PLAY", "PAUSED", "HALFTIME"):
        await notify_owner(context, f"⏳ Status <code>{status}</code> — skip (belum IN_PLAY)")
        return

    prev = _fifa_live_scores.get(match_id, {"home_g": -1, "away_g": -1})

    if match_id not in _fifa_live_scores:
        # First poll — inisialisasi skor
        _fifa_live_scores[match_id] = {"home_g": home_g, "away_g": away_g}
        await notify_owner(context, f"🔵 First poll init: <b>{home} {home_g} - {away_g} {away}</b>")
        return

    # Deteksi gol baru
    if home_g != prev["home_g"] or away_g != prev["away_g"]:
        _fifa_live_scores[match_id] = {"home_g": home_g, "away_g": away_g}
        scorer = home if home_g > prev["home_g"] else away
        try:
            await context.bot.send_message(
                FIFA_GROUP_ID,
                f"⚽ <b>GOL! {scorer}!</b>\n\n"
                f"🏟️ <b>{home} {home_g} - {away_g} {away}</b>\n",
                parse_mode=ParseMode.HTML
            )
            await notify_owner(context, f"✅ GOL announce berhasil: {scorer} | {home} {home_g}-{away_g} {away}")
        except Exception as e:
            err = f"❌ GOL announce GAGAL: {e}\n{home} {home_g}-{away_g} {away}"
            logger.error(err)
            await notify_owner(context, err)

async def fifa_daily_schedule_job(context):
    """Jalan tiap hari jam 00:05 WIB, auto-schedule match hari ini selama FIFA_EVENT_ACTIVE"""
    if not FIFA_EVENT_ACTIVE:
        return
    matches = await fifa_fetch_today_matches()
    if not matches:
        logger.info("FIFA daily schedule: tidak ada match hari ini")
        return
    for match in matches:
        await fifa_schedule_match(context, match)
    logger.info(f"FIFA daily schedule: {len(matches)} match dijadwalkan")

async def cmd_fifaannounce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kirim ulang pesan prediksi ke group + buka voting: /fifaannounce <match_id>"""
    if update.effective_user.id not in OWNER_IDS:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /fifaannounce <match_id>")
        return
    try:
        mid = int(args[0])
    except ValueError:
        await update.message.reply_text("match_id harus angka.")
        return

    global FIFA_EVENT_ACTIVE
    FIFA_EVENT_ACTIVE = True

    # Ambil data dari Supabase atau API
    sched_rows = await sb("GET", "fifa_scheduled", {"match_id": f"eq.{mid}"}) or []
    sched = sched_rows[0] if sched_rows else None

    if sched:
        home    = sched["home"]
        away    = sched["away"]
        kickoff = datetime.fromisoformat(sched["kickoff"])
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=WIB)
    else:
        data = await fifa_fetch_match_result(mid, context)
        if not data:
            await update.message.reply_html(f"❌ Tidak bisa fetch match <code>{mid}</code>")
            return
        home    = data.get("homeTeam", {}).get("name", "Home")
        away    = data.get("awayTeam", {}).get("name", "Away")
        kickoff = fifa_parse_kickoff_wib(data.get("utcDate", ""))
        await sb_upsert("fifa_scheduled", {"match_id": mid, "home": home, "away": away, "kickoff": kickoff.isoformat()})

    kickoff_str = kickoff.strftime("%H:%M WIB")
    home_safe   = home.replace(" ", "_")
    away_safe   = away.replace(" ", "_")

    # Cek sudah berapa yang prediksi
    count_res = await sb("GET", "wc_predictions", {"match_id": f"eq.{mid}", "select": "user_id"}) or []
    count = len([r for r in count_res if r.get("user_id", 0) != 0])

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"⚽ {home}", url=f"https://t.me/{FIFA_BOT_USERNAME}?start=fifa_{mid}_{home_safe}"),
        InlineKeyboardButton(f"⚽ {away}", url=f"https://t.me/{FIFA_BOT_USERNAME}?start=fifa_{mid}_{away_safe}"),
    ]])
    try:
        msg = await context.bot.send_message(
            FIFA_GROUP_ID,
            f"🏆 <b>FIFA World Cup 2026 — Prediksi Match!</b>\n\n"
            f"⚽ <b>{home}</b> vs <b>{away}</b>\n"
            f"🕐 Kickoff: <b>{kickoff_str}</b>\n\n"
            f"Tebak siapa yang menang dan dapatkan <b>🪙 {FIFA_COIN_REWARD} koin!</b>\n"
            f"Max <b>{FIFA_MAX_PREDICTORS} orang</b> bisa ikut.\n\n"
            f"👥 <b>{count} orang</b> sudah memilih\n\n"
            f"⬇️ Tekan tombol untuk tebak di bot!",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        _fifa_announce_msgs[mid] = msg.message_id
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal kirim ke group: {e}")
        return

    # Schedule close job pas kickoff kalau belum lewat
    now = datetime.now(WIB)
    if kickoff > now:
        job_data = {"match_id": mid, "home": home, "away": away, "kickoff": kickoff}
        for job in context.job_queue.get_jobs_by_name(f"fifa_close_{mid}"):
            job.schedule_removal()
        for job in context.job_queue.get_jobs_by_name(f"fifa_result_{mid}"):
            job.schedule_removal()
        for job in context.job_queue.get_jobs_by_name(f"fifa_live_{mid}"):
            job.schedule_removal()
        context.job_queue.run_once(fifa_close_job, when=(kickoff - now).total_seconds(), data=job_data, name=f"fifa_close_{mid}")
        result_time = kickoff + timedelta(hours=2)
        context.job_queue.run_once(fifa_result_job, when=(result_time - now).total_seconds(), data=job_data, name=f"fifa_result_{mid}")
        context.job_queue.run_repeating(fifa_livescore_job, interval=120, first=(kickoff - now).total_seconds(), data=job_data, name=f"fifa_live_{mid}")

    await update.message.reply_html(
        f"✅ Announce terkirim ke group!\n"
        f"<b>{home} vs {away}</b> — {kickoff_str}\n"
        f"{'📅 Close + result job dijadwalkan.' if kickoff > now else '⚠️ Kickoff sudah lewat, job tidak dijadwalkan.'}"
    )

async def cmd_fifawatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start livescore polling manual untuk match yang lagi IN_PLAY: /fifawatch <match_id>"""
    if update.effective_user.id not in OWNER_IDS:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /fifawatch <match_id>")
        return
    try:
        mid = int(args[0])
    except ValueError:
        await update.message.reply_text("match_id harus angka.")
        return

    global FIFA_EVENT_ACTIVE
    FIFA_EVENT_ACTIVE = True

    # Fetch data match dari API
    data = await fifa_fetch_match_result(mid, context)
    if not data:
        await update.message.reply_html(f"❌ Tidak bisa fetch match <code>{mid}</code>")
        return

    status  = data.get("status", "")
    score   = data.get("score", {})
    ft      = score.get("fullTime", {})
    home_g  = ft.get("home") or 0
    away_g  = ft.get("away") or 0

    # Pakai nama canonical dari fifa_scheduled agar konsisten dengan tombol prediksi
    sched_rows = await sb("GET", "fifa_scheduled", {"match_id": f"eq.{mid}"}) or []
    if sched_rows:
        home = sched_rows[0]["home"]
        away = sched_rows[0]["away"]
    else:
        home = data.get("homeTeam", {}).get("name", "Home")
        away = data.get("awayTeam", {}).get("name", "Away")

    # Init skor supaya gol berikutnya ke-detect
    _fifa_live_scores[mid] = {"home_g": home_g, "away_g": away_g}

    job_data = {"match_id": mid, "home": home, "away": away, "kickoff": datetime.now(WIB)}

    # Cancel job lama kalau ada
    for job in context.job_queue.get_jobs_by_name(f"fifa_live_{mid}"):
        job.schedule_removal()
    for job in context.job_queue.get_jobs_by_name(f"fifa_result_{mid}"):
        job.schedule_removal()

    # Start livescore polling sekarang
    context.job_queue.run_repeating(fifa_livescore_job, interval=120, first=5, data=job_data, name=f"fifa_live_{mid}")
    # Schedule result job 2 jam dari sekarang sebagai fallback
    context.job_queue.run_once(fifa_result_job, when=7200, data=job_data, name=f"fifa_result_{mid}")

    # Kirim ulang pesan status match ke group
    skor_str = f"{home_g} - {away_g}"
    await context.bot.send_message(
        FIFA_GROUP_ID,
        f"📡 <b>Live: {home} vs {away}</b>\n\n"
        f"🔴 Status: <code>{status}</code>\n"
        f"⚽ Skor: <b>{skor_str}</b>\n\n"
        f"Bot sekarang memantau match ini setiap 2 menit!",
        parse_mode=ParseMode.HTML
    )
    await update.message.reply_html(
        f"✅ Watching <b>{home} vs {away}</b>\n"
        f"Skor saat ini: <b>{skor_str}</b>\n"
        f"Polling tiap 2 menit, result job dalam 2 jam."
    )

async def cmd_fifaon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FIFA_EVENT_ACTIVE
    if update.effective_user.id not in OWNER_IDS:
        return
    FIFA_EVENT_ACTIVE = True
    matches = await fifa_fetch_today_matches()
    if not matches:
        await update.message.reply_html("✅ FIFA Event <b>ON</b>\n\n⚠️ Tidak ada match hari ini dari API.")
        return
    scheduled = 0
    lines = ""
    for match in matches:
        await fifa_schedule_match(context, match)
        scheduled += 1
        ko = fifa_parse_kickoff_wib(match["utcDate"])
        lines += f"⚽ {match['homeTeam']['name']} vs {match['awayTeam']['name']} — {ko.strftime('%H:%M WIB')}\n"
    await update.message.reply_html(
        f"✅ FIFA Event <b>ON</b>\n\n"
        f"📅 {scheduled} match dijadwalkan hari ini:\n{lines}\n"
        f"Announce otomatis 2 jam sebelum kickoff!"
    )

async def cmd_fifaoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FIFA_EVENT_ACTIVE
    if update.effective_user.id not in OWNER_IDS:
        return
    FIFA_EVENT_ACTIVE = False
    await update.message.reply_html("🔴 FIFA Event <b>OFF</b>")

async def cmd_fifastatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    status = "ON 🟢" if FIFA_EVENT_ACTIVE else "OFF 🔴"
    await update.message.reply_html(
        f"🏆 <b>FIFA Event Status: {status}</b>\n\n"
        f"<code>/fifaon</code> — aktifkan + schedule match hari ini\n"
        f"<code>/fifaoff</code> — nonaktifkan\n"
        f"<code>/fifatest</code> — lihat match hari ini dari API"
    )

async def cmd_fifatest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek koneksi API + list match hari ini. Kalau ada arg match_id, fetch detail match itu."""
    if update.effective_user.id not in OWNER_IDS:
        return
    args = context.args
    # Kalau ada arg, fetch detail 1 match
    if args:
        try:
            mid = int(args[0])
        except ValueError:
            await update.message.reply_text("Usage: /fifatest [match_id]")
            return
        await update.message.reply_text(f"⏳ Fetching match {mid}...")
        data = await fifa_fetch_match_result(mid, context)
        if not data:
            await update.message.reply_html(f"❌ API return kosong untuk match ID <code>{mid}</code>")
            return
        import json
        snippet = json.dumps(data, indent=2, ensure_ascii=False)[:3000]
        await update.message.reply_html(f"<b>Raw API response match {mid}:</b>\n<pre>{snippet}</pre>")
        return
    # Tanpa arg — list match hari ini
    await update.message.reply_text("⏳ Menghubungi API...")
    matches = await fifa_fetch_today_matches()
    if not matches:
        await update.message.reply_html("❌ API tidak return match hari ini.\nCek API key / kompetisi yang didaftarkan.")
        return
    # Cek mana yang udah di-schedule di Supabase
    sched_rows = await sb("GET", "fifa_scheduled", {}) or []
    sched_ids  = {int(r["match_id"]) for r in sched_rows}
    lines = ""
    for m in matches:
        ko = fifa_parse_kickoff_wib(m["utcDate"])
        scheduled_mark = "✅" if m["id"] in sched_ids else "⬜"
        lines += f"{scheduled_mark} ID:<code>{m['id']}</code> {m['homeTeam']['name']} vs {m['awayTeam']['name']} | {ko.strftime('%H:%M WIB')} | <code>{m['status']}</code>\n"
    await update.message.reply_html(
        f"✅ <b>API OK — Match hari ini ({len(matches)}):</b>\n\n{lines}\n"
        f"📋 Match terschedule di Supabase: <b>{len(sched_ids)}</b>\n"
        f"FIFA Event: {'🟢 ON' if FIFA_EVENT_ACTIVE else '🔴 OFF'}"
    )

async def cmd_fifaresult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger result announce manual: /fifaresult <match_id>"""
    if update.effective_user.id not in OWNER_IDS:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /fifaresult <match_id>")
        return
    try:
        mid = int(args[0])
    except ValueError:
        await update.message.reply_text("match_id harus angka.")
        return
    # Cari data match dari Supabase atau fallback ke API
    sched_rows = await sb("GET", "fifa_scheduled", {"match_id": f"eq.{mid}"}) or []
    sched = sched_rows[0] if sched_rows else None
    if sched:
        home = sched["home"]
        away = sched["away"]
    else:
        # Coba fetch dari API buat dapetin nama tim
        data = await fifa_fetch_match_result(mid, context)
        if not data:
            await update.message.reply_html(f"❌ Match ID <code>{mid}</code> tidak ditemukan di schedule maupun API.")
            return
        home = data.get("homeTeam", {}).get("name", "Home")
        away = data.get("awayTeam", {}).get("name", "Away")
    await update.message.reply_html(f"⏳ Fetching result <b>{home} vs {away}</b>...")
    # Bikin fake job data dan trigger result job
    import types
    fake_job = types.SimpleNamespace(
        data={"match_id": mid, "home": home, "away": away, "kickoff": datetime.now(WIB)},
        schedule_removal=lambda: None
    )
    fake_context = types.SimpleNamespace(
        bot=context.bot,
        job=fake_job,
        job_queue=context.job_queue
    )
    global FIFA_EVENT_ACTIVE
    _prev = FIFA_EVENT_ACTIVE
    FIFA_EVENT_ACTIVE = True  # bypass check buat manual trigger
    try:
        await fifa_result_job(fake_context)
    finally:
        FIFA_EVENT_ACTIVE = _prev
    await update.message.reply_text("✅ Result job selesai dijalankan.")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start",      fifa_start_handler))
    app.add_handler(CommandHandler("help",       cmd_help))
    app.add_handler(CommandHandler("startidol",  cmd_start_idol))
    app.add_handler(CommandHandler("startsong",  cmd_start_song))
    app.add_handler(CommandHandler("startemoji", cmd_start_emoji))
    app.add_handler(CommandHandler("startmath",  cmd_start_math))
    app.add_handler(CommandHandler("startquiz",  cmd_start_subject))
    app.add_handler(CommandHandler("endgame",    cmd_end_game))
    app.add_handler(CommandHandler("sendnotif",  cmd_send_notif))
    app.add_handler(CommandHandler("resetnotif", cmd_reset_notif))
    app.add_handler(CommandHandler("fifaon",     cmd_fifaon))
    app.add_handler(CommandHandler("fifaoff",    cmd_fifaoff))
    app.add_handler(CommandHandler("fifastatus", cmd_fifastatus))
    app.add_handler(CommandHandler("fifatest",   cmd_fifatest))
    app.add_handler(CommandHandler("fifaresult",  cmd_fifaresult))
    app.add_handler(CommandHandler("fifawatch",   cmd_fifawatch))
    app.add_handler(CommandHandler("fifaannounce", cmd_fifaannounce))
    app.add_handler(PollAnswerHandler(poll_answer_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    print("=" * 50)
    print("Carpets Quiz Bot — Aktif!")
    print(f"Group: {GAME_GROUP_ID}")
    print(f"Koin per soal: {COIN_PER_CORRECT}")
    print("=" * 50)

    # Auto-schedule FIFA match tiap hari jam 00:05 WIB
    now_wib_dt = datetime.now(WIB)
    next_midnight = now_wib_dt.replace(hour=0, minute=5, second=0, microsecond=0)
    if next_midnight <= now_wib_dt:
        next_midnight += timedelta(days=1)
    delay_secs = (next_midnight - now_wib_dt).total_seconds()
    app.job_queue.run_repeating(
        fifa_daily_schedule_job,
        interval=86400,
        first=delay_secs,
        name="fifa_daily"
    )

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
