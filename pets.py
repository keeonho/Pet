import os
import re

def sanitize_name(name: str) -> str:
    if not name:
        return "User"
    cleaned = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF\u0400-\u04FF\u0600-\u06FF\u0E00-\u0E7F\u2000-\u206F\u20A0-\u20CF\u2100-\u214F\u2190-\u21FF\u2200-\u22FF\u2300-\u23FF\u2500-\u257F\u2580-\u259F\u25A0-\u25FF\u2600-\u26FF\u2700-\u27BF\u2C00-\u2C5F\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF\u4E00-\u9FFF\uAC00-\uD7AF]', "", name, flags=re.UNICODE)
    cleaned = re.sub(r'[\u200B-\u200F\u2028-\u202F\uFEFF]', "", cleaned)
    cleaned = cleaned.strip()[:30]
    return cleaned or "User"

def safe_html(text: str) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&quot;").replace("'", "&#39;"))

import logging
import random
import json
import time
import asyncio
import pytz
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import httpx

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
    InlineQueryHandler, ConversationHandler
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

# ==================== CONFIG ====================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN        = "7827651899:AAEfAKBZob6zQxU7nLqa66hs4ALwo8637R0"
BOT_USERNAME = "@carpetsrobot"
LOG_GROUP    = -1003734864758
_BOT         = None  # di-set saat main()
OWNER_ID     = 8513979925
ADMIN_IDS    = {8513979925, 6234545645, 7763263108, 8309652397, 7784219616, 8684298921}
SHOP_URL     = "https://t.me/listbotfoocl"
REFERRAL_REWARD = 700  # koin per referral
TOPUP_GROUP     = -1003857757432
TOPUP_MIN       = 2000   # minimum top up coin
QRIS_URL        = "https://files.catbox.moe/7f8uv8.jpeg"
FORCE_SUB_CHANNEL = "@listbotfoocl"  # username channel wajib join

# ==================== TASK / MISI ====================
TASKS = [
    {
        "id": "pokergram", "type": "collab",
        "bot_name": "Pokergram", "emoji": "🃏",
        "title": "Join Pokergram & Grab your free chips now!",
        "link": "https://t.me/PokergramComBot/pokerapp?startapp=campCarpetsrobot_Sh_P",
        "image": "https://files.catbox.moe/3ovrnx.jpg",
        "reward_coin": 100, "reward_food": 5,
    },
    {
        "id": "boinkers", "type": "collab",
        "bot_name": "Boinkers", "emoji": "🎰",
        "title": "Spin the slot to claim your Boinkers Pet!",
        "link": "https://t.me/boinker_bot/boinkapp?startapp=campCarpetsrobot_Sh",
        "image": "https://files.catbox.moe/6qbhon.jpg",
        "reward_coin": 100, "reward_food": 5,
    },
    {
        "id": "pixelpaw", "type": "collab",
        "bot_name": "Pixel Paw", "emoji": "🐾",
        "title": "Reach lvl 12 in Pixel Paw",
        "link": "https://t.me/PixelPawsGame_bot/app?startapp=campCarpetsrobot_Sh",
        "image": "https://files.catbox.moe/d81c0x.png",
        "reward_coin": 100, "reward_food": 5,
    },
    {
        "id": "join_quiz", "type": "collab",
        "bot_name": "Carpets Quiz", "emoji": "🏆",
        "title": "Join Carpets Quiz",
        "link": "https://t.me/carpetsquiz",
        "image": None,
        "reward_coin": 100, "reward_food": 0,
    },
    {
        "id": "feed_other", "type": "count",
        "emoji": "🍖", "title": "Kasih makan pet orang lain",
        "target": 1, "reward_coin": 200, "reward_food": 0,
    },
    {
        "id": "play_games", "type": "count",
        "emoji": "🎮", "title": "Main mini game 20 kali",
        "target": 20, "reward_coin": 200, "reward_food": 0,
    },
    {
        "id": "topup_4k", "type": "topup",
        "emoji": "💳", "title": "Top up minimal 4.000 koin",
        "target": 4000, "reward_coin": 2000, "reward_food": 0,
    },
    {
        "id": "pet_lv60", "type": "milestone",
        "emoji": "⭐", "title": "1 pet mencapai level 60",
        "reward_coin": 500, "reward_food": 0,
    },
    {
        "id": "buy_50", "type": "count",
        "emoji": "🛒", "title": "Beli item di shop 50 kali",
        "target": 50, "reward_coin": 500, "reward_food": 0,
    },
    {
        "id": "gift_partner", "type": "count",
        "emoji": "🎁", "title": "Gift item ke partner",
        "target": 1, "reward_coin": 100, "reward_food": 0,
    },
    {
        "id": "gacha_10", "type": "count",
        "emoji": "🎰", "title": "Spin gacha box 10 kali",
        "target": 10, "reward_coin": 500, "reward_food": 0,
    },
    {
        "id": "harvest_10", "type": "count",
        "emoji": "🌾", "title": "Panen hasil ternak 10 kali",
        "target": 10, "reward_coin": 200, "reward_food": 0,
    },
]

SUPABASE_URL = "https://rtqxkdbslgtoyvouepqa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0cXhrZGJzbGd0b3l2b3VlcHFhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDk5ODkwNCwiZXhwIjoyMDk2NTc0OTA0fQ.dJGXkqiQyEsu2_eYLvIZnQ3SWQBY6u0zpRr0YmaY41E"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

WIB            = pytz.timezone('Asia/Jakarta')
DELIVERY_HOURS = 5
TAPS_NEEDED    = 6
ASK_PET_NAME   = 0

# ==================== PET & SHOP DATA ====================
PETS = {
    "cat":      {"name": "Kucing",          "emoji": "🐱", "rare": False, "price": 0},
    "dog":      {"name": "Anjing",          "emoji": "🐶", "rare": False, "price": 0},
    "rabbit":   {"name": "Kelinci",         "emoji": "🐰", "rare": False, "price": 0},
    "hamster":  {"name": "Hamster",         "emoji": "🐹", "rare": False, "price": 0},
    "fox":      {"name": "Rubah",           "emoji": "🦊", "rare": False, "price": 0},
    "penguin":  {"name": "Penguin",         "emoji": "🐧", "rare": False, "price": 0},
    "duck":     {"name": "Bebek",           "emoji": "🦆", "rare": False, "price": 0},
    "frog":     {"name": "Katak",           "emoji": "🐸", "rare": False, "price": 0},
    "bear":     {"name": "Beruang",         "emoji": "🐻", "rare": False, "price": 0},
    "koala":    {"name": "Koala",           "emoji": "🐨", "rare": False, "price": 0},
    "capybara": {"name": "Kapibara",        "emoji": "🦫", "rare": False, "price": 0},
    "axolotl":  {"name": "Axolotl",         "emoji": "🦎", "rare": True,  "price": 200},
    "panda":    {"name": "Panda",           "emoji": "🐼", "rare": True,  "price": 200},
    "unicorn":  {"name": "Unicorn",         "emoji": "🦄", "rare": True,  "price": 300},
    "dragon":   {"name": "Naga",            "emoji": "🐉", "rare": True,  "price": 300},
    "phoenix":  {"name": "Phoenix",         "emoji": "🐦‍🔥",  "rare": True, "price": 500},
    "koi":      {"name": "Ikan Koi",        "emoji": "🐟",   "rare": True,  "price": 500},
    "wolf":     {"name": "Serigala",        "emoji": "🐺",   "rare": False, "price": 0},
    "monkey":   {"name": "Monyet",          "emoji": "🐒",   "rare": False, "price": 0},
    # ===== PET GACHA EKSKLUSIF =====
    "kumiho":   {"name": "Kumiho",          "emoji": "🦊✨", "rare": True,  "price": 0, "gacha_only": True},
    "jellyfish": {"name": "Ubur-ubur",      "emoji": "🪼",   "rare": True,  "price": 0, "gacha_only": True},
    "tanuki":   {"name": "Tanuki",          "emoji": "🦝",   "rare": True,  "price": 0, "gacha_only": True},
    "void_cat": {"name": "Void Cat",        "emoji": "🌑🐱", "rare": True,  "price": 0, "gacha_only": True},
    # ===== PET ASTRO PAWS =====
    "moon_rabbit":   {"name": "Moon Rabbit",   "emoji": "🐇🌙", "rare": True, "price": 0, "astro_only": True, "hunger_resist": True},
    # ===== PET ASTRO PAWS 2 =====
    "scorpion_mars": {"name": "Scorpion Mars", "emoji": "🦂🔴", "rare": True, "price": 0, "astro2_only": True},
    # ===== PET AQUA TAILS =====
    "ikan_koi":      {"name": "Ikan Koi",      "emoji": "🐟",   "rare": True, "price": 0, "aqua_only": True},
    "ikan_biru":     {"name": "Blue Fin",      "emoji": "🐋",   "rare": True, "price": 1000000, "aqua_only": True},
    "ikan_emas_laut":{"name": "Golden Marlin", "emoji": "🌟",   "rare": True, "price": 1000000, "aqua_only": True},
    "ikan_petir":    {"name": "Thunder Eel",   "emoji": "⚡",   "rare": True, "price": 100000000, "aqua_only": True},
}

# ==================== HEWAN TERNAK ====================
# product_food = key di FOOD_SHOP/KOI_FOOD_SHOP yang bisa dikasih ke pet
# sell_price = harga jual per unit ke bot
# feed_hunger = hunger restore kalau dikasih ke pet (bukan dijual)
LIVESTOCK = {
    "cow":       {"name": "Sapi",          "emoji": "🐄", "price": 1000,
                  "product": "milk",       "product_name": "Susu",         "product_emoji": "🥛",
                  "sell_price": 50,        "interval_hours": 8,
                  "food_key": "milk",      "food_hunger": 30, "food_xp": 8, "can_feed_pet": True},
    "chicken":   {"name": "Ayam",          "emoji": "🐔", "price": 500,
                  "product": "egg",        "product_name": "Telur Ayam",   "product_emoji": "🥚",
                  "sell_price": 30,        "interval_hours": 6,
                  "food_key": "egg",       "food_hunger": 20, "food_xp": 5, "can_feed_pet": True},
    "farm_duck": {"name": "Bebek Ternak",  "emoji": "🦆", "price": 600,
                  "product": "duck_egg",   "product_name": "Telur Bebek",  "product_emoji": "🥚",
                  "sell_price": 40,        "interval_hours": 7,
                  "food_key": "duck_egg",  "food_hunger": 25, "food_xp": 6, "can_feed_pet": True},
    "goat":      {"name": "Kambing",       "emoji": "🐐", "price": 800,
                  "product": "goat_milk",  "product_name": "Susu Kambing", "product_emoji": "🥛",
                  "sell_price": 60,        "interval_hours": 10,
                  "food_key": "goat_milk", "food_hunger": 35, "food_xp": 10, "can_feed_pet": True},
    "rabbit_f":  {"name": "Kelinci Ternak","emoji": "🐇", "price": 1000,
                  "product": "rabbit_fur", "product_name": "Bulu Kelinci", "product_emoji": "🪶",
                  "sell_price": 70,        "interval_hours": 12,
                  "food_key": None, "product_key": "rabbit_fur", "food_hunger": 0, "food_xp": 0, "can_feed_pet": False},
    "bee":       {"name": "Lebah",         "emoji": "🐝", "price": 1000,
                  "product": "honey",      "product_name": "Madu",         "product_emoji": "🍯",
                  "sell_price": 80,        "interval_hours": 12,
                  "food_key": "honey",     "food_hunger": 40, "food_xp": 15, "can_feed_pet": True},
    "pig":       {"name": "Babi",          "emoji": "🐷", "price": 1500,
                  "product": "truffle",    "product_name": "Trüffel",      "product_emoji": "🍄",
                  "sell_price": 100,       "interval_hours": 16,
                  "food_key": None, "product_key": "truffle", "food_hunger": 0, "food_xp": 0, "can_feed_pet": False},
    "sheep":     {"name": "Domba",         "emoji": "🐑", "price": 800,
                  "product": "wool",       "product_name": "Wol",          "product_emoji": "🧶",
                  "sell_price": 65,        "interval_hours": 14,
                  "food_key": None,        "food_hunger": 0, "food_xp": 0, "can_feed_pet": False},
}

# Hasil ternak yang bisa jadi makanan pet (inventory key → info)
LIVESTOCK_FOOD = {
    "milk":       {"name": "Susu",         "emoji": "🥛", "hunger": 30, "xp": 8,  "happy": 5},
    "egg":        {"name": "Telur Ayam",   "emoji": "🥚", "hunger": 20, "xp": 5,  "happy": 3},
    "duck_egg":   {"name": "Telur Bebek",  "emoji": "🥚", "hunger": 25, "xp": 6,  "happy": 3},
    "goat_milk":  {"name": "Susu Kambing", "emoji": "🥛", "hunger": 35, "xp": 10, "happy": 8},
    "honey":      {"name": "Madu",         "emoji": "🍯", "hunger": 40, "xp": 15, "happy": 15},
}

BARN_UPGRADE_COST = 500  # per slot kandang

# Battle power multiplier per jenis pet
BATTLE_POWER = {
    "scorpion_mars": 5.0,  # Astro 2 exclusive — battle score tertinggi absolut
    "moon_rabbit": 1.6,  # Astro exclusive
    "phoenix": 2.0, "dragon": 1.9, "unicorn": 1.7, "koi": 1.5,
    "axolotl": 1.4, "panda": 1.3, "wolf": 1.2, "bear": 1.2,
    "fox": 1.1, "monkey": 1.1, "dog": 1.0, "cat": 1.0,
    "rabbit": 0.9, "hamster": 0.85, "frog": 0.85, "penguin": 0.85,
    "duck": 0.8, "koala": 0.8, "capybara": 0.9,
    # Gacha exclusive — battle power lebih tinggi dari semua biasa
    "kumiho":    2.3,   # Nine-Tailed Fox: paling tinggi, trickster
    "void_cat":  2.1,   # Void Cat: dark energy
    "jellyfish": 1.8,   # Ubur-ubur: mysterious power
    "tanuki":    1.6,   # Tanuki: luck-based
}

# Ekspedisi destinations
EXPEDITION_DESTINATIONS = {
    "local":   {"name": "Taman Kota", "emoji": "🌳", "cost": 0,   "duration_hours": 2, "xp_reward": 20,  "happy_reward": 15},
    "city":    {"name": "Luar Kota",  "emoji": "🏙️", "cost": 100, "duration_hours": 4, "xp_reward": 50,  "happy_reward": 30},
    "country": {"name": "Luar Negeri","emoji": "✈️", "cost": 300, "duration_hours": 8, "xp_reward": 120, "happy_reward": 60},
}

BOARDING_COST_PER_DAY = 500

# ==================== GACHA BOX ====================
GACHA_BIASA_PRICE   = 800
GACHA_PREMIUM_PRICE = 2000

# Item eksklusif gacha (key -> info)
GACHA_ITEMS = {
    "mega_feast":     {"name": "Mega Feast",     "emoji": "\U0001f356", "desc": "Kasih makan semua petmu sekaligus!"},
    "grand_revival":  {"name": "Grand Revival",  "emoji": "\U0001f31f", "desc": "Semua pet Hunger 0, Happiness 100, Health 100 sekaligus!"},
    "elixir":         {"name": "Elixir of Life", "emoji": "\U0001f48a", "desc": "HP + Happy + Hunger full sekaligus!"},
    "xp_booster":     {"name": "XP Booster",     "emoji": "\u2728",    "desc": "2x XP selama 24 jam!"},
    "parfum_mewah":   {"name": "Parfum Mewah",   "emoji": "\U0001f9f4", "desc": "Wangi 7 hari (biasanya 3 hari)!"},
    "battle_steak":   {"name": "Steak Petarung", "emoji": "\U0001f969", "desc": "+15 Battle Score permanen!"},
}

# Pet eksklusif gacha
GACHA_PET_POOL_PREMIUM = ["kumiho", "jellyfish", "tanuki", "void_cat"]

# Drop table gacha biasa (hanya item)
GACHA_BIASA_TABLE = [
    ("mega_feast",    15),
    ("grand_revival", 8),
    ("elixir",        12),
    ("xp_booster",   25),
    ("parfum_mewah", 20),
    ("battle_steak", 20),
]

# Drop table gacha premium item (70% item, 30% pet)
GACHA_PREMIUM_ITEM_TABLE = [
    ("mega_feast",    15),
    ("grand_revival", 15),
    ("elixir",        20),
    ("xp_booster",   15),
    ("parfum_mewah", 15),
    ("battle_steak", 20),
]

def _gacha_roll_item(table: list) -> str:
    """Roll item dari weighted table"""
    total = sum(w for _, w in table)
    r = random.randint(1, total)
    cumul = 0
    for key, w in table:
        cumul += w
        if r <= cumul:
            return key
    return table[-1][0]


FOOD_SHOP = {
    "snack":    {"name": "Snack",           "emoji": "🍪", "price": 20, "hunger": 20, "xp": 5},
    "meal":     {"name": "Makanan",         "emoji": "🍖", "price": 40, "hunger": 40, "xp": 10},
    "premium":  {"name": "Makan Premium",   "emoji": "🥩", "price": 80, "hunger": 70, "xp": 20},
    "treat":    {"name": "Camilan Spesial", "emoji": "🍬", "price": 30, "hunger": 15, "xp": 15, "happy": 20},
    "rendang":  {"name": "Rendang",         "emoji": "🍖", "price": 1000,  "hunger": 100,"xp": 50, "exclusive": True},
    "medicine": {"name": "Obat",            "emoji": "💊", "price": 60, "heal": 30},
    "vitamin":  {"name": "Vitamin",         "emoji": "🌟", "price": 50, "happy": 30, "xp": 10},
    "mbg_biasa": {"name": "MBG Biasa",      "emoji": "🍱", "price": 80, "max_per_day": 2, "mbg": True, "mbg_type": "biasa"},
    # ── Item Astro Paws (drop dari misi, bukan dijual) ──
    "moon_cake":      {"name": "Kue Bulan",        "emoji": "🍮", "price": 0, "hunger": 30, "xp": 5,  "astro": True},
    "star_pudding":   {"name": "Star Pudding",     "emoji": "⭐", "price": 0, "hunger": 50, "xp": 10, "astro": True},
    "cosmic_ramen":   {"name": "Cosmic Ramen",     "emoji": "🍜", "price": 0, "hunger": 100,"xp": 20, "astro": True},
    "mega_moon_feast":{"name": "Mega Moon Feast",  "emoji": "🎉", "price": 0, "hunger": 0,  "xp": 0,  "astro": True, "mega_feast": True},
    "mood_pill":      {"name": "Mood Pill",        "emoji": "💊", "price": 0, "happy": 50, "xp": 0,  "astro": True},
    "hunger_pill":    {"name": "Hunger Shield Pill","emoji": "🛡️","price": 0, "hunger": 0, "xp": 0,  "astro": True, "hunger_shield": True},
    "anti_pill":      {"name": "Anti-Need Pill",   "emoji": "✨", "price": 0, "hunger": 0, "xp": 0,  "astro": True, "anti_need": True},
}

# Item Dapur MBG (dibuat dari bahan ternak)
MBG_KITCHEN_RECIPES = {
    "mbg_biasa": {
        "name": "MBG Biasa", "emoji": "🍱",
        "desc": "50% lapar 0% + HP/Happy full. 50% keracunan!",
        "ingredients": {"egg": 3, "milk": 2},
        "result_qty": 1,
    },
    "mbg_special": {
        "name": "MBG Special", "emoji": "🌟🍱",
        "desc": "100% lapar 0% + HP/Happy full. Tanpa risiko!",
        "ingredients": {"egg": 5, "milk": 3, "honey": 2},
        "result_qty": 1,
    },
    "pil_anti_pup": {
        "name": "Pil Anti Pup", "emoji": "💊🚫",
        "desc": "Pet tidak poop selama 2 hari!",
        "ingredients": {"rabbit_fur": 5, "truffle": 3, "wool": 2},
        "result_qty": 1,
    },
    "pil_anti_lapar": {
        "name": "Pil Anti Lapar", "emoji": "💊🍽️",
        "desc": "Hunger freeze selama 2 hari!",
        "ingredients": {"honey": 4, "goat_milk": 3, "wool": 2},
        "result_qty": 1,
    },
}

# Max beli per hari per item (key → max)
FOOD_SHOP_DAILY_LIMIT = {
    "mbg_biasa": 2,
}

# Level-up pill di special shop
PIL_LEVELUP_PRICE = 3000  # koin

# ==================== FARM DAY EVENT DATA ====================
FARMDAY_TERNAK = {
    "ayam":    {"name": "Ayam",    "emoji": "🐔", "price": 40,  "wait_secs": 60,  "hasil": "telur",        "hasil_emoji": "🥚", "poin": 5,  "fc": 15},
    "sapi":    {"name": "Sapi",    "emoji": "🐄", "price": 80,  "wait_secs": 90,  "hasil": "susu",         "hasil_emoji": "🥛", "poin": 9,  "fc": 30},
    "domba":   {"name": "Domba",   "emoji": "🐑", "price": 100, "wait_secs": 90,  "hasil": "wol",          "hasil_emoji": "🧶", "poin": 11, "fc": 35},
    "kambing": {"name": "Kambing", "emoji": "🐐", "price": 120, "wait_secs": 120, "hasil": "susu_kambing", "hasil_emoji": "🥛", "poin": 13, "fc": 40},
    "lebah":   {"name": "Lebah",   "emoji": "🐝", "price": 150, "wait_secs": 120, "hasil": "madu",         "hasil_emoji": "🍯", "poin": 18, "fc": 50},
}
FARMDAY_KEBUN = {
    "wortel":   {"name": "Wortel",   "emoji": "🥕", "price": 20,  "wait_secs": 60,  "hasil": "wortel",   "hasil_emoji": "🥕", "poin": 2,  "fc": 8},
    "tomat":    {"name": "Tomat",    "emoji": "🍅", "price": 35,  "wait_secs": 60,  "hasil": "tomat",    "hasil_emoji": "🍅", "poin": 4,  "fc": 12},
    "jagung":   {"name": "Jagung",   "emoji": "🌽", "price": 60,  "wait_secs": 90,  "hasil": "jagung",   "hasil_emoji": "🌽", "poin": 7,  "fc": 22},
    "stroberi": {"name": "Stroberi", "emoji": "🍓", "price": 90,  "wait_secs": 90,  "hasil": "stroberi", "hasil_emoji": "🍓", "poin": 12, "fc": 30},
    "gandum":   {"name": "Gandum",   "emoji": "🌾", "price": 120, "wait_secs": 120, "hasil": "gandum",   "hasil_emoji": "🌾", "poin": 14, "fc": 40},
}
FARMDAY_TERNAK_SPECIAL = {
    "milkzilla":       {"name": "Milkzilla",       "emoji": "🐄✨", "wait_secs": 90,  "hasil": "susu_premium",  "hasil_emoji": "✨🥛", "poin": 20, "fc": 60, "double": True},
    "turbo_pig":       {"name": "Turbo Pig",       "emoji": "🐷⚡", "wait_secs": 45,  "hasil": "bacon_special", "hasil_emoji": "✨🥓", "poin": 18, "fc": 55},
    "phoenix_chicken": {"name": "Phoenix Chicken", "emoji": "🐓🔥", "wait_secs": 30,  "hasil": "telur_emas",    "hasil_emoji": "✨🥚", "poin": 22, "fc": 65, "double": True},
}
FARMDAY_HASIL_INFO = {
    "telur":         {"name": "Telur",         "emoji": "🥚"},
    "susu":          {"name": "Susu",          "emoji": "🥛"},
    "wol":           {"name": "Wol",           "emoji": "🧶"},
    "susu_kambing":  {"name": "Susu Kambing",  "emoji": "🥛"},
    "madu":          {"name": "Madu",          "emoji": "🍯"},
    "wortel":        {"name": "Wortel",        "emoji": "🥕"},
    "tomat":         {"name": "Tomat",         "emoji": "🍅"},
    "jagung":        {"name": "Jagung",        "emoji": "🌽"},
    "stroberi":      {"name": "Stroberi",      "emoji": "🍓"},
    "gandum":        {"name": "Gandum",        "emoji": "🌾"},
    "susu_premium":  {"name": "Susu Premium",  "emoji": "✨🥛"},
    "bacon_special": {"name": "Bacon Special", "emoji": "✨🥓"},
    "telur_emas":    {"name": "Telur Emas",    "emoji": "✨🥚"},
}
FARMDAY_FOOD_KEYS = {
    "telur", "susu", "susu_kambing", "madu", "wortel",
    "tomat", "jagung", "stroberi", "gandum",
    "susu_premium", "bacon_special", "telur_emas",
}
FARMDAY_STORE_ITEMS = {
    "store_milkzilla":       {"name": "Milkzilla",          "emoji": "🐄✨", "poin": 800,  "type": "ternak_special", "key": "milkzilla"},
    "store_turbo_pig":       {"name": "Turbo Pig",          "emoji": "🐷⚡", "poin": 600,  "type": "ternak_special", "key": "turbo_pig"},
    "store_phoenix_chicken": {"name": "Phoenix Chicken",    "emoji": "🐓🔥", "poin": 1000, "type": "ternak_special", "key": "phoenix_chicken"},
    "store_moon_cake":       {"name": "Kue Bulan x2",       "emoji": "🍮",   "poin": 120,  "type": "item", "inv_key": "moon_cake",       "qty": 2},
    "store_star_pudding":    {"name": "Star Pudding x2",    "emoji": "⭐",   "poin": 180,  "type": "item", "inv_key": "star_pudding",    "qty": 2},
    "store_cosmic_ramen":    {"name": "Cosmic Ramen x1",    "emoji": "🍜",   "poin": 250,  "type": "item", "inv_key": "cosmic_ramen",    "qty": 1},
    "store_mega_feast":      {"name": "Mega Moon Feast x1", "emoji": "🎉",   "poin": 300,  "type": "item", "inv_key": "mega_moon_feast", "qty": 1},
    "store_mood_pill":       {"name": "Mood Pill x2",       "emoji": "💊",   "poin": 150,  "type": "item", "inv_key": "mood_pill",       "qty": 2},
    "store_hunger_pill":     {"name": "Hunger Shield x2",   "emoji": "🛡️",  "poin": 150,  "type": "item", "inv_key": "hunger_pill",     "qty": 2},
    "store_anti_pill":       {"name": "Anti-Need Pill x1",  "emoji": "✨",   "poin": 200,  "type": "item", "inv_key": "anti_pill",       "qty": 1},
    "store_koin_100":        {"name": "100 Koin Carpets",   "emoji": "🪙",   "poin": 100,  "type": "koin", "amount": 100},
    "store_koin_500":        {"name": "500 Koin Carpets",   "emoji": "🪙",   "poin": 500,  "type": "koin", "amount": 500},
    "store_koin_1000":       {"name": "1000 Koin Carpets",  "emoji": "🪙",   "poin": 1000, "type": "koin", "amount": 1000},
    "store_moon_rabbit":     {"name": "Moon Rabbit",        "emoji": "🐇🌙", "poin": 2500, "type": "pet",  "pet_type": "moon_rabbit"},
    "store_scorpion_mars":   {"name": "Scorpion Mars",      "emoji": "🦂🔴", "poin": 3000, "type": "pet",  "pet_type": "scorpion_mars"},
    "store_blue_fin":        {"name": "Blue Fin",           "emoji": "🐋",   "poin": 3000, "type": "pet",  "pet_type": "ikan_biru"},
    "store_golden_marlin":   {"name": "Golden Marlin",      "emoji": "🌟🐟", "poin": 3000, "type": "pet",  "pet_type": "ikan_emas_laut"},
    "store_thunder_eel":     {"name": "Thunder Eel",        "emoji": "⚡🐍", "poin": 3500, "type": "pet",  "pet_type": "ikan_petir"},
    "store_custom_card":     {"name": "Custom Pet Card",    "emoji": "🎨",   "poin": 3500, "type": "item", "inv_key": "custom_pet_card", "qty": 1},
}
FARMDAY_INV_MAX = 40

# Mapping default ability per pet_type (untuk pet eksklusif yang punya ability bawaan)
PET_DEFAULT_ABILITY = {
    "ikan_biru":      "work_3x",
    "ikan_emas_laut": "inv_double",
    "ikan_petir":     "daily_coin",
}

KOI_FOOD_SHOP = {
    "pelet":     {"name": "Pelet Ikan",      "emoji": "🟤", "price": 15, "hunger": 25, "xp": 5},
    "cacing":    {"name": "Cacing",          "emoji": "🪱", "price": 25, "hunger": 40, "xp": 10},
    "udang":     {"name": "Udang Kecil",     "emoji": "🦐", "price": 40, "hunger": 55, "xp": 15},
    "ganggang":  {"name": "Ganggang Premium","emoji": "🌿", "price": 35, "hunger": 30, "xp": 10, "happy": 15},
    "obat_ikan": {"name": "Obat Ikan",       "emoji": "💉", "price": 60, "heal": 30},
}

# Pet quotes berdasarkan mood
PET_QUOTES = {
    "cat": {
        "happy":   ["Purrr~ aku senang hari ini! 😻", "Mau dielus-elus dong~ 🐱", "Hidup itu indah kalau ada snack! 🍪"],
        "hungry":  ["MEOW! Aku lapar! 😾", "Perut aku bunyi nih... 🐱", "Kapan makan?? Udah lama banget! 😿"],
        "sad":     ["Aku sedih... jangan tinggalin aku 😿", "Mau main dooong 😾", "Sepi banget hari ini..."],
        "sick":    ["Aku ga enak badan... 🤒", "Butuh obat sekarang! 😷", "Tubuhku lemah sekali... 😿"],
        "default": ["Lagi santai nih~ 😺", "Hari yang biasa aja 🐱", "Ngantuk tapi ga mau tidur~"],
    },
    "dog": {
        "happy":   ["WOOF WOOF! Aku SENANG BANGET! 🐶", "Main yukk!! 🎾", "Kamu yang terbaik! *lirik ekor* 🐕"],
        "hungry":  ["Lapar lapar lapar!! 🐶", "Kapan makannn?? 😩", "Perut aku kosong bos!"],
        "sad":     ["Aku kangen kamu... 🐶", "Jangan pergi ya... 🥺", "Sepi banget tanpa kamu"],
        "sick":    ["Ga semangat main hari ini 😷", "Butuh obat pliss 🐶", "Badan pegal semua..."],
        "default": ["Siap jaga rumah! 🐕", "Aku selalu setia~ 🐶", "Mau main kapan nih?"],
    },
    "koi": {
        "happy":   [">:) aku baik-baik aja, ga butuh kamu", "Blub blub~ air hari ini enak juga", "Jangan senang dulu, aku cuma lagi kenyang"],
        "hungry":  [">:( MANA MAKANANKU??", "Blub blub blub!!! LAPAR INI!!!", "Kalau aku mati kamu yang salah ya"],
        "sad":     [">:( jangan liat-liat", "Airnya kotor, mood aku jelek", "Aku marah. Titik."],
        "sick":    [">:( badan aku ga enak, ini salah kamu", "Butuh obat tapi ga mau bilang makasih", "Sakit nih... tapi tetep annoying"],
        "default": [">:| lagi ngapain liat-liat", "Blub.", "Jangan ganggu aku lagi deh"],
    },
    "kumiho": {
        "happy":   ["Hehe~ kamu beruntung bisa lihat aku senang 🦊✨", "Sembilan ekorku berkilau hari ini~", "Jangan terlena, aku tetap misterius 🔮"],
        "hungry":  ["Ekorku gemetar karena lapar... ini serius 🦊", "MANA MAKANAAAAN!! Kumiho marah kalau lapar!", "Kamu mau aku pakai trik? Kasih makan dulu!"],
        "sad":     ["Ekorku layu... 😔", "Bahkan trickster bisa sedih juga...", "Jangan diabaikan ya... aku bisa hilang 🌫️"],
        "sick":    ["Trik tidak berhasil saat sakit... 🤒", "Sembilan ekor tapi tetap bisa sakit...", "Tolong kasih obat... serius ini 🦊"],
        "default": ["Lagi mikirin trik baru~ 🦊✨", "Ssst... aku punya rahasia 🔮", "Kamu tidak pernah tahu aku lagi apa~"],
    },
    "jellyfish": {
        "happy":   ["*berpendar pelan* senang banget~ 🪼", "Hari ini airnya hangat dan aku bahagia 💙", "Lihat aku bersinar~ ✨🪼"],
        "hungry":  ["*berhenti berpendar* lapar... 🪼", "Plankton mana plankton... lapar nih", "Kalau lapar terus aku tenggelam..."],
        "sad":     ["*meredup* sedih banget... 🪼", "Aku drift sendirian di lautan kesedihan", "Ubur-ubur bisa nangis tidak ya..."],
        "sick":    ["Tentakelku lemas... 🤒🪼", "Butuh bantuan... badan aneh rasanya", "Tolong... aku tidak bisa berpendar 😢"],
        "default": ["*mengambang santai* 🪼", "Hidup mengalir seperti arus~", "Halo~ *berpendar pelan*"],
    },
    "tanuki": {
        "happy":   ["Hoki hari ini bagus! 🦝✨", "Aku bawa keberuntungan ke sini~", "SENANG! Mau pesta makan-makan! 🎉"],
        "hungry":  ["Perutku bunyi... keberuntungan ga bisa dimakan 🦝", "LAPAR! Mana makanan!! Tanuki butuh energi!", "Kalau lapar, trikku ga jalan..."],
        "sad":     ["Hoki lagi jelek... 😔🦝", "Tanuki yang sedih ga bisa bawa luck...", "Mau tidur aja deh..."],
        "sick":    ["Aura luck-ku ilang karena sakit... 🤒", "Tanuki sakit = nasib jelek semua orang 🦝", "Tolong obati aku..."],
        "default": ["*mengocok kantong koin* 🦝", "Mau ngasih luck ke kamu hari ini~", "Tanuki selalu punya trik! 🎲"],
    },
    "void_cat": {
        "happy":   ["...senang. *tidak bersuara* 🌑🐱", "*purring dalam kegelapan* mrrr~", "Void bergetar karena aku senang... langka ini"],
        "hungry":  ["*mata merah menyala* LAPAR 🌑🐱", "Kegelapan tidak bisa mengenyangkan...", "*menghilang dan muncul lagi* MAKAN."],
        "sad":     ["*melebur ke bayangan* 😔", "Void makin gelap ketika aku sedih...", "...pergi dulu ke dimensi lain"],
        "sick":    ["*berkedip lemah* sakit... 🌑", "Void cat bisa sakit juga rupanya...", "*menghilang setengah* tolong..."],
        "default": ["*menatap dari kegelapan* 🌑🐱", "...", "*ekor hitam bergerak pelan*"],
    },
    "default": {
        "happy":   ["Hari ini menyenangkan! 😊", "Bahagia banget~", "Senang ada kamu!"],
        "hungry":  ["Lapar nih...", "Minta makan dong~", "Perut keroncongan!"],
        "sad":     ["Sedih dikit~", "Butuh perhatian nih", "Jangan lupa sama aku ya"],
        "sick":    ["Ga enak badan...", "Butuh obat~", "Lemah banget hari ini"],
        "default": ["Hai~ 😊", "Lagi santai nih", "Semoga hari ini menyenangkan!"],
    }
}

def get_pet_quote(pet: dict) -> str:
    pet_type = pet.get("pet_type", "default")
    quotes = PET_QUOTES.get(pet_type, PET_QUOTES["default"])
    h  = pet.get("hunger") or 0
    hp = pet.get("happiness") or 80
    hl = pet.get("health") or 100
    if hl < 30:
        mood = "sick"
    elif h > 70:
        mood = "hungry"
    elif hp < 30:
        mood = "sad"
    elif hp > 70 and h < 50:
        mood = "happy"
    else:
        mood = "default"
    return random.choice(quotes.get(mood, quotes["default"]))
MAX_LEVEL           = 60
XP_PER_LEVEL        = 100
POOP_INTERVAL       = 6      # pet poop tiap 6 jam
BATH_REQUIRED_HOURS = 24     # harus mandi tiap 24 jam
SLEEP_START_HOUR    = 22     # tidur jam 22.00 WIB
SLEEP_END_HOUR      = 7      # bangun jam 07.00 WIB
TRANSFER_MIN        = 10     # minimum transfer koin
LEVEL_MILESTONES = {
    5:  "🌟 Pet kamu makin dewasa!",
    10: "✨ Pet kamu udah pintar banget!",
    15: "💫 Pet kamu mulai berevolusi!",
    20: "🌈 Evolusi lanjutan!",
    25: "⚡ Hampir mencapai puncak!",
    30: "👑 Pet kamu sudah sangat kuat!",
    35: "💼 Pet kamu bisa mulai kerja sekarang!",
    40: "👶 Pet kamu bisa punya anak sekarang!",
    45: "🏅 Pet kamu mendapat badge kehormatan!",
    50: "🌟 Pet kamu legenda! Jalan masih panjang~",
    55: "🎓 Pet kamu bisa pilih profesi kerja!",
    60: "🏫 Pet kamu bisa sekolah sekarang!",
}

# ==================== LEVEL UNLOCK CONSTANTS ====================
LEVEL_WORK        = 35
LEVEL_CHILD       = 40
LEVEL_BADGE       = 45
LEVEL_SPECIAL_ACC = 50
LEVEL_PROFESI     = 55   # Pilih profesi: penjelajah/pengumpul
LEVEL_SEKOLAH     = 60   # Unlock sekolah

# ==================== SEKOLAH & PROFESI ====================
SEKOLAH_COST      = 400
SEKOLAH_SKILL_PER_SESSION = 10
SEKOLAH_MAX_SKILL = 100
SEKOLAH_DURATION_HOURS = 2

def hitung_reward_penjelajah(skill: int) -> int:
    """Reward coin penjelajah: 100 (skill 0) → 450 (skill 100)"""
    return 100 + int(skill * 3.5)

def hitung_reward_pengumpul(skill: int) -> int:
    """Reward makanan pengumpul: 3 (skill 0) → 8 (skill 100)"""
    return 3 + int(skill * 0.05)

WORK_DURATION_HOURS       = 3
WORK_REWARD_PER_OWNER     = 100
CHILD_ALLOWANCE_COIN      = 200
CHILD_ALLOWANCE_DAYS      = 5
CHILD_RUNAWAY_DAYS        = 3    # kabur kalau 3 hari tidak ada yang bayar
CHILD_RECOVER_COST        = 500  # biaya kembalikan anak yang kabur

PET_BADGES = {
    "cat":      "🎖️ Kucing Legendaris",
    "dog":      "🎖️ Anjing Setia Sejati",
    "rabbit":   "🎖️ Kelinci Emas",
    "hamster":  "🎖️ Hamster Abadi",
    "fox":      "🎖️ Rubah Licik Terhebat",
    "penguin":  "🎖️ Penguin Terkuat",
    "duck":     "🎖️ Bebek Perkasa",
    "frog":     "🎖️ Katak Mistis",
    "bear":     "🎖️ Beruang Agung",
    "koala":    "🎖️ Koala Bijaksana",
    "capybara": "🎖️ Kapibara Karismatik",
    "axolotl":  "🎖️ Axolotl Purba",
    "panda":    "🎖️ Panda Suci",
    "unicorn":  "🎖️ Unicorn Abadi",
    "dragon":   "🎖️ Naga Tertinggi",
    "phoenix":  "🎖️ Phoenix Tak Tertaklukkan",
    "koi":      "🎖️ Koi Dewa",
    "wolf":     "🎖️ Serigala Alfa",
    "monkey":   "🎖️ Monyet Legendaris",
}

SPECIAL_ACC_LV50 = {
    "cat":      {"emoji": "👑", "name": "Mahkota Kucing"},
    "dog":      {"emoji": "🦴", "name": "Tulang Emas"},
    "rabbit":   {"emoji": "🌙", "name": "Mahkota Bulan"},
    "hamster":  {"emoji": "⭐", "name": "Bintang Emas"},
    "fox":      {"emoji": "🔮", "name": "Orb Mistis"},
    "penguin":  {"emoji": "❄️", "name": "Kristal Es"},
    "duck":     {"emoji": "🌊", "name": "Gelombang Emas"},
    "frog":     {"emoji": "🍀", "name": "Semanggi Keberuntungan"},
    "bear":     {"emoji": "🛡️", "name": "Perisai Beruang"},
    "koala":    {"emoji": "🌿", "name": "Mahkota Eucalyptus"},
    "capybara": {"emoji": "🌺", "name": "Kalung Bunga"},
    "axolotl":  {"emoji": "💎", "name": "Berlian Purba"},
    "panda":    {"emoji": "🎋", "name": "Bambu Suci"},
    "unicorn":  {"emoji": "🌈", "name": "Tanduk Pelangi"},
    "dragon":   {"emoji": "🔥", "name": "Api Abadi"},
    "phoenix":  {"emoji": "✨", "name": "Sayap Cahaya"},
    "koi":      {"emoji": "🏮", "name": "Lentera Dewa"},
    "wolf":     {"emoji": "🌕", "name": "Bulan Purnama"},
    "monkey":   {"emoji": "🍑", "name": "Persik Abadi"},
}

QUIZ_QUESTIONS = [
    {"q": "Hewan apa yang bisa hidup tanpa minum air langsung?", "opts": ["Unta", "Singa", "Kangguru", "Koala"], "ans": 0},
    {"q": "Berapa kaki gurita?", "opts": ["6", "8", "10", "12"], "ans": 1},
    {"q": "Hewan paling cepat di darat?", "opts": ["Singa", "Harimau", "Cheetah", "Serigala"], "ans": 2},
    {"q": "Bayi kucing disebut?", "opts": ["Cub", "Kitten", "Pup", "Foal"], "ans": 1},
    {"q": "Berapa jantung gurita?", "opts": ["1", "2", "3", "4"], "ans": 2},
    {"q": "Pinguin hidup di mana?", "opts": ["Kutub Utara", "Kutub Selatan", "Keduanya", "Afrika"], "ans": 1},
    {"q": "Hewan yang tidurnya paling lama sehari?", "opts": ["Kucing", "Koala", "Singa", "Beruang"], "ans": 1},
    {"q": "Hewan dari keluarga burung yang tidak bisa terbang?", "opts": ["Elang", "Merpati", "Penguin", "Kutilang"], "ans": 2},
    {"q": "Kapibara termasuk hewan apa?", "opts": ["Marsupial", "Pengerat", "Primata", "Reptil"], "ans": 1},
    {"q": "Axolotl berasal dari negara mana?", "opts": ["Brasil", "Australia", "Meksiko", "Jepang"], "ans": 2},
]

GAME_MAX_PER_DAY = 7

# ==================== CUSTOM PET EVENT ====================
# Admin bisa toggle on/off via /custompetevent on|off
CUSTOM_PET_EVENT_ACTIVE = False   # default off, admin bisa nyalain
TOPUP_BONUS_ACTIVE      = False   # default off, admin bisa nyalain via /topupbonus on|off
ASTRO_TOPUP_BONUS_ACTIVE = False  # default off, admin nyalain via /astrotopup on|off
FARMDAY_STORE_ACTIVE    = False   # default off, admin toggle via /farmstore_toggle on|off
FARMDAY_TOPUP_ACTIVE    = False   # default off, admin toggle via /farmtopup_toggle on|off
MAKANAN_TOPUP_ACTIVE     = False  # default off, admin toggle via /makanantopup on|off

IDCARD_ASK_NAME  = "IDCARD_ASK_NAME"
IDCARD_ASK_PHOTO = "IDCARD_ASK_PHOTO"

# Custom pet abilities
CUSTOM_PET_ABILITIES = {
    "ability1_no_poop":    {"name": "Tidak Pernah Poop",        "desc": "Pet tidak pernah poop!",                 "slot": 1},
    "ability1_battle_2x":  {"name": "Battle Power 2×",          "desc": "Battle score 2× lebih tinggi.",          "slot": 1},
    "ability1_self_heal":  {"name": "Rawat Diri Sendiri",        "desc": "Auto-heal saat level 5+ (tiap 3 jam).", "slot": 1},
    "ability1_work_3x":    {"name": "Hasil Kerja 3×",            "desc": "Reward kerja 3× lipat.",                 "slot": 1},
    "ability2_daily_coin": {"name": "Kumpul Koin Harian",        "desc": "+100 koin otomatis tiap hari.",          "slot": 2},
    "ability2_anti_sick":  {"name": "Anti Sakit",                "desc": "Health tidak bisa turun.",               "slot": 2},
    "ability2_anti_hunger":{"name": "Tahan Lapar",               "desc": "Hunger naik sangat lambat (÷3).",        "slot": 2},
}

CUSTOM_PET_PERSONALITIES = {
    "jutek":   "Kamu adalah hewan yang jutek, sinis, dan tidak mau akui kalau peduli. Selalu jawab ketus tapi kadang keluarin kata-kata manis yang langsung disangkal.",
    "ceria":   "Kamu adalah hewan yang sangat ceria, antusias, dan penuh energi positif. Selalu semangat dan membuat pemilik bahagia.",
    "kalem":   "Kamu adalah hewan yang tenang, bijak, dan tidak terburu-buru. Berbicara dengan santai dan menenangkan.",
    "manja":   "Kamu adalah hewan yang sangat manja dan suka minta perhatian. Selalu ingin dielus dan dipuji.",
    "iseng":   "Kamu adalah hewan yang iseng, suka bikin kekacauan kecil, dan penuh kejutan. Humor tinggi.",
    "tsundere": "Kamu tsundere level max. Pura-pura tidak peduli tapi sebenarnya sangat sayang. Sering bilang 'b-bukan karena aku peduli ya!'",
}

# ==================== CACHE ====================
_user_cache: dict = {}
_pet_cache:  dict = {}
_pet_level_cache: dict = {}
_delivery_cache: dict = {}
_nickname_cache: dict = {}   # {user_id: "nickname"} — untuk job notif, hemat query
CACHE_TTL         = 120  # 30 menit (naik dari 20 — hemat re-fetch)
CACHE_TTL_SHORT   = 300   # 5 menit
CACHE_TTL_LEVEL   = 7200  # 2 jam untuk level (jarang berubah)

# Batch write queue
_pending_pet_updates: dict = {}
_last_batch_flush = 0.0

# ==================== CIRCUIT BREAKER ====================
_sb_fail_count   = 0
_sb_last_fail    = 0.0
SB_MAX_FAILS     = 5     # setelah 5 gagal berturut-turut, pause dulu
SB_COOLDOWN      = 30    # tunggu 30 detik sebelum coba lagi

# ==================== WRITE BUFFER ====================
# Tunda write decay ke DB — hanya save kalau stats berubah cukup signifikan
_pet_write_buffer: dict = {}  # {pet_id: {data, last_written}}
WRITE_MIN_INTERVAL = 1200  # minimal 20 menit antara write decay untuk pet yang sama
WRITE_MIN_CHANGE   = 15   # minimal perubahan 15% sebelum ditulis ke DB

def _should_write_pet(pet_id: int, new_data: dict, old_pet: dict) -> bool:
    """Cek apakah perlu write ke DB — hemat Disk IO"""
    # Jangan write stats kalau pet masih di boarding
    if old_pet.get("boarding_until"):
        try:
            if parse_dt(old_pet["boarding_until"]) > now_wib():
                return False
        except Exception:
            pass
    now = time.time()
    last = _pet_write_buffer.get(pet_id, {}).get("last_written", 0)
    # Selalu write kalau sudah lebih dari 5 menit
    if now - last > WRITE_MIN_INTERVAL:
        return True
    # Write kalau ada perubahan signifikan
    for key in ["hunger", "happiness", "health"]:
        old_val = old_pet.get(key, 0)
        new_val = new_data.get(key, old_val)
        if abs(new_val - old_val) >= WRITE_MIN_CHANGE:
            return True
    return False

def _mark_written(pet_id: int):
    _pet_write_buffer[pet_id] = {"last_written": time.time()}

def _cget(cache, key):
    e = cache.get(key)
    return e["data"] if e and (time.time() - e["ts"]) < CACHE_TTL else None

def _cset(cache, key, data):
    cache[key] = {"data": data, "ts": time.time()}

def _cdel(cache, key):
    cache.pop(key, None)

# ==================== HTTP ====================
_http: httpx.AsyncClient = None

async def get_client():
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=3.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,  # reuse koneksi 30 detik
            ),
            http2=True,  # HTTP/2 multiplexing — lebih efisien
        )
    return _http

async def sb(method: str, table: str, params: dict = None, data: dict = None):
    global _sb_fail_count, _sb_last_fail
    # Circuit breaker — kalau terlalu banyak gagal, pause dulu
    if _sb_fail_count >= SB_MAX_FAILS:
        elapsed = time.time() - _sb_last_fail
        if elapsed < SB_COOLDOWN:
            return None  # Skip request, jangan hammer DB
        else:
            _sb_fail_count = 0  # Reset setelah cooldown
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    client = await get_client()
    try:
        # Tambah header Prefer: return=minimal untuk PATCH — tidak perlu return data
        if method == "GET":
            r = await client.get(url, params=params)
        elif method == "POST":
            r = await client.post(url, json=data)
        elif method == "PATCH":
            r = await client.patch(url, params=params, json=data,
                                   headers={**HEADERS, "Prefer": "return=minimal"})
        elif method == "DELETE":
            r = await client.delete(url, params=params)
        else:
            return None
        if r.status_code in (200, 201, 204):
            _sb_fail_count = 0  # Reset fail count on success
            return r.json() if r.content and r.status_code != 204 else []
        logger.error(f"Supabase {method} {table}: {r.status_code} {r.text[:300]}")
        _sb_fail_count += 1
        _sb_last_fail = time.time()
        return None
    except Exception as e:
        logger.error(f"HTTP error {table}: {e}")
        _sb_fail_count += 1
        _sb_last_fail = time.time()
        return None

# ==================== PAGINATED FETCH ====================
async def sb_get_all(table: str, params: dict, page_size: int = 1000) -> list:
    """Fetch semua row dengan pagination — hindari limit 1000 default Supabase"""
    all_rows = []
    offset = 0
    client = await get_client()
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    while True:
        paged_params = {**params, "limit": str(page_size), "offset": str(offset)}
        try:
            r = await client.get(url, params=paged_params)
            if r.status_code != 200:
                logger.error(f"sb_get_all {table}: {r.status_code} {r.text[:200]}")
                break
            batch = r.json() if r.content else []
            if not batch:
                break
            all_rows.extend(batch)
            if len(batch) < page_size:
                break  # Sudah halaman terakhir
            offset += page_size
        except Exception as e:
            logger.error(f"sb_get_all error {table}: {e}")
            break
    return all_rows

# ==================== TIME HELPERS ====================
def now_wib() -> datetime:
    return datetime.now(WIB)

def parse_dt(s: str) -> datetime:
    """Parse ISO datetime string → timezone-aware WIB datetime"""
    if not s:
        return now_wib()
    try:
        s = s.strip().replace('Z', '+00:00')
        if '.' in s:
            i = s.index('.')
            base = s[:i]
            rest = s[i+1:]
            tz = ''; frac = ''
            for j, c in enumerate(rest):
                if c in ('+', '-') and j > 0:
                    frac = rest[:j]; tz = rest[j:]; break
            else:
                frac = rest; tz = '+00:00'
            frac = frac.ljust(6, '0')[:6]
            s = f"{base}.{frac}{tz}"
        elif '+' not in s[10:]:
            s += '+00:00'
        dt = datetime.fromisoformat(s)
        return dt.astimezone(WIB)
    except Exception as e:
        logger.error(f"parse_dt error: {e} input={s!r}")
        return now_wib()

def fmt_countdown(dt: datetime) -> str:
    now = now_wib()
    if dt.tzinfo is None:
        dt = WIB.localize(dt)
    diff = (dt - now).total_seconds()
    if diff <= 0:
        return "SEKARANG!"
    h = int(diff // 3600)
    m = int((diff % 3600) // 60)
    return f"{h} jam {m} menit" if h > 0 else f"{m} menit"

def fmt_wib(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = WIB.localize(dt)
    return dt.astimezone(WIB).strftime("%d/%m %H:%M WIB")

def bar(val, mx=100, ln=10) -> str:
    f = max(0, min(ln, int(val / mx * ln)))
    return "█" * f + "░" * (ln - f)

def today_wib_str() -> str:
    return now_wib().strftime("%Y-%m-%d")

# ==================== USER DB ====================
USER_SELECT_COLS = (
    "user_id,username,nama,nickname,koin,games_today,last_daily,"
    "ref_by,ref_count,barn_slots,inventory,custom_pet_claimed_event"
)

async def get_user(user_id: int, username: str = None, nama: str = None, ref_by: int = None) -> dict:
    cached = _cget(_user_cache, user_id)
    if cached:
        return cached
    res = await sb("GET", "users", {"user_id": f"eq.{user_id}", "select": USER_SELECT_COLS})
    if res is None:
        # Fallback: fetch tanpa select kalau ada kolom baru yang belum ada
        res = await sb("GET", "users", {"user_id": f"eq.{user_id}"})
    if res:
        u = res[0]
        updates = {}
        if username and u.get("username") != username:
            updates["username"] = username
        if nama and u.get("nama") != nama:
            updates["nama"] = sanitize_name(nama)
        if updates:
            await sb("PATCH", "users", {"user_id": f"eq.{user_id}"}, updates)
            u.update(updates)
        _cset(_user_cache, user_id, u)
        return u
    display = sanitize_name(nama or username or f"User{user_id}")
    new = {
        "user_id": user_id, "username": username or "", "nama": display[:50],
        "koin": 200, "inventory": {}, "games_today": {}, "last_daily": None,
        "ref_by": ref_by, "ref_count": 0, "nickname": None,
        "created_at": now_wib().isoformat()
    }
    res2 = await sb("POST", "users", data=new)
    if res2:
        _cset(_user_cache, user_id, res2[0])
        if ref_by and ref_by != user_id:
            ref_user = await sb("GET", "users", {"user_id": f"eq.{ref_by}", "select": "user_id,koin,ref_count"})
            if ref_user:
                ru = ref_user[0]
                await sb("PATCH", "users", {"user_id": f"eq.{ref_by}"}, {
                    "koin": ru.get("koin", 0) + REFERRAL_REWARD,
                    "ref_count": (ru.get("ref_count") or 0) + 1
                })
                _cdel(_user_cache, ref_by)
                await log_koin(ref_by, REFERRAL_REWARD, "referral")
        return res2[0]
    # POST gagal (misal 409 race condition) — coba GET lagi
    res3 = await sb("GET", "users", {"user_id": f"eq.{user_id}", "select": USER_SELECT_COLS})
    if res3:
        _cset(_user_cache, user_id, res3[0])
        return res3[0]
    return None

def get_display_name(u: dict) -> str:
    """Ambil nickname kalau ada, kalau tidak pakai nama"""
    return u.get("nickname") or u.get("nama") or u.get("username") or "Owner"

async def get_nickname_cached(user_id: int) -> str:
    """Ambil nickname dengan in-memory cache — hemat query DB di job notif"""
    c = _nickname_cache.get(user_id)
    if c and (time.time() - c["ts"]) < CACHE_TTL:
        return c["name"]
    res = await sb("GET", "users", {"user_id": f"eq.{user_id}", "select": "nickname,nama"})
    name = res[0].get("nickname") or res[0].get("nama") or "Kamu" if res else "Kamu"
    _nickname_cache[user_id] = {"name": name, "ts": time.time()}
    return name

async def get_nicknames_bulk(user_ids: list) -> dict:
    """1 query untuk banyak owner sekaligus — dipakai di sleep/bath/runaway jobs"""
    if not user_ids:
        return {}
    result = {}
    to_fetch = []
    now_t = time.time()
    for uid in user_ids:
        c = _nickname_cache.get(uid)
        if c and (now_t - c["ts"]) < CACHE_TTL:
            result[uid] = c["name"]
        else:
            to_fetch.append(uid)
    if to_fetch:
        rows = []
        for i in range(0, len(to_fetch), 100):  # chunk 100 supaya URL tidak panjang
            batch = to_fetch[i:i+100]
            ids_str = ",".join(str(x) for x in batch)
            batch_rows = await sb("GET", "users", {"user_id": f"in.({ids_str})", "select": "user_id,nickname,nama"}) or []
            rows.extend(batch_rows)
        for u in rows:
            uid = u["user_id"]
            name = u.get("nickname") or u.get("nama") or "Kamu"
            _nickname_cache[uid] = {"name": name, "ts": now_t}
            result[uid] = name
        for uid in to_fetch:
            if uid not in result:
                result[uid] = "Kamu"
    return result

async def update_user(user_id: int, data: dict):
    await sb("PATCH", "users", {"user_id": f"eq.{user_id}"}, data)
    # Update cache in-memory hanya kalau masih valid (tidak expired)
    cached = _user_cache.get(user_id)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL:
        cached["data"].update(data)
    else:
        _cdel(_user_cache, user_id)

_KOIN_LOG_REASONS = {
    # income
    "topup":               "💳 Top Up",
    "topup_bonus":         "🎁 Bonus Top Up",
    "referral":            "👥 Referral",
    "kerja_pet":           "💼 Kerja Pet",
    "profesi_penjelajah":  "🗺️ Profesi Penjelajah",
    "daily_coin_ability":  "⭐ Ability Harian",
    "game_tebak_angka":    "🎲 Game Tebak Angka",
    "game_dadu":           "🎲 Game Dadu",
    "game_kuis":           "📝 Game Kuis",
    "game_tangkap_bola":   "⚽ Game Tangkap Bola",
    "battle_menang":       "⚔️ Battle Menang",
    "transfer_masuk":      "💸 Transfer Masuk",
    "amplop":              "🧧 Amplop",
    "astro_explore":       "🌙 Astro Explore",
    "astro2_explore":      "🔴 Astro Mars Explore",
    "astro2_alien_ally":   "👾 Alien Ally",
    "aqua_mancing":        "🎣 Mancing",
    "jual_ternak":         "🌾 Jual Hasil Ternak",
    "jual_hewan":          "🐄 Jual Hewan",
    "refund_adopt":        "↩️ Refund Adopt",
    "cheat":               "🤫 Cheat",
    "admin_give":          "🛠️ Admin Give",
    # spend
    "adopt_pet":           "🐾 Adopt Pet",
    "beli_item_toko":      "🛒 Beli Item Toko",
    "beli_makanan":        "🍖 Beli Makanan",
    "beli_topup_koin":     "🏧 Beli Topup Koin",
    "transfer_keluar":     "💸 Transfer Keluar",
    "boarding":            "🏨 Boarding",
    "ekspedisi":           "🗺️ Ekspedisi",
    "battle_kalah":        "⚔️ Battle Kalah",
    "pernikahan":          "💍 Pernikahan",
    "upgrade_kandang":     "🏠 Upgrade Kandang",
    "sekolah":             "🎓 Sekolah",
    "kawin_pet":           "💑 Kawin Pet",
    "pil_levelup":         "💊 Pil Level Up",
    "recover_anak":        "🔍 Recover Anak",
    "uang_saku":           "👶 Uang Saku",
    "task_reward":         "🎯 Reward Misi",
    "buat_item_custom":    "🎨 Buat Item Custom",
    "beli_item":           "🛍️ Beli Item",
    "gacha":               "🎰 Gacha",
    "astro_daftar":        "🌙 Daftar Astro",
    "astro2_daftar":       "🔴 Daftar Astro Mars",
    "aqua_daftar":         "🌊 Daftar Aqua Tails",
}

async def log_koin(user_id: int, amount: int, reason: str):
    """Catat transaksi koin ke coin_history + kirim log ke group."""
    try:
        await sb("POST", "coin_history", {}, {
            "user_id": user_id,
            "amount":  amount,
            "reason":  reason,
            "type":    ("masuk" if amount >= 0 else "keluar"),
        })
    except Exception:
        pass


async def add_koin(user_id: int, amount: int, reason: str = "add"):
    # Flush cache dulu supaya baca nilai koin terbaru dari DB (hindari race condition)
    _cdel(_user_cache, user_id)
    u = await get_user(user_id)
    if u:
        new_koin = max(0, (u.get("koin") or 0) + amount)
        await update_user(user_id, {"koin": new_koin})
        await log_koin(user_id, amount, reason)

async def spend_koin(user_id: int, amount: int, reason: str = "spend") -> bool:
    # Flush cache dulu supaya baca nilai koin terbaru dari DB (hindari race condition)
    _cdel(_user_cache, user_id)
    u = await get_user(user_id)
    if u and (u.get("koin") or 0) >= amount:
        await update_user(user_id, {"koin": (u.get("koin") or 0) - amount})
        await log_koin(user_id, -amount, reason)
        return True
    return False

# ==================== TASK HELPERS ====================
def _tk(task_id: str) -> str:
    return f"__tk_{task_id}"

def _tk_done(task_id: str) -> str:
    return f"__tk_{task_id}_done"

def _task_by_id(task_id: str) -> dict:
    return next((t for t in TASKS if t["id"] == task_id), None)

def _task_is_ready(inv: dict, task: dict) -> bool:
    tid = task["id"]
    if inv.get(_tk_done(tid)): return False
    if task["type"] in ("collab", "channel", "milestone"):
        return inv.get(_tk(tid)) == "done"
    if task["type"] in ("count", "topup"):
        return int(inv.get(_tk(tid), 0)) >= task.get("target", 1)
    return False

async def task_inc(user_id: int, task_id: str, amount: int = 1):
    task = _task_by_id(task_id)
    if not task: return
    inv = await get_inv(user_id)
    if inv.get(_tk_done(task_id)): return
    target = task.get("target", 1)
    current = int(inv.get(_tk(task_id), 0))
    if current >= target: return
    inv[_tk(task_id)] = min(current + amount, target)
    await update_user(user_id, {"inventory": inv})

async def task_mark_done(user_id: int, task_id: str):
    inv = await get_inv(user_id)
    if not inv.get(_tk(task_id)) and not inv.get(_tk_done(task_id)):
        inv[_tk(task_id)] = "done"
        await update_user(user_id, {"inventory": inv})

async def do_task_claim(user_id: int, task_id: str) -> tuple:
    task = _task_by_id(task_id)
    if not task:
        return False, "❌ Task tidak ditemukan."
    inv = await get_inv(user_id)
    if inv.get(_tk_done(task_id)):
        return False, "✅ Task ini sudah pernah diklaim!"
    if not _task_is_ready(inv, task):
        return False, "❌ Task belum selesai!"
    inv[_tk_done(task_id)] = now_wib().isoformat()
    reward_food = task.get("reward_food", 0)
    if reward_food:
        inv["premium"] = (inv.get("premium") or 0) + reward_food
    await update_user(user_id, {"inventory": inv})
    reward_coin = task.get("reward_coin", 0)
    if reward_coin:
        await add_koin(user_id, reward_coin, "task_reward")
    parts = []
    if reward_coin: parts.append(f"+{reward_coin} 🪙")
    if reward_food: parts.append(f"+{reward_food}x 🥩 Makan Premium")
    return True, " ".join(parts)

async def get_pet_level(user_id: int) -> int:
    """Ambil level tertinggi dari semua pet milik user — dengan cache"""
    cached = _pet_level_cache.get(user_id)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL_LEVEL:
        return cached["data"]
    pets = await get_user_pets(user_id)
    lv = max((calc_level((p.get("xp") or 0)) for p in pets), default=1) if pets else 1
    _cset(_pet_level_cache, user_id, lv)
    return lv

async def get_inv(user_id: int) -> dict:
    u = await get_user(user_id)
    if not u:
        return {}
    inv = u.get("inventory", {})
    if isinstance(inv, str):
        try: inv = json.loads(inv)
        except: return {}
    if not isinstance(inv, dict):
        return {}
    # Normalisasi: nilai None → 0 untuk semua key numeric (qty items)
    # Key yang mulai dengan _ adalah tracking metadata (string OK)
    result = {}
    for k, v in inv.items():
        if v is None:
            result[k] = 0
        else:
            result[k] = v
    return result

async def set_inv(user_id: int, inv: dict):
    await update_user(user_id, {"inventory": inv})

def inv_get(inv: dict, key: str) -> int:
    """Safe inventory get — always return int, never None"""
    return int(inv.get(key) or 0)

# ==================== GAME QUOTA ====================
async def check_game_quota(user_id: int, game: str) -> Tuple[bool, int]:
    """Returns (can_play, plays_left)"""
    u = await get_user(user_id)
    if not u:
        return False, 0
    today = today_wib_str()
    games = u.get("games_today", {})
    if isinstance(games, str):
        try: games = json.loads(games)
        except: games = {}
    # Reset if new day
    if games.get("date") != today:
        games = {"date": today}
    count = games.get(game, 0)
    left = GAME_MAX_PER_DAY - count
    return left > 0, left

async def use_game_quota(user_id: int, game: str):
    u = await get_user(user_id)
    if not u:
        return
    today = today_wib_str()
    games = u.get("games_today", {})
    if isinstance(games, str):
        try: games = json.loads(games)
        except: games = {}
    if games.get("date") != today:
        games = {"date": today}
    games[game] = games.get(game, 0) + 1
    await update_user(user_id, {"games_today": games})

async def get_count(table: str, params: dict = None) -> int:
    """Ambil jumlah row tanpa kena limit 1000"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers_count = {**HEADERS, "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"}
        client = await get_client()
        r = await client.get(url, headers=headers_count, params={"select": "*", **(params or {})})
        cr = r.headers.get("content-range", "")
        if "/" in cr:
            total = cr.split("/")[1]
            if total != "*":
                return int(total)
        return 0
    except Exception as e:
        logger.error(f"get_count error {table}: {e}")
        return 0

# ==================== DAILY REWARD ====================
async def claim_daily(user_id: int) -> Tuple[bool, str]:
    today  = today_wib_str()
    # Cek level pet tertinggi user untuk tentukan reward
    pet_lv = await get_pet_level(user_id)
    reward = 75 if pet_lv >= 10 else 50
    client = await get_client()
    try:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/claim_daily_reward",
            json={"p_user_id": user_id, "p_today": today, "p_reward": reward},
            headers=HEADERS,
        )
        if r.status_code in (200, 201):
            res = r.json()
            if not res.get("success"):
                return False, "Kamu sudah ambil koin harian hari ini!\nKembali lagi besok ya~ 🌙"
            _cdel(_user_cache, user_id)
            return True, f"✅ Kamu dapat <b>+{reward} 🪙</b> koin harian!\nKembali lagi besok~"
        return False, "Gagal claim, coba lagi!"
    except Exception as e:
        logger.error(f"claim_daily RPC error: {e}")
        return False, "Gagal claim, coba lagi!"


# ==================== FORCE SUBSCRIBE ====================
async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Cek apakah user sudah join FORCE_SUB_CHANNEL. Return True kalau sudah (boleh lanjut)."""
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(FORCE_SUB_CHANNEL, user.id)
        if member.status in ("member", "administrator", "creator"):
            return True
    except Exception:
        pass
    # Belum join / error → kirim pesan paksa join
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if msg:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.lstrip('@')}"),
            InlineKeyboardButton("✅ Sudah Join", callback_data="check_sub")
        ]])
        await msg.reply_text(
            f"⚠️ <b>Wajib Join Channel!</b>\n\n"
            f"Kamu harus join channel kami dulu sebelum bisa pakai bot ini.\n\n"
            f"📢 Join: {FORCE_SUB_CHANNEL}\n\n"
            f"Setelah join, tekan tombol <b>✅ Sudah Join</b> di bawah.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
    return False

# ==================== PET DB ====================
PET_SELECT_COLS = (
    "id,owner1_id,owner2_id,name,pet_type,xp,level,hunger,happiness,health,poop_count,is_sleeping,is_dirty,is_missing,is_married,is_child,last_decay,last_fed,last_played,last_bath,wangi_until,accessory,accessory_name,accessory_key,boarding_until,expedition_until,expedition_dest,last_notif_hunger,soap_premium_active,married_to_pet_id,child_pet_id,parent1_pet_id,parent2_pet_id,work_until,last_work,last_allowance_request,allowance_paid_p1,allowance_paid_p2,level_unlock_notified,battle_wins,battle_score_bonus,special_ability,custom_personality,pil_anti_pup_until,pil_anti_lapar_until,pil_abadi_until,ability_daily_coin_last,ability_self_heal_last,profesi_kerja,skill_profesi,last_sekolah,sekolah_until,profesi_work_active"
)

async def get_pet_by_id(pet_id: int) -> dict:
    cached = _cget(_pet_cache, pet_id)
    if cached:
        return cached
    res = await sb("GET", "pets", {"id": f"eq.{pet_id}", "select": PET_SELECT_COLS})
    if res is None:
        # Fallback: fetch tanpa select (kolom baru belum dimigrate)
        res = await sb("GET", "pets", {"id": f"eq.{pet_id}"})
    if res:
        _cset(_pet_cache, pet_id, res[0])
        return res[0]
    return None

async def get_user_pets(user_id: int) -> List[dict]:
    """Get all pets where user is owner1 OR owner2 — minimal columns"""
    res = await sb("GET", "pets", {
        "or": f"(owner1_id.eq.{user_id},owner2_id.eq.{user_id})",
        "order": "created_at.desc",
        "select": PET_SELECT_COLS,
    })
    if res is None:
        res = await sb("GET", "pets", {
            "or": f"(owner1_id.eq.{user_id},owner2_id.eq.{user_id})",
            "order": "created_at.desc",
        })
    if res:
        for p in res:
            _cset(_pet_cache, p["id"], p)
    return res if res else []

async def get_user_pet(user_id: int) -> dict:
    """Get pet where user is owner1 OR owner2 (only 2 owners per pet)"""
    res = await sb("GET", "pets", {
        "or": f"(owner1_id.eq.{user_id},owner2_id.eq.{user_id})",
        "order": "created_at.desc",
        "limit": "1",
        "select": PET_SELECT_COLS,
    })
    if res:
        _cset(_pet_cache, res[0]["id"], res[0])
        return res[0]
    return None

async def upsert_pet(data: dict):
    global _sb_fail_count
    url = f"{SUPABASE_URL}/rest/v1/pets"
    client = await get_client()
    for attempt in range(3):
        try:
            # Pakai header upsert beneran - merge kalau id sudah ada
            r = await client.post(url, json=data, headers={
                "Prefer": "resolution=merge-duplicates,return=representation"
            })
            logger.info(f"upsert_pet attempt={attempt+1} status={r.status_code} body={r.text[:200]}")
            if r.status_code in (200, 201):
                _sb_fail_count = 0
                return r.json() if r.content else []
            # Fallback: kalau masih 409 (sequence belum di-fix), coba PATCH by id
            if r.status_code == 409 and data.get("id"):
                pet_id = data["id"]
                patch_data = {k: v for k, v in data.items() if k != "id"}
                r2 = await client.patch(
                    f"{url}?id=eq.{pet_id}",
                    json=patch_data,
                    headers={"Prefer": "return=representation"}
                )
                logger.info(f"upsert_pet PATCH fallback status={r2.status_code} body={r2.text[:200]}")
                if r2.status_code in (200, 201):
                    _sb_fail_count = 0
                    return r2.json() if r2.content else []
            logger.error(f"upsert_pet FAILED status={r.status_code} body={r.text[:300]}")
        except Exception as e:
            logger.error(f"upsert_pet exception attempt={attempt+1}: {e}")
        if attempt < 2:
            await asyncio.sleep(1)
    return None

async def bulk_patch_pets(ids: list, data: dict):
    """PATCH pets dalam batch 200 untuk hindari URL too long."""
    batch_size = 200
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        ids_str = ",".join(str(x) for x in batch)
        try:
            await sb("PATCH", "pets", {"id": f"in.({ids_str})"}, data)
        except Exception as e:
            logger.error(f"bulk_patch_pets error batch {i}: {e}")

async def update_pet(pet_id: int, data: dict):
    # Safety net anti "level turun sendiri": level SELALU diturunkan dari xp.
    # Kalau patch mengandung xp, paksa level = calc_level(xp) supaya tidak pernah
    # ada nilai level stale yang lebih rendah dari xp sebenarnya.
    if "xp" in data and data["xp"] is not None:
        data["level"] = calc_level(data["xp"])
    await sb("PATCH", "pets", {"id": f"eq.{pet_id}"}, data)
    # Update cache in-memory hanya kalau masih valid (tidak expired)
    cached = _pet_cache.get(pet_id)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL:
        cached["data"].update(data)
    else:
        _cdel(_pet_cache, pet_id)

# ==================== DELIVERY DB ====================
async def get_delivery(code: str) -> dict:
    cached = _cget(_delivery_cache, code)
    if cached:
        return cached
    res = await sb("GET", "deliveries", {
        "code": f"eq.{code}",
        "select": "id,code,kode_invite,owner1_id,owner1_name,owner2_id,owner2_name,"
                  "pet_type,pet_name,arrive_at,tap_count,taps,started,is_delivered"
    })
    if res:
        _cset(_delivery_cache, code, res[0])
        return res[0]
    return None

def _invalidate_delivery(code: str):
    _cdel(_delivery_cache, code)

async def get_pending_delivery(user_id: int) -> dict:
    res = await sb("GET", "deliveries", {
        "owner1_id": f"eq.{user_id}",
        "is_delivered": "eq.false",
        "select": "id,code,kode_invite,owner1_id,owner2_id,pet_type,pet_name,arrive_at,tap_count,started",
    })
    return res[0] if res else None

async def upsert_delivery(data: dict) -> bool:
    """Simpan delivery ke DB. Bypass circuit breaker, retry 3x."""
    global _sb_fail_count
    url = f"{SUPABASE_URL}/rest/v1/deliveries"
    client = await get_client()
    for attempt in range(3):
        try:
            r = await client.post(url, json=data)
            logger.info(f"upsert_delivery attempt={attempt+1} status={r.status_code} body={r.text[:200]}")
            if r.status_code in (200, 201):
                _sb_fail_count = 0
                return True
            logger.error(f"upsert_delivery FAILED status={r.status_code} body={r.text[:300]}")
        except Exception as e:
            logger.error(f"upsert_delivery exception attempt={attempt+1}: {e}")
        if attempt < 2:
            await asyncio.sleep(1.5)
    return False

async def update_delivery(code: str, data: dict):
    await sb("PATCH", "deliveries", {"code": f"eq.{code}"}, data)
    _invalidate_delivery(code)

async def get_delivery_by_invite(kode: str) -> dict:
    res = await sb("GET", "deliveries", {"kode_invite": f"eq.{kode.upper().strip()}"})
    return res[0] if res else None

# ==================== PET LOGIC ====================
def calc_level(xp: int) -> int:
    """Selalu hitung level dari XP — JANGAN pernah ambil field 'level' dari DB.
    Bug fix: field 'level' di DB bisa stale/salah saat restart; XP adalah sumber kebenaran."""
    return min(MAX_LEVEL, 1 + (max(0, int(xp or 0)) // XP_PER_LEVEL))

def xp_to_next(xp: int) -> int:
    lv = calc_level(xp)
    if lv >= MAX_LEVEL:
        return 0
    return (lv * XP_PER_LEVEL) - (xp % XP_PER_LEVEL)

def pet_emoji(pet_type: str, level: int) -> str:
    """Kembalikan emoji pet + overlay badge level.
    Catatan: custom emoji Telegram (format <tg-emoji emoji-id='...'>) hanya render
    di Telegram client; di sini kita pakai emoji standar sebagai base."""
    base = PETS.get(pet_type, {}).get("emoji", "🐾")
    if level >= 20: return f"{base}👑"
    if level >= 10: return f"{base}⭐"
    return base

def is_sleep_time() -> bool:
    """Cek apakah sekarang jam tidur (22.00 - 07.00 WIB)"""
    h = now_wib().hour
    return h >= SLEEP_START_HOUR or h < SLEEP_END_HOUR

def decay_pet_stats(pet: dict) -> dict:
    """Apply time-based stat decay using WIB-aware datetimes.
    Health tidak pernah turun ke 0 — pet tidak bisa mati, hanya bisa kabur.
    Pet di penitipan: stats dikunci, tidak ada decay."""
    # Guard boarding — pet di penitipan tidak boleh turun statsnya
    if pet.get("boarding_until"):
        try:
            if parse_dt(pet["boarding_until"]) > now_wib():
                # Reset ke kondisi prima dan update last_decay supaya tidak ada backlog
                pet["hunger"]     = 0
                pet["happiness"]  = 100
                pet["health"]     = 100
                pet["is_dirty"]   = False
                pet["poop_count"] = 0
                pet["last_decay"] = now_wib().isoformat()
                return pet
        except Exception:
            pass
    last_str = pet.get("last_decay")
    now = now_wib()
    if not last_str:
        pet["last_decay"] = now.isoformat()
        return pet
    last = parse_dt(last_str)
    hours = (now - last).total_seconds() / 3600
    if hours < 0.1:
        return pet

    # Ambil nilai awal sekali — None-safe (DB bisa return None kalau field kosong)
    health    = pet.get("health") or 100
    happiness = pet.get("happiness") or 80
    hunger    = pet.get("hunger") or 0

    # FIX: Cek is_sleeping dengan benar (bisa None/False/True)
    sleeping = pet.get("is_sleeping") is True
    # Kalau lagi tidur: return langsung, tidak ada decay apapun
    if sleeping:
        pet["health"]    = min(100, health    + int(hours * 3))
        pet["happiness"] = min(100, happiness + int(hours * 2))
        pet["last_decay"] = now.isoformat()
        return pet
    else:
        # Cek anti_hunger ability atau pil anti lapar — hunger tidak naik
        ability = pet.get("special_ability") or ""
        pil_lapar = pet.get("pil_anti_lapar_until")
        hunger_frozen = "anti_hunger" in ability or (pil_lapar and parse_dt(pil_lapar) > now)
        if not hunger_frozen:
            hunger_add = min(100, int(hours / 3 * 10))
            hunger    = min(100, hunger + hunger_add)
        happy_sub  = min(100, int(hours * 3))
        happiness = max(0, happiness - happy_sub)
        if hunger >= 70:
            health = max(1, health - int(hours * 5))   # min 1, tidak bisa mati
        if happiness <= 10:
            health = max(1, health - int(hours * 2))   # min 1, tidak bisa mati

    pet["hunger"]     = hunger
    pet["happiness"]  = happiness
    # ability2_anti_sick atau pil_abadi_until: health tidak turun
    ability = pet.get("special_ability") or ""
    pil_abadi = pet.get("pil_abadi_until")
    abadi_active = pil_abadi and parse_dt(pil_abadi) > now
    if "anti_sick" not in ability and not abadi_active:
        pet["health"] = health
    else:
        pet["health"] = max(pet.get("health") or 100, health)  # hanya bisa naik
    pet["last_decay"] = now.isoformat()

    # Poop — happiness turun kalau belum dibersihkan (skip saat tidur)
    poop_count = (pet.get("poop_count") or 0)
    if poop_count > 0 and not sleeping:
        pet["happiness"] = max(0, (pet.get("happiness") or 0) - int(poop_count * 5 * hours))

    # Bath — happiness & health turun kalau kotor (koi tidak perlu mandi)
    if pet.get("pet_type") != "koi":
        last_bath_str = pet.get("last_bath")
        bath_required = BATH_REQUIRED_HOURS * (2 if pet.get("soap_premium_active") else 1)
        if last_bath_str:
            hours_since_bath = (now - parse_dt(last_bath_str)).total_seconds() / 3600
            if hours_since_bath > bath_required:
                dirty_hours = hours_since_bath - bath_required
                pet["happiness"] = max(0, (pet.get("happiness") or 0) - int(dirty_hours * 3))
                pet["health"]    = max(1, (pet.get("health") or 100) - int(dirty_hours * 2))  # min 1
                pet["is_dirty"]  = True
        else:
            pet["is_dirty"] = True
    else:
        pet["is_dirty"] = False

    return pet

def pet_mood(pet: dict) -> str:
    h    = pet.get("hunger") or 0
    hp   = pet.get("happiness") or 80
    hl   = pet.get("health") or 100
    pc   = pet.get("poop_count") or 0
    dirty = pet.get("is_dirty", False)
    sleeping = pet.get("is_sleeping", False)
    if sleeping:   return "😴 Lagi tidur~"
    if hl < 30:    return "😷 Sakit"
    if h > 80:     return "😩 Lapar banget!"
    if pc >= 3:    return "💩 Kandang penuh poop! Tolong bersihkan~"
    if pc >= 1:    return f"💩 Ada {'poop' if pc == 1 else f'{pc}x poop'}, bersihkan yuk!"
    if dirty and not pet.get("pet_type") == "koi":      return "🛁 Bau! Pengen mandi~"
    if hp < 20:    return "😢 Sedih"
    if hp > 80:    return "🥰 Senang banget!"
    if h < 30:     return "😄 Kenyang & bahagia!"
    return "😊 Baik-baik aja"

def pet_card(pet: dict) -> str:
    info  = PETS.get(pet["pet_type"], {"name": "?", "emoji": "🐾"})
    lv    = calc_level((pet.get("xp") or 0))
    emoji_str = pet_emoji(pet["pet_type"], lv)

    xp_n  = xp_to_next((pet.get("xp") or 0))
    h     = pet.get("hunger") or 0
    hp    = pet.get("happiness") or 80
    hl    = pet.get("health") or 100
    pc    = pet.get("poop_count") or 0
    hc    = "🔴" if h > 80 else "🟡" if h > 50 else "🟢"
    hpc   = "🔴" if hp < 20 else "🟡" if hp < 50 else "🟢"
    hlc   = "🔴" if hl < 30 else "🟡" if hl < 60 else "🟢"
    rare  = "  ⭐ <i>Langka</i>" if info.get("rare") else ""
    acc   = f" {pet['accessory']}" if pet.get("accessory") else ""
    poop_line  = f"\n💩 <b>Poop</b>: {pc}x tumpukan, belum dibersihkan!" if pc > 0 else ""
    dirty_line = f"\n🛁 <b>Kotor!</b> Pet butuh mandi~" if pet.get("is_dirty") and pet.get("pet_type") != "koi" else ""
    sleep_line = f"\n😴 <b>Lagi tidur</b> — bangun jam 07.00 WIB" if pet.get("is_sleeping") else ""
    wangi_line = f"\n🌸 <b>Wangi~</b>" if pet.get("wangi_until") and parse_dt(pet["wangi_until"]) > now_wib() else ""
    boarding_line = ""
    if pet.get("boarding_until"):
        b_end = parse_dt(pet["boarding_until"])
        if b_end > now_wib():
            boarding_line = f"\n🏨 <b>Di Penitipan</b> sampai {fmt_wib(b_end)}"
    expedition_line = ""
    if pet.get("expedition_until"):
        e_end = parse_dt(pet["expedition_until"])
        if e_end > now_wib():
            d_info = EXPEDITION_DESTINATIONS.get(pet.get("expedition_dest","local"),{})
            expedition_line = f"\n✈️ <b>Ekspedisi: {d_info.get('name','?')}</b> sampai {fmt_wib(e_end)}"
    married_line = f"\n💍 <b>Sudah menikah</b>" if pet.get("is_married") else ""
    bwins = (pet.get("battle_wins") or 0)
    battle_wins_line = f"\n⚔️ <b>Battle Wins: {bwins}x</b>" if bwins > 0 else ""
    badge_line = f"\n{PET_BADGES.get(pet.get('pet_type',''), '')}" if lv >= LEVEL_BADGE and pet.get("pet_type") in PET_BADGES else ""
    work_line = f"\n💼 <b>Sedang kerja...</b>" if (pet.get("work_until") and parse_dt(pet.get("work_until","1970")) > now_wib()) else ""
    sekolah_line = f"\n🏫 <b>Lagi sekolah...</b>" if (pet.get("sekolah_until") and parse_dt(pet.get("sekolah_until","1970")) > now_wib()) else ""

    text = (
        f"{emoji_str} <b>{pet['name']}</b>{acc} — {info['name']}{rare}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💬 <i>\"{get_pet_quote(pet)}\"</i>\n\n"
        f"📊 <b>Lv.{lv}</b>  XP: butuh {xp_n} lagi\n"
        f"🗣️ {pet_mood(pet)}\n\n"
        f"{hc} <b>Lapar</b>   [{bar(h)}] {h}%\n"
        f"{hpc} <b>Senang</b>  [{bar(hp)}] {hp}%\n"
        f"{hlc} <b>Sehat</b>   [{bar(hl)}] {hl}%"
        f"{poop_line}{dirty_line}{sleep_line}{wangi_line}{boarding_line}{expedition_line}{married_line}{battle_wins_line}{badge_line}{work_line}{sekolah_line}"
    )

    return text

# ==================== LOG HELPER ====================
async def log(context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        await context.bot.send_message(LOG_GROUP, text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Log error: {e}")

def fmt_user(user) -> str:
    """Format user info with username for logs"""
    name = getattr(user, 'first_name', None) or str(user.id)
    username = getattr(user, 'username', None)
    uid = getattr(user, 'id', user)
    uname_txt = f" @{username}" if username else ""
    return f"<b>{name}</b>{uname_txt} (<code>{uid}</code>)"

async def _send_error_detail(context, user, exc, where="", data=""):
    """Kirim pesan error ke user. Untuk ADMIN, sertakan traceback lengkap di chat
    biar gampang debug; user biasa cuma dapat pesan ramah."""
    import traceback as _tb
    uid = getattr(user, "id", None)
    # Selalu kirim full ke LOG_GROUP
    try:
        tb_str = "".join(_tb.format_exception(type(exc), exc, exc.__traceback__))
        await context.bot.send_message(
            LOG_GROUP,
            f"⚠️ <b>ERROR</b> [{safe_html(str(where))}] dari {fmt_user(user)}\n"
            f"📲 data: <code>{safe_html(str(data))[:200]}</code>\n"
            f"<pre>{safe_html(tb_str[-3000:])}</pre>",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass
    # Ke user: admin dapat detail, lainnya pesan ramah
    try:
        if uid in ADMIN_IDS:
            tb_str = "".join(_tb.format_exception(type(exc), exc, exc.__traceback__))
            msg = (
                f"🐞 <b>DEBUG (admin)</b>\n"
                f"📍 {safe_html(str(where))}\n"
                f"📲 data: <code>{safe_html(str(data))[:200]}</code>\n"
                f"❌ <code>{safe_html(type(exc).__name__)}: {safe_html(str(exc))[:300]}</code>\n\n"
                f"<pre>{safe_html(tb_str[-3200:])}</pre>"
            )
            await context.bot.send_message(uid, msg, parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_message(uid, "⚠️ Terjadi kesalahan, coba lagi~")
    except Exception:
        # Fallback tanpa HTML kalau traceback bikin parse error
        try:
            await context.bot.send_message(uid, f"⚠️ Error: {type(exc).__name__}: {str(exc)[:300]}")
        except Exception:
            pass

# ==================== KEYBOARDS ====================
def kb_reply() -> ReplyKeyboardMarkup:
    """Reply keyboard selalu tampil di bawah"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Status")],
        [KeyboardButton("🐾 Pet Saya"), KeyboardButton("🏪 Carpet Shop")],
        [KeyboardButton("🎒 Inventori"), KeyboardButton("🛒 Toko Makan")],
        [KeyboardButton("🎮 Mini Game"), KeyboardButton("🚶 Jalan Jalan")],
        [KeyboardButton("🎯 Misi & Task"), KeyboardButton("💳 Top Up Koin")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("❓ Bantuan")],
    ], resize_keyboard=True, is_persistent=True)

MINI_APP_URL  = "https://t.me/Carpetsrobot/carpets"
CARPAWS_URL   = "https://t.me/Carpetsrobot/carpaws"

def kb_main(user_id: int = None, pet_lv: int = 1) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📱 Buka Mini App", url=MINI_APP_URL)],
        [InlineKeyboardButton("🐾 Car Paws — Social Media Pet", url=CARPAWS_URL)],
        [InlineKeyboardButton("🏪 Carpet Shop", callback_data="carpet_shop")],
        [InlineKeyboardButton("🐾 Pet Saya",    callback_data="my_pet"),
         InlineKeyboardButton("🎒 Inventori",   callback_data="inventory")],
        [InlineKeyboardButton("🛒 Toko Makan",  callback_data="food_shop"),
         InlineKeyboardButton("🎮 Mini Game",   callback_data="game_menu")],
        [InlineKeyboardButton("🎁 Koin Harian", callback_data="daily"),
         InlineKeyboardButton("💰 Koin Saya",   callback_data="my_coins")],
        [InlineKeyboardButton("🎰 Gacha Box",     callback_data="gacha_menu"),
         InlineKeyboardButton("💳 Top Up Koin",  callback_data="topup_start")],
        [InlineKeyboardButton("💸 Transfer Koin", callback_data="transfer_koin"),
         InlineKeyboardButton("⚙️ Settings",      callback_data="settings")],
        [InlineKeyboardButton("🐄 Ternak",        callback_data="livestock_menu"),
         InlineKeyboardButton("🍳 Dapur MBG",     callback_data="mbg_kitchen")],
        [InlineKeyboardButton("🎯 Misi & Task",    callback_data="task_menu"),
         InlineKeyboardButton("❓ Help & Info",    callback_data="help_info")],
        [InlineKeyboardButton("📋 List Bot",       url=SHOP_URL)],
    ]
    if pet_lv >= 10:
        rows.insert(3, [InlineKeyboardButton("🛍️ Special Store", callback_data="special_store")])
    if user_id in ADMIN_IDS:
        rows.append([InlineKeyboardButton("🔧 Stats Bot", callback_data="bot_stats")])
    return InlineKeyboardMarkup(rows)

def kb_shop() -> InlineKeyboardMarkup:
    rows = []
    row  = []
    for key, info in PETS.items():
        if info.get("gacha_only"):   continue  # Pet eksklusif gacha
        if info.get("astro_only"):   continue  # Pet eksklusif Astro Paws
        if info.get("astro2_only"):  continue  # Pet eksklusif Astro Paws 2
        if info.get("aqua_only"):    continue  # Pet eksklusif Aqua Tails
        label = f"{'⭐' if info['rare'] else ''}{info['emoji']} {info['name']}"
        if info["price"] > 0:
            label += f" ({info['price']}🪙)"
        row.append(InlineKeyboardButton(label, callback_data=f"adopt_{key}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🛠️ Buat Item Sendiri (1.000🪙 → 5 item)", callback_data="buatitem_start")])
    rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def kb_pet(pet: dict, pet_lv: int = 1) -> InlineKeyboardMarkup:
    pid = pet["id"]
    is_koi = pet.get("pet_type") == "koi"
    # Cek boarding/ekspedisi
    is_boarding = bool(pet.get("boarding_until") and parse_dt(pet.get("boarding_until","1970")) > now_wib())
    is_expedition = bool(pet.get("expedition_until") and parse_dt(pet.get("expedition_until","1970")) > now_wib())
    is_sekolah = bool(pet.get("sekolah_until") and parse_dt(pet.get("sekolah_until","1970")) > now_wib())
    is_working = bool(pet.get("work_until") and parse_dt(pet.get("work_until","1970")) > now_wib())

    if is_boarding:
        # Cek apakah boarding sudah expired (misi selesai tapi belum di-clear)
        b_until = parse_dt(pet.get("boarding_until", "1970"))
        if b_until <= now_wib():
            # Auto-clear — boarding sudah expired
            import asyncio
            asyncio.create_task(update_pet(pid, {"boarding_until": None, "last_decay": now_wib().isoformat()}))
            is_boarding = False
        else:
            return InlineKeyboardMarkup([
                [InlineKeyboardButton("🏨 Jemput dari Penitipan", callback_data=f"boarding_pickup_{pid}")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
            ])
    if is_expedition:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✈️ Cek Ekspedisi", callback_data=f"expedition_check_{pid}")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    if is_sekolah:
        sisa = fmt_countdown(parse_dt(pet["sekolah_until"]))
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🏫 Lagi sekolah... ({sisa} lagi)", callback_data=f"pet_sekolah_{pid}")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    if is_working:
        sisa = fmt_countdown(parse_dt(pet["work_until"]))
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💼 Lagi kerja... ({sisa} lagi)", callback_data=f"pet_work_{pid}")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])

    rows = [
        [InlineKeyboardButton("🍽️ Kasih Makan", callback_data=f"feed_{pid}"),
         InlineKeyboardButton("🎾 Ajak Main",   callback_data=f"play_{pid}")],
        [InlineKeyboardButton("💊 Obati",        callback_data=f"heal_{pid}"),
         *([InlineKeyboardButton("🛁 Mandi",     callback_data=f"bath_{pid}")] if not is_koi else [])],
        [InlineKeyboardButton("🏨 Titip Pet",    callback_data=f"boarding_{pid}"),
         InlineKeyboardButton("✈️ Ekspedisi",    callback_data=f"expedition_{pid}")],
        [InlineKeyboardButton("⚔️ Battle Pet",   callback_data=f"battle_menu_{pid}")],
    ]
    if (pet.get("poop_count") or 0) > 0:
        rows.append([InlineKeyboardButton(f"🧹 Bersihkan Poop ({pet['poop_count']}x)", callback_data=f"clean_{pid}")])
    # Koi tidak bisa pakai aksesoris
    if not is_koi and pet.get("accessory"):
        rows.append([InlineKeyboardButton(f"❌ Lepas {pet['accessory']}", callback_data=f"remove_acc_{pid}")])
    lv = calc_level(pet.get("xp") or 0)
    if lv >= 10 and not pet.get("is_married"):
        rows.append([InlineKeyboardButton("💍 Nikahkan Pet (Lv.10+)", callback_data=f"marriage_{pid}")])
    # Partner management
    has_partner = bool(pet.get("owner2_id"))
    if not has_partner:
        rows.append([InlineKeyboardButton("👫 Tambah Partner", callback_data=f"pet_add_partner_{pid}")])
    else:
        rows.append([
            InlineKeyboardButton("🔄 Ganti Partner (1000🪙)", callback_data=f"pet_change_partner_{pid}"),
            InlineKeyboardButton("💔 Hapus Partner", callback_data=f"pet_remove_partner_{pid}"),
        ])
    # Cerai
    if pet.get("is_married"):
        rows.append([InlineKeyboardButton("💔 Ceraikan Pet", callback_data=f"pet_divorce_{pid}")])
    if pet_lv >= 15:
        rows.append([InlineKeyboardButton("🎁 Gift ke Partner", callback_data=f"gift_partner_{pid}")])
    if pet_lv >= 20:
        rows.append([InlineKeyboardButton("🎁 Gift ke Orang Lain", callback_data=f"gift_other_{pid}")])
    if pet_lv >= 30:
        rows.append([InlineKeyboardButton("👀 Lihat Pet Orang Lain", callback_data="view_others_pet")])
    # Lv 35: Kerja (diganti profesi di Lv.55+)
    if lv >= LEVEL_WORK and lv < LEVEL_PROFESI:
        is_working = bool(pet.get("work_until") and parse_dt(pet.get("work_until","1970")) > now_wib())
        work_label = "💼 Cek Kerja" if is_working else "💼 Kirim Kerja (Lv.35+)"
        rows.append([InlineKeyboardButton(work_label, callback_data=f"pet_work_{pid}")])
    # Lv 55: Profesi (upgrade dari kerja biasa)
    if lv >= LEVEL_PROFESI:
        profesi = pet.get("profesi_kerja")
        is_working = bool(pet.get("work_until") and parse_dt(pet.get("work_until","1970")) > now_wib())
        if not profesi:
            rows.append([InlineKeyboardButton("🎓 Pilih Profesi Kerja (Lv.55+)", callback_data=f"pet_profesi_{pid}")])
        else:
            profesi_label = "🗺️ Penjelajah" if profesi == "penjelajah" else "🧺 Pengumpul"
            work_label = f"💼 Cek Kerja Profesional" if is_working else f"💼 Kerja Profesional ({profesi_label})"
            rows.append([InlineKeyboardButton(work_label, callback_data=f"pet_profwork_{pid}")])
    # Lv 60: Sekolah
    if lv >= LEVEL_SEKOLAH:
        rows.append([InlineKeyboardButton("🏫 Sekolah (Lv.60+)", callback_data=f"pet_sekolah_{pid}")])
    # Lv 40: Punya anak (hanya kalau sudah nikah ATAU sudah punya anak meski sudah cerai)
    has_child = bool(pet.get("child_pet_id"))
    if lv >= LEVEL_CHILD and (pet.get("is_married") or has_child):
        child_label = "👶 Lihat Anak" if has_child else "👶 Punya Anak (Lv.40+)"
        rows.append([InlineKeyboardButton(child_label, callback_data=f"pet_child_{pid}")])
    # Lv 45: Badge
    if lv >= LEVEL_BADGE:
        badge = PET_BADGES.get(pet.get("pet_type",""), "🎖️ Badge Kehormatan")
        rows.append([InlineKeyboardButton(f"{badge}", callback_data=f"pet_badge_{pid}")])
    # Lv 50: Aksesoris spesial
    if lv >= LEVEL_SPECIAL_ACC and not is_koi:
        acc50 = SPECIAL_ACC_LV50.get(pet.get("pet_type",""), {})
        already = pet.get("accessory_key","") == f"lv50_{pet.get('pet_type','')}"
        if not already:
            rows.append([InlineKeyboardButton(f"🌟 Equip {acc50.get('emoji','')} {acc50.get('name','')} (Lv.50)", callback_data=f"equip_lv50_{pid}")])
    # Bayar uang saku langsung dari kartu pet anak
    if pet.get("is_child"):
        rows.append([InlineKeyboardButton("💰 Bayar Uang Saku", callback_data=f"child_pay_{pid}")])
    rows.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def kb_delivery(code: str, taps: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👆 Tap! ({taps}/{TAPS_NEEDED})", callback_data=f"tap_{code}")],
    ])

def kb_food_shop() -> InlineKeyboardMarkup:
    # Tampilkan semua makanan: biasa + koi + MBG biasa + Pil Level Up
    # EXCLUDE item Astro Paws (astro: True) — eksklusif dari event, bukan dijual
    all_items = {k: v for k, v in {**FOOD_SHOP, **KOI_FOOD_SHOP}.items() if not v.get("astro") and not v.get("exclusive")}
    rows = [[InlineKeyboardButton(f"{i['emoji']} {i['name']} — {i['price']}🪙", callback_data=f"buy_{k}")] for k, i in all_items.items()]
    rows.append([InlineKeyboardButton("🌟 Pil Level Up — 3.000🪙", callback_data="buy_pil_levelup")])
    rows.append([InlineKeyboardButton("🍳 Dapur MBG (Buat dari Ternak)", callback_data="mbg_kitchen")])
    rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def kb_game() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔢 Tebak Angka", callback_data="game_guess"),
         InlineKeyboardButton("🎲 Dadu",        callback_data="game_roll")],
        [InlineKeyboardButton("🧠 Kuis Hewan",  callback_data="game_quiz"),
         InlineKeyboardButton("⚽ Tangkap Bola", callback_data="game_catch")],
        [InlineKeyboardButton("🔙 Kembali",      callback_data="main_menu")],
    ])

def kb_pet_selector(pets: List[dict], user_id: int, missing_pets: list = None) -> InlineKeyboardMarkup:
    """Keyboard untuk memilih pet kalau punya lebih dari 1"""
    buttons = []
    for pet in pets:
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        role = "👑" if pet.get("owner1_id") == user_id else "👤"
        buttons.append([InlineKeyboardButton(
            f"{role} {info['emoji']} {pet['name']} (Lv.{calc_level(pet.get('xp',0))})",
            callback_data=f"select_pet_{pet['id']}"
        )])
    for pet in (missing_pets or []):
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        buttons.append([InlineKeyboardButton(
            f"🏃 {info['emoji']} {pet['name']} — kabur! Cari?",
            callback_data=f"find_pet_{pet['id']}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

# ==================== HANDLERS ====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_by = None

    # Simpan ref_by ke global dict SEBELUM force sub check
    if context.args:
        arg0 = context.args[0].upper()
        if arg0.startswith("REF_"):
            try:
                _rb = int(arg0[4:])
                if _rb != user.id:
                    _PENDING_REFS[user.id] = _rb
            except: pass

    # Cek force subscribe
    if not await check_force_sub(update, context):
        return

    # Cek astro lock AP1+AP2
    locked, lock_status, unlock_time = await astro_is_locked(user.id)
    if not locked:
        locked, lock_status, unlock_time = await a2_is_locked(user.id)
    if locked:
        await astro_send_lock_msg(update.message, lock_status, unlock_time); return

    if context.args:
        arg = context.args[0].upper()
        # Referral link: /start REF_userid
        if arg.startswith("REF_"):
            try:
                ref_by = int(arg[4:])
                if ref_by == user.id:
                    ref_by = None
            except:
                ref_by = None

            # Cek apakah user ini BARU (belum pernah start bot)
            # Flush cache dulu biar ga salah baca
            _cdel(_user_cache, user.id)
            existing = await sb("GET", "users", {"user_id": f"eq.{user.id}"})
            is_new_user = not existing

            u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name), ref_by=ref_by if is_new_user else None)

            # Kirim notif + reward HANYA kalau user baru dan ref_by valid
            if ref_by and is_new_user:
                try:
                    await context.bot.send_message(
                        ref_by,
                        f"🎉 <b>{safe_html(user.first_name)}</b> bergabung pakai link referralmu!\n"
                        f"💰 Kamu dapat <b>+{REFERRAL_REWARD} 🪙</b>!",
                        parse_mode=ParseMode.HTML
                    )
                except: pass
        else:
            u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            # Validasi format kode invite: harus PET + 5 digit angka
            if arg.startswith("PET") and len(arg) == 8 and arg[3:].isdigit():
                await handle_join(update, context, arg)
                return
            if arg.startswith("BATTLE_"):
                battle_code = arg[7:]
                await handle_battle_accept(update, context, battle_code)
                return
            if arg.startswith("AMPLOP_"):
                kid = arg[7:]
                await handle_amplop_claim(update, context, kid)
                return
            if arg.startswith("MARRY_"):
                marry_code = arg[6:]
                await handle_marriage_link(update, context, marry_code)
                return
            if arg == "VERIFY_QUIZ":
                await _verify_quiz_membership(context, user.id, reply_msg=update.message)
                return
            # Bukan kode valid, lanjut tampil welcome biasa
    else:
        u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    bot_name = BOT_USERNAME.lstrip("@")
    ref_link = f"https://t.me/{bot_name}?start=REF_{user.id}"
    koin_display = u.get('koin', 0) if u else 0
    text = (
        f"👋 Halo <b>{safe_html(user.first_name)}</b>! Selamat datang di\n\n"
        "🏪 <b>The Carpet Shop</b> — Toko Adopsi Hewan!\n"
        "━━━━━━━━━━━━━━━\n\n"
        "Di sini kamu bisa:\n"
        "🐾 <b>Adopsi hewan peliharaan</b> — dari kucing, anjing, kelinci, hingga naga & phoenix langka!\n"
        "👫 <b>Rawat bareng partner</b> — setiap pet punya 2 owner. Rawat bersama teman!\n"
        "🍽️ <b>Kasih makan & obati</b> — jaga kesehatan petmu agar tetap bahagia!\n"
        "🎾 <b>Ajak main</b> — tingkatkan kesenangan petmu (cooldown 5 jam)\n"
        "📦 <b>Sistem pengiriman unik</b> — percepat dengan tap dari teman-temanmu!\n"
        "🎮 <b>Mini game</b> — kumpulkan koin dari tebak angka, dadu, kuis, & tangkap bola!\n"
        "⭐ <b>Hewan langka</b> — unlock Axolotl, Panda, Unicorn, Naga, hingga Phoenix!\n"
        "📱 <b>Mini App</b> — rawat petmu lewat mini app!\n"
        "🎯 <b>Misi & Task</b> — selesaikan misi harian dan dapat reward koin!\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 Koin kamu: <b>{koin_display} 🪙</b>\n\n"
        f"🔗 <b>Link referralmu:</b>\n<code>{ref_link}</code>\n"
        f"<i>Ajak teman pakai link ini → kamu dapat {REFERRAL_REWARD} 🪙 setiap teman yang bergabung!</i>\n\n"
        "🐾 Yok adopt disini!"
    )
    pet_lv = await get_pet_level(user.id)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb_main(user.id, pet_lv))
    await update.message.reply_text("⬇️ Menu cepat tersedia di bawah!", reply_markup=kb_reply())
    # Tanya nickname kalau belum punya
    if u and not u.get("nickname"):
        context.user_data["state"] = "ASK_NICKNAME_ONBOARD"
        await update.message.reply_text(
            "👤 <b>Satu lagi!</b>\n\n"
            "Mau dipanggil apa sama petmu? Masukkan nickname kamu~\n"
            "<i>Contoh: Kakak, Ayah, Bunda, dll</i>\n\n"
            "Ketik nickname atau /skip untuk lewati:",
            parse_mode=ParseMode.HTML
        )
    await log(context, f"👤 Start: {fmt_user(user)}")

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_force_sub(update, context):
        return
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    pet_lv = await get_pet_level(user.id)
    await update.message.reply_text("🏠 <b>Menu Utama</b>", parse_mode=ParseMode.HTML, reply_markup=kb_main(user.id, pet_lv))
    await update.message.reply_text("⬇️ Menu cepat:", reply_markup=kb_reply())

async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip nickname onboarding"""
    context.user_data["state"] = None
    await update.message.reply_text("Oke, nickname dilewati~ Bisa diatur kapan saja di ⚙️ Settings!")

async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Ketik: <code>/join KODE_INVITE</code>", parse_mode=ParseMode.HTML)
        return
    await handle_join(update, context, context.args[0].upper())

async def handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE, kode: str):
    user = update.effective_user
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    # Selalu ambil fresh dari DB — filter is_delivered=false supaya tidak ambil delivery lama
    kode = kode.upper().strip()
    res = await sb("GET", "deliveries", {
        "kode_invite":  f"eq.{kode}",
        "is_delivered": "eq.false",
    })
    d = res[0] if res else None
    if not d:
        await update.message.reply_text(
            "❌ Kode invite tidak valid!\n\n"
            "<i>Pastikan kode benar (contoh: PET12345). Kode sudah kedaluwarsa jika pet sudah dikirim.</i>",
            parse_mode=ParseMode.HTML
        )
        return
    if int(d["owner1_id"]) == user.id:
        await update.message.reply_text("❌ Kamu tidak bisa join ke petmu sendiri!")
        return
    # Cek slot partner — owner2_id harus benar-benar NULL / 0 / kosong
    owner2_val = d.get("owner2_id")
    partner_filled = (
        owner2_val is not None
        and str(owner2_val).strip() not in ("", "null", "None", "0", "false")
        and str(owner2_val).strip() != "0"
    )
    try:
        if partner_filled and int(owner2_val) > 0:
            await update.message.reply_text("❌ Slot partner sudah terisi!")
            return
    except (ValueError, TypeError):
        pass

    info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})
    is_koi = d["pet_type"] == "koi"

    # Cek apakah ini gacha delivery (pet sudah exist di DB, tidak perlu dibuat ulang)
    # Gacha delivery: started=True dari awal dan pet sudah dibuat saat gacha
    is_gacha_delivery = bool(d.get("started")) and d.get("arrive_at") and not is_koi

    existing_gacha_pet = None
    if is_gacha_delivery:
        # Cari pet yang sudah dibuat oleh owner1 dengan tipe ini
        pets_owner1 = await sb("GET", "pets", {
            "owner1_id": f"eq.{d['owner1_id']}",
            "pet_type":  f"eq.{d['pet_type']}",
            "owner2_id": "is.null",
        })
        existing_gacha_pet = pets_owner1[0] if pets_owner1 else None

    # Koi atau gacha: langsung deliver tanpa pengiriman
    if is_koi or existing_gacha_pet:
        arrive_at = now_wib().isoformat()
    else:
        arrive_at = (now_wib() + timedelta(hours=DELIVERY_HOURS)).isoformat()

    await update_delivery(d["code"], {
        "owner2_id":   user.id,
        "owner2_name": safe_html(user.first_name) or safe_html(user.username) or str(user.id),
        "arrive_at":   arrive_at,
        "started":     True,
    })

    # Anti-race condition: re-fetch pastikan kita yang berhasil nulis
    d_verify = await sb("GET", "deliveries", {"code": f"eq.{d['code']}"})
    d_verify = d_verify[0] if d_verify else None
    if not d_verify or int(d_verify.get("owner2_id") or 0) != user.id:
        await update.message.reply_text("❌ Slot partner baru saja diisi orang lain, minta kode baru ke temanmu!")
        return

    # Hapus kode_invite dari DB supaya tidak bisa dipakai lagi
    await sb("PATCH", "deliveries", {"code": f"eq.{d['code']}"}, {"kode_invite": None})
    _invalidate_delivery(d["code"])
    owner1_name = safe_html(d.get("owner1_name", "Temanmu"))

    # === SPECIAL CASE: add_partner untuk pet yang sudah ada (solo adopt) ===
    if d.get("add_partner_pet_id"):
        pet_id = int(d["add_partner_pet_id"])
        pet = await get_pet_by_id(pet_id)
        if pet and pet.get("owner1_id") == d["owner1_id"] and not pet.get("owner2_id"):
            await update_pet(pet_id, {"owner2_id": user.id})
            await update_delivery(d["code"], {"is_delivered": True})
            pinfo = PETS.get(pet["pet_type"], {"emoji": "🐾", "name": "?"})
            await update.message.reply_text(
                f"🎉 Kamu berhasil join sebagai partner!\n\n"
                f"{pinfo['emoji']} <b>{pet['name']}</b> milik {owner1_name}\n\n"
                f"🌟 <b>Selamat merawat bersama!</b> 💕",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")],
                    [InlineKeyboardButton("🏠 Menu", callback_data="main_menu")],
                ])
            )
            try:
                await context.bot.send_message(
                    d["owner1_id"],
                    f"🎊 <b>{safe_html(user.first_name)}</b> join sebagai partner!\n"
                    f"{pinfo['emoji']} <b>{pet['name']}</b> sekarang punya partner baru~ 💕",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
                )
            except: pass
            await log(context, f"👫 Add partner: {fmt_user(user)} join {pinfo['emoji']} <b>{pet['name']}</b> milik <code>{d['owner1_id']}</code>")
            return

    if existing_gacha_pet:
        # Gacha pet sudah ada — cukup update owner2_id di pet existing
        await update_pet(existing_gacha_pet["id"], {"owner2_id": user.id})
        await update_delivery(d["code"], {"is_delivered": True})

        text = (
            f"🎉 Kamu berhasil join sebagai partner!\n\n"
            f"{info['emoji']} <b>{existing_gacha_pet['name']}</b> milik {owner1_name}\n\n"
            f"🌟 <b>Pet eksklusif langsung bisa dirawat!</b>\n\n"
            f"Selamat merawat bersama! 💕"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")],
            [InlineKeyboardButton("🏠 Menu", callback_data="main_menu")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

        # Notify owner1
        try:
            await context.bot.send_message(
                d["owner1_id"],
                f"🎊 <b>{safe_html(user.first_name)}</b> join sebagai partner!\n"
                f"{info['emoji']} <b>{existing_gacha_pet['name']}</b> sekarang punya 2 owner~ 💕",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
            )
        except: pass

    elif is_koi:
        # Langsung buat pet dan deliver
        await _create_pet_from_delivery(d, d["code"], owner2_id_override=user.id)
        await update_delivery(d["code"], {"is_delivered": True})

        text = (
            f"🎉 Kamu berhasil join sebagai partner!\n\n"
            f"{info['emoji']} <b>{d['pet_name']}</b> milik {owner1_name}\n\n"
            f"🐟 <b>Ikan Koi langsung tiba!</b> Tidak perlu nunggu~\n\n"
            f"Selamat merawat ikan koi bersama! 💕"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")],
            [InlineKeyboardButton("🏠 Menu", callback_data="main_menu")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

        # Notify owner1
        try:
            await context.bot.send_message(
                d["owner1_id"],
                f"🎊 <b>{safe_html(user.first_name)}</b> telah join sebagai partnermu!\n"
                f"{info['emoji']} <b>{d['pet_name']}</b> sudah tiba! Langsung bisa dirawat~\n\n"
                f"<i>Ikan Koi tidak perlu masa pengiriman 💕</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
            )
        except: pass
    else:
        text = (
            f"🎉 Kamu berhasil join sebagai partner!\n\n"
            f"{info['emoji']} <b>{d['pet_name']}</b> milik {owner1_name}\n\n"
            f"📦 Pengiriman dimulai sekarang!\n"
            f"⏰ Tiba dalam: <b>5 jam</b>\n\n"
            f"🚀 Percepat dengan share link ke teman!\n"
            f"Butuh <b>{TAPS_NEEDED} tap</b> untuk langsung tiba~\n\n"
            f"📌 Kode pengiriman: <code>{d['code']}</code>\n"
            f"Share ke teman: ketik <code>@carpetsrobot tap {d['code']}</code> di chat mana aja!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Cek Pengiriman", callback_data=f"check_{d['code']}")],
            [InlineKeyboardButton("🚀 Share & Percepat", switch_inline_query=f"tap {d['code']}")],
            [InlineKeyboardButton("🏠 Menu", callback_data="main_menu")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

        # Notify owner1
        try:
            await context.bot.send_message(
                d["owner1_id"],
                f"🎊 <b>{safe_html(user.first_name)}</b> telah join sebagai partnermu!\n"
                f"{info['emoji']} <b>{d['pet_name']}</b> akan tiba dalam 5 jam!\n\n"
                f"📦 Kode: <code>{d['code']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Cek Pengiriman", callback_data=f"check_{d['code']}")]])
            )
        except: pass

    await log(context, f"👫 Partner join: {fmt_user(user)} join pet <b>{d['pet_name']}</b> ({info['name']}) milik <b>{d['owner1_name']}</b>")

# ==================== BUTTON CALLBACK ====================
async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    user = q.from_user
    data = q.data

    # Force subscribe — skip untuk tap_ (delivery orang lain) dan check_sub itu sendiri
    if data != "check_sub" and not data.startswith("tap_"):
        if not await check_force_sub(update, context):
            return

    # Cek astro lock — AP1 + AP2
    _ap_allowed = ("astro_","a2_","topup_","find_pet_","bath_","boarding_pickup_","check_sub","main_menu")
    if not any(data.startswith(p) for p in _ap_allowed) and data not in ("main_menu","check_sub") and user.id not in ADMIN_IDS:
        locked, lock_status, unlock_time = await astro_is_locked(user.id)
        if not locked:
            locked, lock_status, unlock_time = await a2_is_locked(user.id)
        if locked:
            await astro_send_lock_msg(q.message, lock_status, unlock_time); return

    # Jangan buat user baru kalau cuma tap pengiriman orang lain atau check_sub
    if not data.startswith("tap_") and data != "check_sub":
        await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    try:
        if data == "main_menu":
            pet_lv = await get_pet_level(user.id)
            await q.edit_message_text("🏠 <b>Menu Utama</b>", parse_mode=ParseMode.HTML, reply_markup=kb_main(user.id, pet_lv))

        elif data.startswith("riwayat_"):
            if user.id not in ADMIN_IDS:
                await q.answer("❌ Bukan admin!", show_alert=True); return
            parts = data.split("_")  # riwayat_{target_id}_{page}
            await _send_riwayat(q, int(parts[1]), int(parts[2]), edit=True)

        elif data == "carpet_shop":
            # Bersihkan state buatitem supaya tidak ghosting
            for k in ("state", "buatitem_nama", "buatitem_emoji", "buatitem_type"):
                context.user_data[k] = None
            await show_shop(q)

        elif data.startswith("adopt_solo_"):
            code = data[11:]
            await do_adopt_solo(q, user, code, context)

        elif data.startswith("adopt_partner_"):
            code = data[14:]
            await show_adopt_partner_info(q, user, code, context)

        elif data.startswith("adopt_"):
            pet_type = data[6:]
            info = PETS[pet_type]
            price = info["price"]
            u = await get_user(user.id)
            if price > 0 and (u.get("koin") or 0) < price:
                await q.edit_message_text(
                    f"❌ Koin tidak cukup!\n{info['emoji']} {info['name']} butuh <b>{price} 🪙</b>\nKoinmu: {u.get('koin',0)} 🪙",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="carpet_shop")]])
                )
                return
            context.user_data["adopting"] = pet_type
            context.user_data["state"]    = ASK_PET_NAME
            await q.edit_message_text(
                f"✏️ Kamu memilih {info['emoji']} <b>{info['name']}</b>!\n\nKetik nama untuk peliharaanmu:",
                parse_mode=ParseMode.HTML
            )

        # Legacy callback: tombol lama pakai format "partner_DEL{code}"
        elif data.startswith("partner_DEL"):
            code = data[11:]  # "partner_DEL" = 11 karakter
            await show_adopt_partner_info(q, user, code, context)

        # Legacy callback: tombol lama pakai format "solo_DEL{code}"
        elif data.startswith("solo_DEL"):
            code = data[8:]  # "solo_DEL" = 8 karakter
            await do_adopt_solo(q, user, code, context)

        elif data == "my_pet":
            await show_my_pet(q, user, context)

        elif data.startswith("select_pet_"):
            pet_id = int(data[11:])
            await show_single_pet(q, user, pet_id, context)

        elif data == "check_sub":
            try:
                member = await context.bot.get_chat_member(FORCE_SUB_CHANNEL, user.id)
                if member.status in ("member", "administrator", "creator"):
                    # Sudah join — proses referral yang pending dulu
                    pending_ref = _PENDING_REFS.pop(user.id, None)
                    _cdel(_user_cache, user.id)
                    existing = await sb("GET", "users", {"user_id": f"eq.{user.id}"})
                    is_new_user = not existing

                    u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name),
                                       ref_by=pending_ref if (pending_ref and is_new_user) else None)

                    # Kasih reward ke yang ngundang kalau user baru
                    if pending_ref and is_new_user:
                        try:
                            await context.bot.send_message(
                                pending_ref,
                                f"🎉 <b>{safe_html(user.first_name)}</b> bergabung pakai link referralmu!\n"
                                f"💰 Kamu dapat <b>+{REFERRAL_REWARD} 🪙</b>!",
                                parse_mode=ParseMode.HTML)
                        except: pass

                    await q.edit_message_text("✅ Verifikasi berhasil! Selamat datang di Carpets~ 🐾",
                                              parse_mode=ParseMode.HTML)
                    bot_name = BOT_USERNAME.lstrip("@")
                    ref_link = f"https://t.me/{bot_name}?start=REF_{user.id}"
                    koin_display = u.get("koin", 0) if u else 0
                    pet_lv = await get_pet_level(user.id)
                    welcome_text = (
                        f"👋 Halo <b>{safe_html(user.first_name)}</b>! Selamat datang di\n\n"
                        "🏪 <b>The Carpet Shop</b> — Toko Adopsi Hewan!\n"
                        "━━━━━━━━━━━━━━━\n\n"
                        "Di sini kamu bisa:\n"
                        "🐾 <b>Adopsi hewan peliharaan</b> — dari kucing, anjing, kelinci, hingga naga & phoenix langka!\n"
                        "👫 <b>Rawat bareng partner</b> — setiap pet punya 2 owner. Rawat bersama teman!\n"
                        "🍽️ <b>Kasih makan & obati</b> — jaga kesehatan petmu agar tetap bahagia!\n"
                        "🎾 <b>Ajak main</b> — tingkatkan kesenangan petmu (cooldown 5 jam)\n"
                        "📦 <b>Sistem pengiriman unik</b> — percepat dengan tap dari teman-temanmu!\n"
                        "🎮 <b>Mini game</b> — kumpulkan koin dari tebak angka, dadu, kuis, & tangkap bola!\n"
                        "⭐ <b>Hewan langka</b> — unlock Axolotl, Panda, Unicorn, Naga, hingga Phoenix!\n"
                        "📱 <b>Mini App</b> — rawat petmu lewat mini app!\n\n"
                        "━━━━━━━━━━━━━━━\n"
                        f"💰 Koin kamu: <b>{koin_display} 🪙</b>\n\n"
                        f"🔗 <b>Link referralmu:</b>\n<code>{ref_link}</code>\n"
                        f"<i>Ajak teman pakai link ini → kamu dapat {REFERRAL_REWARD} 🪙 setiap teman yang bergabung!</i>\n\n"
                        "🐾 Yok adopt disini!"
                    )
                    await q.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb_main(user.id, pet_lv))
                    await q.message.reply_text("⬇️ Menu cepat tersedia di bawah!", reply_markup=kb_reply())
                else:
                    await q.answer("❌ Kamu belum join channel! Coba join dulu lalu tekan tombol lagi.", show_alert=True)
            except Exception as e:
                logger.warning(f"check_sub error: {e}")
                await q.answer("⚠️ Gagal verifikasi, coba lagi sebentar.", show_alert=True)

        elif data.startswith("check_"):
            code = data[6:]
            await show_delivery(q, user, code, context)

        elif data.startswith("tap_"):
            code = data[4:]
            await do_tap(q, user, code, context)

        elif data == "inventory":
            await show_inventory(q, user)

        elif data == "buatitem_start":
            u = await get_user(user.id)
            koin = (u.get("koin") or 0)
            await q.edit_message_text(
                "🛠️ <b>Buat Item Sendiri</b>\n━━━━━━━━━━━━━━━\n\n"
                "Kamu bisa bikin item custom sendiri!\n\n"
                "💰 Biaya: <b>1.000 🪙</b>\n"
                "🎁 Dapat: <b>5 item</b>\n\n"
                f"Koin kamu: <b>{koin} 🪙</b>\n\n"
                "Pilih jenis item:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍖 Makanan", callback_data="buatitem_type_food"),
                     InlineKeyboardButton("👒 Aksesoris", callback_data="buatitem_type_accessory")],
                    [InlineKeyboardButton("🔙 Kembali", callback_data="carpet_shop")],
                ])
            )

        elif data.startswith("buatitem_type_"):
            item_type = data[14:]
            u = await get_user(user.id)
            if (u.get("koin") or 0) < 1000:
                await q.answer("❌ Koin tidak cukup! Butuh 1.000 🪙", show_alert=True)
                return
            context.user_data["buatitem_type"] = item_type
            context.user_data["state"] = "ASK_BUATITEM_NAMA"
            type_label = "Makanan 🍖" if item_type == "food" else "Aksesoris 👒"
            await q.edit_message_text(
                f"🛠️ <b>Buat Item — {type_label}</b>\n━━━━━━━━━━━━━━━\n\n"
                "Ketik <b>nama item</b> kamu:\n"
                "<i>Contoh: Kue Ulang Tahun, Topi Lucu, dll</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="carpet_shop")]])
            )

        elif data == "buatitem_confirm":
            await do_buatitem(q, user, context)

        # ===== KERJA (LV 35) =====
        elif data.startswith("pet_work_send_"):
            await do_send_work(q, user, int(data[14:]), context)

        elif data.startswith("pet_work_recall_"):
            pet_id = int(data[16:])
            pet = await get_pet_by_id(pet_id)
            if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
                await q.answer("❌ Bukan petmu!", show_alert=True); return
            await update_pet(pet_id, {"work_until": None, "last_work": now_wib().isoformat(), "profesi_work_active": False})
            _cdel(_pet_cache, pet_id)
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            await q.edit_message_text(
                f"🏠 <b>{pet['name']}</b> dipulangkan dari kerja!\n"
                f"{info['emoji']} Tidak dapat reward karena belum selesai.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))

        elif data.startswith("pet_work_"):
            await show_pet_work(q, user, int(data[9:]), context)

        # ===== ANAK (LV 40) =====
        elif data.startswith("child_create_"):
            parts = data[13:].split("_", 1)
            await do_create_child(q, user, int(parts[0]), parts[1], context)

        elif data.startswith("child_pay_"):
            await do_pay_child_allowance(q, user, int(data[10:]), context)

        elif data.startswith("pet_child_"):
            await show_pet_child_menu(q, user, int(data[10:]), context)

        # ===== BADGE (LV 45) =====
        elif data.startswith("pet_badge_"):
            await show_pet_badge(q, user, int(data[10:]))

        # ===== AKSESORIS LV 50 =====
        elif data.startswith("equip_lv50_"):
            await do_equip_lv50_acc(q, user, int(data[11:]), context)

        elif data == "food_shop":
            u = await get_user(user.id)
            await q.edit_message_text(
                f"🛒 <b>Toko Makanan</b>\n💰 Koinmu: <b>{u.get('koin',0)} 🪙</b>\n━━━━━━━━━━━━━━━",
                parse_mode=ParseMode.HTML, reply_markup=kb_food_shop()
            )

        elif data == "koi_food_shop":
            u = await get_user(user.id)
            rows = [[InlineKeyboardButton(f"{i['emoji']} {i['name']} — {i['price']}🪙", callback_data=f"buy_koi_{k}")] for k, i in KOI_FOOD_SHOP.items()]
            rows.append([InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")])
            await q.edit_message_text(
                f"🐟 <b>Toko Makanan Ikan</b>\n💰 Koinmu: <b>{u.get('koin',0)} 🪙</b>\n━━━━━━━━━━━━━━━\n<i>Khusus untuk Ikan Koi!</i>",
                parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows)
            )

        elif data.startswith("buy_koi_"):
            await do_buy_koi(q, user, data[8:])

        elif data == "view_others_pet":
            await show_others_pet(q, user)

        elif data == "jalan_menu":
            await show_jalan(q, user)

        elif data == "jalan_rumah":
            await show_jalan_rumah_ask(q, user, context)

        elif data.startswith("feed_other_"):
            await do_feed_other(q, user, int(data[11:]))

        elif data.startswith("feedother_"):
            inner = data[10:]  # {pet_id}_{item_key} — item_key bisa ada underscore
            sep = inner.index("_")
            await do_feedother_confirm(q, user, int(inner[:sep]), inner[sep+1:], context)

        # ===== ASTRO PAWS =====
        elif data.startswith("astro_reg_"):
            parts = data[10:].split("_")
            if len(parts) == 2:
                await astro_handle_register(q, user, int(parts[0]), int(parts[1]), context)

        elif data.startswith("astro_steal_"):
            parts = data[12:].split("_")
            if len(parts) == 2:
                await astro_handle_steal(q, user, int(parts[0]), int(parts[1]), context)

        elif data.startswith("astro_list_"):
            page = int(data[11:])
            await _send_astro_list(q.message, page, context, edit=True)

        elif data.startswith("a2_list_"):
            page = int(data[8:])
            await _send_astro2_list(q.message, page, context, edit=True)

        elif data == "astro_skip":
            await q.edit_message_reply_markup(reply_markup=None)

        # ===== ASTRO PAWS 2 =====
        elif data.startswith("a2_reg_"):
            parts = data[7:].split("_")
            if len(parts) == 2:
                await a2_handle_register(q, user, int(parts[0]), int(parts[1]), context)
        elif data.startswith("a2_steal_"):
            parts = data[9:].split("_")
            if len(parts) == 2:
                await a2_handle_steal(q, user, int(parts[0]), int(parts[1]), context)
        elif data == "a2_skip":
            await q.edit_message_reply_markup(reply_markup=None)

        # ===== AQUA TAILS =====
        elif data.startswith("aqua_"):
            await aqua_callback(q, user, data, context)

        # ===== FARM DAY =====
        elif data.startswith("fd_"):
            await farmday_callback(q, user, data, context)

        elif data.startswith("buy_"):
            await do_buy(q, user, data[4:])

        elif data.startswith("feed_"):
            await show_feed_menu(q, user, int(data[5:]))

        elif data.startswith("feeditem_"):
            # Format: feeditem_{pet_id}_{item_key} — item_key bisa mengandung underscore
            inner = data[9:]  # buang "feeditem_"
            sep = inner.index("_")
            pet_id_str = inner[:sep]
            item_key   = inner[sep+1:]
            await do_feed(q, user, int(pet_id_str), item_key, context)

        elif data.startswith("play_"):
            await do_play(q, user, int(data[5:]), context)

        elif data.startswith("heal_"):
            await do_heal(q, user, int(data[5:]))

        elif data.startswith("clean_"):
            await do_clean_poop(q, user, int(data[6:]), context)

        elif data.startswith("bath_"):
            await do_bath(q, user, int(data[5:]), context)

        elif data.startswith("status_"):
            await refresh_pet(q, user, int(data[7:]))

        elif data == "game_menu":
            await show_game_menu(q, user)

        elif data == "game_guess":
            await start_guess(q, user, context)

        elif data == "game_roll":
            await play_roll(q, user, context)

        elif data == "game_quiz":
            await start_quiz(q, user, context)

        elif data.startswith("qans_"):
            await answer_quiz(q, user, context, int(data[5:]))

        elif data == "game_catch":
            await start_catch(q, user, context)

        elif data.startswith("catch_"):
            await answer_catch(q, user, context, int(data[6:]))

        elif data == "daily":
            ok, msg = await claim_daily(user.id)
            u = await get_user(user.id)
            await q.edit_message_text(
                msg + f"\n\n💰 Total koin: <b>{u.get('koin',0)} 🪙</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
            )

        elif data == "my_coins":
            u = await get_user(user.id)
            await q.edit_message_text(
                f"💰 Koin kamu: <b>{u.get('koin', 0)} 🪙</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
            )

        elif data == "bot_stats":
            if user.id not in ADMIN_IDS:
                await q.answer("❌ Bukan owner!", show_alert=True); return
            total_u = await get_count("users")
            total_p = await get_count("pets")
            total_d = await get_count("deliveries")
            await q.edit_message_text(
                f"🔧 <b>Stats Bot</b>\n━━━━━━━━━━━━━━━\n"
                f"👤 Total users: <b>{total_u}</b>\n"
                f"🐾 Total pets: <b>{total_p}</b>\n"
                f"📦 Total deliveries: <b>{total_d}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
            )

        elif data.startswith("confirm_delete_"):
            pet_id = int(data[15:])
            await do_delete_pet(q, user, pet_id, context)

        elif data.startswith("find_pet_"):
            pet_id = int(data[9:])
            await do_find_pet(q, user, pet_id, context)

        elif data == "special_store":
            await show_special_store(q, user)

        elif data.startswith("spbuy_"):
            await do_spbuy(q, user, data[6:])

        elif data == "help":
            await show_help(q)

        elif data == "help_info":
            await show_help_info(q)

        # ===== MISI & TASK =====
        elif data == "task_menu":
            await show_tasks(q, user)

        elif data.startswith("task_verify_"):
            tid = data[12:]
            if tid == "join_quiz":
                await _verify_quiz_membership(context, user.id, reply_q=q)
            else:
                await q.answer("❌ Verifikasi tidak tersedia untuk task ini.", show_alert=True)

        elif data.startswith("task_claim_"):
            tid = data[11:]
            ok, msg = await do_task_claim(user.id, tid)
            if ok:
                await q.answer(f"🎉 Berhasil klaim! {msg}", show_alert=True)
                await show_tasks(q, user)
            else:
                await q.answer(msg, show_alert=True)

        # ===== LIVESTOCK =====
        elif data == "livestock_menu":
            await show_livestock_menu(q, user)

        elif data.startswith("buy_livestock_"):
            lt_type = data[14:]
            lt = LIVESTOCK.get(lt_type)
            if not lt:
                await q.answer("❌ Jenis ternak tidak valid!", show_alert=True); return
            # Cek kandang
            u_data = await get_user(user.id)
            barn_slots = u_data.get("barn_slots", 1)
            used = await get_count("livestocks", {"owner_id": f"eq.{user.id}"})
            if used >= barn_slots:
                await q.answer(f"🏚️ Kandang penuh! ({used}/{barn_slots}) Upgrade dulu~", show_alert=True); return
            context.user_data["buying_livestock"] = lt_type
            context.user_data["state"] = "ASK_LIVESTOCK_NAME"
            msg_text = f"✏️ Beli {lt['emoji']} <b>{lt['name']}</b>!\n\nKetik nama untuk ternak kamu:"
            try:
                await q.edit_message_text(msg_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"buy_livestock edit_message_text error: {e}")
                try:
                    await context.bot.send_message(user.id, msg_text, parse_mode=ParseMode.HTML)
                except Exception as e2:
                    logger.error(f"buy_livestock send_message fallback error: {e2}")

        elif data.startswith("livestock_view_"):
            await show_livestock_detail(q, user, int(data[15:]))

        elif data == "send_item_confirm":
            await do_send_item_confirm(q, user, context)

        # ===== ADMIN LEVELUP =====
        elif data.startswith("admin_lvup_"):
            if user.id not in ADMIN_IDS:
                await q.answer("❌ Bukan admin!", show_alert=True); return
            # Format: admin_lvup_{pet_id}_{new_level}
            parts = data[11:].rsplit("_", 1)
            pet_id_al = int(parts[0])
            new_lv_al = int(parts[1])
            pet_al = await get_pet_by_id(pet_id_al)
            if not pet_al:
                await q.answer("❌ Pet tidak ditemukan!", show_alert=True); return
            await _do_admin_levelup(q, pet_al, new_lv_al, context, is_callback=True)

        # ===== LIVESTOCK SELL ANIMAL =====
        elif data.startswith("livestock_sell_animal_confirm_"):
            await do_livestock_sell_animal_confirm(q, user, int(data[30:]))

        elif data.startswith("livestock_sell_animal_"):
            await do_livestock_sell_animal(q, user, int(data[22:]))

        elif data.startswith("livestock_sell_"):
            await do_livestock_sell(q, user, int(data[15:]))

        elif data.startswith("livestock_save_"):
            await do_livestock_save(q, user, int(data[15:]))

        elif data.startswith("livestock_collect_"):
            await do_collect_livestock(q, user, int(data[18:]))

        elif data == "barn_upgrade":
            await do_barn_upgrade(q, user)

        # ===== TOP UP =====
        elif data.startswith("amplop_status_"):
            await show_amplop_status(q, user, data[14:])

        elif data == "gacha_menu":
            await show_gacha_menu(q, user)

        elif data == "gacha_open_biasa":
            await do_gacha_open(q, user, "biasa", context)

        elif data == "gacha_open_premium":
            await do_gacha_open(q, user, "premium", context)

        elif data.startswith("gacha_use_"):
            # rsplit dari kanan: "gacha_use_xp_booster_0" → item_key="xp_booster", pet_id=0
            inner = data[10:]  # buang prefix "gacha_use_"
            rparts = inner.rsplit("_", 1)
            item_key_parsed = rparts[0]
            pet_id_parsed = int(rparts[1]) if len(rparts) > 1 and rparts[1].isdigit() else 0
            await do_use_gacha_item(q, user, item_key_parsed, pet_id_parsed, context)

        elif data == "topup_cancel":
            context.user_data["state"] = None
            context.user_data["topup_amount"] = None
            await q.answer("✅ Top up dibatalkan!", show_alert=False)
            pet_lv = await get_pet_level(user.id)
            try:
                await q.edit_message_caption(
                    "❌ <b>Top up dibatalkan.</b>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

        elif data == "topup_start":
            context.user_data["state"] = "ASK_TOPUP_AMOUNT"
            await q.message.reply_text(
                "💳 <b>Top Up Koin</b>\n"
                "━━━━━━━━━━━━━━━\n\n"
                "💡 <b>Harga:</b> Rp 1.000 = 1.000 🪙\n"
                f"📦 <b>Minimum:</b> {TOPUP_MIN:,} 🪙 (Rp {TOPUP_MIN:,})\n\n"
                "Ketik jumlah koin yang ingin kamu beli:\n"
                "<i>Contoh: 10000 → dapat 10.000 🪙 seharga Rp 10.000</i>"
                + (_aqua_topup_bonus_info() if AQUA_TOPUP_BONUS_ACTIVE else ""),
                parse_mode=ParseMode.HTML
            )

        elif data == "buatitem_start":
            u = await get_user(user.id)
            koin = (u.get("koin") or 0)
            await q.edit_message_text(
                "🛠️ <b>Buat Item Sendiri</b>\n━━━━━━━━━━━━━━━\n\n"
                "Kamu bisa bikin item custom sendiri!\n\n"
                f"💰 Biaya: <b>1.000 🪙</b> → dapat <b>5 item</b>\n"
                f"💳 Koinmu sekarang: <b>{koin} 🪙</b>\n\n"
                "Pilih jenis item yang mau dibuat:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍖 Makanan", callback_data="buatitem_type_food"),
                     InlineKeyboardButton("👒 Aksesoris", callback_data="buatitem_type_accessory")],
                    [InlineKeyboardButton("🔙 Kembali", callback_data="carpet_shop")],
                ])
            )

        elif data.startswith("buatitem_type_"):
            item_type = data[14:]  # "food" or "accessory"
            context.user_data["buatitem_type"] = item_type
            context.user_data["state"] = "ASK_BUATITEM_NAMA"
            type_label = "Makanan 🍖" if item_type == "food" else "Aksesoris 👒"
            await q.edit_message_text(
                f"🛠️ <b>Buat Item: {type_label}</b>\n━━━━━━━━━━━━━━━\n\n"
                "Ketik <b>nama item</b> yang kamu mau:\n"
                "<i>Contoh: Kue Coklat, Topi Lucu, dll (maks 20 karakter)</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="carpet_shop")]])
            )

        elif data == "buatitem_confirm":
            item_nama  = context.user_data.get("buatitem_nama")
            item_emoji = context.user_data.get("buatitem_emoji", "🎁")
            item_type  = context.user_data.get("buatitem_type", "food")
            context.user_data["state"] = None

            if not item_nama:
                await q.answer("❌ Data item tidak lengkap, mulai ulang!", show_alert=True)
                return

            # Bayar 1000 koin
            ok = await spend_koin(user.id, 1000, "beli_topup_koin")
            if not ok:
                await q.answer("❌ Koin tidak cukup! Butuh 1.000 🪙", show_alert=True)
                return

            # Buat key unik untuk inventory: "custom_TIMESTAMP_userid"
            item_key = f"ci_{user.id}_{int(time.time())}"

            # Simpan definisi item custom ke DB (tabel custom_items)
            item_data = {
                "owner_id":   user.id,
                "item_key":   item_key,
                "name":       item_nama,
                "emoji":      item_emoji,
                "item_type":  item_type,  # "food" or "accessory"
                "hunger":     30 if item_type == "food" else 0,
                "xp":         5  if item_type == "food" else 0,
                "happy":      0,
                "created_at": now_wib().isoformat(),
            }
            await sb("POST", "custom_items", data=item_data)

            # Tambah 5 item ke inventory
            inv = await get_inv(user.id)
            inv[item_key] = (inv.get(item_key) or 0) + 5
            await set_inv(user.id, inv)

            type_label = "Makanan 🍖" if item_type == "food" else "Aksesoris 👒"
            await q.edit_message_text(
                f"🎉 <b>Item berhasil dibuat!</b>\n━━━━━━━━━━━━━━━\n\n"
                f"{item_emoji} <b>{safe_html(item_nama)}</b>\n"
                f"📦 Jenis: {type_label}\n"
                f"🎁 Kamu dapat <b>5 item</b> yang sudah masuk inventori!\n\n"
                f"<i>Pakai item dari menu pet → kasih makan / aksesoris</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎒 Lihat Inventori", callback_data="inventory")],
                    [InlineKeyboardButton("🔙 Shop", callback_data="carpet_shop")],
                ])
            )
            await log(context, f"🛠️ Buat item: {item_emoji} <b>{safe_html(item_nama)}</b> ({item_type}) owner <code>{user.id}</code>")

        elif data.startswith("topup_accept_"):
            # Hanya admin yang bisa
            if user.id not in ADMIN_IDS:
                await q.answer("❌ Bukan admin!", show_alert=True); return
            # Format: topup_accept_{user_id}_{amount} — rsplit dari kanan supaya aman
            inner = data[13:]
            rparts = inner.rsplit("_", 1)
            if len(rparts) != 2 or not rparts[0].isdigit() or not rparts[1].isdigit():
                await q.answer("❌ Format callback tidak valid!", show_alert=True); return
            target_id = int(rparts[0])
            amount    = int(rparts[1])
            await add_koin(target_id, amount, "topup")
            asyncio.create_task(task_inc(target_id, "topup_4k", amount))

            # Bonus koin event (kalau aktif)
            bonus_koin = _topup_bonus_amount(amount)
            bonus_koin_text = ""
            if bonus_koin > 0:
                await add_koin(target_id, bonus_koin, "topup_bonus")
                bonus_koin_text = f"\n🎁 +{bonus_koin:,} 🪙 (bonus event!)"

            # Kasih makanan sesuai nominal (per 1000 dapat 1 makanan biasa + 1 premium)
            food_qty = amount // 1000
            food_bonus_text = ""
            _cdel(_user_cache, target_id)  # flush cache sebelum baca inventory
            inv = await get_inv(target_id)
            if food_qty > 0:
                if MAKANAN_TOPUP_ACTIVE:
                    actual_qty = food_qty * 2
                    inv["meal"]    = (inv.get("meal") or 0) + actual_qty
                    inv["premium"] = (inv.get("premium") or 0) + actual_qty
                    inv["treat"]   = (inv.get("treat") or 0) + actual_qty
                    inv["rendang"] = (inv.get("rendang") or 0) + actual_qty
                    food_bonus_text = (
                        f"\n🍖 +{actual_qty}x Makanan & 🥩 +{actual_qty}x Makanan Premium"
                        f" & 🍬 +{actual_qty}x Camilan Spesial & 🍖 +{actual_qty}x Rendang\n"
                        f"<i>(2× Makanan Topup Event aktif!)</i>"
                    )
                else:
                    inv["meal"]    = (inv.get("meal") or 0) + food_qty
                    inv["premium"] = (inv.get("premium") or 0) + food_qty
                    food_bonus_text = f"\n🍖 +{food_qty}x Makanan & 🥩 +{food_qty}x Makanan Premium"

            # Bonus: 1 item gacha random
            gacha_bonus_key = _gacha_roll_item(GACHA_BIASA_TABLE)
            gi_bonus = GACHA_ITEMS[gacha_bonus_key]
            inv[gacha_bonus_key] = (inv.get(gacha_bonus_key) or 0) + 1
            food_bonus_text += f"\n{gi_bonus['emoji']} +1x {gi_bonus['name']} (bonus gacha!)"

            await set_inv(target_id, inv)

            # Kasih kartu custom pet kalau event aktif dan user belum dapat di event ini
            custom_pet_bonus_text = ""
            if CUSTOM_PET_EVENT_ACTIVE:
                try:
                    _cdel(_user_cache, target_id)
                    claimed_res = await sb("GET", "users", {
                        "user_id": f"eq.{target_id}",
                        "select": "user_id,custom_pet_claimed_event"
                    })
                    claimed_event = claimed_res[0].get("custom_pet_claimed_event") if claimed_res else None
                    if not claimed_event or claimed_event != "active":
                        inv_fresh = await get_inv(target_id)
                        inv_fresh["custom_pet_card"] = (inv_fresh.get("custom_pet_card") or 0) + 1
                        await set_inv(target_id, inv_fresh)
                        await sb("PATCH", "users", {"user_id": f"eq.{target_id}"},
                                 {"custom_pet_claimed_event": "active"})
                        _cdel(_user_cache, target_id)
                        custom_pet_bonus_text = "\n🎨 +1 Kartu Custom Pet (bonus event!)"
                except Exception as e:
                    logger.warning(f"Custom pet event bonus error: {e}")

            # Astro Paws topup bonus
            astro_bonus_text = ""
            try:
                astro_bonus_text = await _astro_topup_bonus(target_id, amount, context)
                if astro_bonus_text:
                    astro_bonus_text = "\n🚀 <b>Astro Paws Bonus:</b>\n" + astro_bonus_text
            except Exception as e:
                logger.warning(f"Astro topup bonus error: {e}")
            # Astro Paws 2 topup bonus
            a2_bonus_text = ""
            try:
                a2_bonus_text = await _a2_topup_bonus(target_id, amount, context)
                if a2_bonus_text:
                    a2_bonus_text = "\n🔴 <b>Astro Paws 2 Bonus:</b>\n" + a2_bonus_text
            except Exception as e:
                logger.warning(f"Astro2 topup bonus error: {e}")
            # Aqua Tails topup bonus
            aqua_bonus_text = ""
            try:
                aqua_bonus_text = await _aqua_topup_bonus(target_id, amount, context)
                if aqua_bonus_text:
                    aqua_bonus_text = "\n🎣 <b>Aqua Tails Bonus:</b>\n" + aqua_bonus_text
            except Exception as e:
                logger.warning(f"Aqua topup bonus error: {e}")

            # Edit pesan di grup jadi sudah diterima
            await q.edit_message_caption(
                (q.message.caption or "") + f"\n\n✅ <b>ACCEPTED</b> oleh {safe_html(user.first_name)}"
                + (f"\n🎁 Bonus koin: +{bonus_koin:,} 🪙" if bonus_koin > 0 else ""),
                parse_mode=ParseMode.HTML
            )
            # Notif ke user
            try:
                await context.bot.send_message(
                    target_id,
                    f"✅ <b>Top Up Berhasil!</b>\n\n"
                    f"💰 <b>{amount:,} 🪙</b> sudah masuk ke akunmu!{bonus_koin_text}{food_bonus_text}{custom_pet_bonus_text}{astro_bonus_text}{a2_bonus_text}{aqua_bonus_text}\n\n"
                    f"Selamat berbelanja~ 🐾",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Cek Koin", callback_data="my_coins")]])
                )
            except: pass
            extra = f" + bonus {bonus_koin:,} koin" if bonus_koin > 0 else ""
            await q.answer(f"✅ {amount:,} koin{extra} + makanan + gacha dikirim ke {target_id}!", show_alert=True)

        elif data.startswith("topup_reject_"):
            if user.id not in ADMIN_IDS:
                await q.answer("❌ Bukan admin!", show_alert=True); return
            inner2 = data[13:]
            rparts2 = inner2.rsplit("_", 1)
            if len(rparts2) != 2 or not rparts2[0].isdigit() or not rparts2[1].isdigit():
                await q.answer("❌ Format tidak valid!", show_alert=True); return
            target_id = int(rparts2[0])
            amount    = int(rparts2[1])
            await q.edit_message_caption(
                (q.message.caption or "") + f"\n\n❌ <b>DITOLAK</b> oleh {safe_html(user.first_name)}",
                parse_mode=ParseMode.HTML
            )
            try:
                await context.bot.send_message(
                    target_id,
                    f"❌ <b>Top Up Ditolak</b>\n\n"
                    f"Permintaan top up <b>{amount:,} 🪙</b> kamu ditolak.\n"
                    f"Hubungi @carpetshelpbot jika ada pertanyaan.",
                    parse_mode=ParseMode.HTML
                )
            except: pass
            await q.answer("❌ Top up ditolak.", show_alert=True)

        # ===== ID CARD =====
        elif data == "idcard_settings":
            existing = await sb("GET", "idcards", {"user_id": f"eq.{user.id}", "select": "user_id,card_name"})
            if existing:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📷 Lihat ID Card", callback_data="idcard_view")],
                    [InlineKeyboardButton("🔄 Buat Ulang (500 🪙)", callback_data="idcard_remake")],
                    [InlineKeyboardButton("🔙 Kembali", callback_data="settings")],
                ])
                await q.edit_message_text(
                    f"📇 <b>Carpets ID Card</b>\n\nKamu sudah punya ID Card atas nama <b>{safe_html(existing[0]['card_name'])}</b>!",
                    parse_mode=ParseMode.HTML, reply_markup=kb
                )
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🆕 Buat ID Card (500 🪙)", callback_data="idcard_make")],
                    [InlineKeyboardButton("🔙 Kembali", callback_data="settings")],
                ])
                await q.edit_message_text(
                    "📇 <b>Carpets ID Card</b>\n\nBelum punya ID Card nih!\nBuat sekarang seharga <b>500 🪙</b>?",
                    parse_mode=ParseMode.HTML, reply_markup=kb
                )

        elif data == "idcard_make":
            await _idcard_start_make(update, context, is_remake=False)

        elif data == "idcard_remake":
            await _idcard_start_make(update, context, is_remake=True)

        elif data == "idcard_view":
            existing = await sb("GET", "idcards", {"user_id": f"eq.{user.id}", "select": "file_id,card_name"})
            if existing:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=existing[0]["file_id"],
                    caption="📇 <b>ID Card kamu!</b>\n<i>Ketik /idcard untuk buat ulang~</i>",
                    parse_mode=ParseMode.HTML
                )
                await q.answer()
            else:
                await q.answer("ID Card tidak ditemukan!", show_alert=True)

        elif data == "idcard_cancel":
            await q.edit_message_text("❌ Dibatalkan.")

        # ===== BOARDING =====
        elif data.startswith("boarding_pickup_"):
            await do_boarding_pickup(q, user, int(data[16:]))

        elif data.startswith("boarding_confirm_"):
            parts = data[17:].split("_")
            await do_boarding_confirm(q, user, int(parts[0]), int(parts[1]))

        elif data.startswith("boarding_"):
            pet_id = int(data[9:])
            await show_boarding_menu(q, user, pet_id)

        # ===== EXPEDITION =====
        elif data.startswith("expedition_check_"):
            await show_expedition_status(q, user, int(data[17:]))

        elif data.startswith("expstart_"):
            parts = data[9:].split("_", 1)
            await do_start_expedition(q, user, int(parts[0]), parts[1], context)

        elif data.startswith("expedition_"):
            pet_id = int(data[11:])
            await show_expedition_menu(q, user, pet_id)

        # ===== BATTLE =====
        elif data.startswith("battle_menu_"):
            await show_battle_menu(q, user, int(data[12:]))

        elif data.startswith("battle_accept_pet_"):
            # Format: battle_accept_pet_{pet_id}_{battle_code}
            parts = data[18:].rsplit("_", 1)  # split dari kanan 1x
            my_pet_id = int(parts[0])
            battle_code = parts[1]
            my_pet = await get_pet_by_id(my_pet_id)
            battles_res = await sb("GET", "battles", {"code": f"eq.{battle_code}", "status": "eq.waiting"})
            if not battles_res:
                await q.answer("❌ Battle sudah selesai!", show_alert=True); return
            battle = battles_res[0]
            await _execute_battle(q, context, battle, battle_code, user, my_pet)

        elif data.startswith("battle_start_"):
            await do_battle(q, user, data[13:], context)

        # ===== MARRIAGE =====
        elif data.startswith("marriage_confirm_"):
            await do_marriage(q, user, int(data[17:]), context)

        elif data.startswith("marry_choose_"):
            # Format: marry_choose_{pet_id}_{marry_code}
            parts = data[13:].rsplit("_", 1)
            my_pet_id = int(parts[0])
            marry_code = parts[1]
            my_pet = await get_pet_by_id(my_pet_id)
            proposal_res = await sb("GET", "marriage_proposals", {"code": f"eq.{marry_code}", "select": "id,code,status,pet1_id,pet2_id,owner1_pet1,owner2_pet1,owner1_pet2,owner2_pet2,approved_by"})
            if proposal_res and my_pet:
                await _set_marriage_pet2(q, context, marry_code, proposal_res[0], user, my_pet)
            else:
                await q.answer("❌ Proposal tidak ditemukan!", show_alert=True)

        elif data.startswith("marriage_"):
            await show_marriage_menu(q, user, int(data[9:]))

        # ===== SETTINGS =====
        elif data == "settings":
            await show_settings(q, user)

        elif data == "settings_nickname":
            context.user_data["state"] = "ASK_NICKNAME"
            await q.edit_message_text(
                "👤 <b>Ganti Nickname</b>\n\nKetik nickname baru kamu~\n<i>Contoh: Kakak, Ayah, Bunda</i>",
                parse_mode=ParseMode.HTML
            )

        elif data.startswith("settings_rename_"):
            pet_id = int(data[16:])
            context.user_data["renaming_pet"] = pet_id
            context.user_data["state"] = "ASK_PET_RENAME"
            pet = await get_pet_by_id(pet_id)
            await q.edit_message_text(
                f"✏️ Ketik nama baru untuk <b>{pet['name']}</b>:",
                parse_mode=ParseMode.HTML
            )

        elif data == "settings_deletepet":
            await cmd_deletepet_inline(q, user, context)

        elif data == "settings_transfer":
            context.user_data["state"] = "ASK_TRANSFER_TARGET"
            await q.edit_message_text(
                "💸 <b>Transfer Koin</b>\n\nKetik <b>username</b> atau <b>user ID</b> penerima:",
                parse_mode=ParseMode.HTML
            )

        # ===== TRANSFER =====
        elif data == "transfer_koin":
            context.user_data["state"] = "ASK_TRANSFER_TARGET"
            await q.edit_message_text(
                "💸 <b>Transfer Koin</b>\n\nKetik <b>username</b> atau <b>user ID</b> penerima:",
                parse_mode=ParseMode.HTML
            )

        # ===== ACCESSORY =====
        elif data.startswith("remove_acc_"):
            await do_remove_accessory(q, user, int(data[11:]))

        elif data.startswith("acc_select_pet_"):
            # Format: acc_select_pet_{item_key} — pilih pet dulu baru equip
            item_key = data[15:]
            pets = await get_user_pets(user.id)
            if not pets:
                await q.answer("❌ Kamu belum punya pet!", show_alert=True); return
            custom_map = await get_custom_items_map(user.id)
            ci = custom_map.get(item_key, {})
            if len(pets) == 1:
                await do_equip_accessory(q, user, item_key, pets[0]["id"], context)
            else:
                buttons = [
                    [InlineKeyboardButton(
                        f"{PETS.get(p['pet_type'], {}).get('emoji','🐾')} {p['name']}",
                        callback_data=f"equip_acc_{item_key}_{p['id']}"
                    )] for p in pets
                ]
                buttons.append([InlineKeyboardButton("🔙 Batal", callback_data="inventory")])
                await q.edit_message_text(
                    f"👒 Pasang <b>{ci.get('emoji','')} {safe_html(ci.get('name',''))}</b> ke pet mana?",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )

        elif data.startswith("equip_acc_"):
            # Format: equip_acc_{item_key}_{pet_id}
            parts = data[10:].rsplit("_", 1)
            await do_equip_accessory(q, user, parts[0], int(parts[1]), context)

        elif data.startswith("equip_pet_select_"):
            # Format: equip_pet_select_{item_key}_{pet_id}
            parts = data[17:].rsplit("_", 1)
            await do_equip_accessory(q, user, parts[0], int(parts[1]), context)

        # ===== PARTNER MANAGEMENT =====
        elif data.startswith("pet_add_partner_"):
            await show_add_partner(q, user, int(data[16:]))

        elif data.startswith("pet_change_partner_confirm_"):
            await do_change_partner(q, user, int(data[27:]))

        elif data.startswith("pet_change_partner_"):
            await show_change_partner(q, user, int(data[19:]))

        elif data.startswith("pet_remove_partner_confirm_"):
            await do_remove_partner(q, user, int(data[27:]))

        elif data.startswith("pet_remove_partner_"):
            await show_remove_partner_confirm(q, user, int(data[19:]))

        # ===== CERAI =====
        elif data.startswith("pet_divorce_confirm_"):
            await do_divorce(q, user, int(data[20:]), context)

        elif data.startswith("pet_divorce_"):
            await show_divorce_confirm(q, user, int(data[12:]))

        # ===== DAPUR MBG =====
        elif data == "mbg_kitchen":
            await show_mbg_kitchen(q, user)

        elif data.startswith("mbg_cook_"):
            await do_mbg_cook(q, user, data[9:])

        elif data.startswith("mbg_feed_"):
            # Format: mbg_feed_{pet_id}_{biasa|special}
            parts = data[9:].rsplit("_", 1)
            await do_feed_mbg(q, user, int(parts[0]), parts[1], context)

        # ===== PIL =====
        elif data.startswith("pil_use_"):
            # Format: pil_use_anti_pup__{pet_id} or pil_use_anti_lapar__{pet_id}
            inner = data[8:]  # e.g. "anti_pup__123" or "anti_lapar__456"
            parts = inner.rsplit("__", 1)
            if len(parts) == 2 and parts[1].isdigit():
                await do_use_pil(q, user, int(parts[1]), parts[0])
            else:
                await q.answer("❌ Format tidak valid!", show_alert=True)

        elif data.startswith("pil_levelup_use_"):
            await do_use_pil_levelup(q, user, int(data[16:]))

        # ===== SEKOLAH & PROFESI =====
        elif data.startswith("pet_profesi_") and not data.startswith("pet_profesi_set_"):
            pet_id = int(data[12:])
            await show_profesi_pilih(q, user, pet_id)

        elif data.startswith("pet_profesi_set_"):
            parts = data[16:].rsplit("_", 1)
            await do_profesi_set(q, user, int(parts[0]), parts[1])

        elif data.startswith("pet_profwork_confirm_"):
            await do_profesi_work(q, user, int(data[21:]), context)

        elif data.startswith("pet_profwork_"):
            await show_profesi_work(q, user, int(data[13:]), context)

        elif data.startswith("pet_sekolah_confirm_"):
            await do_sekolah(q, user, int(data[20:]), context)

        elif data.startswith("pet_sekolah_"):
            await show_sekolah(q, user, int(data[12:]))

        # ===== CUSTOM PET =====
        elif data == "custom_pet_show":
            await show_custom_pet_card(q, user)

        elif data == "custom_pet_start":
            await start_custom_pet_flow(q, user, context)

        elif data.startswith("cpt_type_"):
            await custom_pet_choose_personality(q, user, data[9:], context)

        elif data.startswith("cpt_pers_"):
            await custom_pet_choose_ability1(q, user, data[9:], context)

        elif data.startswith("cpt_ab1_"):
            await custom_pet_choose_ability2(q, user, data[8:], context)

        elif data.startswith("cpt_ab2_"):
            await custom_pet_ask_name(q, user, data[8:], context)

        # ===== CHILD RECOVER =====
        elif data.startswith("child_recover_confirm_"):
            await do_child_recover(q, user, int(data[22:]), context)

        elif data.startswith("child_recover_"):
            await show_child_recover(q, user, int(data[14:]))

        # ===== INVENTORI: PILIH PET UNTUK PIL / MBG =====
        elif data.startswith("inv_select_pet_"):
            pil_type = data[15:]  # e.g. "pil_anti_pup", "mbg_biasa", "mbg_special", "pil_levelup"
            pets = await get_user_pets(user.id)
            active = [p for p in pets if not p.get("is_missing")]
            if not active:
                await q.answer("❌ Tidak punya pet!", show_alert=True); return
            is_mbg = pil_type in ("mbg_biasa", "mbg_special")
            # Item makanan Astro (mega_feast/moon_cake/dll) di-handle do_feed, BUKAN do_use_pil
            is_astro_food = pil_type in ASTRO_FOOD_INV_KEYS
            if len(active) == 1:
                pet = active[0]
                if is_mbg:
                    await do_feed_mbg(q, user, pet["id"], pil_type.replace("mbg_", ""), context)
                elif pil_type == "pil_levelup":
                    await do_use_pil_levelup(q, user, pet["id"])
                elif is_astro_food:
                    await do_feed(q, user, pet["id"], pil_type, context)
                else:
                    await do_use_pil(q, user, pet["id"], pil_type.replace("pil_", ""))
            else:
                buttons = []
                for p in active:
                    info = PETS.get(p["pet_type"], {"emoji": "🐾"})
                    if is_mbg:
                        cb = f"feeditem_{p['id']}_{pil_type}"
                    elif pil_type == "pil_levelup":
                        cb = f"pil_levelup_use_{p['id']}"
                    elif is_astro_food:
                        cb = f"feeditem_{p['id']}_{pil_type}"
                    else:
                        cb = f"pil_use_{pil_type.replace('pil_','')}__{p['id']}"
                    buttons.append([InlineKeyboardButton(
                        f"{info['emoji']} {p['name']} Lv.{calc_level(p.get('xp',0))}",
                        callback_data=cb
                    )])
                buttons.append([InlineKeyboardButton("❌ Batal", callback_data="inventory")])
                label = "🍱 Kasih MBG ke pet mana?" if is_mbg else "🍽️ Kasih makan ke pet mana?" if is_astro_food else "💊 Pakai pil ke pet mana?"
                await q.edit_message_text(
                    label, parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )

    except BadRequest as e:
        emsg = str(e)
        if "Message is not modified" in emsg:
            pass  # tidak ada perubahan, abaikan
        elif "Message to edit not found" in emsg or "message can't be edited" in emsg or "MESSAGE_ID_INVALID" in emsg:
            # Pesan asal sudah hilang/kadaluarsa — bukan bug, kirim ulang menu utama
            try:
                pet_lv = await get_pet_level(user.id)
                await context.bot.send_message(
                    user.id,
                    "🔄 Pesan lama sudah kedaluwarsa~ Ini menu terbarunya:",
                    reply_markup=kb_main(user.id, pet_lv)
                )
            except Exception:
                try:
                    await context.bot.send_message(user.id, "🔄 Pesan lama sudah kedaluwarsa~ Ketik /menu untuk buka menu lagi.")
                except Exception:
                    pass
        else:
            logger.error(f"BadRequest: {e}")
            await _send_error_detail(context, user, e, where="callback/BadRequest", data=data)
    except Exception as e:
        logger.error(f"btn error: {e}")
        await _send_error_detail(context, user, e, where="callback", data=data)

# ==================== SHOP ====================
async def show_shop(q):
    await q.edit_message_text(
        "🏪 <b>The Carpet Shop</b>\n━━━━━━━━━━━━━━━\n"
        "Pilih hewan yang mau kamu adopsi!\n\n"
        "⭐ = Hewan Langka (butuh koin)\n"
        "🐾 = Hewan Biasa (gratis)\n\n"
        "📌 <b>Sistem Partner:</b>\n"
        "• Setelah kamu pilih hewan, kamu dapat <b>kode invite</b>\n"
        "• Bagikan ke 1 teman untuk rawat bareng\n"
        "• Pengiriman baru mulai setelah partner join!\n"
        "• Butuh <b>6 tap</b> untuk percepat pengiriman",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_shop()
    )

# ==================== ADOPT FLOW ====================
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    if not user or not update.message:
        return
    state = context.user_data.get("state")
    text  = update.message.text.strip() if update.message.text else ""

    # Force subscribe
    if not await check_force_sub(update, context):
        return

    # Cek astro lock AP1+AP2
    if not state:
        locked, lock_status, unlock_time = await astro_is_locked(user.id)
        if not locked:
            locked, lock_status, unlock_time = await a2_is_locked(user.id)
        if locked:
            await astro_send_lock_msg(update.message, lock_status, unlock_time); return

    # Handle reply keyboard shortcuts
    if not state:
        if text == "🐾 Pet Saya":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            # Langsung ke pet, tanpa menu utama
            await show_my_pet_direct(update, user, context)
            return
        elif text == "🏪 Carpet Shop":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            await update.message.reply_text(
                "🏪 <b>The Carpet Shop</b>\nPilih hewan yang mau kamu adopsi!",
                parse_mode=ParseMode.HTML, reply_markup=kb_shop()
            )
            return
        elif text == "🎒 Inventori":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            class _FakeQInv:
                def __init__(self, msg): self._msg = msg
                async def edit_message_text(self, *a, **kw):
                    kw.pop("disable_web_page_preview", None)
                    await self._msg.reply_text(*a, **kw)
                async def answer(self, *a, **kw): pass
            await show_inventory(_FakeQInv(update.message), user)
            return
        elif text == "🛒 Toko Makan":
            u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            await update.message.reply_text(
                f"🛒 <b>Toko Makanan</b>\n💰 Koinmu: <b>{u.get('koin',0)} 🪙</b>\n━━━━━━━━━━━━━━━",
                parse_mode=ParseMode.HTML, reply_markup=kb_food_shop()
            )
            return
        elif text == "🎯 Misi & Task":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            await cmd_task(update, context)
            return
        elif text == "🎮 Mini Game":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            await update.message.reply_text("🎮 <b>Mini Game</b>", parse_mode=ParseMode.HTML, reply_markup=kb_game())
            return
        elif text == "📊 Status":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            class _FakeQSt:
                def __init__(self, msg): self._msg = msg
                async def edit_message_text(self, *a, **kw):
                    kw.pop("disable_web_page_preview", None)
                    await self._msg.reply_text(*a, **kw)
                async def answer(self, *a, **kw): pass
            await show_status(_FakeQSt(update.message), user)
            return
        elif text == "🚶 Jalan Jalan":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            await update.message.reply_text(
                "🚶 <b>Jalan-Jalan</b>\n━━━━━━━━━━━━━━━\nMau ke mana hari ini?",
                parse_mode=ParseMode.HTML, reply_markup=kb_jalan()
            )
            return
        elif text == "⚙️ Settings":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            class _FakeQSet:
                def __init__(self, msg): self._msg = msg
                async def edit_message_text(self, *a, **kw):
                    kw.pop("disable_web_page_preview", None)
                    await self._msg.reply_text(*a, **kw)
                async def answer(self, *a, **kw): pass
            await show_settings(_FakeQSet(update.message), user)
            return
        elif text == "💳 Top Up Koin":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            await cmd_topup_start(update, context)
            return

        elif text == "❓ Bantuan":
            await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
            # Kirim info kontak dulu (seperti show_help_info), lalu bantuan ringkas
            await update.message.reply_text(
                "❓ <b>Help & Info</b>\n━━━━━━━━━━━━━━━\n\n"
                "Butuh bantuan atau pertanyaan tentang bot ini?\n\n"
                "💬 <b>Kontak untuk pertanyaan & bantuan:</b>\n@carpetsrobot\n\n"
                "📋 <b>Info update Carpets:</b>\n@listbotfoocl\n\n"
                "━━━━━━━━━━━━━━━\n<i>Kami siap membantu kamu~ 🐾</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Contact: @carpetshelpbot", url="https://t.me/carpetshelpbot")],
                    [InlineKeyboardButton("📋 Update: @listbotfoocl", url="https://t.me/listbotfoocl")],
                    [InlineKeyboardButton("❓ Bantuan Lengkap", callback_data="help"),
                     InlineKeyboardButton("🐄 Ternak", callback_data="livestock_menu")],
                    [InlineKeyboardButton("🔙 Menu", callback_data="main_menu"), InlineKeyboardButton("📋 List Bot", url=SHOP_URL)],
                ])
            )
            return

    if state == "ASK_RUMAH_ID":
        context.user_data["state"] = None
        raw = (text or "").strip().lstrip("@")
        if not raw.isdigit():
            await update.message.reply_text(
                "❌ ID harus berupa angka. Coba lagi dari menu Jalan-Jalan ya~",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Coba Lagi", callback_data="jalan_rumah")]])
            )
            return
        await show_rumah_pets(update.message, user, int(raw), context, is_msg=True)
        return

    if state == IDCARD_ASK_NAME:
        await _idcard_process_name(update, context)
        return

    if state == ASK_PET_NAME:
        name = update.message.text.strip()
        if len(name) < 2 or len(name) > 20:
            await update.message.reply_text("⚠️ Nama harus 2–20 karakter, coba lagi:")
            return
        pet_type = context.user_data.get("adopting", "cat")
        context.user_data["state"] = None
        info  = PETS[pet_type]
        price = info["price"]

        # Deduct coins for rare pets
        if price > 0:
            ok = await spend_koin(user.id, price, "adopt_pet")
            if not ok:
                await update.message.reply_text("❌ Koin tidak cukup!")
                return

        # Create delivery (status: MENUNGGU partner)
        kode_invite = f"PET{random.randint(10000,99999)}"
        code        = f"DEL{random.randint(10000,99999)}"
        saved = await upsert_delivery({
            "code":        code,
            "owner1_id":   user.id,
            "owner1_name": safe_html(user.first_name) or safe_html(user.username) or str(user.id),
            "pet_type":    pet_type,
            "pet_name":    name,
            "arrive_at":   None,           # Belum dimulai, tunggu partner
            "taps":        {str(user.id): now_wib().isoformat()},
            "tap_count":   1,
            "kode_invite": kode_invite,
            "owner2_id":   None,
            "owner2_name": None,
            "started":     False,
            "is_delivered": False,
            "created_at":  now_wib().isoformat(),
        })
        if not saved:
            # Refund koin kalau gagal simpan
            if price > 0:
                await add_koin(user.id, price, "refund_adopt")
            await update.message.reply_text(
                "❌ Gagal menyimpan data ke server. Coba lagi dalam beberapa detik!",
                parse_mode=ParseMode.HTML
            )
            logger.error(f"upsert_delivery GAGAL untuk {user.id} kode={kode_invite}")
            return

        bot_name = BOT_USERNAME.lstrip("@")
        invite_link = f"https://t.me/{bot_name}?start={kode_invite}"

        text = (
            f"🎉 Kamu mau adopsi {info['emoji']} <b>{name}</b>!\n\n"
            f"Mau rawat sendirian atau bareng partner?\n\n"
            f"👤 <b>Solo</b> — pet langsung tiba, rawat sendiri.\n"
            f"   Kamu tetap bisa invite partner kapan saja nanti!\n\n"
            f"👫 <b>Bareng Partner</b> — bagikan kode ke 1 teman,\n"
            f"   rawat bareng setelah partner join (5 jam / 6 tap)."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Rawat Sendiri (Solo)", callback_data=f"adopt_solo_{code}")],
            [InlineKeyboardButton("👫 Bareng Partner", callback_data=f"adopt_partner_{code}")],
            [InlineKeyboardButton("❌ Batal", callback_data="carpet_shop")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        await log(context, f"🐾 Adopt baru: {fmt_user(user)} mau adopt {info['emoji']} {name}")

    elif state == "ASK_LIVESTOCK_NAME":
        lt_type = context.user_data.get("buying_livestock")
        lt = LIVESTOCK.get(lt_type)
        if not lt:
            context.user_data["state"] = None; return
        lname = text
        if len(lname) < 2 or len(lname) > 20:
            await update.message.reply_text("⚠️ Nama harus 2–20 karakter, coba lagi:"); return
        context.user_data["state"] = None
        ok = await spend_koin(user.id, lt["price"], "beli_item")
        if not ok:
            await update.message.reply_text(f"❌ Koin tidak cukup! Butuh {lt['price']} 🪙"); return
        res = await sb("POST", "livestocks", data={
            "owner_id":  user.id, "lt_type": lt_type, "name": lname,
            "last_collect": (now_wib() - timedelta(hours=lt["interval_hours"])).isoformat(),
            "created_at": now_wib().isoformat(),
        })
        if res:
            await update.message.reply_text(
                f"🎉 <b>{lt['emoji']} {lname}</b> berhasil dibeli!\n"
                f"Panen {lt['product_emoji']} {lt['product_name']} tiap {lt['interval_hours']} jam~\n"
                f"Jual seharga <b>{lt['sell_price']} 🪙</b> per item!",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐄 Lihat Ternak", callback_data="livestock_menu")]]))
        else:
            await update.message.reply_text("❌ Gagal beli ternak, coba lagi!")

    elif context.user_data.get("state") == "guess":
        await answer_guess(update, context, user)

    elif context.user_data.get("state") == "ASK_NICKNAME_ONBOARD":
        nickname = text
        if len(nickname) < 2 or len(nickname) > 20:
            await update.message.reply_text("⚠️ Nickname harus 2–20 karakter, coba lagi:")
            return
        context.user_data["state"] = None
        await update_user(user.id, {"nickname": nickname})
        _cdel(_user_cache, user.id)
        await update.message.reply_text(
            f"✅ Nickname <b>{nickname}</b> berhasil disimpan!\n"
            f"Sekarang petmu akan memanggil kamu <b>{nickname}</b>~ 🐾",
            parse_mode=ParseMode.HTML
        )

    elif context.user_data.get("state") == "ASK_NICKNAME":
        nickname = text
        if len(nickname) < 2 or len(nickname) > 20:
            await update.message.reply_text("⚠️ Nickname harus 2–20 karakter, coba lagi:")
            return
        context.user_data["state"] = None
        await update_user(user.id, {"nickname": nickname})
        _cdel(_user_cache, user.id)
        pet_lv = await get_pet_level(user.id)
        await update.message.reply_text(
            f"✅ Nickname berhasil diubah ke <b>{nickname}</b>!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Settings", callback_data="settings"), InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
        )

    elif context.user_data.get("state") == "ASK_PET_RENAME":
        new_name = text
        if len(new_name) < 2 or len(new_name) > 20:
            await update.message.reply_text("⚠️ Nama harus 2–20 karakter, coba lagi:")
            return
        pet_id = context.user_data.get("renaming_pet")
        context.user_data["state"] = None
        pet = await get_pet_by_id(pet_id)
        if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
            await update.message.reply_text("❌ Bukan petmu!")
            return
        old_name = pet["name"]
        await update_pet(pet_id, {"name": new_name})
        await update.message.reply_text(
            f"✅ Nama pet berhasil diubah: <b>{old_name}</b> → <b>{new_name}</b>!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}"), InlineKeyboardButton("⚙️ Settings", callback_data="settings")]])
        )

    elif context.user_data.get("state") == "ASK_TRANSFER_TARGET":
        target_raw = text.lstrip("@").strip()
        context.user_data["transfer_target"] = target_raw
        context.user_data["state"] = "ASK_TRANSFER_AMOUNT"
        await update.message.reply_text(
            f"💸 Transfer ke <b>{target_raw}</b>\n\nBerapa koin yang mau ditransfer?",
            parse_mode=ParseMode.HTML
        )

    elif context.user_data.get("state") == "ASK_TRANSFER_AMOUNT":
        target = context.user_data.get("transfer_target")
        context.user_data["state"] = None
        if not text.isdigit():
            await update.message.reply_text("⚠️ Masukkan angka koin yang valid!")
            return
        amount = int(text)
        if amount < TRANSFER_MIN:
            await update.message.reply_text(f"⚠️ Minimum transfer {TRANSFER_MIN} 🪙!")
            return
        await do_transfer_koin(update, user, target, amount, context)

    elif context.user_data.get("state") == "ASK_TOPUP_AMOUNT":
        context.user_data["state"] = None
        raw = text.replace(".", "").replace(",", "").strip()
        if not raw.isdigit():
            await update.message.reply_text("⚠️ Masukkan angka yang valid!\nContoh: <code>10000</code>", parse_mode=ParseMode.HTML)
            return
        amount = int(raw)
        if amount < TOPUP_MIN:
            await update.message.reply_text(
                f"⚠️ Minimum top up <b>{TOPUP_MIN:,} 🪙</b> (Rp {TOPUP_MIN:,})\nCoba lagi dengan nominal lebih besar~",
                parse_mode=ParseMode.HTML
            )
            return
        # Simpan amount ke user_data untuk dipakai saat verifikasi bukti
        context.user_data["topup_amount"] = amount
        context.user_data["state"] = "WAIT_TOPUP_PROOF"
        caption = (
            f"💳 <b>Top Up {amount:,} 🪙</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💰 Jumlah koin: <b>{amount:,} 🪙</b>\n"
            f"💵 Nominal bayar: <b>Rp {amount:,}</b>\n\n"
            f"📱 Scan QRIS di atas dan bayar tepat <b>Rp {amount:,}</b>\n\n"
            f"📸 Setelah bayar, kirim <b>screenshot bukti pembayaran</b> ke sini!\n\n"
            f"<i>Tekan Batal jika ingin membatalkan top up.</i>"
        )
        await update.message.reply_photo(
            photo=QRIS_URL,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Batal Top Up", callback_data="topup_cancel")]
            ])
        )

    elif context.user_data.get("state") == "WAIT_TOPUP_PROOF":
        # User kirim teks saat nunggu bukti — ingatkan kirim foto
        await update.message.reply_text(
            "📸 Kirim <b>foto/screenshot</b> bukti pembayaran ya, bukan teks~",
            parse_mode=ParseMode.HTML
        )

    elif context.user_data.get("state") == "ASK_BUATITEM_NAMA":
        nama = text.strip()
        if len(nama) < 2 or len(nama) > 20:
            await update.message.reply_text("⚠️ Nama item harus 2–20 karakter, coba lagi:")
            return
        context.user_data["buatitem_nama"] = nama
        context.user_data["state"] = "ASK_BUATITEM_EMOJI"
        await update.message.reply_text(
            f"✅ Nama: <b>{safe_html(nama)}</b>\n\n"
            "Sekarang kirim <b>emoji</b> untuk item kamu:\n"
            "<i>Contoh: 🍰 🎀 🌸 (1 emoji aja ya)</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="carpet_shop")]])
        )

    elif context.user_data.get("state") == "ASK_BUATITEM_EMOJI":
        emoji_input = text.strip()
        # Ambil karakter pertama saja
        if not emoji_input:
            await update.message.reply_text("⚠️ Kirim emoji dulu ya~")
            return
        item_emoji = emoji_input[0] if len(emoji_input) >= 1 else "🎁"
        item_nama  = context.user_data.get("buatitem_nama", "Item")
        item_type  = context.user_data.get("buatitem_type", "food")
        type_label = "Makanan 🍖" if item_type == "food" else "Aksesoris 👒"

        context.user_data["buatitem_emoji"] = item_emoji
        context.user_data["state"] = "CONFIRM_BUATITEM"

        await update.message.reply_text(
            f"🛠️ <b>Konfirmasi Buat Item</b>\n━━━━━━━━━━━━━━━\n\n"
            f"{item_emoji} <b>{safe_html(item_nama)}</b>\n"
            f"📦 Jenis: {type_label}\n"
            f"🎁 Jumlah: <b>5 item</b>\n"
            f"💰 Biaya: <b>1.000 🪙</b>\n\n"
            f"Lanjut bayar?",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Bayar 1.000🪙", callback_data="buatitem_confirm"),
                 InlineKeyboardButton("❌ Batal", callback_data="carpet_shop")],
            ])
        )

    elif context.user_data.get("state") == "CONFIRM_BUATITEM":
        # User ngetik teks padahal harusnya pencet tombol
        await update.message.reply_text(
            "👆 Tekan tombol <b>Bayar</b> atau <b>Batal</b> di atas ya~",
            parse_mode=ParseMode.HTML
        )

    elif context.user_data.get("state") == "CUSTOM_PET_NAME":
        await do_create_custom_pet(update, user, context)

async def do_buatitem(q, user, context):
    """Eksekusi buat item custom — bayar 1000 koin, masuk 5 item ke inventory"""
    item_nama  = context.user_data.get("buatitem_nama")
    item_emoji = context.user_data.get("buatitem_emoji")
    item_type  = context.user_data.get("buatitem_type", "food")

    if not item_nama or not item_emoji:
        await q.answer("❌ Data item tidak lengkap, mulai ulang!", show_alert=True)
        return

    # Bayar
    ok = await spend_koin(user.id, 1000, "buat_item_custom")
    if not ok:
        await q.answer("❌ Koin tidak cukup! Butuh 1.000 🪙", show_alert=True)
        return

    # Bersihkan state
    context.user_data["state"] = None
    context.user_data["buatitem_nama"] = None
    context.user_data["buatitem_emoji"] = None
    context.user_data["buatitem_type"] = None

    # Masukkan 5 item ke inventory
    # Key inventory: custom_<type>_<nama_slug>
    import re as _re
    slug = _re.sub(r"[^a-z0-9]", "", item_nama.lower())[:20] or "item"
    inv_key = f"custom_{item_type}_{slug}"

    _cdel(_user_cache, user.id)  # flush cache supaya inventory terbaca fresh
    inv = await get_inv(user.id)
    inv[inv_key] = (inv.get(inv_key) or 0) + 5
    await set_inv(user.id, inv)

    # Simpan metadata ke tabel custom_items (upsert by item_key+owner_id)
    existing = await sb("GET", "custom_items", {"owner_id": f"eq.{user.id}", "item_key": f"eq.{inv_key}"})
    if existing:
        await sb("PATCH", "custom_items", {"owner_id": f"eq.{user.id}", "item_key": f"eq.{inv_key}"}, {
            "name": item_nama, "emoji": item_emoji, "item_type": item_type,
        })
    else:
        await sb("POST", "custom_items", data={
            "owner_id": user.id,
            "item_key": inv_key,
            "name": item_nama,
            "emoji": item_emoji,
            "item_type": item_type,
            "hunger": 30 if item_type == "food" else 0,
            "xp": 5 if item_type == "food" else 0,
            "happy": 0,
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        })

    type_label = "Makanan 🍖" if item_type == "food" else "Aksesoris 👒"
    await q.edit_message_text(
        f"🎉 <b>Item berhasil dibuat!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{item_emoji} <b>{safe_html(item_nama)}</b>\n"
        f"📦 Jenis: {type_label}\n"
        f"🎁 +5 item masuk ke inventorimu!\n\n"
        f"Lihat di 🎒 Inventori untuk pakai atau gift ke teman~",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎒 Lihat Inventori", callback_data="inventory")],
            [InlineKeyboardButton("🛠️ Buat Lagi", callback_data="buatitem_start"),
             InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )
    await log(context, f"🛠️ Buat item: {item_emoji} <b>{safe_html(item_nama)}</b> ({item_type}) x5 → <code>{user.id}</code>")



# ==================== KERJA (LV 35) ====================
async def show_pet_work(q, user, pet_id: int, context=None):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp") or 0)
    if lv < LEVEL_WORK:
        await q.answer(f"❌ Butuh Level {LEVEL_WORK}! Sekarang Lv.{lv}", show_alert=True); return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})

    # Cek apakah sedang kerja
    work_until = pet.get("work_until")
    if work_until:
        wu = parse_dt(work_until)
        if wu > now_wib():
            sisa = fmt_countdown(wu)
            await q.edit_message_text(
                f"💼 <b>{pet['name']}</b> sedang kerja!\n━━━━━━━━━━━━━━━\n\n"
                f"{info['emoji']} Lagi sibuk cari koin~\n"
                f"⏰ Selesai dalam: <b>{sisa}</b>\n\n"
                f"Nanti otomatis dapat <b>{WORK_REWARD_PER_OWNER} 🪙</b> per owner!",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Pulangkan (tanpa reward)", callback_data=f"pet_work_recall_{pet_id}")],
                    [InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")],
                ])
            )
            return
        else:
            # Sudah selesai tapi belum diklaim — auto claim
            await _claim_work_reward(pet, context)
            pet = await get_pet_by_id(pet_id)

    # Cek sudah kerja hari ini
    last_work = pet.get("last_work")
    if last_work:
        lw = parse_dt(last_work)
        sisa = (now_wib() - lw).total_seconds()
        if sisa < 86400:
            cd = fmt_countdown(lw + timedelta(hours=24))
            await q.edit_message_text(
                f"💼 <b>{pet['name']}</b> sudah kerja hari ini!\n━━━━━━━━━━━━━━━\n\n"
                f"{info['emoji']} Istirahat dulu ya~\n"
                f"⏰ Bisa kerja lagi dalam: <b>{cd}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")],
                ])
            )
            return

    # Tampil menu kirim kerja
    await q.edit_message_text(
        f"💼 <b>Kirim {pet['name']} Kerja</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} Pet kamu akan pergi kerja selama <b>{WORK_DURATION_HOURS} jam</b>.\n\n"
        f"💰 Reward: <b>{WORK_REWARD_PER_OWNER} 🪙</b> per owner (otomatis)\n"
        f"⚠️ Selama kerja pet tidak bisa diajak main/mandi\n\n"
        f"Kirim sekarang?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💼 Kirim Kerja!", callback_data=f"pet_work_send_{pet_id}")],
            [InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def _claim_profesi_reward(pet: dict, context):
    """Klaim reward kerja profesional (penjelajah/pengumpul)"""
    user_id  = pet.get("owner1_id")
    profesi  = pet.get("profesi_kerja", "penjelajah")
    skill    = int(pet.get("skill_profesi") or 0)
    ability  = pet.get("special_ability") or ""
    is_3x    = "work_3x" in ability
    info     = PETS.get(pet.get("pet_type",""), {"emoji":"🐾","name":"?"})
    new_happy = min(100, (pet.get("happiness") or 80) + 10)
    await update_pet(pet["id"], {"work_until": None, "profesi_work_active": False, "happiness": new_happy})
    _cdel(_pet_cache, pet["id"])
    # Rare event apes 15%
    is_apes = random.random() < 0.15
    apes_txt = ""
    if is_apes:
        new_hp     = max(10, (pet.get("health") or 100) - 20)
        new_happy2 = max(0, new_happy - 20)
        await update_pet(pet["id"], {"health": new_hp, "happiness": new_happy2})
        kejadian = random.choice([
            "🌧️ Kehujanan di jalan pulang!",
            "🤕 Kepeleset waktu pulang kerja!",
            "🎒 Barang ketinggalan, harus balik lagi!",
            "😵 Kelelahan di perjalanan pulang!",
            "🌪️ Angin kencang bikin berantakan!",
        ])
        apes_txt = f"\n\n⚠️ <b>Kejadian: {kejadian}</b>\nHP -20 | Mood -20\n<i>Tetap dapat reward~</i>"
    if profesi == "penjelajah":
        reward = hitung_reward_penjelajah(skill) * (3 if is_3x else 1)
        for uid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
            await add_koin(uid, reward, "profesi_penjelajah")
        reward_txt = f"🪙 +{reward:,} koin"
    else:
        reward = hitung_reward_pengumpul(skill) * (3 if is_3x else 1)
        for uid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
            inv = await get_inv(uid)
            inv["meal"] = (inv.get("meal") or 0) + reward
            await set_inv(uid, inv)
        reward_txt = f"🍖 +{reward}x makanan"
    label = "🗺️ Penjelajah" if profesi == "penjelajah" else "🧺 Pengumpul"
    ability_txt = "\n⚡ <i>Ability Work 3× aktif!</i>" if is_3x else ""
    msg = (f"💼 <b>{info['emoji']} {pet['name']}</b> pulang kerja sebagai {label}!\n"
           f"{reward_txt} | 😊 +10{ability_txt}{apes_txt}")
    for uid in filter(None, [user_id, pet.get("owner2_id")]):
        try: await context.bot.send_message(uid, msg, parse_mode=ParseMode.HTML)
        except: pass

async def _claim_work_reward(pet: dict, context=None):
    """Kasih reward kerja ke kedua owner. Kalau ability work_3x, reward 3x."""
    ability = pet.get("special_ability") or ""
    reward = WORK_REWARD_PER_OWNER * (3 if "work_3x" in ability else 1)
    for oid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
        await add_koin(oid, reward, "kerja_pet")
        if context:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            try:
                await context.bot.send_message(
                    oid,
                    f"💼 <b>{pet['name']}</b> selesai kerja!\n"
                    f"{info['emoji']} Dapat <b>{reward} 🪙</b> dari hasil kerja~"
                    + (f"\n⚡ <i>Ability Work 3× aktif!</i>" if "work_3x" in ability else ""),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
                )
            except: pass
    await update_pet(pet["id"], {"work_until": None, "last_work": now_wib().isoformat()})

async def do_send_work(q, user, pet_id: int, context=None):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp") or 0)
    if lv < LEVEL_WORK:
        await q.answer(f"❌ Butuh Level {LEVEL_WORK}!", show_alert=True); return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    # Cek kalau masih kerja
    if pet.get("work_until") and parse_dt(pet["work_until"]) > now_wib():
        sisa = fmt_countdown(parse_dt(pet["work_until"]))
        await q.edit_message_text(
            f"💼 <b>{pet['name']}</b> masih kerja!\n━━━━━━━━━━━━━━━\n\n"
            f"{info['emoji']} Selesai dalam: <b>{sisa}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")]]))
        return
    # Cek cooldown: hanya bisa kerja 1x per hari
    last_work = pet.get("last_work")
    if last_work:
        lw = parse_dt(last_work)
        if (now_wib() - lw).total_seconds() < 86400:
            sisa = fmt_countdown(lw + timedelta(hours=24))
            await q.edit_message_text(
                f"💼 <b>{pet['name']}</b> sudah kerja hari ini!\n━━━━━━━━━━━━━━━\n\n"
                f"{info['emoji']} Istirahat dulu ya~\n"
                f"⏰ Bisa kerja lagi dalam: <b>{sisa}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")]]))
            return
    work_until = (now_wib() + timedelta(hours=WORK_DURATION_HOURS)).isoformat()
    await update_pet(pet_id, {"work_until": work_until, "last_work": now_wib().isoformat()})
    await q.edit_message_text(
        f"💼 <b>{pet['name']}</b> berangkat kerja!\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} Selesai dalam <b>{WORK_DURATION_HOURS} jam</b>~\n"
        f"💰 Reward otomatis: <b>{WORK_REWARD_PER_OWNER} 🪙</b> per owner!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
    )
    await log(context, f"💼 Kerja: {info['emoji']} <b>{pet['name']}</b> → selesai jam {work_until[:16]}")


# ==================== PUNYA ANAK (LV 40) ====================
async def show_pet_child_menu(q, user, pet_id: int, context=None):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp") or 0)
    if lv < LEVEL_CHILD:
        await q.answer(f"❌ Butuh Level {LEVEL_CHILD}!", show_alert=True); return
    if not pet.get("is_married"):
        await q.answer("❌ Pet harus menikah dulu!", show_alert=True); return

    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    child_id = pet.get("child_pet_id")

    if child_id:
        child = await get_pet_by_id(child_id)
        if child:
            cinfo = PETS.get(child["pet_type"], {"emoji": "🐾"})
            clv = calc_level((child.get("xp") or 0))

            # Ambil parent pets untuk tahu owner mana yang bayar
            parent1 = await get_pet_by_id(child.get("parent1_pet_id")) if child.get("parent1_pet_id") else None
            parent2 = await get_pet_by_id(child.get("parent2_pet_id")) if child.get("parent2_pet_id") else None
            p1_paid = child.get("allowance_paid_p1", False)
            p2_paid = child.get("allowance_paid_p2", False)

            # Apakah user ini termasuk keluarga parent1 atau parent2?
            is_p1_owner = parent1 and (parent1.get("owner1_id") == user.id or parent1.get("owner2_id") == user.id)
            is_p2_owner = parent2 and (parent2.get("owner1_id") == user.id or parent2.get("owner2_id") == user.id)
            my_family_paid = (is_p1_owner and p1_paid) or (is_p2_owner and p2_paid)

            # Helper: format daftar usn owner dari sebuah parent pet
            async def _owner_label(parent_pet):
                if not parent_pet:
                    return "?"
                names = []
                for oid in [parent_pet.get("owner1_id"), parent_pet.get("owner2_id")]:
                    if not oid:
                        continue
                    ou = await get_user(oid)
                    if ou and ou.get("username"):
                        names.append(f"@{ou['username']}")
                    elif ou:
                        names.append(safe_html(ou.get("nickname") or ou.get("nama") or str(oid)))
                    else:
                        names.append(str(oid))
                return ", ".join(names) if names else "?"

            # Cek tagihan uang saku
            last_allowance = child.get("last_allowance_request")
            bill_active = False
            tagihan_txt = ""
            if last_allowance:
                la = parse_dt(last_allowance)
                next_req = la + timedelta(days=CHILD_ALLOWANCE_DAYS)
                if next_req > now_wib():
                    tagihan_txt = f"\n⏰ Tagihan berikutnya: {fmt_countdown(next_req)}"
                else:
                    bill_active = True
                    tagihan_txt = f"\n⚠️ <b>Anak minta uang saku!</b> {CHILD_ALLOWANCE_COIN} 🪙 per keluarga"

            # Status pembayaran tiap keluarga
            p1_label = await _owner_label(parent1)
            p2_label = await _owner_label(parent2)
            status_lines = "\n\n💰 <b>Status Uang Saku:</b>"
            status_lines += f"\n{'✅' if p1_paid else '❌'} Keluarga 1: {p1_label}"
            if parent2:
                status_lines += f"\n{'✅' if p2_paid else '❌'} Keluarga 2: {p2_label}"

            rows = []
            # Tombol bayar hanya muncul kalau ada tagihan & keluarga user BELUM bayar
            if bill_active and not my_family_paid and (is_p1_owner or is_p2_owner):
                rows.append([InlineKeyboardButton(
                    f"💰 Bayar Uang Saku ({CHILD_ALLOWANCE_COIN}🪙)",
                    callback_data=f"child_pay_{child_id}"
                )])
            elif my_family_paid:
                status_lines += "\n\n<i>✅ Keluargamu sudah bayar~</i>"
            rows.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")])

            await q.edit_message_text(
                f"👶 <b>Anak {pet['name']}</b>\n━━━━━━━━━━━━━━━\n\n"
                f"{cinfo['emoji']} <b>{child['name']}</b> (Lv.{clv})\n"
                f"❤️ HP: {child.get('health',100)} | 😊 Mood: {child.get('happiness',80)}\n"
                f"🍽️ Lapar: {child.get('hunger',30)}%{tagihan_txt}{status_lines}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(rows)
            )
            return

    # Belum punya anak
    partner_pet_id = pet.get("married_to_pet_id")
    partner_pet = await get_pet_by_id(partner_pet_id) if partner_pet_id else None
    pinfo = PETS.get(partner_pet["pet_type"], {"emoji": "🐾"}) if partner_pet else {"emoji": "❓"}

    # Tipe anak random dari dua parent
    parent_types = [pet["pet_type"]]
    if partner_pet:
        parent_types.append(partner_pet["pet_type"])
    child_type = random.choice(parent_types)
    child_info = PETS.get(child_type, {"emoji": "🐾", "name": "?"})

    await q.edit_message_text(
        f"👶 <b>Punya Anak</b>\n━━━━━━━━━━━━━━━\n\n"
        f"Pasangan: {info['emoji']} <b>{pet['name']}</b> × {pinfo['emoji']} <b>{partner_pet['name'] if partner_pet else '?'}</b>\n\n"
        f"Anak akan lahir sebagai: {child_info['emoji']} <b>{child_info['name']}</b> (random)\n"
        f"⭐ Level awal: <b>1</b>\n\n"
        f"⚠️ Setiap {CHILD_ALLOWANCE_DAYS} hari, anak akan minta uang saku <b>{CHILD_ALLOWANCE_COIN} 🪙</b> ke setiap orang tua.\n"
        f"Kalau {CHILD_RUNAWAY_DAYS} hari tidak dikasih sama sekali, anak bisa kabur!\n\n"
        f"Lanjut punya anak?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👶 Ya, Punya Anak!", callback_data=f"child_create_{pet_id}_{child_type}")],
            [InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def do_create_child(q, user, pet_id: int, child_type: str, context=None):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("child_pet_id"):
        await q.answer("❌ Sudah punya anak!", show_alert=True); return

    partner_pet_id = pet.get("married_to_pet_id")
    partner_pet = await get_pet_by_id(partner_pet_id) if partner_pet_id else None

    cinfo = PETS.get(child_type, {"emoji": "🐾", "name": "Anak Pet"})
    child_name = f"Anak {pet['name']}"

    # Buat pet anak — is_child=True, parent1/2 adalah id pet orang tua
    child_data = {
        "owner1_id":   pet.get("owner1_id"),
        "owner2_id":   pet.get("owner2_id"),
        "name":        child_name,
        "pet_type":    child_type,
        "level":       1,
        "xp":          0,
        "hunger":      30,
        "happiness":   80,
        "health":      100,
        "is_child":    True,
        "parent1_pet_id": pet_id,
        "parent2_pet_id": partner_pet_id,
        "last_allowance_request": now_wib().isoformat(),
        "allowance_paid_p1": False,
        "allowance_paid_p2": False,
        "last_decay":  now_wib().isoformat(),
        "last_fed":  now_wib().isoformat(),
        "last_played": (now_wib() - timedelta(hours=6)).isoformat(),
        "created_at":  now_wib().isoformat(),
    }
    new_child = await upsert_pet(child_data)
    if isinstance(new_child, list): new_child = new_child[0]
    if not new_child:
        await q.answer("❌ Gagal membuat anak pet!", show_alert=True); return

    child_id = new_child["id"]
    # Update parent pets dengan child_pet_id
    await update_pet(pet_id, {"child_pet_id": child_id})
    if partner_pet:
        await update_pet(partner_pet_id, {"child_pet_id": child_id})

    await q.edit_message_text(
        f"🎉 <b>Selamat! Anak telah lahir!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{cinfo['emoji']} <b>{child_name}</b> lahir!\n"
        f"⭐ Level 1 | Tipe: {cinfo['name']}\n\n"
        f"💰 Setiap {CHILD_ALLOWANCE_DAYS} hari akan minta uang saku <b>{CHILD_ALLOWANCE_COIN} 🪙</b>~\n"
        f"Rawat anak dengan baik ya!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
    )

    # Notif ke semua owner kedua pet
    all_owners = list(filter(None, set([
        pet.get("owner1_id"), pet.get("owner2_id"),
        partner_pet.get("owner1_id") if partner_pet else None,
        partner_pet.get("owner2_id") if partner_pet else None,
    ])))
    for oid in all_owners:
        if oid == user.id: continue
        try:
            await context.bot.send_message(
                oid,
                f"🎉 <b>Anak pet lahir!</b>\n{cinfo['emoji']} <b>{child_name}</b> sudah ada di dunia~\n"
                f"Rawat bersama ya! 💕",
                parse_mode=ParseMode.HTML
            )
        except: pass
    await log(context, f"👶 Anak lahir: {cinfo['emoji']} <b>{child_name}</b> dari {pet['name']} × {partner_pet['name'] if partner_pet else '?'}")

async def do_pay_child_allowance(q, user, child_id: int, context=None):
    child = await get_pet_by_id(child_id)
    if not child:
        await q.answer("❌ Anak pet tidak ditemukan!", show_alert=True); return

    parent1_id = child.get("parent1_pet_id")
    parent2_id = child.get("parent2_pet_id")
    parent1 = await get_pet_by_id(parent1_id) if parent1_id else None
    parent2 = await get_pet_by_id(parent2_id) if parent2_id else None

    # Cek user ini owner dari parent pet mana (parent1 bisa punya 2 owner, parent2 juga)
    is_parent1_owner = parent1 and (parent1.get("owner1_id") == user.id or parent1.get("owner2_id") == user.id)
    is_parent2_owner = parent2 and (parent2.get("owner1_id") == user.id or parent2.get("owner2_id") == user.id)
    if not is_parent1_owner and not is_parent2_owner:
        await q.answer("❌ Bukan orang tua pet ini!", show_alert=True); return

    paid_key = "allowance_paid_p1" if is_parent1_owner else "allowance_paid_p2"
    if child.get(paid_key):
        await q.answer("✅ Keluargamu sudah bayar uang saku ini!", show_alert=True); return

    ok = await spend_koin(user.id, CHILD_ALLOWANCE_COIN, "uang_saku")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {CHILD_ALLOWANCE_COIN} 🪙", show_alert=True); return

    await update_pet(child_id, {paid_key: True})
    child_fresh = await get_pet_by_id(child_id)
    p1_paid = child_fresh.get("allowance_paid_p1", False)
    p2_paid = child_fresh.get("allowance_paid_p2", False)

    if p1_paid and p2_paid:
        await update_pet(child_id, {
            "last_allowance_request": now_wib().isoformat(),
            "allowance_paid_p1": False, "allowance_paid_p2": False,
            "hunger": max(0, (child_fresh.get("hunger") or 30) - 20),
            "happiness": min(100, (child_fresh.get("happiness") or 80) + 15),
        })
        status_txt = "✅ Kedua keluarga sudah bayar! Anak senang~"
    else:
        await update_pet(child_id, {"hunger": min(100, (child_fresh.get("hunger") or 30) + 10)})
        status_txt = "⚠️ Baru 1 keluarga yang bayar — anak masih sedikit kelaparan"

    cinfo = PETS.get(child["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"💰 <b>Uang saku dibayar!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{cinfo['emoji']} <b>{child['name']}</b>\n-{CHILD_ALLOWANCE_COIN} 🪙\n\n{status_txt}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
    )

    # Notif ke semua 4 owner lain
    all_owners = set(filter(None, [
        parent1.get("owner1_id") if parent1 else None,
        parent1.get("owner2_id") if parent1 else None,
        parent2.get("owner1_id") if parent2 else None,
        parent2.get("owner2_id") if parent2 else None,
    ]))
    for oid in all_owners:
        if oid == user.id: continue
        try:
            if context:
                await context.bot.send_message(
                    oid,
                    f"💰 Uang saku {cinfo['emoji']} <b>{child['name']}</b> dibayar salah satu orang tua~",
                    parse_mode=ParseMode.HTML
                )
        except: pass


# ==================== BADGE (LV 45) ====================
async def show_pet_badge(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp") or 0)
    if lv < LEVEL_BADGE:
        await q.answer(f"❌ Butuh Level {LEVEL_BADGE}!", show_alert=True); return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    badge = PET_BADGES.get(pet["pet_type"], "🎖️ Badge Kehormatan")
    await q.edit_message_text(
        f"🏅 <b>Badge Kehormatan</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{pet['name']}</b>\n\n"
        f"{badge}\n\n"
        f"<i>Badge ini diraih karena pet kamu sudah mencapai Level {LEVEL_BADGE}!\n"
        f"Tampil di profil pet sebagai tanda kehormatan.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")]])
    )


# ==================== AKSESORIS LV 50 ====================
async def do_equip_lv50_acc(q, user, pet_id: int, context=None):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp") or 0)
    if lv < LEVEL_SPECIAL_ACC:
        await q.answer(f"❌ Butuh Level {LEVEL_SPECIAL_ACC}!", show_alert=True); return
    acc = SPECIAL_ACC_LV50.get(pet["pet_type"])
    if not acc:
        await q.answer("❌ Tidak ada aksesoris untuk tipe pet ini!", show_alert=True); return
    acc_key = f"lv50_{pet['pet_type']}"
    await update_pet(pet_id, {
        "accessory": acc["emoji"],
        "accessory_name": acc["name"],
        "accessory_key": acc_key,
    })
    pet["accessory"] = acc["emoji"]
    pet_lv = await get_pet_level(user.id)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"🌟 <b>Aksesoris Spesial Terpasang!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{acc['emoji']} <b>{acc['name']}</b> dipasang ke {info['emoji']} <b>{pet['name']}</b>!\n\n"
        f"<i>Aksesoris eksklusif Level 50 — tanda kejayaan pet kamu!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]])
    )
    await log(context, f"🌟 Equip Lv50 acc: {acc['emoji']} {acc['name']} → {info['emoji']} <b>{pet['name']}</b>")

async def cmd_buatitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /buatitem — shortcut buat item custom"""
    user = update.effective_user
    u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    koin = (u.get("koin") or 0)
    await update.message.reply_text(
        "🛠️ <b>Buat Item Sendiri</b>\n━━━━━━━━━━━━━━━\n\n"
        "Kamu bisa bikin item custom sendiri!\n\n"
        "💰 Biaya: <b>1.000 🪙</b>\n"
        "🎁 Dapat: <b>5 item</b>\n\n"
        f"Koin kamu: <b>{koin} 🪙</b>\n\n"
        "Pilih jenis item:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🍖 Makanan", callback_data="buatitem_type_food"),
             InlineKeyboardButton("👒 Aksesoris", callback_data="buatitem_type_accessory")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )


async def show_my_pet_direct(update: Update, user, context):
    """Tampilkan pet langsung, tanpa menu utama, dengan selector kalau >1 pet"""
    pets = await get_user_pets(user.id)
    
    if not pets:
        d = await get_pending_delivery(user.id)
        if d:
            await update.message.reply_text(
                "📦 Kamu punya pengiriman aktif!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Cek Pengiriman", callback_data=f"check_{d['code']}")]])
            )
            return
        await update.message.reply_text(
            "🐾 Kamu belum punya pet!\nKunjungi 🏪 Carpet Shop untuk adopsi~",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏪 Carpet Shop", callback_data="carpet_shop")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
            ])
        )
        return
    
    # Kalau cuma 1 pet, langsung tampilkan
    if len(pets) == 1:
        pet = pets[0]
        pet = decay_pet_stats(pet)
        if _should_write_pet(pet["id"], {"hunger": pet["hunger"], "happiness": pet["happiness"], "health": pet["health"]}, pet):
            await update_pet(pet["id"], {"hunger": pet["hunger"], "happiness": pet["happiness"], "health": pet["health"], "last_decay": pet["last_decay"]})
            _mark_written(pet["id"])
        
        role = "👑 Owner 1" if pet.get("owner1_id") == user.id else "👤 Owner 2"
        partner_id = pet.get("owner2_id") if pet.get("owner1_id") == user.id else pet.get("owner1_id")

        partner_txt = "\n👫 Partner: <i>belum ada</i>"
        if partner_id:
            p_user = await sb("GET", "users", {"user_id": f"eq.{partner_id}", "select": "user_id,nama,nickname,username"})
            if p_user:
                p = p_user[0]
                p_name = safe_html(p.get("nickname") or p.get("nama") or p.get("username") or str(partner_id))
                p_username = f" @{p.get('username')}" if p.get("username") else ""
                partner_txt = f"\n👫 Partner: <b>{p_name}</b>{p_username}"
            else:
                partner_txt = f"\n👫 Partner: <code>{partner_id}</code>"
        
        sick_warn = ""
        if (pet.get("hunger") or 0) >= 70:
            sick_warn = "\n🤒 <b>PET SAKIT! Kelaparan terlalu tinggi! Kasih makan segera!</b>"
        elif (pet.get("hunger") or 0) >= 20:
            sick_warn = f"\n⚠️ <b>Kelaparan sudah {pet.get('hunger',0)}%! Jangan sampai lebih dari 70%!</b>"
        
        await update.message.reply_text(
            f"{role}{partner_txt}{sick_warn}\n\n{pet_card(pet)}",
            parse_mode=ParseMode.HTML,
            reply_markup=kb_pet(pet)
        )
    else:
        # Lebih dari 1 pet, tampilkan selector
        await update.message.reply_text(
            "🐾 <b>Pilih pet yang mau dilihat:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb_pet_selector(pets, user.id)
        )

# ==================== DELIVERY ====================
async def show_delivery(q, user, code: str, context):
    d = await get_delivery(code)
    if not d:
        await q.edit_message_text("❌ Pengiriman tidak ditemukan.")
        return

    if d["is_delivered"]:
        await q.edit_message_text(
            "✅ Pet sudah tiba! Cek menu 🐾 Pet Saya~",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
        )
        return

    info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})

    # Belum ada partner
    if not d.get("owner2_id"):
        bot_name    = BOT_USERNAME.lstrip("@")
        kode_invite = d.get("kode_invite", "?")
        invite_link = f"https://t.me/{bot_name}?start={kode_invite}"
        await q.edit_message_text(
            f"⏳ <b>Menunggu partner...</b>\n\n"
            f"{info['emoji']} <b>{d['pet_name']}</b>\n\n"
            f"🔑 Kode: <code>{kode_invite}</code>\n"
            f"🔗 Link: {invite_link}\n\n"
            f"Bagikan ke temanmu untuk mulai pengiriman!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"check_{code}")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
            ])
        )
        return

    # Ada partner, cek waktu
    arrive_at = parse_dt(d["arrive_at"])
    tap_count = d.get("tap_count", 1)

    # Cek apakah sudah harus dikirim
    should_deliver = now_wib() >= arrive_at or tap_count >= TAPS_NEEDED
    if should_deliver:
        await deliver_pet(q, user, d, code, context)
        return

    countdown = fmt_countdown(arrive_at)
    text = (
        f"📦 <b>Status Pengiriman</b>\n━━━━━━━━━━━━━━━\n"
        f"{info['emoji']} <b>{d['pet_name']}</b> ({info['name']})\n\n"
        f"👫 Partner: {d.get('owner2_name', '?')}\n"
        f"⏰ Tiba dalam: <b>{countdown}</b>\n"
        f"👆 Tap: <b>{tap_count}/{TAPS_NEEDED}</b> [{bar(tap_count, TAPS_NEEDED, 6)}]\n\n"
        f"🚀 Share ke teman untuk dipercepat!"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh",       callback_data=f"check_{code}")],
        [InlineKeyboardButton("🚀 Share Percepat", switch_inline_query=f"tap {code}")],
        [InlineKeyboardButton("🔙 Menu",           callback_data="main_menu")],
    ])
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def do_tap(q, user, code: str, context):
    d = await get_delivery(code)
    if not d:
        await q.answer("❌ Pengiriman tidak ditemukan!", show_alert=True); return
    if d["is_delivered"]:
        await q.answer("✅ Pet ini sudah dikirim!", show_alert=True); return
    if not d.get("owner2_id"):
        await q.answer("⏳ Masih menunggu partner bergabung!", show_alert=True); return

    taps = json.loads(d["taps"]) if isinstance(d["taps"], str) else (d["taps"] or {})
    uid  = str(user.id)
    if uid in taps:
        await q.answer("⚠️ Kamu sudah tap! 1 orang = 1 tap.", show_alert=True); return

    taps[uid] = now_wib().isoformat()
    new_count  = len(taps)
    await update_delivery(code, {"taps": taps, "tap_count": new_count})

    info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})

    if new_count >= TAPS_NEEDED:
        await q.answer(f"🎉 Tap ke-{new_count}! Pet langsung dikirim!", show_alert=True)
        try:
            await q.edit_message_text(
                f"🎊 <b>{new_count}/{TAPS_NEEDED} tap terpenuhi!</b>\n"
                f"{info['emoji']} <b>{d['pet_name']}</b> langsung dikirim ke pemiliknya!\n\nTerima kasih sudah membantu! 💕",
                parse_mode=ParseMode.HTML
            )
        except: pass
        await _create_pet_from_delivery(d, code)
        await update_delivery(code, {"is_delivered": True})
        # Notify both owners
        for oid in [d["owner1_id"], d.get("owner2_id")]:
            if oid:
                try:
                    await context.bot.send_message(
                        oid,
                        f"🎊 <b>Pet kamu sudah tiba!</b>\n{info['emoji']} <b>{d['pet_name']}</b> siap dirawat!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
                    )
                except: pass
        await log(context, f"📦 Pengiriman selesai (tap): <b>{d['pet_name']}</b> ({info['name']})")
    else:
        await q.answer(f"👆 Tap #{new_count}! {TAPS_NEEDED - new_count} lagi!", show_alert=True)
        try:
            await q.edit_message_text(
                f"📦 <b>Bantu percepat pengiriman!</b>\n"
                f"{info['emoji']} <b>{d['pet_name']}</b> milik {d['owner1_name']}\n\n"
                f"👆 Tap: <b>{new_count}/{TAPS_NEEDED}</b>  [{bar(new_count, TAPS_NEEDED, 6)}]",
                parse_mode=ParseMode.HTML,
                reply_markup=kb_delivery(code, new_count)
            )
        except: pass

async def deliver_pet(q, user, d: dict, code: str, context):
    await _create_pet_from_delivery(d, code)
    await update_delivery(code, {"is_delivered": True})
    info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})
    await q.edit_message_text(
        f"🎊 <b>Pet kamu sudah tiba!</b>\n\n{info['emoji']} <b>{d['pet_name']}</b> siap dirawat!\nSelamat merawat peliharaanmu~ 💕",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
    )
    try:
        owner1_data = await sb("GET", "users", {"user_id": f"eq.{d['owner1_id']}", "select": "user_id,nama,nickname,username"})
        owner1_txt = f"<b>{owner1_data[0].get('nama','?')}</b> @{owner1_data[0].get('username','')} (<code>{d['owner1_id']}</code>)" if owner1_data else f"<code>{d['owner1_id']}</code>"
    except:
        owner1_txt = f"<code>{d['owner1_id']}</code>"
    await log(context, f"📦 Pengiriman selesai (waktu): {info['emoji']} <b>{d['pet_name']}</b> milik {owner1_txt}")

async def _create_pet_from_delivery(d: dict, code: str, owner2_id_override=None):
    # Gunakan override kalau ada — penting untuk koi karena d["owner2_id"] masih null
    # saat handle_join memanggil fungsi ini (d diambil sebelum update_delivery)
    owner2_id = owner2_id_override if owner2_id_override is not None else d.get("owner2_id")
    now = now_wib().isoformat()
    await upsert_pet({
        "owner1_id":          d["owner1_id"],
        "owner2_id":          owner2_id,
        "name":               d["pet_name"],
        "pet_type":           d["pet_type"],
        "level":              1,
        "xp":                 0,
        "hunger":             50,
        "happiness":          80,
        "health":             100,
        "last_decay":         now,
        "last_fed":           now,
        "last_played":        (now_wib() - timedelta(hours=6)).isoformat(),
        "last_bath":          now,
        "last_poop_at":       now,
        "last_poop":          now,
        "poop_count":         0,
        "wangi_until":        now,
        "is_sleeping":        False,
        "is_dirty":           False,
        "is_missing":         False,
        "is_married":         False,
        "married_at":         None,
        "married_to_pet_id":  None,
        "accessory":          None,
        "accessory_name":     None,
        "soap_premium_active": False,
        "boarding_until":     None,
        "boarding_paid_at":   None,
        "expedition_until":   None,
        "expedition_dest":    None,
        "expedition_destination": None,
        "last_notif_hunger":  100,
        "created_at":         now,
    })

# ==================== PET CARE ====================
async def show_my_pet(q, user, context):
    pets = await get_user_pets(user.id)

    if not pets:
        d = await get_pending_delivery(user.id)
        if d:
            await show_delivery(q, user, d["code"], context)
            return
        await q.edit_message_text(
            "🐾 Kamu belum punya pet!\nKunjungi 🏪 Carpet Shop untuk adopsi~",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏪 Carpet Shop", callback_data="carpet_shop")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
            ])
        )
        return

    # Pisahkan pet aktif dan yang kabur
    active_pets  = [p for p in pets if not p.get("is_missing")]
    missing_pets = [p for p in pets if p.get("is_missing")]

    # Kalau semua kabur
    if not active_pets:
        pet = missing_pets[0]
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        buttons = [[InlineKeyboardButton(f"🔍 Cari {info['emoji']} {pet['name']}", callback_data=f"find_pet_{pet['id']}")] for pet in missing_pets]
        buttons.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
        await q.edit_message_text(
            "🏃 <b>Semua petmu sedang kabur!</b>\n\n"
            "<i>Tekan tombol di bawah untuk mencari dan membawa mereka pulang~</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Kalau cuma 1 pet aktif, langsung tampilkan (+ info pet kabur kalau ada)
    if len(active_pets) == 1:
        await show_single_pet(q, user, active_pets[0]["id"], context, missing_pets=missing_pets)
    else:
        await q.edit_message_text(
            "🐾 <b>Pilih pet yang mau dilihat:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb_pet_selector(active_pets, user.id, missing_pets=missing_pets)
        )

async def show_single_pet(q, user, pet_id: int, context, missing_pets: list = None):
    """Tampilkan detail satu pet"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True)
        return

    # Kalau pet lagi kabur, tunjukkan halaman cari
    if pet.get("is_missing"):
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        await q.edit_message_text(
            f"🏃 <b>{pet['name']}</b> sedang kabur...\n\n"
            f"{info['emoji']} {info['name']} kamu tidak diurus selama 3 hari dan pergi sendiri.\n\n"
            f"<i>Tekan tombol di bawah untuk mencarinya~ 🔍</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Cari Pet", callback_data=f"find_pet_{pet_id}")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
            ])
        )
        return

    pet = decay_pet_stats(pet)
    # Hemat Disk IO: hanya write kalau perubahan signifikan atau sudah lama
    if _should_write_pet(pet["id"], {"hunger": pet["hunger"], "happiness": pet["happiness"], "health": pet["health"]}, pet):
        await update_pet(pet["id"], {
            "hunger": pet["hunger"], "happiness": pet["happiness"],
            "health": pet["health"], "last_decay": pet["last_decay"]
        })
        _mark_written(pet["id"])

    role = "👑 Owner 1" if pet.get("owner1_id") == user.id else "👤 Owner 2"

    # Partner adalah owner yang BUKAN user ini
    partner_id = pet.get("owner2_id") if pet.get("owner1_id") == user.id else pet.get("owner1_id")

    # Cari info partner
    partner_txt = "\n👫 Partner: <i>belum ada</i>"
    if partner_id:
        p_user = await sb("GET", "users", {"user_id": f"eq.{partner_id}"})
        if p_user:
            p = p_user[0]
            p_name = safe_html(p.get("nama") or p.get("username") or str(partner_id))
            p_username = f" @{p.get('username')}" if p.get("username") else ""
            partner_txt = f"\n👫 Partner: <b>{p_name}</b>{p_username}"
        else:
            partner_txt = f"\n👫 Partner: <code>{partner_id}</code>"

    sick_warn = ""
    if (pet.get("hunger") or 0) >= 70:
        sick_warn = "\n🤒 <b>PET SAKIT! Kelaparan terlalu tinggi! Kasih makan segera!</b>"
    elif (pet.get("hunger") or 0) >= 20:
        sick_warn = f"\n⚠️ <b>Kelaparan sudah {pet.get('hunger',0)}%! Jangan sampai lebih dari 70%!</b>"

    # Susun keyboard — tambah tombol cari kalau ada pet yang kabur
    pet_kb = kb_pet(pet)
    if missing_pets:
        extra_buttons = []
        for mp in missing_pets:
            minfo = PETS.get(mp["pet_type"], {"emoji": "🐾"})
            extra_buttons.append(InlineKeyboardButton(
                f"🔍 Cari {minfo['emoji']} {mp['name']}",
                callback_data=f"find_pet_{mp['id']}"
            ))
        rows = list(pet_kb.inline_keyboard) + [extra_buttons]
        pet_kb = InlineKeyboardMarkup(rows)

    await q.edit_message_text(
        f"{role}{partner_txt}{sick_warn}\n\n{pet_card(pet)}",
        parse_mode=ParseMode.HTML,
        reply_markup=pet_kb
    )

async def refresh_pet(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    pet = decay_pet_stats(pet)
    await update_pet(pet_id, {"hunger": pet["hunger"], "happiness": pet["happiness"], "health": pet["health"], "last_decay": pet["last_decay"]})
    await q.edit_message_text(pet_card(pet), parse_mode=ParseMode.HTML, reply_markup=kb_pet(pet))

async def show_feed_menu(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    inv = await get_inv(user.id)

    is_koi = pet.get("pet_type") == "koi"
    shop = KOI_FOOD_SHOP if is_koi else FOOD_SHOP

    buttons = []
    for k, info in shop.items():
        # Item astro selalu tampil (punya efek khusus meski hunger=0)
        if not info.get("astro") and not info.get("isPil") and not info.get("mbg"):
            if "hunger" not in info and "happy" not in info: continue
        if info.get("mbg"): continue  # mbg dihandle tersendiri di bawah
        if info.get("isPil"): continue  # pil dihandle dari inventori
        c = inv.get(k) or 0
        if c > 0:
            buttons.append([InlineKeyboardButton(f"{info['emoji']} {info['name']} x{c}", callback_data=f"feeditem_{pet_id}_{k}")])

    # MBG items (hanya untuk non-koi)
    if not is_koi:
        for k, recipe in MBG_KITCHEN_RECIPES.items():
            c = inv.get(k) or 0
            if c > 0:
                buttons.append([InlineKeyboardButton(f"{recipe['emoji']} {recipe['name']} x{c} 🍳", callback_data=f"feeditem_{pet_id}_{k}")])

    # Tambah custom food items (hanya untuk non-koi)
    if not is_koi:
        custom_map = await get_custom_items_map(user.id)
        for k, v in inv.items():
            if (v or 0) > 0 and k in custom_map and custom_map[k]["item_type"] == "food":
                ci = custom_map[k]
                buttons.append([InlineKeyboardButton(f"{ci['emoji']} {safe_html(ci['name'])} x{v} ✨", callback_data=f"feeditem_{pet_id}_{k}")])

    # Item hasil panen Farm Day (hanya non-koi)
    if not is_koi:
        fd_inv_data = await fd_get_inv(user.id)
        for k, v in fd_inv_data.items():
            if k in FARMDAY_FOOD_KEYS and (v or 0) > 0:
                finfo = FARMDAY_HASIL_INFO.get(k, {"emoji": "📦", "name": k})
                buttons.append([InlineKeyboardButton(f"{finfo['emoji']} {finfo['name']} x{v} 🌾", callback_data=f"feeditem_{pet_id}_farm_{k}")])

    if not buttons:
        await q.edit_message_text(
            f"🍽️ Inventori {'makanan ikan' if is_koi else 'makanan'} kosong!\nBeli dulu di 🛒 Toko Makanan~",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Toko", callback_data="food_shop")],
                [InlineKeyboardButton("🍳 Dapur MBG", callback_data="mbg_kitchen")],
                [InlineKeyboardButton("🔙", callback_data="my_pet")],
            ])
        )
        return
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="my_pet")])
    await q.edit_message_text(
        f"🍽️ Pilih makanan untuk <b>{pet['name']}</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def do_feed(q, user, pet_id: int, item_key: str, context=None):
    _cdel(_pet_cache, pet_id)  # flush cache biar XP fresh dari DB
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return

    # Handle Farm Day items (prefix farm_)
    if item_key.startswith("farm_"):
        real_key = item_key[5:]
        fd_inv_data = await fd_get_inv(user.id)
        if (fd_inv_data.get(real_key) or 0) <= 0:
            await q.answer("❌ Stok habis!", show_alert=True); return
        fd_inv_data[real_key] = (fd_inv_data[real_key] or 0) - 1
        if fd_inv_data[real_key] <= 0: del fd_inv_data[real_key]
        await fd_set_inv(user.id, fd_inv_data)
        _cdel(_pet_cache, pet_id)
        pet = await get_pet_by_id(pet_id)
        if not pet:
            await q.answer("❌ Gagal load data pet!", show_alert=True); return
        pet = decay_pet_stats(pet)
        finfo  = FARMDAY_HASIL_INFO.get(real_key, {"emoji": "📦", "name": real_key})
        old_xp = (pet.get("xp") or 0)
        pet["hunger"]    = max(0, (pet.get("hunger") or 0) - 30)
        pet["happiness"] = min(100, (pet.get("happiness") or 80) + 5)
        pet["xp"]        = old_xp + 5
        new_lv = calc_level(pet["xp"]); old_lv = calc_level(old_xp)
        await update_pet(pet_id, {"hunger": pet["hunger"], "happiness": pet["happiness"], "xp": pet["xp"], "level": new_lv, "last_decay": now_wib().isoformat(), "last_fed": now_wib().isoformat()})
        lv_txt = f"\n\n✨ <b>LEVEL UP!</b> Lv.{old_lv} → Lv.{new_lv}!" if new_lv > old_lv else ""
        await q.edit_message_text(
            f"🌾 <b>{pet['name']}</b> makan {finfo['emoji']} {finfo['name']}!\nLapar -30 | Senang +5 | XP +5{lv_txt}",
            parse_mode=ParseMode.HTML, reply_markup=kb_pet(pet))
        return

    inv = await get_inv(user.id)
    if (inv.get(item_key) or 0) <= 0:
        await q.answer("❌ Stok habis!", show_alert=True); return

    # Handle MBG items
    if item_key in ("mbg_biasa", "mbg_special"):
        mbg_type = "biasa" if item_key == "mbg_biasa" else "special"
        await do_feed_mbg(q, user, pet_id, mbg_type, context)
        return

    # Handle pil items dari feed menu
    if item_key in ("pil_anti_pup", "pil_anti_lapar"):
        pil_type = item_key.replace("pil_", "")
        await do_use_pil(q, user, pet_id, pil_type)
        return

    is_koi = pet.get("pet_type") == "koi"

    # Tentukan info item — cek standar dulu, lalu custom
    food = None
    is_custom = item_key.startswith("ci_") or item_key.startswith("custom_")
    if is_custom:
        custom_map = await get_custom_items_map(user.id)
        ci = custom_map.get(item_key)
        if ci and ci["item_type"] == "food":
            food = {"emoji": ci["emoji"], "name": ci["name"], "hunger": (ci.get("hunger") or 30), "xp": (ci.get("xp") or 5), "happy": ci.get("happy", 0)}
        else:
            await q.answer("❌ Item ini bukan makanan!", show_alert=True); return
    else:
        food = KOI_FOOD_SHOP.get(item_key) if is_koi else FOOD_SHOP.get(item_key)
        if not food:
            food = KOI_FOOD_SHOP.get(item_key) or FOOD_SHOP.get(item_key)
        # Item makanan Astro: key inventory bisa beda dari key FOOD_SHOP (mis. mega_feast -> mega_moon_feast)
        if not food and item_key in ASTRO_INV_TO_FOOD_KEY:
            food = FOOD_SHOP.get(ASTRO_INV_TO_FOOD_KEY[item_key])
        if not food:
            await q.answer("❌ Item tidak dikenal!", show_alert=True); return

        # Koi tidak bisa makan makanan biasa dan sebaliknya
        if is_koi and item_key in FOOD_SHOP and item_key not in KOI_FOOD_SHOP:
            await q.answer("❌ Ikan koi tidak bisa makan makanan itu! Beli makanan khusus ikan.", show_alert=True); return
        if not is_koi and item_key in KOI_FOOD_SHOP and item_key not in FOOD_SHOP:
            await q.answer("❌ Makanan ikan tidak cocok untuk pet ini!", show_alert=True); return

    # Cek daily limit untuk mbg_biasa (sudah dihandle di atas, tapi jaga-jaga)
    if item_key == "mbg_biasa":
        daily_limit = FOOD_SHOP_DAILY_LIMIT.get("mbg_biasa", 2)
        today = today_wib_str()
        daily_key = f"mbg_biasa_used_{today}"
        inv_daily = inv.get(daily_key, 0)
        if inv_daily >= daily_limit:
            await q.answer(f"❌ MBG Biasa sudah dibeli/dipakai {daily_limit}x hari ini!", show_alert=True); return

    inv[item_key] = (inv.get(item_key) or 0) - 1
    if inv[item_key] <= 0: del inv[item_key]
    await set_inv(user.id, inv)
    # Flush cache — xp mungkin sudah diupdate dari Mini App (race condition fix)
    _cdel(_pet_cache, pet_id)
    pet = await get_pet_by_id(pet_id)
    if not pet:
        await q.answer("❌ Gagal load data pet!", show_alert=True); return
    pet = decay_pet_stats(pet)
    old_xp = (pet.get("xp") or 0)
    extra_txt = ""

    # ── Efek khusus item Astro Paws ──────────────────────────────────────
    if food.get("mega_feast"):
        # Kenyangin SEMUA pet user sekaligus
        all_pets = await get_user_pets(user.id)
        ids_str = ",".join(str(p["id"]) for p in all_pets)
        if ids_str:
            await bulk_patch_pets([p["id"] for p in all_pets], {"hunger": 0, "last_decay": now_wib().isoformat(), "last_fed": now_wib().isoformat()})
            for p in all_pets:
                _cdel(_pet_cache, p["id"])
        extra_txt = f"\n🎉 Semua {len(all_pets)} petmu langsung kenyang!"
        await set_inv(user.id, inv)
        await q.edit_message_text(
            f"🎉 <b>Mega Moon Feast!</b> Semua petmu langsung kenyang!{extra_txt}",
            parse_mode=ParseMode.HTML, reply_markup=kb_pet(pet))
        return

    if food.get("hunger_shield"):
        # Freeze hunger 6 jam
        shield_until = (now_wib() + timedelta(hours=6)).isoformat()
        await update_pet(pet_id, {"pil_anti_lapar_until": shield_until})
        await set_inv(user.id, inv)
        await q.edit_message_text(
            f"🛡️ <b>Hunger Shield aktif!</b>\n{PETS.get(pet['pet_type'],{}).get('emoji','🐾')} <b>{pet['name']}</b> tidak lapar selama 6 jam!",
            parse_mode=ParseMode.HTML, reply_markup=kb_pet(pet))
        return

    if food.get("anti_need"):
        # Freeze hunger + anti poop 24 jam
        until = (now_wib() + timedelta(hours=24)).isoformat()
        await update_pet(pet_id, {"pil_anti_lapar_until": until, "pil_anti_pup_until": until})
        await set_inv(user.id, inv)
        await q.edit_message_text(
            f"✨ <b>Anti-Need Pill aktif!</b>\n{PETS.get(pet['pet_type'],{}).get('emoji','🐾')} <b>{pet['name']}</b> tidak lapar & tidak poop selama 24 jam!",
            parse_mode=ParseMode.HTML, reply_markup=kb_pet(pet))
        return
    # ── End efek khusus ──────────────────────────────────────────────────

    pet["hunger"]    = max(0, (pet.get("hunger") or 0) - (food.get("hunger") or 0))
    pet["happiness"] = min(100, (pet.get("happiness") or 80) + food.get("happy", 0))
    pet["health"]    = min(100, (pet.get("health") or 100) + food.get("heal", 0))
    # Cek XP Booster aktif — flush cache dulu biar baca dari DB
    _cdel(_user_cache, user.id)
    u_fresh = await get_user(user.id)
    xp_boost_until = u_fresh.get("xp_boost_until") if u_fresh else None
    xp_boosted = bool(xp_boost_until and parse_dt(xp_boost_until) > now_wib())
    xp_gain = (food.get("xp") or 0) * (2 if xp_boosted else 1)
    pet["xp"] = old_xp + xp_gain
    old_lv = calc_level(old_xp)
    new_lv = calc_level(pet["xp"])
    _cdel(_pet_cache, pet_id)
    await update_pet(pet_id, {"hunger": pet["hunger"], "happiness": pet["happiness"], "health": pet["health"], "xp": pet["xp"], "level": new_lv, "last_decay": now_wib().isoformat(), "last_fed": now_wib().isoformat()})
    lv_txt = ""
    if new_lv > old_lv:
        ms = LEVEL_MILESTONES.get(new_lv, f"Level {new_lv}!")
        lv_txt = f"\n\n✨ <b>LEVEL UP!</b> Lv.{old_lv} → Lv.{new_lv}\n{ms}"
    stat_txt = []
    if food.get("hunger"): stat_txt.append(f"Lapar -{food['hunger']}")
    if food.get("happy"):  stat_txt.append(f"Senang +{food['happy']}")
    if food.get("heal"):   stat_txt.append(f"HP +{food['heal']}")
    if xp_gain > 0:        stat_txt.append(f"XP +{xp_gain}" + (" ✨x2" if xp_boosted else ""))
    await q.edit_message_text(
        f"🍽️ <b>{pet['name']}</b> makan {food['emoji']} {food['name']}!\n{'  |  '.join(stat_txt) if stat_txt else 'Efek aktif!'}{lv_txt}",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_pet(pet)
    )
    # Notif ke partner
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id and context:
        try:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            await context.bot.send_message(
                partner_id,
                f"🍽️ <b>{safe_html(user.first_name)}</b> kasih makan {info['emoji']} <b>{pet['name']}</b>!\n"
                f"{food['emoji']} {food['name']} — Lapar -{food.get('hunger',0)}",
                parse_mode=ParseMode.HTML
            )
        except: pass

async def do_play(q, user, pet_id: int, context=None):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    last_played = parse_dt(pet.get("last_played", ""))
    elapsed_hours = (now_wib() - last_played).total_seconds() / 3600
    if elapsed_hours < 5:
        remaining_h = int(5 - elapsed_hours)
        remaining_m = int(((5 - elapsed_hours) - remaining_h) * 60)
        wait_txt = f"{remaining_h} jam {remaining_m} menit" if remaining_h > 0 else f"{remaining_m} menit"
        await q.answer(f"⏰ Ajak main cooldown 5 jam!\nTunggu {wait_txt} lagi!", show_alert=True); return

    # Cek kelaparan: kalau lapar >= 70%, kucing bisa sakit
    pet = decay_pet_stats(pet)
    if (pet.get("hunger") or 0) >= 70:
        await q.answer(
            f"⚠️ {pet['name']} terlalu lapar untuk diajak main!\nKelaparan sudah {pet.get('hunger') or 0}% — kasih makan dulu!",
            show_alert=True
        )
        # Update decay saja
        await update_pet(pet_id, {"hunger": pet["hunger"], "happiness": pet["happiness"], "health": pet["health"], "last_decay": pet["last_decay"]})
        return

    gain   = random.randint(15, 30)
    xpg    = random.randint(5, 15)
    # Flush cache — xp mungkin sudah diupdate dari Mini App (race condition fix)
    _cdel(_pet_cache, pet_id)
    pet_fresh = await get_pet_by_id(pet_id)
    if pet_fresh:
        pet["xp"] = pet_fresh.get("xp") or pet.get("xp") or 0
    old_xp = (pet.get("xp") or 0)
    pet["happiness"] = min(100, (pet.get("happiness") or 80) + gain)
    pet["hunger"]    = min(100, (pet.get("hunger") or 0) + 5)
    pet["xp"]        = old_xp + xpg
    old_lv = calc_level(old_xp)
    new_lv = calc_level(pet["xp"])
    _cdel(_pet_cache, pet_id)
    await update_pet(pet_id, {"happiness": pet["happiness"], "hunger": pet["hunger"], "xp": pet["xp"], "level": new_lv, "last_played": now_wib().isoformat(), "last_decay": pet["last_decay"], "last_fed": now_wib().isoformat()})
    activities = ["main bola ⚽", "kejar-kejaran 🏃", "main puzzle 🧩", "tiduran bareng 😴", "lomba lompat 🐸"]
    act    = random.choice(activities)
    lv_txt = f"\n✨ <b>LEVEL UP!</b> Lv.{new_lv}!" if new_lv > old_lv else ""
    await q.edit_message_text(
        f"🎾 <b>{pet['name']}</b> diajak {act}!\nSenang +{gain} | XP +{xpg}\n<i>Bisa ajak main lagi dalam 5 jam~</i>{lv_txt}",
        parse_mode=ParseMode.HTML, reply_markup=kb_pet(pet)
    )
    # Notif ke partner
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id and context:
        try:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            await context.bot.send_message(
                partner_id,
                f"🎾 <b>{safe_html(user.first_name)}</b> mengajak {info['emoji']} <b>{pet['name']}</b> {act}!\n"
                f"Senang +{gain} | XP +{xpg}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]])
            )
        except: pass

async def do_heal(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    inv = await get_inv(user.id)
    if (inv.get("medicine") or 0) <= 0:
        await q.edit_message_text(
            "💊 Kamu tidak punya obat!\nBeli di 🛒 Toko Makanan~",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Toko", callback_data="food_shop")],
                [InlineKeyboardButton("🔙", callback_data="my_pet")],
            ])
        )
        return
    inv["medicine"] = (inv.get("medicine") or 0) - 1
    if inv["medicine"] <= 0: del inv["medicine"]
    await set_inv(user.id, inv)
    pet = decay_pet_stats(pet)
    heal = FOOD_SHOP["medicine"]["heal"]
    pet["health"] = min(100, (pet.get("health") or 100) + heal)
    await update_pet(pet_id, {"health": pet["health"], "last_decay": pet["last_decay"], "last_fed": now_wib().isoformat()})
    await q.edit_message_text(
        f"💊 <b>{pet['name']}</b> diberi obat!\nKesehatan +{heal} → {pet['health']}%",
        parse_mode=ParseMode.HTML, reply_markup=kb_pet(pet)
    )

async def do_clean_poop(q, user, pet_id: int, context=None):
    """Bersihkan poop pet — happiness naik, poop_count reset, notif ke partner"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    poop_count = (pet.get("poop_count") or 0)
    if poop_count <= 0:
        await q.answer("✨ Kandang sudah bersih!", show_alert=True); return
    # Naikkan happiness karena kandang bersih
    happy_gain = min(20, poop_count * 5)
    new_happiness = min(100, (pet.get("happiness") or 80) + happy_gain)
    await update_pet(pet_id, {"poop_count": 0, "happiness": new_happiness})
    pet["poop_count"] = 0
    pet["happiness"]  = new_happiness
    await q.edit_message_text(
        f"🧹 Kandang <b>{pet['name']}</b> udah bersih!\n"
        f"Senang +{happy_gain} → {new_happiness}%\n\n"
        f"<i>Pet kamu senang kandangnya wangi lagi~ 🌸</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_pet(pet)
    )
    # Notif ke partner
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id and context:
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        try:
            await context.bot.send_message(
                partner_id,
                f"🧹 <b>{safe_html(user.first_name)}</b> udah bersihin kandang {info['emoji']} <b>{pet['name']}</b>!\n"
                f"Senang +{happy_gain} → {new_happiness}%\n\n"
                f"<i>Kandang wangi lagi~ 🌸</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")
                ]])
            )
        except: pass

async def do_bath(q, user, pet_id: int, context=None):
    """Mandiin pet — happiness & health naik, is_dirty reset, notif ke partner"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("is_sleeping"):
        await q.answer("😴 Pet lagi tidur, jangan dibangunin!", show_alert=True); return
    if not pet.get("is_dirty"):
        # Cek juga manual via last_bath
        last_bath_str = pet.get("last_bath")
        bath_required = BATH_REQUIRED_HOURS * (2 if pet.get("soap_premium_active") else 1)
        if last_bath_str:
            hours_since = (now_wib() - parse_dt(last_bath_str)).total_seconds() / 3600
            if hours_since < bath_required:
                remaining = bath_required - hours_since
                h = int(remaining)
                m = int((remaining % 1) * 60)
                await q.answer(f"✨ Pet masih bersih! Mandi lagi dalam {h}j {m}m", show_alert=True)
                return
    now = now_wib()
    happy_gain  = 20
    health_gain = 15
    new_happiness = min(100, (pet.get("happiness") or 80) + happy_gain)
    new_health    = min(100, (pet.get("health") or 100)   + health_gain)
    await update_pet(pet_id, {
        "is_dirty":    False,
        "last_bath":   now.isoformat(),
        "happiness":   new_happiness,
        "health":      new_health,
        "wangi_until": (now + timedelta(hours=6)).isoformat(),
        "last_fed":    now.isoformat(),
    })
    pet["is_dirty"]    = False
    pet["happiness"]   = new_happiness
    pet["health"]      = new_health
    pet["last_bath"]   = now.isoformat()
    pet["wangi_until"] = (now + timedelta(hours=6)).isoformat()
    await q.edit_message_text(
        f"🛁 <b>{pet['name']}</b> udah mandi bersih!\n"
        f"Senang +{happy_gain} → {new_happiness}%\n"
        f"Sehat +{health_gain} → {new_health}%\n\n"
        f"<i>Pet kamu wangi selama 6 jam ke depan~ 🌸</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_pet(pet)
    )
    # Notif ke partner
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id and context:
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        try:
            await context.bot.send_message(
                partner_id,
                f"🛁 <b>{safe_html(user.first_name)}</b> udah mandiin {info['emoji']} <b>{pet['name']}</b>!\n"
                f"Senang +{happy_gain} → {new_happiness}%\n"
                f"Sehat +{health_gain} → {new_health}%\n\n"
                f"<i>Pet wangi~ 🌸</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")
                ]])
            )
        except: pass

# ==================== SHOP ====================
async def do_buy_koi(q, user, item_key: str):
    if item_key not in KOI_FOOD_SHOP:
        await q.answer("❌ Item tidak ada!", show_alert=True); return
    item = KOI_FOOD_SHOP[item_key]
    ok = await spend_koin(user.id, item["price"], "beli_makanan")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {item['price']} 🪙", show_alert=True); return
    inv = await get_inv(user.id)
    inv[item_key] = (inv.get(item_key) or 0) + 1
    await set_inv(user.id, inv)
    u = await get_user(user.id)
    await q.edit_message_text(
        f"✅ <b>Berhasil beli!</b>\n\n"
        f"{item['emoji']} <b>{item['name']}</b> x1\n"
        f"💰 Sisa koin: <b>{u.get('koin', 0)} 🪙</b>\n"
        f"📦 Stok: <b>{inv[item_key]}x</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐟 Beli Lagi", callback_data="koi_food_shop")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )

async def show_others_pet(q, user):
    """Fitur lv 30: lihat dan kasih makan pet orang lain"""
    pet_lv = await get_pet_level(user.id)
    if pet_lv < 30:
        await q.answer("❌ Fitur ini butuh Level 30!", show_alert=True); return

    # Filter di DB langsung — jauh lebih hemat dari ambil 50 lalu filter Python
    others = await sb("GET", "pets", {
        "select": "id,pet_type,name,hunger,xp,owner1_id,owner2_id",
        "is_missing": "eq.false",
        "is_married": "eq.false",
        "owner1_id":  f"neq.{user.id}",
        "owner2_id":  f"neq.{user.id}",
        "order": "random()",
        "limit": "8",
    }) or []
    others = [p for p in others]  # already filtered
    if not others:
        await q.edit_message_text(
            "👀 Belum ada pet orang lain yang bisa dilihat~",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="my_pet")]])
        )
        return

    # Pilih random 5
    sample = random.sample(others, min(5, len(others)))
    lines  = ["👀 <b>Pet Orang Lain</b>\n━━━━━━━━━━━━━━━\n<i>Kamu bisa kasih makan pet mereka!</i>\n"]
    buttons = []
    for p in sample:
        info = PETS.get(p["pet_type"], {"emoji": "🐾", "name": "?"})
        lv   = calc_level((p.get("xp") or 0))
        h    = (p.get("hunger") or 0)
        hc   = "🔴" if h > 70 else "🟡" if h > 40 else "🟢"
        lines.append(f"{info['emoji']} <b>{p['name']}</b> Lv.{lv}  {hc} Lapar {h}%")
        buttons.append([InlineKeyboardButton(
            f"🍽️ Kasih makan {info['emoji']} {p['name']}",
            callback_data=f"feed_other_{p['id']}"
        )])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="view_others_pet")])
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="my_pet")])
    await q.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def do_feed_other(q, user, pet_id: int):
    """Kasih makan pet orang lain — pakai makanan dari inventori sendiri"""
    pet_lv = await get_pet_level(user.id)
    if pet_lv < 30:
        await q.answer("❌ Fitur ini butuh Level 30!", show_alert=True); return

    pet = await get_pet_by_id(pet_id)
    if not pet:
        await q.answer("❌ Pet tidak ditemukan!", show_alert=True); return
    if pet.get("owner1_id") == user.id or pet.get("owner2_id") == user.id:
        await q.answer("❌ Itu petmu sendiri!", show_alert=True); return

    inv = await get_inv(user.id)
    # Cari makanan biasa yang ada di inventory.
    # Kecualikan item astro/special (mega feast/shield/anti-need/dll) — efeknya buat petmu sendiri,
    # nggak cocok dipakai ke pet orang lain.
    def _is_normal_food(k):
        f = FOOD_SHOP.get(k) or {}
        if not isinstance(f, dict):
            return False
        if f.get("astro") or f.get("mega_feast") or f.get("hunger_shield") or f.get("anti_need") or f.get("mbg"):
            return False
        return "hunger" in f and (f.get("hunger") or 0) > 0
    food_items = [(k, FOOD_SHOP[k]) for k in FOOD_SHOP if k in inv and (inv.get(k) or 0) > 0 and _is_normal_food(k)]
    if not food_items:
        await q.edit_message_text(
            "🍽️ Kamu tidak punya makanan biasa!\nBeli dulu di 🛒 Toko Makanan~\n<i>(Item event/astro tidak bisa dipakai ke pet orang lain)</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Toko", callback_data="food_shop")],
                [InlineKeyboardButton("🔙", callback_data="view_others_pet")],
            ])
        )
        return

    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    buttons = []
    for k, food in food_items:
        buttons.append([InlineKeyboardButton(
            f"{food['emoji']} {food['name']} x{inv[k]}",
            callback_data=f"feedother_{pet_id}_{k}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="view_others_pet")])
    await q.edit_message_text(
        f"🍽️ Kasih makan {info['emoji']} <b>{pet['name']}</b>?\nPilih makanan:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def do_feedother_confirm(q, user, pet_id: int, item_key: str, context):
    """Eksekusi kasih makan pet orang lain"""
    pet_lv = await get_pet_level(user.id)
    if pet_lv < 30:
        await q.answer("❌ Fitur ini butuh Level 30!", show_alert=True); return

    pet = await get_pet_by_id(pet_id)
    if not pet:
        await q.answer("❌ Pet tidak ditemukan!", show_alert=True); return

    inv = await get_inv(user.id)
    if (inv.get(item_key) or 0) <= 0:
        await q.answer("❌ Stok habis!", show_alert=True); return

    food = FOOD_SHOP.get(item_key)
    if not food:
        await q.answer("❌ Item tidak dikenal!", show_alert=True); return
    # Tolak item astro/special — nggak cocok buat pet orang lain
    if food.get("astro") or food.get("mega_feast") or food.get("hunger_shield") or food.get("anti_need") or food.get("mbg"):
        await q.answer("❌ Item event/astro tidak bisa dipakai ke pet orang lain~", show_alert=True); return
    if (food.get("hunger") or 0) <= 0:
        await q.answer("❌ Item ini bukan makanan biasa!", show_alert=True); return

    # Kurangi inventory pemberi
    inv[item_key] = (inv.get(item_key) or 0) - 1
    if inv[item_key] == 0: del inv[item_key]
    await set_inv(user.id, inv)

    # Update stats pet
    pet = decay_pet_stats(pet)
    pet["hunger"]    = max(0, (pet.get("hunger") or 0) - (food.get("hunger") or 0))
    pet["happiness"] = min(100, (pet.get("happiness") or 80) + food.get("happy", 5))
    await update_pet(pet_id, {"hunger": pet["hunger"], "happiness": pet["happiness"], "last_decay": now_wib().isoformat(), "last_fed": now_wib().isoformat()})
    asyncio.create_task(task_inc(user.id, "feed_other"))

    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"🍽️ Kamu kasih makan {info['emoji']} <b>{pet['name']}</b>!\n"
        f"{food['emoji']} {food['name']} — Lapar -{food.get('hunger',0)}\n\n"
        f"<i>Baik banget~ 💕</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👀 Lihat Lainnya", callback_data="view_others_pet")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )
    # Notif ke owner pet
    sender_name = safe_html(user.username and f"@{user.username}" or user.first_name or str(user.id))
    for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
        if oid:
            try:
                await context.bot.send_message(
                    oid,
                    f"🍽️ <b>{sender_name}</b> kasih makan {info['emoji']} <b>{pet['name']}</b> kamu!\n"
                    f"{food['emoji']} {food['name']} — Lapar -{food.get('hunger',0)}\n\n"
                    f"<i>Ada yang peduli sama petmu~ 💕</i>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]])
                )
            except: pass

# ==================== JALAN JALAN ====================
def kb_jalan() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Rumah Orang Lain", callback_data="jalan_rumah")],
        [InlineKeyboardButton("🛍️ Special Store", callback_data="special_store")],
        [InlineKeyboardButton("🎰 Gacha Box", callback_data="gacha_menu")],
        [InlineKeyboardButton("🐄 Ternak", callback_data="livestock_menu")],
        [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
    ])

async def show_jalan(q, user):
    await q.edit_message_text(
        "🚶 <b>Jalan-Jalan</b>\n━━━━━━━━━━━━━━━\nMau ke mana hari ini?",
        parse_mode=ParseMode.HTML, reply_markup=kb_jalan()
    )

async def show_jalan_rumah_ask(q, user, context):
    """Minta user masukin ID rumah yang mau dikunjungi"""
    pet_lv = await get_pet_level(user.id)
    if pet_lv < 30:
        await q.answer("❌ Fitur Rumah Orang Lain butuh Level 30!", show_alert=True); return
    context.user_data["state"] = "ASK_RUMAH_ID"
    await q.edit_message_text(
        "🏠 <b>Berkunjung ke Rumah Orang Lain</b>\n━━━━━━━━━━━━━━━\n\n"
        "Masukkan <b>ID</b> orang yang mau kamu kunjungi.\n"
        "Kamu bisa kasih makan pet mereka pakai makananmu sendiri~\n\n"
        "<i>Ketik ID-nya (contoh: 8513979925):</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data="jalan_menu")]])
    )

async def show_rumah_pets(q_or_msg, user, target_id: int, context=None, is_msg=False):
    """Tampilkan pet milik target_id supaya bisa dikasih makan"""
    async def _reply(text, **kw):
        if is_msg:
            kw.pop("disable_web_page_preview", None)
            await q_or_msg.reply_text(text, **kw)
        else:
            await q_or_msg.edit_message_text(text, **kw)

    pet_lv = await get_pet_level(user.id)
    if pet_lv < 30:
        await _reply("❌ Fitur Rumah Orang Lain butuh Level 30!",
                     parse_mode=ParseMode.HTML,
                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Jalan-Jalan", callback_data="jalan_menu")]]))
        return

    if target_id == user.id:
        await _reply("❌ Itu rumahmu sendiri! Masukkan ID orang lain.",
                     parse_mode=ParseMode.HTML,
                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Jalan-Jalan", callback_data="jalan_menu")]]))
        return

    target_u = await get_user(target_id)
    if not target_u:
        await _reply("❌ User dengan ID itu tidak ditemukan~",
                     parse_mode=ParseMode.HTML,
                     reply_markup=InlineKeyboardMarkup([
                         [InlineKeyboardButton("🔁 Coba ID Lain", callback_data="jalan_rumah")],
                         [InlineKeyboardButton("🔙 Jalan-Jalan", callback_data="jalan_menu")],
                     ]))
        return

    pets = await sb("GET", "pets", {
        "select": "id,pet_type,name,hunger,xp,owner1_id,owner2_id,is_missing",
        "or": f"(owner1_id.eq.{target_id},owner2_id.eq.{target_id})",
        "is_missing": "eq.false",
    }) or []

    owner_name = safe_html(target_u.get("nickname") or target_u.get("nama") or target_u.get("username") or str(target_id))
    if not pets:
        await _reply(
            f"🏠 <b>Rumah {owner_name}</b>\n━━━━━━━━━━━━━━━\n\n"
            f"<i>Mereka belum punya pet untuk dikunjungi~</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Kunjungi ID Lain", callback_data="jalan_rumah")],
                [InlineKeyboardButton("🔙 Jalan-Jalan", callback_data="jalan_menu")],
            ]))
        return

    lines = [f"🏠 <b>Rumah {owner_name}</b>\n━━━━━━━━━━━━━━━\n<i>Kamu bisa kasih makan pet mereka~</i>\n"]
    buttons = []
    for p in pets:
        info = PETS.get(p["pet_type"], {"emoji": "🐾", "name": "?"})
        lv   = calc_level((p.get("xp") or 0))
        h    = (p.get("hunger") or 0)
        hc   = "🔴" if h > 70 else "🟡" if h > 40 else "🟢"
        lines.append(f"{info['emoji']} <b>{p['name']}</b> Lv.{lv}  {hc} Lapar {h}%")
        buttons.append([InlineKeyboardButton(
            f"🍽️ Kasih makan {info['emoji']} {p['name']}",
            callback_data=f"feed_other_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton("🔁 Kunjungi ID Lain", callback_data="jalan_rumah")])
    buttons.append([InlineKeyboardButton("🔙 Jalan-Jalan", callback_data="jalan_menu")])
    await _reply("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

# ==================== STATUS ====================
async def show_status(q, user):
    """Tampilkan ID, nickname, koin, dan info semua pet milik user"""
    u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    pets = await get_user_pets(user.id)
    nickname = u.get("nickname") or "(belum diset)"

    lines = [
        "📊 <b>Status Kamu</b>\n━━━━━━━━━━━━━━━",
        f"🆔 ID: <code>{user.id}</code>",
        f"👤 Nickname: <b>{safe_html(nickname)}</b>",
        f"💰 Koin: <b>{u.get('koin', 0)} 🪙</b>",
        "",
        f"🐾 <b>Pet kamu ({len(pets)}):</b>",
    ]
    if pets:
        for p in pets:
            info = PETS.get(p["pet_type"], {"emoji": "🐾", "name": "?"})
            lv   = calc_level((p.get("xp") or 0))
            if p.get("is_missing"):
                lines.append(f"• {info['emoji']} <b>{safe_html(p['name'])}</b> Lv.{lv} — 🏃 <i>kabur</i>")
            else:
                lines.append(
                    f"• {info['emoji']} <b>{safe_html(p['name'])}</b> Lv.{lv} "
                    f"| 🍽️{p.get('hunger',0)}% ❤️{p.get('health',100)} 😊{p.get('happiness',80)}"
                )
    else:
        lines.append("<i>Belum punya pet. Adopt di Carpet Shop yuk!</i>")

    # Tombol seperti welcome text, tanpa: Inventori, Koin Saya, Mini Game, Carpet Shop, Gacha Box, Ternak
    rows = [
        [InlineKeyboardButton("📱 Buka Mini App", url=MINI_APP_URL)],
        [InlineKeyboardButton("🐾 Pet Saya",      callback_data="my_pet"),
         InlineKeyboardButton("🛒 Toko Makan",    callback_data="food_shop")],
        [InlineKeyboardButton("🎁 Koin Harian",   callback_data="daily"),
         InlineKeyboardButton("💳 Top Up Koin",   callback_data="topup_start")],
        [InlineKeyboardButton("💸 Transfer Koin", callback_data="transfer_koin"),
         InlineKeyboardButton("⚙️ Settings",      callback_data="settings")],
        [InlineKeyboardButton("🍳 Dapur MBG",     callback_data="mbg_kitchen"),
         InlineKeyboardButton("🚶 Jalan Jalan",   callback_data="jalan_menu")],
        [InlineKeyboardButton("❓ Help & Info",    callback_data="help_info")],
        [InlineKeyboardButton("🔙 Menu",           callback_data="main_menu")],
    ]
    await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML,
                              reply_markup=InlineKeyboardMarkup(rows))

async def do_buy(q, user, item_key: str):
    all_items = {**FOOD_SHOP, **KOI_FOOD_SHOP}
    if item_key not in all_items:
        await q.answer("❌ Item tidak ada!", show_alert=True); return
    item = all_items[item_key]

    # Cek daily limit
    daily_limit = FOOD_SHOP_DAILY_LIMIT.get(item_key)
    if daily_limit:
        inv_check = await get_inv(user.id)
        today = today_wib_str()
        bought_today = inv_check.get(f"_bought_{item_key}_{today}", 0)
        if bought_today >= daily_limit:
            await q.answer(f"❌ Batas harian {item['name']} ({daily_limit}x/hari) sudah tercapai!", show_alert=True); return

    ok = await spend_koin(user.id, item["price"], "beli_item_toko")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {item['price']} 🪙", show_alert=True); return
    inv = await get_inv(user.id)
    inv[item_key] = (inv.get(item_key) or 0) + 1
    # Catat jumlah beli hari ini untuk item yang ada daily limit
    if daily_limit:
        today = today_wib_str()
        track_key = f"_bought_{item_key}_{today}"
        inv[track_key] = (inv.get(track_key) or 0) + 1
    await set_inv(user.id, inv)
    asyncio.create_task(task_inc(user.id, "buy_50"))
    u = await get_user(user.id)
    extra = f"\n<i>Batas harian: {daily_limit}x (sisa {daily_limit - inv.get(f'_bought_{item_key}_{today_wib_str()}', 1)}x lagi)</i>" if daily_limit else ""
    await q.edit_message_text(
        f"✅ <b>Berhasil beli!</b>\n\n"
        f"{item['emoji']} <b>{item['name']}</b> x1\n"
        f"💰 Sisa koin: <b>{u.get('koin', 0)} 🪙</b>\n"
        f"📦 Stok: <b>{inv[item_key]}x</b>{extra}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Beli Lagi", callback_data="food_shop")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )

async def get_custom_items_map(user_id: int) -> dict:
    """Fetch custom items milik user dari DB → return dict {item_key: info}"""
    res = await sb("GET", "custom_items", {"owner_id": f"eq.{user_id}"}) or []
    return {r["item_key"]: r for r in res}

async def show_inventory(q, user):
    inv = await get_inv(user.id)
    lines = ["🎒 <b>Inventori Kamu</b>\n━━━━━━━━━━━━━━━"]
    has_item = False
    acc_buttons = []
    special_buttons = []
    all_shops = {**FOOD_SHOP, **KOI_FOOD_SHOP}
    # Item standar
    for k, v in inv.items():
        if (v or 0) > 0 and k in all_shops:
            info = all_shops[k]
            lines.append(f"{info['emoji']} {info['name']}: <b>x{v}</b>")
            has_item = True
    # Item MBG kitchen (hasil masak)
    for k, recipe in MBG_KITCHEN_RECIPES.items():
        qty = inv.get(k, 0)
        if qty > 0:
            lines.append(f"{recipe['emoji']} {recipe['name']}: <b>x{qty}</b>")
            special_buttons.append([InlineKeyboardButton(f"{recipe['emoji']} Pakai {recipe['name']}", callback_data=f"inv_select_pet_{k}")])
            has_item = True
    # Pil anti pup
    if int(inv.get("pil_anti_pup") or 0) > 0:
        lines.append(f"💊🚫 Pil Anti Pup: <b>x{inv['pil_anti_pup']}</b>")
        special_buttons.append([InlineKeyboardButton("💊🚫 Pakai Pil Anti Pup", callback_data="inv_select_pet_pil_anti_pup")])
        has_item = True
    # Pil anti lapar
    if int(inv.get("pil_anti_lapar") or 0) > 0:
        lines.append(f"💊🍽️ Pil Anti Lapar: <b>x{inv['pil_anti_lapar']}</b>")
        special_buttons.append([InlineKeyboardButton("💊🍽️ Pakai Pil Anti Lapar", callback_data="inv_select_pet_pil_anti_lapar")])
        has_item = True
    # Pil level up
    if int(inv.get("pil_levelup") or 0) > 0:
        lines.append(f"🌟 Pil Level Up: <b>x{inv['pil_levelup']}</b>")
        special_buttons.append([InlineKeyboardButton("🌟 Pakai Pil Level Up", callback_data="inv_select_pet_pil_levelup")])
        has_item = True
    # Item Astro Paws
    for astro_key, astro_info in ASTRO_PERM_ITEMS.items():
        inv_key = _astro_to_inv_key(astro_key)
        qty = int(inv.get(inv_key) or 0)
        if qty > 0:
            lines.append(f"{astro_info['emoji']} {astro_info['name']} 🌙: <b>x{qty}</b>")
            if astro_key in ("mood_pill", "hunger_pill", "anti_pill", "moon_cake", "star_pudding", "cosmic_ramen", "mega_moon_feast", "pil_levelup"):
                special_buttons.append([InlineKeyboardButton(
                    f"{astro_info['emoji']} Pakai {astro_info['name']}",
                    callback_data=f"inv_select_pet_{inv_key}"
                )])
            has_item = True
    # Item Astro Paws 2
    for a2_key, a2_info in ASTRO2_PERM_ITEMS.items():
        qty = int(inv.get(a2_key) or 0)
        if qty > 0:
            lines.append(f"{a2_info['emoji']} {a2_info['name']} 🔴: <b>x{qty}</b>")
            if a2_info.get("isPil"):
                special_buttons.append([InlineKeyboardButton(
                    f"{a2_info['emoji']} Pakai {a2_info['name']}",
                    callback_data=f"inv_select_pet_{a2_key}"
                )])
            has_item = True
    # Kartu custom pet
    if int(inv.get("custom_pet_card") or 0) > 0:
        lines.append(f"🎨 Kartu Custom Pet: <b>x{inv['custom_pet_card']}</b>")
        special_buttons.append([InlineKeyboardButton("🎨 Buat Pet Custom!", callback_data="custom_pet_show")])
        has_item = True
    # Item custom
    custom_map = await get_custom_items_map(user.id)
    for k, v in inv.items():
        if (v or 0) > 0 and k in custom_map:
            ci = custom_map[k]
            if ci["item_type"] == "food":
                lines.append(f"{ci['emoji']} {safe_html(ci['name'])} 🍖: <b>x{v}</b>")
            else:
                lines.append(f"{ci['emoji']} {safe_html(ci['name'])} 👒: <b>x{v}</b>")
                acc_buttons.append([InlineKeyboardButton(
                    f"👒 Pakai {ci['emoji']} {safe_html(ci['name'])}",
                    callback_data=f"acc_select_pet_{k}"
                )])
            has_item = True
    # Item gacha eksklusif
    gacha_buttons = []
    for k, gi in GACHA_ITEMS.items():
        qty = inv.get(k, 0)
        if qty > 0:
            lines.append(f"{gi['emoji']} {gi['name']} 🎰: <b>x{qty}</b>")
            gacha_buttons.append([InlineKeyboardButton(
                f"✨ Pakai {gi['emoji']} {gi['name']}",
                callback_data=f"gacha_use_{k}_0"
            )])
            has_item = True

    if not has_item:
        lines.append("<i>Kosong! Beli di toko atau buat sendiri~</i>")
    kb_rows = special_buttons + acc_buttons + gacha_buttons + [
        [InlineKeyboardButton("🍳 Dapur MBG", callback_data="mbg_kitchen")],
        [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
    ]
    await q.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(kb_rows)
    )

# ==================== MINI GAMES ====================
async def show_game_menu(q, user):
    u = await get_user(user.id)
    today = today_wib_str()
    games = u.get("games_today", {})
    if isinstance(games, str):
        try: games = json.loads(games)
        except: games = {}
    if games.get("date") != today:
        games = {}
    def left(g): return GAME_MAX_PER_DAY - games.get(g, 0)
    text = (
        f"🎮 <b>Mini Game</b>\n━━━━━━━━━━━━━━━\n"
        f"Max <b>{GAME_MAX_PER_DAY}x/hari</b> per game. Gagal = 0 hadiah!\n\n"
        f"🔢 Tebak Angka — sisa {left('guess')}x\n"
        f"🎲 Dadu — sisa {left('roll')}x\n"
        f"🧠 Kuis Hewan — sisa {left('quiz')}x\n"
        f"⚽ Tangkap Bola — sisa {left('catch')}x"
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb_game())

async def start_guess(q, user, context):
    can, left = await check_game_quota(user.id, "guess")
    if not can:
        await q.answer(f"❌ Limit {GAME_MAX_PER_DAY}x/hari habis! Coba besok~", show_alert=True); return
    await use_game_quota(user.id, "guess")
    asyncio.create_task(task_inc(user.id, "play_games"))
    number = random.randint(1, 10)
    context.user_data["guess"] = number
    context.user_data["state"] = "guess"
    await q.edit_message_text(
        f"🔢 <b>Tebak Angka!</b> (sisa {left-1}x hari ini)\n\nAku lagi mikirin angka 1–10...\nKetik jawabanmu di chat!\n\n<i>Benar: +25–40 🪙 | Salah: 0 🪙</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="game_menu")]])
    )

async def answer_guess(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    txt = update.message.text.strip()
    if not txt.isdigit(): return
    ans     = int(txt)
    correct = context.user_data.get("guess")
    context.user_data["state"] = None
    if ans == correct:
        reward = random.randint(25, 40)
        await add_koin(user.id, reward, "game_tebak_angka")
        await update.message.reply_text(f"🎉 <b>BENAR!</b> Angkanya {correct}!\n<b>+{reward} 🪙</b>", parse_mode=ParseMode.HTML, reply_markup=kb_main(user.id))
    else:
        await update.message.reply_text(f"❌ Salah! Angkanya adalah <b>{correct}</b>\n+0 🪙", parse_mode=ParseMode.HTML, reply_markup=kb_main(user.id))

async def play_roll(q, user, context):
    can, left = await check_game_quota(user.id, "roll")
    if not can:
        await q.answer(f"❌ Limit {GAME_MAX_PER_DAY}x/hari habis!", show_alert=True); return
    await use_game_quota(user.id, "roll")
    asyncio.create_task(task_inc(user.id, "play_games"))
    dice   = random.randint(1, 6)
    emojis = ["", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    reward = {1: 0, 2: 0, 3: 10, 4: 20, 5: 35, 6: 50}[dice]
    if reward > 0:
        await add_koin(user.id, reward, "game_dadu")
    await q.edit_message_text(
        f"🎲 <b>Dadu!</b> (sisa {left-1}x hari ini)\n\nHasil: {emojis[dice]}\n{'<b>+'+str(reward)+' 🪙</b>' if reward else 'Tidak dapat koin 😢'}\n\n<i>Dadu 1–2 = 0 | 3=10 | 4=20 | 5=35 | 6=50</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Roll Lagi", callback_data="game_roll")],
            [InlineKeyboardButton("🔙 Game", callback_data="game_menu")],
        ])
    )

async def start_quiz(q, user, context):
    can, left = await check_game_quota(user.id, "quiz")
    if not can:
        await q.answer(f"❌ Limit {GAME_MAX_PER_DAY}x/hari habis!", show_alert=True); return
    await use_game_quota(user.id, "quiz")
    asyncio.create_task(task_inc(user.id, "play_games"))
    qz = random.choice(QUIZ_QUESTIONS)
    context.user_data["quiz"] = qz
    buttons = [[InlineKeyboardButton(f"{chr(65+i)}. {o}", callback_data=f"qans_{i}")] for i, o in enumerate(qz["opts"])]
    await q.edit_message_text(
        f"🧠 <b>Kuis Hewan!</b> (sisa {left-1}x hari ini)\n\n❓ {qz['q']}\n\n<i>Benar: +40–60 🪙 | Salah: 0 🪙</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def answer_quiz(q, user, context, chosen: int):
    qz = context.user_data.get("quiz")
    if not qz:
        await q.answer("⚠️ Kuis sudah habis!", show_alert=True); return
    context.user_data["quiz"] = None
    if chosen == qz["ans"]:
        reward = random.randint(40, 60)
        await add_koin(user.id, reward, "game_kuis")
        await q.edit_message_text(
            f"✅ <b>BENAR!</b>\nJawaban: <b>{qz['opts'][qz['ans']]}</b>\n<b>+{reward} 🪙</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧠 Lagi", callback_data="game_quiz"), InlineKeyboardButton("🔙", callback_data="game_menu")]])
        )
    else:
        await q.edit_message_text(
            f"❌ <b>Salah!</b>\nJawaban: <b>{qz['opts'][qz['ans']]}</b>\n+0 🪙",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧠 Lagi", callback_data="game_quiz"), InlineKeyboardButton("🔙", callback_data="game_menu")]])
        )

async def start_catch(q, user, context):
    can, left = await check_game_quota(user.id, "catch")
    if not can:
        await q.answer(f"❌ Limit {GAME_MAX_PER_DAY}x/hari habis!", show_alert=True); return
    await use_game_quota(user.id, "catch")
    asyncio.create_task(task_inc(user.id, "play_games"))
    pos = random.randint(0, 4)
    context.user_data["catch"] = pos
    display = " ".join(["⚽" if i == pos else "⬜" for i in range(5)])
    await q.edit_message_text(
        f"⚽ <b>Tangkap Bola!</b> (sisa {left-1}x hari ini)\n\n{display}\n\nBola ada di posisi mana? Tekan angkanya!\n<i>Benar: +25–35 🪙 | Salah: 0 🪙</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(str(i+1), callback_data=f"catch_{i}") for i in range(5)]])
    )

async def answer_catch(q, user, context, chosen: int):
    correct = context.user_data.get("catch")
    context.user_data["catch"] = None
    if not isinstance(correct, int):
        await q.answer("⏰ Sesi game sudah habis, mulai lagi ya!", show_alert=True)
        return
    if chosen == correct:
        reward = random.randint(25, 35)
        await add_koin(user.id, reward, "game_tangkap_bola")
        await q.edit_message_text(
            f"🎉 <b>TANGKAP!</b> Posisi {correct+1}!\n<b>+{reward} 🪙</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚽ Lagi", callback_data="game_catch"), InlineKeyboardButton("🔙", callback_data="game_menu")]])
        )
    else:
        await q.edit_message_text(
            f"❌ Meleset! Bolanya di posisi <b>{correct+1}</b>\n+0 🪙",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚽ Lagi", callback_data="game_catch"), InlineKeyboardButton("🔙", callback_data="game_menu")]])
        )

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    results = []
    q_upper = query.upper()

    # TAP pengiriman
    if q_upper.startswith("TAP "):
        code = query[4:].strip().upper()
        d = await get_delivery(code)
        if d and not d["is_delivered"] and d.get("owner2_id"):
            info      = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})
            tap_count = d.get("tap_count", 1)
            msg = (
                f"📦 <b>Bantu percepat pengiriman!</b>\n"
                f"{info['emoji']} <b>{d['pet_name']}</b>\n"
                f"👑 {d.get('owner1_name','?')} & 👫 {d.get('owner2_name','?')}\n\n"
                f"👆 Tap: <b>{tap_count}/{TAPS_NEEDED}</b>  [{bar(tap_count, TAPS_NEEDED, 6)}]"
            )
            results.append(InlineQueryResultArticle(
                id=code,
                title=f"📦 Bantu kirim {d['pet_name']} {info['emoji']}",
                description=f"Tap sekarang! {tap_count}/{TAPS_NEEDED} tap",
                input_message_content=InputTextMessageContent(msg, parse_mode=ParseMode.HTML),
                reply_markup=kb_delivery(code, tap_count)
            ))

    # BATTLE challenge share
    elif q_upper.startswith("BATTLE "):
        code = query[7:].strip().upper()
        battles_res = await sb("GET", "battles", {"code": f"eq.{code}", "status": "eq.waiting"})
        if battles_res:
            battle = battles_res[0]
            c_pet = await get_pet_by_id(battle["challenger_pet_id"])
            if c_pet:
                c_info = PETS.get(c_pet["pet_type"], {"emoji": "🐾"})
                c_lv = calc_level((c_pet.get("xp") or 0))
                c_score = int(c_lv * 10 * BATTLE_POWER.get(c_pet["pet_type"], 1.0))
                msg = (
                    f"⚔️ <b>Battle Challenge!</b>\n━━━━━━━━━━━━━━━\n\n"
                    f"🔵 Penantang: {c_info['emoji']} <b>{c_pet['name']}</b> Lv.{c_lv} (Skor: {c_score})\n\n"
                    f"💰 Taruhan: <b>{battle['stake']} 🪙</b>\n"
                    f"Klik tombol di bawah untuk terima tantangan!\n\n"
                    f"<i>Kamu butuh pet untuk ikut battle~</i>"
                )
                bot_name = BOT_USERNAME.lstrip("@")
                results.append(InlineQueryResultArticle(
                    id=code,
                    title=f"⚔️ Battle vs {c_pet['name']} {c_info['emoji']} (Taruhan {battle['stake']}🪙)",
                    description=f"Klik untuk terima tantangan battle!",
                    input_message_content=InputTextMessageContent(msg, parse_mode=ParseMode.HTML),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "⚔️ Terima Battle!",
                            url=f"https://t.me/{bot_name}?start=BATTLE_{code}"
                        )
                    ]])
                ))

    # MARRIAGE invite share
    elif q_upper.startswith("MARRY "):
        code = query[6:].strip().upper()
        proposal_res = await sb("GET", "marriage_proposals", {"code": f"eq.{code}", "status": "eq.pending"})
        if proposal_res:
            proposal = proposal_res[0]
            pet1 = await get_pet_by_id(proposal["pet1_id"])
            if pet1:
                p1_info = PETS.get(pet1.get("pet_type","cat"), {"emoji": "🐾"})
                bot_name = BOT_USERNAME.lstrip("@")
                marry_link = f"https://t.me/{bot_name}?start=MARRY_{code}"
                msg = (
                    f"💍 <b>Undangan Pernikahan!</b>\n━━━━━━━━━━━━━━━\n\n"
                    f"{p1_info['emoji']} <b>{pet1['name']}</b> mencari pasangan!\n\n"
                    f"Klik tombol untuk menerima proposal pernikahan ini~\n"
                    f"<i>Kamu butuh pet Level 10+ untuk nikah</i>"
                )
                results.append(InlineQueryResultArticle(
                    id=code,
                    title=f"💍 Proposal nikah dari {pet1['name']} {p1_info['emoji']}",
                    description="Klik untuk terima undangan pernikahan!",
                    input_message_content=InputTextMessageContent(msg, parse_mode=ParseMode.HTML),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💍 Terima Undangan!", url=marry_link)
                    ]])
                ))

    # AMPLOP share
    elif q_upper.startswith("AMPLOP "):
        kid = query[7:].strip().upper()
        amplop = _amplop_store.get(kid)
        if amplop and amplop["sisa_slot"] > 0:
            bot_name   = BOT_USERNAME.lstrip("@")
            claim_link = f"https://t.me/{bot_name}?start=AMPLOP_{kid}"
            msg = (
                f"🎁 <b>Amplop Kaget dari {amplop['pengirim']}!</b>\n━━━━━━━━━━━━━━━\n\n"
                f"💰 Pool: <b>{amplop['total']:,} 🪙</b>\n"
                f"🎫 Sisa slot: <b>{amplop['sisa_slot']}/{amplop['slots']}</b>\n\n"
                f"💌 <i>{safe_html(amplop['pesan'])}</i>\n\n"
                f"Klik tombol untuk rebut koinmu~ 🍀"
            )
            results.append(InlineQueryResultArticle(
                id=kid,
                title=f"🎁 Amplop Kaget — {amplop['sisa_slot']} slot tersisa!",
                description=f"Pool {amplop['total']:,}🪙 | Klik untuk rebut!",
                input_message_content=InputTextMessageContent(msg, parse_mode=ParseMode.HTML),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎁 Rebut Amplop!", url=claim_link)
                ]])
            ))

    if not results:
        results.append(InlineQueryResultArticle(
            id="help", title="🏪 The Carpet Shop — Bot Hewan Peliharaan",
            description="Ketik: tap KODE  |  battle KODE  |  marry KODE  |  amplop KODE",
            input_message_content=InputTextMessageContent(
                "🏪 <b>The Carpet Shop</b>\n\nKetik salah satu perintah berikut:\n"
                "• <code>tap KODE</code> — bantu percepat pengiriman pet\n"
                "• <code>battle KODE</code> — share tantangan battle\n"
                "• <code>marry KODE</code> — share undangan pernikahan\n"
                "• <code>amplop KODE</code> — share amplop kaget",
                parse_mode=ParseMode.HTML
            )
        ))
    await update.inline_query.answer(results, cache_time=5)

# ==================== DELETE PET ====================
async def cmd_deletepet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    pets = await get_user_pets(user.id)
    if not pets:
        await update.message.reply_text("🐾 Kamu belum punya pet yang bisa dihapus.")
        return
    if len(pets) == 1:
        pet = pets[0]
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        await update.message.reply_text(
            f"⚠️ <b>Hapus Pet?</b>\n\n"
            f"{info['emoji']} <b>{pet['name']}</b> (Lv.{calc_level(pet.get('xp',0))})\n\n"
            f"Pet akan dihapus permanen dan tidak bisa dikembalikan!\nYakin?",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Ya, Hapus!", callback_data=f"confirm_delete_{pet['id']}"),
                 InlineKeyboardButton("❌ Batal", callback_data="main_menu")]
            ])
        )
    else:
        buttons = []
        for pet in pets:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            buttons.append([InlineKeyboardButton(
                f"🗑️ {info['emoji']} {pet['name']} (Lv.{calc_level(pet.get('xp',0))})",
                callback_data=f"confirm_delete_{pet['id']}"
            )])
        buttons.append([InlineKeyboardButton("❌ Batal", callback_data="main_menu")])
        await update.message.reply_text(
            "⚠️ <b>Pilih pet yang mau dihapus:</b>\n<i>Tindakan ini tidak bisa dibatalkan!</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def do_delete_pet(q, user, pet_id: int, context):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True)
        return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    pet_name = pet["name"]
    await sb("DELETE", "pets", {"id": f"eq.{pet_id}"})
    _cdel(_pet_cache, pet_id)
    await q.edit_message_text(
        f"🗑️ <b>{pet_name}</b> {info['emoji']} telah dihapus.\n\n"
        f"<i>Kamu bisa adopt hewan baru kapan saja~</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Adopt Lagi", callback_data="carpet_shop"), InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
    )
    await log(context, f"🗑️ Hapus pet: {fmt_user(user)} hapus {info['emoji']} <b>{pet_name}</b>")
    # Notif ke partner
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id:
        try:
            await context.bot.send_message(
                partner_id,
                f"🗑️ <b>{safe_html(user.first_name)}</b> menghapus {info['emoji']} <b>{pet_name}</b>.\n"
                f"<i>Pet kalian sudah tidak ada lagi.</i>",
                parse_mode=ParseMode.HTML
            )
        except: pass
async def do_find_pet(q, user, pet_id: int, context):
    """User menekan tombol Cari Pet — kembalikan pet yang kabur"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True)
        return
    if not pet.get("is_missing"):
        await q.answer("Pet ini tidak sedang kabur~", show_alert=True)
        return

    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})

    # Bayar 1000 coin untuk cari pet
    ok = await spend_koin(user.id, 1000, "cari_partner_pet")
    if not ok:
        await q.answer("❌ Koin tidak cukup! Butuh 1.000 🪙 untuk mencari pet.", show_alert=True); return

    # Kembalikan pet: reset is_missing, pulihkan stats sedikit, update last_decay
    await update_pet(pet_id, {
        "is_missing":  False,
        "hunger":      60,   # masih lapar, perlu diurus
        "happiness":   20,   # sedih habis kabur
        "health":      max(1, (pet.get("health") or 50)),
        "last_decay":  now_wib().isoformat(),
        "last_fed":  now_wib().isoformat(),
    })
    _cdel(_pet_cache, pet_id)

    u_check = await get_user(user.id)
    sisa = (u_check.get("koin") or 0)
    await q.edit_message_text(
        f"🎉 <b>{pet['name']}</b> ditemukan!\n\n"
        f"{info['emoji']} {info['name']} kamu sudah kembali~\n"
        f"Dia tampak lapar dan sedikit sedih...\n\n"
        f"💰 Biaya cari: <b>-1.000 🪙</b> | Sisa: <b>{sisa:,} 🪙</b>\n\n"
        f"<i>Ayo urus dia lagi ya! 💕</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")],
            [InlineKeyboardButton("🍽️ Kasih Makan", callback_data=f"feed_{pet_id}")],
        ])
    )

    # Notif ke partner juga
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id:
        try:
            await context.bot.send_message(
                partner_id,
                f"🎉 <b>{pet['name']}</b> sudah ditemukan!\n"
                f"{info['emoji']} {info['name']} sudah kembali~\n\n"
                f"<i>Ayo urus dia lagi bareng! 💕</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]),
            )
        except: pass

    await log(context, f"🔍 Pet kembali: {info['emoji']} <b>{pet['name']}</b> ditemukan oleh <code>{user.id}</code>")


# ==================== SPECIAL STORE ====================
async def show_special_store(q, user):
    """Special Store — tersedia di bot dan Mini App"""
    u = await get_user(user.id)
    koin = u.get("koin", 0) if u else 0
    await q.edit_message_text(
        f"🛍️ <b>Special Store</b>\n━━━━━━━━━━━━━━━\n\n"
        f"💼 Koinmu: <b>{koin:,} 🪙</b>\n\n"
        f"🌟 <b>Pil Level Up</b> — <b>{PIL_LEVELUP_PRICE:,} 🪙</b>\n"
        f"   Naikkan 1 level pet kamu secara instan!\n\n"
        f"📱 Untuk sabun, aksesoris, dan gift item, buka <b>Mini App</b>~",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🌟 Beli Pil Level Up ({PIL_LEVELUP_PRICE:,}🪙)", callback_data="buy_pil_levelup")],
            [InlineKeyboardButton("📱 Buka Mini App", url=MINI_APP_URL)],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )

# ==================== SETTINGS ====================
async def show_settings(q, user):
    u = await get_user(user.id)
    pets = await get_user_pets(user.id)
    nickname = u.get("nickname") or "(belum diset)"
    pet_buttons = []
    for pet in pets:
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        pet_buttons.append([InlineKeyboardButton(
            f"✏️ Ganti nama {info['emoji']} {pet['name']}",
            callback_data=f"settings_rename_{pet['id']}"
        )])
    rows = [
        [InlineKeyboardButton("👤 Ganti Nickname", callback_data="settings_nickname")],
        *pet_buttons,

        [InlineKeyboardButton("🗑️ Hapus Pet", callback_data="settings_deletepet")],
        [InlineKeyboardButton("📇 ID Card", callback_data="idcard_settings")],
        [InlineKeyboardButton("💸 Transfer Koin", callback_data="transfer_koin")],
        [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
    ]
    await q.edit_message_text(
        f"⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━\n"
        f"👤 Nickname: <b>{nickname}</b>\n"
        f"💰 Koin: <b>{u.get('koin', 0)} 🪙</b>\n"
        f"🆔 ID kamu: <code>{user.id}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def cmd_deletepet_inline(q, user, context):
    """Hapus pet dari settings menu — semua owner bisa hapus"""
    pets = await get_user_pets(user.id)
    if not pets:
        await q.answer("🐾 Tidak ada pet untuk dihapus!", show_alert=True); return
    buttons = []
    for pet in pets:
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        role = "👑" if pet.get("owner1_id") == user.id else "👤"
        buttons.append([InlineKeyboardButton(
            f"🗑️ {role} {info['emoji']} {pet['name']} (Lv.{calc_level(pet.get('xp',0))})",
            callback_data=f"confirm_delete_{pet['id']}"
        )])
    buttons.append([InlineKeyboardButton("❌ Batal", callback_data="settings")])
    await q.edit_message_text(
        "⚠️ <b>Pilih pet yang mau dihapus:</b>\n<i>Tindakan ini permanen!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ==================== TRANSFER KOIN ====================
async def do_transfer_koin(update, user, target: str, amount: int, context):
    # Flush cache dulu — pastikan baca koin terbaru dari DB
    _cdel(_user_cache, user.id)
    u = await get_user(user.id)
    if not u or (u.get("koin") or 0) < amount:
        await update.message.reply_text(f"❌ Koin tidak cukup! Koinmu: {u.get('koin',0) if u else 0} 🪙")
        return
    # Cari target
    target_uid = None
    try:
        target_uid = int(target)
    except:
        res = await sb("GET", "users", {"username": f"eq.{target}"})
        target_uid = res[0]["user_id"] if res else None
    if not target_uid:
        await update.message.reply_text("❌ User tidak ditemukan!")
        return
    if target_uid == user.id:
        await update.message.reply_text("❌ Tidak bisa transfer ke diri sendiri!")
        return
    target_user = await get_user(target_uid)
    if not target_user:
        await update.message.reply_text("❌ User tidak ditemukan di database!")
        return
    # Proses transfer — kurangi sender dulu, lalu tambah receiver secara terpisah
    # Re-fetch sender koin terbaru sebelum kurangi (anti double-deduct dari cache stale)
    sender_koin = (u.get("koin") or 0)
    new_sender_koin = sender_koin - amount
    await update_user(user.id, {"koin": new_sender_koin})
    _cdel(_user_cache, user.id)  # invalidate cache setelah write
    await log_koin(user.id, -amount, "transfer_keluar")
    # Flush cache receiver juga sebelum add
    _cdel(_user_cache, target_uid)
    await add_koin(target_uid, amount, "transfer_masuk")
    sender_name = get_display_name(u)
    target_name = get_display_name(target_user)
    await update.message.reply_text(
        f"💸 <b>Transfer berhasil!</b>\n\n"
        f"Kamu transfer <b>{amount} 🪙</b> ke <b>{target_name}</b>\n"
        f"Sisa koin: <b>{new_sender_koin} 🪙</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
    )
    # Notif ke penerima
    try:
        await context.bot.send_message(
            target_uid,
            f"💸 <b>{sender_name}</b> transfer <b>{amount} 🪙</b> ke kamu!\n"
            f"Total koin: <b>{target_user.get('koin',0) + amount} 🪙</b>",
            parse_mode=ParseMode.HTML
        )
    except: pass
    await log(context, f"💸 Transfer: {fmt_user(user)} → {target_name} ({target_uid}): {amount} 🪙")

# ==================== ACCESSORY ====================
async def do_equip_accessory(q, user, item_key: str, pet_id: int, context=None):
    """Pasang aksesoris ke pet"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    res = await sb("GET", "users", {"user_id": f"eq.{user.id}"})
    if not res: await q.answer("❌ Error!", show_alert=True); return
    raw_inv = res[0].get("inventory", {})
    inv = json.loads(raw_inv) if isinstance(raw_inv, str) else (raw_inv or {})
    if (inv.get(item_key) or 0) <= 0:
        await q.answer("❌ Item habis!", show_alert=True); return

    # Cek apakah custom item
    is_custom = item_key.startswith("ci_") or item_key.startswith("custom_")
    if is_custom:
        custom_map = await get_custom_items_map(user.id)
        ci = custom_map.get(item_key)
        if not ci or ci["item_type"] != "accessory":
            await q.answer("❌ Bukan aksesoris!", show_alert=True); return
        item = {"emoji": ci["emoji"], "name": ci["name"]}
    else:
        item = SPECIAL_SHOP.get(item_key, {})
        if item.get("category") != "acc":
            await q.answer("❌ Bukan aksesoris!", show_alert=True); return

    # Kurangi inventory
    inv[item_key] = (inv.get(item_key) or 0) - 1
    if inv[item_key] <= 0: del inv[item_key]
    await sb("PATCH", "users", {"user_id": f"eq.{user.id}"}, {"inventory": inv})
    _cdel(_user_cache, user.id)
    # Pasang ke pet — simpan item_key biar bisa dikembalikan ke inven saat dilepas
    await update_pet(pet_id, {"accessory": item["emoji"], "accessory_name": item["name"], "accessory_key": item_key})
    pet["accessory"] = item["emoji"]
    pet["accessory_name"] = item["name"]
    pet_lv = await get_pet_level(user.id)
    await q.edit_message_text(
        f"✨ {item['emoji']} <b>{item['name']}</b> dipasang ke <b>{pet['name']}</b>!\n"
        f"Aksesoris langsung keliatan di nama pet~",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_pet(pet, pet_lv)
    )
    # Notif partner
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id and context:
        info = PETS.get(pet["pet_type"], {"emoji":"🐾"})
        try:
            await context.bot.send_message(
                partner_id,
                f"✨ <b>{safe_html(user.first_name)}</b> pasang {item['emoji']} <b>{item['name']}</b> ke {info['emoji']} <b>{pet['name']}</b>!",
                parse_mode=ParseMode.HTML
            )
        except: pass

async def do_remove_accessory(q, user, pet_id: int):
    """Lepas aksesoris dari pet — balik ke inventory (FIXED: pakai accessory_key dari DB)"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if not pet.get("accessory"):
        await q.answer("❌ Pet tidak pakai aksesoris!", show_alert=True); return
    acc_emoji = pet["accessory"]
    acc_name  = pet.get("accessory_name") or ""

    # FIX: Ambil accessory_key langsung dari pet DB — ini yang disimpan saat equip
    item_key = pet.get("accessory_key")

    # Fallback lama kalau accessory_key kosong (data lama sebelum fix)
    if not item_key:
        try:
            item_key = next(
                (k for k, v in SPECIAL_SHOP.items()
                 if v.get("emoji") == acc_emoji and v.get("category") == "acc"),
                None
            )
        except NameError:
            pass
    if not item_key and acc_name:
        item_key = acc_name.lower().replace(" ", "_")

    # Kembalikan ke inventory
    if item_key:
        _cdel(_user_cache, user.id)  # flush cache biar baca inventory fresh dari DB
        inv = await get_inv(user.id)
        inv[item_key] = (inv.get(item_key) or 0) + 1
        await set_inv(user.id, inv)

    # Lepas dari pet & bersihkan accessory_key juga
    await update_pet(pet_id, {"accessory": None, "accessory_name": None, "accessory_key": None})
    _cdel(_pet_cache, pet_id)
    pet["accessory"]      = None
    pet["accessory_name"] = None
    pet["accessory_key"]  = None
    pet_lv = await get_pet_level(user.id)
    returned_txt = f"\n<i>🎒 {acc_emoji} {acc_name} kembali ke inventorimu~</i>" if item_key else "\n<i>(Aksesoris tidak ada di inventori — mungkin data lama)</i>"
    await q.edit_message_text(
        f"✅ Aksesoris {acc_emoji} dilepas dari <b>{pet['name']}</b>!{returned_txt}",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_pet(pet, pet_lv)
    )

# ==================== PART 2 - Lanjutan pets.py ====================
# ==================== CREATE PET (ADMIN) ====================
async def cmd_createpet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: /createpet <user_id> <pet_type> [nama]"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) < 2:
        all_types = ", ".join(sorted(PETS.keys()))
        await update.message.reply_text(
            f"Usage: /createpet <user_id> <pet_type> [nama]\n\nJenis pet:\n{all_types}"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id harus angka"); return

    pet_type = args[1].lower()
    if pet_type not in PETS:
        await update.message.reply_text(f"❌ Pet type tidak valid: <code>{pet_type}</code>\nCek /createpet untuk list.", parse_mode=ParseMode.HTML)
        return

    info     = PETS[pet_type]
    pet_name = " ".join(args[2:]) if len(args) > 2 else info["name"]

    new_pet = {
        "owner1_id":  target_id,
        "owner2_id":  None,
        "name":       pet_name,
        "pet_type":   pet_type,
        "xp":         0, "level": 1,
        "hunger":     0, "happiness": 100, "health": 100,
        "poop_count": 0, "is_sleeping": False, "is_dirty": False,
        "is_missing": False, "is_married": False, "is_child": False,
        "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
    }
    result = await sb("POST", "pets", {}, new_pet)
    if result:
        pet_id = result[0].get("id", "?") if isinstance(result, list) else "?"
        await update.message.reply_text(
            f"✅ Pet berhasil dibuat!\n"
            f"👤 User: <code>{target_id}</code>\n"
            f"{info['emoji']} <b>{pet_name}</b> ({pet_type})\n"
            f"🆔 Pet ID: <code>{pet_id}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ Gagal buat pet, cek log.")

# ==================== RIWAYAT KOIN ====================
_RIWAYAT_PAGE_SIZE = 10

async def cmd_riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner only: /riwayat <user_id> [page]"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /riwayat <user_id>"); return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id harus angka"); return
    page = int(args[1]) if len(args) > 1 else 0
    await _send_riwayat(update.message, target_id, page)

async def _send_riwayat(msg_or_q, target_id: int, page: int, edit: bool = False):
    offset = page * _RIWAYAT_PAGE_SIZE
    rows = await sb("GET", "coin_history", {
        "user_id":    f"eq.{target_id}",
        "order":      "created_at.desc",
        "limit":      str(_RIWAYAT_PAGE_SIZE),
        "offset":     str(offset),
    }) or []

    # Count total untuk pagination
    count_rows = await sb("GET", "coin_history", {
        "user_id":  f"eq.{target_id}",
        "select":   "id",
    }) or []
    total = len(count_rows)
    total_pages = max(1, (total + _RIWAYAT_PAGE_SIZE - 1) // _RIWAYAT_PAGE_SIZE)

    # Cek user info
    u_data = await sb("GET", "users", {"user_id": f"eq.{target_id}", "select": "username,nama,koin"})
    u_info = u_data[0] if u_data else {}
    nama   = u_info.get("nama") or u_info.get("username") or str(target_id)
    koin   = u_info.get("koin", "?")

    if not rows:
        text = f"📒 <b>Riwayat Koin</b>\n👤 {nama} (<code>{target_id}</code>)\n💰 Saldo: <b>{koin} 🪙</b>\n\n<i>Belum ada riwayat.</i>"
    else:
        lines = [f"📒 <b>Riwayat Koin</b> — {nama} (<code>{target_id}</code>)",
                 f"💰 Saldo: <b>{koin} 🪙</b>  |  Hal. {page+1}/{total_pages}\n━━━━━━━━━━━━━━━"]
        for r in rows:
            amt    = r.get("amount", 0)
            reason = r.get("reason", "?")
            label  = _KOIN_LOG_REASONS.get(reason, f"❓ {reason}")
            arah   = f"+{amt}" if amt > 0 else str(amt)
            emoji  = "📥" if amt > 0 else "📤"
            ts     = (r.get("created_at") or "")[:16].replace("T", " ")
            lines.append(f"{emoji} <b>{arah} 🪙</b>  {label}\n    <i>{ts}</i>")
        text = "\n".join(lines)

    # Tombol navigasi
    btns = []
    if page > 0:
        btns.append(InlineKeyboardButton("◀️ Prev", callback_data=f"riwayat_{target_id}_{page-1}"))
    if page + 1 < total_pages:
        btns.append(InlineKeyboardButton("Next ▶️", callback_data=f"riwayat_{target_id}_{page+1}"))
    kb = InlineKeyboardMarkup([btns]) if btns else None

    if edit:
        await msg_or_q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg_or_q.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# ==================== ADMIN ====================
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    total_u = await get_count("users")
    total_p = await get_count("pets")
    total_d = await get_count("deliveries")
    pending_d = await get_count("deliveries", {"is_delivered": "eq.false", "started": "eq.true"})
    await update.message.reply_text(
        f"🔧 <b>Admin Panel</b>\n━━━━━━━━━━━━━━━\n"
        f"👤 Total users: <b>{total_u}</b>\n"
        f"🐾 Total pets: <b>{total_p}</b>\n"
        f"📦 Total deliveries: <b>{total_d}</b>\n"
        f"  ↳ ⏳ Lagi perjalanan: <b>{pending_d}</b>\n\n"
        f"<code>/addkoin [user_id] [jumlah]</code>\n"
        f"<code>/delivery [nama pet]</code>\n"
        f"<code>/recoverpet [jenis] [nama] [owner1_id] [owner2_id] [level]</code>",
        parse_mode=ParseMode.HTML
    )

async def cmd_cheat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🤫 Secret cheat code"""
    user = update.effective_user
    await add_koin(user.id, 10000, "cheat")
    u = await get_user(user.id)
    await update.message.reply_text(
        f"🤫 <b>CHEAT ACTIVATED!</b>\n\n"
        f"💰 +10.000 koin!\n\n"
        f"💼 Total koin: <b>{u.get('koin', 0)} 🪙</b>\n\n"
        f"<i>ssstt jangan bilang siapa siapa lhoo 🤫</i>",
        parse_mode=ParseMode.HTML
    )
    await log(context, f"🤫 Cheat: {fmt_user(user)}")

async def cmd_addkoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addkoin [user_id] [jumlah]"); return
    try:
        uid    = int(context.args[0])
        amount = int(context.args[1])
        await add_koin(uid, amount, "admin_give")
        await update.message.reply_text(f"✅ +{amount} 🪙 ke user {uid}")
        await log(context, f"🔧 Admin tambah {amount} koin ke {uid}")
    except:
        await update.message.reply_text("❌ Format salah!")

async def cmd_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /delivery namapet — force deliver 1 pet
              /delivery all     — force deliver SEMUA yang pending & sudah punya partner"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text(
            "❌ Usage:\n"
            "• <code>/delivery namapet</code> — force deliver 1 pet\n"
            "• <code>/delivery all</code> — force deliver semua pending (yang sudah punya partner)",
            parse_mode=ParseMode.HTML
        )
        return

    pet_name = " ".join(context.args).strip()

    # ===== /delivery all =====
    if pet_name.lower() == "all":
        prog = await update.message.reply_text("⏳ Mengambil semua pending delivery...")
        all_deliveries = await sb_get_all("deliveries", {
            "is_delivered": "eq.false",
            "started":      "eq.true",
            "select":       "id,code,owner1_id,owner2_id,pet_type,pet_name,tap_count",
        })
        # Filter yang sudah punya owner2
        pending = [d for d in all_deliveries if d.get("owner2_id")]
        if not pending:
            await prog.edit_text("✅ Tidak ada pending delivery yang siap dikirim.")
            return

        success = 0
        fail = 0
        skipped = 0
        for d in pending:
            try:
                info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})
                await _create_pet_from_delivery(d, d["code"])
                await update_delivery(d["code"], {"is_delivered": True})
                success += 1
                # Notif ke kedua owner
                for oid in [d.get("owner1_id"), d.get("owner2_id")]:
                    if oid:
                        try:
                            await context.bot.send_message(
                                oid,
                                f"🎊 <b>Pet kamu sudah tiba!</b>\n"
                                f"{info['emoji']} <b>{d['pet_name']}</b> siap dirawat!\n\n"
                                f"<i>Force delivered oleh admin~ 💕</i>",
                                parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")
                                ]])
                            )
                        except: pass
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Force deliver all error for {d.get('pet_name')}: {e}")
                fail += 1

        await prog.edit_text(
            f"✅ <b>Force Deliver All selesai!</b>\n\n"
            f"📦 Total pending: <b>{len(pending)}</b>\n"
            f"✅ Berhasil: <b>{success}</b>\n"
            f"❌ Gagal: <b>{fail}</b>",
            parse_mode=ParseMode.HTML
        )
        await log(context, f"🚀 Force deliver ALL: {success}/{len(pending)} pet dikirim oleh {fmt_user(update.effective_user)}")
        return

    # ===== /delivery namapet =====
    # Cari delivery yang belum dikirim dengan nama pet tersebut
    deliveries = await sb("GET", "deliveries", {
        "is_delivered": "eq.false",
        "started": "eq.true",
        "pet_name": f"ilike.{pet_name}",
    })
    if not deliveries:
        # Coba tanpa filter started (mungkin belum ada partner)
        deliveries = await sb("GET", "deliveries", {
            "is_delivered": "eq.false",
            "pet_name": f"ilike.{pet_name}",
        })

    if not deliveries:
        await update.message.reply_text(
            f"❌ Delivery untuk pet <b>{safe_html(pet_name)}</b> tidak ditemukan atau sudah delivered.",
            parse_mode=ParseMode.HTML
        )
        return

    d = deliveries[0]
    info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})

    if not d.get("owner2_id"):
        # Tampilkan info delivery yg belum punya partner
        bot_name = BOT_USERNAME.lstrip("@")
        kode = d.get("kode_invite", "?")
        invite_link = f"https://t.me/{bot_name}?start={kode}" if kode and kode != "?" else "-"
        await update.message.reply_text(
            f"⚠️ <b>{safe_html(d['pet_name'])}</b> belum punya partner.\n"
            f"Owner 1: <code>{d['owner1_id']}</code>\n"
            f"Kode invite: <code>{kode}</code>\n"
            f"Link: {invite_link}\n\n"
            f"Tidak bisa force deliver tanpa 2 owner.",
            parse_mode=ParseMode.HTML
        )
        return
    await _create_pet_from_delivery(d, d["code"])
    await update_delivery(d["code"], {"is_delivered": True})

    await update.message.reply_text(
        f"✅ <b>Force deliver berhasil!</b>\n"
        f"{info['emoji']} <b>{safe_html(d['pet_name'])}</b> ({info['name']}) langsung diantar!\n"
        f"👤 Owner 1: <code>{d['owner1_id']}</code>\n"
        f"👤 Owner 2: <code>{d.get('owner2_id')}</code>",
        parse_mode=ParseMode.HTML
    )

    for oid in [d.get("owner1_id"), d.get("owner2_id")]:
        if oid:
            try:
                await context.bot.send_message(
                    oid,
                    f"🎊 <b>Pet kamu sudah tiba!</b>\n"
                    f"{info['emoji']} <b>{d['pet_name']}</b> siap dirawat!\n\n"
                    f"Selamat merawat peliharaanmu~ 💕",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")
                    ]])
                )
            except Exception as e:
                logger.warning(f"Notif force-deliver gagal ke {oid}: {e}")

    await log(context, f"🚀 Force deliver: {info['emoji']} <b>{safe_html(d['pet_name'])}</b> → owner <code>{d['owner1_id']}</code>")



async def cmd_recovercarpaws(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: /recovercarpaws username tg_id — fix telegram_user_id akun Car Paws yang ke-0"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    usage = (
        "🔑 <b>Recover Akun Car Paws</b>\n\n"
        "Usage:\n"
        "<code>/recovercarpaws username tg_id</code>\n\n"
        "Contoh:\n"
        "<code>/recovercarpaws elegant 6897393675</code>\n\n"
        "Fungsi: update telegram_user_id akun @username ke tg_id yang benar."
    )

    if len(context.args) < 2:
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return

    username = context.args[0].lower().lstrip("@")
    try:
        new_tg_id = str(int(context.args[1]))
    except ValueError:
        await update.message.reply_text("❌ Telegram ID harus berupa angka!", parse_mode=ParseMode.HTML)
        return

    # Cari akun di cp_accounts
    async with httpx.AsyncClient() as client:
        # Cek username di semua slot
        params = f"or=(username.eq.{username},username2.eq.{username},username3.eq.{username},username4.eq.{username})"
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/cp_accounts?{params}&select=id,display_name,username,telegram_user_id",
            headers=HEADERS
        )
        accounts = resp.json()

    if not accounts:
        await update.message.reply_text(
            f"❌ Akun dengan username <b>@{safe_html(username)}</b> tidak ditemukan di Car Paws!",
            parse_mode=ParseMode.HTML
        )
        return

    acc = accounts[0]
    old_tg_id = acc.get("telegram_user_id", "?")

    # Konfirmasi sebelum update
    msg = await update.message.reply_text(
        f"⚠️ <b>Konfirmasi Recover</b>\n\n"
        f"Akun: <b>{safe_html(acc.get('display_name','?'))}</b> (@{safe_html(acc.get('username','?'))}))\n"
        f"TG ID lama: <code>{old_tg_id}</code>\n"
        f"TG ID baru: <code>{new_tg_id}</code>\n\n"
        f"Ketik <code>/confirmrecover {acc['id']} {new_tg_id}</code> untuk konfirmasi.",
        parse_mode=ParseMode.HTML
    )


async def cmd_confirmrecover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: konfirmasi recover akun Car Paws"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /confirmrecover account_id tg_id", parse_mode=ParseMode.HTML)
        return

    acc_id = context.args[0]
    try:
        new_tg_id = str(int(context.args[1]))
    except ValueError:
        await update.message.reply_text("❌ Telegram ID harus angka!", parse_mode=ParseMode.HTML)
        return

    async with httpx.AsyncClient() as client:
        # Update telegram_user_id
        resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/cp_accounts?id=eq.{acc_id}",
            headers=HEADERS,
            json={"telegram_user_id": new_tg_id}
        )

    if resp.status_code in (200, 204):
        await update.message.reply_text(
            f"✅ <b>Berhasil!</b>\n\n"
            f"Akun ID <code>{acc_id}</code> sekarang terhubung ke Telegram ID <code>{new_tg_id}</code>.\n"
            f"User bisa login lagi via Car Paws.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"❌ Gagal update: {resp.text}",
            parse_mode=ParseMode.HTML
        )


async def cmd_recoverpet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner only: /recoverpet jenis nama owner1_id owner2_id level — tambahin pet langsung ke DB"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    usage = (
        "❌ Usage:\n"
        "<code>/recoverpet jenis nama owner1_id owner2_id level</code>\n\n"
        "Contoh:\n"
        "<code>/recoverpet cat Mimi 123456789 987654321 5</code>\n\n"
        "Jenis yang tersedia: " + ", ".join(f"<code>{k}</code>" for k in PETS.keys())
    )
    if len(context.args) < 5:
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return

    # Parse args: jenis nama owner1_id owner2_id level
    # nama bisa spasi, jadi ambil dari tengah
    pet_type  = context.args[0].lower()
    try:
        level     = int(context.args[-1])
        owner2_id = int(context.args[-2])
        owner1_id = int(context.args[-3])
        pet_name  = " ".join(context.args[1:-3]).strip()
    except (ValueError, IndexError):
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return

    if pet_type not in PETS:
        await update.message.reply_text(
            f"❌ Jenis pet <b>{safe_html(pet_type)}</b> tidak valid!\n\n" + usage,
            parse_mode=ParseMode.HTML
        )
        return

    if not pet_name:
        await update.message.reply_text("❌ Nama pet tidak boleh kosong!", parse_mode=ParseMode.HTML)
        return

    level = max(1, min(MAX_LEVEL, level))
    xp    = (level - 1) * XP_PER_LEVEL  # XP minimal untuk level tersebut

    info = PETS[pet_type]
    new_pet = await upsert_pet({
        "owner1_id":   owner1_id,
        "owner2_id":   owner2_id,
        "name":        pet_name,
        "pet_type":    pet_type,
        "level":       level,
        "xp":          xp,
        "hunger":      30,
        "happiness":   80,
        "health":      100,
        "last_decay":  now_wib().isoformat(),
        "last_fed":  now_wib().isoformat(),
        "last_played": (now_wib() - timedelta(hours=6)).isoformat(),
        "created_at":  now_wib().isoformat(),
    })

    if not new_pet:
        await update.message.reply_text("❌ Gagal membuat pet. Cek log untuk detail.")
        return

    if isinstance(new_pet, list):
        new_pet = new_pet[0]

    await update.message.reply_text(
        f"✅ <b>Pet berhasil di-recover!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{info['emoji']} <b>{safe_html(pet_name)}</b> ({info['name']})\n"
        f"⭐ Level: <b>{level}</b> | XP: <b>{xp}</b>\n"
        f"👤 Owner 1: <code>{owner1_id}</code>\n"
        f"👤 Owner 2: <code>{owner2_id}</code>\n"
        f"🆔 Pet ID: <code>{new_pet.get('id', '?')}</code>",
        parse_mode=ParseMode.HTML
    )

    # Notif ke kedua owner
    for oid in [owner1_id, owner2_id]:
        try:
            await context.bot.send_message(
                oid,
                f"🎁 <b>Pet kamu telah dipulihkan!</b>\n"
                f"{info['emoji']} <b>{pet_name}</b> (Lv.{level}) sudah ada di akunmu.\n\n"
                f"Selamat merawat peliharaanmu~ 💕",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")
                ]])
            )
        except Exception as e:
            logger.warning(f"Notif recoverpet gagal ke {oid}: {e}")

    await log(context, f"🔧 Recover pet: {info['emoji']} <b>{safe_html(pet_name)}</b> Lv{level} → owner1 <code>{owner1_id}</code> owner2 <code>{owner2_id}</code>")





# ==================== BATTLE ACCEPT (via start link) ====================
async def handle_battle_accept(update: Update, context: ContextTypes.DEFAULT_TYPE, battle_code: str):
    """User klik link battle → pilih pet dulu, lalu battle"""
    user = update.effective_user
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    battles_res = await sb("GET", "battles", {"code": f"eq.{battle_code}", "status": "eq.waiting"})
    if not battles_res:
        await update.message.reply_text("❌ Battle tidak ditemukan atau sudah selesai!")
        return
    battle = battles_res[0]
    if battle["challenger_id"] == user.id:
        await update.message.reply_text("❌ Tidak bisa battle sama diri sendiri!")
        return

    # Ambil pet user
    pets = await get_user_pets(user.id)
    active_pets = [p for p in pets if not p.get("is_missing") and not p.get("is_married")]
    if not active_pets:
        await update.message.reply_text("❌ Kamu tidak punya pet untuk battle!\nAdopt dulu di 🏪 Carpet Shop~")
        return

    # Ambil info challenger
    c_pet = await get_pet_by_id(battle["challenger_pet_id"])
    c_info = PETS.get(c_pet["pet_type"], {"emoji": "🐾"}) if c_pet else {"emoji": "⚔️"}
    c_lv = calc_level((c_pet.get("xp") or 0)) if c_pet else 1
    c_score = int(c_lv * 10 * BATTLE_POWER.get(c_pet.get("pet_type","cat"), 1.0) * (2.0 if "battle_2x" in (c_pet.get("special_ability") or "") else 1.0)) if c_pet else 0

    if len(active_pets) == 1:
        # Langsung battle
        await _execute_battle(update, context, battle, battle_code, user, active_pets[0])
    else:
        # Pilih pet dulu
        context.user_data["pending_battle_code"] = battle_code
        buttons = []
        for pet in active_pets:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            lv = calc_level(pet.get("xp") or 0)
            score = int(lv * 10 * BATTLE_POWER.get(pet["pet_type"], 1.0) * (2.0 if "battle_2x" in (pet.get("special_ability") or "") else 1.0)) + (pet.get("battle_score_bonus") or 0)
            buttons.append([InlineKeyboardButton(
                f"{info['emoji']} {pet['name']} Lv.{lv} (Skor:{score})",
                callback_data=f"battle_accept_pet_{pet['id']}_{battle_code}"
            )])
        await update.message.reply_text(
            f"⚔️ <b>Battle Challenge!</b>\n\n"
            f"Penantang: {c_info['emoji']} <b>{c_pet['name'] if c_pet else '?'}</b> Lv.{c_lv} (Skor:{c_score})\n"
            f"💰 Taruhan: <b>{battle['stake']} 🪙</b>\n\n"
            f"Pilih pet kamu untuk battle:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def _execute_battle(update_or_q, context, battle: dict, battle_code: str, user, my_pet: dict):
    """Eksekusi battle — bisa dari message maupun callback"""
    is_msg = hasattr(update_or_q, 'message')
    reply = update_or_q.message.reply_text if is_msg else update_or_q.edit_message_text

    u = await get_user(user.id)
    if (u.get("koin") or 0) < battle["stake"]:
        await reply(f"❌ Koin tidak cukup! Butuh {battle['stake']} 🪙")
        return

    c_pet = await get_pet_by_id(battle["challenger_pet_id"])
    if not c_pet:
        await reply("❌ Pet penantang tidak ditemukan!")
        return

    # Update battle status dulu (anti double)
    patch = await sb("PATCH", "battles",
        {"code": f"eq.{battle_code}", "status": "eq.waiting"},
        {"status": "done", "opponent_pet_id": my_pet["id"], "opponent_id": user.id}
    )

    # Kalkulasi
    c_lv  = calc_level((c_pet.get("xp") or 0))
    my_lv = calc_level((my_pet.get("xp") or 0))
    c_bonus  = (c_pet.get("battle_score_bonus") or 0)
    my_bonus = (my_pet.get("battle_score_bonus") or 0)
    c_ability_mult  = 2.0 if "battle_2x" in (c_pet.get("special_ability") or "") else 1.0
    my_ability_mult = 2.0 if "battle_2x" in (my_pet.get("special_ability") or "") else 1.0
    c_score  = (c_lv  * 10 * BATTLE_POWER.get(c_pet["pet_type"], 1.0)  * c_ability_mult  + c_bonus)  * random.uniform(0.8, 1.2)
    my_score = (my_lv * 10 * BATTLE_POWER.get(my_pet["pet_type"], 1.0) * my_ability_mult + my_bonus) * random.uniform(0.8, 1.2)

    c_info  = PETS.get(c_pet["pet_type"],  {"emoji": "🐾"})
    my_info = PETS.get(my_pet["pet_type"], {"emoji": "🐾"})
    stake   = battle["stake"]

    if my_score > c_score:
        # Aku (opponent) menang
        await add_koin(user.id, stake, "battle_menang")
        await spend_koin(battle["challenger_id"], stake, "battle_kalah")
        # Tambah battle_wins ke pet yang menang
        new_wins = (my_pet.get("battle_wins") or 0) + 1
        await update_pet(my_pet["id"], {"battle_wins": new_wins})
        result = (f"🏆 <b>{my_pet['name']}</b> MENANG!\n\n"
                  f"{my_info['emoji']} {my_pet['name']} ({my_score:.0f}) vs "
                  f"{c_info['emoji']} {c_pet['name']} ({c_score:.0f})\n\n"
                  f"💰 +{stake} 🪙 direbut dari penantang!\n"
                  f"🏆 Total menang: <b>{new_wins}x</b>")
        notif_challenger = (f"⚔️ <b>{c_pet['name']}</b> kalah battle!\n"
                            f"vs {my_info['emoji']} {my_pet['name']}\n💸 -{stake} 🪙")
        winner_id = user.id
    else:
        # Penantang menang
        await spend_koin(user.id, stake, "battle_kalah")
        await add_koin(battle["challenger_id"], stake, "battle_menang")
        # Tambah battle_wins ke pet challenger yang menang
        new_wins_c = (c_pet.get("battle_wins") or 0) + 1
        await update_pet(c_pet["id"], {"battle_wins": new_wins_c})
        result = (f"💀 <b>{my_pet['name']}</b> KALAH!\n\n"
                  f"{my_info['emoji']} {my_pet['name']} ({my_score:.0f}) vs "
                  f"{c_info['emoji']} {c_pet['name']} ({c_score:.0f})\n\n"
                  f"💸 -{stake} 🪙 diambil penantang!")
        notif_challenger = (f"⚔️ <b>{c_pet['name']}</b> menang battle!\n"
                            f"vs {my_info['emoji']} {my_pet['name']}\n💰 +{stake} 🪙\n"
                            f"🏆 Total menang: <b>{new_wins_c}x</b>")
        winner_id = battle["challenger_id"]

    await sb("PATCH", "battles", {"code": f"eq.{battle_code}"}, {"winner_id": winner_id})

    await reply(result, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{my_pet['id']}")]]))

    try:
        await context.bot.send_message(battle["challenger_id"], notif_challenger, parse_mode=ParseMode.HTML)
    except: pass

# ==================== PENITIPAN (BOARDING) ====================
async def show_boarding_menu(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("expedition_until") and parse_dt(pet.get("expedition_until","")) > now_wib():
        await q.answer("✈️ Pet lagi ekspedisi!", show_alert=True); return
    u = await get_user(user.id)
    koin = (u.get("koin") or 0)
    await q.edit_message_text(
        f"🏨 <b>Penitipan Pet</b>\n━━━━━━━━━━━━━━━\n"
        f"Titip <b>{pet['name']}</b> ke penitipan!\n\n"
        f"💰 Biaya: <b>{BOARDING_COST_PER_DAY} 🪙 / hari</b>\n"
        f"Pet tetap sehat & aman selama dititip!\n\n"
        f"💼 Koinmu: <b>{koin} 🪙</b>\n\nPilih lama penitipan:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"1 Hari ({BOARDING_COST_PER_DAY}🪙)", callback_data=f"boarding_confirm_{pet_id}_1")],
            [InlineKeyboardButton(f"3 Hari ({BOARDING_COST_PER_DAY*3}🪙)", callback_data=f"boarding_confirm_{pet_id}_3")],
            [InlineKeyboardButton(f"7 Hari ({BOARDING_COST_PER_DAY*7}🪙)", callback_data=f"boarding_confirm_{pet_id}_7")],
            [InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def do_boarding_confirm(q, user, pet_id: int, days: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    cost = BOARDING_COST_PER_DAY * days
    ok = await spend_koin(user.id, cost, "boarding")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {cost} 🪙", show_alert=True); return
    boarding_until = (now_wib() + timedelta(days=days)).isoformat()
    # Pet di penitipan: sehat, bahagia, tidak lapar
    await update_pet(pet_id, {
        "boarding_until": boarding_until,
        "health": 100,
        "happiness": 100,
        "hunger": 0,
        "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
    })
    await q.edit_message_text(
        f"🏨 <b>{pet['name']}</b> berhasil dititipkan!\n\n"
        f"💰 Biaya: <b>{cost} 🪙</b>\n"
        f"⏰ Selesai: <b>{fmt_wib(parse_dt(boarding_until))}</b>\n\n"
        f"❤️ Health, happiness, dan hunger sudah dipulihkan!\n"
        f"<i>Pet kamu aman dan sehat selama di penitipan~ 🐾</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
    )

async def do_boarding_pickup(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    # Cek apakah pet ini sedang di misi Astro — cek by pet_id bukan user_id
    sess = await astro_get_open_session()
    if sess and sess["status"] in ("traveling", "active", "returning"):
        pet_reg = await sb("GET", "astro_registrations", {"session_id": f"eq.{sess['id']}", "pet_id": f"eq.{pet_id}"})
        if pet_reg:
            await q.answer("🚀 Pet lagi di misi Astro Paws! Tunggu misi selesai ya~", show_alert=True); return
    await update_pet(pet_id, {
        "boarding_until": None,
        "last_decay":     now_wib().isoformat(),
        "last_fed":     now_wib().isoformat(),
        "hunger":         0,
        "happiness":      100,
        "health":         100,
        "is_dirty":       False,
        "poop_count":     0,
    })
    board_end = parse_dt(pet.get("boarding_until", ""))
    if board_end > now_wib():
        msg = f"✅ <b>{pet['name']}</b> dijemput lebih awal!\n<i>Sisa waktu tidak direfund.</i>"
    else:
        msg = f"✅ <b>{pet['name']}</b> sudah dijemput dari penitipan!"
    await q.edit_message_text(msg, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))

# ==================== EKSPEDISI ====================
async def show_expedition_menu(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("boarding_until") and parse_dt(pet.get("boarding_until","")) > now_wib():
        await q.answer("🏨 Pet lagi di penitipan!", show_alert=True); return
    if pet.get("expedition_until") and parse_dt(pet.get("expedition_until","")) > now_wib():
        await show_expedition_status(q, user, pet_id); return
    u = await get_user(user.id)
    koin = (u.get("koin") or 0)
    lines = [f"✈️ <b>Ekspedisi {pet['name']}</b>\n━━━━━━━━━━━━━━━\n"]
    buttons = []
    for key, dest in EXPEDITION_DESTINATIONS.items():
        lines.append(f"{dest['emoji']} <b>{dest['name']}</b> — {dest['cost']}🪙 | {dest['duration_hours']}jam\n  XP +{dest['xp_reward']} | Senang +{dest['happy_reward']}\n")
        buttons.append([InlineKeyboardButton(f"{dest['emoji']} {dest['name']} ({dest['cost']}🪙)", callback_data=f"expstart_{pet_id}_{key}")])
    lines.append(f"\n💼 Koinmu: <b>{koin} 🪙</b>")
    lines.append(f"\n⚠️ Saat ekspedisi, pet tidak bisa dimainkan!")
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")])
    await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def do_start_expedition(q, user, pet_id: int, dest_key: str, context):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    dest = EXPEDITION_DESTINATIONS.get(dest_key)
    if not dest:
        await q.answer("❌ Tujuan tidak valid!", show_alert=True); return
    if dest["cost"] > 0:
        ok = await spend_koin(user.id, dest["cost"], "ekspedisi")
        if not ok:
            await q.answer(f"❌ Koin tidak cukup! Butuh {dest['cost']} 🪙", show_alert=True); return
    exp_until = (now_wib() + timedelta(hours=dest["duration_hours"])).isoformat()
    await update_pet(pet_id, {"expedition_until": exp_until, "expedition_dest": dest_key})
    await q.edit_message_text(
        f"✈️ <b>{pet['name']}</b> berangkat ke {dest['emoji']} <b>{dest['name']}</b>!\n\n"
        f"⏰ Kembali dalam: <b>{dest['duration_hours']} jam</b>\n"
        f"🎁 Hadiah: XP +{dest['xp_reward']} | Senang +{dest['happy_reward']}\n\n"
        f"<i>Pet tidak bisa dimainkan saat ekspedisi~ ✈️</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✈️ Cek Ekspedisi", callback_data=f"expedition_check_{pet_id}")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id:
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        try:
            await context.bot.send_message(partner_id,
                f"✈️ {info['emoji']} <b>{pet['name']}</b> lagi ekspedisi ke {dest['emoji']} {dest['name']}!\nKembali dalam {dest['duration_hours']} jam.",
                parse_mode=ParseMode.HTML)
        except: pass

async def show_expedition_status(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet:
        await q.answer("❌ Pet tidak ditemukan!", show_alert=True); return
    exp_until = parse_dt(pet.get("expedition_until", ""))
    dest_key = pet.get("expedition_dest", "local")
    dest = EXPEDITION_DESTINATIONS.get(dest_key, {})
    if now_wib() >= exp_until:
        old_xp = (pet.get("xp") or 0)
        new_xp = old_xp + dest.get("xp_reward", 20)
        new_happy = min(100, (pet.get("happiness") or 80) + dest.get("happy_reward", 15))
        new_lv = calc_level(new_xp)
        await update_pet(pet_id, {"expedition_until": None, "expedition_dest": None, "xp": new_xp, "happiness": new_happy})
        lv_txt = f"\n✨ <b>LEVEL UP!</b> Lv.{new_lv}!" if new_lv > calc_level(old_xp) else ""
        await q.edit_message_text(
            f"🎉 <b>{pet['name']}</b> pulang dari ekspedisi {dest.get('emoji','')} {dest.get('name','')}!\n\n"
            f"🎁 XP +{dest.get('xp_reward',20)} | Senang +{dest.get('happy_reward',15)}{lv_txt}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))
    else:
        countdown = fmt_countdown(exp_until)
        await q.edit_message_text(
            f"✈️ <b>{pet['name']}</b> lagi ekspedisi ke {dest.get('emoji','')} <b>{dest.get('name','?')}</b>\n\n"
            f"⏰ Kembali dalam: <b>{countdown}</b>\n<i>Sabar ya! 🌍</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"expedition_check_{pet_id}")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
            ]))

# ==================== BATTLE PET ====================
async def show_battle_menu(q, user, pet_id: int):
    """Battle menu: buat battle code, lalu share via inline ke orang lain"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("boarding_until") and parse_dt(pet.get("boarding_until","")) > now_wib():
        await q.answer("🏨 Pet lagi di penitipan!", show_alert=True); return
    if pet.get("expedition_until") and parse_dt(pet.get("expedition_until","")) > now_wib():
        await q.answer("✈️ Pet lagi ekspedisi!", show_alert=True); return

    pet_lv = calc_level((pet.get("xp") or 0))
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    power = BATTLE_POWER.get(pet["pet_type"], 1.0)
    battle_wins = (pet.get("battle_wins") or 0)
    score_bonus = (pet.get("battle_score_bonus") or 0)
    ability_mult = 2.0 if "battle_2x" in (pet.get("special_ability") or "") else 1.0
    battle_score = int(pet_lv * 10 * power * ability_mult) + battle_wins + score_bonus  # base score + menang + steak bonus
    u = await get_user(user.id)
    koin = (u.get("koin") or 0)
    stake = max(10, min(200, koin // 10))

    # Buat battle code di DB
    battle_code = f"BTL{random.randint(10000,99999)}"
    res = await sb("POST", "battles", data={
        "code": battle_code,
        "challenger_pet_id": pet_id,
        "challenger_id": user.id,
        "stake": stake,
        "status": "waiting",
        "created_at": now_wib().isoformat(),
    })
    if not res:
        await q.answer("❌ Gagal buat battle, coba lagi!", show_alert=True); return

    bot_name = BOT_USERNAME.lstrip("@")
    share_text = f"battle {battle_code}"

    await q.edit_message_text(
        f"⚔️ <b>Battle Pet!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"🔵 Petmu: {info['emoji']} <b>{pet['name']}</b> Lv.{pet_lv}\n"
        f"⚡ Battle Score: <b>{battle_score}</b>\n"
        f"🏆 Total Menang: <b>{battle_wins}x</b>\n"
        f"💰 Taruhan: <b>{stake} 🪙</b>\n\n"
        f"🎯 Share tombol di bawah ke chat/grup!\n"
        f"Lawan klik link → pilih pet → battle otomatis!\n\n"
        f"📌 Kode: <code>{battle_code}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Share Battle Challenge!", switch_inline_query=share_text)],
            [InlineKeyboardButton("🔙 Batal", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def do_battle(q, user, encoded: str, context):
    parts = encoded.split("_")
    if len(parts) < 3:
        await q.answer("❌ Data battle tidak valid!", show_alert=True); return
    pet_id = int(parts[0])
    opp_id = int(parts[1])
    stake  = int(parts[2])
    pet = await get_pet_by_id(pet_id)
    opp = await get_pet_by_id(opp_id)
    if not pet or not opp:
        await q.answer("❌ Pet tidak ditemukan!", show_alert=True); return
    if pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id:
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    u = await get_user(user.id)
    if (u.get("koin") or 0) < stake:
        await q.answer("❌ Koin tidak cukup untuk taruhan!", show_alert=True); return
    pet_lv   = calc_level((pet.get("xp") or 0))
    opp_lv   = calc_level((opp.get("xp") or 0))
    pet_score = pet_lv * 10 * BATTLE_POWER.get(pet["pet_type"], 1.0) * random.uniform(0.8, 1.2)
    opp_score = opp_lv * 10 * BATTLE_POWER.get(opp["pet_type"], 1.0) * random.uniform(0.8, 1.2)
    pet_info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    opp_info = PETS.get(opp["pet_type"], {"emoji": "🐾"})
    opp_owner = opp.get("owner1_id") or opp.get("owner2_id")
    if pet_score > opp_score:
        await add_koin(user.id, stake, "battle_menang")
        new_wins = (pet.get("battle_wins") or 0) + 1
        await update_pet(pet_id, {"battle_wins": new_wins})
        if opp_owner:
            await spend_koin(opp_owner, stake, "battle_kalah")
            try:
                await context.bot.send_message(opp_owner,
                    f"⚔️ {opp_info['emoji']} <b>{opp['name']}</b> kalah battle!\nLawan: {pet_info['emoji']} {pet['name']}\n💸 -{stake} 🪙",
                    parse_mode=ParseMode.HTML)
            except: pass
        await update_pet(pet_id, {"xp": (pet.get("xp") or 0) + 20})
        result_msg = (f"🏆 <b>{pet['name']}</b> MENANG!\n\n"
                      f"{pet_info['emoji']} Skor: {pet_score:.0f} vs {opp_info['emoji']} {opp_score:.0f}\n\n"
                      f"💰 +{stake} 🪙 direbut dari lawan!\n"
                      f"🏆 Total menang: <b>{new_wins}x</b>\n<i>Lawan keok! 🥊</i>")
    else:
        await spend_koin(user.id, stake, "battle_kalah")
        new_wins_opp = (opp.get("battle_wins") or 0) + 1
        await update_pet(opp_id, {"battle_wins": new_wins_opp})
        if opp_owner:
            await add_koin(opp_owner, stake, "battle_menang")
            try:
                await context.bot.send_message(opp_owner,
                    f"⚔️ {opp_info['emoji']} <b>{opp['name']}</b> menang battle!\n💰 +{stake} 🪙\n🏆 Total menang: <b>{new_wins_opp}x</b>",
                    parse_mode=ParseMode.HTML)
            except: pass
        result_msg = (f"💀 <b>{pet['name']}</b> KALAH!\n\n"
                      f"{pet_info['emoji']} Skor: {pet_score:.0f} vs {opp_info['emoji']} {opp_score:.0f}\n\n"
                      f"💸 -{stake} 🪙 diambil lawan\n<i>Latih lagi petmu! 💪</i>")
    await q.edit_message_text(result_msg, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Battle Lagi", callback_data=f"battle_menu_{pet_id}")],
            [InlineKeyboardButton("🐾 Lihat Pet",   callback_data=f"select_pet_{pet_id}")],
        ]))

# ==================== PERNIKAHAN PET ====================
async def show_marriage_menu(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp") or 0)
    if lv < 10:
        await q.answer(f"❌ Pet harus Level 10+ untuk menikah! (Sekarang Lv.{lv})", show_alert=True); return
    if pet.get("is_married"):
        await q.answer("💍 Pet ini sudah menikah!", show_alert=True); return
    MARRIAGE_COST = 500
    u = await get_user(user.id)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"💍 <b>Nikahkan Pet</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{pet['name']}</b> (Lv.{lv})\n\n"
        f"⚠️ Setelah menikah, kedua pet akan <b>tinggal bersama</b> tapi tetap bisa kamu rawat!\n"
        f"💰 Biaya: <b>{MARRIAGE_COST} 🪙</b>\n💼 Koinmu: <b>{u.get('koin',0)} 🪙</b>\n\nYakin?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💍 Ya, Nikahkan!", callback_data=f"marriage_confirm_{pet_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def do_marriage(q, user, pet_id: int, context):
    """Langkah 1: User memilih untuk menikahkan petnya — sekarang harus pilih pet pasangan"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp") or 0)
    if lv < 10:
        await q.answer("❌ Level belum cukup!", show_alert=True); return
    if pet.get("is_married"):
        await q.answer("💍 Sudah menikah!", show_alert=True); return

    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    MARRIAGE_COST = 500
    bot_name = BOT_USERNAME.lstrip("@")

    # Buat marriage proposal code
    marry_code = f"MRY{random.randint(10000,99999)}"
    res = await sb("POST", "marriage_proposals", data={
        "code": marry_code,
        "pet1_id": pet_id,
        "pet2_id": 0,  # belum dipilih
        "owner1_pet1": pet.get("owner1_id"),
        "owner2_pet1": pet.get("owner2_id"),
        "approved_by": json.dumps([user.id]),
        "status": "pending",
        "created_at": now_wib().isoformat(),
    })
    if not res:
        await q.answer("❌ Gagal buat proposal, coba lagi!", show_alert=True); return

    marry_link = f"https://t.me/{bot_name}?start=MARRY_{marry_code}"

    await q.edit_message_text(
        f"💍 <b>Proposal Pernikahan</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{pet['name']}</b> mau menikah!\n\n"
        f"⚠️ Pernikahan butuh persetujuan <b>semua owner</b>:\n"
        f"• Owner 1 & 2 petmu (kamu sudah setuju ✅)\n"
        f"• Owner 1 & 2 pet pasangan\n\n"
        f"📌 Share link ini ke pemilik pet yang mau dinikahkan:\n"
        f"<code>{marry_link}</code>\n\n"
        f"💰 Biaya nikah: <b>{MARRIAGE_COST} 🪙</b> (dibayar saat semua setuju)\n"
        f"<i>Setelah menikah, kedua pet bisa dilihat tinggal bersama~</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share ke Pemilik Pasangan", switch_inline_query=f"marry {marry_code}")],
            [InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def handle_marriage_link(update: Update, context: ContextTypes.DEFAULT_TYPE, marry_code: str):
    """User klik link marry → pilih pet mereka untuk dinikahkan"""
    user = update.effective_user
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    res = await sb("GET", "marriage_proposals", {"code": f"eq.{marry_code}", "status": "eq.pending", "select": "id,code,status,pet1_id,pet2_id,owner1_pet1,owner2_pet1,owner1_pet2,owner2_pet2,approved_by"})
    if not res:
        await update.message.reply_text("❌ Proposal tidak ditemukan atau sudah selesai!")
        return
    proposal = res[0]

    # Cek apakah user ini owner dari pet1
    is_owner_pet1 = (user.id in [proposal.get("owner1_pet1"), proposal.get("owner2_pet1")])

    # Ambil pet milik user yang eligible
    pets = await get_user_pets(user.id)
    eligible = [p for p in pets if not p.get("is_missing") and not p.get("is_married")
                and p["id"] != proposal["pet1_id"]
                and calc_level((p.get("xp") or 0)) >= 10]

    if not eligible and not is_owner_pet1:
        await update.message.reply_text(
            "❌ Kamu tidak punya pet yang eligible untuk menikah!\nPet harus Level 10+ dan belum menikah~"
        )
        return

    # Kalau ini owner pet1 yang approve saja (bukan pilih pasangan)
    approved_by = json.loads(proposal.get("approved_by") or "[]")
    if is_owner_pet1:
        if user.id in approved_by:
            await update.message.reply_text("✅ Kamu sudah menyetujui proposal ini!")
        else:
            approved_by.append(user.id)
            await sb("PATCH", "marriage_proposals", {"code": f"eq.{marry_code}"},
                     {"approved_by": json.dumps(approved_by)})
            await update.message.reply_text("✅ Kamu setuju dengan pernikahan ini!")
            await _check_marriage_complete(context, marry_code, proposal)
        return

    # Pilih pet pasangan
    if len(eligible) == 1:
        await _set_marriage_pet2(update, context, marry_code, proposal, user, eligible[0])
    else:
        context.user_data["pending_marry_code"] = marry_code
        buttons = []
        for pet in eligible:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            lv = calc_level(pet.get("xp") or 0)
            buttons.append([InlineKeyboardButton(
                f"{info['emoji']} {pet['name']} Lv.{lv}",
                callback_data=f"marry_choose_{pet['id']}_{marry_code}"
            )])
        pet1 = await get_pet_by_id(proposal["pet1_id"])
        p1_info = PETS.get(pet1.get("pet_type","cat"), {"emoji": "🐾"}) if pet1 else {"emoji": "🐾"}
        await update.message.reply_text(
            f"💍 <b>Proposal Pernikahan</b>\n\n"
            f"Pet yang mau dinikahkan: {p1_info['emoji']} <b>{pet1['name'] if pet1 else '?'}</b>\n\n"
            f"Pilih pet kamu sebagai pasangan:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def _set_marriage_pet2(update_or_q, context, marry_code: str, proposal: dict, user, my_pet: dict):
    is_msg = hasattr(update_or_q, 'message')
    reply = update_or_q.message.reply_text if is_msg else update_or_q.edit_message_text

    approved_by = json.loads(proposal.get("approved_by") or "[]")
    if user.id not in approved_by:
        approved_by.append(user.id)

    await sb("PATCH", "marriage_proposals", {"code": f"eq.{marry_code}"}, {
        "pet2_id": my_pet["id"],
        "owner1_pet2": my_pet.get("owner1_id"),
        "owner2_pet2": my_pet.get("owner2_id"),
        "approved_by": json.dumps(approved_by),
    })

    pet1 = await get_pet_by_id(proposal["pet1_id"])
    p1_info = PETS.get(pet1.get("pet_type","cat"), {"emoji": "🐾"}) if pet1 else {"emoji": "🐾"}
    my_info = PETS.get(my_pet["pet_type"], {"emoji": "🐾"})

    # Hitung berapa yang perlu approve lagi
    needed_owners = set(filter(None, [
        proposal.get("owner1_pet1"), proposal.get("owner2_pet1"),
        my_pet.get("owner1_id"), my_pet.get("owner2_id")
    ]))
    remaining = [uid for uid in needed_owners if uid not in approved_by]

    await reply(
        f"💍 Kamu memilih {my_info['emoji']} <b>{my_pet['name']}</b> sebagai pasangan "
        f"{p1_info['emoji']} {pet1['name'] if pet1 else '?'}!\n\n"
        f"✅ Sudah setuju: {len(approved_by)} orang\n"
        f"⏳ Masih perlu persetujuan: {len(remaining)} orang lagi\n\n"
        f"<i>Semua owner harus setuju sebelum nikah~</i>",
        parse_mode=ParseMode.HTML
    )

    # Notif ke remaining owners
    bot_name = BOT_USERNAME.lstrip("@")
    marry_link = f"https://t.me/{bot_name}?start=MARRY_{marry_code}"
    for uid in remaining:
        try:
            await context.bot.send_message(
                uid,
                f"💍 Ada proposal pernikahan menunggu persetujuanmu!\n\n"
                f"{p1_info['emoji']} <b>{pet1['name'] if pet1 else '?'}</b> × {my_info['emoji']} <b>{my_pet['name']}</b>\n\n"
                f"Klik link untuk setuju:\n{marry_link}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💍 Lihat & Setuju", url=marry_link)]])
            )
        except: pass

    await _check_marriage_complete(context, marry_code, proposal)

async def _check_marriage_complete(context, marry_code: str, proposal: dict):
    """Cek kalau semua 4 owner sudah setuju → execute marriage"""
    fresh = await sb("GET", "marriage_proposals", {"code": f"eq.{marry_code}", "select": "id,code,status,pet1_id,pet2_id,owner1_pet1,owner2_pet1,owner1_pet2,owner2_pet2,approved_by"})
    if not fresh: return
    proposal = fresh[0]
    if proposal["status"] != "pending": return

    approved_by = json.loads(proposal.get("approved_by") or "[]")
    needed = set(filter(None, [
        proposal.get("owner1_pet1"), proposal.get("owner2_pet1"),
        proposal.get("owner1_pet2"), proposal.get("owner2_pet2"),
    ]))
    if not needed or not proposal.get("pet2_id") or proposal["pet2_id"] == 0:
        return  # pet2 belum dipilih
    if not all(uid in approved_by for uid in needed):
        return  # belum semua setuju

    # SEMUA SETUJU! Execute marriage
    MARRIAGE_COST = 500
    # Ambil biaya dari semua owner (share rata)
    pet1 = await get_pet_by_id(proposal["pet1_id"])
    pet2 = await get_pet_by_id(proposal["pet2_id"])
    if not pet1 or not pet2: return

    # Bayar dari owner1 pet1 saja (simplify)
    payer = proposal.get("owner1_pet1")
    if payer:
        await spend_koin(payer, MARRIAGE_COST, "pernikahan")

    # Set both pets married — owner TETAP, hanya set is_married + partner_pet_id
    await update_pet(proposal["pet1_id"], {
        "is_married": True,
        "married_at": now_wib().isoformat(),
        "married_to_pet_id": proposal["pet2_id"],
    })
    await update_pet(proposal["pet2_id"], {
        "is_married": True,
        "married_at": now_wib().isoformat(),
        "married_to_pet_id": proposal["pet1_id"],
    })

    await sb("PATCH", "marriage_proposals", {"code": f"eq.{marry_code}"}, {"status": "approved"})

    p1_info = PETS.get(pet1["pet_type"], {"emoji": "🐾"})
    p2_info = PETS.get(pet2["pet_type"], {"emoji": "🐾"})

    msg = (f"🎊 <b>Pernikahan berhasil!</b>\n\n"
           f"{p1_info['emoji']} <b>{pet1['name']}</b> × {p2_info['emoji']} <b>{pet2['name']}</b>\n\n"
           f"Keduanya kini tinggal bersama~ 🌸\n"
           f"Rawat terus pet kamu ya!")

    for uid in filter(None, [proposal.get("owner1_pet1"), proposal.get("owner2_pet1"),
                              proposal.get("owner1_pet2"), proposal.get("owner2_pet2")]):
        try:
            await context.bot.send_message(uid, msg, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Adopt Baru", callback_data="carpet_shop")]]))
        except: pass


# ==================== HEWAN TERNAK ====================
async def show_livestock_menu(q, user):
    u = await get_user(user.id)
    if not u:
        await q.edit_message_text("❌ Gagal memuat data. Coba lagi!")
        return
    koin = (u.get("koin") or 0)
    user_livestocks = await sb("GET", "livestocks", {"owner_id": f"eq.{user.id}", "order": "created_at.desc"}) or []
    lines = ["🐄 <b>Hewan Ternak</b>\n━━━━━━━━━━━━━━━\n"]
    buttons = []
    if user_livestocks:
        lines.append("<b>Ternak Kamu:</b>")
        for lt_item in user_livestocks:
            lt = LIVESTOCK.get(lt_item["lt_type"], {})
            last_collect = parse_dt(lt_item.get("last_collect", ""))
            hours_since = (now_wib() - last_collect).total_seconds() / 3600
            ready = hours_since >= lt.get("interval_hours", 8)
            status = "✅ Siap dipanen!" if ready else f"⏰ {fmt_countdown(last_collect + timedelta(hours=lt.get('interval_hours',8)))}"
            lines.append(f"{lt.get('emoji','🐄')} <b>{lt_item['name']}</b> — {status}")
            buttons.append([InlineKeyboardButton(
                f"{'🎁 Panen' if ready else '📋 Lihat'} {lt.get('emoji','')} {lt_item['name']}",
                callback_data=f"livestock_view_{lt_item['id']}"
            )])
    else:
        lines.append("<i>Kamu belum punya hewan ternak~</i>\n")
    # Info katalog ternak (tanpa tombol beli)
    lines.append("\n<b>📋 Katalog Hewan Ternak:</b>")
    for key, lt in LIVESTOCK.items():
        lines.append(f"{lt['emoji']} <b>{lt['name']}</b> — {lt['price']}🪙 → {lt['product_emoji']} tiap {lt['interval_hours']}jam (jual {lt['sell_price']}🪙/item)")
    # Info kandang
    barn_slots = (u.get("barn_slots") or 1)
    used_slots = len(user_livestocks)
    lines.append(f"\n🏚️ <b>Kandang:</b> {used_slots}/{barn_slots} slot")
    if used_slots >= barn_slots:
        lines.append(f"<i>Kandang penuh! Upgrade untuk beli ternak baru.</i>")
        buttons.append([InlineKeyboardButton(f"🏚️ Upgrade Kandang (+1 slot = {BARN_UPGRADE_COST}🪙)", callback_data="barn_upgrade")])
    lines.append(f"\n💼 Koinmu: <b>{koin} 🪙</b>")
    lines.append(f"\n🛒 <i>Beli hewan ternak melalui Mini App di bawah~</i>")
    buttons.append([InlineKeyboardButton("🛒 Beli Ternak di Mini App", url=MINI_APP_URL)])
    buttons.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
    await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def do_barn_upgrade(q, user):
    """Upgrade kandang +1 slot"""
    u = await get_user(user.id)
    current = (u.get("barn_slots") or 1)
    ok = await spend_koin(user.id, BARN_UPGRADE_COST, "upgrade_kandang")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {BARN_UPGRADE_COST} 🪙", show_alert=True); return
    await update_user(user.id, {"barn_slots": current + 1})
    await q.edit_message_text(
        f"🏚️ <b>Kandang di-upgrade!</b>\n\n"
        f"Slot sekarang: <b>{current + 1}</b>\n"
        f"💰 -{BARN_UPGRADE_COST} 🪙\n\n"
        f"<i>Sekarang bisa beli ternak lebih banyak~</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐄 Lihat Ternak", callback_data="livestock_menu")]]))

async def show_livestock_detail(q, user, lt_id: int):
    res = await sb("GET", "livestocks", {"id": f"eq.{lt_id}", "owner_id": f"eq.{user.id}"})
    if not res:
        await q.answer("❌ Ternak tidak ditemukan!", show_alert=True); return
    lt_item = res[0]
    lt = LIVESTOCK.get(lt_item["lt_type"], {})
    last_collect = parse_dt(lt_item.get("last_collect", ""))
    hours_since = (now_wib() - last_collect).total_seconds() / 3600
    ready = hours_since >= lt.get("interval_hours", 8)
    items_ready = min(3, int(hours_since // lt.get("interval_hours", 8))) if ready else 0
    status = f"✅ Siap dipanen! ({items_ready}x {lt.get('product_emoji','')})" if ready else f"⏰ {fmt_countdown(last_collect + timedelta(hours=lt.get('interval_hours',8)))}"
    buttons = []
    if ready:
        earn_full = items_ready * lt.get('sell_price', 0)
        buttons.append([
            InlineKeyboardButton(f"🌾 Jual Hasil ({items_ready}x hasil → {earn_full}🪙)", callback_data=f"livestock_sell_{lt_id}"),
        ])
        can_save = lt.get("can_feed_pet") or lt.get("product_key")
        save_label = "🐾 Simpan ke Inventori (kasih ke pet)" if lt.get("can_feed_pet") else "🎒 Simpan ke Inventori (bahan Dapur MBG)"
        buttons.append([InlineKeyboardButton(save_label, callback_data=f"livestock_save_{lt_id}")])
    # Tombol jual ternak itu sendiri (selalu ada)
    sell_animal_price = max(1, int(lt.get("price", 0) * 0.20))
    buttons.append([InlineKeyboardButton(f"🏷️ Jual Ternak Ini (dapet {sell_animal_price}🪙 + 2🍪, slot berkurang)", callback_data=f"livestock_sell_animal_{lt_id}")])
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="livestock_menu")])
    sell_or_keep = "\n💡 Hasil bisa dijual atau disimpan!" if (lt.get("can_feed_pet") or lt.get("product_key")) else ""
    sell_animal_price = max(1, int(lt.get("price", 0) * 0.20))
    await q.edit_message_text(
        f"{lt.get('emoji','🐄')} <b>{lt_item['name']}</b>\n━━━━━━━━━━━━━━━\n"
        f"Jenis: {lt.get('name','?')}\n"
        f"Produk: {lt.get('product_emoji','')} {lt.get('product_name','?')} tiap {lt.get('interval_hours','?')} jam\n"
        f"Harga jual hasil: <b>{lt.get('sell_price','?')} 🪙</b>/item{sell_or_keep}\n"
        f"Jual hewan: <b>{sell_animal_price} 🪙 + 2 snack</b> (slot berkurang)\n\n"
        f"Status: <b>{status}</b>",
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def _get_livestock_ready(lt_id: int, user_id: int):
    """Helper: ambil lt data dan cek apakah ready"""
    res = await sb("GET", "livestocks", {"id": f"eq.{lt_id}", "owner_id": f"eq.{user_id}"})
    if not res: return None, None, 0
    lt_item = res[0]
    lt = LIVESTOCK.get(lt_item["lt_type"], {})
    last_collect = parse_dt(lt_item.get("last_collect", ""))
    hours_since = (now_wib() - last_collect).total_seconds() / 3600
    items = min(3, int(hours_since // lt.get("interval_hours", 8))) if hours_since >= lt.get("interval_hours", 8) else 0
    return lt_item, lt, items

async def do_collect_livestock(q, user, lt_id: int):
    """Alias ke sell (backward compat)"""
    await do_livestock_sell(q, user, lt_id)

async def do_livestock_sell(q, user, lt_id: int):
    """Jual hasil panen ke bot → dapat koin (20%). Ternak TIDAK dihapus, slot TIDAK berkurang."""
    lt_item, lt, items = await _get_livestock_ready(lt_id, user.id)
    if lt_item is None:
        await q.answer("❌ Ternak tidak ditemukan!", show_alert=True); return
    if items == 0:
        countdown = fmt_countdown(parse_dt(lt_item.get("last_collect","")) + timedelta(hours=lt.get("interval_hours",8)))
        await q.answer(f"⏰ Belum waktunya panen! Tunggu {countdown}~", show_alert=True); return

    earn = items * lt.get("sell_price", 30)

    await add_koin(user.id, earn, "jual_ternak")
    asyncio.create_task(task_inc(user.id, "harvest_10"))
    # Update last_collect saja — ternak TIDAK dihapus, slot TIDAK berkurang
    await sb("PATCH", "livestocks", {"id": f"eq.{lt_id}"}, {"last_collect": now_wib().isoformat()})

    u = await get_user(user.id)
    await q.edit_message_text(
        f"💰 <b>Hasil panen dijual!</b>\n\n{lt.get('emoji','🐄')} <b>{lt_item['name']}</b>\n"
        f"{lt.get('product_emoji','')} {lt.get('product_name','?')}: <b>x{items}</b> → <b>{earn} 🪙</b>\n\n"
        f"💼 Total koin: <b>{u.get('koin',0):,} 🪙</b>\n"
        f"<i>Ternakmu masih ada — panen lagi nanti!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐄 Lihat Ternak", callback_data="livestock_menu")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ]))

async def do_livestock_save(q, user, lt_id: int):
    """Simpan hasil panen ke inventori (bukan dijual).
    - Ternak can_feed_pet → simpan pakai food_key (bisa dikasih ke pet)
    - Lainnya → simpan pakai product_key (bahan Dapur MBG)"""
    lt_item, lt, items = await _get_livestock_ready(lt_id, user.id)
    if lt_item is None:
        await q.answer("❌ Ternak tidak ditemukan!", show_alert=True); return
    if items == 0:
        countdown = fmt_countdown(parse_dt(lt_item.get("last_collect","")) + timedelta(hours=lt.get("interval_hours",8)))
        await q.answer(f"⏰ Belum waktunya panen! Tunggu {countdown}~", show_alert=True); return

    # Tentukan inventory key
    inv_key = lt.get("food_key") if lt.get("can_feed_pet") else lt.get("product_key")
    if not inv_key:
        # Tidak ada tempat menyimpan (mis. wol) → arahkan untuk jual saja
        await q.answer("❌ Hasil ini tidak bisa disimpan, jual saja ya~", show_alert=True); return

    # Tambahkan ke inventori
    inv = await get_inv(user.id)
    inv[inv_key] = (inv.get(inv_key) or 0) + items
    await set_inv(user.id, inv)
    # Update last_collect — ternak TIDAK dihapus
    await sb("PATCH", "livestocks", {"id": f"eq.{lt_id}"}, {"last_collect": now_wib().isoformat()})

    usage_txt = "bisa dikasih ke pet 🐾" if lt.get("can_feed_pet") else "bahan Dapur MBG 🍳"
    await q.edit_message_text(
        f"🎒 <b>Hasil panen disimpan!</b>\n\n{lt.get('emoji','🐄')} <b>{lt_item['name']}</b>\n"
        f"{lt.get('product_emoji','')} {lt.get('product_name','?')}: <b>+{items}</b> masuk inventori\n\n"
        f"<i>{usage_txt.capitalize()}~</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎒 Buka Inventori", callback_data="inventory")],
            [InlineKeyboardButton("🐄 Lihat Ternak", callback_data="livestock_menu")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ]))

async def do_livestock_sell_animal(q, user, lt_id: int):
    """Jual hewan ternak itu sendiri — dapat 20% harga beli + 2 snack, slot berkurang"""
    res = await sb("GET", "livestocks", {"id": f"eq.{lt_id}", "owner_id": f"eq.{user.id}"})
    if not res:
        await q.answer("❌ Ternak tidak ditemukan!", show_alert=True); return
    lt_item = res[0]
    lt = LIVESTOCK.get(lt_item["lt_type"], {})
    sell_price = max(1, int(lt.get("price", 0) * 0.20))

    # Konfirmasi dulu
    await q.edit_message_text(
        f"🏷️ <b>Jual Ternak?</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{lt.get('emoji','🐄')} <b>{lt_item['name']}</b> ({lt.get('name','?')})\n\n"
        f"💰 Kamu dapat: <b>{sell_price} 🪙</b> + 🍪 <b>2 Snack</b>\n\n"
        f"<i>Ternak akan dihapus permanen!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Jual Ternak!", callback_data=f"livestock_sell_animal_confirm_{lt_id}"),
             InlineKeyboardButton("❌ Batal", callback_data=f"livestock_view_{lt_id}")],
        ])
    )

async def do_livestock_sell_animal_confirm(q, user, lt_id: int):
    """Eksekusi jual hewan ternak"""
    res = await sb("GET", "livestocks", {"id": f"eq.{lt_id}", "owner_id": f"eq.{user.id}"})
    if not res:
        await q.answer("❌ Ternak tidak ditemukan!", show_alert=True); return
    lt_item = res[0]
    lt = LIVESTOCK.get(lt_item["lt_type"], {})
    sell_price = max(1, int(lt.get("price", 0) * 0.20))

    # Beri koin
    await add_koin(user.id, sell_price, "jual_hewan")

    # Bonus 2 snack
    _cdel(_user_cache, user.id)
    inv = await get_inv(user.id)
    inv["snack"] = (inv.get("snack") or 0) + 2
    await set_inv(user.id, inv)

    # Hapus ternak dari DB — slot otomatis berkurang karena count ternak berkurang
    # barn_slots adalah KAPASITAS MAX, jangan dikurangi!
    await sb("DELETE", "livestocks", {"id": f"eq.{lt_id}", "owner_id": f"eq.{user.id}"})

    await q.edit_message_text(
        f"✅ <b>Ternak berhasil dijual!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{lt.get('emoji','🐄')} <b>{lt_item['name']}</b> terjual\n"
        f"💰 +<b>{sell_price} 🪙</b> | 🍪 +<b>2 Snack</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐄 Lihat Ternak", callback_data="livestock_menu")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )
    """Simpan hasil panen ke inventori → bisa dikasih ke pet"""
    lt_item, lt, items = await _get_livestock_ready(lt_id, user.id)
    if lt_item is None:
        await q.answer("❌ Ternak tidak ditemukan!", show_alert=True); return
    if items == 0:
        countdown = fmt_countdown(parse_dt(lt_item.get("last_collect","")) + timedelta(hours=lt.get("interval_hours",8)))
        await q.answer(f"⏰ Belum waktunya panen! Tunggu {countdown}~", show_alert=True); return
    food_key = lt.get("food_key") or lt.get("product_key")
    if not food_key:
        await q.answer("❌ Tidak ada kunci inventori untuk hasil ini!", show_alert=True); return
    inv = await get_inv(user.id)
    inv[food_key] = (inv.get(food_key) or 0) + items
    await set_inv(user.id, inv)
    await sb("PATCH", "livestocks", {"id": f"eq.{lt_id}"}, {"last_collect": now_wib().isoformat()})
    food_info = LIVESTOCK_FOOD.get(food_key, {})
    await q.edit_message_text(
        f"🎒 Disimpan ke inventori!\n\n{lt.get('emoji','🐄')} <b>{lt_item['name']}</b>\n"
        f"{lt.get('product_emoji','')} <b>{lt.get('product_name','?')} x{items}</b> tersimpan!\n\n"
        f"Bisa dikasih ke petmu langsung dari menu 🍽️ Kasih Makan~\n"
        f"<i>Restore Hunger: {food_info.get('hunger',0)} | XP: {food_info.get('xp',0)}</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐾 Kasih ke Pet Sekarang", callback_data="my_pet")],
            [InlineKeyboardButton("🐄 Lihat Ternak", callback_data="livestock_menu")],
        ]))

# ==================== BROADCAST ====================
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: reply pesan lalu /broadcast, atau /broadcast teks"""
    if update.effective_user.id not in ADMIN_IDS:
        return

    replied = update.message.reply_to_message

    if replied:
        # Mode reply: copy pesan asli ke semua user (formatting, foto, video, sticker preserved)
        await update.message.reply_text(
            "📢 <b>Broadcast dimulai (mode reply)...</b>\n"
            "<i>Pesan dikirim persis seperti aslinya~</i>",
            parse_mode=ParseMode.HTML
        )
        asyncio.create_task(_do_broadcast_copy(
            context,
            from_chat_id=replied.chat_id,
            message_id=replied.message_id,
            sender_id=update.effective_user.id
        ))
    elif context.args:
        # Mode teks biasa
        message = " ".join(context.args)
        await update.message.reply_text(
            f"📢 <b>Broadcast dimulai...</b>\nPesan: <i>{safe_html(message)}</i>",
            parse_mode=ParseMode.HTML
        )
        asyncio.create_task(_do_broadcast_text(context, message, update.effective_user.id))
    else:
        await update.message.reply_text(
            "❌ <b>Cara pakai:</b>\n"
            "• Reply ke pesan lalu ketik <code>/broadcast</code> — kirim pesan itu ke semua user (formatting asli)\n"
            "• <code>/broadcast teks pesan</code> — kirim teks biasa",
            parse_mode=ParseMode.HTML
        )

async def _fetch_all_user_ids() -> list:
    """Ambil semua user_id dari DB dengan pagination"""
    all_users = []
    offset = 0
    while True:
        res = await sb("GET", "users", {
            "select": "user_id", "limit": "1000",
            "offset": str(offset), "order": "created_at.asc"
        }) or []
        if not res: break
        all_users.extend(res)
        if len(res) < 1000: break
        offset += 1000
    return all_users

async def _broadcast_progress(context, sender_id: int, progress_msg_id: int, success: int, fail: int, total: int, done: bool = False):
    """Edit pesan progress broadcast"""
    pct = int((success + fail) / total * 100) if total else 0
    filled = pct // 10
    bar = "█" * filled + "░" * (10 - filled)
    status = "✅ <b>Selesai!</b>" if done else "📢 <b>Sedang broadcast...</b>"
    text = (
        f"{status}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"[{bar}] {pct}%\n\n"
        f"👥 Total: <b>{total}</b>\n"
        f"📤 Terkirim: <b>{success}</b>\n"
        f"❌ Gagal: <b>{fail}</b>\n"
        f"⏳ Sisa: <b>{total - success - fail}</b>"
    )
    try:
        await context.bot.edit_message_text(
            chat_id=sender_id, message_id=progress_msg_id,
            text=text, parse_mode=ParseMode.HTML
        )
    except: pass

async def cmd_broadcastforward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: reply pesan lalu /broadcastforward, forward ke semua user (ada 'Forwarded from')"""
    if update.effective_user.id not in ADMIN_IDS:
        return

    replied = update.message.reply_to_message
    if not replied:
        await update.message.reply_text(
            "❌ <b>Cara pakai:</b>\nReply ke pesan lalu ketik <code>/broadcastforward</code>\n"
            "<i>Pesan akan diforward ke semua user (ada label 'Forwarded from')</i>",
            parse_mode=ParseMode.HTML
        )
        return

    await update.message.reply_text(
        "📢 <b>Broadcast Forward dimulai...</b>\n"
        "<i>Pesan akan terlihat sebagai 'Forwarded from'~</i>",
        parse_mode=ParseMode.HTML
    )
    asyncio.create_task(_do_broadcast_forward(
        context,
        from_chat_id=replied.chat_id,
        message_id=replied.message_id,
        sender_id=update.effective_user.id
    ))

async def _do_broadcast_forward(context: ContextTypes.DEFAULT_TYPE, from_chat_id: int, message_id: int, sender_id: int):
    """Broadcast dengan forward_message — ada label 'Forwarded from'"""
    try:
        all_users = await _fetch_all_user_ids()
        total = len(all_users)
        success = fail = 0

        prog_msg = await context.bot.send_message(
            sender_id,
            f"📢 <b>Sedang broadcast forward...</b>\n[░░░░░░░░░░] 0%\n\n👥 Total: <b>{total}</b>\n📤 Terkirim: <b>0</b>\n❌ Gagal: <b>0</b>\n⏳ Sisa: <b>{total}</b>",
            parse_mode=ParseMode.HTML
        )
        prog_id = prog_msg.message_id

        for i, u in enumerate(all_users):
            uid = u.get("user_id")
            if not uid: continue
            try:
                await context.bot.forward_message(chat_id=uid, from_chat_id=from_chat_id, message_id=message_id)
                success += 1
                await asyncio.sleep(0.05)
            except:
                fail += 1
                await asyncio.sleep(0.02)
            if (i + 1) % 500 == 0:
                await _broadcast_progress(context, sender_id, prog_id, success, fail, total)

        await _broadcast_progress(context, sender_id, prog_id, success, fail, total, done=True)
        logger.info(f"Broadcast (forward) selesai: {success} sukses, {fail} gagal")
    except Exception as e:
        logger.error(f"Broadcast forward error: {e}")

async def _do_broadcast_copy(context: ContextTypes.DEFAULT_TYPE, from_chat_id: int, message_id: int, sender_id: int):
    """Broadcast dengan copy_message — formatting, foto, video, sticker semua preserved"""
    try:
        all_users = await _fetch_all_user_ids()
        total = len(all_users)
        success = fail = 0

        # Kirim pesan progress awal
        prog_msg = await context.bot.send_message(
            sender_id,
            f"📢 <b>Sedang broadcast...</b>\n[░░░░░░░░░░] 0%\n\n👥 Total: <b>{total}</b>\n📤 Terkirim: <b>0</b>\n❌ Gagal: <b>0</b>\n⏳ Sisa: <b>{total}</b>",
            parse_mode=ParseMode.HTML
        )
        prog_id = prog_msg.message_id

        for i, u in enumerate(all_users):
            uid = u.get("user_id")
            if not uid: continue
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=from_chat_id, message_id=message_id)
                success += 1
                await asyncio.sleep(0.05)
            except:
                fail += 1
                await asyncio.sleep(0.02)
            # Update progress tiap 500 user
            if (i + 1) % 500 == 0:
                await _broadcast_progress(context, sender_id, prog_id, success, fail, total)

        await _broadcast_progress(context, sender_id, prog_id, success, fail, total, done=True)
        logger.info(f"Broadcast (copy) selesai: {success} sukses, {fail} gagal")
    except Exception as e:
        logger.error(f"Broadcast copy error: {e}")

async def _do_broadcast_text(context: ContextTypes.DEFAULT_TYPE, message: str, sender_id: int):
    """Broadcast teks biasa dengan header admin"""
    try:
        all_users = await _fetch_all_user_ids()
        total = len(all_users)
        success = fail = 0

        # Kirim pesan progress awal
        prog_msg = await context.bot.send_message(
            sender_id,
            f"📢 <b>Sedang broadcast...</b>\n[░░░░░░░░░░] 0%\n\n👥 Total: <b>{total}</b>\n📤 Terkirim: <b>0</b>\n❌ Gagal: <b>0</b>\n⏳ Sisa: <b>{total}</b>",
            parse_mode=ParseMode.HTML
        )
        prog_id = prog_msg.message_id

        for i, u in enumerate(all_users):
            uid = u.get("user_id")
            if not uid: continue
            try:
                await context.bot.send_message(uid, message, parse_mode=ParseMode.HTML)
                success += 1
                await asyncio.sleep(0.05)
            except:
                fail += 1
                await asyncio.sleep(0.02)
            # Update progress tiap 500 user
            if (i + 1) % 500 == 0:
                await _broadcast_progress(context, sender_id, prog_id, success, fail, total)

        await _broadcast_progress(context, sender_id, prog_id, success, fail, total, done=True)
        logger.info(f"Broadcast (text) selesai: {success} sukses, {fail} gagal")
    except Exception as e:
        logger.error(f"Broadcast text error: {e}")

# ==================== HELP & INFO ====================
async def _verify_quiz_membership(context, user_id: int, reply_q=None, reply_msg=None):
    """Check if user is member of @carpetsquiz and mark task done if so."""
    try:
        member = await context.bot.get_chat_member(chat_id="@carpetsquiz", user_id=user_id)
        is_member = member.status not in ("left", "kicked", "banned")
    except Exception:
        is_member = False

    if is_member:
        await task_mark_done(user_id, "join_quiz")
        text = (
            "✅ <b>Terverifikasi!</b> Kamu adalah member <b>@carpetsquiz</b>.\n\n"
            "Task sudah dicatat. Kembali ke Mini App untuk klaim reward! 🎁"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📱 Kembali ke Mini App", url=MINI_APP_URL)]])
    else:
        text = (
            "❌ Kamu belum join <b>@carpetsquiz</b>.\n\n"
            "Join grupnya dulu, lalu tekan <b>Verifikasi</b> lagi!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ Join @carpetsquiz", url="https://t.me/carpetsquiz")],
            [InlineKeyboardButton("📱 Kembali ke Mini App", url=MINI_APP_URL)],
        ])

    if reply_q:
        await reply_q.answer("✅ Terverifikasi!" if is_member else "❌ Belum join @carpetsquiz.", show_alert=True)
        try:
            await reply_q.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception: pass
    elif reply_msg:
        await reply_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def show_tasks(q, user):
    u = await get_user(user.id)
    inv = u.get("inventory", {}) or {}

    text = "🎯 <b>Misi & Task</b>\n━━━━━━━━━━━━━━━\n\n"
    claimed = 0

    for task in TASKS:
        tid = task["id"]
        emoji = task.get("emoji", "📋")
        coin = task.get("reward_coin", 0)
        food = task.get("reward_food", 0)
        reward_txt = f"+{coin}🪙" + (f" +{food}x🥩" if food else "")
        is_claimed = bool(inv.get(_tk_done(tid)))
        is_ready = _task_is_ready(inv, task)
        if is_claimed:
            claimed += 1

        if task["type"] in ("collab", "channel", "milestone"):
            status = "✅" if is_claimed else ("🟢" if is_ready else "⬜")
            prog_txt = ""
        else:
            current = int(inv.get(_tk(tid), 0))
            target = task.get("target", 1)
            status = "✅" if is_claimed else ("🟢" if is_ready else f"({current}/{target})")
            prog_txt = f" {current}/{target}" if not is_claimed else ""

        text += f"{status} {emoji} <b>{task['title']}</b>{prog_txt}\n   💰 {reward_txt}\n\n"

    text += f"<i>{claimed}/{len(TASKS)} misi diklaim</i>\n\n"
    text += "📱 <b>Buka Mini App untuk GO, Sudah Selesai & Klaim reward!</b>"

    buttons = [
        [InlineKeyboardButton("📱 Buka Mini App → Misi", url=MINI_APP_URL)],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="main_menu")],
    ]
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_force_sub(update, context): return
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    u = await get_user(user.id)
    inv = u.get("inventory", {}) or {}
    text = "🎯 <b>Misi & Task</b>\n━━━━━━━━━━━━━━━\n\n"
    claimed = 0
    for task in TASKS:
        tid = task["id"]
        emoji = task.get("emoji", "📋")
        coin = task.get("reward_coin", 0)
        food = task.get("reward_food", 0)
        reward_txt = f"+{coin}🪙" + (f" +{food}x🥩" if food else "")
        is_claimed = bool(inv.get(_tk_done(tid)))
        is_ready = _task_is_ready(inv, task)
        if is_claimed:
            claimed += 1
        if task["type"] in ("collab", "channel", "milestone"):
            status = "✅" if is_claimed else ("🟢" if is_ready else "⬜")
            prog_txt = ""
        else:
            current = int(inv.get(_tk(tid), 0))
            target = task.get("target", 1)
            status = "✅" if is_claimed else ("🟢" if is_ready else f"({current}/{target})")
            prog_txt = f" {current}/{target}" if not is_claimed else ""
        text += f"{status} {emoji} <b>{task['title']}</b>{prog_txt}\n   💰 {reward_txt}\n\n"
    text += f"<i>{claimed}/{len(TASKS)} misi diklaim</i>\n\n"
    text += "📱 <b>Buka Mini App untuk GO, Sudah Selesai & Klaim reward!</b>"
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Buka Mini App → Misi", url=MINI_APP_URL)]])
    )


async def show_help_info(q):
    await q.edit_message_text(
        "❓ <b>Help & Info</b>\n━━━━━━━━━━━━━━━\n\n"
        "Butuh bantuan atau pertanyaan tentang bot ini?\n\n"
        "💬 <b>Kontak untuk pertanyaan & bantuan:</b>\n@carpetsrobot\n\n"
        "📋 <b>Info update Carpets:</b>\n@listbotfoocl\n\n"
        "━━━━━━━━━━━━━━━\n<i>Kami siap membantu kamu~ 🐾</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contact: @carpetshelpbot", url="https://t.me/carpetshelpbot")],
            [InlineKeyboardButton("📋 Update: @listbotfoocl", url="https://t.me/listbotfoocl")],
            [InlineKeyboardButton("❓ Bantuan Lengkap", callback_data="help")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )

# ==================== HELP ====================
async def show_help(q):
    text = """
❓ <b>BANTUAN THE CARPET SHOP</b>
━━━━━━━━━━━━━━━

🏪 <b>Adopsi Pet:</b>
• Buka Carpet Shop → pilih hewan
• Kamu dapat kode invite — bagikan ke 1 teman
• Partner join dengan: <code>/join KODE</code> atau klik link
• Pengiriman baru mulai setelah partner join!
• Tunggu 5 jam atau percepat dengan 6 tap

👫 <b>Sistem 2 Orang:</b>
• Setiap pet dimiliki 2 orang (Owner 1 & 2)
• Partner join via kode atau link
• Keduanya bisa rawat pet bersama

👆 <b>Tap Percepat:</b>
• Share link pengiriman ke teman
• Butuh 6 tap dari 6 orang berbeda
• Pet langsung tiba setelah 6 tap!
• Cara share: klik tombol 🚀 Share & Percepat

🐾 <b>Rawat Pet:</b>
• 🍽️ Kasih Makan — beli makanan dulu di toko
• 🎾 Ajak Main — cooldown 5 jam
• 💊 Obati — pakai obat dari toko
• ⚠️ Jaga kelaparan &lt; 70% biar pet ga sakit!

🐄 <b>Hewan Ternak:</b>
• Beli ternak di menu 🐄 Ternak
• Ternak produksi hasil (susu, telur, madu, dll) secara berkala
• Panen → Jual dapat koin, atau Simpan ke inventori untuk kasih ke pet

🎮 <b>Mini Game (Maks 7x/hari per game):</b>
• 🔢 Tebak Angka | 🎲 Dadu
• 🧠 Kuis Hewan | ⚽ Tangkap Bola
• Gagal = tidak dapat koin!

🎁 <b>Koin Harian:</b>
• Ambil 50 🪙 gratis tiap hari!

🔗 <b>Referral:</b>
• Ajak teman pakai link referralmu (di menu /start)
• Teman join → kamu dapat <b>1.000 🪙</b>!

⭐ <b>Hewan Langka:</b>
• Axolotl & Panda: 200 🪙
• Unicorn & Naga: 300 🪙
• Phoenix & Koi: 500 🪙

💍 <b>Pernikahan Pet:</b>
• Pet Level 10+ bisa dinikahkan
• Share undangan lewat inline: <code>@carpetsrobot marry KODE</code>
""".strip()
    kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🐄 Ternak", callback_data="livestock_menu"),
             InlineKeyboardButton("❓ Help & Info", callback_data="help_info")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu"),
             InlineKeyboardButton("📋 List Bot", url=SHOP_URL)]
        ])
    try:
        await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        # Pesan asal tidak bisa di-edit (mis. dipanggil dari reply keyboard) → kirim baru
        try:
            await q.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            chat_id = q.message.chat_id if getattr(q, "message", None) else q.from_user.id
            await _BOT.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def job_delivery_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 10 menit: auto deliver — filter di DB, hemat transfer"""
    logger.info("job_delivery_tick: mulai...")
    try:
        now = now_wib()
        # Ambil delivery yang sudah waktunya tiba DAN sudah ada partner (owner2_id)
        deliveries = await sb("GET", "deliveries", {
            "is_delivered": "eq.false",
            "started": "eq.true",
            "arrive_at": f"lte.{now.isoformat()}",
            "select": "id,code,owner1_id,owner2_id,pet_type,pet_name,tap_count",
        }) or []

        delivered_count = 0

        for d in deliveries:
            # Hanya deliver kalau sudah ada owner2 (partner sudah join)
            if not d.get("owner2_id"):
                continue

            info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})
            try:
                await _create_pet_from_delivery(d, d["code"])
                await update_delivery(d["code"], {"is_delivered": True})
                delivered_count += 1

                # Notif ke kedua owner
                for oid in [d.get("owner1_id"), d.get("owner2_id")]:
                    if oid:
                        try:
                            await context.bot.send_message(
                                oid,
                                f"🎊 <b>Pet kamu sudah tiba!</b>\n"
                                f"{info['emoji']} <b>{d['pet_name']}</b> siap dirawat!\n\n"
                                f"Selamat merawat peliharaanmu~ 💕",
                                parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")
                                ]])
                            )
                            await asyncio.sleep(0.05)
                        except Exception as e:
                            logger.warning(f"Notif deliver gagal ke {oid}: {e}")

                await log(context, f"📦 Auto-deliver: {info['emoji']} <b>{d['pet_name']}</b> milik <code>{d['owner1_id']}</code>")
            except Exception as e:
                logger.error(f"job_delivery_tick: gagal deliver {d.get('code')}: {e}")

        # Cleanup: tandai delivered untuk delivery lama (>30 hari) yang tidak punya partner
        # supaya tidak numpuk terus
        cutoff_stale = (now - timedelta(days=30)).isoformat()
        stale = await sb("GET", "deliveries", {
            "is_delivered": "eq.false",
            "started": "eq.false",
            "created_at": f"lte.{cutoff_stale}",
            "select": "id,code,owner1_id,pet_name",
        }) or []
        for d in stale:
            await update_delivery(d["code"], {"is_delivered": True})
            logger.info(f"job_delivery_tick: cleanup stale delivery {d['code']} ({d.get('pet_name')})")

        if delivered_count:
            logger.info(f"job_delivery_tick: {delivered_count} pet berhasil dikirim")
        else:
            logger.info("job_delivery_tick: tidak ada pengiriman yang perlu diproses")

    except Exception as e:
        logger.error(f"job_delivery_tick error: {e}")


# ==================== HUNGER & POOP JOBS ====================
HUNGER_THRESHOLDS = [20, 40, 60, 80, 100]

async def job_hunger_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 30 menit: apply hunger decay ke semua pet yang tidak tidur, notif per threshold 20%"""
    logger.info("job_hunger_tick: mulai...")
    try:
        now_ts = now_wib()
        now_iso = now_ts.isoformat()
        pets = await sb_get_all("pets", {
            "select": "id,owner1_id,owner2_id,pet_type,name,hunger,happiness,health,"
                      "last_decay,last_bath,soap_premium_active,is_dirty,is_sleeping,"
                      "poop_count,last_notif_hunger,boarding_until,expedition_until,special_ability,pil_anti_lapar_until,pil_abadi_until",
            "is_missing":  "eq.false",
            "is_married":  "eq.false",
            "or": f"(boarding_until.is.null,boarding_until.lte.{now_iso})",
        })

        for pet in pets:
            # Skip pet tidur
            if pet.get("is_sleeping"):
                continue
            # Skip pet di boarding/ekspedisi aktif
            if pet.get("boarding_until") and parse_dt(pet["boarding_until"]) > now_ts:
                continue
            if pet.get("expedition_until") and parse_dt(pet["expedition_until"]) > now_ts:
                continue
            # Skip kalau punya special ability anti lapar (hunger freeze)
            ability = pet.get("special_ability") or ""
            if "anti_hunger" in ability:
                continue
            # Skip kalau pil anti lapar masih aktif
            pil_lapar = pet.get("pil_anti_lapar_until")
            if pil_lapar and parse_dt(pil_lapar) > now_ts:
                continue
            # Moon Rabbit: tahan lapar (hunger naik ÷4)
            if PETS.get(pet.get("pet_type", ""), {}).get("hunger_resist"):
                if random.random() < 0.75:  # 75% skip tick
                    continue
            old_hunger = (pet.get("hunger") or 0)
            last_notif = pet.get("last_notif_hunger") or 0
            updated    = decay_pet_stats(dict(pet))
            new_hunger = updated["hunger"]

            stats_changed = (
                new_hunger != old_hunger
                or updated["happiness"] != (pet.get("happiness") or 0)
                or updated["health"]    != (pet.get("health") or 100)
                or updated.get("is_dirty", False) != pet.get("is_dirty", False)
            )
            patch = {
                "hunger":    new_hunger,
                "happiness": updated["happiness"],
                "health":    updated["health"],
                "is_dirty":  updated.get("is_dirty", False),
            }
            if stats_changed:
                patch["last_decay"] = updated["last_decay"]

            # Cari threshold yang baru dilewati & belum pernah dinotif
            crossed = [t for t in HUNGER_THRESHOLDS if old_hunger < t <= new_hunger and t > last_notif]

            if crossed:
                threshold = crossed[-1]
                patch["last_notif_hunger"] = threshold

                info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🍽️ Kasih Makan", callback_data=f"feed_{pet['id']}")
                ]])

                _hunger_notif_count = getattr(job_hunger_tick, "_notif_count", 0)
                for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
                    if oid:
                        try:
                            nick = await get_nickname_cached(oid)
                            if threshold >= 80:
                                msg = (f"😩 {nick}, {info['emoji']} <b>{pet['name']}</b> LAPAR BANGET! "
                                       f"Kelaparan sudah <b>{new_hunger}%</b>!\n\n"
                                       f"Segera kasih makan sebelum sakit! 🍖")
                            elif threshold >= 60:
                                msg = (f"🤒 {nick}, {info['emoji']} <b>{pet['name']}</b> mulai kelaparan! "
                                       f"Kelaparan <b>{new_hunger}%</b>!\n\n"
                                       f"Kasih makan sekarang ya~ 🍖")
                            elif threshold >= 40:
                                msg = (f"⚠️ {nick}, {info['emoji']} <b>{pet['name']}</b> lapar nih! "
                                       f"Kelaparan <b>{new_hunger}%</b>.\n\n"
                                       f"Jangan lupa kasih makan~ 🍪")
                            else:
                                msg = (f"🍽️ {nick}, {info['emoji']} <b>{pet['name']}</b> mulai lapar. "
                                       f"Kelaparan <b>{new_hunger}%</b>.")
                            await context.bot.send_message(
                                oid, msg,
                                parse_mode=ParseMode.HTML,
                                reply_markup=kb
                            )
                            _hunger_notif_count += 1
                            # Rate limit: pause tiap 30 notif agar bot tetap responsif
                            if _hunger_notif_count % 30 == 0:
                                await asyncio.sleep(1)
                            else:
                                await asyncio.sleep(0.05)
                        except Exception as e:
                            logger.warning(f"Notif hunger gagal ke {oid}: {e}")
                job_hunger_tick._notif_count = _hunger_notif_count

            # Reset last_notif_hunger kalau hunger turun (udah dikasih makan)
            if new_hunger < last_notif and last_notif > 0:
                patch["last_notif_hunger"] = 0

            # Batch: hanya write kalau ada perubahan signifikan
            changed = (
                abs(patch.get("hunger", old_hunger) - old_hunger) >= 5 or
                patch.get("last_notif_hunger") is not None or
                patch.get("is_dirty") != pet.get("is_dirty")
            )
            if changed:
                await sb("PATCH", "pets", {"id": f"eq.{pet['id']}"}, patch)
                # Update cache in-place, jangan hapus
                cached = _pet_cache.get(pet["id"])
                if cached:
                    cached["data"].update(patch)

        logger.info(f"job_hunger_tick: {len(pets)} pet diproses")
    except Exception as e:
        logger.error(f"job_hunger_tick error: {e}")


async def job_poop_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 45 menit: filter last_poop_at di DB — hemat transfer"""
    logger.info("job_poop_tick: mulai...")
    try:
        now = now_wib()
        cutoff = (now - timedelta(hours=POOP_INTERVAL)).isoformat()
        now_iso2 = now.isoformat()
        # Filter: tidak tidur, tidak missing, poop < 5, last_poop sudah lewat interval
        # boarding dan expedition di-filter Python-side (nested AND di PostgREST kadang bermasalah)
        pets = await sb_get_all("pets", {
            "select": "id,owner1_id,owner2_id,pet_type,name,poop_count,boarding_until,expedition_until,special_ability,pil_anti_pup_until",
            "is_sleeping": "eq.false",
            "is_missing":  "eq.false",
            "is_married":  "eq.false",
            "poop_count":  "lt.5",
            "or": f"(last_poop_at.is.null,last_poop_at.lte.{cutoff})",
        })

        for pet in pets:
            # Skip pet di boarding/ekspedisi aktif
            if pet.get("boarding_until") and parse_dt(pet["boarding_until"]) > now:
                continue
            if pet.get("expedition_until") and parse_dt(pet["expedition_until"]) > now:
                continue
            # Skip kalau punya special ability anti pup
            ability = pet.get("special_ability") or ""
            if "anti_poop" in ability:
                continue
            # Skip kalau pil anti pup masih aktif
            pil_until = pet.get("pil_anti_pup_until")
            if pil_until and parse_dt(pil_until) > now:
                continue

            new_poop = min(5, (pet.get("poop_count") or 0) + 1)
            await sb("PATCH", "pets", {"id": f"eq.{pet['id']}"}, {
                "poop_count":  new_poop,
                "last_poop_at": now.isoformat(),
            })
            _cdel(_pet_cache, pet["id"])

            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🧹 Bersihkan", callback_data=f"clean_{pet['id']}")
            ]])

            for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
                if oid:
                    try:
                        nick = await get_nickname_cached(oid)
                        if new_poop >= 3:
                            msg = (f"💩 {nick}, {info['emoji']} <b>{pet['name']}</b> poopnya udah numpuk ({new_poop}x)!\n\n"
                                   f"Kandang makin kotor, happiness terus turun! Bersihkan sekarang~ 🧹")
                        else:
                            msg = (f"💩 {nick}, {info['emoji']} <b>{pet['name']}</b> poop! ({new_poop}x)\n\n"
                                   f"Bersihkan kandang yuk~ 🧹")
                        await context.bot.send_message(
                            oid, msg,
                            parse_mode=ParseMode.HTML,
                            reply_markup=kb
                        )
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.warning(f"Notif poop gagal ke {oid}: {e}")

        logger.info("job_poop_tick: selesai")
    except Exception as e:
        logger.error(f"job_poop_tick error: {e}")


# ==================== SLEEP JOBS ====================
async def job_bath_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Tiap hari jam 08.00 WIB: bulk mark dirty + bulk nickname fetch"""
    logger.info("job_bath_reminder: mulai...")
    try:
        # Filter langsung di query: bukan koi, bukan missing, bukan sleeping
        now_bath_iso = now_wib().isoformat()
        pets = await sb_get_all("pets", {
            "select": "id,owner1_id,owner2_id,pet_type,name,last_bath,soap_premium_active,boarding_until,expedition_until",
            "is_missing": "eq.false",
            "is_sleeping": "eq.false",
            "pet_type": "neq.koi",
            "or": f"(boarding_until.is.null,boarding_until.lte.{now_bath_iso})",
        })

        now = now_wib()
        dirty_pets = []
        for pet in pets:
            # Skip pet di boarding/ekspedisi aktif
            if pet.get("boarding_until") and parse_dt(pet["boarding_until"]) > now:
                continue
            if pet.get("expedition_until") and parse_dt(pet["expedition_until"]) > now:
                continue
            last_bath = pet.get("last_bath")
            bath_hours = 48 if pet.get("soap_premium_active") else 24
            is_dirty = not last_bath or (now - parse_dt(last_bath)).total_seconds() / 3600 >= bath_hours
            if is_dirty:
                dirty_pets.append(pet)

        if not dirty_pets:
            logger.info("job_bath_reminder: semua pet bersih")
            return

        # BULK update is_dirty — 1 query
        await bulk_patch_pets([p["id"] for p in dirty_pets], {"is_dirty": True})
        for p in dirty_pets:
            _cdel(_pet_cache, p["id"])

        # Bulk nickname — 1 query
        all_owner_ids = list({oid for p in dirty_pets for oid in [p.get("owner1_id"), p.get("owner2_id")] if oid})
        nicknames = await get_nicknames_bulk(all_owner_ids)

        for pet in dirty_pets:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
                if oid:
                    try:
                        panggilan = nicknames.get(oid, "Kamu")
                        await context.bot.send_message(
                            oid,
                            f"🛁 {panggilan}, {info['emoji']} <b>{pet['name']}</b> belum mandi!\n"
                            f"<i>Buka Pet → 🛁 Mandi sekarang!</i>",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛁 Mandi", callback_data=f"bath_{pet['id']}")]])
                        )
                        await asyncio.sleep(0.05)
                    except: pass

        logger.info(f"job_bath_reminder: {len(dirty_pets)}/{len(pets)} pet kotor (1 bulk query)")
    except Exception as e:
        logger.error(f"job_bath_reminder error: {e}")

async def job_startup_recovery(context: ContextTypes.DEFAULT_TYPE):
    """Jalan sekali saat bot start: bangunkan pet yang masih sleeping di luar jam tidur"""
    logger.info("job_startup_recovery: cek pet yang masih ketiduran...")
    if is_sleep_time():
        logger.info("job_startup_recovery: masih jam tidur, skip")
        return
    try:
        pets = await sb_get_all("pets", {
            "select": "id,owner1_id,owner2_id,pet_type,name,health,happiness",
            "is_sleeping": "eq.true"
        })
        if not pets:
            logger.info("job_startup_recovery: tidak ada pet yang ketiduran")
            return
        now_str = now_wib().isoformat()
        for pet in pets:
            new_health    = min(100, (pet.get("health") or 100) + 20)
            new_happiness = min(100, (pet.get("happiness") or 80) + 15)
            await sb("PATCH", "pets", {"id": f"eq.{pet['id']}"}, {
                "is_sleeping": False, "health": new_health,
                "happiness": new_happiness, "last_decay": now_str
            })
            _cdel(_pet_cache, pet["id"])

        # Bulk nickname fetch
        all_owner_ids = list({oid for p in pets for oid in [p.get("owner1_id"), p.get("owner2_id")] if oid})
        nicknames = await get_nicknames_bulk(all_owner_ids)

        for pet in pets:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
                if oid:
                    try:
                        panggilan = nicknames.get(oid, "Kamu")
                        await context.bot.send_message(
                            oid,
                            f"☀️ {panggilan}, {info['emoji']} <b>{pet['name']}</b> udah bangun!\n"
                            f"❤️ +20 Sehat | 😊 +15 Senang",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet['id']}")]])
                        )
                        await asyncio.sleep(0.05)
                    except: pass
        logger.info(f"job_startup_recovery: {len(pets)} pet dibangunkan")
    except Exception as e:
        logger.error(f"job_startup_recovery error: {e}")



async def job_sleep_start(context: ContextTypes.DEFAULT_TYPE):
    """Jam 22.00 WIB: semua pet mulai tidur — BULK update, notif paralel"""
    logger.info("job_sleep_start: pet mulai tidur...")
    try:
        pets = await sb_get_all("pets", {
            "select": "id,owner1_id,owner2_id,pet_type,name",
            "is_missing": "eq.false",
            "is_sleeping": "eq.false",
        })
        if not pets:
            logger.info("job_sleep_start: tidak ada pet")
            return

        # BULK UPDATE semua sekaligus — 1 query, semua tidur di waktu yang sama
        pet_ids = [p["id"] for p in pets]
        ids_str = ",".join(str(i) for i in pet_ids)
        await bulk_patch_pets(pet_ids, {"is_sleeping": True, "last_decay": now_wib().isoformat()})
        _pet_cache.clear()

        # Buat semua task notif lalu kirim paralel (tanpa fetch nickname — hemat koneksi)
        async def _send_sleep_notif(pet):
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
                if oid:
                    try:
                        await context.bot.send_message(
                            oid,
                            f"🌙 {info['emoji']} <b>{pet['name']}</b> mau tidur~\n"
                            f"<i>Bangun jam 07.00 WIB!</i>",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet['id']}")]])
                        )
                    except: pass

        # Kirim notif tidur dalam batch 50 supaya ga flood Telegram rate limit
        for i in range(0, len(pets), 50):
            batch = pets[i:i+50]
            await asyncio.gather(*[_send_sleep_notif(p) for p in batch], return_exceptions=True)
            if i + 50 < len(pets):
                await asyncio.sleep(1)
        logger.info(f"job_sleep_start: {len(pets)} pet tidur (bulk update + notif paralel)")
    except Exception as e:
        logger.error(f"job_sleep_start error: {e}")

async def job_sleep_end(context: ContextTypes.DEFAULT_TYPE):
    """Jam 07.00 WIB: semua pet bangun — bulk update stats, notif paralel"""
    logger.info("job_sleep_end: pet bangun...")
    try:
        pets = await sb_get_all("pets", {
            "select": "id,owner1_id,owner2_id,pet_type,name,health,happiness,is_sleeping",
            "is_sleeping": "eq.true",
        })
        if not pets:
            logger.info("job_sleep_end: tidak ada pet tidur")
            return

        now_str = now_wib().isoformat()

        # Bulk update is_sleeping=false dulu untuk semua sekaligus
        pet_ids = [p["id"] for p in pets]
        await bulk_patch_pets(pet_ids, {"is_sleeping": False, "last_decay": now_str})
        logger.info(f"job_sleep_end: bulk update {len(pet_ids)} pet selesai")

        # Update health/happiness per-pet tapi tetap batch (nilai berbeda tiap pet)
        async def _wake_pet(pet):
            new_health    = min(100, (pet.get("health") or 100) + 20)
            new_happiness = min(100, (pet.get("happiness") or 80) + 15)
            await update_pet(pet["id"], {"health": new_health, "happiness": new_happiness})

        for i in range(0, len(pets), 100):
            batch = pets[i:i+100]
            await asyncio.gather(*[_wake_pet(p) for p in batch], return_exceptions=True)
            if i + 100 < len(pets):
                await asyncio.sleep(0.3)

        # Notif bangun batch 50
        async def _send_wake_notif(pet):
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
                if oid:
                    try:
                        await context.bot.send_message(
                            oid,
                            f"☀️ {info['emoji']} <b>{pet['name']}</b> udah bangun!\n"
                            f"❤️ +20 Sehat | 😊 +15 Senang",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet['id']}")]])
                        )
                    except: pass

        for i in range(0, len(pets), 50):
            batch = pets[i:i+50]
            await asyncio.gather(*[_send_wake_notif(p) for p in batch], return_exceptions=True)
            if i + 50 < len(pets):
                await asyncio.sleep(1)

        logger.info(f"job_sleep_end: {len(pets)} pet bangun selesai")
    except Exception as e:
        logger.error(f"job_sleep_end error: {e}")

async def job_runaway_check(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 1 jam: bulk mark missing + bulk nickname.
    PENTING: pakai last_fed (waktu terakhir benar2 dirawat: kasih makan/main/obati/mandi),
    BUKAN last_decay — karena last_decay ikut ke-reset tiap kali pet sekadar DILIHAT,
    sehingga timer kabur tidak pernah terkumpul."""
    logger.info("job_runaway_check: mulai...")
    NEGLECT_HOURS = 72
    try:
        cutoff = (now_wib() - timedelta(hours=NEGLECT_HOURS)).isoformat()
        now_iso = now_wib().isoformat()
        candidates = await sb_get_all("pets", {
            "select": "id,owner1_id,owner2_id,pet_type,name,boarding_until,expedition_until,last_fed,last_decay",
            "is_sleeping": "eq.false",
            "is_missing": "eq.false",
        })
        # Filter manual berbasis last_fed (fallback ke last_decay utk row lama yg belum punya last_fed)
        cutoff_dt = now_wib() - timedelta(hours=NEGLECT_HOURS)
        pets = []
        for p in candidates:
            ref = p.get("last_fed") or p.get("last_decay")
            if not ref:
                continue
            try:
                if parse_dt(ref) > cutoff_dt:
                    continue
            except Exception:
                continue
            pets.append(p)
        # Filter manual: skip pet yang masih boarding atau ekspedisi
        pets = [p for p in pets if (
            not p.get("boarding_until") or parse_dt(p["boarding_until"]) <= now_wib()
        ) and (
            not p.get("expedition_until") or parse_dt(p["expedition_until"]) <= now_wib()
        )]

        if not pets:
            logger.info("job_runaway_check: tidak ada pet kabur")
            return

        # BULK mark missing — 1 query
        await bulk_patch_pets([p["id"] for p in pets], {"is_missing": True})
        for p in pets:
            _cdel(_pet_cache, p["id"])

        # Bulk nickname — 1 query
        all_owner_ids = list({oid for p in pets for oid in [p.get("owner1_id"), p.get("owner2_id")] if oid})
        nicknames = await get_nicknames_bulk(all_owner_ids)

        for pet in pets:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾", "name": "?"})
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Cari Pet", callback_data=f"find_pet_{pet['id']}")]])
            msg = (f"🏃 <b>{pet['name']}</b> kabur!\n"
                   f"{info['emoji']} Sudah 3 hari tidak diurus...\n"
                   f"<i>Masih bisa dicari kembali~ 🔍</i>")
            for oid in [pet.get("owner1_id"), pet.get("owner2_id")]:
                if oid:
                    try:
                        await context.bot.send_message(oid, msg, parse_mode=ParseMode.HTML, reply_markup=kb)
                        await asyncio.sleep(0.05)
                    except: pass
            await log(context, f"🏃 Kabur: {info['emoji']} <b>{pet['name']}</b> owner <code>{pet.get('owner1_id')}</code>")

        logger.info(f"job_runaway_check: {len(pets)} pet ditandai kabur (1 bulk)")
    except Exception as e:
        logger.error(f"job_runaway_check error: {e}")


# ==================== JOB: WORK COMPLETION ====================

# ==================== SEKOLAH & PROFESI ====================

async def show_profesi_pilih(q, user, pet_id: int):
    """Tampilkan pilihan profesi: penjelajah atau pengumpul"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp", 0))
    if lv < LEVEL_PROFESI:
        await q.answer(f"❌ Butuh Lv.{LEVEL_PROFESI}!", show_alert=True); return
    if pet.get("profesi_kerja"):
        await q.answer(f"✅ Sudah punya profesi: {pet['profesi_kerja']}!", show_alert=True); return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"🎓 <b>Pilih Profesi untuk {info['emoji']} {pet['name']}</b>\n━━━━━━━━━━━━━━━\n\n"
        f"<b>🗺️ Penjelajah</b>\n"
        f"• Sekali kerja dapat koin\n"
        f"• Skill 0→100, max reward 500 🪙/kerja\n\n"
        f"<b>🧺 Pengumpul</b>\n"
        f"• Sekali kerja dapat makanan\n"
        f"• Skill 0→100, max reward 10 makanan/kerja\n\n"
        f"<i>Pilihan permanen! Pilih dengan bijak.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗺️ Penjelajah", callback_data=f"pet_profesi_set_{pet_id}_penjelajah")],
            [InlineKeyboardButton("🧺 Pengumpul", callback_data=f"pet_profesi_set_{pet_id}_pengumpul")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"select_pet_{pet_id}")],
        ]))

async def do_profesi_set(q, user, pet_id: int, profesi: str):
    """Set profesi permanen"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("profesi_kerja"):
        await q.answer("❌ Profesi sudah dipilih!", show_alert=True); return
    await update_pet(pet_id, {"profesi_kerja": profesi, "skill_profesi": 0})
    _cdel(_pet_cache, pet_id)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    label = "🗺️ Penjelajah" if profesi == "penjelajah" else "🧺 Pengumpul"
    await q.edit_message_text(
        f"✅ <b>{info['emoji']} {pet['name']}</b> kini berprofesi sebagai <b>{label}</b>!\n\n"
        f"Sekolah di Lv.60 untuk tingkatkan skill profesinya~",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))

async def show_profesi_work(q, user, pet_id: int, context):
    """Kerja profesional berdasarkan profesi"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    profesi = pet.get("profesi_kerja")
    if not profesi:
        await q.answer("❌ Belum punya profesi! Pilih profesi dulu.", show_alert=True)
        await show_profesi_pilih(q, user, pet_id)
        return
    # Cek masih kerja
    if pet.get("work_until") and parse_dt(pet["work_until"]) > now_wib():
        sisa = fmt_countdown(parse_dt(pet["work_until"]))
        await q.answer(f"⏳ Masih kerja! Selesai dalam {sisa}", show_alert=True); return
    # Cek cooldown 1x per hari
    last_work = pet.get("last_work")
    if last_work:
        lw = parse_dt(last_work)
        if (now_wib() - lw).total_seconds() < 86400:
            cd = fmt_countdown(lw + timedelta(hours=24))
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            await q.edit_message_text(
                f"💼 <b>{pet['name']}</b> sudah kerja hari ini!\n━━━━━━━━━━━━━━━\n\n"
                f"{info['emoji']} Istirahat dulu ya~\n"
                f"⏰ Bisa kerja lagi dalam: <b>{cd}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")]]))
            return
    skill = int(pet.get("skill_profesi") or 0)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    if profesi == "penjelajah":
        reward = hitung_reward_penjelajah(skill)
        label = "🗺️ Penjelajah"
        reward_txt = f"🪙 {reward:,} koin"
    else:
        reward = hitung_reward_pengumpul(skill)
        label = "🧺 Pengumpul"
        reward_txt = f"🍖 {reward}x makanan"
    await q.edit_message_text(
        f"💼 <b>Kerja Profesional — {label}</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{pet['name']}</b>\n"
        f"🎓 Skill: <b>{skill}/100</b>\n"
        f"💰 Estimasi reward: <b>{reward_txt}</b>\n\n"
        f"Durasi kerja: <b>2 jam</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ Kirim Kerja ({reward_txt})", callback_data=f"pet_profwork_confirm_{pet_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"select_pet_{pet_id}")],
        ]))

async def do_profesi_work(q, user, pet_id: int, context):
    """Konfirmasi kirim kerja profesional"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("work_until") and parse_dt(pet["work_until"]) > now_wib():
        await q.answer("❌ Masih kerja!", show_alert=True); return
    # Double-check cooldown di konfirmasi
    last_work = pet.get("last_work")
    if last_work:
        lw = parse_dt(last_work)
        if (now_wib() - lw).total_seconds() < 86400:
            sisa = fmt_countdown(lw + timedelta(hours=24))
            await q.answer(f"⏰ Sudah kerja hari ini! Bisa lagi dalam {sisa}", show_alert=True); return
    work_until = (now_wib() + timedelta(hours=2)).isoformat()
    await update_pet(pet_id, {
        "work_until": work_until,
        "last_work": now_wib().isoformat(),
        "profesi_work_active": True,
    })
    _cdel(_pet_cache, pet_id)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    profesi = pet.get("profesi_kerja", "penjelajah")
    label = "🗺️ Penjelajah" if profesi == "penjelajah" else "🧺 Pengumpul"
    await q.edit_message_text(
        f"💼 <b>{info['emoji']} {pet['name']}</b> pergi kerja sebagai {label}!\n"
        f"🏠 Pulang dalam <b>2 jam</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]))

async def show_sekolah(q, user, pet_id: int):
    """Tampilkan menu sekolah"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    lv = calc_level(pet.get("xp", 0))
    if lv < LEVEL_SEKOLAH:
        await q.answer(f"❌ Butuh Lv.{LEVEL_SEKOLAH}!", show_alert=True); return
    profesi = pet.get("profesi_kerja")
    if not profesi:
        await q.answer("❌ Belum punya profesi! Pilih profesi dulu.", show_alert=True)
        await show_profesi_pilih(q, user, pet_id)
        return
    skill = int(pet.get("skill_profesi") or 0)
    if skill >= SEKOLAH_MAX_SKILL:
        await q.answer("✅ Skill sudah maksimal (100)! Tidak bisa sekolah lagi.", show_alert=True); return
    # Cek sudah sekolah hari ini
    last_sekolah = pet.get("last_sekolah")
    today = now_wib().date().isoformat()
    if last_sekolah and last_sekolah[:10] == today:
        await q.answer("❌ Sudah sekolah hari ini! Coba lagi besok.", show_alert=True); return
    u = await get_user(user.id)
    koin = u.get("koin", 0)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    label = "🗺️ Penjelajah" if profesi == "penjelajah" else "🧺 Pengumpul"
    new_skill = min(SEKOLAH_MAX_SKILL, skill + SEKOLAH_SKILL_PER_SESSION)
    reward_preview = hitung_reward_penjelajah(new_skill) if profesi == "penjelajah" else hitung_reward_pengumpul(new_skill)
    reward_unit = "🪙 koin" if profesi == "penjelajah" else "x makanan"
    await q.edit_message_text(
        f"🏫 <b>Sekolah — {info['emoji']} {pet['name']}</b>\n━━━━━━━━━━━━━━━\n\n"
        f"Profesi: <b>{label}</b>\n"
        f"🎓 Skill sekarang: <b>{skill}/100</b>\n"
        f"📈 Setelah sekolah: <b>{new_skill}/100</b>\n"
        f"💰 Reward kerja nanti: <b>{reward_preview} {reward_unit}</b>\n\n"
        f"Biaya: <b>{SEKOLAH_COST:,} 🪙</b>\nKoinmu: <b>{koin:,} 🪙</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📚 Sekolah ({SEKOLAH_COST:,}🪙)", callback_data=f"pet_sekolah_confirm_{pet_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"select_pet_{pet_id}")],
        ]))

async def do_sekolah(q, user, pet_id: int, context):
    """Proses sekolah: bayar, set timer, reward pas pulang"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    # Cek lagi sedang sekolah
    if pet.get("sekolah_until") and parse_dt(pet["sekolah_until"]) > now_wib():
        sisa = fmt_countdown(parse_dt(pet["sekolah_until"]))
        await q.answer(f"⏳ Masih sekolah! Selesai dalam {sisa}", show_alert=True); return
    # Cek lagi sedang kerja
    if pet.get("work_until") and parse_dt(pet.get("work_until","1970")) > now_wib():
        await q.answer("❌ Pet lagi kerja! Selesai dulu baru bisa sekolah.", show_alert=True); return
    today = now_wib().date().isoformat()
    if (pet.get("last_sekolah") or "")[:10] == today:
        await q.answer("❌ Sudah sekolah hari ini!", show_alert=True); return
    skill = int(pet.get("skill_profesi") or 0)
    if skill >= SEKOLAH_MAX_SKILL:
        await q.answer("✅ Skill sudah max!", show_alert=True); return
    ok = await spend_koin(user.id, SEKOLAH_COST, "sekolah")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {SEKOLAH_COST:,} 🪙", show_alert=True); return
    sekolah_until = (now_wib() + timedelta(hours=SEKOLAH_DURATION_HOURS)).isoformat()
    await update_pet(pet_id, {"sekolah_until": sekolah_until, "last_sekolah": now_wib().isoformat()})
    _cdel(_pet_cache, pet_id)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    profesi = pet.get("profesi_kerja", "penjelajah")
    label = "🗺️ Penjelajah" if profesi == "penjelajah" else "🧺 Pengumpul"
    await q.edit_message_text(
        f"🏫 <b>{info['emoji']} {pet['name']} berangkat sekolah!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"📚 Belajar skill {label}...\n"
        f"⏰ Pulang dalam <b>{SEKOLAH_DURATION_HOURS} jam</b>\n\n"
        f"<i>Selama sekolah pet tidak bisa diajak main atau dikasih makan~</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]))
    # Notif partner
    partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    if partner_id:
        try:
            await context.bot.send_message(partner_id,
                f"🏫 <b>{info['emoji']} {pet['name']}</b> lagi sekolah!\n"
                f"Pulang dalam <b>{SEKOLAH_DURATION_HOURS} jam</b>~",
                parse_mode=ParseMode.HTML)
        except: pass



async def job_work_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 15 menit: cek pet yang selesai kerja → kasih reward otomatis"""
    try:
        now_str = now_wib().isoformat()
        pets = await sb_get_all("pets", {
            "work_until": f"lte.{now_str}",
            "select": "id,name,pet_type,owner1_id,owner2_id,work_until,special_ability,profesi_kerja,skill_profesi,profesi_work_active,happiness,health",
            "is_missing": "eq.false",
        })
        for pet in pets:
            if not pet.get("work_until"): continue
            if pet.get("profesi_work_active"):
                await _claim_profesi_reward(pet, context)
            else:
                await _claim_work_reward(pet, context)
        if pets:
            logger.info(f"job_work_tick: {len(pets)} pet selesai kerja")
    except Exception as e:
        logger.error(f"job_work_tick error: {e}")


async def job_sekolah_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 15 menit: cek pet yang selesai sekolah → kasih reward skill"""
    try:
        now_str = now_wib().isoformat()
        pets = await sb_get_all("pets", {
            "sekolah_until": f"lte.{now_str}",
            "select": "id,name,pet_type,owner1_id,owner2_id,sekolah_until,profesi_kerja,skill_profesi,happiness",
            "is_missing": "eq.false",
        })
        for pet in pets:
            if not pet.get("sekolah_until"): continue
            skill = int(pet.get("skill_profesi") or 0)
            new_skill = min(SEKOLAH_MAX_SKILL, skill + SEKOLAH_SKILL_PER_SESSION)
            new_happy = min(100, (pet.get("happiness") or 80) + 10)
            await update_pet(pet["id"], {
                "skill_profesi": new_skill,
                "sekolah_until": None,
                "happiness": new_happy,
            })
            _cdel(_pet_cache, pet["id"])
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            profesi = pet.get("profesi_kerja", "penjelajah")
            label = "🗺️ Penjelajah" if profesi == "penjelajah" else "🧺 Pengumpul"
            msg = (f"🏫 <b>{info['emoji']} {pet['name']} pulang sekolah!</b>\n"
                   f"📚 Skill {label}: <b>{skill} → {new_skill}/100</b>\n"
                   f"😊 Senang +10\n\n<i>Besok bisa sekolah lagi~</i>")
            for uid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
                try:
                    await context.bot.send_message(uid, msg, parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet['id']}")]]))
                except: pass
        if pets:
            logger.info(f"job_sekolah_tick: {len(pets)} pet pulang sekolah")
    except Exception as e:
        logger.error(f"job_sekolah_tick error: {e}")


# ==================== JOB: CHILD ALLOWANCE ====================
async def job_child_allowance_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 6 jam: cek anak pet yang butuh uang saku / kabur"""
    try:
        now_dt = now_wib()
        children = await sb_get_all("pets", {
            "is_child": "eq.true",
            "is_missing": "eq.false",
            "select": "id,name,pet_type,owner1_id,owner2_id,last_allowance_request,allowance_paid_p1,allowance_paid_p2,parent1_pet_id,parent2_pet_id",
        })

        for child in children:
            last_req = child.get("last_allowance_request")
            if not last_req: continue
            la = parse_dt(last_req)
            days_since = (now_dt - la).total_seconds() / 86400

            if days_since < CHILD_ALLOWANCE_DAYS:
                continue

            p1_paid = child.get("allowance_paid_p1", False)
            p2_paid = child.get("allowance_paid_p2", False)

            # Ambil semua 4 orang tua (parent1 punya 2 owner, parent2 punya 2 owner)
            p1_pet = await get_pet_by_id(child.get("parent1_pet_id")) if child.get("parent1_pet_id") else None
            p2_pet = await get_pet_by_id(child.get("parent2_pet_id")) if child.get("parent2_pet_id") else None
            all_parent_owners = list(filter(None, set([
                p1_pet.get("owner1_id") if p1_pet else None,
                p1_pet.get("owner2_id") if p1_pet else None,
                p2_pet.get("owner1_id") if p2_pet else None,
                p2_pet.get("owner2_id") if p2_pet else None,
            ])))

            # Kalau 3 hari belum ada yang bayar → kabur
            if days_since >= CHILD_RUNAWAY_DAYS and not p1_paid and not p2_paid:
                await update_pet(child["id"], {"is_missing": True, "missing_since": now_dt.isoformat()})
                cinfo = PETS.get(child["pet_type"], {"emoji": "🐾"})
                for oid in all_parent_owners:
                    try:
                        await context.bot.send_message(
                            oid,
                            f"💔 <b>{child['name']} kabur!</b>\n"
                            f"{cinfo['emoji']} Tidak ada yang memberikan uang saku selama {CHILD_RUNAWAY_DAYS} hari...\n\n"
                            f"💰 Bayar <b>{CHILD_RECOVER_COST} 🪙</b> untuk membawanya pulang!",
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(
                                    f"🔍 Cari & Pulangkan ({CHILD_RECOVER_COST}🪙)",
                                    callback_data=f"child_recover_{child['id']}"
                                )
                            ]])
                        )
                    except: pass
                continue

            # Kirim notif minta uang saku ke semua parent yang belum bayar
            cinfo = PETS.get(child["pet_type"], {"emoji": "🐾"})
            p1_owner_ids = list(filter(None, [p1_pet.get("owner1_id") if p1_pet else None, p1_pet.get("owner2_id") if p1_pet else None]))
            p2_owner_ids = list(filter(None, [p2_pet.get("owner1_id") if p2_pet else None, p2_pet.get("owner2_id") if p2_pet else None]))

            notif_targets = set()
            if not p1_paid: notif_targets.update(p1_owner_ids)
            if not p2_paid: notif_targets.update(p2_owner_ids)

            for oid in notif_targets:
                try:
                    sisa_hari = max(0, CHILD_RUNAWAY_DAYS - int(days_since))
                    await context.bot.send_message(
                        oid,
                        f"👶 <b>{child['name']} minta uang saku!</b>\n"
                        f"{cinfo['emoji']} Bayar <b>{CHILD_ALLOWANCE_COIN} 🪙</b> ya~\n"
                        f"⚠️ Kalau tidak dibayar dalam <b>{sisa_hari} hari</b>, anak bisa kabur!",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                f"💰 Bayar {CHILD_ALLOWANCE_COIN}🪙",
                                callback_data=f"child_pay_{child['id']}"
                            )
                        ]])
                    )
                except: pass

        logger.info(f"job_child_allowance_tick: {len(children)} anak dicek")
    except Exception as e:
        logger.error(f"job_child_allowance_tick error: {e}")


# ==================== JOB: BADGE & LV50 ACC NOTIF ====================
async def job_level_unlock_check(context: ContextTypes.DEFAULT_TYPE):
    """Tiap jam: cek pet yang baru unlock fitur level baru"""
    try:
        for threshold, label in [(LEVEL_WORK, "kerja"), (LEVEL_CHILD, "punya anak"),
                                  (LEVEL_BADGE, "badge"), (LEVEL_SPECIAL_ACC, "aksesoris spesial")]:
            min_xp = (threshold - 1) * XP_PER_LEVEL
            pets = await sb_get_all("pets", {
                "xp": f"gte.{min_xp}",
                "select": "id,name,pet_type,xp,owner1_id,owner2_id,level_unlock_notified",
                "is_missing": "eq.false",
                "is_child": "eq.false",
            })
            for pet in pets:
                lv = calc_level(pet.get("xp") or 0)
                if lv < threshold: continue
                notified = pet.get("level_unlock_notified") or []
                if isinstance(notified, str):
                    try: notified = json.loads(notified)
                    except: notified = []
                if threshold in notified: continue
                # Kirim notif unlock
                info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
                ms = LEVEL_MILESTONES.get(threshold, f"Level {threshold}!")
                for oid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
                    try:
                        await context.bot.send_message(
                            oid,
                            f"🎉 <b>{pet['name']} mencapai Level {threshold}!</b>\n"
                            f"{info['emoji']} {ms}\n\n"
                            f"<i>Fitur baru tersedia — cek halaman pet kamu!</i>",
                            parse_mode="HTML",
                            reply_markup=__import__("telegram").InlineKeyboardMarkup([[
                                __import__("telegram").InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")
                            ]])
                        )
                    except: pass
                notified.append(threshold)
                await update_pet(pet["id"], {"level_unlock_notified": json.dumps(notified)})
        # Track task pet_lv60
        if lv >= 60:
            for oid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
                asyncio.create_task(task_mark_done(oid, "pet_lv60"))
    except Exception as e:
        logger.error(f"job_level_unlock_check error: {e}")


# ==================== ERROR HANDLER ====================
async def job_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Tiap hari jam 03.00 WIB: hapus semua data lama — deliveries, battles, marriages"""
    try:
        cutoff_30d = (now_wib() - timedelta(days=30)).isoformat()
        cutoff_3d  = (now_wib() - timedelta(days=3)).isoformat()
        cutoff_7d  = (now_wib() - timedelta(days=7)).isoformat()

        # Deliveries selesai > 30 hari
        await sb("DELETE", "deliveries", {"is_delivered": "eq.true", "created_at": f"lt.{cutoff_7d}"})
        # Battles selesai/expire > 3 hari
        await sb("DELETE", "battles", {"created_at": f"lt.{cutoff_3d}"})
        # Marriage proposals > 7 hari
        await sb("DELETE", "marriage_proposals", {"created_at": f"lt.{cutoff_7d}"})
        # Pet married orphan (is_married=true tapi owner1 DAN owner2 null dan sudah lama)
        await sb("DELETE", "pets", {"is_married": "eq.true", "owner1_id": "is.null", "owner2_id": "is.null",
                                    "married_at": f"lt.{cutoff_7d}"})
        # Clear nickname cache tiap malam
        _nickname_cache.clear()
        _pet_level_cache.clear()

        logger.info("job_cleanup: semua data lama dihapus")
    except Exception as e:
        logger.error(f"job_cleanup error: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}", exc_info=context.error)



# ==================== SOLO ADOPT ====================
async def do_adopt_solo(q, user, code: str, context):
    """User pilih rawat sendiri — pet langsung tiba tanpa nunggu partner"""
    res = await sb("GET", "deliveries", {"code": f"eq.{code}", "is_delivered": "eq.false"})
    if not res:
        await q.answer("❌ Data adopsi tidak ditemukan!", show_alert=True); return
    d = res[0]
    if d["owner1_id"] != user.id:
        await q.answer("❌ Bukan adopsimu!", show_alert=True); return

    info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})

    # Langsung buat pet tanpa owner2
    new_pet = await upsert_pet({
        "owner1_id":          d["owner1_id"],
        "owner2_id":          None,
        "name":               d["pet_name"],
        "pet_type":           d["pet_type"],
        "level":              1, "xp": 0,
        "hunger":             50, "happiness": 80, "health": 100,
        "last_decay":         now_wib().isoformat(),
        "last_fed":         now_wib().isoformat(),
        "last_played":        (now_wib() - timedelta(hours=6)).isoformat(),
        "last_bath":          now_wib().isoformat(),
        "last_poop_at":       now_wib().isoformat(),
        "last_poop":          now_wib().isoformat(),
        "poop_count":         0, "wangi_until": now_wib().isoformat(),
        "is_sleeping": False, "is_dirty": False, "is_missing": False,
        "is_married": False, "married_at": None, "married_to_pet_id": None,
        "accessory": None, "accessory_name": None, "accessory_key": None,
        "soap_premium_active": False,
        "boarding_until": None, "expedition_until": None, "expedition_dest": None,
        "last_notif_hunger": 100,
        "created_at": now_wib().isoformat(),
    })
    if not new_pet:
        await q.answer("❌ Gagal membuat pet, coba lagi dalam beberapa detik!", show_alert=True)
        return
    # Simpan kode_invite di delivery (is_delivered=True tapi kode masih valid untuk add partner nanti)
    await update_delivery(code, {"is_delivered": True})

    await q.edit_message_text(
        f"🎉 {info['emoji']} <b>{d['pet_name']}</b> sudah tiba!\n\n"
        f"👤 Kamu merawatnya <b>sendirian</b> untuk sekarang~\n\n"
        f"💡 Kapanpun mau invite partner, buka <b>🐾 Pet Saya</b> → tombol <b>👫 Tambah Partner</b>!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")],
            [InlineKeyboardButton("🏠 Menu", callback_data="main_menu")],
        ])
    )
    await log(context, f"🐾 Solo adopt: {fmt_user(user)} adopt {info['emoji']} {d['pet_name']}")

async def show_adopt_partner_info(q, user, code: str, context):
    """Tampilkan info kode invite untuk ajak partner"""
    res = await sb("GET", "deliveries", {"code": f"eq.{code}", "is_delivered": "eq.false"})
    if not res:
        await q.answer("❌ Data tidak ditemukan!", show_alert=True); return
    d = res[0]
    if d["owner1_id"] != user.id:
        await q.answer("❌ Bukan adopsimu!", show_alert=True); return

    info = PETS.get(d["pet_type"], {"emoji": "🐾", "name": "?"})
    bot_name    = BOT_USERNAME.lstrip("@")
    kode_invite = d.get("kode_invite", "?")
    invite_link = f"https://t.me/{bot_name}?start={kode_invite}"

    await q.edit_message_text(
        f"🎉 Kamu mau adopsi {info['emoji']} <b>{d['pet_name']}</b>!\n\n"
        f"👫 Bagikan kode invite ke partner-mu:\n\n"
        f"🔑 Kode: <code>{kode_invite}</code>\n"
        f"🔗 Link: {invite_link}\n\n"
        f"📌 Partner bisa join dengan:\n"
        f"• Klik link di atas, <b>ATAU</b>\n"
        f"• Ketik: <code>/join {kode_invite}</code>\n\n"
        f"⏳ <b>Pengiriman dimulai setelah partner join!</b>\n"
        f"Pet tiba dalam <b>5 jam</b> atau percepat dengan <b>6 tap</b>~",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Cek Status", callback_data=f"check_{code}")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )

# ==================== PARTNER MANAGEMENT ====================
async def show_add_partner(q, user, pet_id: int):
    """Tampilkan link invite untuk tambah partner ke pet solo"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if pet.get("owner2_id"):
        await q.answer("❌ Pet sudah punya partner!", show_alert=True); return

    info = PETS.get(pet["pet_type"], {"emoji": "🐾", "name": "?"})
    bot_name = BOT_USERNAME.lstrip("@")

    # Cek apakah ada delivery add_partner yang masih valid
    existing_del = await sb("GET", "deliveries", {
        "owner1_id": f"eq.{pet.get('owner1_id')}",
        "is_delivered": "eq.false",
        "add_partner_pet_id": f"eq.{pet_id}",
    })
    if existing_del and existing_del[0].get("kode_invite"):
        d = existing_del[0]
        kode_invite = d["kode_invite"]
    else:
        kode_invite = f"PET{random.randint(10000,99999)}"
        code = f"DEL{random.randint(10000,99999)}"
        await upsert_delivery({
            "code":              code,
            "owner1_id":         pet.get("owner1_id"),
            "owner1_name":       safe_html(user.first_name) or str(user.id),
            "pet_type":          pet["pet_type"],
            "pet_name":          pet["name"],
            "arrive_at":         None,
            "taps":              {},
            "tap_count":         0,
            "kode_invite":       kode_invite,
            "owner2_id":         None,
            "owner2_name":       None,
            "started":           False,
            "is_delivered":      False,
            "add_partner_pet_id": pet_id,
            "created_at":        now_wib().isoformat(),
        })

    invite_link = f"https://t.me/{bot_name}?start={kode_invite}"
    await q.edit_message_text(
        f"👫 <b>Tambah Partner</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{pet['name']}</b>\n\n"
        f"Bagikan link ini ke temanmu:\n"
        f"🔗 <code>{invite_link}</code>\n\n"
        f"Atau kode: <code>{kode_invite}</code>\n"
        f"<i>Partner ketik: <code>/join {kode_invite}</code></i>\n\n"
        f"Setelah partner join, mereka langsung bisa rawat pet!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def show_change_partner(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if not pet.get("owner2_id"):
        await q.answer("❌ Belum punya partner!", show_alert=True); return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"🔄 <b>Ganti Partner</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{pet['name']}</b>\n\n"
        f"⚠️ Partner lama akan dikeluarkan!\n💰 Biaya: <b>1.000 🪙</b>\n\nLanjutkan?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Ganti Partner", callback_data=f"pet_change_partner_confirm_{pet_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def do_change_partner(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    ok = await spend_koin(user.id, 1000, "kawin_pet")
    if not ok:
        await q.answer("❌ Koin tidak cukup! Butuh 1.000 🪙", show_alert=True); return
    old_partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    u_changer = await get_user(user.id)
    changer_name = safe_html(get_display_name(u_changer) if u_changer else str(user.id))
    if user.id == pet.get("owner1_id"):
        await update_pet(pet_id, {"owner2_id": None})
    else:
        await update_pet(pet_id, {"owner1_id": user.id, "owner2_id": None})
    _cdel(_pet_cache, pet_id)
    if old_partner_id:
        try:
            await q.bot.send_message(old_partner_id,
                f"🔄 <b>Partner Berubah!</b>\n\n"
                f"{info['emoji']} <b>{pet['name']}</b>\n\n"
                f"<b>{changer_name}</b> mengganti partner pada pet ini.\n"
                f"<i>Kamu tidak lagi menjadi partner pet tersebut.</i>",
                parse_mode=ParseMode.HTML)
        except: pass
    await show_add_partner(q, user, pet_id)

async def show_remove_partner_confirm(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if not pet.get("owner2_id"):
        await q.answer("❌ Belum punya partner!", show_alert=True); return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    u = await get_user(user.id)
    koin = u.get("koin", 0) if u else 0
    await q.edit_message_text(
        f"💔 <b>Hapus Partner</b>\n━━━━━━━━━━━━━━━\n\n{info['emoji']} <b>{pet['name']}</b>\n\n"
        f"💰 Biaya: <b>1.000 🪙</b>\n"
        f"💼 Koinmu: <b>{koin:,} 🪙</b>\n\n"
        f"Partner akan dikeluarkan. Lanjutkan?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Hapus (1.000🪙)", callback_data=f"pet_remove_partner_confirm_{pet_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def do_remove_partner(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    # Cek & kurangi 1000 koin
    ok = await spend_koin(user.id, 1000, "kawin_pet")
    if not ok:
        await q.answer("❌ Koin tidak cukup! Butuh 1.000 🪙", show_alert=True); return
    old_partner_id = pet.get("owner2_id") if user.id == pet.get("owner1_id") else pet.get("owner1_id")
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    u_remover = await get_user(user.id)
    remover_name = safe_html(get_display_name(u_remover) if u_remover else str(user.id))
    if user.id == pet.get("owner1_id"):
        await update_pet(pet_id, {"owner2_id": None})
    else:
        await update_pet(pet_id, {"owner1_id": user.id, "owner2_id": None})
    _cdel(_pet_cache, pet_id)
    if old_partner_id:
        try:
            await q.bot.send_message(old_partner_id,
                f"💔 <b>Partner Dihapus!</b>\n\n"
                f"{info['emoji']} <b>{pet['name']}</b>\n\n"
                f"<b>{remover_name}</b> menghapusmu sebagai partner pada pet ini.\n"
                f"<i>Kamu tidak lagi terdaftar sebagai partner.</i>",
                parse_mode=ParseMode.HTML)
        except: pass
    u = await get_user(user.id)
    await q.edit_message_text(
        f"✅ Partner berhasil dihapus!\n{info['emoji']} <b>{pet['name']}</b> sekarang solo~\n\n💰 Sisa: <b>{u.get('koin',0):,} 🪙</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]])
    )

# ==================== CERAI ====================
async def show_divorce_confirm(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if not pet.get("is_married"):
        await q.answer("❌ Pet belum menikah!", show_alert=True); return
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"💔 <b>Ceraikan Pet</b>\n━━━━━━━━━━━━━━━\n\n{info['emoji']} <b>{pet['name']}</b>\n\n"
        f"⚠️ Tidak bisa dibatalkan!\nYakin ingin cerai?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💔 Ya, Cerai!", callback_data=f"pet_divorce_confirm_{pet_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"select_pet_{pet_id}")],
        ])
    )

async def do_divorce(q, user, pet_id: int, context=None):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    if not pet.get("is_married"):
        await q.answer("❌ Pet belum menikah!", show_alert=True); return
    partner_pet_id = pet.get("married_to_pet_id")
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await update_pet(pet_id, {"is_married": False, "married_to_pet_id": None, "married_at": None})
    if partner_pet_id:
        await update_pet(partner_pet_id, {"is_married": False, "married_to_pet_id": None, "married_at": None})
        partner_pet = await get_pet_by_id(partner_pet_id)
        if partner_pet and context:
            for oid in filter(None, [partner_pet.get("owner1_id"), partner_pet.get("owner2_id")]):
                try:
                    await context.bot.send_message(oid,
                        f"💔 {info['emoji']} <b>{pet['name']}</b> memutuskan bercerai dari pasangannya.\n<i>Status pernikahan berakhir.</i>",
                        parse_mode=ParseMode.HTML)
                except: pass
    await q.edit_message_text(
        f"💔 <b>{pet['name']}</b> sudah bercerai.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]])
    )
    if context: await log(context, f"💔 Cerai: {info['emoji']} <b>{pet['name']}</b> owner <code>{user.id}</code>")


# ==================== DAPUR MBG ====================
async def show_mbg_kitchen(q, user):
    inv = await get_inv(user.id)
    BAHAN = {"egg":"🥚 Telur Ayam","milk":"🥛 Susu","honey":"🍯 Madu",
              "goat_milk":"🥛 Susu Kambing","rabbit_fur":"🪶 Bulu Kelinci",
              "truffle":"🍄 Trüffel","wool":"🧶 Wol"}
    # Guard: nilai inventory bisa None kalau data corrupt
    def inv_qty(k): return int(inv.get(k) or 0)
    stok_parts = [f"{lbl}: x{inv_qty(k)}" for k,lbl in BAHAN.items() if inv_qty(k) > 0]
    stok_txt = " | ".join(stok_parts) if stok_parts else "<i>Belum ada bahan. Panen dulu dari ternak~</i>"
    lines = [f"🍳 <b>Dapur MBG</b>\n━━━━━━━━━━━━━━━\n\n📦 Bahan:\n{stok_txt}\n\n<b>Resep:</b>"]
    buttons = []
    for key, recipe in MBG_KITCHEN_RECIPES.items():
        ing_txt = " + ".join(f"{v}x {BAHAN.get(k,k)}" for k,v in recipe["ingredients"].items())
        can_make = all((inv_qty(k) >= v) for k,v in recipe["ingredients"].items())
        lines.append(f"\n{'✅' if can_make else '❌'} {recipe['emoji']} <b>{recipe['name']}</b>\n   {recipe['desc']}\n   Bahan: {ing_txt}")
        if can_make:
            buttons.append([InlineKeyboardButton(f"🍳 Buat {recipe['name']}", callback_data=f"mbg_cook_{key}")])
    buttons.append([InlineKeyboardButton("🔙 Menu", callback_data="main_menu")])
    await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def do_mbg_cook(q, user, recipe_key: str):
    recipe = MBG_KITCHEN_RECIPES.get(recipe_key)
    if not recipe:
        await q.answer("❌ Resep tidak ditemukan!", show_alert=True); return
    inv = await get_inv(user.id)
    # Guard: nilai inventory bisa None kalau data corrupt
    for k, v in recipe["ingredients"].items():
        if int(inv.get(k) or 0) < v:
            await q.answer(f"❌ Bahan tidak cukup!", show_alert=True); return
    for k, v in recipe["ingredients"].items():
        inv[k] = int(inv.get(k) or 0) - v
        if inv[k] <= 0: del inv[k]
    inv[recipe_key] = int(inv.get(recipe_key) or 0) + recipe["result_qty"]
    await set_inv(user.id, inv)
    await q.edit_message_text(
        f"🍳 <b>Berhasil dibuat!</b>\n\n{recipe['emoji']} <b>{recipe['name']}</b> x{recipe['result_qty']} masuk inventori!\n\n"
        f"<i>{recipe['desc']}</i>\n\nPakai dari menu 🍽️ Kasih Makan~",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🍳 Dapur MBG", callback_data="mbg_kitchen")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )

async def do_feed_mbg(q, user, pet_id: int, mbg_type: str, context=None):
    """Kasih makan MBG — 50% chance keracunan untuk biasa, 100% untuk special"""
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    inv_key = "mbg_biasa" if mbg_type == "biasa" else "mbg_special"
    inv = await get_inv(user.id)
    if (inv.get(inv_key) or 0) <= 0:
        await q.answer("❌ Stok habis!", show_alert=True); return
    inv[inv_key] -= 1
    if inv[inv_key] <= 0: del inv[inv_key]
    await set_inv(user.id, inv)
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    if mbg_type == "special" or random.random() < 0.5:
        await update_pet(pet_id, {"hunger": 0, "health": 100, "happiness": 100, "last_decay": now_wib().isoformat()})
        result_text = (f"🌟 <b>MBG {'Special' if mbg_type=='special' else 'Biasa'} berhasil!</b>\n\n"
                       f"{info['emoji']} <b>{pet['name']}</b> makan enak~\n🍽️ Lapar 0% | ❤️ 100% | 😊 100%!")
    else:
        new_health = max(1, (pet.get("health") or 100) - 30)
        await update_pet(pet_id, {"health": new_health, "last_decay": now_wib().isoformat()})
        result_text = (f"☠️ <b>MBG Biasa backfire!</b>\n\n{info['emoji']} <b>{pet['name']}</b> keracunan!\n"
                       f"❤️ Sehat -{30} → <b>{new_health}%</b>\n<i>Obati segera!</i>")
    await q.edit_message_text(result_text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))

async def do_use_pil(q, user, pet_id: int, pil_type: str):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    inv_key = f"pil_{pil_type}"
    inv = await get_inv(user.id)
    if (inv.get(inv_key) or 0) <= 0:
        await q.answer("❌ Pil habis!", show_alert=True); return
    inv[inv_key] -= 1
    if inv[inv_key] <= 0: del inv[inv_key]
    await set_inv(user.id, inv)
    expires = (now_wib() + timedelta(days=2)).isoformat()
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    if pil_type == "anti_pup":
        await update_pet(pet_id, {"pil_anti_pup_until": expires})
        label, desc = "Pil Anti Pup 💊🚫", "tidak poop selama 2 hari!"
    elif pil_type == "mars":
        expires48 = (now_wib() + timedelta(hours=48)).isoformat()
        await update_pet(pet_id, {"pil_anti_lapar_until": expires48, "pil_anti_pup_until": expires48})
        label, desc = "Pil Mars 🔴💊", "tidak lapar & tidak poop selama 48 jam!"
        await q.edit_message_text(
            f"💊 <b>{label}</b> dipakai!\n\n{info['emoji']} <b>{pet['name']}</b> {desc}\n⏰ Aktif hingga: <b>{fmt_wib(parse_dt(expires48))}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))
        return
    elif pil_type == "gladiator":
        pet_data = await get_pet_by_id(pet_id)
        current_bonus = (pet_data.get("battle_score_bonus") or 0) if pet_data else 0
        await update_pet(pet_id, {"battle_score_bonus": current_bonus + 100})
        await q.edit_message_text(
            f"⚔️ <b>Pil Gladiator</b> dipakai!\n\n{info['emoji']} <b>{pet['name']}</b> battle score +100 permanen!\n📊 Total bonus: <b>{current_bonus + 100}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))
        return
    elif pil_type == "evolusi":
        pet_data = await get_pet_by_id(pet_id)
        old_xp = (pet_data.get("xp") or 0) if pet_data else 0
        new_xp = min(old_xp + XP_PER_LEVEL * 3, (MAX_LEVEL - 1) * XP_PER_LEVEL)
        old_lv = calc_level(old_xp); new_lv = calc_level(new_xp)
        await update_pet(pet_id, {"xp": new_xp})
        await q.edit_message_text(
            f"🌟💊 <b>Pil Evolusi</b> dipakai!\n\n{info['emoji']} <b>{pet['name']}</b> naik {new_lv - old_lv} level!\n✨ Lv.<b>{old_lv}</b> → Lv.<b>{new_lv}</b>!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))
        return
    elif pil_type == "abadi":
        expires7 = (now_wib() + timedelta(days=7)).isoformat()
        await update_pet(pet_id, {"pil_abadi_until": expires7})
        await q.edit_message_text(
            f"🧬 <b>Pil Abadi</b> dipakai!\n\n{info['emoji']} <b>{pet['name']}</b> health tidak turun selama 7 hari!\n⏰ Aktif hingga: <b>{fmt_wib(parse_dt(expires7))}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]]))
        return
    else:
        await update_pet(pet_id, {"pil_anti_lapar_until": expires})
        label, desc = "Pil Anti Lapar 💊🍽️", "hunger freeze selama 2 hari!"
    await q.edit_message_text(
        f"💊 <b>{label}</b> dipakai!\n\n{info['emoji']} <b>{pet['name']}</b> {desc}\n⏰ Aktif: <b>{fmt_wib(parse_dt(expires))}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]])
    )

async def do_buy_pil_levelup(q, user):
    u = await get_user(user.id)
    koin = u.get("koin", 0)
    if koin < PIL_LEVELUP_PRICE:
        await q.answer(f"❌ Koin tidak cukup! Butuh {PIL_LEVELUP_PRICE:,} 🪙", show_alert=True); return
    await spend_koin(user.id, PIL_LEVELUP_PRICE, "pil_levelup")
    inv = await get_inv(user.id)
    inv["pil_levelup"] = (inv.get("pil_levelup") or 0) + 1
    await set_inv(user.id, inv)
    await q.edit_message_text(
        f"🌟 <b>Pil Level Up dibeli!</b>\n\n💊 x1 masuk inventori.\nPakai dari inventori untuk naikkan 1 level pet!\n\n💰 Sisa: <b>{koin - PIL_LEVELUP_PRICE:,} 🪙</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎒 Inventori", callback_data="inventory")]])
    )

async def do_use_pil_levelup(q, user, pet_id: int):
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return
    inv = await get_inv(user.id)
    if (inv.get("pil_levelup") or 0) <= 0:
        await q.answer("❌ Pil Level Up habis!", show_alert=True); return
    inv["pil_levelup"] -= 1
    if inv["pil_levelup"] <= 0: del inv["pil_levelup"]
    await set_inv(user.id, inv)
    old_xp = pet.get("xp") or 0
    old_lv = calc_level(old_xp)
    new_xp = min(old_xp + XP_PER_LEVEL, (MAX_LEVEL - 1) * XP_PER_LEVEL)
    new_lv = calc_level(new_xp)
    await update_pet(pet_id, {"xp": new_xp})
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"💊 <b>Pil Level Up!</b>\n\n{info['emoji']} <b>{pet['name']}</b>\n✨ Lv.{old_lv} → Lv.{new_lv}!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data=f"select_pet_{pet_id}")]])
    )

# ==================== CUSTOM PET ====================
async def show_custom_pet_card(q, user):
    inv = await get_inv(user.id)
    if (inv.get("custom_pet_card") or 0) <= 0:
        await q.answer("❌ Kamu tidak punya kartu custom pet!", show_alert=True); return
    await q.edit_message_text(
        "🎨 <b>Kartu Custom Pet</b>\n━━━━━━━━━━━━━━━\n\nBuat pet sendiri!\n\n"
        "• 🏷️ Nama pet\n• 🐾 Jenis pet\n• 💬 Kepribadian\n• ⚡ Special Ability 1\n• 🌟 Special Ability 2\n\n"
        "Pet langsung solo (tambah partner nanti).",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 Buat Sekarang!", callback_data="custom_pet_start")],
            [InlineKeyboardButton("❌ Batal", callback_data="inventory")],
        ])
    )

async def start_custom_pet_flow(q, user, context):
    inv = await get_inv(user.id)
    if (inv.get("custom_pet_card") or 0) <= 0:
        await q.answer("❌ Kartu habis!", show_alert=True); return
    context.user_data["custom_pet"] = {}
    context.user_data["state"] = "CUSTOM_PET_TYPE"
    pet_buttons, row = [], []
    for k, v in PETS.items():
        if v.get("gacha_only"): continue
        row.append(InlineKeyboardButton(f"{v['emoji']} {v['name']}", callback_data=f"cpt_type_{k}"))
        if len(row) == 3: pet_buttons.append(row); row = []
    if row: pet_buttons.append(row)
    pet_buttons.append([InlineKeyboardButton("❌ Batal", callback_data="inventory")])
    await q.edit_message_text("🐾 <b>Pilih Jenis Pet</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(pet_buttons))

async def custom_pet_choose_personality(q, user, pet_type: str, context):
    context.user_data["custom_pet"]["type"] = pet_type
    context.user_data["state"] = "CUSTOM_PET_PERSONALITY"
    info = PETS.get(pet_type, {"emoji": "🐾", "name": "?"})
    buttons = [
        [InlineKeyboardButton("😒 Jutek", callback_data="cpt_pers_jutek"), InlineKeyboardButton("😄 Ceria", callback_data="cpt_pers_ceria")],
        [InlineKeyboardButton("😌 Kalem", callback_data="cpt_pers_kalem"), InlineKeyboardButton("🥺 Manja", callback_data="cpt_pers_manja")],
        [InlineKeyboardButton("😈 Iseng", callback_data="cpt_pers_iseng"), InlineKeyboardButton("😳 Tsundere", callback_data="cpt_pers_tsundere")],
        [InlineKeyboardButton("❌ Batal", callback_data="inventory")],
    ]
    await q.edit_message_text(f"💬 <b>Pilih Kepribadian</b>\nPet: {info['emoji']} {info['name']}", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def custom_pet_choose_ability1(q, user, personality: str, context):
    context.user_data["custom_pet"]["personality"] = personality
    buttons = [
        [InlineKeyboardButton("💩 Tidak Pernah Poop", callback_data="cpt_ab1_ability1_no_poop")],
        [InlineKeyboardButton("⚔️ Battle Power 2×", callback_data="cpt_ab1_ability1_battle_2x")],
        [InlineKeyboardButton("💊 Rawat Diri (Lv.5+)", callback_data="cpt_ab1_ability1_self_heal")],
        [InlineKeyboardButton("💰 Hasil Kerja 3×", callback_data="cpt_ab1_ability1_work_3x")],
        [InlineKeyboardButton("❌ Batal", callback_data="inventory")],
    ]
    await q.edit_message_text("⚡ <b>Pilih Special Ability 1</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def custom_pet_choose_ability2(q, user, ability1: str, context):
    context.user_data["custom_pet"]["ability1"] = ability1
    buttons = [
        [InlineKeyboardButton("🪙 Kumpul 100 Koin/Hari", callback_data="cpt_ab2_ability2_daily_coin")],
        [InlineKeyboardButton("🛡️ Anti Sakit", callback_data="cpt_ab2_ability2_anti_sick")],
        [InlineKeyboardButton("🍽️ Tahan Lapar", callback_data="cpt_ab2_ability2_anti_hunger")],
        [InlineKeyboardButton("❌ Batal", callback_data="inventory")],
    ]
    ab1_info = CUSTOM_PET_ABILITIES.get(ability1, {"name": ability1})
    await q.edit_message_text(f"🌟 <b>Pilih Special Ability 2</b>\nAbility 1: ⚡ {ab1_info['name']}", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def custom_pet_ask_name(q, user, ability2: str, context):
    context.user_data["custom_pet"]["ability2"] = ability2
    context.user_data["state"] = "CUSTOM_PET_NAME"
    cp = context.user_data["custom_pet"]
    info = PETS.get(cp.get("type","cat"), {"emoji":"🐾","name":"?"})
    ab1 = CUSTOM_PET_ABILITIES.get(cp.get("ability1",""), {"name":"?"})
    ab2 = CUSTOM_PET_ABILITIES.get(ability2, {"name":"?"})
    pers_labels = {"jutek":"😒 Jutek","ceria":"😄 Ceria","kalem":"😌 Kalem","manja":"🥺 Manja","iseng":"😈 Iseng","tsundere":"😳 Tsundere"}
    await q.edit_message_text(
        f"✏️ <b>Ketik nama petmu</b>\n━━━━━━━━━━━━━━━\n\n"
        f"Jenis: {info['emoji']} {info['name']}\nKepribadian: {pers_labels.get(cp.get('personality',''),'?')}\n"
        f"Ability 1: ⚡ {ab1['name']}\nAbility 2: 🌟 {ab2['name']}\n\n<i>Ketik nama (2-20 karakter):</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="inventory")]])
    )

async def do_create_custom_pet(update, user, context):
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 20:
        await update.message.reply_text("⚠️ Nama harus 2–20 karakter, coba lagi:"); return
    cp = context.user_data.get("custom_pet", {})
    inv = await get_inv(user.id)
    if (inv.get("custom_pet_card") or 0) <= 0:
        await update.message.reply_text("❌ Kartu custom pet habis!")
        context.user_data["state"] = None; return
    inv["custom_pet_card"] -= 1
    if inv["custom_pet_card"] <= 0: del inv["custom_pet_card"]
    await set_inv(user.id, inv)
    context.user_data["state"] = None
    context.user_data["custom_pet"] = {}
    pet_type = cp.get("type","cat")
    personality = cp.get("personality","ceria")
    ability1 = cp.get("ability1","")
    ability2 = cp.get("ability2","")
    special_ability = ",".join(filter(None, [ability1, ability2]))
    info = PETS.get(pet_type, {"emoji":"🐾","name":"?"})
    ab1_info = CUSTOM_PET_ABILITIES.get(ability1, {"name":"?"})
    ab2_info = CUSTOM_PET_ABILITIES.get(ability2, {"name":"?"})
    pers_labels = {"jutek":"😒 Jutek","ceria":"😄 Ceria","kalem":"😌 Kalem","manja":"🥺 Manja","iseng":"😈 Iseng","tsundere":"😳 Tsundere"}
    new_pet = await upsert_pet({
        "owner1_id": user.id, "owner2_id": None, "name": name, "pet_type": pet_type,
        "level":1,"xp":0,"hunger":30,"happiness":90,"health":100,
        "last_decay": now_wib().isoformat(), "last_played": (now_wib()-timedelta(hours=6)).isoformat(),
        "last_bath": now_wib().isoformat(), "last_poop_at": now_wib().isoformat(), "last_poop": now_wib().isoformat(),
        "poop_count":0,"wangi_until":now_wib().isoformat(),"is_sleeping":False,"is_dirty":False,"is_missing":False,
        "is_married":False,"married_at":None,"married_to_pet_id":None,"accessory":None,"accessory_name":None,"accessory_key":None,
        "soap_premium_active":False,"boarding_until":None,"expedition_until":None,"expedition_dest":None,
        "last_notif_hunger":100,"special_ability":special_ability,"custom_personality":personality,"created_at":now_wib().isoformat(),
    })
    if not new_pet:
        await update.message.reply_text("❌ Gagal membuat pet!"); return
    await update.message.reply_text(
        f"🎉 <b>Pet Custom Berhasil!</b>\n{info['emoji']} <b>{name}</b>\n"
        f"Kepribadian: {pers_labels.get(personality,'?')}\n⚡ {ab1_info['name']}\n🌟 {ab2_info['name']}\n\n"
        f"👤 Solo sekarang — tambah partner dari menu pet kapanpun!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
    )


# ==================== CHILD RECOVER ====================
async def show_child_recover(q, user, child_id: int):
    child = await get_pet_by_id(child_id)
    if not child or not child.get("is_missing"):
        await q.answer("❌ Anak tidak kabur!", show_alert=True); return
    cinfo = PETS.get(child["pet_type"], {"emoji":"🐾"})
    await q.edit_message_text(
        f"🔍 <b>Cari Anak yang Kabur</b>\n\n{cinfo['emoji']} <b>{child['name']}</b>\n\n"
        f"💰 Biaya kembalikan: <b>{CHILD_RECOVER_COST} 🪙</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💰 Bayar {CHILD_RECOVER_COST}🪙 & Pulangkan", callback_data=f"child_recover_confirm_{child_id}")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="my_pet")],
        ])
    )

async def do_child_recover(q, user, child_id: int, context=None):
    child = await get_pet_by_id(child_id)
    if not child or not child.get("is_missing"):
        await q.answer("❌ Anak sudah pulang!", show_alert=True); return
    ok = await spend_koin(user.id, CHILD_RECOVER_COST, "recover_anak")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {CHILD_RECOVER_COST} 🪙", show_alert=True); return
    now_str = now_wib().isoformat()
    await update_pet(child_id, {
        "is_missing": False, "missing_since": None,
        "hunger": 50, "happiness": 60, "health": 80,
        "last_decay": now_str, "last_allowance_request": now_str,
        "allowance_paid_p1": False, "allowance_paid_p2": False,
    })
    cinfo = PETS.get(child["pet_type"], {"emoji":"🐾"})
    await q.edit_message_text(
        f"🎊 <b>{child['name']} sudah pulang!</b>\n{cinfo['emoji']} Kembali ke keluarga~\n💰 -{CHILD_RECOVER_COST} 🪙\n\n<i>Jangan lupa bayar uang saku tepat waktu ya!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
    )


# ==================== ADMIN: CUSTOM PET EVENT ====================
async def cmd_custompetevent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CUSTOM_PET_EVENT_ACTIVE
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if not args or args[0].lower() not in ("on","off"):
        await update.message.reply_text(
            f"🎨 Custom Pet Event\nStatus: <b>{'ON 🟢' if CUSTOM_PET_EVENT_ACTIVE else 'OFF 🔴'}</b>\n\nUsage: <code>/custompetevent on|off</code>",
            parse_mode=ParseMode.HTML); return
    turning_on = (args[0].lower() == "on")
    CUSTOM_PET_EVENT_ACTIVE = turning_on
    status = "ON 🟢" if CUSTOM_PET_EVENT_ACTIVE else "OFF 🔴"

    # Kalau on, reset semua claimed biar semua user bisa dapat lagi di session ini
    if turning_on:
        try:
            await sb("PATCH", "users", {}, {"custom_pet_claimed_event": None})
        except Exception as e:
            logger.warning(f"Reset custom_pet_claimed_event gagal: {e}")
            await update.message.reply_text(f"⚠️ Event ON tapi reset claimed gagal: {e}\n(Cek kolom custom_pet_claimed_event di tabel users)", parse_mode=ParseMode.HTML)

    await update.message.reply_text(f"🎨 Custom Pet Event: <b>{status}</b>", parse_mode=ParseMode.HTML)
    await log(context, f"🎨 Custom Pet Event {'AKTIF' if CUSTOM_PET_EVENT_ACTIVE else 'NONAKTIF'} by {fmt_user(update.effective_user)}")


# ==================== ADMIN: TOPUP BONUS EVENT ====================
def _topup_bonus_amount(amount: int) -> int:
    """Hitung bonus koin berdasarkan nominal top up. Return 0 kalau bonus off."""
    if not TOPUP_BONUS_ACTIVE:
        return 0
    if amount < 5000:
        return 0
    elif amount < 10000:
        # 5k–9.999: bonus 1.000–2.000
        return random.randint(1000, 2000)
    elif amount < 20000:
        # 10k–19.999: bonus 1.500–2.500
        return random.randint(1500, 2500)
    elif amount < 30000:
        # 20k–29.999: bonus 2.000–3.000
        return random.randint(2000, 3000)
    else:
        # 30k+: bonus 4.000–5.000
        return random.randint(4000, 5000)

async def cmd_astrotopup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: on/off bonus topup Astro Paws"""
    global ASTRO_TOPUP_BONUS_ACTIVE
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        status = "ON 🟢" if ASTRO_TOPUP_BONUS_ACTIVE else "OFF 🔴"
        await update.message.reply_text(
            f"🚀 Astro Paws Topup Bonus\nStatus: <b>{status}</b>\n\n"
            f"Usage: <code>/astrotopup on|off</code>\n\n"
            f"Tabel bonus:\n"
            f"• 2k–4.999 → 2x common (×2)\n"
            f"• 5k–9.999 → 3x common (×2) + uncommon (×1)\n"
            f"• 10k–19.999 → common (×2) + 2x uncommon random\n"
            f"• 20k+ → semua item + 🐇🌙 Moon Rabbit",
            parse_mode=ParseMode.HTML); return
    ASTRO_TOPUP_BONUS_ACTIVE = (args[0].lower() == "on")
    status = "ON 🟢" if ASTRO_TOPUP_BONUS_ACTIVE else "OFF 🔴"
    await update.message.reply_text(f"🚀 Astro Topup Bonus: <b>{status}</b>", parse_mode=ParseMode.HTML)
    await log(context, f"🚀 Astro Topup Bonus {'AKTIF' if ASTRO_TOPUP_BONUS_ACTIVE else 'NONAKTIF'} by {fmt_user(update.effective_user)}")


async def cmd_topupbonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TOPUP_BONUS_ACTIVE
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        await update.message.reply_text(
            f"🎁 Topup Bonus Event\nStatus: <b>{'ON 🟢' if TOPUP_BONUS_ACTIVE else 'OFF 🔴'}</b>\n\n"
            f"Usage: <code>/topupbonus on|off</code>\n\n"
            f"Tabel bonus:\n"
            f"• 5k–9.999 → +1.000–2.000 🪙\n"
            f"• 10k–19.999 → +1.500–2.500 🪙\n"
            f"• 20k–29.999 → +2.000–3.000 🪙\n"
            f"• 30k+ → +4.000–5.000 🪙",
            parse_mode=ParseMode.HTML); return
    TOPUP_BONUS_ACTIVE = (args[0].lower() == "on")
    status = "ON 🟢" if TOPUP_BONUS_ACTIVE else "OFF 🔴"
    await update.message.reply_text(f"🎁 Topup Bonus Event: <b>{status}</b>", parse_mode=ParseMode.HTML)
    await log(context, f"🎁 Topup Bonus {'AKTIF' if TOPUP_BONUS_ACTIVE else 'NONAKTIF'} by {fmt_user(update.effective_user)}")



async def job_ability_daily_coin(context: ContextTypes.DEFAULT_TYPE):
    """Tiap hari: +100 koin ke owner pet ability2_daily_coin"""
    try:
        today = today_wib_str()
        pets = await sb_get_all("pets", {
            "select": "id,name,pet_type,owner1_id,owner2_id,special_ability,ability_daily_coin_last",
            "is_missing": "eq.false",
        })
        for pet in pets:
            if "daily_coin" not in (pet.get("special_ability") or ""): continue
            last = pet.get("ability_daily_coin_last") or ""
            if last.startswith(today): continue
            await update_pet(pet["id"], {"ability_daily_coin_last": now_wib().isoformat()})
            info = PETS.get(pet["pet_type"], {"emoji":"🐾"})
            for oid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
                await add_koin(oid, 100, "daily_coin_ability")
                try:
                    await context.bot.send_message(oid,
                        f"🪙 {info['emoji']} <b>{pet['name']}</b> kumpulkan <b>+100 🪙</b>!\n<i>Special Ability: Kumpul Koin Harian ✨</i>",
                        parse_mode=ParseMode.HTML)
                except: pass
    except Exception as e:
        logger.error(f"job_ability_daily_coin error: {e}")

async def job_ability_self_heal(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 3 jam: auto-heal untuk pet dengan self_heal ability dan lv>=5"""
    try:
        now = now_wib()
        pets = await sb_get_all("pets", {
            "select": "id,xp,health,special_ability,ability_self_heal_last",
            "is_missing": "eq.false",
        })
        for pet in pets:
            if "self_heal" not in (pet.get("special_ability") or ""): continue
            if calc_level(pet.get("xp") or 0) < 5: continue
            health = pet.get("health") or 100
            if health >= 100: continue
            last_str = pet.get("ability_self_heal_last") or ""
            if last_str and (now - parse_dt(last_str)).total_seconds() < 10800: continue
            await update_pet(pet["id"], {"health": min(100, health+10), "ability_self_heal_last": now.isoformat()})
    except Exception as e:
        logger.error(f"job_ability_self_heal error: {e}")


# ==================== GACHA BOX ====================

async def show_gacha_menu(q, user):
    u = await get_user(user.id)
    koin = u.get("koin", 0) if u else 0
    await q.edit_message_text(
        "🎰 <b>Gacha Box</b>\n━━━━━━━━━━━━━━━\n\n"
        "🎁 <b>Kotak Biasa</b> — 800 🪙\n"
        "  • 1 item eksklusif (Mega Feast, Grand Revival, Elixir, XP Booster, Parfum Mewah, Steak Petarung)\n\n"
        "💎 <b>Kotak Premium</b> — 2.000 🪙\n"
        "  • 2 item eksklusif\n"
        "  • 3–5 Steak Petarung bonus\n"
        "  • 30% chance: pet eksklusif gacha!\n"
        "  • Pet gacha: 🦊✨ Kumiho | 🪼 Ubur-ubur | 🦝 Tanuki | 🌑🐱 Void Cat\n\n"
        f"💼 Koinmu: <b>{koin} 🪙</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📦 Buka Kotak Biasa (800🪙)", callback_data="gacha_open_biasa")],
            [InlineKeyboardButton(f"💎 Buka Kotak Premium (2.000🪙)", callback_data="gacha_open_premium")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )

async def do_gacha_open(q, user, tier: str, context):
    """Buka gacha box"""
    price = GACHA_BIASA_PRICE if tier == "biasa" else GACHA_PREMIUM_PRICE
    ok = await spend_koin(user.id, price, "gacha")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup! Butuh {price:,} 🪙", show_alert=True); return

    asyncio.create_task(task_inc(user.id, "gacha_10"))
    inv = await get_inv(user.id)
    results = []

    if tier == "biasa":
        # 1 item random
        item_key = _gacha_roll_item(GACHA_BIASA_TABLE)
        inv[item_key] = (inv.get(item_key) or 0) + 1
        gi = GACHA_ITEMS[item_key]
        results.append(f"{gi['emoji']} <b>{gi['name']}</b>")

    else:  # premium
        # 2 item random
        for _ in range(2):
            item_key = _gacha_roll_item(GACHA_PREMIUM_ITEM_TABLE)
            inv[item_key] = (inv.get(item_key) or 0) + 1
            gi = GACHA_ITEMS[item_key]
            results.append(f"{gi['emoji']} <b>{gi['name']}</b>")

        # 3–5 Steak Petarung bonus
        steak_count = random.randint(3, 5)
        inv["battle_steak"] = (inv.get("battle_steak") or 0) + steak_count
        results.append(f"🥩 <b>Steak Petarung</b> x{steak_count} (bonus!)")

        # 30% chance dapat pet eksklusif
        if random.random() < 0.30:
            pet_type = random.choice(GACHA_PET_POOL_PREMIUM)
            pet_info = PETS.get(pet_type, {"emoji": "🐾", "name": "?"})

            # Cek kalau user sudah punya pet ini, skip (jangan duplikat)
            existing_pets = await get_user_pets(user.id)
            has_this_type = any(p.get("pet_type") == pet_type for p in existing_pets)

            if not has_this_type:
                # Langsung buat pet gacha, simpan kode_invite buat link partner
                gacha_kode_invite = f"PET{random.randint(10000,99999)}"
                # Buat delivery placeholder sudah delivered, hanya untuk simpan kode_invite
                gacha_del_code = f"DEL{random.randint(10000,99999)}"
                await upsert_delivery({
                    "code":         gacha_del_code,
                    "owner1_id":    user.id,
                    "owner1_name":  safe_html(user.first_name) or safe_html(user.username) or str(user.id),
                    "pet_type":     pet_type,
                    "pet_name":     pet_info["name"],
                    "arrive_at":    now_wib().isoformat(),
                    "taps":         {},
                    "tap_count":    0,
                    "kode_invite":  gacha_kode_invite,
                    "owner2_id":    None,
                    "owner2_name":  None,
                    "started":      True,
                    "is_delivered": False,  # False dulu, biar bisa di-join partner
                    "created_at":   now_wib().isoformat(),
                })
                new_gacha_pet = await upsert_pet({
                    "owner1_id": user.id, "owner2_id": None,
                    "name": pet_info["name"],
                    "pet_type": pet_type,
                    "level": 1, "xp": 0,
                    "hunger": 30, "happiness": 90, "health": 100,
                    "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
                    "last_played": (now_wib() - timedelta(hours=6)).isoformat(),
                    "last_bath": now_wib().isoformat(),
                    "last_poop_at": now_wib().isoformat(),
                    "last_poop": now_wib().isoformat(),
                    "poop_count": 0, "wangi_until": now_wib().isoformat(),
                    "is_sleeping": False, "is_dirty": False, "is_missing": False,
                    "is_married": False, "married_at": None, "married_to_pet_id": None,
                    "accessory": None, "accessory_name": None, "accessory_key": None,
                    "soap_premium_active": False,
                    "boarding_until": None, "expedition_until": None, "expedition_dest": None,
                    "last_notif_hunger": 100,
                    "special_ability": PET_DEFAULT_ABILITY.get(pet_type),
                    "created_at": now_wib().isoformat(),
                })
                context.user_data["gacha_invite_code"] = gacha_kode_invite
                results.append(f"🌟 <b>PET EKSKLUSIF!</b> {pet_info['emoji']} <b>{pet_info['name']}</b> langsung masuk ke petmu!")
            else:
                # Sudah punya, ganti jadi item bonus
                inv["battle_steak"] = (inv.get("battle_steak") or 0) + 3
                results.append(f"🥩 <b>+3 Steak Petarung</b> (pet sudah punya, diganti item)")

    await set_inv(user.id, inv)

    result_txt = "\n".join(f"  • {r}" for r in results)
    box_name = "Kotak Biasa 📦" if tier == "biasa" else "Kotak Premium 💎"

    # Kalau dapat pet eksklusif, tampilkan link invite partner
    gacha_invite_code = context.user_data.pop("gacha_invite_code", None)
    pet_note = "\n\n<i>Item sudah masuk ke inventori kamu~ 🎒</i>"
    if gacha_invite_code:
        bot_name_str = BOT_USERNAME.lstrip("@")
        invite_link  = f"https://t.me/{bot_name_str}?start={gacha_invite_code}"
        pet_note = (
            f"\n\n🌟 Pet eksklusif langsung masuk ke petmu!\n"
            f"👫 Mau rawat bareng partner? Share link ini ke teman:\n"
            f"<code>{invite_link}</code>\n"
            f"<i>Partner bisa join kapan saja~</i>"
        )

    await q.edit_message_text(
        f"🎰 <b>Gacha {box_name}!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"Kamu dapat:\n{result_txt}{pet_note}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎒 Lihat Inventori", callback_data="inventory")],
            [InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")],
            [InlineKeyboardButton("🎰 Gacha Lagi", callback_data="gacha_menu")],
        ])
    )
    await log(context, f"🎰 Gacha {tier}: {fmt_user(user)} dapat {', '.join(results)}")

async def do_use_gacha_item(q, user, item_key: str, pet_id: int, context):
    """Pakai item gacha eksklusif"""
    inv = await get_inv(user.id)
    if (inv.get(item_key) or 0) <= 0:
        await q.answer("❌ Item habis!", show_alert=True); return

    gi = GACHA_ITEMS.get(item_key)
    if not gi:
        await q.answer("❌ Item tidak dikenal!", show_alert=True); return

    # Kurangi inventory
    inv[item_key] = (inv.get(item_key) or 0) - 1
    if inv[item_key] <= 0: del inv[item_key]
    await set_inv(user.id, inv)

    result_msg = ""

    if item_key == "mega_feast":
        pets = await get_user_pets(user.id)
        count = 0
        for pet in pets:
            if not pet.get("is_missing"):
                await update_pet(pet["id"], {"hunger": 0, "last_decay": now_wib().isoformat()})
                _cdel(_pet_cache, pet["id"])
                count += 1
        result_msg = f"🍖 <b>Mega Feast!</b>\n\nSemua {count} petmu sudah dikasih makan!\nKelaparan → 0% ✅"

    elif item_key == "grand_revival":
        pets = await get_user_pets(user.id)
        count = 0
        for pet in pets:
            if not pet.get("is_missing"):
                await update_pet(pet["id"], {
                    "hunger": 0, "happiness": 100, "health": 100,
                    "last_decay": now_wib().isoformat()
                })
                _cdel(_pet_cache, pet["id"])
                count += 1
        result_msg = (
            f"🌟 <b>Grand Revival!</b>\n\n"
            f"Semua {count} petmu dipulihkan total!\n"
            f"Lapar → 0% | Senang → 100% | Sehat → 100% ✅"
        )

    elif item_key == "elixir":
        if pet_id == 0:
            pets = await get_user_pets(user.id)
            active = [p for p in pets if not p.get("is_missing")]
            if not active:
                await q.answer("❌ Tidak ada pet aktif!", show_alert=True)
                inv[item_key] = (inv.get(item_key) or 0) + 1
                await set_inv(user.id, inv)
                return
            pet = active[0]
            pet_id = pet["id"]
        pet = await get_pet_by_id(pet_id)
        if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
            await q.answer("❌ Bukan petmu!", show_alert=True)
            inv[item_key] = (inv.get(item_key) or 0) + 1
            await set_inv(user.id, inv)
            return
        await update_pet(pet_id, {"hunger": 0, "happiness": 100, "health": 100, "last_decay": now_wib().isoformat()})
        _cdel(_pet_cache, pet_id)
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        result_msg = f"💊 <b>Elixir of Life!</b>\n\n{info['emoji']} <b>{pet['name']}</b>\nHunger → 0% | Happy → 100% | HP → 100% ✅"

    elif item_key == "xp_booster":
        # Simpan flag xp_booster di user data (expired 24 jam)
        xp_boost_until = (now_wib() + timedelta(hours=24)).isoformat()
        await update_user(user.id, {"xp_boost_until": xp_boost_until})
        _cdel(_user_cache, user.id)
        result_msg = f"✨ <b>XP Booster aktif!</b>\n\nSemua XP x2 selama <b>24 jam</b>!\nBerlaku sampai: {fmt_wib(parse_dt(xp_boost_until))}"

    elif item_key == "parfum_mewah":
        if pet_id == 0:
            pets = await get_user_pets(user.id)
            active = [p for p in pets if not p.get("is_missing")]
            if not active:
                await q.answer("❌ Tidak ada pet aktif!", show_alert=True)
                inv[item_key] = (inv.get(item_key) or 0) + 1
                await set_inv(user.id, inv)
                return
            pet = active[0]
            pet_id = pet["id"]
        pet = await get_pet_by_id(pet_id)
        if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
            await q.answer("❌ Bukan petmu!", show_alert=True)
            inv[item_key] = (inv.get(item_key) or 0) + 1
            await set_inv(user.id, inv)
            return
        wangi_until = (now_wib() + timedelta(days=7)).isoformat()
        await update_pet(pet_id, {"wangi_until": wangi_until, "is_dirty": False, "last_bath": now_wib().isoformat()})
        _cdel(_pet_cache, pet_id)
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        result_msg = f"🧴 <b>Parfum Mewah!</b>\n\n{info['emoji']} <b>{pet['name']}</b> wangi selama <b>7 hari</b>! 🌸"

    elif item_key == "battle_steak":
        if pet_id == 0:
            pets = await get_user_pets(user.id)
            active = [p for p in pets if not p.get("is_missing")]
            if not active:
                await q.answer("❌ Tidak ada pet aktif!", show_alert=True)
                inv[item_key] = (inv.get(item_key) or 0) + 1
                await set_inv(user.id, inv)
                return
            pet = active[0]
            pet_id = pet["id"]
        pet = await get_pet_by_id(pet_id)
        if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
            await q.answer("❌ Bukan petmu!", show_alert=True)
            inv[item_key] = (inv.get(item_key) or 0) + 1
            await set_inv(user.id, inv)
            return
        # Tambah battle_score_bonus ke pet
        current_bonus = (pet.get("battle_score_bonus") or 0)
        new_bonus = current_bonus + 15
        await update_pet(pet_id, {"battle_score_bonus": new_bonus})
        _cdel(_pet_cache, pet_id)
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        result_msg = f"🥩 <b>Steak Petarung!</b>\n\n{info['emoji']} <b>{pet['name']}</b>\nBattle Score +15 permanen!\nTotal bonus: <b>+{new_bonus}</b> ⚔️"

    await q.edit_message_text(
        f"✅ {result_msg}\n\n<i>Item berhasil dipakai~</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")],
            [InlineKeyboardButton("🎒 Inventori", callback_data="inventory")],
        ])
    )

# ==================== THR / AMPLOP KAGET ====================
# In-memory store amplop kaget (reset saat bot restart)
_amplop_store: dict = {}  # {kid: {total, slots, sisa_slot, sisa_nominal, pesan, pengirim_id, claimers}}

async def cmd_thr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: /thr [total_koin] [jumlah_slot] [pesan_opsional]
    Buat amplop kaget — user rebut sendiri via link, tiap orang dapat koin random."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    args = context.args
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.message.reply_text(
            "🎁 <b>Buat Amplop Kaget</b>\n━━━━━━━━━━━━━━━\n\n"
            "<b>Usage:</b>\n"
            "<code>/thr [total_koin] [jumlah_slot] [pesan]</code>\n\n"
            "<b>Contoh:</b>\n"
            "• <code>/thr 10000 20 Selamat Lebaran!</code>\n"
            "  → Pool 10.000🪙 dibagi ke 20 orang pertama yang rebut\n"
            "• <code>/thr 5000 10</code>\n"
            "  → Pool 5.000🪙, 10 slot, tanpa pesan\n\n"
            "<i>Tiap orang dapat koin random dari pool — cepat-cepatan!</i> 🎁",
            parse_mode=ParseMode.HTML
        )
        return

    total = int(args[0])
    slots = int(args[1])
    pesan = " ".join(args[2:]) if len(args) > 2 else "Selamat! Dari The Carpet Shop 🐾"

    if total < 100:
        await update.message.reply_text("❌ Minimum total koin: 100 🪙"); return
    if slots < 1 or slots > 500:
        await update.message.reply_text("❌ Jumlah slot harus 1–500!"); return
    if total < slots:
        await update.message.reply_text("❌ Total koin harus lebih besar dari jumlah slot!"); return

    # Generate ID amplop
    import uuid
    kid = uuid.uuid4().hex[:10].upper()

    # Simpan ke in-memory store
    _amplop_store[kid] = {
        "total":        total,
        "slots":        slots,
        "sisa_slot":    slots,
        "sisa_nominal": total,
        "pesan":        pesan,
        "pengirim_id":  update.effective_user.id,
        "pengirim":     safe_html(update.effective_user.first_name),
        "claimers":     [],  # list of user_id yang sudah rebut
    }

    bot_name   = BOT_USERNAME.lstrip("@")
    claim_link = f"https://t.me/{bot_name}?start=AMPLOP_{kid}"

    await update.message.reply_text(
        f"🎁 <b>Amplop Kaget Dibuat!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"💰 Total pool: <b>{total:,} 🪙</b>\n"
        f"🎫 Jumlah slot: <b>{slots} orang</b>\n"
        f"💌 Pesan: <i>{safe_html(pesan)}</i>\n\n"
        f"🔗 <b>Link rebut:</b>\n<code>{claim_link}</code>\n\n"
        f"Share link ini ke group atau teman-teman!\n"
        f"<i>Siapa cepat dia dapat, tiap orang dapat random~ 🍀</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Amplop", switch_inline_query=f"amplop {kid}")],
            [InlineKeyboardButton("📊 Cek Status", callback_data=f"amplop_status_{kid}")],
        ])
    )
    await log(context, f"🎁 Amplop kaget dibuat: <b>{kid}</b> — {total:,}🪙 / {slots} slot oleh {fmt_user(update.effective_user)}")

async def handle_amplop_claim(update: Update, context: ContextTypes.DEFAULT_TYPE, kid: str):
    """User klik link amplop → rebut koin"""
    user = update.effective_user
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    amplop = _amplop_store.get(kid)
    if not amplop:
        await update.message.reply_text(
            "❌ <b>Amplop tidak ditemukan!</b>\n"
            "<i>Mungkin sudah habis atau bot restart. Minta link baru~</i>",
            parse_mode=ParseMode.HTML
        )
        return

    if user.id in amplop["claimers"]:
        await update.message.reply_text(
            "❌ <b>Kamu sudah rebut amplop ini!</b>\n"
            "<i>1 orang hanya boleh rebut 1x per amplop~</i>",
            parse_mode=ParseMode.HTML
        )
        return

    if amplop["sisa_slot"] <= 0:
        await update.message.reply_text(
            "❌ <b>Amplop sudah habis!</b>\n"
            "<i>Lebih cepat lain kali ya~ 😄</i>",
            parse_mode=ParseMode.HTML
        )
        return

    # Hitung koin yang didapat (random, sisa dibagi rata dengan sedikit variance)
    ss = amplop["sisa_slot"]
    sn = amplop["sisa_nominal"]
    if ss == 1:
        dapat = sn  # Orang terakhir dapat semua sisa
    else:
        avg = sn // ss
        min_dapat = max(1, avg // 2)
        max_dapat = min(sn - (ss - 1), avg * 2)
        dapat = random.randint(min_dapat, max(min_dapat, max_dapat))

    # Update store
    amplop["claimers"].append(user.id)
    amplop["sisa_slot"]    -= 1
    amplop["sisa_nominal"] -= dapat

    # Kasih koin
    await add_koin(user.id, dapat, "amplop")
    u = await get_user(user.id)

    # Animasi buka amplop
    msg = await update.message.reply_text("🎁")
    for frame in ["🎁 ✨", "✨🎁✨", "🎊✨🎁✨🎊"]:
        await asyncio.sleep(0.4)
        try: await msg.edit_text(frame)
        except: pass
    await asyncio.sleep(0.3)

    sisa_info = f"\n📦 Sisa: <b>{amplop['sisa_slot']}/{amplop['slots']} slot</b>" if amplop["sisa_slot"] > 0 else "\n🎉 <b>Amplop habis!</b>"
    await msg.edit_text(
        f"🎊 <b>AMPLOP TERBUKA!</b> 🎊\n━━━━━━━━━━━━━━━\n\n"
        f"Hore <b>{safe_html(user.first_name)}</b>! 🎉\n"
        f"Kamu rebut amplop dari <b>{amplop['pengirim']}</b>!\n\n"
        f"┌─────────────────────┐\n"
        f"│  🪙 <b>{dapat:,} Koin</b>  │\n"
        f"└─────────────────────┘\n\n"
        f"💌 <i>{safe_html(amplop['pesan'])}</i>\n"
        f"💼 Total koinmu: <b>{u.get('koin',0):,} 🪙</b>{sisa_info}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Cek Koin", callback_data="my_coins")],
            [InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")],
        ])
    )

    # Notif ke pembuat amplop
    try:
        await context.bot.send_message(
            amplop["pengirim_id"],
            f"🔔 <b>{safe_html(user.first_name)}</b> rebut amplop <b>{kid}</b>!\n"
            f"💰 Dapat: <b>{dapat:,} 🪙</b>\n"
            f"📦 Sisa slot: <b>{amplop['sisa_slot']}/{amplop['slots']}</b>",
            parse_mode=ParseMode.HTML
        )
    except: pass

async def show_amplop_status(q, user, kid: str):
    """Admin: lihat status amplop"""
    if user.id not in ADMIN_IDS:
        await q.answer("❌ Bukan admin!", show_alert=True); return
    amplop = _amplop_store.get(kid)
    if not amplop:
        await q.answer("❌ Amplop tidak ditemukan!", show_alert=True); return

    pct = int((amplop["slots"] - amplop["sisa_slot"]) / amplop["slots"] * 100)
    bar_filled = pct // 10
    bar_str = "█" * bar_filled + "░" * (10 - bar_filled)

    await q.edit_message_text(
        f"📊 <b>Status Amplop {kid}</b>\n━━━━━━━━━━━━━━━\n\n"
        f"💰 Total: <b>{amplop['total']:,} 🪙</b>\n"
        f"🎫 Slot: <b>{amplop['slots'] - amplop['sisa_slot']}/{amplop['slots']}</b> terisi\n"
        f"[{bar_str}] {pct}%\n"
        f"💸 Sisa nominal: <b>{amplop['sisa_nominal']:,} 🪙</b>\n\n"
        f"💌 Pesan: <i>{safe_html(amplop['pesan'])}</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"amplop_status_{kid}")],
            [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
        ])
    )


# ==================== TOP UP KOIN ====================
async def cmd_topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mulai proses top up — tanya jumlah koin"""
    context.user_data["state"] = "ASK_TOPUP_AMOUNT"
    await update.message.reply_text(
        "💳 <b>Top Up Koin</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "💡 <b>Harga:</b> Rp 1.000 = 1.000 🪙\n"
        f"📦 <b>Minimum:</b> {TOPUP_MIN:,} 🪙 (Rp {TOPUP_MIN:,})\n\n"
        "Ketik jumlah koin yang ingin kamu beli:\n"
        "<i>Contoh: 10000 → dapat 10.000 🪙 seharga Rp 10.000</i>"
        + (_aqua_topup_bonus_info() if AQUA_TOPUP_BONUS_ACTIVE else ""),
        parse_mode=ParseMode.HTML
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle foto masuk — bukti top up & ID card"""
    user  = update.effective_user
    state = context.user_data.get("state")

    if state == IDCARD_ASK_PHOTO:
        await _idcard_process_photo(update, context)
        return

    if state != "WAIT_TOPUP_PROOF":
        return  # Abaikan foto kalau bukan lagi tunggu bukti topup

    amount = context.user_data.get("topup_amount", 0)
    context.user_data["state"] = None
    context.user_data["topup_amount"] = None

    u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    display_name = get_display_name(u)
    username_str = f"@{user.username}" if user.username else f"ID: {user.id}"

    # Kirim bukti + info ke grup admin
    caption_admin = (
        f"💳 <b>Permintaan Top Up Baru!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Nama: <b>{safe_html(display_name)}</b>\n"
        f"🆔 User: {username_str}\n"
        f"🔢 ID: <code>{user.id}</code>\n"
        f"💰 Jumlah: <b>{amount:,} 🪙</b>\n"
        f"💵 Nominal: <b>Rp {amount:,}</b>"
    )

    kb_admin = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ Accept ({amount:,} 🪙)", callback_data=f"topup_accept_{user.id}_{amount}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"topup_reject_{user.id}_{amount}"),
        ]
    ])

    # Forward foto bukti ke grup admin
    photo_file = update.message.photo[-1].file_id
    try:
        await context.bot.send_photo(
            chat_id=TOPUP_GROUP,
            photo=photo_file,
            caption=caption_admin,
            parse_mode=ParseMode.HTML,
            reply_markup=kb_admin
        )
    except Exception as e:
        logger.error(f"Gagal kirim bukti topup ke grup: {e}")
        await update.message.reply_text("❌ Gagal mengirim bukti ke admin. Hubungi @carpetshelpbot ya!")
        return

    # Konfirmasi ke user
    await update.message.reply_text(
        f"✅ <b>Bukti pembayaran diterima!</b>\n\n"
        f"💰 Top up <b>{amount:,} 🪙</b> sedang diproses admin~\n"
        f"Koin akan masuk otomatis setelah dikonfirmasi. Biasanya dalam beberapa menit! 🚀",
        parse_mode=ParseMode.HTML
    )

# ==================== ASTRO PAWS ====================
# SQL (jalankan sekali di Supabase):
# create table astro_sessions (
#   id bigserial primary key,
#   scheduled_at timestamptz not null,
#   status text not null default 'open',
#   created_by bigint not null,
#   created_at timestamptz default now()
# );
# create table astro_registrations (
#   id bigserial primary key,
#   session_id bigint references astro_sessions(id),
#   user_id bigint not null,
#   pet_id bigint not null,
#   registered_at timestamptz default now(),
#   inventory jsonb default '{}',
#   active_buffs jsonb default '{}',
#   last_explore_at timestamptz,
#   cooldown_until timestamptz,
#   coins_earned int default 0,
#   explore_log jsonb default '[]',
#   unique(session_id, pet_id)
# );

_PENDING_REFS: dict = {}  # {user_id: ref_by_id} — simpan sementara selama force sub gate
ASTRO_FORCE_SUB_ENABLED = False  # True saat pendaftaran, False saat event sudah jalan
ASTRO_COST        = 1000
ASTRO_TRAVEL_MINS = 30
ASTRO_EXPLORE_MINS= 45
ASTRO_RETURN_MINS = 30
ASTRO_INV_DEFAULT = 40
ASTRO_INV_RABBIT  = 80
ASTRO_EXPLORE_COOLDOWN = 15  # detik

# ── Item permanen (masuk inv global setelah misi) ─────────────────────────────
ASTRO_PERM_ITEMS = {
    "moon_cake":    {"name": "Kue Bulan",          "emoji": "🍮", "tier": "common",     "chance": 0.35},
    "star_pudding": {"name": "Star Pudding",        "emoji": "⭐", "tier": "uncommon",   "chance": 0.20},
    "cosmic_ramen": {"name": "Cosmic Ramen",        "emoji": "🍜", "tier": "rare",       "chance": 0.10},
    "mega_moon_feast":{"name":"Mega Moon Feast",    "emoji": "🎉", "tier": "legendary",  "chance": 0.05},
    "mood_pill":    {"name": "Mood Pill",           "emoji": "💊", "tier": "common",     "chance": 0.30},
    "hunger_pill":  {"name": "Hunger Shield Pill",  "emoji": "🛡️","tier": "uncommon",   "chance": 0.15},
    "pil_levelup":  {"name": "Level Up Pill",       "emoji": "🌟", "tier": "rare",       "chance": 0.08},
    "anti_pill":    {"name": "Anti-Need Pill",      "emoji": "✨", "tier": "legendary",  "chance": 0.04},
    "moon_rabbit":  {"name": "Moon Rabbit",         "emoji": "🐇🌙","tier":"rare",       "chance": 0.10},
}

# ── Buff sementara (aktif selama misi) ────────────────────────────────────────
ASTRO_BUFF_ITEMS = {
    "space_guard":       {"name": "Space Guard",        "emoji": "🛡️","tier":"rare",     "chance": 0.08},
    "invisibility_cloak":{"name": "Invisibility Cloak", "emoji": "🫥", "tier":"rare",     "chance": 0.06},
    "lunar_compass":     {"name": "Lunar Compass",      "emoji": "🧭", "tier":"rare",     "chance": 0.07},
    "gravity_boots":     {"name": "Gravity Boots",      "emoji": "👢", "tier":"uncommon", "chance": 0.10},
    "speed_pill":        {"name": "Speed Pill",         "emoji": "💨", "tier":"uncommon", "chance": 0.12},
    "lucky_charm":       {"name": "Lucky Charm",        "emoji": "🍀", "tier":"rare",     "chance": 0.07},
    "decoy_bag":         {"name": "Decoy Bag",          "emoji": "🎭", "tier":"rare",     "chance": 0.06},
    "steal_boost":       {"name": "Steal Boost",        "emoji": "💥", "tier":"rare",     "chance": 0.05},
    "magnet":            {"name": "Space Magnet",       "emoji": "🧲", "tier":"legendary","chance": 0.02},
}

# ── Drop table builder ────────────────────────────────────────────────────────
def _astro_roll(buffs: dict) -> tuple:
    """Return (category, key|None).
    category: 'nothing' | 'perm' | 'buff'
    """
    mult = 2.0 if buffs.get("lucky_charm", {}).get("uses", 0) > 0 else 1.0

    # Roll item permanen
    for key, info in ASTRO_PERM_ITEMS.items():
        if random.random() < info["chance"] * mult:
            return ("perm", key)
    # Roll buff
    for key, info in ASTRO_BUFF_ITEMS.items():
        if random.random() < info["chance"] * mult:
            return ("buff", key)
    # 35% nothing
    if random.random() < 0.35:
        return ("nothing", None)
    # Fallback: common item
    return ("perm", "moon_cake")

def _astro_coin_roll() -> int:
    """30% chance dapat 20-30 coin."""
    if random.random() < 0.30:
        return random.randint(20, 30)
    return 0

# ── Helpers DB ────────────────────────────────────────────────────────────────
async def astro_get_open_session() -> dict | None:
    res = await sb("GET", "astro_sessions", {"status": "in.(open,traveling,active,returning)", "order": "scheduled_at.asc", "limit": "1"})
    return res[0] if res else None

async def astro_get_session(session_id: int) -> dict | None:
    res = await sb("GET", "astro_sessions", {"id": f"eq.{session_id}"})
    return res[0] if res else None

async def astro_get_reg(session_id: int, user_id: int) -> dict | None:
    res = await sb("GET", "astro_registrations", {"session_id": f"eq.{session_id}", "user_id": f"eq.{user_id}"})
    return res[0] if res else None

async def astro_update_reg(reg_id: int, data: dict):
    await sb("PATCH", "astro_registrations", {"id": f"eq.{reg_id}"}, data)

async def astro_get_all_regs(session_id: int) -> list:
    return await sb_get_all("astro_registrations", {"session_id": f"eq.{session_id}"}) or []

async def astro_is_locked(user_id: int) -> tuple:
    """Cek apakah user sedang locked (traveling/active/returning).
    Return (locked: bool, status: str, unlock_time: datetime|None)"""
    sess = await astro_get_open_session()
    if not sess or sess["status"] not in ("traveling", "active", "returning"):
        return (False, "", None)
    reg = await astro_get_reg(sess["id"], user_id)
    if not reg:
        return (False, "", None)
    scheduled = parse_dt(sess["scheduled_at"])
    explore_start = scheduled + timedelta(minutes=ASTRO_TRAVEL_MINS)
    explore_end   = explore_start + timedelta(minutes=ASTRO_EXPLORE_MINS)
    mission_end   = explore_end + timedelta(minutes=ASTRO_RETURN_MINS)
    now = now_wib()
    if sess["status"] == "traveling" and now < explore_start:
        return (True, "traveling", explore_start)
    if sess["status"] == "active" and now < explore_end:
        return (True, "active", mission_end)
    if sess["status"] == "returning" and now < mission_end:
        return (True, "returning", mission_end)
    return (False, "", None)

async def astro_send_lock_msg(update_or_msg, status: str, unlock_time):
    """Kirim pesan locked ke user."""
    eta = int((unlock_time - now_wib()).total_seconds() / 60)
    if status == "traveling":
        txt = (f"🚀 <b>Kamu lagi dalam perjalanan ke Bulan!</b>\n"
               f"Bot dikunci selama perjalanan.\n"
               f"🌙 Explore mulai ~{eta} menit lagi\n\n"
               f"<i>Gunakan /astropaws untuk cek status</i>")
    elif status == "active":
        txt = (f"🌙 <b>Kamu lagi di Bulan!</b>\n"
               f"Bot dikunci selama di bulan — fokus explore!\n"
               f"🛸 Balik ke bumi dalam ~{eta} menit\n\n"
               f"<i>Gunakan /explore untuk cari item!</i>")
    else:
        txt = (f"🛸 <b>Kamu lagi dalam perjalanan pulang!</b>\n"
               f"Bot dikunci sampai mendarat.\n"
               f"🏠 Tiba ~{eta} menit lagi\n\n"
               f"<i>Gunakan /astropaws untuk cek status</i>")
    msg = update_or_msg if hasattr(update_or_msg, 'reply_text') else update_or_msg.message
    await msg.reply_text(txt, parse_mode=ParseMode.HTML)

# ── /astro_create (admin) ─────────────────────────────────────────────────────
async def cmd_astro_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: <code>/astro_create YYYY-MM-DD HH:MM</code>\n"
            "Contoh: <code>/astro_create 2026-04-25 19:00</code>",
            parse_mode=ParseMode.HTML); return
    try:
        dt_str = f"{args[0]} {args[1]}"
        naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        scheduled = WIB.localize(naive)
    except Exception:
        await update.message.reply_text("❌ Format tanggal/jam salah. Pakai: <code>YYYY-MM-DD HH:MM</code>", parse_mode=ParseMode.HTML); return

    # Cek tidak ada session aktif
    existing = await astro_get_open_session()
    if existing:
        await update.message.reply_text(
            f"❌ Masih ada sesi aktif (ID {existing['id']}, status {existing['status']}).\n"
            f"Tutup dulu dengan /astro_close.", parse_mode=ParseMode.HTML); return

    res = await sb("POST", "astro_sessions", {}, {
        "scheduled_at": scheduled.isoformat(),
        "status": "open",
        "created_by": update.effective_user.id
    })
    sid = res[0]["id"] if res else "?"
    await update.message.reply_text(
        f"🚀 <b>Astro Paws sesi #{sid} dibuat!</b>\n"
        f"📅 Jadwal berangkat: <b>{fmt_wib(scheduled)}</b>\n\n"
        f"Player bisa daftar sekarang via /astropaws\n"
        f"Sesi akan otomatis aktif di jadwal.",
        parse_mode=ParseMode.HTML)
    await log(context, f"🚀 Astro Paws sesi #{sid} dibuat oleh {fmt_user(update.effective_user)}, jadwal {fmt_wib(scheduled)}")

# ── /astro_close (admin) ──────────────────────────────────────────────────────
async def cmd_astro_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return
    sess = await astro_get_open_session()
    if not sess:
        await update.message.reply_text("❌ Tidak ada sesi aktif."); return
    await sb("PATCH", "astro_sessions", {"id": f"eq.{sess['id']}"}, {"status": "closed"})
    # Unlock semua pet yang terdaftar
    regs = await astro_get_all_regs(sess["id"])
    for r in regs:
        await update_pet(r["pet_id"], {"boarding_until": None, "last_decay": now_wib().isoformat()})
    # Reset astro_topup_total semua user
    await sb("PATCH", "users", {}, {"astro_topup_total": 0})
    await update.message.reply_text(f"✅ Sesi #{sess['id']} ditutup paksa. {len(regs)} pet di-unlock. Total topup event direset.", parse_mode=ParseMode.HTML)

# ── /astropaws ────────────────────────────────────────────────────────────────
async def cmd_astropaws(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ASTRO_FORCE_SUB_ENABLED and not await check_force_sub(update, context):
        return
    u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    sess = await astro_get_open_session()

    if not sess:
        await update.message.reply_text(
            "🌙 <b>Astro Paws</b>\n━━━━━━━━━━━━━━━\n\n"
            "Belum ada misi yang dibuka.\nTunggu pengumuman dari admin ya~",
            parse_mode=ParseMode.HTML); return

    status = sess["status"]
    scheduled = parse_dt(sess["scheduled_at"])
    explore_start = scheduled + timedelta(minutes=ASTRO_TRAVEL_MINS)
    explore_end   = explore_start + timedelta(minutes=ASTRO_EXPLORE_MINS)
    mission_end   = explore_end + timedelta(minutes=ASTRO_RETURN_MINS)
    now = now_wib()

    # Cek apakah sudah terdaftar
    reg = await astro_get_reg(sess["id"], user.id)

    if status == "open":
        if reg:
            pet = await get_pet_by_id(reg["pet_id"])
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"}) if pet else {"emoji": "🐾"}
            pet_name = pet["name"] if pet else "?"
            await update.message.reply_text(
                f"🚀 <b>Astro Paws — Terdaftar!</b>\n━━━━━━━━━━━━━━━\n\n"
                f"✅ Kamu sudah daftar!\n"
                f"🐾 Pet: {info['emoji']} <b>{pet_name}</b>\n"
                f"📅 Berangkat: <b>{fmt_wib(scheduled)}</b>\n"
                f"🌙 Explore mulai: <b>{fmt_wib(explore_start)}</b>\n"
                f"🏠 Tiba kembali: <b>{fmt_wib(mission_end)}</b>\n\n"
                f"<i>Siapkan dirimu! 🚀</i>",
                parse_mode=ParseMode.HTML); return
        # Belum daftar — tampilkan form pilih pet
        await _astro_show_register(update, context, u, sess)

    elif status in ("traveling", "active", "returning"):
        if not reg:
            await update.message.reply_text(
                "🚀 Misi sedang berlangsung tapi kamu tidak ikut.\nTunggu sesi berikutnya ya~",
                parse_mode=ParseMode.HTML); return
        # Tampilkan status misi
        pet = await get_pet_by_id(reg["pet_id"])
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"}) if pet else {"emoji": "🐾"}
        pet_name = pet["name"] if pet else "?"
        inv = reg.get("inventory") or {}
        total_items = sum(v for v in inv.values() if isinstance(v, int))
        coins = reg.get("coins_earned", 0)
        if status == "traveling":
            eta = int((explore_start - now).total_seconds() / 60)
            phase = f"🛸 Perjalanan ke bulan... tiba dalam ~{eta} menit"
        elif status == "active":
            eta = int((explore_end - now).total_seconds() / 60)
            phase = f"🌙 Lagi explore bulan! Sisa ~{eta} menit\nGunakan /explore untuk cari item!"
        else:
            eta = int((mission_end - now).total_seconds() / 60)
            phase = f"🛸 Balik ke bumi... tiba dalam ~{eta} menit"
        await update.message.reply_text(
            f"🚀 <b>Astro Paws — Status Misi</b>\n━━━━━━━━━━━━━━━\n\n"
            f"{info['emoji']} <b>{pet_name}</b>\n{phase}\n\n"
            f"🎒 Item terkumpul: <b>{total_items}</b>\n"
            f"🪙 Koin earned: <b>{coins}</b>\n\n"
            f"<i>/astro_bag untuk lihat inventory misi</i>",
            parse_mode=ParseMode.HTML)

    elif status == "closed":
        # Tampilkan summary kalau ada reg
        if reg:
            await _astro_show_summary(update.message, reg, sess)
        else:
            await update.message.reply_text("🌙 Misi selesai! Tidak ada data untukmu di sesi ini.")

async def _astro_show_register(update, context, u, sess):
    """Tampilkan pilihan pet untuk daftar."""
    user = update.effective_user
    koin = u.get("koin", 0)
    if koin < ASTRO_COST:
        await update.message.reply_text(
            f"🚀 <b>Astro Paws</b>\n━━━━━━━━━━━━━━━\n\n"
            f"❌ Koin tidak cukup!\nBiaya daftar: <b>{ASTRO_COST:,} 🪙</b>\nKoinmu: <b>{koin:,} 🪙</b>",
            parse_mode=ParseMode.HTML); return

    pets = await get_user_pets(user.id)
    now = now_wib()
    active_pets = [p for p in pets if
        not p.get("is_missing") and
        not (p.get("boarding_until") and parse_dt(p["boarding_until"]) > now) and
        not (p.get("expedition_until") and parse_dt(p["expedition_until"]) > now) and
        not (p.get("work_until") and parse_dt(p["work_until"]) > now)
    ]
    if not active_pets:
        await update.message.reply_text(
            "❌ Tidak ada pet yang bisa didaftarkan.\n"
            "Pastikan petmu tidak sedang boarding/ekspedisi/bekerja.",
            parse_mode=ParseMode.HTML); return

    scheduled = parse_dt(sess["scheduled_at"])
    explore_start = scheduled + timedelta(minutes=ASTRO_TRAVEL_MINS)
    explore_end   = explore_start + timedelta(minutes=ASTRO_EXPLORE_MINS)
    mission_end   = explore_end + timedelta(minutes=ASTRO_RETURN_MINS)

    buttons = []
    for p in active_pets:
        info = PETS.get(p["pet_type"], {"emoji": "🐾"})
        lv = calc_level(p.get("xp", 0))
        is_rabbit = p.get("pet_type") == "moon_rabbit"
        label = f"{info['emoji']} {p['name']} Lv.{lv}" + (" 🐇🌙+80slot" if is_rabbit else "")
        buttons.append([InlineKeyboardButton(label, callback_data=f"astro_reg_{sess['id']}_{p['id']}")])
    buttons.append([InlineKeyboardButton("❌ Batal", callback_data="main_menu")])

    await update.message.reply_text(
        f"🚀 <b>Astro Paws — Daftar Misi!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"📅 Berangkat: <b>{fmt_wib(scheduled)}</b>\n"
        f"🌙 Explore: <b>{fmt_wib(explore_start)}</b> – <b>{fmt_wib(explore_end)}</b>\n"
        f"🏠 Tiba kembali: <b>{fmt_wib(mission_end)}</b>\n\n"
        f"💰 Biaya: <b>{ASTRO_COST:,} 🪙</b>\nKoinmu: <b>{koin:,} 🪙</b>\n\n"
        f"Pilih pet yang mau dibawa:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons))

# ── Callback: astro_reg_{session_id}_{pet_id} ─────────────────────────────────
async def astro_handle_register(q, user, session_id: int, pet_id: int, context):
    u = await get_user(user.id)
    koin = u.get("koin", 0)
    if koin < ASTRO_COST:
        await q.answer(f"❌ Koin tidak cukup! Butuh {ASTRO_COST:,} 🪙", show_alert=True); return

    sess = await astro_get_session(session_id)
    if not sess or sess["status"] != "open":
        await q.answer("❌ Sesi tidak tersedia atau sudah ditutup!", show_alert=True); return

    # Cek pet milik user
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
        await q.answer("❌ Bukan petmu!", show_alert=True); return

    # Cek pet belum terdaftar di sesi ini (bisa oleh partner)
    existing = await sb("GET", "astro_registrations", {"session_id": f"eq.{session_id}", "pet_id": f"eq.{pet_id}"})
    if existing:
        # Siapa yang daftar duluan?
        first_uid = existing[0]["user_id"]
        first_u = await get_user(first_uid)
        first_name = get_display_name(first_u) if first_u else str(first_uid)
        await q.answer(f"❌ Pet ini sudah didaftarkan oleh {first_name}!", show_alert=True); return

    # Cek user belum daftar di sesi ini
    my_reg = await astro_get_reg(session_id, user.id)
    if my_reg:
        await q.answer("❌ Kamu sudah terdaftar di sesi ini!", show_alert=True); return

    # Bayar & daftarkan
    ok = await spend_koin(user.id, ASTRO_COST, "astro_daftar")
    if not ok:
        await q.answer(f"❌ Koin tidak cukup!", show_alert=True); return

    # Lock pet: pakai boarding_until = mission_end supaya semua guard aktif
    scheduled = parse_dt(sess["scheduled_at"])
    mission_end = scheduled + timedelta(minutes=ASTRO_TRAVEL_MINS + ASTRO_EXPLORE_MINS + ASTRO_RETURN_MINS)
    await update_pet(pet_id, {"boarding_until": mission_end.isoformat()})

    await sb("POST", "astro_registrations", {}, {
        "session_id": session_id,
        "user_id":    user.id,
        "pet_id":     pet_id,
        "inventory":  {},
        "active_buffs": {},
        "coins_earned": 0,
        "explore_log": [],
    })

    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    await q.edit_message_text(
        f"✅ <b>Terdaftar di Astro Paws!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{pet['name']}</b> siap ke bulan!\n"
        f"📅 Berangkat: <b>{fmt_wib(scheduled)}</b>\n\n"
        f"<i>Tunggu notif saat misi dimulai~ 🚀</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]]))
    await log(context, f"🚀 Astro Paws reg: {fmt_user(user)} → {info['emoji']} {pet['name']} sesi #{session_id}")

# ── /explore ─────────────────────────────────────────────────────────────────
async def cmd_explore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ASTRO_FORCE_SUB_ENABLED and not await check_force_sub(update, context):
        return
    u = await get_user(user.id)
    sess = await astro_get_open_session()
    if not sess or sess["status"] != "active":
        await update.message.reply_text("🌙 Tidak ada misi aktif saat ini. Tunggu jadwal Astro Paws berikutnya~"); return

    reg = await astro_get_reg(sess["id"], user.id)
    if not reg:
        await update.message.reply_text("❌ Kamu tidak terdaftar di misi ini."); return

    now = now_wib()
    cooldown_until = reg.get("cooldown_until")
    pet = await get_pet_by_id(reg["pet_id"])
    info = PETS.get(pet["pet_type"], {"emoji": "🐾"}) if pet else {"emoji": "🐾"}
    pet_name = pet["name"] if pet else "?"

    # Cek cooldown
    if cooldown_until:
        cd_dt = parse_dt(cooldown_until)
        if now < cd_dt:
            # Penalty: cooldown +15 detik
            new_cd = cd_dt + timedelta(seconds=ASTRO_EXPLORE_COOLDOWN)
            await astro_update_reg(reg["id"], {"cooldown_until": new_cd.isoformat()})
            sisa = int((new_cd - now).total_seconds())
            await update.message.reply_text(
                f"⚠️ <b>{pet_name}</b> masih jalan... kamu memaksanya berlari!\n"
                f"Dia tersandung. Cooldown +15 detik.\n"
                f"⏳ Tunggu <b>{sisa} detik</b> lagi.",
                parse_mode=ParseMode.HTML); return

    # Hitung cooldown berikutnya (cek gravity_boots / speed_pill)
    buffs = reg.get("active_buffs") or {}
    cd_secs = ASTRO_EXPLORE_COOLDOWN
    if buffs.get("gravity_boots"):
        cd_secs = 10
    if buffs.get("speed_pill", {}).get("until"):
        if parse_dt(buffs["speed_pill"]["until"]) > now:
            cd_secs = max(5, cd_secs - 8)

    new_cd = now + timedelta(seconds=cd_secs)
    inv = reg.get("inventory") or {}
    coins_earned = reg.get("coins_earned", 0)
    log_entries = reg.get("explore_log") or []
    result_lines = [f"🌙 <b>{pet_name}</b> menjelajah bulan..."]

    # ── Cek lunar_compass (guaranteed item) ────────────────────────────────
    force_item = buffs.pop("lunar_compass", None) is not None

    # ── Encounter player lain ──────────────────────────────────────────────
    encounter_msg = None
    if random.random() < 0.50:
        all_regs = await astro_get_all_regs(sess["id"])
        others = [r for r in all_regs if r["user_id"] != user.id and r["id"] != reg["id"]]
        if others:
            target_reg = random.choice(others)
            target_buffs = target_reg.get("active_buffs") or {}
            if not target_buffs.get("invisibility_cloak"):
                target_u = await get_user(target_reg["user_id"])
                target_name = get_display_name(target_u) if target_u else "Seseorang"
                target_uname = target_u.get("username") if target_u else None
                target_display = f"{safe_html(target_name)} (@{safe_html(target_uname)})" if target_uname else safe_html(target_name)
                target_pet = await get_pet_by_id(target_reg["pet_id"])
                target_pet_info = PETS.get(target_pet["pet_type"], {"emoji": "🐾"}) if target_pet else {"emoji": "🐾"}
                target_pet_name = target_pet["name"] if target_pet else "?"
                encounter_msg = (target_reg, target_display, target_pet_name, target_pet_info)
                result_lines.append(f"\n👀 Kamu bertemu <b>{target_display}</b> dan {target_pet_info['emoji']} <b>{target_pet_name}</b>!")

    # ── Roll item ──────────────────────────────────────────────────────────
    # Consume lucky_charm
    if buffs.get("lucky_charm", {}).get("uses", 0) > 0:
        buffs["lucky_charm"]["uses"] -= 1
        if buffs["lucky_charm"]["uses"] <= 0:
            del buffs["lucky_charm"]

    pet_type = (await get_pet_by_id(reg["pet_id"]) or {}).get("pet_type", "")
    inv_slots = ASTRO_INV_RABBIT if pet_type == "moon_rabbit" else ASTRO_INV_DEFAULT
    total_qty_now = sum(v for v in inv.values() if isinstance(v, int) and v > 0)
    slot_full = total_qty_now >= inv_slots

    cat, key = _astro_roll(buffs)
    if force_item and cat == "nothing":
        cat, key = "perm", "moon_cake"

    if cat == "perm" and key:
        if slot_full:
            result_lines.append(f"\n📦 Tas penuh ({total_qty_now}/{inv_slots})! Item terlewat. Hapus dulu via /remove")
        else:
            item_info = ASTRO_PERM_ITEMS[key]
            inv[key] = (inv.get(key) or 0) + 1
            result_lines.append(f"\n✨ Dapat: {item_info['emoji']} <b>{item_info['name']}</b>! (masuk tas)")
            log_entries.append({"type": "item", "key": key, "name": item_info["name"]})
    elif cat == "buff" and key:
        buff_info = ASTRO_BUFF_ITEMS[key]
        # Inisialisasi buff
        if key == "lucky_charm":
            buffs[key] = {"uses": 3}
        elif key == "speed_pill":
            buffs[key] = {"until": (now + timedelta(minutes=5)).isoformat()}
        elif key in ("space_guard", "invisibility_cloak", "decoy_bag", "steal_boost"):
            buffs[key] = {"active": True}
        elif key == "gravity_boots":
            buffs[key] = {"active": True}
        elif key == "lunar_compass":
            buffs[key] = {"active": True}
        elif key == "magnet":
            # Langsung tarik item dari player lain
            all_regs_m = await astro_get_all_regs(sess["id"])
            victims = [r for r in all_regs_m if r["user_id"] != user.id]
            stolen = None
            for v in _random_shuffle(victims):
                v_inv = v.get("inventory") or {}
                v_items = [k for k, vv in v_inv.items() if vv > 0]
                if v_items:
                    stolen_key = random.choice(v_items)
                    stolen_info = ASTRO_PERM_ITEMS.get(stolen_key, {"name": stolen_key, "emoji": "📦"})
                    v_inv[stolen_key] -= 1
                    if v_inv[stolen_key] <= 0: del v_inv[stolen_key]
                    await astro_update_reg(v["id"], {"inventory": v_inv})
                    inv[stolen_key] = (inv.get(stolen_key) or 0) + 1
                    stolen = (v, stolen_key, stolen_info)
                    break
            if stolen:
                v_reg, s_key, s_info = stolen
                result_lines.append(f"\n🧲 <b>Space Magnet!</b> Menarik {s_info['emoji']} {s_info['name']} dari seseorang!")
                try:
                    v_u = await get_user(v_reg["user_id"])
                    v_name = get_display_name(v_u) if v_u else "Seseorang"
                    await context.bot.send_message(v_reg["user_id"],
                        f"🧲 <b>Space Magnet!</b> {info['emoji']} {pet_name} mencuri "
                        f"{s_info['emoji']} {s_info['name']} kamu dengan magnet!\n"
                        f"(oleh {safe_html(get_display_name(u))})",
                        parse_mode=ParseMode.HTML)
                except: pass
            else:
                result_lines.append(f"\n🧲 Space Magnet aktif tapi tidak ada yang bisa ditarik.")
        result_lines.append(f"\n🎯 Buff aktif: {buff_info['emoji']} <b>{buff_info['name']}</b>!")
        log_entries.append({"type": "buff", "key": key, "name": buff_info["name"]})
    else:
        result_lines.append("\n🌑 Tidak menemukan apa-apa kali ini...")

    # ── Coin roll ──────────────────────────────────────────────────────────
    coin_gain = _astro_coin_roll()
    if coin_gain > 0:
        coins_earned += coin_gain
        await add_koin(user.id, coin_gain, "astro_explore")
        result_lines.append(f"\n🪙 +{coin_gain} koin!")

    # ── Random event (5%) ──────────────────────────────────────────────────
    if random.random() < 0.05:
        ev = random.choice(["meteor", "alien"])
        items_keys = [k for k, v in inv.items() if isinstance(v, int) and v > 0]
        if ev == "meteor" and items_keys:
            lost = random.sample(items_keys, min(random.randint(1, 3), len(items_keys)))
            for lk in lost:
                inv[lk] = max(0, inv.get(lk, 1) - 1)
                if inv[lk] <= 0: del inv[lk]
            result_lines.append(f"\n☄️ <b>Meteor Shower!</b> {len(lost)} item hilang dari tas!")
            log_entries.append({"type": "event", "name": "meteor", "lost": lost})
        elif ev == "alien" and items_keys:
            if random.random() < 0.50:
                stolen_key = random.choice(items_keys)
                inv[stolen_key] = max(0, inv.get(stolen_key, 1) - 1)
                if inv[stolen_key] <= 0: del inv[stolen_key]
                s_info = ASTRO_PERM_ITEMS.get(stolen_key, {"name": stolen_key, "emoji": "📦"})
                result_lines.append(f"\n👽 <b>Alien Encounter!</b> Alien mengambil {s_info['emoji']} {s_info['name']}!")
                log_entries.append({"type": "event", "name": "alien", "lost": [stolen_key]})
            else:
                result_lines.append("\n👽 <b>Alien Encounter!</b> Alien lewat... kamu selamat!")

    # ── Simpan state ───────────────────────────────────────────────────────
    await astro_update_reg(reg["id"], {
        "inventory":      inv,
        "active_buffs":   buffs,
        "coins_earned":   coins_earned,
        "last_explore_at": now.isoformat(),
        "cooldown_until": new_cd.isoformat(),
        "explore_log":    log_entries[-40:],  # max 50 entries
    })

    total = sum(v for v in inv.values() if isinstance(v, int))
    result_lines.append(f"\n\n🎒 Tas: <b>{total} item</b> | 🪙 Total coin: <b>{coins_earned}</b>")
    result_lines.append(f"\n⏳ Explore lagi dalam <b>{cd_secs} detik</b>")

    # Kirim result + tombol encounter kalau ada
    kb = None
    if encounter_msg:
        t_reg, t_name, t_pet_name, t_pet_info = encounter_msg
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("😈 Steal", callback_data=f"astro_steal_{sess['id']}_{t_reg['id']}"),
             InlineKeyboardButton("➡️ Skip",  callback_data="astro_skip")],
        ])

    await update.message.reply_text(
        "\n".join(result_lines), parse_mode=ParseMode.HTML, reply_markup=kb)

def _random_shuffle(lst):
    import random as r
    lst2 = list(lst)
    r.shuffle(lst2)
    return lst2

# ── /astro_bag ────────────────────────────────────────────────────────────────
async def cmd_astro_bag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sess = await astro_get_open_session()
    if not sess or sess["status"] not in ("active", "traveling", "returning"):
        await update.message.reply_text("🌙 Tidak ada misi aktif."); return
    reg = await astro_get_reg(sess["id"], user.id)
    if not reg:
        await update.message.reply_text("❌ Kamu tidak terdaftar di misi ini."); return

    inv = reg.get("inventory") or {}
    buffs = reg.get("active_buffs") or {}
    items = [(k, v) for k, v in inv.items() if isinstance(v, int) and v > 0]

    lines = ["🎒 <b>Astro Bag</b>\n━━━━━━━━━━━━━━━\n"]
    if items:
        for k, v in items:
            info = ASTRO_PERM_ITEMS.get(k, {"name": k, "emoji": "📦"})
            lines.append(f"{info['emoji']} {info['name']}: <b>x{v}</b>")
    else:
        lines.append("<i>Belum dapat item apapun~</i>")

    if buffs:
        lines.append("\n🌀 <b>Buff Aktif:</b>")
        for bk, bv in buffs.items():
            bi = ASTRO_BUFF_ITEMS.get(bk, {"name": bk, "emoji": "✨"})
            lines.append(f"{bi['emoji']} {bi['name']}")

    lines.append(f"\n🪙 Koin earned: <b>{reg.get('coins_earned', 0)}</b>")
    inv_slots = ASTRO_INV_RABBIT if (await get_pet_by_id(reg["pet_id"]) or {}).get("pet_type") == "moon_rabbit" else ASTRO_INV_DEFAULT
    total_qty = sum(v for _, v in items)
    lines.append(f"📦 Slot: <b>{total_qty}/{inv_slots}</b>")
    lines.append(f"\n<i>Hapus item: /remove nama_item jumlah\nContoh: /remove moon_cake 2</i>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ── /astro2_list (admin) dengan pagination ───────────────────────────────────
ASTRO2_LIST_PAGE_SIZE = 10

async def cmd_astro2_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return
    page = int(context.args[0]) if context.args else 1
    await _send_astro2_list(update.message, page, context)

async def _send_astro2_list(msg, page: int, context, edit=False):
    sess = await a2_get_open_session()
    if not sess:
        text = "❌ Tidak ada sesi Mars aktif."
        if edit: await msg.edit_text(text)
        else: await msg.reply_text(text)
        return

    regs = await a2_get_all_regs(sess["id"])
    if not regs:
        text = "👥 Belum ada peserta."
        if edit: await msg.edit_text(text)
        else: await msg.reply_text(text)
        return

    total = len(regs)
    total_pages = max(1, (total + ASTRO2_LIST_PAGE_SIZE - 1) // ASTRO2_LIST_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ASTRO2_LIST_PAGE_SIZE
    page_regs = regs[start:start + ASTRO2_LIST_PAGE_SIZE]

    lines = [
        f"👥 <b>Peserta Astro Paws 2 — Mars</b> (sesi #{sess['id']})",
        f"Halaman <b>{page}/{total_pages}</b> — Total <b>{total}</b> peserta",
        "━━━━━━━━━━━━━━━",
        "",
    ]

    for i, r in enumerate(page_regs, start=start+1):
        u_data = await sb("GET", "users", {"user_id": f"eq.{r['user_id']}"})
        u_info = u_data[0] if u_data else {}
        nama = safe_html(u_info.get("nama") or str(r["user_id"]))
        uname = u_info.get("username")
        uname_txt = f" @{safe_html(uname)}" if uname else ""
        pet_data = await get_pet_by_id(r["pet_id"])
        pet_info = PETS.get((pet_data or {}).get("pet_type", ""), {"emoji": "🐾"})
        pet_name = pet_data.get("name", "?") if pet_data else "?"
        inv_r = r.get("inventory") or {}
        item_count = sum(v for v in inv_r.values() if isinstance(v, int) and v > 0)
        coins = r.get("coins_earned", 0) or 0
        explore_count = len(r.get("explore_log") or [])
        scorpion = "🦂" if r.get("scorpion_caught") else ""
        lines.append(f"{i}. <b>{nama}</b>{uname_txt} {scorpion}")
        lines.append(f"   {pet_info['emoji']} {pet_name} | 📦{item_count} item | 🪙{coins:,} | 🔍{explore_count}x explore")

    text = "\n".join(lines)
    buttons = []
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"a2_list_{page-1}"))
    if page < total_pages: nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"a2_list_{page+1}"))
    if nav: buttons.append(nav)
    kb = InlineKeyboardMarkup(buttons) if buttons else None

    if edit: await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else: await msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ── /astro2_stats (admin) ─────────────────────────────────────────────────────
async def cmd_astro2_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return

    sess = await a2_get_open_session()

    all_users = await sb_get_all("users", {"astro2_topup_total": "gt.0", "order": "astro2_topup_total.desc"}) or []

    tier_count = {"legendary": 0, "rare": 0, "uncommon": 0, "common": 0}
    total_topup = 0
    for u in all_users:
        t = u.get("astro2_topup_total", 0) or 0
        total_topup += t
        tier_count[_astro_tier(t)] += 1

    lines = ["🔴 <b>ASTRO PAWS 2 — STATS</b>\n━━━━━━━━━━━━━━━━━━━━\n"]

    if sess:
        status_label = {
            "open":      "🟢 Open (daftar)",
            "traveling": "🚀 Traveling ke Mars",
            "active":    "🔴 Exploring Mars",
            "returning": "🔄 Returning",
        }.get(sess["status"], sess["status"])
        scheduled = parse_dt(sess["scheduled_at"])
        lines.append(f"📡 <b>Sesi #{sess['id']}</b> — {status_label}")
        lines.append(f"📅 Jadwal: <b>{fmt_wib(scheduled)}</b>")

        regs = await a2_get_all_regs(sess["id"])
        lines.append(f"👥 Peserta terdaftar: <b>{len(regs)}</b>")
        scorpion_count = sum(1 for r in regs if r.get("scorpion_caught"))
        lines.append(f"🦂 Scorpion tertangkap: <b>{scorpion_count}</b>\n")

        if regs:
            total_items_all = 0
            total_coins_all = 0
            for r in regs:
                inv_r = r.get("inventory") or {}
                total_items_all += sum(v for v in inv_r.values() if isinstance(v, int) and v > 0)
                total_coins_all += r.get("coins_earned", 0) or 0
            lines.append(f"📦 Total item terkumpul: <b>{total_items_all}</b>")
            lines.append(f"🪙 Total koin earned: <b>{total_coins_all:,}</b>")
            lines.append(f"\n<i>Ketik /astro2_list untuk lihat detail tiap peserta</i>")
        lines.append("")
    else:
        lines.append("📡 <i>Tidak ada sesi aktif saat ini.</i>\n")

    lines.append("💰 <b>Topup Event (Global):</b>")
    lines.append(f"  Total partisipan: <b>{len(all_users)}</b>")
    lines.append(f"  Total topup: <b>{total_topup:,} koin</b>")
    lines.append(f"  🟡 Legendary (20k+): <b>{tier_count['legendary']}</b>")
    lines.append(f"  🔴 Rare     (10k+): <b>{tier_count['rare']}</b>")
    lines.append(f"  🔵 Uncommon  (5k+): <b>{tier_count['uncommon']}</b>")
    lines.append(f"  ⚪ Common    (2k+): <b>{tier_count['common']}</b>")

    if all_users:
        lines.append("\n🏆 <b>Top 5 Topup:</b>")
        for u in all_users[:5]:
            nama = safe_html(u.get("nama") or str(u.get("user_id", "?")))
            uname = u.get("username")
            uname_txt = f" @{safe_html(uname)}" if uname else ""
            topup = u.get("astro2_topup_total", 0) or 0
            lines.append(f"  • <b>{nama}</b>{uname_txt} — {topup:,} koin")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ── /astro_list (admin) dengan pagination ────────────────────────────────────
ASTRO_LIST_PAGE_SIZE = 10

async def cmd_astro_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return
    page = int(context.args[0]) if context.args else 1
    await _send_astro_list(update.message, page, context)

async def _send_astro_list(msg, page: int, context, edit=False):
    sess = await astro_get_open_session()
    if not sess:
        text = "❌ Tidak ada sesi aktif."; 
        if edit: await msg.edit_text(text)
        else: await msg.reply_text(text)
        return

    regs = await astro_get_all_regs(sess["id"])
    if not regs:
        text = "👥 Belum ada peserta."
        if edit: await msg.edit_text(text)
        else: await msg.reply_text(text)
        return

    total = len(regs)
    total_pages = max(1, (total + ASTRO_LIST_PAGE_SIZE - 1) // ASTRO_LIST_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * ASTRO_LIST_PAGE_SIZE
    page_regs = regs[start:start + ASTRO_LIST_PAGE_SIZE]

    lines = [
        f"👥 <b>Peserta Astro Paws</b> (sesi #{sess['id']})",
        f"Halaman <b>{page}/{total_pages}</b> — Total <b>{total}</b> peserta",
        "━━━━━━━━━━━━━━━",
        "",
    ]

    for i, r in enumerate(page_regs, start=start+1):
        u_data = await sb("GET", "users", {"user_id": f"eq.{r['user_id']}"})
        u_info = u_data[0] if u_data else {}
        nama = safe_html(u_info.get("nama") or str(r["user_id"]))
        uname = u_info.get("username")
        uname_txt = f" @{safe_html(uname)}" if uname else ""
        pet_data = await get_pet_by_id(r["pet_id"])
        pet_info = PETS.get((pet_data or {}).get("pet_type", ""), {"emoji": "🐾"})
        pet_name = pet_data.get("name", "?") if pet_data else "?"
        inv_r = r.get("inventory") or {}
        item_count = sum(v for v in inv_r.values() if isinstance(v, int) and v > 0)
        coins = r.get("coins_earned", 0) or 0
        explore_count = len(r.get("explore_log") or [])
        lines.append(f"{i}. <b>{nama}</b>{uname_txt}")
        lines.append(f"   {pet_info['emoji']} {pet_name} | 📦{item_count} item | 🪙{coins:,} | 🔍{explore_count}x explore")

    text = "\n".join(lines)
    buttons = []
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"astro_list_{page-1}"))
    if page < total_pages: nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"astro_list_{page+1}"))
    if nav: buttons.append(nav)
    kb = InlineKeyboardMarkup(buttons) if buttons else None

    if edit: await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else: await msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ── /astro_stats (admin) ─────────────────────────────────────────────────────
async def cmd_astro_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return

    sess = await astro_get_open_session()

    # ── Stats user (dari kolom astro_topup_total) ──────────────────────────
    all_users = await sb_get_all("users", {"astro_topup_total": "gt.0", "order": "astro_topup_total.desc"}) or []

    tier_count = {"legendary": 0, "rare": 0, "uncommon": 0, "common": 0}
    total_topup = 0
    for u in all_users:
        t = u.get("astro_topup_total", 0) or 0
        total_topup += t
        tier_count[_astro_tier(t)] += 1

    lines = ["🌙 <b>ASTRO PAWS — STATS</b>\n━━━━━━━━━━━━━━━━━━━━\n"]

    # ── Info sesi aktif ────────────────────────────────────────────────────
    if sess:
        status_label = {
            "open":      "🟢 Open (daftar)",
            "traveling": "🚀 Traveling",
            "active":    "🌑 Exploring",
            "returning": "🔄 Returning",
        }.get(sess["status"], sess["status"])
        scheduled = parse_dt(sess["scheduled_at"])
        lines.append(f"📡 <b>Sesi #{sess['id']}</b> — {status_label}")
        lines.append(f"📅 Jadwal: <b>{fmt_wib(scheduled)}</b>")

        regs = await astro_get_all_regs(sess["id"])
        lines.append(f"👥 Peserta terdaftar: <b>{len(regs)}</b>\n")

        if regs:
            total_items_all = 0
            total_coins_all = 0
            for r in regs:
                inv_r = r.get("inventory") or {}
                total_items_all += sum(v for v in inv_r.values() if isinstance(v, int) and v > 0)
                total_coins_all += r.get("coins_earned", 0) or 0
            lines.append(f"📦 Total item terkumpul: <b>{total_items_all}</b>")
            lines.append(f"🪙 Total koin earned: <b>{total_coins_all:,}</b>")
            lines.append(f"\n<i>Ketik /astro_list untuk lihat detail tiap peserta</i>")
        lines.append("")
    else:
        lines.append("📡 <i>Tidak ada sesi aktif saat ini.</i>\n")

    # ── Stats topup global ────────────────────────────────────────────────
    lines.append("💰 <b>Topup Event (Global):</b>")
    lines.append(f"  Total partisipan: <b>{len(all_users)}</b>")
    lines.append(f"  Total topup: <b>{total_topup:,} koin</b>")
    lines.append(f"  🟡 Legendary (20k+): <b>{tier_count['legendary']}</b>")
    lines.append(f"  🔴 Rare     (10k+): <b>{tier_count['rare']}</b>")
    lines.append(f"  🔵 Uncommon  (5k+): <b>{tier_count['uncommon']}</b>")
    lines.append(f"  ⚪ Common    (2k+): <b>{tier_count['common']}</b>")

    if all_users:
        lines.append("\n🏆 <b>Top 5 Topup:</b>")
        for u in all_users[:5]:
            nama = safe_html(u.get("nama") or str(u.get("user_id", "?")))
            uname = u.get("username")
            uname_txt = f" @{safe_html(uname)}" if uname else ""
            topup = u.get("astro_topup_total", 0) or 0
            lines.append(f"  • <b>{nama}</b>{uname_txt} — {topup:,} koin")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ── /remove item_key jumlah ───────────────────────────────────────────────────
async def cmd_astro_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: <code>/remove moon_cake 2</code>", parse_mode=ParseMode.HTML); return
    item_key = args[0].lower().replace(" ", "_")
    # Alias: nama Indonesia / tanpa underscore → key internal
    _ASTRO_ALIASES = {
        "kue_bulan":       "moon_cake",
        "kuebulan":        "moon_cake",
        "starpudding":     "star_pudding",
        "cosmicramen":     "cosmic_ramen",
        "megamoonfeast":   "mega_moon_feast",
        "moodpill":        "mood_pill",
        "hungerpill":      "hunger_pill",
        "antipill":        "anti_pill",
        "moonrabbit":      "moon_rabbit",
        "pillevelup":      "pil_levelup",
        "pil_level_up":    "pil_levelup",
        "leveluppill":     "pil_levelup",
    }
    item_key = _ASTRO_ALIASES.get(item_key, item_key)
    try:
        qty = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus angka."); return

    sess = await astro_get_open_session()
    if not sess or sess["status"] not in ("active",):
        await update.message.reply_text("❌ Hanya bisa hapus item saat misi aktif."); return
    reg = await astro_get_reg(sess["id"], user.id)
    if not reg:
        await update.message.reply_text("❌ Kamu tidak terdaftar."); return

    inv = reg.get("inventory") or {}
    have = inv.get(item_key, 0)
    if have <= 0:
        # Kasih hint item apa yang ada di tas
        available = [k for k, v in inv.items() if isinstance(v, int) and v > 0]
        hint = f"\nItem di tasmu: {', '.join(available)}" if available else ""
        await update.message.reply_text(f"❌ Tidak punya <code>{item_key}</code> di tas misi.{hint}", parse_mode=ParseMode.HTML); return
    remove_qty = min(qty, have)
    inv[item_key] -= remove_qty
    if inv[item_key] <= 0: del inv[item_key]
    await astro_update_reg(reg["id"], {"inventory": inv})
    info = ASTRO_PERM_ITEMS.get(item_key, {"name": item_key, "emoji": "📦"})
    await update.message.reply_text(f"🗑️ {info['emoji']} {info['name']} x{remove_qty} dihapus dari tas misi.")

# ── Callback: steal ───────────────────────────────────────────────────────────
_ASTRO_STEAL_LOCK: set = set()

async def astro_handle_steal(q, user, session_id: int, target_reg_id: int, context):
    lock_key = (user.id, target_reg_id)
    if lock_key in _ASTRO_STEAL_LOCK:
        await q.answer("⏳ Sabar, lagi diproses...", show_alert=False); return
    _ASTRO_STEAL_LOCK.add(lock_key)
    try:
        sess = await astro_get_session(session_id)
        if not sess or sess["status"] != "active":
            await q.answer("❌ Misi sudah tidak aktif!", show_alert=True); return
    
        my_reg = await astro_get_reg(session_id, user.id)
        if not my_reg:
            await q.answer("❌ Kamu tidak terdaftar!", show_alert=True); return
    
        # Fetch target
        target_res = await sb("GET", "astro_registrations", {"id": f"eq.{target_reg_id}"})
        if not target_res:
            await q.answer("❌ Target tidak ditemukan!", show_alert=True); return
        t_reg = target_res[0]
    
        t_inv   = t_reg.get("inventory") or {}
        t_buffs = t_reg.get("active_buffs") or {}
        my_buffs = my_reg.get("active_buffs") or {}
        my_inv   = my_reg.get("inventory") or {}
    
        t_items = [k for k, v in t_inv.items() if isinstance(v, int) and v > 0]
        if not t_items:
            await q.edit_message_text("😅 Target tidak punya item apa-apa!", parse_mode=ParseMode.HTML); return
    
        # Cek space_guard
        if t_buffs.get("space_guard"):
            del t_buffs["space_guard"]
            await astro_update_reg(t_reg["id"], {"active_buffs": t_buffs})
            t_u = await get_user(t_reg["user_id"])
            t_name = get_display_name(t_u) if t_u else "Korban"
            try:
                await context.bot.send_message(t_reg["user_id"],
                    f"🛡️ <b>Space Guard</b> aktif! Steal dari {safe_html(get_display_name(await get_user(user.id)))} berhasil diblok!\nGuard habis.",
                    parse_mode=ParseMode.HTML)
            except: pass
            await q.edit_message_text("🛡️ Gagal! Target punya <b>Space Guard</b> — steal diblok. Guard-nya hangus.", parse_mode=ParseMode.HTML); return
    
        # Cek decoy_bag
        if t_buffs.get("decoy_bag"):
            del t_buffs["decoy_bag"]
            await astro_update_reg(t_reg["id"], {"active_buffs": t_buffs})
            await q.edit_message_text("🎭 Kamu dapat item dari tasnya... tapi itu <b>Decoy Bag</b>! Isinya kosong.\nKorban aman.", parse_mode=ParseMode.HTML); return
    
        # Roll steal chance
        steal_chance = 0.90 if my_buffs.get("steal_boost") else 0.60
        if my_buffs.get("steal_boost"):
            del my_buffs["steal_boost"]
            await astro_update_reg(my_reg["id"], {"active_buffs": my_buffs})
    
        if random.random() > steal_chance:
            await q.edit_message_text("😅 Gagal mencuri... kamu kepergok!", parse_mode=ParseMode.HTML); return
    
        # Berhasil steal
        stolen_key = random.choice(t_items)
        stolen_info = ASTRO_PERM_ITEMS.get(stolen_key, {"name": stolen_key, "emoji": "📦"})
        t_inv[stolen_key] -= 1
        if t_inv[stolen_key] <= 0: del t_inv[stolen_key]
        my_inv[stolen_key] = (my_inv.get(stolen_key) or 0) + 1
    
        await astro_update_reg(t_reg["id"], {"inventory": t_inv})
        await astro_update_reg(my_reg["id"], {"inventory": my_inv})
    
        u = await get_user(user.id)
        my_name = get_display_name(u)
        try:
            u_username = (await get_user(user.id) or {}).get("username") or ""
            username_str = f" (@{safe_html(u_username)})" if u_username else ""
            await context.bot.send_message(t_reg["user_id"],
                f"⚠️ <b>{safe_html(my_name)}</b>{username_str} mencuri {stolen_info['emoji']} <b>{stolen_info['name']}</b> dari tasmu saat misi!",
                parse_mode=ParseMode.HTML)
        except: pass
    
        await q.edit_message_text(
            f"😈 Berhasil! Kamu mencuri {stolen_info['emoji']} <b>{stolen_info['name']}</b>!\nMasuk ke tas misimu.",
            parse_mode=ParseMode.HTML)
    
    finally:
        _ASTRO_STEAL_LOCK.discard(lock_key)
# ── Job: cek & ubah status sesi ───────────────────────────────────────────────
async def job_astro_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap 60 detik: update status sesi Astro Paws & kirim notif."""
    sess = await astro_get_open_session()
    if not sess:
        return

    now = now_wib()
    scheduled    = parse_dt(sess["scheduled_at"])
    explore_start = scheduled + timedelta(minutes=ASTRO_TRAVEL_MINS)
    explore_end   = explore_start + timedelta(minutes=ASTRO_EXPLORE_MINS)
    mission_end   = explore_end + timedelta(minutes=ASTRO_RETURN_MINS)
    status = sess["status"]

    # open → traveling
    if status == "open" and now >= scheduled:
        await sb("PATCH", "astro_sessions", {"id": f"eq.{sess['id']}"}, {"status": "traveling"})
        regs = await astro_get_all_regs(sess["id"])
        for r in regs:
            pet = await get_pet_by_id(r["pet_id"])
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"}) if pet else {"emoji": "🐾"}
            try:
                await context.bot.send_message(r["user_id"],
                    f"🚀 <b>Astro Paws dimulai!</b>\n"
                    f"{info['emoji']} <b>{pet['name']}</b> sedang dalam perjalanan ke bulan...\n"
                    f"🌙 Explore mulai pukul <b>{fmt_wib(explore_start)}</b>\n\n"
                    f"<i>Sementara ini mini app dikunci ya~</i>",
                    parse_mode=ParseMode.HTML)
            except: pass
        logger.info(f"Astro Paws #{sess['id']}: open → traveling")

    # traveling → active
    elif status == "traveling" and now >= explore_start:
        await sb("PATCH", "astro_sessions", {"id": f"eq.{sess['id']}"}, {"status": "active"})
        regs = await astro_get_all_regs(sess["id"])
        for r in regs:
            pet = await get_pet_by_id(r["pet_id"])
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"}) if pet else {"emoji": "🐾"}
            try:
                await context.bot.send_message(r["user_id"],
                    f"🌙 <b>Kamu sudah di Bulan!</b>\n"
                    f"{info['emoji']} <b>{pet['name']}</b> siap explore!\n\n"
                    f"Gunakan /explore untuk cari item!\n"
                    f"⏰ Waktu explore: <b>45 menit</b>\n"
                    f"/astro_bag — lihat tas misi",
                    parse_mode=ParseMode.HTML)
            except: pass
        logger.info(f"Astro Paws #{sess['id']}: traveling → active")

    # active → returning
    elif status == "active" and now >= explore_end:
        await sb("PATCH", "astro_sessions", {"id": f"eq.{sess['id']}"}, {"status": "returning"})
        regs = await astro_get_all_regs(sess["id"])
        for r in regs:
            pet = await get_pet_by_id(r["pet_id"])
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"}) if pet else {"emoji": "🐾"}
            try:
                await context.bot.send_message(r["user_id"],
                    f"🛸 <b>Waktunya pulang!</b>\n"
                    f"{info['emoji']} <b>{pet['name']}</b> dalam perjalanan balik ke Bumi...\n"
                    f"🏠 Tiba pukul <b>{fmt_wib(mission_end)}</b>\n\n"
                    f"<i>Item akan masuk inventory saat mendarat!</i>",
                    parse_mode=ParseMode.HTML)
            except: pass
        logger.info(f"Astro Paws #{sess['id']}: active → returning")

    # returning → closed → distribusi item
    elif status == "returning" and now >= mission_end:
        await sb("PATCH", "astro_sessions", {"id": f"eq.{sess['id']}"}, {"status": "closed"})
        regs = await astro_get_all_regs(sess["id"])
        for r in regs:
            await _astro_finish_reg(r, context)
        # Reset total topup event
        await sb("PATCH", "users", {}, {"astro_topup_total": 0})
        logger.info(f"Astro Paws #{sess['id']}: returning → closed, {len(regs)} regs diproses")

async def _astro_finish_reg(reg: dict, context):
    """Distribusi item ke inventory global, unlock pet, kirim summary."""
    user_id = reg["user_id"]
    pet_id  = reg["pet_id"]
    inv_mission = reg.get("inventory") or {}
    coins   = reg.get("coins_earned", 0)

    # Unlock pet
    await update_pet(pet_id, {"boarding_until": None, "last_decay": now_wib().isoformat()})

    # Masukkan item ke inventory global
    _cdel(_user_cache, user_id)
    global_inv = await get_inv(user_id)

    summary_lines = ["🏠 <b>Misi Selesai — Astro Paws!</b>\n━━━━━━━━━━━━━━━\n\n🎒 Item yang kamu bawa pulang:\n"]
    got_any = False

    for key, qty in inv_mission.items():
        if not isinstance(qty, int) or qty <= 0:
            continue
        got_any = True
        info = ASTRO_PERM_ITEMS.get(key, {"name": key, "emoji": "📦"})

        # Efek khusus moon_rabbit: tambahkan sebagai pet jenis moon_rabbit
        if key == "moon_rabbit":
            # Buat pet moon_rabbit sebanyak qty
            for i in range(qty):
                new_pet = {
                    "owner1_id": user_id, "owner2_id": None,
                    "name": "Moon Rabbit",
                    "pet_type": "moon_rabbit",
                    "xp": 0, "level": 1,
                    "hunger": 0, "happiness": 100, "health": 100,
                    "poop_count": 0, "is_sleeping": False, "is_dirty": False,
                    "is_missing": False, "is_married": False, "is_child": False,
                    "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
                }
                await sb("POST", "pets", {}, new_pet)
            label = f"🐇🌙 <b>Moon Rabbit x{qty}</b> kini jadi petmu! (Tahan lapar, +80 slot misi)" if qty > 1 else "🐇🌙 <b>Moon Rabbit</b> kini jadi petmu! (Tahan lapar, +80 slot misi)"
            summary_lines.append(label)

        else:
            # Terjemahkan item Astro ke kunci inventory global yang ada
            inv_key = _astro_to_inv_key(key)
            global_inv[inv_key] = (global_inv.get(inv_key) or 0) + qty
            summary_lines.append(f"{info['emoji']} {info['name']}: x{qty}")

    if not got_any:
        summary_lines.append("<i>Tidak dapat item apapun kali ini~</i>")

    if coins > 0:
        summary_lines.append(f"\n🪙 Total koin earned: <b>{coins:,}</b>")

    await set_inv(user_id, global_inv)

    try:
        await context.bot.send_message(
            user_id,
            "\n".join(summary_lines),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎒 Lihat Inventory", callback_data="inventory")]]))
    except: pass

def _astro_to_inv_key(astro_key: str) -> str:
    """Map kunci item Astro ke kunci inventory global."""
    mapping = {
        "moon_cake":       "moon_cake",
        "star_pudding":    "star_pudding",
        "cosmic_ramen":    "cosmic_ramen",
        "mega_moon_feast": "mega_feast",
        "mood_pill":       "mood_pill",
        "hunger_pill":     "hunger_pill",
        "pil_levelup":     "pil_levelup",
        "anti_pill":       "anti_pill",
    }
    return mapping.get(astro_key, astro_key)

# Inventory key (apa yang disimpan di inventory user) -> key entry di FOOD_SHOP
# Dipakai do_feed supaya item makanan Astro bisa diresolve walau key inventory beda
ASTRO_INV_TO_FOOD_KEY = {
    "moon_cake":     "moon_cake",
    "star_pudding":  "star_pudding",
    "cosmic_ramen":  "cosmic_ramen",
    "mega_feast":    "mega_moon_feast",   # inventory simpan "mega_feast", FOOD_SHOP pakai "mega_moon_feast"
    "mood_pill":     "mood_pill",
    "hunger_pill":   "hunger_pill",
    "anti_pill":     "anti_pill",
}
# Set kunci inventory yang merupakan "makanan Astro" (harus lewat do_feed, bukan do_use_pil)
ASTRO_FOOD_INV_KEYS = set(ASTRO_INV_TO_FOOD_KEY.keys())

# ── Summary viewer via /astropaws setelah closed ──────────────────────────────
async def _astro_show_summary(message, reg: dict, sess: dict):
    inv = reg.get("inventory") or {}
    log_e = reg.get("explore_log") or []
    coins = reg.get("coins_earned", 0)
    lines = ["🏆 <b>Summary Misi Astro Paws</b>\n━━━━━━━━━━━━━━━\n"]
    items = [(k, v) for k, v in inv.items() if isinstance(v, int) and v > 0]
    if items:
        for k, v in items:
            info = ASTRO_PERM_ITEMS.get(k, {"name": k, "emoji": "📦"})
            lines.append(f"{info['emoji']} {info['name']}: x{v}")
    else:
        lines.append("<i>Tidak dapat item~</i>")
    lines.append(f"\n🪙 Koin earned: <b>{coins:,}</b>")
    lines.append(f"🔍 Total explore: <b>{len(log_e)}</b>x")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ── Topup Bonus Astro (item berdasarkan nominal) ──────────────────────────────
# Pool item untuk bonus topup
ASTRO_COMMON_POOL   = ["moon_cake", "mood_pill"]        # ×2 qty
ASTRO_UNCOMMON_POOL = ["star_pudding", "hunger_pill"]   # ×1 qty

def _astro_tier(total: int) -> str:
    """Kembalikan tier berdasarkan total kumulatif topup."""
    if total >= 20000: return "legendary"
    if total >= 10000: return "rare"
    if total >= 5000:  return "uncommon"
    if total >= 2000:  return "common"
    return "none"

def _astro_next_tier_info(current_total: int) -> str:
    """Teks info tier berikutnya."""
    if current_total >= 20000:
        return ""
    thresholds = [(2000,"common"),(5000,"uncommon"),(10000,"rare"),(20000,"legendary")]
    for thresh, tier in thresholds:
        if current_total < thresh:
            need = thresh - current_total
            if tier == "common":
                preview = "🍮×2 Kue Bulan + 💊×2 Mood Pill"
            elif tier == "uncommon":
                preview = "🍮×N Kue Bulan + 💊×N Mood Pill + ⭐×1 Star Pudding + 🛡️×1 Hunger Pill"
            elif tier == "rare":
                preview = "semua common + 2× uncommon random"
            else:
                preview = "🎉 SEMUA item + 🐇🌙 Moon Rabbit!"
            return f"\n\n📈 Top up <b>Rp {need:,}</b> lagi → dapat bonus: {preview}"
    return ""

async def _astro_topup_bonus(target_id: int, amount: int, context) -> str:
    """Berikan bonus item Astro saat topup berdasarkan total kumulatif."""
    if not ASTRO_TOPUP_BONUS_ACTIVE:
        return ""
    if amount < 2000:
        return ""

    # Ambil / update total kumulatif topup event ini dari DB
    _cdel(_user_cache, target_id)  # flush cache supaya prev selalu fresh dari DB
    u = await get_user(target_id)
    prev_total = u.get("astro_topup_total") or 0
    new_total  = prev_total + amount
    await update_user(target_id, {"astro_topup_total": new_total})
    _cdel(_user_cache, target_id)

    prev_tier = _astro_tier(prev_total)
    new_tier  = _astro_tier(new_total)

    # qty common = (amount // 1000) × 2, qty uncommon = amount // 1000
    qty_common   = (amount // 1000) * 2
    qty_uncommon = amount // 1000

    _cdel(_user_cache, target_id)
    inv = await get_inv(target_id)
    bonus_lines = []

    # ── Tier common: 2k–4.999 ──────────────────────────────────────────
    if new_tier == "common":
        for key in ASTRO_COMMON_POOL:
            info = ASTRO_PERM_ITEMS.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")

    # ── Tier uncommon: 5k–9.999 ───────────────────────────────────────
    elif new_tier == "uncommon":
        for key in ASTRO_COMMON_POOL:
            info = ASTRO_PERM_ITEMS.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")
        for key in ASTRO_UNCOMMON_POOL:
            info = ASTRO_PERM_ITEMS.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_uncommon
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_uncommon}x {info.get('name', key)}")

    # ── Tier rare: 10k–19.999 ─────────────────────────────────────────
    elif new_tier == "rare":
        for key in ASTRO_COMMON_POOL:
            info = ASTRO_PERM_ITEMS.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")
        picked_uncommon = random.sample(ASTRO_UNCOMMON_POOL, min(2, len(ASTRO_UNCOMMON_POOL)))
        for key in picked_uncommon:
            info = ASTRO_PERM_ITEMS.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_uncommon
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_uncommon}x {info.get('name', key)}")

    # ── Tier legendary: 20k+ ──────────────────────────────────────────
    elif new_tier == "legendary":
        all_astro = list(ASTRO_PERM_ITEMS.keys())
        for key in all_astro:
            if key == "moon_rabbit": continue
            info = ASTRO_PERM_ITEMS.get(key, {})
            tier_k = info.get("tier", "common")
            give = qty_common if tier_k == "common" else qty_uncommon
            inv[key] = (inv.get(key) or 0) + give
            bonus_lines.append(f"{info.get('emoji','📦')} +{give}x {info.get('name', key)}")
        bonus_lines.append("🎉 Semua item Astro Paws!")
        # Moon rabbit — cek belum punya
        # Moon rabbit — cek belum punya
        if True:
            new_pet = {
                "owner1_id": target_id, "owner2_id": None,
                "name": "Moon Rabbit", "pet_type": "moon_rabbit",
                "xp": 0, "level": 1, "hunger": 0, "happiness": 100, "health": 100,
                "poop_count": 0, "is_sleeping": False, "is_dirty": False,
                "is_missing": False, "is_married": False, "is_child": False,
                "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
            }
            await sb("POST", "pets", {}, new_pet)
            bonus_lines.append("🐇🌙 Moon Rabbit kini jadi petmu!")


    if not bonus_lines:
        return ""

    await set_inv(target_id, inv)

    # Info next tier
    next_info = _astro_next_tier_info(new_total)
    result = "\n".join(bonus_lines) + next_info
    return result

# ==================== MAIN ====================
# ==================== ASTRO PAWS 2 — MARS ====================
# SQL:
# create table astro2_sessions (id bigserial primary key, scheduled_at timestamptz not null, status text not null default 'open', created_by bigint not null, created_at timestamptz default now());
# create table astro2_registrations (id bigserial primary key, session_id bigint references astro2_sessions(id), user_id bigint not null, pet_id bigint not null, registered_at timestamptz default now(), inventory jsonb default '{}', active_buffs jsonb default '{}', last_explore_at timestamptz, cooldown_until timestamptz, coins_earned int default 0, explore_log jsonb default '[]', scorpion_caught boolean default false, unique(session_id, pet_id));
# alter table users add column if not exists astro2_topup_total int default 0;
# alter table pets add column if not exists pil_abadi_until text;

ASTRO2_COST          = 1000
ASTRO2_TRAVEL_MINS   = 30
ASTRO2_EXPLORE_MINS  = 45
ASTRO2_RETURN_MINS   = 30
ASTRO2_INV_DEFAULT   = 50
ASTRO2_INV_RABBIT    = 80
ASTRO2_EXPLORE_COOLDOWN = 15
ASTRO2_TOPUP_BONUS_ACTIVE = False

ASTRO2_PERM_ITEMS = {
    "lava_cake":      {"name":"Lava Cake",        "emoji":"🌋",   "tier":"common",    "chance":0.35, "hunger":40, "xp":10},
    "planet_pudding": {"name":"Planet Pudding",    "emoji":"🪐",   "tier":"common",    "chance":0.30, "hunger":60, "happy":20},
    "mars_bar":       {"name":"Mars Bar",          "emoji":"🔴",   "tier":"common",    "chance":0.35, "hunger":30, "heal":15},
    "meteor_bite":    {"name":"Meteor Bite",       "emoji":"☄️",  "tier":"uncommon",  "chance":0.20, "hunger":50, "xp":20},
    "rocket_soup":    {"name":"Rocket Fuel Soup",  "emoji":"🚀",   "tier":"uncommon",  "chance":0.18, "hunger":100, "heal":30},
    "alien_feast":    {"name":"Alien Feast",       "emoji":"🛸",   "tier":"uncommon",  "chance":0.15, "hunger":50, "heal":20, "happy":20, "xp":20},
    "stardust_candy": {"name":"Stardust Candy",    "emoji":"💫",   "tier":"uncommon",  "chance":0.18, "happy":80},
    "galaxy_ramen":   {"name":"Galaxy Ramen",      "emoji":"🌌",   "tier":"rare",      "chance":0.08, "hunger":100, "xp":50},
    "pil_mars":       {"name":"Pil Mars",          "emoji":"🔴💊", "tier":"rare",      "chance":0.07, "isPil":True},
    "pil_gladiator":  {"name":"Pil Gladiator",     "emoji":"⚔️",  "tier":"rare",      "chance":0.06, "isPil":True},
    "pil_evolusi":    {"name":"Pil Evolusi",       "emoji":"🌟💊", "tier":"rare",      "chance":0.06, "isPil":True},
    "pil_abadi":      {"name":"Pil Abadi",         "emoji":"🧬",   "tier":"legendary", "chance":0.03, "isPil":True},
    "mars_banquet":   {"name":"Mars Banquet",      "emoji":"🎉🔴", "tier":"legendary", "chance":0.04, "mega_feast2":True},
    "scorpion_mars":  {"name":"Scorpion Mars",     "emoji":"🦂🔴", "tier":"legendary", "chance":0.05, "isPet":True},
}
ASTRO2_BUFF_ITEMS = {
    "mars_shield":       {"name":"Mars Shield",       "emoji":"🛡️🔴","tier":"rare",     "chance":0.07},
    "alien_ally":        {"name":"Alien Ally",         "emoji":"👾",  "tier":"uncommon", "chance":0.10},
    "invisibility_cloak":{"name":"Invisibility Cloak", "emoji":"🫥",  "tier":"rare",     "chance":0.06},
    "lunar_compass":     {"name":"Lunar Compass",      "emoji":"🧭",  "tier":"rare",     "chance":0.07},
    "gravity_boots":     {"name":"Gravity Boots",      "emoji":"👢",  "tier":"uncommon", "chance":0.10},
    "speed_pill":        {"name":"Speed Pill",         "emoji":"💨",  "tier":"uncommon", "chance":0.12},
    "lucky_charm":       {"name":"Lucky Charm",        "emoji":"🍀",  "tier":"rare",     "chance":0.07},
    "decoy_bag":         {"name":"Decoy Bag",          "emoji":"🎭",  "tier":"rare",     "chance":0.06},
    "steal_boost":       {"name":"Steal Boost",        "emoji":"💥",  "tier":"rare",     "chance":0.05},
    "space_magnet":      {"name":"Space Magnet",       "emoji":"🧲",  "tier":"legendary","chance":0.02},
}

async def a2_get_open_session():
    res = await sb("GET","astro2_sessions",{"status":"in.(open,traveling,active,returning)","order":"scheduled_at.asc","limit":"1"})
    return res[0] if res else None

async def a2_get_session(sid):
    res = await sb("GET","astro2_sessions",{"id":f"eq.{sid}"})
    return res[0] if res else None

async def a2_get_reg(session_id, user_id):
    res = await sb("GET","astro2_registrations",{"session_id":f"eq.{session_id}","user_id":f"eq.{user_id}"})
    return res[0] if res else None

async def a2_update_reg(reg_id, data):
    await sb("PATCH","astro2_registrations",{"id":f"eq.{reg_id}"},data)

async def a2_get_all_regs(session_id):
    return await sb_get_all("astro2_registrations",{"session_id":f"eq.{session_id}"}) or []

async def a2_is_locked(user_id):
    sess = await a2_get_open_session()
    if not sess or sess["status"] not in ("traveling","active","returning"):
        return (False,"",None)
    reg = await a2_get_reg(sess["id"],user_id)
    if not reg: return (False,"",None)
    scheduled     = parse_dt(sess["scheduled_at"])
    explore_start = scheduled + timedelta(minutes=ASTRO2_TRAVEL_MINS)
    explore_end   = explore_start + timedelta(minutes=ASTRO2_EXPLORE_MINS)
    mission_end   = explore_end + timedelta(minutes=ASTRO2_RETURN_MINS)
    now = now_wib()
    if sess["status"]=="traveling" and now<explore_start: return (True,"traveling",explore_start)
    if sess["status"]=="active"    and now<explore_end:   return (True,"active",mission_end)
    if sess["status"]=="returning" and now<mission_end:   return (True,"returning",mission_end)
    return (False,"",None)

def a2_inv_total(inv):
    return sum(v for v in inv.values() if isinstance(v,int) and v>0)

def a2_roll(buffs):
    mult = 2.0 if buffs.get("lucky_charm",{}).get("uses",0)>0 else 1.0
    for key,info in ASTRO2_PERM_ITEMS.items():
        if random.random() < info["chance"]*mult: return ("perm",key)
    for key,info in ASTRO2_BUFF_ITEMS.items():
        if random.random() < info["chance"]*mult: return ("buff",key)
    return ("nothing",None)

def a2_coin_roll():
    return random.randint(20,30) if random.random()<0.30 else 0

async def cmd_astro2_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return
    args = context.args
    if not args or len(args)<2:
        await update.message.reply_text("Usage: <code>/astro2_create YYYY-MM-DD HH:MM</code>",parse_mode=ParseMode.HTML); return
    try:
        scheduled = WIB.localize(datetime.strptime(f"{args[0]} {args[1]}","%Y-%m-%d %H:%M"))
    except:
        await update.message.reply_text("❌ Format salah."); return
    existing = await a2_get_open_session()
    if existing:
        await update.message.reply_text(f"❌ Sesi aktif (ID {existing['id']}). Tutup dulu /astro2_close."); return
    res = await sb("POST","astro2_sessions",{},{"scheduled_at":scheduled.isoformat(),"status":"open","created_by":update.effective_user.id})
    sid = res[0]["id"] if res else "?"
    explore_start = scheduled+timedelta(minutes=ASTRO2_TRAVEL_MINS)
    explore_end   = explore_start+timedelta(minutes=ASTRO2_EXPLORE_MINS)
    mission_end   = explore_end+timedelta(minutes=ASTRO2_RETURN_MINS)
    await update.message.reply_text(
        f"🔴 <b>Astro Paws 2 — Mars sesi #{sid}!</b>\n"
        f"📅 Berangkat: <b>{fmt_wib(scheduled)}</b>\n"
        f"🌋 Explore: <b>{fmt_wib(explore_start)}</b> – <b>{fmt_wib(explore_end)}</b>\n"
        f"🏠 Tiba: <b>{fmt_wib(mission_end)}</b>\n\nDaftar via /astropaws2",parse_mode=ParseMode.HTML)
    await log(context,f"🔴 Astro2 #{sid} dibuat oleh {fmt_user(update.effective_user)}")

async def cmd_astro2_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bukan admin!"); return
    sess = await a2_get_open_session()
    if not sess:
        await update.message.reply_text("❌ Tidak ada sesi aktif."); return
    await sb("PATCH","astro2_sessions",{"id":f"eq.{sess['id']}"},{"status":"closed"})
    regs = await a2_get_all_regs(sess["id"])
    for r in regs:
        await update_pet(r["pet_id"],{"boarding_until":None,"last_decay":now_wib().isoformat()})
    await sb("PATCH","users",{},{"astro2_topup_total":0})
    await update.message.reply_text(f"✅ Sesi #{sess['id']} ditutup. {len(regs)} pet di-unlock.")

async def cmd_astropaws2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ASTRO_FORCE_SUB_ENABLED and not await check_force_sub(update, context):
        return
    u = await get_user(user.id,safe_html(user.username),safe_html(user.first_name))
    sess = await a2_get_open_session()
    if not sess:
        await update.message.reply_text("🔴 <b>Astro Paws 2 — Mars</b>\n\nBelum ada misi~",parse_mode=ParseMode.HTML); return
    status = sess["status"]
    scheduled     = parse_dt(sess["scheduled_at"])
    explore_start = scheduled+timedelta(minutes=ASTRO2_TRAVEL_MINS)
    explore_end   = explore_start+timedelta(minutes=ASTRO2_EXPLORE_MINS)
    mission_end   = explore_end+timedelta(minutes=ASTRO2_RETURN_MINS)
    now = now_wib()
    reg = await a2_get_reg(sess["id"],user.id)
    if status=="open":
        if reg:
            pet = await get_pet_by_id(reg["pet_id"])
            info = PETS.get(pet["pet_type"],{"emoji":"🐾"}) if pet else {"emoji":"🐾"}
            await update.message.reply_text(
                f"🔴 <b>Astro Paws 2 — Terdaftar!</b>\n"
                f"✅ {info['emoji']} <b>{pet['name']}</b> siap ke Mars!\n"
                f"📅 Berangkat: <b>{fmt_wib(scheduled)}</b>",parse_mode=ParseMode.HTML); return
        koin = u.get("koin",0)
        if koin < ASTRO2_COST:
            await update.message.reply_text(f"❌ Koin kurang! Butuh {ASTRO2_COST:,} 🪙"); return
        pets = await get_user_pets(user.id)
        active_pets = [p for p in pets if not p.get("is_missing")
            and not (p.get("boarding_until") and parse_dt(p["boarding_until"])>now)
            and not (p.get("expedition_until") and parse_dt(p["expedition_until"])>now)
            and not (p.get("work_until") and parse_dt(p["work_until"])>now)]
        if not active_pets:
            await update.message.reply_text("❌ Tidak ada pet yang bisa dibawa."); return
        buttons = []
        for p in active_pets:
            info = PETS.get(p["pet_type"],{"emoji":"🐾"})
            lv = calc_level(p.get("xp",0))
            is_rabbit = p.get("pet_type")=="moon_rabbit"
            label = f"{info['emoji']} {p['name']} Lv.{lv}"+(" 🐇🌙+80slot" if is_rabbit else "")
            buttons.append([InlineKeyboardButton(label,callback_data=f"a2_reg_{sess['id']}_{p['id']}")])
        buttons.append([InlineKeyboardButton("❌ Batal",callback_data="main_menu")])
        await update.message.reply_text(
            f"🔴 <b>Astro Paws 2 — Daftar Misi Mars!</b>\n━━━━━━━━━━━━━━━\n"
            f"📅 Berangkat: <b>{fmt_wib(scheduled)}</b>\n"
            f"🌋 Explore: <b>{fmt_wib(explore_start)}</b> – <b>{fmt_wib(explore_end)}</b>\n"
            f"🏠 Tiba: <b>{fmt_wib(mission_end)}</b>\n\n"
            f"💰 Biaya: <b>{ASTRO2_COST:,} 🪙</b> | Koinmu: <b>{koin:,} 🪙</b>\n\nPilih pet:",
            parse_mode=ParseMode.HTML,reply_markup=InlineKeyboardMarkup(buttons))
    elif status in ("traveling","active","returning"):
        if not reg:
            await update.message.reply_text("🔴 Misi berlangsung tapi kamu tidak ikut."); return
        pet = await get_pet_by_id(reg["pet_id"])
        info = PETS.get(pet["pet_type"],{"emoji":"🐾"}) if pet else {"emoji":"🐾"}
        inv = reg.get("inventory") or {}
        total = a2_inv_total(inv)
        coins = reg.get("coins_earned",0)
        pet_type = pet.get("pet_type","") if pet else ""
        inv_slots = ASTRO2_INV_RABBIT if pet_type=="moon_rabbit" else ASTRO2_INV_DEFAULT
        if status=="traveling":
            eta=int((explore_start-now).total_seconds()/60); phase=f"🛸 Perjalanan ke Mars... ~{eta} menit"
        elif status=="active":
            eta=int((explore_end-now).total_seconds()/60); phase=f"🌋 Explore Mars! ~{eta} menit\n/explore2"
        else:
            eta=int((mission_end-now).total_seconds()/60); phase=f"🛸 Balik ke Bumi... ~{eta} menit"
        await update.message.reply_text(
            f"🔴 <b>Astro Paws 2 — Status</b>\n{info['emoji']} <b>{pet['name']}</b>\n{phase}\n"
            f"🎒 {total}/{inv_slots} | 🪙 {coins:,}",parse_mode=ParseMode.HTML)

async def a2_handle_register(q, user, session_id, pet_id, context):
    sess = await a2_get_session(session_id)
    if not sess or sess["status"]!="open":
        await q.answer("❌ Sesi tidak tersedia!",show_alert=True); return
    pet = await get_pet_by_id(pet_id)
    if not pet or (pet.get("owner1_id")!=user.id and pet.get("owner2_id")!=user.id):
        await q.answer("❌ Bukan petmu!",show_alert=True); return
    existing_pet = await sb("GET","astro2_registrations",{"session_id":f"eq.{session_id}","pet_id":f"eq.{pet_id}"})
    if existing_pet:
        fu = await get_user(existing_pet[0]["user_id"])
        fn = get_display_name(fu) if fu else "?"
        await q.answer(f"❌ Pet ini sudah didaftarkan {fn}!",show_alert=True); return
    my_reg = await a2_get_reg(session_id,user.id)
    if my_reg:
        await q.answer("❌ Kamu sudah terdaftar!",show_alert=True); return
    ok = await spend_koin(user.id,ASTRO2_COST, "astro2_daftar")
    if not ok:
        await q.answer("❌ Koin tidak cukup!",show_alert=True); return
    scheduled  = parse_dt(sess["scheduled_at"])
    mission_end = scheduled+timedelta(minutes=ASTRO2_TRAVEL_MINS+ASTRO2_EXPLORE_MINS+ASTRO2_RETURN_MINS)
    await update_pet(pet_id,{"boarding_until":mission_end.isoformat()})
    await sb("POST","astro2_registrations",{},{
        "session_id":session_id,"user_id":user.id,"pet_id":pet_id,
        "inventory":{},"active_buffs":{},"coins_earned":0,"explore_log":[],"scorpion_caught":False})
    info = PETS.get(pet["pet_type"],{"emoji":"🐾"})
    await q.edit_message_text(
        f"✅ <b>Terdaftar Astro Paws 2!</b>\n{info['emoji']} <b>{pet['name']}</b> siap ke Mars! 🔴",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu",callback_data="main_menu")]]))

async def cmd_explore2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ASTRO_FORCE_SUB_ENABLED and not await check_force_sub(update, context):
        return
    sess = await a2_get_open_session()
    if not sess or sess["status"]!="active":
        await update.message.reply_text("🔴 Tidak ada misi Mars aktif."); return
    reg = await a2_get_reg(sess["id"],user.id)
    if not reg:
        await update.message.reply_text("❌ Kamu tidak terdaftar."); return
    now = now_wib()
    if reg.get("cooldown_until"):
        cd_dt = parse_dt(reg["cooldown_until"])
        if now < cd_dt:
            new_cd = cd_dt+timedelta(seconds=ASTRO2_EXPLORE_COOLDOWN)
            await a2_update_reg(reg["id"],{"cooldown_until":new_cd.isoformat()})
            sisa = int((new_cd-now).total_seconds())
            pet = await get_pet_by_id(reg["pet_id"])
            pname = pet["name"] if pet else "Petmu"
            await update.message.reply_text(
                f"⚠️ <b>{pname}</b> tersandung batu Mars! Cooldown +15 detik.\n⏳ <b>{sisa} detik</b>",
                parse_mode=ParseMode.HTML); return
    pet = await get_pet_by_id(reg["pet_id"])
    info = PETS.get(pet["pet_type"],{"emoji":"🐾"}) if pet else {"emoji":"🐾"}
    pet_name = pet["name"] if pet else "?"
    buffs = reg.get("active_buffs") or {}
    inv   = reg.get("inventory") or {}
    coins_earned = reg.get("coins_earned",0)
    log_entries  = reg.get("explore_log") or []
    scorpion_caught = reg.get("scorpion_caught",False)
    pet_type = pet.get("pet_type","") if pet else ""
    inv_slots = ASTRO2_INV_RABBIT if pet_type=="moon_rabbit" else ASTRO2_INV_DEFAULT
    total_qty = a2_inv_total(inv)
    slot_full = total_qty >= inv_slots
    cd_secs = ASTRO2_EXPLORE_COOLDOWN
    if buffs.get("gravity_boots"): cd_secs=10
    if buffs.get("speed_pill",{}).get("until"):
        if parse_dt(buffs["speed_pill"]["until"])>now: cd_secs=max(5,cd_secs-8)
    new_cd = now+timedelta(seconds=cd_secs)
    result_lines = [f"🌋 <b>{pet_name}</b> menjelajah Mars..."]
    if buffs.get("lucky_charm",{}).get("uses",0)>0:
        buffs["lucky_charm"]["uses"]-=1
        if buffs["lucky_charm"]["uses"]<=0: del buffs["lucky_charm"]
    force_item = buffs.pop("lunar_compass",None) is not None
    # Encounter
    encounter_msg = None
    if random.random()<0.50:
        all_regs = await a2_get_all_regs(sess["id"])
        others = [r for r in all_regs if r["user_id"]!=user.id]
        if others:
            t_reg = random.choice(others)
            tbuffs = t_reg.get("active_buffs") or {}
            if not tbuffs.get("invisibility_cloak"):
                tu = await get_user(t_reg["user_id"])
                tname = get_display_name(tu) if tu else "Seseorang"
                tuname = tu.get("username") if tu else None
                tdisplay = f"{safe_html(tname)} (@{safe_html(tuname)})" if tuname else safe_html(tname)
                tpet = await get_pet_by_id(t_reg["pet_id"])
                tpet_info = PETS.get(tpet["pet_type"],{"emoji":"🐾"}) if tpet else {"emoji":"🐾"}
                encounter_msg = (t_reg,tdisplay,tpet["name"] if tpet else "?",tpet_info)
                result_lines.append(f"\n👀 Kamu bertemu <b>{tdisplay}</b> dan {tpet_info['emoji']} <b>{encounter_msg[2]}</b>!")
    # Roll item
    cat,key = a2_roll(buffs)
    if force_item and cat=="nothing": cat,key="perm","lava_cake"
    if cat=="perm" and key:
        item_info = ASTRO2_PERM_ITEMS[key]
        if item_info.get("isPet"):
            if not scorpion_caught and random.random()<0.05:
                inv[key]=(inv.get(key) or 0)+1
                scorpion_caught=True
                result_lines.append(f"\n🦂 <b>LANGKA!</b> {item_info['emoji']} <b>{item_info['name']}</b> berhasil ditangkap!")
            else:
                result_lines.append(f"\n👀 {item_info['emoji']} <b>{item_info['name']}</b> muncul tapi kabur!")
        elif slot_full:
            result_lines.append(f"\n📦 Tas penuh ({total_qty}/{inv_slots})! Item terlewat.")
        else:
            inv[key]=(inv.get(key) or 0)+1
            result_lines.append(f"\n✨ Dapat: {item_info['emoji']} <b>{item_info['name']}</b>!")
            log_entries.append({"type":"item","key":key})
    elif cat=="buff" and key:
        buff_info = ASTRO2_BUFF_ITEMS[key]
        if key=="lucky_charm":   buffs[key]={"uses":3}
        elif key=="speed_pill":  buffs[key]={"until":(now+timedelta(minutes=5)).isoformat()}
        elif key=="mars_shield": buffs[key]={"blocks":2}
        elif key=="alien_ally":  buffs[key]={"active":True}
        elif key=="space_magnet":
            all_regs_m = await a2_get_all_regs(sess["id"])
            for v in random.sample(all_regs_m,min(len(all_regs_m),3)):
                if v["user_id"]==user.id: continue
                v_inv=v.get("inventory") or {}
                v_items=[k for k,vv in v_inv.items() if vv>0]
                if v_items:
                    sk=random.choice(v_items); si=ASTRO2_PERM_ITEMS.get(sk,{"name":sk,"emoji":"📦"})
                    v_inv[sk]-=1
                    if v_inv[sk]<=0: del v_inv[sk]
                    await a2_update_reg(v["id"],{"inventory":v_inv})
                    inv[sk]=(inv.get(sk) or 0)+1
                    result_lines.append(f"\n🧲 <b>Space Magnet!</b> Tarik {si['emoji']} {si['name']}!")
                    try:
                        vu=await get_user(v["user_id"]); vn=get_display_name(vu) if vu else "?"
                        my_u=await get_user(user.id)
                        await context.bot.send_message(v["user_id"],
                            f"🧲 {safe_html(get_display_name(my_u))} menarik {si['emoji']} {si['name']} dari tasmu!",parse_mode=ParseMode.HTML)
                    except: pass
                    break
        else: buffs[key]={"active":True}
        result_lines.append(f"\n🎯 Buff: {buff_info['emoji']} <b>{buff_info['name']}</b>!")
    else:
        result_lines.append("\n🔴 Debu Mars... tidak menemukan apa-apa.")
    if buffs.get("alien_ally"):
        ac=random.randint(10,30); coins_earned+=ac; await add_koin(user.id,ac,"astro2_alien_ally")
        result_lines.append(f"\n👾 Alien Ally: +{ac} 🪙!")
    coin_gain=a2_coin_roll()
    if coin_gain>0:
        coins_earned+=coin_gain; await add_koin(user.id,coin_gain,"astro2_explore")
        result_lines.append(f"\n🪙 +{coin_gain} koin!")
    if random.random()<0.05:
        ev=random.choice(["meteor","alien"])
        items_keys=[k for k,v in inv.items() if isinstance(v,int) and v>0]
        if ev=="meteor" and items_keys:
            lost=random.sample(items_keys,min(random.randint(1,3),len(items_keys)))
            for lk in lost:
                inv[lk]=max(0,inv.get(lk,1)-1)
                if inv[lk]<=0: del inv[lk]
            result_lines.append(f"\n☄️ <b>Badai Meteor!</b> {len(lost)} item hilang!")
        elif ev=="alien" and items_keys:
            if random.random()<0.50:
                sk=random.choice(items_keys); si=ASTRO2_PERM_ITEMS.get(sk,{"name":sk,"emoji":"📦"})
                inv[sk]=max(0,inv.get(sk,1)-1)
                if inv[sk]<=0: del inv[sk]
                result_lines.append(f"\n👾 <b>Alien Mars!</b> Mengambil {si['emoji']} {si['name']}!")
            else: result_lines.append("\n👾 <b>Alien Mars!</b> Kamu selamat!")
    await a2_update_reg(reg["id"],{
        "inventory":inv,"active_buffs":buffs,"coins_earned":coins_earned,
        "scorpion_caught":scorpion_caught,
        "last_explore_at":now.isoformat(),"cooldown_until":new_cd.isoformat(),
        "explore_log":log_entries[-50:]})
    total2=a2_inv_total(inv)
    result_lines.append(f"\n\n🎒 <b>{total2}/{inv_slots}</b> | 🪙 <b>{coins_earned:,}</b> | ⏳ <b>{cd_secs}s</b>")
    kb=None
    if encounter_msg:
        t_reg2,t_disp,t_pname,t_pinfo=encounter_msg
        kb=InlineKeyboardMarkup([[
            InlineKeyboardButton("😈 Steal",callback_data=f"a2_steal_{sess['id']}_{t_reg2['id']}"),
            InlineKeyboardButton("➡️ Skip",callback_data="a2_skip")]])
    await update.message.reply_text("\n".join(result_lines),parse_mode=ParseMode.HTML,reply_markup=kb)

async def a2_handle_steal(q, user, session_id, target_reg_id, context):
    sess = await a2_get_session(session_id)
    if not sess or sess["status"]!="active":
        await q.answer("❌ Misi tidak aktif!",show_alert=True); return
    my_reg = await a2_get_reg(session_id,user.id)
    if not my_reg:
        await q.answer("❌ Tidak terdaftar!",show_alert=True); return
    # Anti-spam: cek steal cooldown 10 detik
    now = now_wib()
    my_buffs = my_reg.get("active_buffs") or {}
    steal_cd = my_buffs.get("_steal_cd")
    if steal_cd and parse_dt(steal_cd) > now:
        await q.answer("⏳ Tunggu sebentar sebelum steal lagi!", show_alert=True); return
    my_buffs["_steal_cd"] = (now + timedelta(seconds=10)).isoformat()
    await a2_update_reg(my_reg["id"], {"active_buffs": my_buffs})
    # Hapus tombol steal supaya tidak bisa diklik lagi
    try: await q.edit_message_reply_markup(reply_markup=None)
    except: pass
    t_res = await sb("GET","astro2_registrations",{"id":f"eq.{target_reg_id}"})
    if not t_res:
        await q.answer("❌ Target tidak ada!",show_alert=True); return
    t_reg=t_res[0]; t_inv=t_reg.get("inventory") or {}; t_buffs=t_reg.get("active_buffs") or {}
    my_buffs=my_reg.get("active_buffs") or {}; my_inv=my_reg.get("inventory") or {}
    t_items=[k for k,v in t_inv.items() if isinstance(v,int) and v>0]
    if not t_items:
        await q.edit_message_text("😅 Target tidak punya item!",parse_mode=ParseMode.HTML); return
    # Cek slot pencuri
    my_pet_type=(await get_pet_by_id(my_reg["pet_id"]) or {}).get("pet_type","")
    my_slots=ASTRO2_INV_RABBIT if my_pet_type=="moon_rabbit" else ASTRO2_INV_DEFAULT
    if a2_inv_total(my_inv)>=my_slots:
        await q.edit_message_text("❌ Tas penuh! Tidak bisa steal.",parse_mode=ParseMode.HTML); return
    # Mars Shield
    if t_buffs.get("mars_shield"):
        blocks=t_buffs["mars_shield"].get("blocks",1)-1
        if blocks<=0: del t_buffs["mars_shield"]
        else: t_buffs["mars_shield"]["blocks"]=blocks
        await a2_update_reg(t_reg["id"],{"active_buffs":t_buffs})
        u=await get_user(user.id)
        try:
            await context.bot.send_message(t_reg["user_id"],
                f"🛡️🔴 <b>Mars Shield</b> memblok steal dari {safe_html(get_display_name(u))}! ({blocks} block tersisa)",
                parse_mode=ParseMode.HTML)
        except: pass
        await q.edit_message_text("🛡️🔴 Gagal! Target punya <b>Mars Shield</b>!",parse_mode=ParseMode.HTML); return
    if t_buffs.get("decoy_bag"):
        del t_buffs["decoy_bag"]
        await a2_update_reg(t_reg["id"],{"active_buffs":t_buffs})
        await q.edit_message_text("🎭 <b>Decoy Bag</b>! Isinya kosong.",parse_mode=ParseMode.HTML); return
    steal_chance=0.90 if my_buffs.get("steal_boost") else 0.60
    if my_buffs.get("steal_boost"):
        del my_buffs["steal_boost"]
        await a2_update_reg(my_reg["id"],{"active_buffs":my_buffs})
    if random.random()>steal_chance:
        await q.edit_message_text("😅 Gagal! Kepergok!",parse_mode=ParseMode.HTML); return
    stolen_key=random.choice(t_items)
    stolen_info=ASTRO2_PERM_ITEMS.get(stolen_key,{"name":stolen_key,"emoji":"📦"})
    t_inv[stolen_key]-=1
    if t_inv[stolen_key]<=0: del t_inv[stolen_key]
    my_inv[stolen_key]=(my_inv.get(stolen_key) or 0)+1
    await a2_update_reg(t_reg["id"],{"inventory":t_inv})
    await a2_update_reg(my_reg["id"],{"inventory":my_inv})
    u=await get_user(user.id); mn=get_display_name(u); mun=u.get("username") if u else None
    mdisp=f"{safe_html(mn)} (@{safe_html(mun)})" if mun else safe_html(mn)
    try:
        await context.bot.send_message(t_reg["user_id"],
            f"⚠️ <b>{mdisp}</b> mencuri {stolen_info['emoji']} <b>{stolen_info['name']}</b> dari tasmu di Mars!",
            parse_mode=ParseMode.HTML)
    except: pass
    await q.edit_message_text(f"😈 Berhasil! Dapat {stolen_info['emoji']} <b>{stolen_info['name']}</b>!",parse_mode=ParseMode.HTML)

async def cmd_astro2_bag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sess = await a2_get_open_session()
    if not sess or sess["status"] not in ("active","traveling","returning"):
        await update.message.reply_text("🔴 Tidak ada misi Mars aktif."); return
    reg = await a2_get_reg(sess["id"],user.id)
    if not reg:
        await update.message.reply_text("❌ Tidak terdaftar."); return
    inv=reg.get("inventory") or {}; buffs=reg.get("active_buffs") or {}
    items=[(k,v) for k,v in inv.items() if isinstance(v,int) and v>0]
    pet_type=(await get_pet_by_id(reg["pet_id"]) or {}).get("pet_type","")
    inv_slots=ASTRO2_INV_RABBIT if pet_type=="moon_rabbit" else ASTRO2_INV_DEFAULT
    total=a2_inv_total(inv)
    lines=["🎒 <b>Astro Paws 2 Bag — Mars</b>\n━━━━━━━━━━━━━━━\n"]
    if items:
        for k,v in items:
            info=ASTRO2_PERM_ITEMS.get(k,{"name":k,"emoji":"📦"})
            lines.append(f"{info['emoji']} {info['name']}: <b>x{v}</b>")
    else: lines.append("<i>Tas kosong~</i>")
    if buffs:
        lines.append("\n🌀 <b>Buff Aktif:</b>")
        for bk,bv in buffs.items():
            bi=ASTRO2_BUFF_ITEMS.get(bk,{"name":bk,"emoji":"✨"})
            extra=f" ({bv.get('blocks')}x block)" if bk=="mars_shield" else ""
            lines.append(f"{bi['emoji']} {bi['name']}{extra}")
    lines.append(f"\n🪙 Coin: <b>{reg.get('coins_earned',0):,}</b> | 📦 <b>{total}/{inv_slots}</b>")
    lines.append("<i>\nHapus item: /remove nama_item jumlah</i>")
    await update.message.reply_text("\n".join(lines),parse_mode=ParseMode.HTML)

async def _a2_finish_reg(reg, context):
    user_id=reg["user_id"]; pet_id=reg["pet_id"]
    inv_mission=reg.get("inventory") or {}; coins=reg.get("coins_earned",0)
    await update_pet(pet_id,{"boarding_until":None,"last_decay":now_wib().isoformat()})
    _cdel(_user_cache,user_id)
    global_inv=await get_inv(user_id)
    summary=["🏠 <b>Misi Mars Selesai!</b>\n━━━━━━━━━━━━━━━\n\n🎒 Item yang kamu bawa:\n"]
    got=False
    for key,qty in inv_mission.items():
        if not isinstance(qty,int) or qty<=0: continue
        got=True
        info=ASTRO2_PERM_ITEMS.get(key,{"name":key,"emoji":"📦"})
        if key=="scorpion_mars":
            for _ in range(qty):
                await sb("POST","pets",{},{
                    "owner1_id":user_id,"owner2_id":None,"name":"Scorpion Mars","pet_type":"scorpion_mars",
                    "xp":0,"level":1,"hunger":0,"happiness":100,"health":100,
                    "poop_count":0,"is_sleeping":False,"is_dirty":False,"is_missing":False,"is_married":False,"is_child":False,
                    "special_ability":"battle_top_2","last_decay":now_wib().isoformat()})
            summary.append(f"🦂🔴 <b>Scorpion Mars</b> x{qty} kini jadi petmu!")
        elif info.get("mega_feast2"):
            all_pets=await get_user_pets(user_id)
            ids_str=",".join(str(p["id"]) for p in all_pets)
            if ids_str:
                await sb("PATCH","pets",{"id":f"in.({ids_str})"},{"hunger":0,"happiness":50,"last_decay":now_wib().isoformat()})
            summary.append(f"🎉🔴 Mars Banquet! Semua petmu kenyang + mood +50!")
        elif key == "pil_mars":
            # Tidak lapar + tidak poop selama 48 jam (pakai ke pet misi)
            expires48 = (now_wib() + timedelta(hours=48)).isoformat()
            await update_pet(pet_id, {"pil_anti_lapar_until": expires48, "pil_anti_pup_until": expires48})
            summary.append(f"🔴💊 <b>Pil Mars x{qty}</b> otomatis dipakai ke {(await get_pet_by_id(pet_id) or {}).get('name','petmu')}! Tidak lapar & tidak poop 48 jam!")
        elif key == "pil_gladiator":
            # Battle score +100 permanen per qty
            pet_data = await get_pet_by_id(pet_id)
            current_bonus = (pet_data.get("battle_score_bonus") or 0) if pet_data else 0
            await update_pet(pet_id, {"battle_score_bonus": current_bonus + (100 * qty)})
            summary.append(f"⚔️ <b>Pil Gladiator x{qty}</b> dipakai! Battle score +{100*qty} permanen!")
        elif key == "pil_evolusi":
            # Naik 3 level per pil
            pet_data = await get_pet_by_id(pet_id)
            old_xp = (pet_data.get("xp") or 0) if pet_data else 0
            new_xp = min(old_xp + XP_PER_LEVEL * 3 * qty, (MAX_LEVEL - 1) * XP_PER_LEVEL)
            old_lv = calc_level(old_xp); new_lv = calc_level(new_xp)
            await update_pet(pet_id, {"xp": new_xp})
            summary.append(f"🌟💊 <b>Pil Evolusi x{qty}</b> dipakai! Naik {new_lv - old_lv} level (Lv.{old_lv} → Lv.{new_lv})!")
        elif key == "pil_abadi":
            # Health tidak turun selama 7 hari per pil
            expires_abadi = (now_wib() + timedelta(days=7 * qty)).isoformat()
            await update_pet(pet_id, {"pil_abadi_until": expires_abadi})
            summary.append(f"🧬 <b>Pil Abadi x{qty}</b> dipakai! Health tidak turun selama {7*qty} hari!")
        else:
            global_inv[key]=(global_inv.get(key) or 0)+qty
            summary.append(f"{info['emoji']} {info['name']}: x{qty}")
    if not got: summary.append("<i>Tidak dapat item~</i>")
    if coins>0: summary.append(f"\n🪙 Total coin: <b>{coins:,}</b>")
    await set_inv(user_id,global_inv)
    try:
        await context.bot.send_message(user_id,"\n".join(summary),parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎒 Inventory",callback_data="inventory")]]))
    except: pass

async def job_astro2_tick(context: ContextTypes.DEFAULT_TYPE):
    sess = await a2_get_open_session()
    if not sess: return
    now=now_wib(); scheduled=parse_dt(sess["scheduled_at"])
    explore_start=scheduled+timedelta(minutes=ASTRO2_TRAVEL_MINS)
    explore_end=explore_start+timedelta(minutes=ASTRO2_EXPLORE_MINS)
    mission_end=explore_end+timedelta(minutes=ASTRO2_RETURN_MINS)
    status=sess["status"]
    if status=="open" and now>=scheduled:
        await sb("PATCH","astro2_sessions",{"id":f"eq.{sess['id']}"},{"status":"traveling"})
        for r in await a2_get_all_regs(sess["id"]):
            pet=await get_pet_by_id(r["pet_id"]); info=PETS.get(pet["pet_type"],{"emoji":"🐾"}) if pet else {"emoji":"🐾"}
            try:
                await context.bot.send_message(r["user_id"],
                    f"🚀 <b>Astro Paws 2 dimulai!</b>\n{info['emoji']} <b>{pet['name']}</b> ke Mars!\n"
                    f"🌋 Explore mulai: <b>{fmt_wib(explore_start)}</b>",parse_mode=ParseMode.HTML)
            except: pass
    elif status=="traveling" and now>=explore_start:
        await sb("PATCH","astro2_sessions",{"id":f"eq.{sess['id']}"},{"status":"active"})
        for r in await a2_get_all_regs(sess["id"]):
            pet=await get_pet_by_id(r["pet_id"]); info=PETS.get(pet["pet_type"],{"emoji":"🐾"}) if pet else {"emoji":"🐾"}
            try:
                await context.bot.send_message(r["user_id"],
                    f"🌋 <b>Kamu sudah di Mars!</b>\n{info['emoji']} <b>{pet['name']}</b> siap explore!\n"
                    f"Gunakan /explore2 | ⏰ 45 menit",parse_mode=ParseMode.HTML)
            except: pass
    elif status=="active" and now>=explore_end:
        await sb("PATCH","astro2_sessions",{"id":f"eq.{sess['id']}"},{"status":"returning"})
        for r in await a2_get_all_regs(sess["id"]):
            pet=await get_pet_by_id(r["pet_id"]); info=PETS.get(pet["pet_type"],{"emoji":"🐾"}) if pet else {"emoji":"🐾"}
            try:
                await context.bot.send_message(r["user_id"],
                    f"🛸 <b>Waktunya pulang!</b>\n{info['emoji']} <b>{pet['name']}</b> balik ke Bumi...\n"
                    f"🏠 Tiba: <b>{fmt_wib(mission_end)}</b>",parse_mode=ParseMode.HTML)
            except: pass
    elif status=="returning" and now>=mission_end:
        await sb("PATCH","astro2_sessions",{"id":f"eq.{sess['id']}"},{"status":"closed"})
        regs=await a2_get_all_regs(sess["id"])
        for r in regs: await _a2_finish_reg(r,context)
        await sb("PATCH","users",{},{"astro2_topup_total":0})

async def cmd_astro2topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ASTRO2_TOPUP_BONUS_ACTIVE
    if update.effective_user.id not in ADMIN_IDS: return
    args=context.args
    if not args or args[0].lower() not in ("on","off"):
        s="ON 🟢" if ASTRO2_TOPUP_BONUS_ACTIVE else "OFF 🔴"
        await update.message.reply_text(f"🔴 Astro Paws 2 Topup: <b>{s}</b>\nUsage: <code>/astro2topup on|off</code>",parse_mode=ParseMode.HTML); return
    ASTRO2_TOPUP_BONUS_ACTIVE=(args[0].lower()=="on")
    s="ON 🟢" if ASTRO2_TOPUP_BONUS_ACTIVE else "OFF 🔴"
    await update.message.reply_text(f"🔴 Astro Paws 2 Topup: <b>{s}</b>",parse_mode=ParseMode.HTML)

ASTRO2_COMMON_TOPUP  = ["lava_cake","planet_pudding","mars_bar"]
ASTRO2_UNCOMMON_TOPUP= ["meteor_bite","rocket_soup","alien_feast","stardust_candy"]
ASTRO2_RARE_TOPUP    = ["galaxy_ramen"]
ASTRO2_PIL_TOPUP     = ["pil_mars","pil_gladiator","pil_evolusi","pil_abadi"]

async def _a2_topup_bonus(target_id, amount, context):
    if not ASTRO2_TOPUP_BONUS_ACTIVE or amount < 2000: return ""
    _cdel(_user_cache, target_id)  # flush cache supaya prev selalu fresh dari DB
    u = await get_user(target_id)
    prev = u.get("astro2_topup_total") or 0
    new_total = prev + amount
    await update_user(target_id, {"astro2_topup_total": new_total})
    _cdel(_user_cache, target_id)

    prev_tier = _astro_tier(prev)
    new_tier  = _astro_tier(new_total)

    qty_common   = (amount // 1000) * 2
    qty_uncommon = amount // 1000
    qty_rare     = max(1, amount // 5000)

    inv = await get_inv(target_id)
    bonus = []

    # ── Item reguler per tier ─────────────────────────────────────────────
    if new_tier == "common":
        for k in ASTRO2_COMMON_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_common
            bonus.append(f"{i.get('emoji','📦')} +{qty_common}x {i.get('name',k)}")

    elif new_tier == "uncommon":
        for k in ASTRO2_COMMON_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_common
            bonus.append(f"{i.get('emoji','📦')} +{qty_common}x {i.get('name',k)}")
        for k in ASTRO2_UNCOMMON_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_uncommon
            bonus.append(f"{i.get('emoji','📦')} +{qty_uncommon}x {i.get('name',k)}")

    elif new_tier == "rare":
        for k in ASTRO2_COMMON_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_common
            bonus.append(f"{i.get('emoji','📦')} +{qty_common}x {i.get('name',k)}")
        for k in ASTRO2_UNCOMMON_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_uncommon
            bonus.append(f"{i.get('emoji','📦')} +{qty_uncommon}x {i.get('name',k)}")
        for k in ASTRO2_RARE_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_rare
            bonus.append(f"{i.get('emoji','📦')} +{qty_rare}x {i.get('name',k)}")

    elif new_tier == "legendary":
        for k in ASTRO2_COMMON_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_common
            bonus.append(f"{i.get('emoji','📦')} +{qty_common}x {i.get('name',k)}")
        for k in ASTRO2_UNCOMMON_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_uncommon
            bonus.append(f"{i.get('emoji','📦')} +{qty_uncommon}x {i.get('name',k)}")
        for k in ASTRO2_RARE_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_rare
            bonus.append(f"{i.get('emoji','📦')} +{qty_rare}x {i.get('name',k)}")
        for k in ASTRO2_PIL_TOPUP:
            i = ASTRO2_PERM_ITEMS.get(k, {})
            inv[k] = (inv.get(k) or 0) + qty_rare
            bonus.append(f"{i.get('emoji','📦')} +{qty_rare}x {i.get('name',k)}")

    # ── Milestone: pertama kali reach legendary (20rb) ───────────────────
    if prev < 20000 and new_total >= 20000:
        bonus.append("🎉 Semua item Astro Paws 2!")
        # Scorpion Mars — cek belum punya
        existing = await sb_get_all("pets", {"owner1_id": f"eq.{target_id}", "pet_type": "eq.scorpion_mars"})
        if not existing:
            await sb("POST", "pets", {}, {
                "owner1_id": target_id, "owner2_id": None,
                "name": "Scorpion Mars", "pet_type": "scorpion_mars",
                "xp": 0, "level": 1, "hunger": 0, "happiness": 100, "health": 100,
                "poop_count": 0, "is_sleeping": False, "is_dirty": False,
                "is_missing": False, "is_married": False, "is_child": False,
                "special_ability": "battle_top_2", "last_decay": now_wib().isoformat()
            })
            bonus.append("🦂🔴 Scorpion Mars kini jadi petmu!")
        # Moon Rabbit — cek belum punya
        existing_mr = await sb_get_all("pets", {"owner1_id": f"eq.{target_id}", "pet_type": "eq.moon_rabbit"})
        if not existing_mr:
            await sb("POST", "pets", {}, {
                "owner1_id": target_id, "owner2_id": None,
                "name": "Moon Rabbit", "pet_type": "moon_rabbit",
                "xp": 0, "level": 1, "hunger": 0, "happiness": 100, "health": 100,
                "poop_count": 0, "is_sleeping": False, "is_dirty": False,
                "is_missing": False, "is_married": False, "is_child": False,
                "last_decay": now_wib().isoformat()
            })
            bonus.append("🐇🌙 Moon Rabbit kini jadi petmu!")

    if not bonus: return ""
    await set_inv(target_id, inv)
    return "\n".join(bonus) + _a2_next_tier_info(new_total)

def _a2_next_tier_info(current_total: int) -> str:
    if current_total >= 20000: return ""
    thresholds = [
        (2000,  "common",    "🌋 Lava Cake + 🪐 Planet Pudding + 🔴 Mars Bar"),
        (5000,  "uncommon",  "common + ☄️ Meteor Bite + 🚀 Rocket Soup + 🛸 Alien Feast + 💫 Stardust Candy"),
        (10000, "rare",      "semua uncommon + 🌌 Galaxy Ramen"),
        (20000, "legendary", "🎉 SEMUA item + pil + 🦂🔴 Scorpion Mars + 🐇🌙 Moon Rabbit!"),
    ]
    for thresh, tier, preview in thresholds:
        if current_total < thresh:
            need = thresh - current_total
            return f"\n\n📈 Top up <b>Rp {need:,}</b> lagi → dapat bonus: {preview}"
    return ""


# ╔══════════════════════════════════════════════════════════════════╗
# ║                     🎣 AQUA TAILS EVENT                         ║
# ╚══════════════════════════════════════════════════════════════════╝
# SQL (jalankan sekali di Supabase):
# create table aqua_sessions (
#   id bigserial primary key,
#   scheduled_at timestamptz not null,
#   status text not null default 'open',
#   created_by bigint not null,
#   created_at timestamptz default now()
# );
# create table aqua_players (
#   id bigserial primary key,
#   session_id bigint references aqua_sessions(id),
#   user_id bigint not null,
#   pet_id bigint not null,
#   energy int default 50,
#   area text default null,
#   area_found jsonb default '[]',
#   session_fish text default null,
#   inventory jsonb default '{}',
#   last_explore_at timestamptz,
#   coins_earned int default 0,
#   unique(session_id, user_id)
# );
# ALTER TABLE users ADD COLUMN IF NOT EXISTS aqua_topup_total int default 0;

AQUA_FORCE_SUB_ENABLED   = False
AQUA_TOPUP_BONUS_ACTIVE  = False
AQUA_MAX_ENERGY          = 50
AQUA_EXPLORE_COST        = 1
AQUA_EXPLORE_COOLDOWN_S  = 10
AQUA_MAX_INV             = 40

AQUA_AREAS = {
    "danau": {"name": "🏞️ Danau",  "emoji": "🏞️"},
    "teluk": {"name": "🌊 Teluk",  "emoji": "🌊"},
    "sungai":{"name": "🌿 Sungai", "emoji": "🌿"},
    "laut":  {"name": "🌊 Laut",   "emoji": "🌊"},
}
AQUA_AREA_FIND_CHANCE = 0.50

AQUA_DANAU_ITEMS = {
    "ikan_koi":  {"name": "Ikan Koi",  "emoji": "🐟", "type": "pet_fish", "chance": 0.08},
    "ikan_lele": {"name": "Ikan Lele", "emoji": "🐠", "type": "food",     "chance": 0.35},
    "ikan_mas":  {"name": "Ikan Mas",  "emoji": "🐡", "type": "food",     "chance": 0.30},
    "ikan_nila": {"name": "Ikan Nila", "emoji": "🐟", "type": "food",     "chance": 0.25},
}
AQUA_TELUK_ITEMS = {
    "rumput_laut":    {"name": "Rumput Laut",    "emoji": "🌿", "type": "food",      "chance": 0.40},
    "kerang_mutiara": {"name": "Kerang Mutiara", "emoji": "🦪", "type": "food_rare", "chance": 0.15},
    "ubur_ubur":      {"name": "Ubur-ubur",      "emoji": "🪼", "type": "food_rare", "chance": 0.12},
    "pil_aqua":       {"name": "Pil Aqua",       "emoji": "💊", "type": "pill",      "chance": 0.07},
    "pil_stamina":    {"name": "Pil Stamina",    "emoji": "⚡", "type": "pill",      "chance": 0.05},
    "pil_mood_aqua":  {"name": "Pil Mood",       "emoji": "😊", "type": "pill",      "chance": 0.06},
}
AQUA_SUNGAI_ITEMS = {
    "sampah_plastik":  {"name": "Sampah Plastik",   "emoji": "🗑️", "type": "trash", "chance": 0.50, "coin": 5},
    "sampah_kaca":     {"name": "Pecahan Kaca",     "emoji": "🔷", "type": "trash", "chance": 0.35, "coin": 5},
    "sampah_logam":    {"name": "Logam Rongsokan",  "emoji": "⚙️", "type": "trash", "chance": 0.25, "coin": 5},
    "emas_tersembunyi":{"name": "Emas Tersembunyi", "emoji": "🥇", "type": "trash", "chance": 0.04, "coin": 50},
}
AQUA_LAUT_ITEMS = {
    "teri_asin":      {"name": "Teri Asin",     "emoji": "🐟", "type": "food",     "chance": 0.35},
    "cumi_cumi":      {"name": "Cumi-cumi",     "emoji": "🦑", "type": "food",     "chance": 0.28},
    "ikan_biru":      {"name": "Blue Fin",      "emoji": "🐋", "type": "pet_fish", "chance": 0.01, "ability": "work_3x",   "ability_name": "Triple Reward"},
    "ikan_emas_laut": {"name": "Golden Marlin", "emoji": "🌟", "type": "pet_fish", "chance": 0.02, "ability": "inv_double", "ability_name": "Double Inventory"},
    "ikan_petir":     {"name": "Thunder Eel",   "emoji": "⚡", "type": "pet_fish", "chance": 0.04, "ability": "daily_coin","ability_name": "Daily Coin"},
}
AQUA_ALL_POOL = {**AQUA_DANAU_ITEMS, **AQUA_TELUK_ITEMS, **AQUA_SUNGAI_ITEMS, **AQUA_LAUT_ITEMS}

AQUA_SIREN_CHANCE       = 0.05
AQUA_SIREN_CATCH_CHANCE = 0.30
AQUA_SIREN_ITEMS_LOST   = 2

def _aqua_tier(total: int) -> str:
    if total >= 25000: return "ultra"
    if total >= 20000: return "legendary"
    if total >= 10000: return "rare"
    if total >= 5000:  return "uncommon"
    return "common"



def _aqua_topup_bonus_info() -> str:
    return (
        "\n\n🎣 <b>Bonus Aqua Tails (kumulatif):</b>\n"
        "⚪ 2k–5k → Makanan laut (common)\n"
        "🔵 5k–10k → + Kerang, Ubur-ubur, Pil Mood\n"
        "🔴 10k–20k → + Pil Aqua & Pil Stamina\n"
        "🟡 20k–25k → + 1 pet eksklusif acak\n"
        "🌊 25k+ → + 🐋🌟⚡ <b>Semua pet eksklusif!</b>"
    )
AQUA_ENTRY_COST       = 1000

async def aqua_get_session() -> dict | None:
    """Ambil session aqua yang aktif (open/active)"""
    res = await sb("GET", "aqua_sessions", {
        "status": "in.(open,active)",
        "order": "scheduled_at.asc",
        "limit": "1"
    })
    return res[0] if res else None

async def aqua_get_open_session() -> dict | None:
    """Ambil session yang sedang active (event berlangsung)"""
    res = await sb("GET", "aqua_sessions", {
        "status": "eq.active",
        "order": "scheduled_at.asc",
        "limit": "1"
    })
    return res[0] if res else None

async def aqua_get_player(session_id: int, user_id: int) -> dict | None:
    res = await sb("GET", "aqua_players", {"session_id": f"eq.{session_id}", "user_id": f"eq.{user_id}"})
    return res[0] if res else None

async def aqua_update_player(session_id: int, user_id: int, data: dict):
    await sb("PATCH", "aqua_players", {"session_id": f"eq.{session_id}", "user_id": f"eq.{user_id}"}, data)

async def aqua_join(session_id: int, user_id: int, pet_id: int):
    await sb("POST", "aqua_players", {}, {
        "session_id": session_id, "user_id": user_id, "pet_id": pet_id,
        "energy": AQUA_MAX_ENERGY, "area": None, "area_found": [],
        "session_fish": None, "inventory": {}, "last_explore_at": None, "coins_earned": 0,
    })

def _aqua_roll_area() -> str | None:
    if random.random() < AQUA_AREA_FIND_CHANCE:
        return random.choice(list(AQUA_AREAS.keys()))
    return None

def _aqua_roll_item(area: str, session_fish: str | None) -> dict | None:
    pool = {"danau": AQUA_DANAU_ITEMS, "teluk": AQUA_TELUK_ITEMS,
            "sungai": AQUA_SUNGAI_ITEMS, "laut": AQUA_LAUT_ITEMS}.get(area, {})
    candidates = []
    for key, info in pool.items():
        if info["type"] == "pet_fish" and session_fish is not None:
            continue
        if random.random() < info["chance"]:
            candidates.append((key, info))
    if not candidates: return None
    key, info = random.choice(candidates)
    return {"key": key, **info}

async def _aqua_max_inv(pet_id: int) -> int:
    """Max inventory, 2x kalau pet yang dibawa ke event adalah Golden Marlin (inv_double)"""
    if not pet_id:
        return AQUA_MAX_INV
    pet = await get_pet_by_id(pet_id)
    if pet and pet.get("special_ability") == "inv_double":
        return AQUA_MAX_INV * 2
    return AQUA_MAX_INV

def _aqua_inv_count(inv: dict) -> int:
    return sum(v for v in inv.values() if isinstance(v, int))

def _aqua_inv_add(inv: dict, key: str, qty: int = 1, max_inv: int = AQUA_MAX_INV) -> bool:
    if _aqua_inv_count(inv) >= max_inv: return False
    inv[key] = (inv.get(key) or 0) + qty
    return True

async def aqua_show_main(msg_or_q, user, sess: dict, player: dict):
    energy    = player.get("energy", AQUA_MAX_ENERGY)
    area      = player.get("area")
    area_found= player.get("area_found") or []
    inv       = player.get("inventory") or {}
    coins     = player.get("coins_earned", 0)
    max_inv   = await _aqua_max_inv(player.get("pet_id") or 0)
    inv_count = _aqua_inv_count(inv)
    area_txt  = AQUA_AREAS.get(area, {}).get("name", "❓ Belum ada") if area else "❓ Belum nemuin area"
    energy_bar= "⚡" * min(10, energy // 5) + "▪" * (10 - min(10, energy // 5))
    cmd_hint = f"📍 Di <b>{area_txt}</b> — /mancing untuk mancing, /jalan untuk pindah" if area else "🚶 Ketik /jalan untuk cari area"
    txt = (f"🎣 <b>Aqua Tails</b>\n━━━━━━━━━━━━━━━\n\n"
           f"⚡ Energy: <b>{energy}/{AQUA_MAX_ENERGY}</b> [{energy_bar}]\n"
           f"📍 Area: <b>{area_txt}</b>\n"
           f"🗺️ Area ditemukan: <b>{len(area_found)}/4</b>\n"
           f"🎒 Inventori: <b>{inv_count}/{max_inv}</b>\n"
           f"🪙 Koin didapat: <b>{coins:,}</b>\n\n"
           f"{cmd_hint}")
    kb = [
        [InlineKeyboardButton("🎒 Inventori", callback_data=f"aqua_inv_{sess['id']}"),
         InlineKeyboardButton("🗺️ Area", callback_data=f"aqua_areas_{sess['id']}")],
    ]
    rm = InlineKeyboardMarkup(kb)
    if hasattr(msg_or_q, 'edit_message_text'):
        await msg_or_q.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=rm)
    else:
        await msg_or_q.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=rm)

async def aqua_jalan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ jalan — jalan-jalan cari area (hanya kalau belum di area)"""
    user = update.effective_user
    sess = await aqua_get_session()
    if not sess or sess["status"] != "active":
        await update.message.reply_text("🎣 Event Aqua Tails belum/sudah selesai!"); return
    player = await aqua_get_player(sess["id"], user.id)
    if not player:
        await update.message.reply_text("❌ Kamu belum terdaftar! Daftar dulu via /aquatails."); return
    if not player.get("pet_id") or player["pet_id"] == 0:
        await update.message.reply_text("❌ Pilih pet dulu lewat /mancing!"); return
    # Kalau masih di area, harus keluar dulu
    if player.get("area"):
        # Otomatis keluar area dan langsung jalan
        await aqua_update_player(sess["id"], user.id, {"area": None})
        player = dict(player)
        player["area"] = None
    # Cek cooldown
    last = player.get("last_explore_at")
    if last:
        elapsed = (now_wib() - parse_dt(last)).total_seconds()
        if elapsed < AQUA_EXPLORE_COOLDOWN_S:
            sisa = int(AQUA_EXPLORE_COOLDOWN_S - elapsed)
            await update.message.reply_text(f"⏳ Tunggu <b>{sisa} detik</b> lagi sebelum jalan!", parse_mode=ParseMode.HTML); return
    energy = player.get("energy", AQUA_MAX_ENERGY)
    if energy <= 0:
        await aqua_update_player(sess["id"], user.id, {"energy": AQUA_MAX_ENERGY, "last_explore_at": now_wib().isoformat()})
        await update.message.reply_text("💤 Energy habis! Udah direset penuh. Coba lagi~"); return
    # Siren event
    if random.random() < AQUA_SIREN_CHANCE:
        # Kirim via inline keyboard
        await aqua_update_player(sess["id"], user.id, {
            "energy": max(0, energy - 1), "last_explore_at": now_wib().isoformat()
        })
        await update.message.reply_text(
            "🧜 <b>SIREN MUNCUL!</b>\n━━━━━━━━━━━━━━━\n\n"
            "Dari balik ombak muncul sosok Siren yang menggoda...\n"
            "🎵 Nyanyiannya membuatmu terpesona!\n\n"
            "<b>Apa yang kamu lakukan?</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎣 Coba Tangkap Siren!", callback_data=f"aqua_siren_catch_{sess['id']}")],
                [InlineKeyboardButton("💨 Kabur!", callback_data=f"aqua_siren_run_{sess['id']}")],
            ])); return
    new_energy  = max(0, energy - 1)
    update_data = {"energy": new_energy, "last_explore_at": now_wib().isoformat()}
    area_found  = list(player.get("area_found") or [])
    new_area    = _aqua_roll_area()
    if new_area and new_area not in area_found:
        area_found.append(new_area)
        update_data["area_found"] = area_found
        update_data["area"] = new_area
        msg = (f"🚶 Jalan-jalan...\n\n"
               f"🗺️ <b>Area baru: {AQUA_AREAS[new_area]['name']}!</b>\n"
               f"Gunakan /mancing untuk mancing disini~\n\n"
               f"⚡ Energy: <b>{new_energy}/{AQUA_MAX_ENERGY}</b>")
    elif new_area:
        update_data["area"] = new_area
        msg = (f"🚶 Jalan-jalan...\n\n"
               f"📍 Kamu berada di <b>{AQUA_AREAS[new_area]['name']}</b>\n"
               f"Gunakan /mancing untuk mancing disini~\n\n"
               f"⚡ Energy: <b>{new_energy}/{AQUA_MAX_ENERGY}</b>")
    else:
        msg = (f"🚶 Jalan-jalan...\n\n"
               f"🌊 Belum nemuin area. Coba /jalan lagi!\n\n"
               f"⚡ Energy: <b>{new_energy}/{AQUA_MAX_ENERGY}</b>")
    await aqua_update_player(sess["id"], user.id, update_data)
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def aqua_mancing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mancing — mancing di area saat ini (harus sudah di area)"""
    user = update.effective_user
    sess = await aqua_get_session()
    if not sess or sess["status"] != "active":
        await update.message.reply_text("🎣 Event Aqua Tails belum/sudah selesai!"); return
    player = await aqua_get_player(sess["id"], user.id)
    if not player:
        await update.message.reply_text(
            "❌ Kamu belum terdaftar!\n"
            "Daftar dulu via /aquatails (biaya 1.000🪙)"); return
    if not player.get("pet_id") or player["pet_id"] == 0:
        await update.message.reply_text(
            "❌ Pet belum dipilih! Hubungi admin."); return
    if not player.get("area"):
        await update.message.reply_text(
            "❌ Kamu belum di area manapun!\n\n"
            "Gunakan /jalan dulu untuk nemuin area mancing~"); return
    # Cek cooldown
    last = player.get("last_explore_at")
    if last:
        elapsed = (now_wib() - parse_dt(last)).total_seconds()
        if elapsed < AQUA_EXPLORE_COOLDOWN_S:
            sisa = int(AQUA_EXPLORE_COOLDOWN_S - elapsed)
            await update.message.reply_text(f"⏳ Tunggu <b>{sisa} detik</b> lagi!", parse_mode=ParseMode.HTML); return
    energy = player.get("energy", 0)
    if energy <= 0:
        await update.message.reply_text(
            "💤 Energy habis!\n\n"
            "Ketik /jalan untuk reset energy dan mulai lagi~"); return
    area        = player["area"]
    inv         = dict(player.get("inventory") or {})
    session_fish= player.get("session_fish")
    item        = _aqua_roll_item(area, session_fish)
    update_data = {"energy": max(0, energy - 1), "last_explore_at": now_wib().isoformat()}
    result_txt  = ""
    if item is None:
        result_txt = "🌊 Tidak dapat apa-apa kali ini..."
    elif item["type"] == "trash":
        coin = item.get("coin", 5)
        update_data["coins_earned"] = (player.get("coins_earned") or 0) + coin
        await add_koin(user.id, coin, "aqua_mancing")
        result_txt = f"{item['emoji']} <b>{item['name']}</b> → auto jual <b>+{coin} 🪙</b>!"
    elif item["type"] == "pet_fish":
        if _aqua_inv_count(inv) >= await _aqua_max_inv(player.get("pet_id") or 0):
            result_txt = f"🎒 Inventori penuh! {item['emoji']} <b>{item['name']}</b> kabur..."
        else:
            energy_cost = random.randint(3, 8)
            update_data["energy"] = max(0, energy - energy_cost)
            update_data["session_fish"] = item["key"]
            # Langsung jadi pet beneran
            ability = item.get("ability", "")
            await sb("POST", "pets", {}, {
                "owner1_id": user.id, "owner2_id": None,
                "name": item["name"], "pet_type": item["key"],
                "xp": 0, "hunger": 0, "happiness": 100, "health": 100,
                "poop_count": 0, "is_sleeping": False, "is_dirty": False,
                "is_missing": False, "is_married": False, "is_child": False,
                "special_ability": ability,
                "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
            })
            ability_txt = f"\n✨ Ability: <b>{item.get('ability_name','?')}</b>" if ability else ""
            result_txt = (f"🎣 <b>TANGKAP! {item['emoji']} {item['name']}</b>{ability_txt}\n"
                          f"🐾 Langsung jadi petmu!\n"
                          f"⚡ Energy -{energy_cost}")
    else:
        if _aqua_inv_count(inv) >= await _aqua_max_inv(player.get("pet_id") or 0):
            result_txt = f"🎒 Inventori penuh! {item['emoji']} <b>{item['name']}</b> terbuang..."
        else:
            _aqua_inv_add(inv, item["key"], max_inv=await _aqua_max_inv(player.get("pet_id") or 0))
            update_data["inventory"] = inv
            result_txt = f"{item['emoji']} Dapat <b>{item['name']}</b>!"
    await aqua_update_player(sess["id"], user.id, update_data)
    new_energy = update_data.get("energy", energy)
    area_name  = AQUA_AREAS[area]["name"]
    await update.message.reply_text(
        f"🎣 Mancing di <b>{area_name}</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{result_txt}\n\n"
        f"⚡ Energy: <b>{new_energy}/{AQUA_MAX_ENERGY}</b> | "
        f"🎒 <b>{_aqua_inv_count(update_data.get('inventory', inv))}/{max_inv}</b>\n\n"
        f"<i>/mancing lagi atau /jalan untuk pindah area</i>",
        parse_mode=ParseMode.HTML)

async def aqua_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sess = await aqua_get_session()
    if not sess:
        await update.message.reply_text("🎣 <b>Aqua Tails</b>\n\nTidak ada event aktif saat ini.", parse_mode=ParseMode.HTML); return

    now      = now_wib()
    sched    = parse_dt(sess["scheduled_at"])
    status   = sess["status"]
    end_time = sched + timedelta(minutes=AQUA_DURATION_MINUTES)

    # Fase pendaftaran
    if status == "open":
        sisa = fmt_countdown(sched)
        player = await aqua_get_player(sess["id"], user.id)
        if player:
            await update.message.reply_text(
                f"🎣 <b>Aqua Tails</b>\n━━━━━━━━━━━━━━━\n\n"
                f"✅ Kamu sudah terdaftar!\n\n"
                f"⏰ Event mulai: <b>{sched.strftime('%H:%M')} WIB</b>\n"
                f"⏳ Mulai dalam: <b>{sisa}</b>\n"
                f"🏁 Selesai: <b>{end_time.strftime('%H:%M')} WIB</b>\n\n"
                f"<i>Santai dulu, notif dikirim pas event mulai~</i>",
                parse_mode=ParseMode.HTML); return
        # Belum daftar
        u = await get_user(user.id)
        koin = u.get("koin", 0) if u else 0
        await update.message.reply_text(
            f"🎣 <b>Aqua Tails</b>\n━━━━━━━━━━━━━━━\n\n"
            f"🌊 Jelajahi 4 area: Danau, Teluk, Sungai, Laut\n"
            f"⚡ Energy max: {AQUA_MAX_ENERGY} | 🎒 Inventori: {AQUA_MAX_INV}\n"
            f"⚠️ Hati-hati Siren!\n\n"
            f"⏰ Event mulai: <b>{sched.strftime('%H:%M')} WIB</b>\n"
            f"⏳ Mulai dalam: <b>{sisa}</b>\n"
            f"💰 Biaya daftar: <b>1.000 🪙</b>\n"
            f"💳 Koin kamu: <b>{koin:,} 🪙</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Daftar Sekarang (1.000🪙)", callback_data=f"aqua_register_{sess['id']}")
            ]])); return

    # Fase active — event berlangsung
    if status == "active":
        sisa_event = fmt_countdown(end_time)
        player = await aqua_get_player(sess["id"], user.id)
        if not player:
            await update.message.reply_text(
                f"🎣 <b>Aqua Tails</b> sedang berlangsung!\n\n"
                f"⏳ Selesai dalam: <b>{sisa_event}</b>\n\n"
                f"❌ Pendaftaran sudah ditutup.",
                parse_mode=ParseMode.HTML); return
        if not player.get("pet_id"):
            # Sudah daftar tapi belum pilih pet
            pets = await get_user_pets(user.id)
            active = [p for p in pets if not p.get("is_missing")]
            kb = [[InlineKeyboardButton(
                f"{PETS.get(p['pet_type'],{}).get('emoji','🐾')} {p['name']} (Lv.{calc_level(p.get('xp',0))})",
                callback_data=f"aqua_join_{sess['id']}_{p['id']}"
            )] for p in active[:8]]
            await update.message.reply_text(
                "🎣 <b>Aqua Tails</b> — Pilih pet yang ikut mancing!",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb)); return
        await aqua_show_main(update.message, user, sess, player)

async def aqua_siren_event(q, user, sess: dict, player: dict, context):
    sess_id = sess["id"]
    energy  = player.get("energy", 0)
    await aqua_update_player(sess_id, user.id, {
        "energy": max(0, energy - AQUA_EXPLORE_COST),
        "last_explore_at": now_wib().isoformat()
    })
    await q.edit_message_text(
        "🧜 <b>SIREN MUNCUL!</b>\n━━━━━━━━━━━━━━━\n\n"
        "Dari balik ombak muncul sosok Siren yang menggoda...\n"
        "🎵 Nyanyiannya membuatmu terpesona!\n\n"
        "<b>Apa yang kamu lakukan?</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎣 Coba Tangkap Siren!", callback_data=f"aqua_siren_catch_{sess_id}")],
            [InlineKeyboardButton("💨 Kabur!", callback_data=f"aqua_siren_run_{sess_id}")],
        ]))

async def aqua_callback(q, user, data: str, context):
    if data.startswith("aqua_register_"):
        sess_id = int(data[14:])
        sess = await aqua_get_session()
        if not sess or sess["id"] != sess_id or sess["status"] != "open":
            await q.answer("❌ Pendaftaran sudah ditutup!", show_alert=True); return
        existing = await aqua_get_player(sess_id, user.id)
        if existing:
            await q.answer("✅ Kamu sudah terdaftar!", show_alert=True); return
        ok = await spend_koin(user.id, AQUA_ENTRY_COST, "aqua_daftar")
        if not ok:
            await q.answer(f"❌ Koin tidak cukup! Butuh {AQUA_ENTRY_COST:,} 🪙", show_alert=True); return
        sched = parse_dt(sess["scheduled_at"])
        # Langsung minta pilih pet
        pets = await get_user_pets(user.id)
        active = [p for p in pets if not p.get("is_missing")]
        if not active:
            await q.answer("❌ Kamu belum punya pet!", show_alert=True); return
        kb = [[InlineKeyboardButton(
            f"{PETS.get(p['pet_type'],{}).get('emoji','🐾')} {p['name']} (Lv.{calc_level(p.get('xp',0))})",
            callback_data=f"aqua_petpick_{sess_id}_{p['id']}"
        )] for p in active[:8]]
        await q.edit_message_text(
            f"✅ Pembayaran 1.000🪙 berhasil!\n\n"
            f"🎣 Pilih pet yang ikut mancing di <b>Aqua Tails</b>:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("aqua_petpick_"):
        p = data[13:].split("_")
        sess_id, pet_id = int(p[0]), int(p[1])
        sess = await aqua_get_session()
        if not sess or sess["id"] != sess_id:
            await q.answer("❌ Session tidak valid!", show_alert=True); return
        existing = await aqua_get_player(sess_id, user.id)
        if existing:
            await q.answer("✅ Sudah terdaftar!", show_alert=True); return
        pet = await get_pet_by_id(pet_id)
        if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
            await q.answer("❌ Bukan petmu!", show_alert=True); return
        await sb("POST", "aqua_players", {}, {
            "session_id": sess_id, "user_id": user.id, "pet_id": pet_id,
            "energy": AQUA_MAX_ENERGY, "area": None, "area_found": [],
            "session_fish": None, "inventory": {}, "last_explore_at": None, "coins_earned": 0,
        })
        sched = parse_dt(sess["scheduled_at"])
        end_time = sched + timedelta(minutes=AQUA_DURATION_MINUTES)
        info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
        await q.edit_message_text(
            f"✅ <b>Berhasil daftar Aqua Tails!</b>\n━━━━━━━━━━━━━━━\n\n"
            f"{info['emoji']} <b>{pet['name']}</b> siap mancing!\n\n"
            f"⏰ Event mulai jam <b>{sched.strftime('%H:%M')} WIB</b>\n"
            f"🏁 Selesai jam <b>{end_time.strftime('%H:%M')} WIB</b>\n\n"
            f"<i>Kamu akan dapat notif saat event dimulai~</i>",
            parse_mode=ParseMode.HTML)
        # Log ke GC
        total_now = await sb("GET", "aqua_players", {"session_id": f"eq.{sess_id}", "select": "user_id"})
        total_now = len(total_now) if total_now else 1
        await log(context,
            f"🎣 <b>Aqua Tails — Daftar Baru!</b>\n"
            f"👤 {fmt_user(user)}\n"
            f"🐾 Pet: {info['emoji']} <b>{pet['name']}</b>\n"
            f"👥 Total peserta: <b>{total_now}</b>")
        return

    if data.startswith("aqua_join_"):
        p = data[10:].split("_")
        sess_id, pet_id = int(p[0]), int(p[1])
        sess = await aqua_get_session()
        if not sess or sess["id"] != sess_id or sess["status"] != "active":
            await q.answer("❌ Event belum/sudah selesai!", show_alert=True); return
        existing = await aqua_get_player(sess_id, user.id)
        if not existing:
            await q.answer("❌ Kamu tidak terdaftar!", show_alert=True); return
        if existing.get("pet_id") and existing["pet_id"] != 0:
            await aqua_show_main(q, user, sess, existing); return
        pet = await get_pet_by_id(pet_id)
        if not pet or (pet.get("owner1_id") != user.id and pet.get("owner2_id") != user.id):
            await q.answer("❌ Bukan petmu!", show_alert=True); return
        await aqua_update_player(sess_id, user.id, {"pet_id": pet_id})
        player = await aqua_get_player(sess_id, user.id)
        await aqua_show_main(q, user, sess, player)

    elif data.startswith("aqua_explore_"):
        sess_id = int(data[13:])
        sess = await aqua_get_session()
        if not sess or sess["id"] != sess_id or sess["status"] != "active":
            await q.answer("❌ Event sudah selesai!", show_alert=True); return
        player = await aqua_get_player(sess_id, user.id)
        if not player: await q.answer("❌ Belum join!", show_alert=True); return
        if not player.get("pet_id") or player["pet_id"] == 0:
            # Belum pilih pet, redirect ke pilih pet
            pets = await get_user_pets(user.id)
            active = [p for p in pets if not p.get("is_missing")]
            kb = [[InlineKeyboardButton(
                f"{PETS.get(p['pet_type'],{}).get('emoji','🐾')} {p['name']} (Lv.{calc_level(p.get('xp',0))})",
                callback_data=f"aqua_join_{sess_id}_{p['id']}"
            )] for p in active[:8]]
            await q.edit_message_text(
                "🎣 <b>Aqua Tails</b> — Pilih pet yang ikut mancing dulu!",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb)); return
        last = player.get("last_explore_at")
        if last:
            elapsed = (now_wib() - parse_dt(last)).total_seconds()
            if elapsed < AQUA_EXPLORE_COOLDOWN_S:
                await q.answer(f"⏳ Tunggu {int(AQUA_EXPLORE_COOLDOWN_S - elapsed)} detik lagi!", show_alert=True); return
        energy = player.get("energy", AQUA_MAX_ENERGY)
        if energy <= 0:
            await aqua_update_player(sess_id, user.id, {
                "energy": AQUA_MAX_ENERGY, "area": None, "last_explore_at": now_wib().isoformat()
            })
            await q.answer("💤 Energy habis! Direset penuh, tapi harus cari area lagi~", show_alert=True)
            player = await aqua_get_player(sess_id, user.id)
            await aqua_show_main(q, user, sess, player); return
        if random.random() < AQUA_SIREN_CHANCE:
            await aqua_siren_event(q, user, sess, player, context); return
        new_energy  = max(0, energy - AQUA_EXPLORE_COST)
        update_data = {"energy": new_energy, "last_explore_at": now_wib().isoformat()}
        area_found  = list(player.get("area_found") or [])
        new_area    = _aqua_roll_area()
        msg_extra   = ""
        if new_area and new_area not in area_found:
            area_found.append(new_area)
            update_data["area_found"] = area_found
            update_data["area"] = new_area
            msg_extra = f"\n\n🗺️ <b>Area baru: {AQUA_AREAS[new_area]['name']}!</b>\nAyo mancing disini~"
        elif new_area:
            update_data["area"] = new_area
            msg_extra = f"\n\n📍 Kamu berada di <b>{AQUA_AREAS[new_area]['name']}</b>"
        else:
            msg_extra = "\n\n🌊 Terus berjalan... belum nemuin area."
        await aqua_update_player(sess_id, user.id, update_data)
        energy_bar = "⚡" * min(10, new_energy // 5) + "▪" * (10 - min(10, new_energy // 5))
        await q.edit_message_text(
            f"🚶 <b>Jalan-jalan...</b>{msg_extra}\n\n"
            f"⚡ Energy: <b>{new_energy}/{AQUA_MAX_ENERGY}</b> [{energy_bar}]",
            parse_mode=ParseMode.HTML)

    elif data.startswith("aqua_fish_"):
        sess_id = int(data[10:])
        sess = await aqua_get_session()
        if not sess or sess["status"] != "active": await q.answer("❌ Event belum/sudah selesai!", show_alert=True); return
        player = await aqua_get_player(sess_id, user.id)
        if not player: await q.answer("❌ Belum join!", show_alert=True); return
        area = player.get("area")
        if not area: await q.answer("❌ Temukan area dulu!", show_alert=True); return
        last = player.get("last_explore_at")
        if last:
            elapsed = (now_wib() - parse_dt(last)).total_seconds()
            if elapsed < AQUA_EXPLORE_COOLDOWN_S:
                await q.answer(f"⏳ Tunggu {int(AQUA_EXPLORE_COOLDOWN_S - elapsed)} detik lagi!", show_alert=True); return
        energy = player.get("energy", 0)
        if energy <= 0: await q.answer("💤 Energy habis!", show_alert=True); return
        inv         = dict(player.get("inventory") or {})
        session_fish= player.get("session_fish")
        item        = _aqua_roll_item(area, session_fish)
        update_data = {"energy": max(0, energy - 1), "last_explore_at": now_wib().isoformat()}
        result_txt  = ""
        if item is None:
            result_txt = "🌊 Tidak dapat apa-apa kali ini..."
        elif item["type"] == "trash":
            coin = item.get("coin", 5)
            update_data["coins_earned"] = (player.get("coins_earned") or 0) + coin
            await add_koin(user.id, coin, "aqua_mancing")
            result_txt = f"{item['emoji']} <b>{item['name']}</b> → auto jual <b>+{coin} 🪙</b>!"
        elif item["type"] == "pet_fish":
            if _aqua_inv_count(inv) >= await _aqua_max_inv(player.get("pet_id") or 0):
                result_txt = f"🎒 Inventori penuh! {item['emoji']} <b>{item['name']}</b> kabur..."
            else:
                energy_cost = random.randint(3, 8)
                update_data["energy"] = max(0, energy - energy_cost)
                update_data["session_fish"] = item["key"]
                ability = item.get("ability", "")
                await sb("POST", "pets", {}, {
                    "owner1_id": user.id, "owner2_id": None,
                    "name": item["name"], "pet_type": item["key"],
                    "xp": 0, "hunger": 0, "happiness": 100, "health": 100,
                    "poop_count": 0, "is_sleeping": False, "is_dirty": False,
                    "is_missing": False, "is_married": False, "is_child": False,
                    "special_ability": ability,
                    "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
                })
                ability_txt = f"\n✨ Ability: <b>{item.get('ability_name','?')}</b>" if ability else ""
                result_txt = (f"🎣 <b>TANGKAP! {item['emoji']} {item['name']}</b>{ability_txt}\n"
                              f"🐾 Langsung jadi petmu!\n"
                              f"⚡ Energy -{energy_cost}")
        else:
            if _aqua_inv_count(inv) >= await _aqua_max_inv(player.get("pet_id") or 0):
                result_txt = f"🎒 Inventori penuh! {item['emoji']} <b>{item['name']}</b> terbuang..."
            else:
                _aqua_inv_add(inv, item["key"], max_inv=await _aqua_max_inv(player.get("pet_id") or 0))
                update_data["inventory"] = inv
                result_txt = f"{item['emoji']} Dapat <b>{item['name']}</b>!"
        await aqua_update_player(sess_id, user.id, update_data)
        new_energy = update_data.get("energy", energy)
        await q.edit_message_text(
            f"🎣 Mancing di <b>{AQUA_AREAS[area]['name']}</b>\n━━━━━━━━━━━━━━━\n\n"
            f"{result_txt}\n\n"
            f"⚡ Energy: <b>{new_energy}/{AQUA_MAX_ENERGY}</b> | "
            f"🎒 <b>{_aqua_inv_count(update_data.get('inventory', inv))}/{max_inv}</b>",
            parse_mode=ParseMode.HTML)

    elif data.startswith("aqua_inv_"):
        sess_id = int(data[9:])
        sess = await aqua_get_session()
        player = await aqua_get_player(sess_id, user.id) if sess else None
        if not player: await q.answer("❌", show_alert=True); return
        inv = player.get("inventory") or {}
        max_inv = await _aqua_max_inv(player.get("pet_id") or 0)
        if not inv:
            txt = "🎒 <b>Inventori Aqua Tails</b>\n\nKosong~ Ayo /mancing dulu!"
        else:
            lines = [f"{AQUA_ALL_POOL.get(k,{}).get('emoji','📦')} {AQUA_ALL_POOL.get(k,{}).get('name',k)}: <b>{v}x</b>"
                     for k,v in inv.items() if isinstance(v,int) and v > 0]
            txt = (f"🎒 <b>Inventori Aqua Tails</b>\n━━━━━━━━━━━━━━━\n\n"
                   + "\n".join(lines)
                   + f"\n\n<i>{_aqua_inv_count(inv)}/{max_inv} slot</i>\n\n"
                   f"🗑️ Hapus item: /aquainv remove &lt;nama item&gt; [qty]\n"
                   f"Contoh: /aquainv remove ikan lele 2")
        await q.edit_message_text(txt, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"aqua_menu_{sess_id}")]]))

    elif data.startswith("aqua_areas_"):
        sess_id = int(data[11:])
        sess = await aqua_get_session()
        player = await aqua_get_player(sess_id, user.id) if sess else None
        if not player: await q.answer("❌", show_alert=True); return
        found = player.get("area_found") or []
        lines = [f"{'✅' if k in found else '❓'} {v['name']}" for k,v in AQUA_AREAS.items()]
        await q.edit_message_text(
            f"🗺️ <b>Area Aqua Tails</b>\n━━━━━━━━━━━━━━━\n\n" + "\n".join(lines)
            + "\n\n<i>Jalan-jalan untuk temukan semua area!</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"aqua_menu_{sess_id}")]]))

    elif data.startswith("aqua_siren_catch_"):
        sess_id = int(data[17:])
        sess = await aqua_get_session()
        player = await aqua_get_player(sess_id, user.id) if sess else None
        if not player: await q.answer("❌", show_alert=True); return
        if random.random() < AQUA_SIREN_CATCH_CHANCE:
            inv = dict(player.get("inventory") or {})
            _aqua_inv_add(inv, "pil_aqua", 2)
            _aqua_inv_add(inv, "kerang_mutiara", 3)
            await aqua_update_player(sess_id, user.id, {"inventory": inv, "last_explore_at": now_wib().isoformat()})
            await q.edit_message_text(
                "🧜 <b>BERHASIL tangkap Siren!</b>\n━━━━━━━━━━━━━━━\n\n"
                "✨ Siren memberikan hadiahnya sebelum kabur~\n"
                "💊 +2 Pil Aqua | 🦪 +3 Kerang Mutiara",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data=f"aqua_menu_{sess_id}")]]))
        else:
            inv  = dict(player.get("inventory") or {})
            keys = [k for k,v in inv.items() if isinstance(v,int) and v > 0]
            lost = []
            for _ in range(min(AQUA_SIREN_ITEMS_LOST, len(keys))):
                if not keys: break
                k = random.choice(keys)
                inv[k] = max(0, inv[k] - 1)
                if inv[k] == 0: del inv[k]
                lost.append(f"{AQUA_ALL_POOL.get(k,{}).get('emoji','📦')} {AQUA_ALL_POOL.get(k,{}).get('name',k)}")
                keys = [k for k,v in inv.items() if isinstance(v,int) and v > 0]
            lost_txt = ", ".join(lost) if lost else "tidak ada"
            await aqua_update_player(sess_id, user.id, {
                "energy": AQUA_MAX_ENERGY, "area": None, "inventory": inv,
                "last_explore_at": now_wib().isoformat()
            })
            await q.edit_message_text(
                "🧜 <b>KECEBUR!</b> Siren kabur...\n━━━━━━━━━━━━━━━\n\n"
                f"💦 Kamu kecebur ke laut!\n"
                f"⚡ Energy habis & direset penuh\n"
                f"❌ Item hilang: {lost_txt}\n\n"
                f"<i>Untung masih selamat~ Ayo mulai lagi!</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data=f"aqua_menu_{sess_id}")]]))

    elif data.startswith("aqua_siren_run_"):
        sess_id = int(data[15:])
        player = await aqua_get_player(sess_id, user.id)
        if player:
            await aqua_update_player(sess_id, user.id, {
                "energy": max(0, (player.get("energy") or 0) - 5),
                "last_explore_at": now_wib().isoformat()
            })
        await q.edit_message_text(
            "💨 Kamu kabur dari Siren!\n\n⚡ -5 energy karena panik.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data=f"aqua_menu_{sess_id}")]]))

    elif data.startswith("aqua_leave_"):
        sess_id = int(data[11:])
        player = await aqua_get_player(sess_id, user.id)
        if player:
            await aqua_update_player(sess_id, user.id, {"area": None})
        await q.edit_message_text(
            "🚪 Keluar dari area.\n\nGunakan /jalan untuk cari area baru!",
            parse_mode=ParseMode.HTML)
        sess_id = int(data[10:])
        sess = await aqua_get_session()
        if not sess or sess["status"] != "active": await q.answer("❌ Event belum/sudah selesai!", show_alert=True); return
        player = await aqua_get_player(sess_id, user.id)
        if not player: await q.answer("❌ Belum join!", show_alert=True); return
        await aqua_show_main(q, user, sess, player)

async def cmd_aqua_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    sess = await aqua_get_open_session()
    if not sess:
        await update.message.reply_text("❌ Tidak ada event Aqua Tails aktif."); return
    player = await aqua_get_player(sess["id"], user.id)
    if not player:
        await update.message.reply_text("❌ Kamu belum join event!"); return
    inv = dict(player.get("inventory") or {})
    if args and args[0].lower() == "remove":
        if len(args) < 2:
            await update.message.reply_text("Usage: /aquainv remove &lt;nama item&gt; [qty]", parse_mode=ParseMode.HTML); return
        # Pisah qty di akhir jika ada angka
        rest = args[1:]
        qty = 1
        if rest and rest[-1].isdigit():
            qty = int(rest[-1])
            rest = rest[:-1]
        raw = " ".join(rest).lower().strip()
        # Cari key: coba exact key dulu, lalu spasi→underscore, lalu match by name
        key = None
        if raw in inv and (inv.get(raw) or 0) > 0:
            key = raw
        elif raw.replace(" ", "_") in inv and (inv.get(raw.replace(" ", "_")) or 0) > 0:
            key = raw.replace(" ", "_")
        else:
            for k, info in AQUA_ALL_POOL.items():
                if info.get("name", "").lower() == raw and k in inv and (inv.get(k) or 0) > 0:
                    key = k; break
        if not key:
            await update.message.reply_text(f"❌ Item <b>{raw}</b> tidak ada di inventori.", parse_mode=ParseMode.HTML); return
        inv[key] = max(0, inv[key] - qty)
        if inv[key] == 0: del inv[key]
        await aqua_update_player(sess["id"], user.id, {"inventory": inv})
        await update.message.reply_text(f"✅ -{qty}x <code>{key}</code> dihapus.", parse_mode=ParseMode.HTML); return
    if not inv:
        await update.message.reply_text("🎒 Inventori Aqua Tails kosong!"); return
    lines = [f"{AQUA_ALL_POOL.get(k,{}).get('emoji','📦')} <b>{AQUA_ALL_POOL.get(k,{}).get('name',k)}</b>: {v}x"
             for k,v in inv.items() if isinstance(v,int) and v > 0]
    await update.message.reply_text(
        f"🎒 <b>Inventori Aqua Tails</b>\n━━━━━━━━━━━━━━━\n\n" + "\n".join(lines)
        + f"\n\n<i>{_aqua_inv_count(inv)}/{AQUA_MAX_INV} slot</i>\n\n"
        f"🗑️ Hapus: /aquainv remove &lt;nama item&gt; [qty]\n"
        f"Contoh: /aquainv remove ikan mas 1",
        parse_mode=ParseMode.HTML)

async def job_aqua_tick(context: ContextTypes.DEFAULT_TYPE):
    """Tiap menit: cek aqua session — auto activate & auto close"""
    try:
        now = now_wib()
        # Cek session open yang sudah waktunya → activate
        opening = await sb("GET", "aqua_sessions", {
            "status": "eq.open",
            "scheduled_at": f"lte.{now.isoformat()}",
            "limit": "1"
        })
        for sess in (opening or []):
            await sb("PATCH", "aqua_sessions", {"id": f"eq.{sess['id']}"}, {"status": "active"})
            # Notif semua peserta
            players = await sb("GET", "aqua_players", {"session_id": f"eq.{sess['id']}", "select": "user_id"}) or []
            end_time = parse_dt(sess["scheduled_at"]) + timedelta(minutes=AQUA_DURATION_MINUTES)
            for p in players:
                try:
                    await context.bot.send_message(p["user_id"],
                        f"🎣 <b>Aqua Tails dimulai!</b>\n"
                        f"⏰ Selesai jam <b>{end_time.strftime('%H:%M')} WIB</b>\n\n"
                        f"Ketik /mancing untuk mulai!",
                        parse_mode=ParseMode.HTML)
                except: pass
            logger.info(f"Aqua Tails session {sess['id']} → ACTIVE, {len(players)} peserta")

        # Cek session active yang sudah habis → close
        closing = await sb("GET", "aqua_sessions", {
            "status": "eq.active",
            "scheduled_at": f"lte.{(now - timedelta(minutes=AQUA_DURATION_MINUTES)).isoformat()}",
            "limit": "1"
        })
        for sess in (closing or []):
            await sb("PATCH", "aqua_sessions", {"id": f"eq.{sess['id']}"}, {"status": "closed"})
            players = await sb("GET", "aqua_players", {
                "session_id": f"eq.{sess['id']}",
                "select": "user_id,coins_earned,inventory,session_fish"
            }) or []
            for p in players:
                try:
                    inv_aqua = p.get("inventory") or {}
                    coins    = p.get("coins_earned", 0)
                    # Transfer inventory aqua ke inventory user biasa
                    if inv_aqua:
                        user_inv = await get_inv(p["user_id"])
                        for key, qty in inv_aqua.items():
                            if isinstance(qty, int) and qty > 0:
                                user_inv[key] = (user_inv.get(key) or 0) + qty
                        await set_inv(p["user_id"], user_inv)
                    # Susun ringkasan item
                    if inv_aqua:
                        item_lines = []
                        for key, qty in inv_aqua.items():
                            if isinstance(qty, int) and qty > 0:
                                info = AQUA_ALL_POOL.get(key, {})
                                item_lines.append(f"{info.get('emoji','📦')} {info.get('name', key)}: {qty}x")
                        item_txt = "\n".join(item_lines)
                        inv_txt  = f"\n\n🎒 <b>Item masuk inventori:</b>\n{item_txt}"
                    else:
                        inv_txt = "\n\n🎒 Tidak dapat item kali ini."
                    await context.bot.send_message(p["user_id"],
                        f"🎣 <b>Aqua Tails selesai!</b>\n━━━━━━━━━━━━━━━\n"
                        f"🪙 Koin dari event: <b>{coins:,}</b>"
                        f"{inv_txt}\n\n"
                        f"<i>Sampai event berikutnya~</i>",
                        parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.warning(f"Aqua close notif error uid={p.get('user_id')}: {e}")
            logger.info(f"Aqua Tails session {sess['id']} → CLOSED, {len(players)} pemain")
    except Exception as e:
        logger.error(f"job_aqua_tick error: {e}")

async def cmd_aqua_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS: await update.message.reply_text("❌ Bukan admin!"); return
    args = context.args
    if not args: await update.message.reply_text("Usage: /aquaset 18:00 atau /aquaset 18:00 2025-05-08"); return
    try:
        h, m = map(int, args[0].split(":"))
        now  = now_wib()
        if len(args) > 1:
            from datetime import date as _date
            d = _date.fromisoformat(args[1])
            sched = now.replace(year=d.year, month=d.month, day=d.day, hour=h, minute=m, second=0, microsecond=0)
        else:
            sched = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if sched <= now: sched += timedelta(days=1)
    except Exception as e:
        await update.message.reply_text(f"❌ Format salah! Contoh: /aquatails 18:00"); return
    end_time = sched + timedelta(minutes=AQUA_DURATION_MINUTES)
    res = await sb("POST", "aqua_sessions", {}, {"scheduled_at": sched.isoformat(), "status": "open", "created_by": user.id})
    sess_id = res[0]["id"] if res else "?"
    await update.message.reply_text(
        f"🎣 <b>Aqua Tails dijadwalkan!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"📋 Pendaftaran: <b>sekarang</b> (1.000🪙)\n"
        f"⏰ Mulai: <b>{sched.strftime('%d %b %H:%M')} WIB</b>\n"
        f"🏁 Selesai: <b>{end_time.strftime('%H:%M')} WIB</b>\n"
        f"ID: <code>{sess_id}</code>",
        parse_mode=ParseMode.HTML)
    await log(context, f"🎣 Aqua Tails dijadwalkan {sched.strftime('%d/%m %H:%M')} oleh {fmt_user(user)}")

async def cmd_aqua_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS: await update.message.reply_text("❌ Bukan admin!"); return
    sess = await aqua_get_session()
    if not sess: await update.message.reply_text("❌ Tidak ada event aktif!"); return
    await sb("PATCH", "aqua_sessions", {"id": f"eq.{sess['id']}"}, {"status": "closed"})
    await update.message.reply_text(f"✅ Aqua Tails ditutup. Session ID: {sess['id']}")
    await log(context, f"🎣 Aqua Tails ditutup oleh {fmt_user(user)}")

async def cmd_aqua_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS: await update.message.reply_text("❌ Bukan admin!"); return

    sess = await aqua_get_open_session()

    # ── Stats topup global ──────────────────────────────────────────────────
    all_users = await sb_get_all("users", {"aqua_topup_total": "gt.0", "order": "aqua_topup_total.desc"}) or []
    total_topup = sum((u.get("aqua_topup_total") or 0) for u in all_users)
    tier_count = {"ultra": 0, "legendary": 0, "rare": 0, "uncommon": 0, "common": 0}
    for u in all_users:
        t = u.get("aqua_topup_total") or 0
        if t >= 25000:   tier_count["ultra"] += 1
        elif t >= 20000: tier_count["legendary"] += 1
        elif t >= 10000: tier_count["rare"] += 1
        elif t >= 5000:  tier_count["uncommon"] += 1
        else:            tier_count["common"] += 1

    lines = ["🎣 <b>AQUA TAILS — STATS</b>\n━━━━━━━━━━━━━━━━━━━━\n"]

    if sess:
        status_label = {
            "open":   "🟢 Open (daftar)",
            "active": "🌊 Aktif",
            "closed": "🔒 Selesai",
        }.get(sess.get("status", ""), sess.get("status", "-"))
        sched = parse_dt(sess["scheduled_at"])
        lines.append(f"📡 <b>Sesi #{sess['id']}</b> — {status_label}")
        lines.append(f"📅 Jadwal: <b>{fmt_wib(sched)}</b>")

        players = await sb_get_all("aqua_players", {"session_id": f"eq.{sess['id']}"}) or []
        lines.append(f"👥 Peserta: <b>{len(players)}</b>\n")

        if players:
            total_coins = sum(p.get("coins_earned") or 0 for p in players)
            total_fish  = sum(1 for p in players if p.get("session_fish"))
            total_items = sum(
                sum(v for v in (p.get("inventory") or {}).values() if isinstance(v, int))
                for p in players
            )
            lines.append(f"🪙 Total koin earned: <b>{total_coins:,}</b>")
            lines.append(f"📦 Total item terkumpul: <b>{total_items}</b>")
            lines.append(f"🐟 Sudah dapat ikan langka: <b>{total_fish}</b>")
            lines.append(f"\n<i>Ketik /aqua_list untuk detail tiap peserta</i>")
        lines.append("")
    else:
        lines.append("📡 <i>Tidak ada sesi aktif saat ini.</i>\n")

    lines.append("💰 <b>Topup Event (Global):</b>")
    lines.append(f"  Total partisipan: <b>{len(all_users)}</b>")
    lines.append(f"  Total topup: <b>{total_topup:,} koin</b>")
    lines.append(f"  🌊 Ultra    (25k+): <b>{tier_count['ultra']}</b>")
    lines.append(f"  🟡 Legendary (20k+): <b>{tier_count['legendary']}</b>")
    lines.append(f"  🔴 Rare     (10k+): <b>{tier_count['rare']}</b>")
    lines.append(f"  🔵 Uncommon  (5k+): <b>{tier_count['uncommon']}</b>")
    lines.append(f"  ⚪ Common    (<5k):  <b>{tier_count['common']}</b>")

    if all_users:
        lines.append("\n🏆 <b>Top 5 Topup:</b>")
        for u in all_users[:5]:
            nama  = safe_html(u.get("nama") or str(u.get("user_id", "?")))
            uname = u.get("username")
            uname_txt = f" @{safe_html(uname)}" if uname else ""
            topup = u.get("aqua_topup_total") or 0
            lines.append(f"  • <b>{nama}</b>{uname_txt} — {topup:,} koin")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_aqua_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AQUA_TOPUP_BONUS_ACTIVE
    user = update.effective_user
    if user.id not in ADMIN_IDS: await update.message.reply_text("❌ Bukan admin!"); return
    args = context.args
    if not args:
        s = "ON 🟢" if AQUA_TOPUP_BONUS_ACTIVE else "OFF 🔴"
        await update.message.reply_text(f"🎣 Aqua Topup Bonus: <b>{s}</b>", parse_mode=ParseMode.HTML); return
    AQUA_TOPUP_BONUS_ACTIVE = (args[0].lower() == "on")
    s = "ON 🟢" if AQUA_TOPUP_BONUS_ACTIVE else "OFF 🔴"
    await update.message.reply_text(f"🎣 Aqua Topup Bonus: <b>{s}</b>", parse_mode=ParseMode.HTML)
    await log(context, f"🎣 Aqua Topup {'AKTIF' if AQUA_TOPUP_BONUS_ACTIVE else 'NONAKTIF'} by {fmt_user(user)}")

async def _aqua_topup_bonus(target_id: int, amount: int, context) -> str:
    if not AQUA_TOPUP_BONUS_ACTIVE: return ""
    if amount < 2000: return ""
    _cdel(_user_cache, target_id)
    u = await get_user(target_id)
    prev_total = u.get("aqua_topup_total") or 0
    new_total  = prev_total + amount
    await update_user(target_id, {"aqua_topup_total": new_total})
    _cdel(_user_cache, target_id)

    inv  = await get_inv(target_id)
    tier = _aqua_tier(new_total)
    AQUA_C = ["ikan_lele", "ikan_mas", "ikan_nila", "teri_asin", "cumi_cumi", "rumput_laut"]
    AQUA_U = ["kerang_mutiara", "ubur_ubur", "pil_mood_aqua"]
    AQUA_R = ["pil_aqua", "pil_stamina"]
    qty_common   = (amount // 1000) * 2
    qty_uncommon = amount // 1000
    bonus_lines  = []

    if tier == "common":
        for key in AQUA_C:
            info = AQUA_ALL_POOL.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")

    elif tier == "uncommon":
        for key in AQUA_C:
            info = AQUA_ALL_POOL.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")
        for key in AQUA_U:
            info = AQUA_ALL_POOL.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_uncommon
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_uncommon}x {info.get('name', key)}")

    elif tier == "rare":
        for key in AQUA_C + AQUA_U:
            info = AQUA_ALL_POOL.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")
        for key in AQUA_R:
            info = AQUA_ALL_POOL.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_uncommon
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_uncommon}x {info.get('name', key)}")

    elif tier == "legendary":
        for key in AQUA_C + AQUA_U + AQUA_R:
            info = AQUA_ALL_POOL.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")
        # Random 1 dari 3 pet eksklusif
        exclusive = random.choice([
            {"pet_type": "ikan_biru",      "name": "Blue Fin",      "emoji": "🐋", "ability": "work_3x",    "ability_name": "Triple Reward"},
            {"pet_type": "ikan_emas_laut", "name": "Golden Marlin", "emoji": "🌟", "ability": "inv_double", "ability_name": "Double Inventory"},
            {"pet_type": "ikan_petir",     "name": "Thunder Eel",   "emoji": "⚡", "ability": "daily_coin", "ability_name": "Daily Coin"},
        ])
        await sb("POST", "pets", {}, {
            "owner1_id": target_id, "owner2_id": None,
            "name": exclusive["name"], "pet_type": exclusive["pet_type"],
            "xp": 0, "hunger": 0, "happiness": 100, "health": 100,
            "poop_count": 0, "is_sleeping": False, "is_dirty": False,
            "is_missing": False, "is_married": False, "is_child": False,
            "special_ability": exclusive["ability"],
            "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
        })
        bonus_lines.append(f"\n🎉 Pet eksklusif: {exclusive['emoji']} <b>{exclusive['name']}</b> (Ability: {exclusive['ability_name']})")

    elif tier == "ultra":
        for key in AQUA_C + AQUA_U + AQUA_R:
            info = AQUA_ALL_POOL.get(key, {})
            inv[key] = (inv.get(key) or 0) + qty_common
            bonus_lines.append(f"{info.get('emoji','📦')} +{qty_common}x {info.get('name', key)}")
        # Dapat SEMUA 3 pet eksklusif sekaligus
        all_exclusive = [
            {"pet_type": "ikan_biru",      "name": "Blue Fin",      "emoji": "🐋", "ability": "work_3x",    "ability_name": "Triple Reward"},
            {"pet_type": "ikan_emas_laut", "name": "Golden Marlin", "emoji": "🌟", "ability": "inv_double", "ability_name": "Double Inventory"},
            {"pet_type": "ikan_petir",     "name": "Thunder Eel",   "emoji": "⚡", "ability": "daily_coin", "ability_name": "Daily Coin"},
        ]
        for exc in all_exclusive:
            await sb("POST", "pets", {}, {
                "owner1_id": target_id, "owner2_id": None,
                "name": exc["name"], "pet_type": exc["pet_type"],
                "xp": 0, "hunger": 0, "happiness": 100, "health": 100,
                "poop_count": 0, "is_sleeping": False, "is_dirty": False,
                "is_missing": False, "is_married": False, "is_child": False,
                "special_ability": exc["ability"],
                "last_decay": now_wib().isoformat(),
        "last_fed": now_wib().isoformat(),
            })
        bonus_lines.append(
            f"\n🌊✨ <b>ULTRA LEGENDARY!</b> Semua pet eksklusif Aqua Tails kamu dapatkan!\n"
            f"🐋 <b>Blue Fin</b> (Triple Reward)\n"
            f"🌟 <b>Golden Marlin</b> (Double Inventory)\n"
            f"⚡ <b>Thunder Eel</b> (Daily Coin)"
        )

    if not bonus_lines: return ""
    await set_inv(target_id, inv)
    return "\n".join(bonus_lines)


# ==================== /send — TRANSFER ITEM ====================
# Level minimum untuk bisa gift item: punya pet level 15+ (sama dengan gift ke partner)
SEND_MIN_LEVEL = 15

async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /send nama item id_penerima jumlah
    Contoh: /send Steak Petarung 123456789 2
    Nama item bisa pakai spasi. Jumlah dan id_penerima selalu di akhir.
    """
    user = update.effective_user
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    # Cek level pet minimal
    pet_lv = await get_pet_level(user.id)
    if pet_lv < SEND_MIN_LEVEL:
        await update.message.reply_text(
            f"❌ Fitur /send butuh pet Level <b>{SEND_MIN_LEVEL}+</b>!\n"
            f"Level petmu sekarang: <b>{pet_lv}</b>",
            parse_mode=ParseMode.HTML
        )
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📦 <b>Transfer Item</b>\n━━━━━━━━━━━━━━━\n\n"
            "Format: <code>/send nama item id_penerima jumlah</code>\n\n"
            "Contoh:\n"
            "<code>/send Steak Petarung 123456789 2</code>\n"
            "<code>/send snack 987654321 5</code>\n\n"
            "<i>Nama item boleh pakai spasi. ID penerima & jumlah selalu di posisi terakhir.</i>",
            parse_mode=ParseMode.HTML
        )
        return

    # Parse: jumlah = args[-1], id_penerima = args[-2], nama = args[:-2]
    try:
        jumlah = int(args[-1])
        target_id = int(args[-2])
        nama_item_input = " ".join(args[:-2]).strip()
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Format salah!\nContoh: <code>/send Steak Petarung 123456789 2</code>",
            parse_mode=ParseMode.HTML
        )
        return

    if jumlah <= 0 or jumlah > 99:
        await update.message.reply_text("❌ Jumlah harus 1–99!")
        return
    if target_id == user.id:
        await update.message.reply_text("❌ Tidak bisa kirim ke diri sendiri!")
        return

    # Cari item di inventory berdasarkan nama (case-insensitive, partial match)
    inv = await get_inv(user.id)
    all_items_meta: dict = {}  # key → display info

    # Standar shop items
    for k, v in {**FOOD_SHOP, **KOI_FOOD_SHOP}.items():
        all_items_meta[k] = {"name": v["name"], "emoji": v.get("emoji", "📦")}
    # Gacha items
    for k, v in GACHA_ITEMS.items():
        all_items_meta[k] = {"name": v["name"], "emoji": v.get("emoji", "🎰")}
    # MBG Kitchen
    for k, v in MBG_KITCHEN_RECIPES.items():
        all_items_meta[k] = {"name": v["name"], "emoji": v.get("emoji", "🍱")}
    # Livestock food & raw products
    for k, v in LIVESTOCK_FOOD.items():
        all_items_meta[k] = {"name": v["name"], "emoji": v.get("emoji", "🥛")}
    for k, v in LIVESTOCK.items():
        prod_key = v.get("food_key") or v.get("product_key") or v.get("product")
        if prod_key:
            all_items_meta[prod_key] = {"name": v.get("product_name", prod_key), "emoji": v.get("product_emoji", "📦")}
    # Astro Paws items
    try:
        for k, v in ASTRO_PERM_ITEMS.items():
            inv_k = _astro_to_inv_key(k)
            all_items_meta[inv_k] = {"name": v.get("name", k), "emoji": v.get("emoji", "🌙")}
            all_items_meta[k] = {"name": v.get("name", k), "emoji": v.get("emoji", "🌙")}
    except Exception: pass
    # Astro Paws 2 items
    try:
        for k, v in ASTRO2_PERM_ITEMS.items():
            all_items_meta[k] = {"name": v.get("name", k), "emoji": v.get("emoji", "🔴")}
    except Exception: pass
    # Aqua items
    try:
        for pool in [AQUA_DANAU_ITEMS, AQUA_TELUK_ITEMS, AQUA_SUNGAI_ITEMS, AQUA_LAUT_ITEMS]:
            for k, v in pool.items():
                all_items_meta[k] = {"name": v.get("name", k), "emoji": v.get("emoji", "🎣")}
    except Exception: pass
    # Custom items
    custom_map = await get_custom_items_map(user.id)
    for k, v in custom_map.items():
        all_items_meta[k] = {"name": v["name"], "emoji": v.get("emoji", "🎁")}
    # Fallback: semua item yang ada di inventory tapi belum ada di meta
    for k in inv:
        if k not in all_items_meta and not k.startswith("_") and (inv.get(k) or 0) > 0:
            all_items_meta[k] = {"name": k, "emoji": "📦"}

    # Cari key yang cocok (nama exact dulu, lalu partial, lalu key langsung)
    found_key = None
    nama_lower = nama_item_input.lower()
    nama_key_guess = nama_lower.replace(" ", "_")  # "pil abadi" → "pil_abadi"

    # 1. Exact match by display name
    for k, meta in all_items_meta.items():
        if meta["name"].lower() == nama_lower and (inv.get(k) or 0) > 0:
            found_key = k; break
    # 2. Exact match by inventory key (langsung atau dengan underscore)
    if not found_key:
        for k in [nama_lower, nama_key_guess]:
            if (inv.get(k) or 0) > 0:
                found_key = k
                if found_key not in all_items_meta:
                    all_items_meta[found_key] = {"name": found_key, "emoji": "📦"}
                break
    # 3. Partial match by display name
    if not found_key:
        for k, meta in all_items_meta.items():
            if nama_lower in meta["name"].lower() and (inv.get(k) or 0) > 0:
                found_key = k; break
    # 4. Partial match by key
    if not found_key:
        for k in inv:
            if nama_key_guess in k and (inv.get(k) or 0) > 0:
                found_key = k
                if found_key not in all_items_meta:
                    all_items_meta[found_key] = {"name": k, "emoji": "📦"}
                break

    if not found_key:
        await update.message.reply_text(
            f"❌ Item <b>{safe_html(nama_item_input)}</b> tidak ditemukan di inventorimu atau stoknya habis!\n\n"
            f"<i>Cek inventori di 🎒 Inventori</i>",
            parse_mode=ParseMode.HTML
        )
        return

    stok = inv.get(found_key) or 0
    if stok < jumlah:
        await update.message.reply_text(
            f"❌ Stok tidak cukup!\n"
            f"Item: {all_items_meta[found_key]['emoji']} <b>{all_items_meta[found_key]['name']}</b>\n"
            f"Stok kamu: <b>{stok}x</b> | Minta kirim: <b>{jumlah}x</b>",
            parse_mode=ParseMode.HTML
        )
        return

    # Cek penerima ada di DB
    target_user = await get_user(target_id)
    if not target_user:
        await update.message.reply_text("❌ Penerima tidak ditemukan! Pastikan ID benar.")
        return

    item_meta = all_items_meta[found_key]
    target_name = safe_html(get_display_name(target_user))

    # Simpan ke context untuk konfirmasi
    context.user_data["send_confirm"] = {
        "item_key": found_key,
        "item_name": item_meta["name"],
        "item_emoji": item_meta["emoji"],
        "jumlah": jumlah,
        "target_id": target_id,
        "target_name": target_name,
    }

    await update.message.reply_text(
        f"📦 <b>Konfirmasi Transfer Item</b>\n━━━━━━━━━━━━━━━\n\n"
        f"Item: {item_meta['emoji']} <b>{safe_html(item_meta['name'])}</b>\n"
        f"Jumlah: <b>{jumlah}x</b>\n"
        f"Penerima: <b>{target_name}</b> (<code>{target_id}</code>)\n\n"
        f"Lanjutkan?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Kirim!", callback_data="send_item_confirm"),
             InlineKeyboardButton("❌ Batal", callback_data="main_menu")],
        ])
    )

async def do_send_item_confirm(q, user, context):
    """Eksekusi transfer item setelah user confirm"""
    data = context.user_data.get("send_confirm")
    if not data:
        await q.answer("❌ Data transfer tidak ditemukan, mulai ulang!", show_alert=True)
        return

    item_key = data["item_key"]
    jumlah = data["jumlah"]
    target_id = data["target_id"]
    item_name = data["item_name"]
    item_emoji = data["item_emoji"]
    target_name = data["target_name"]

    context.user_data["send_confirm"] = None

    # Kurangi dari sender
    _cdel(_user_cache, user.id)
    inv_sender = await get_inv(user.id)
    stok = inv_sender.get(item_key) or 0
    if stok < jumlah:
        await q.answer(f"❌ Stok tidak cukup! ({stok}x tersisa)", show_alert=True)
        return

    inv_sender[item_key] = stok - jumlah
    if inv_sender[item_key] <= 0:
        del inv_sender[item_key]
    await set_inv(user.id, inv_sender)

    # Tambah ke penerima
    _cdel(_user_cache, target_id)
    inv_target = await get_inv(target_id)
    inv_target[item_key] = (inv_target.get(item_key) or 0) + jumlah
    await set_inv(target_id, inv_target)

    sender_u = await get_user(user.id)
    sender_name = safe_html(get_display_name(sender_u) if sender_u else str(user.id))

    asyncio.create_task(task_inc(user.id, "gift_partner"))
    await q.edit_message_text(
        f"✅ <b>Item berhasil dikirim!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{item_emoji} <b>{safe_html(item_name)}</b> x{jumlah}\n"
        f"📬 Ke: <b>{target_name}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])
    )

    # Notif ke penerima
    try:
        await context.bot.send_message(
            target_id,
            f"🎁 <b>Kamu menerima item!</b>\n━━━━━━━━━━━━━━━\n\n"
            f"Dari: <b>{sender_name}</b>\n"
            f"Item: {item_emoji} <b>{safe_html(item_name)}</b> x{jumlah}\n\n"
            f"<i>Cek di 🎒 Inventori~</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎒 Lihat Inventori", callback_data="inventory")]])
        )
    except: pass

    await log(context, f"📦 Send item: {fmt_user(user)} → <code>{target_id}</code> {item_emoji} <b>{safe_html(item_name)}</b> x{jumlah}")


# ==================== ADMIN: /levelup ====================
async def cmd_levelup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin: /levelup id_owner namapet level
    Naikan level pet milik owner tertentu.
    Kalau ada 2 pet dengan nama sama, kasih pilihan.
    """
    if update.effective_user.id not in ADMIN_IDS:
        return

    usage = (
        "🔧 <b>Admin Level Up Pet</b>\n\n"
        "Usage: <code>/levelup id_owner namapet level</code>\n\n"
        "Contoh:\n"
        "<code>/levelup 123456789 Mimi 20</code>\n"
        "<code>/levelup 123456789 Kucing Hitam 30</code>\n\n"
        "<i>Nama pet boleh pakai spasi. Level & ID owner di posisi yang benar.</i>"
    )

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return

    try:
        owner_id = int(args[0])
        new_level = int(args[-1])
        pet_name_input = " ".join(args[1:-1]).strip()
    except (ValueError, IndexError):
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return

    if new_level < 1 or new_level > MAX_LEVEL:
        await update.message.reply_text(f"❌ Level harus 1–{MAX_LEVEL}!")
        return

    if not pet_name_input:
        await update.message.reply_text("❌ Nama pet tidak boleh kosong!")
        return

    # Cari semua pet milik owner dengan nama yang cocok
    all_pets = await get_user_pets(owner_id)
    matched = [p for p in all_pets if p["name"].lower() == pet_name_input.lower()]

    # Juga cari partial match kalau exact tidak ada
    if not matched:
        matched = [p for p in all_pets if pet_name_input.lower() in p["name"].lower()]

    if not matched:
        await update.message.reply_text(
            f"❌ Pet bernama <b>{safe_html(pet_name_input)}</b> tidak ditemukan untuk owner <code>{owner_id}</code>!",
            parse_mode=ParseMode.HTML
        )
        return

    if len(matched) == 1:
        # Langsung level up
        await _do_admin_levelup(update.message, matched[0], new_level, context)
    else:
        # Ada >1 pet dengan nama sama, kasih pilihan
        buttons = []
        for pet in matched:
            info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
            curr_lv = calc_level(pet.get("xp") or 0)
            buttons.append([InlineKeyboardButton(
                f"{info['emoji']} {pet['name']} (Lv.{curr_lv}) — ID:{pet['id']}",
                callback_data=f"admin_lvup_{pet['id']}_{new_level}"
            )])
        buttons.append([InlineKeyboardButton("❌ Batal", callback_data="main_menu")])
        await update.message.reply_text(
            f"⚠️ Ada {len(matched)} pet bernama <b>{safe_html(pet_name_input)}</b>.\nPilih yang mana:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def _do_admin_levelup(msg_or_q, pet: dict, new_level: int, context, is_callback=False):
    """Eksekusi level up pet oleh admin"""
    new_xp = (new_level - 1) * XP_PER_LEVEL
    old_lv = calc_level(pet.get("xp") or 0)

    await update_pet(pet["id"], {"xp": new_xp})
    _cdel(_pet_cache, pet["id"])

    info = PETS.get(pet["pet_type"], {"emoji": "🐾"})
    text = (
        f"✅ <b>Level Up berhasil!</b>\n━━━━━━━━━━━━━━━\n\n"
        f"{info['emoji']} <b>{safe_html(pet['name'])}</b>\n"
        f"Level: <b>{old_lv}</b> → <b>{new_level}</b>\n"
        f"XP: <b>{new_xp}</b>\n"
        f"Owner: <code>{pet.get('owner1_id')}</code>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]])

    if is_callback:
        await msg_or_q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg_or_q.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # Notif ke owner(s)
    for oid in filter(None, [pet.get("owner1_id"), pet.get("owner2_id")]):
        try:
            await context.bot.send_message(
                oid,
                f"⬆️ <b>Pet kamu di-level up oleh admin!</b>\n\n"
                f"{info['emoji']} <b>{safe_html(pet['name'])}</b>\n"
                f"Level: <b>{old_lv}</b> → <b>{new_level}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐾 Lihat Pet", callback_data="my_pet")]])
            )
        except: pass

    await log(context, f"🔧 Admin LevelUp: {info['emoji']} <b>{safe_html(pet['name'])}</b> Lv{old_lv}→{new_level} owner <code>{pet.get('owner1_id')}</code>")




# ==================== IDUL ADHA 2026 ====================
async def cmd_iduladha2026(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User claim hadiah Idul Adha 1447H — berlaku 26-29 Mei 2026, 1x per user"""
    user = update.effective_user
    await get_user(user.id, safe_html(user.username), safe_html(user.first_name))

    now   = now_wib()
    start_dt = WIB.localize(datetime(2026, 5, 26, 0, 0, 0))
    end_dt   = WIB.localize(datetime(2026, 5, 30, 0, 0, 0))
    if not (start_dt <= now < end_dt):
        await update.message.reply_text(
            "\U0001f319 <b>Event Idul Adha 1447H</b>\n\n"
            "\u274c Event ini hanya berlaku pada <b>26\u201329 Mei 2026</b>.",
            parse_mode=ParseMode.HTML
        )
        return

    res = await sb("GET", "users", {
        "user_id": f"eq.{user.id}",
        "select": "user_id,iduladha2026_claimed"
    })
    if not res:
        await update.message.reply_text("\u274c Akun tidak ditemukan, coba /start dulu.")
        return
    if res[0].get("iduladha2026_claimed"):
        await update.message.reply_text(
            "\U0001f319 Kamu sudah mengklaim hadiah Idul Adha 1447H sebelumnya!\n"
            "<i>1 akun hanya bisa klaim 1\u00d7 ya~</i>",
            parse_mode=ParseMode.HTML
        )
        return

    _cdel(_user_cache, user.id)
    u = await get_user(user.id)
    inv = await get_inv(user.id)

    # +1 slot kandang
    current_slots = (u.get("barn_slots") or 1)
    await update_user(user.id, {
        "barn_slots": current_slots + 1,
        "iduladha2026_claimed": True
    })

    # +1 sapi
    cow_name = f"Sapi Kurban {safe_html(user.first_name)}"
    await sb("POST", "livestocks", data={
        "owner_id":    user.id,
        "lt_type":     "cow",
        "name":        cow_name,
        "last_collect": (now_wib() - timedelta(hours=8)).isoformat(),
        "created_at":  now_wib().isoformat(),
    })

    # +10 meal, +5 premium, +5 snack
    inv["meal"]    = (inv.get("meal") or 0) + 10
    inv["premium"] = (inv.get("premium") or 0) + 5
    inv["snack"]   = (inv.get("snack") or 0) + 10
    inv["rendang"] = (inv.get("rendang") or 0) + 5
    await set_inv(user.id, inv)
    _cdel(_user_cache, user.id)

    hadiah_text = (
        "\U0001f319 <b>Selamat Idul Adha 1447H!</b>\n\n"
        "Hadiah kamu:\n"
        "\U0001f3d5 +1 Slot Kandang\n"
        "\U0001f404 +1 Sapi Kurban (<i>" + cow_name + "</i>)\n"
        "\U0001f956 +10 Makanan\n"
        "\U0001f969 +10 Makanan Premium\n"
        "\U0001f36a +10 Snack\n"
        "\U0001f956 +5 Rendang\n\n"
        "<i>Taqabbalallahu minna wa minkum \U0001f917</i>"
    )

    try:
        import io
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open("kupon_kurban.png").convert("RGBA")

        # Foto profil
        try:
            photos = await context.bot.get_user_profile_photos(user.id, limit=1)
            if photos.total_count > 0:
                file = await photos.photos[0][0].get_file()
                photo_bytes = await file.download_as_bytearray()
                pfp = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
            else:
                raise Exception("no photo")
        except Exception:
            pfp = Image.new("RGBA", (200, 200), (180, 180, 180, 255))

        box_x, box_y, box_w, box_h = 79, 352, 509, 446
        pfp = pfp.resize((box_w, box_h), Image.LANCZOS)
        mask = Image.new("L", (box_w, box_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, box_w, box_h], radius=40, fill=255)
        pfp.putalpha(mask)
        img.paste(pfp, (box_x, box_y), pfp)

        draw = ImageDraw.Draw(img)
        try:
            font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 48)
            font_id   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 38)
        except Exception:
            font_name = font_id = ImageFont.load_default()

        dark_green = (30, 80, 50)
        draw.text((980, 500), user.first_name or "User", font=font_name, fill=dark_green)
        draw.text((980, 680), str(user.id), font=font_id, fill=dark_green)

        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        await update.message.reply_photo(photo=buf, caption=hadiah_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.warning(f"Kupon kurban gagal generate: {e}")
        await update.message.reply_text(hadiah_text, parse_mode=ParseMode.HTML)

    await log(context, f"\U0001f319 Idul Adha claimed: {fmt_user(user)}")


# ==================== MAKANAN TOPUP ====================
async def cmd_makanantopup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: toggle double makanan bonus di topup"""
    global MAKANAN_TOPUP_ACTIVE
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        status = "ON \U0001f7e2" if MAKANAN_TOPUP_ACTIVE else "OFF \U0001f534"
        await update.message.reply_text(
            f"\U0001f956 <b>Makanan Topup Event</b>\nStatus: <b>{status}</b>\n\n"
            f"Usage: <code>/makanantopup on|off</code>\n\n"
            f"Kalau aktif, setiap topup dapat (per 1000 koin):\n"
            f"\u2022 2\u00d7 Makanan biasa\n"
            f"\u2022 2\u00d7 Makanan Premium\n"
            f"\u2022 2\u00d7 Cemilan",
            parse_mode=ParseMode.HTML
        )
        return
    MAKANAN_TOPUP_ACTIVE = (args[0].lower() == "on")
    status = "ON \U0001f7e2" if MAKANAN_TOPUP_ACTIVE else "OFF \U0001f534"
    await update.message.reply_text(
        f"\U0001f956 Makanan Topup Event: <b>{status}</b>",
        parse_mode=ParseMode.HTML
    )
    await log(context, f"\U0001f956 Makanan Topup {'AKTIF' if MAKANAN_TOPUP_ACTIVE else 'NONAKTIF'} by {fmt_user(update.effective_user)}")



# ==================== ID CARD ====================
IDCARD_COST = 500
IDCARD_TEMPLATE = "idcard_template.png"
IDCARD_BOX_X, IDCARD_BOX_Y, IDCARD_BOX_W, IDCARD_BOX_H = 142, 280, 604, 591
IDCARD_NAME_XY     = (1066, 400)
IDCARD_USERNAME_XY = (1186, 544)
IDCARD_ID_XY       = (1087, 687)


async def cmd_idcard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    existing = await sb("GET", "idcards", {"user_id": f"eq.{user.id}", "select": "user_id,card_name,file_id"})
    if existing:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f4f7 Lihat ID Card", callback_data="idcard_view")],
            [InlineKeyboardButton("\U0001f504 Buat Ulang (500 \U0001fa99)", callback_data="idcard_remake")],
        ])
        await update.message.reply_text(
            "\U0001f4c7 <b>Carpets ID Card</b>\n\nKamu sudah punya ID Card! Mau ngapain?",
            parse_mode=ParseMode.HTML, reply_markup=kb
        )
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f195 Buat ID Card (500 \U0001fa99)", callback_data="idcard_make")],
            [InlineKeyboardButton("\u274c Batal", callback_data="idcard_cancel")],
        ])
        await update.message.reply_text(
            "\U0001f4c7 <b>Carpets ID Card</b>\n\nBelum punya ID Card nih!\nBuat sekarang seharga <b>500 \U0001fa99</b>?",
            parse_mode=ParseMode.HTML, reply_markup=kb
        )


async def _idcard_start_make(update, context, is_remake=False):
    user = update.effective_user
    u = await get_user(user.id)
    koin = u.get("koin", 0)
    if koin < IDCARD_COST:
        txt = f"\u274c Koin kurang! Butuh <b>{IDCARD_COST} \U0001fa99</b>, kamu punya <b>{koin} \U0001fa99</b>."
        q = getattr(update, "callback_query", None)
        if q: await q.edit_message_text(txt, parse_mode=ParseMode.HTML)
        else: await update.message.reply_text(txt, parse_mode=ParseMode.HTML)
        return
    context.user_data["state"]         = IDCARD_ASK_NAME
    context.user_data["idcard_remake"] = is_remake
    txt = "\U0001f4c7 <b>Buat ID Card</b>\n\nKetik nama yang mau ditampilin di ID Card kamu\n<i>(Maks 20 karakter)</i>"
    q = getattr(update, "callback_query", None)
    if q: await q.edit_message_text(txt, parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def _idcard_process_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 1 or len(name) > 20:
        await update.message.reply_text("\u26a0\ufe0f Nama harus 1-20 karakter, coba lagi:")
        return
    context.user_data["idcard_name"] = name
    context.user_data["state"]       = IDCARD_ASK_PHOTO
    await update.message.reply_text(
        f"\U0001f44d Nama: <b>{safe_html(name)}</b>\n\nSekarang kirim <b>foto</b> yang mau dipasang di ID Card kamu!",
        parse_mode=ParseMode.HTML
    )


async def _idcard_process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u    = await get_user(user.id)
    koin = u.get("koin", 0)
    name = context.user_data.get("idcard_name", user.first_name or "User")
    is_remake = context.user_data.get("idcard_remake", False)
    context.user_data["state"] = None

    if koin < IDCARD_COST:
        await update.message.reply_text(f"\u274c Koin kurang! Butuh <b>{IDCARD_COST} \U0001fa99</b>.", parse_mode=ParseMode.HTML)
        return

    await update_user(user.id, {"koin": koin - IDCARD_COST})
    _cdel(_user_cache, user.id)

    username_str = f"@{user.username}" if user.username else f"ID {user.id}"

    try:
        import io
        from PIL import Image, ImageDraw, ImageFont

        template = Image.open(IDCARD_TEMPLATE).convert("RGBA")
        photo_file = update.message.photo[-1]
        file_obj   = await photo_file.get_file()
        photo_bytes = await file_obj.download_as_bytearray()

        pfp = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        pfp = pfp.resize((IDCARD_BOX_W, IDCARD_BOX_H), Image.LANCZOS)
        mask = Image.new("L", (IDCARD_BOX_W, IDCARD_BOX_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, IDCARD_BOX_W, IDCARD_BOX_H], radius=50, fill=255)
        pfp.putalpha(mask)
        template.paste(pfp, (IDCARD_BOX_X, IDCARD_BOX_Y), pfp)

        draw = ImageDraw.Draw(template)
        try:
            font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
            font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
        except Exception:
            font_name = font_info = ImageFont.load_default()

        color = (50, 180, 160)
        draw.text(IDCARD_NAME_XY,     name,         font=font_name, fill=color)
        draw.text(IDCARD_USERNAME_XY, username_str, font=font_info, fill=color)
        draw.text(IDCARD_ID_XY,       str(user.id), font=font_info, fill=color)

        template = template.convert("RGB")
        buf = io.BytesIO()
        template.save(buf, format="PNG")
        buf.seek(0)

        sent = await update.message.reply_photo(
            photo=buf,
            caption=(
                "\U0001f4c7 <b>ID Card kamu sudah jadi!</b>\n"
                f"\U0001f4b0 <b>-{IDCARD_COST} \U0001fa99</b> dipotong\n\n"
                "<i>Ketik /idcard untuk lihat atau buat ulang~</i>"
            ),
            parse_mode=ParseMode.HTML
        )
        file_id = sent.photo[-1].file_id

    except Exception as e:
        logger.warning(f"ID Card generate gagal: {e}")
        await update.message.reply_text(
            "\u274c Gagal generate ID Card, coba lagi nanti.\n<i>Koin sudah dikembalikan.</i>",
            parse_mode=ParseMode.HTML
        )
        await update_user(user.id, {"koin": koin})
        _cdel(_user_cache, user.id)
        return

    existing = await sb("GET", "idcards", {"user_id": f"eq.{user.id}", "select": "user_id"})
    if existing:
        await sb("PATCH", "idcards", {"user_id": f"eq.{user.id}"}, data={
            "card_name": name, "file_id": file_id, "updated_at": now_wib().isoformat()
        })
    else:
        await sb("POST", "idcards", data={
            "user_id": user.id, "card_name": name,
            "file_id": file_id, "created_at": now_wib().isoformat()
        })

    await log(context, f"\U0001f4c7 ID Card {'remake' if is_remake else 'baru'}: {fmt_user(user)} nama={safe_html(name)}")


# ==================== FARM DAY EVENT ====================

async def fd_get_session():
    res = await sb("GET", "farmday_sessions", {"status": "eq.open", "order": "start_at.desc", "limit": "1"})
    return res[0] if res else None

async def fd_session_active(sess=None):
    if sess is None: sess = await fd_get_session()
    if not sess: return False
    return parse_dt(sess["start_at"]) <= now_wib() <= parse_dt(sess["end_at"])

async def fd_get_inv(user_id: int) -> dict:
    res = await sb("GET", "farmday_inventory", {"user_id": f"eq.{user_id}", "select": "items"})
    return (res[0].get("items") or {}) if res else {}

async def fd_set_inv(user_id: int, items: dict):
    ex = await sb("GET", "farmday_inventory", {"user_id": f"eq.{user_id}", "select": "user_id"})
    if ex: await sb("PATCH", "farmday_inventory", {"user_id": f"eq.{user_id}"}, {"items": items})
    else:  await sb("POST",  "farmday_inventory", data={"user_id": user_id, "items": items})

def fd_inv_count(items: dict) -> int:
    return sum(v for v in items.values() if isinstance(v, int) and v > 0)

async def fd_get_slots(user_id: int, session_id: int) -> list:
    res = await sb("GET", "farmday_slots", {"user_id": f"eq.{user_id}", "session_id": f"eq.{session_id}", "order": "id.asc"})
    return res or []

def fd_slot_status(slot: dict) -> str:
    feed_at = slot.get("feed_at"); ready_at = slot.get("ready_at")
    if not feed_at: return "lapar"
    if ready_at and now_wib() >= parse_dt(ready_at): return "siap"
    return "tunggu"

def fd_get_item_info(slot: dict) -> dict:
    cat = FARMDAY_TERNAK if slot["slot_type"] == "ternak" else FARMDAY_KEBUN
    return cat.get(slot["item_key"]) or FARMDAY_TERNAK_SPECIAL.get(slot["item_key"]) or {}

async def cmd_farmday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u    = await get_user(user.id, safe_html(user.username), safe_html(user.first_name))
    sess = await fd_get_session()
    if not sess or not await fd_session_active(sess):
        await update.message.reply_text(
            "🌾 <b>Farm Day</b>\n\n❌ Tidak ada event Farm Day yang sedang berlangsung.\n<i>Pantau pengumuman untuk event berikutnya~</i>",
            parse_mode=ParseMode.HTML); return
    fd_modal = u.get("farmday_modal") or 0
    fd_poin  = u.get("farmday_points") or 0
    welcome  = ""
    if fd_modal == 0:
        await update_user(user.id, {"farmday_modal": 500})
        _cdel(_user_cache, user.id); fd_modal = 500
        welcome = "\n\n🎉 <b>Selamat datang!</b> Kamu dapat modal awal <b>500 FC</b>!"
    slots = await fd_get_slots(user.id, sess["id"])
    fd_inv = await fd_get_inv(user.id); inv_count = fd_inv_count(fd_inv)
    slot_lines = []; has_siap = False
    for s in slots:
        info = fd_get_item_info(s)
        if not info: continue
        status = fd_slot_status(s)
        if status == "siap":   has_siap = True; status_txt = "✅ <b>SIAP PANEN!</b>"
        elif status == "tunggu": status_txt = f"⏳ Siap: {fmt_countdown(parse_dt(s['ready_at']))}"
        else:                    status_txt = "🍽️ Butuh makan"
        slot_lines.append(f"{info['emoji']} <b>{info['name']}</b> — {status_txt}")
    slot_txt = "\n".join(slot_lines) if slot_lines else "<i>Belum ada ternak/tanaman. Beli di Farm Shop!</i>"
    inv_warn = "\n⚠️ <b>Inventori penuh!</b> Hasil auto-dijual ke FC." if inv_count >= FARMDAY_INV_MAX else ""
    buttons = [
        [InlineKeyboardButton("🐾 Kelola Ternak/Kebun", callback_data="fd_kelola")],
        [InlineKeyboardButton("🛒 Farm Shop", callback_data="fd_shop_menu"), InlineKeyboardButton("🎒 Inventori", callback_data="fd_inv")],
    ]
    if has_siap: buttons.insert(0, [InlineKeyboardButton("✅ Panen Semua!", callback_data="fd_panen_all")])
    await update.message.reply_text(
        f"🌾 <b>Farm Day!</b>{welcome}\n━━━━━━━━━━━━━━━\n"
        f"⏰ Sisa: <b>{fmt_countdown(parse_dt(sess['end_at']))}</b>\n"
        f"💰 Modal FC: <b>{fd_modal} FC</b> | ⭐ Poin: <b>{fd_poin}</b>\n"
        f"🎒 Inventori: <b>{inv_count}/{FARMDAY_INV_MAX}</b>{inv_warn}\n\n"
        f"<b>Ternak & Kebunmu:</b>\n{slot_txt}\n\n<i>Kasih makan → tunggu → panen! Siklus terus selama event!</i>",
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def cmd_farmshop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sess = await fd_get_session()
    if not sess or not await fd_session_active(sess):
        await update.message.reply_text("❌ Tidak ada event Farm Day aktif saat ini."); return
    u = await get_user(update.effective_user.id)
    await _fd_show_shop(update.message, u.get("farmday_modal") or 0, edit=False)

async def _fd_show_shop(target, fd_modal: int, edit=False):
    lines = [f"🛒 <b>Farm Shop</b>\n💰 Modal FC: <b>{fd_modal} FC</b>\n━━━━━━━━━━━━━━━\n🐾 <b>Ternak:</b>"]
    buttons = []
    for k, v in FARMDAY_TERNAK.items():
        ws = v['wait_secs']; wt = f"{ws//60}m {ws%60}s" if ws >= 60 else f"{ws}s"
        lines.append(f"{v['emoji']} {v['name']} — <b>{v['price']} FC</b> | +{v['poin']} poin | ⏳{wt}")
        buttons.append([InlineKeyboardButton(f"{v['emoji']} Beli {v['name']} ({v['price']} FC)", callback_data=f"fd_buy_ternak_{k}")])
    lines.append("\n🌱 <b>Kebun:</b>")
    for k, v in FARMDAY_KEBUN.items():
        ws = v['wait_secs']; wt = f"{ws//60}m {ws%60}s" if ws >= 60 else f"{ws}s"
        lines.append(f"{v['emoji']} {v['name']} — <b>{v['price']} FC</b> | +{v['poin']} poin | ⏳{wt}")
        buttons.append([InlineKeyboardButton(f"{v['emoji']} Beli {v['name']} ({v['price']} FC)", callback_data=f"fd_buy_kebun_{k}")])
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="fd_back")])
    text = "\n".join(lines)
    if edit: await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:    await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def cmd_farmstore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FARMDAY_STORE_ACTIVE:
        await update.message.reply_text("🏪 <b>Farm Store</b>\n\n⏳ Toko penukaran poin belum dibuka.\n<i>Pantau pengumuman ya~</i>", parse_mode=ParseMode.HTML); return
    u = await get_user(update.effective_user.id)
    await _fd_show_store(update.message, u.get("farmday_points") or 0, edit=False)

async def _fd_show_store(target, fd_poin: int, edit=False):
    lines = [f"🏪 <b>Farm Store</b>\n⭐ Poinmu: <b>{fd_poin}</b>\n━━━━━━━━━━━━━━━"]
    cats  = [
        ("🐾 Ternak Special", [k for k,v in FARMDAY_STORE_ITEMS.items() if v["type"]=="ternak_special"]),
        ("🍱 Item Rare",      [k for k,v in FARMDAY_STORE_ITEMS.items() if v["type"]=="item" and v.get("inv_key")!="custom_pet_card"]),
        ("🪙 Koin Carpets",   [k for k,v in FARMDAY_STORE_ITEMS.items() if v["type"]=="koin"]),
        ("🐾 Hewan Eksklusif",[k for k,v in FARMDAY_STORE_ITEMS.items() if v["type"]=="pet"]),
        ("🎨 Custom Pet Card",[k for k,v in FARMDAY_STORE_ITEMS.items() if v.get("inv_key")=="custom_pet_card"]),
    ]
    buttons = []
    for cat_name, keys in cats:
        if not keys: continue
        lines.append(f"\n<b>{cat_name}</b>")
        for k in keys:
            item = FARMDAY_STORE_ITEMS[k]; mark = "✅" if fd_poin >= item["poin"] else "❌"
            lines.append(f"{item['emoji']} {item['name']} — <b>{item['poin']} poin</b> {mark}")
            buttons.append([InlineKeyboardButton(f"{item['emoji']} {item['name']} ({item['poin']} poin)", callback_data=f"fd_store_{k}")])
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="fd_back")])
    text = "\n".join(lines)
    if edit: await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:    await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def cmd_farmrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await sb("GET", "users", {"select": "user_id,nama,username,farmday_points", "farmday_points": "gt.0", "order": "farmday_points.desc", "limit": "10"})
    if not res:
        await update.message.reply_text("🌾 Belum ada pemain Farm Day."); return
    lines = ["🌾 <b>Farm Day — Leaderboard</b>\n━━━━━━━━━━━━━━━"]; medals = ["🥇","🥈","🥉"]
    for i, u in enumerate(res):
        name = safe_html(u.get("nama") or u.get("username") or f"User {u['user_id']}")
        lines.append(f"{medals[i] if i<3 else str(i+1)+'.'} <b>{name}</b> — {u.get('farmday_points',0)} poin")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_farmtopup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FARMDAY_TOPUP_ACTIVE:
        await update.message.reply_text("💳 <b>Farm Topup</b>\n\n⏳ Bonus topup belum aktif.\n<i>Pantau pengumuman ya~</i>", parse_mode=ParseMode.HTML); return
    await update.message.reply_text(
        "💳 <b>Farm Topup Bonus</b>\n━━━━━━━━━━━━━━━\n\n"
        "• Per 1.000 koin → <b>250 poin</b>\n• 10.000 koin → <b>2.500 poin</b>\n"
        "• 20.000 koin → <b>5.000 poin</b> + 2 ternak special\n• 30.000 koin → <b>7.500 poin</b> + semua ternak special\n\n"
        "<i>Topup melalui admin ya~ 🌾</i>", parse_mode=ParseMode.HTML)

async def cmd_remove_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: <code>/remove_farm nama_item jumlah</code>", parse_mode=ParseMode.HTML); return
    try:
        qty = int(args[-1]); item_name = "_".join(args[:-1]).lower()
    except:
        await update.message.reply_text("❌ Format salah."); return
    if qty <= 0:
        await update.message.reply_text("❌ Jumlah harus > 0."); return
    fd_inv    = await fd_get_inv(user.id)
    found_key = next((k for k in fd_inv if k == item_name or k.replace("_"," ") == item_name.replace("_"," ")), None)
    if not found_key or (fd_inv.get(found_key) or 0) <= 0:
        await update.message.reply_text(f"❌ Item <b>{safe_html(item_name)}</b> tidak ada di inventori Farm.", parse_mode=ParseMode.HTML); return
    remove = min(qty, fd_inv[found_key]); fd_inv[found_key] -= remove
    if fd_inv[found_key] <= 0: del fd_inv[found_key]
    await fd_set_inv(user.id, fd_inv)
    finfo = FARMDAY_HASIL_INFO.get(found_key, {"name": found_key, "emoji": "📦"})
    await update.message.reply_text(f"🗑️ {finfo['emoji']} <b>{finfo['name']}</b> ×{remove} dihapus dari inventori Farm.", parse_mode=ParseMode.HTML)

async def cmd_farmday_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Usage: <code>/farmday_create YYYY-MM-DD HH:MM</code>", parse_mode=ParseMode.HTML); return
    try:    start_dt = WIB.localize(datetime.strptime(f"{args[0]} {args[1]}", "%Y-%m-%d %H:%M"))
    except: await update.message.reply_text("❌ Format salah."); return
    existing = await fd_get_session()
    if existing:
        await update.message.reply_text(f"❌ Sesi aktif (ID {existing['id']}). Tutup dulu /farmday_close."); return
    end_dt = start_dt + timedelta(minutes=45)
    res    = await sb("POST", "farmday_sessions", data={"start_at": start_dt.isoformat(), "end_at": end_dt.isoformat(), "status": "open", "created_by": update.effective_user.id})
    sid    = res[0]["id"] if res else "?"
    await update.message.reply_text(
        f"🌾 <b>Farm Day #{sid} dibuat!</b>\n🕐 Mulai: <b>{fmt_wib(start_dt)}</b>\n🕔 Selesai: <b>{fmt_wib(end_dt)}</b>\n\nPlayer bisa join via /farmday",
        parse_mode=ParseMode.HTML)
    await log(context, f"🌾 Farm Day #{sid} dibuat oleh {fmt_user(update.effective_user)}")

async def cmd_farmday_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    sess = await fd_get_session()
    if not sess:
        await update.message.reply_text("❌ Tidak ada sesi aktif."); return
    await sb("PATCH", "farmday_sessions", {"id": f"eq.{sess['id']}"}, {"status": "closed"})
    await sb("PATCH", "users", {}, {"farmday_modal": 0})
    await update.message.reply_text(f"✅ Farm Day #{sess['id']} ditutup.")
    await log(context, f"🌾 Farm Day #{sess['id']} ditutup oleh {fmt_user(update.effective_user)}")

async def cmd_farmstore_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FARMDAY_STORE_ACTIVE
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if not args or args[0].lower() not in ("on","off"):
        s = "ON 🟢" if FARMDAY_STORE_ACTIVE else "OFF 🔴"
        await update.message.reply_text(f"🏪 Farm Store: <b>{s}</b>\nUsage: <code>/farmstore_toggle on|off</code>", parse_mode=ParseMode.HTML); return
    FARMDAY_STORE_ACTIVE = args[0].lower() == "on"
    await update.message.reply_text(f"🏪 Farm Store: <b>{'ON 🟢' if FARMDAY_STORE_ACTIVE else 'OFF 🔴'}</b>", parse_mode=ParseMode.HTML)
    await log(context, f"🏪 Farm Store {'AKTIF' if FARMDAY_STORE_ACTIVE else 'NONAKTIF'} by {fmt_user(update.effective_user)}")

async def cmd_farmtopup_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FARMDAY_TOPUP_ACTIVE
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if not args or args[0].lower() not in ("on","off"):
        s = "ON 🟢" if FARMDAY_TOPUP_ACTIVE else "OFF 🔴"
        await update.message.reply_text(f"💳 Farm Topup: <b>{s}</b>\nUsage: <code>/farmtopup_toggle on|off</code>", parse_mode=ParseMode.HTML); return
    FARMDAY_TOPUP_ACTIVE = args[0].lower() == "on"
    await update.message.reply_text(f"💳 Farm Topup: <b>{'ON 🟢' if FARMDAY_TOPUP_ACTIVE else 'OFF 🔴'}</b>", parse_mode=ParseMode.HTML)
    await log(context, f"💳 Farm Topup {'AKTIF' if FARMDAY_TOPUP_ACTIVE else 'NONAKTIF'} by {fmt_user(update.effective_user)}")

async def cmd_addfarmpoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: <code>/addfarmpoin user_id jumlah_koin</code>", parse_mode=ParseMode.HTML); return
    try:    target_id = int(args[0]); koin = int(args[1])
    except: await update.message.reply_text("❌ Format salah."); return
    bonus = await _fd_topup_bonus(target_id, koin, context)
    await update.message.reply_text(f"✅ Farm Topup untuk <code>{target_id}</code>:\n{bonus or '(tidak ada bonus)'}", parse_mode=ParseMode.HTML)

async def _fd_topup_bonus(target_id: int, koin: int, context) -> str:
    if not FARMDAY_TOPUP_ACTIVE or koin <= 0: return ""
    _cdel(_user_cache, target_id)
    u           = await get_user(target_id)
    base_poin   = (koin // 1000) * 250
    bonus_extra = 0; bonus_special = []; tier_txt = ""
    if koin >= 30000:   bonus_extra=2000; bonus_special=list(FARMDAY_TERNAK_SPECIAL.keys()); tier_txt="30k+ → semua ternak special!"
    elif koin >= 20000: bonus_extra=1250; bonus_special=["milkzilla","phoenix_chicken"];      tier_txt="20k+ → Milkzilla + Phoenix Chicken!"
    total_poin = base_poin + bonus_extra
    await update_user(target_id, {"farmday_points": (u.get("farmday_points") or 0)+total_poin, "farmday_topup_total": (u.get("farmday_topup_total") or 0)+koin})
    _cdel(_user_cache, target_id)
    lines = [f"🌾 <b>Farm Day Topup Bonus!</b>", f"⭐ +<b>{total_poin}</b> Farm Poin"]
    if tier_txt: lines.append(f"🎉 {tier_txt}")
    if bonus_special:
        fd_inv = await fd_get_inv(target_id)
        for k in bonus_special:
            info = FARMDAY_TERNAK_SPECIAL[k]; fd_inv[k] = (fd_inv.get(k) or 0)+1
            lines.append(f"{info['emoji']} +1 {info['name']}")
        await fd_set_inv(target_id, fd_inv)
    summary = "\n".join(lines)
    try: await context.bot.send_message(target_id, summary, parse_mode=ParseMode.HTML)
    except: pass
    return summary

async def farmday_callback(q, user, data: str, context):
    if data == "fd_back":
        sess = await fd_get_session()
        if not sess or not await fd_session_active(sess):
            await q.edit_message_text("❌ Event sudah selesai."); return
        await _fd_render_main(q, user, sess); return

    if data.startswith("fd_buy_ternak_") or data.startswith("fd_buy_kebun_"):
        is_ternak = data.startswith("fd_buy_ternak_")
        item_key  = data[len("fd_buy_ternak_"):] if is_ternak else data[len("fd_buy_kebun_"):]
        catalog   = FARMDAY_TERNAK if is_ternak else FARMDAY_KEBUN
        info      = catalog.get(item_key)
        if not info: await q.answer("❌ Item tidak dikenal!", show_alert=True); return
        sess = await fd_get_session()
        if not sess or not await fd_session_active(sess): await q.answer("❌ Event sudah selesai!", show_alert=True); return
        _cdel(_user_cache, user.id); u = await get_user(user.id)
        fd_modal = u.get("farmday_modal") or 0
        if fd_modal < info["price"]: await q.answer(f"❌ Modal kurang! Butuh {info['price']} FC, punya {fd_modal} FC.", show_alert=True); return
        await update_user(user.id, {"farmday_modal": fd_modal - info["price"]}); _cdel(_user_cache, user.id)
        await sb("POST", "farmday_slots", data={"user_id": user.id, "session_id": sess["id"], "slot_type": "ternak" if is_ternak else "kebun", "item_key": item_key, "bought_at": now_wib().isoformat()})
        await q.answer(f"✅ {info['emoji']} {info['name']} dibeli! Kasih makan sekarang~", show_alert=True)
        await _fd_render_main(q, user, sess); return

    if data == "fd_kelola":
        sess = await fd_get_session()
        if not sess or not await fd_session_active(sess): await q.edit_message_text("❌ Event sudah selesai."); return
        slots = await fd_get_slots(user.id, sess["id"])
        if not slots: await q.answer("Belum ada ternak/tanaman! Beli dulu di Farm Shop~", show_alert=True); return
        await _fd_render_kelola(q, user, slots); return

    if data.startswith("fd_feed_"):
        await _fd_do_feed(q, user, int(data[len("fd_feed_"):])); return

    if data == "fd_panen_all":
        sess = await fd_get_session()
        if not sess or not await fd_session_active(sess): await q.edit_message_text("❌ Event sudah selesai."); return
        await _fd_panen_all(q, user, sess); return

    if data.startswith("fd_panen_"):
        await _fd_do_panen(q, user, int(data[len("fd_panen_"):])); return

    if data == "fd_inv":
        fd_inv = await fd_get_inv(user.id); inv_count = fd_inv_count(fd_inv)
        if inv_count == 0: await q.answer("Inventori kosong~", show_alert=True); return
        lines = [f"🎒 <b>Inventori Farm</b> ({inv_count}/{FARMDAY_INV_MAX})\n━━━━━━━━━━━━━━━"]
        for k, v in fd_inv.items():
            if (v or 0) <= 0: continue
            finfo = FARMDAY_HASIL_INFO.get(k, {"name": k, "emoji": "📦"})
            lines.append(f"{finfo['emoji']} {finfo['name']}: ×{v}")
        lines.append("\n<i>Item bisa dipakai kasih makan pet via menu pet~</i>")
        await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="fd_back")]])); return

    if data == "fd_shop_menu":
        sess = await fd_get_session()
        if not sess or not await fd_session_active(sess): await q.edit_message_text("❌ Event sudah selesai."); return
        _cdel(_user_cache, user.id); u = await get_user(user.id)
        await _fd_show_shop(q, u.get("farmday_modal") or 0, edit=True); return

    if data.startswith("fd_store_"):
        await _fd_do_store_buy(q, user, data[len("fd_store_"):], context); return

async def _fd_render_main(q, user, sess):
    _cdel(_user_cache, user.id); u = await get_user(user.id)
    fd_modal = u.get("farmday_modal") or 0; fd_poin = u.get("farmday_points") or 0
    slots = await fd_get_slots(user.id, sess["id"]); fd_inv = await fd_get_inv(user.id); inv_count = fd_inv_count(fd_inv)
    slot_lines = []; has_siap = False
    for s in slots:
        info = fd_get_item_info(s)
        if not info: continue
        status = fd_slot_status(s)
        if status == "siap":     has_siap = True; status_txt = "✅ <b>SIAP PANEN!</b>"
        elif status == "tunggu": status_txt = f"⏳ {fmt_countdown(parse_dt(s['ready_at']))}"
        else:                    status_txt = "🍽️ Butuh makan"
        slot_lines.append(f"{info['emoji']} <b>{info['name']}</b> — {status_txt}")
    slot_txt = "\n".join(slot_lines) if slot_lines else "<i>Belum ada ternak/tanaman~</i>"
    inv_warn = " ⚠️ Penuh!" if inv_count >= FARMDAY_INV_MAX else ""
    buttons  = [
        [InlineKeyboardButton("🐾 Kelola", callback_data="fd_kelola")],
        [InlineKeyboardButton("🛒 Farm Shop", callback_data="fd_shop_menu"), InlineKeyboardButton("🎒 Inventori", callback_data="fd_inv")],
    ]
    if has_siap: buttons.insert(0, [InlineKeyboardButton("✅ Panen Semua!", callback_data="fd_panen_all")])
    await q.edit_message_text(
        f"🌾 <b>Farm Day!</b>\n━━━━━━━━━━━━━━━\n"
        f"⏰ Sisa: <b>{fmt_countdown(parse_dt(sess['end_at']))}</b>\n"
        f"💰 FC: <b>{fd_modal}</b> | ⭐ Poin: <b>{fd_poin}</b> | 🎒 {inv_count}/{FARMDAY_INV_MAX}{inv_warn}\n\n"
        f"<b>Ternak & Kebunmu:</b>\n{slot_txt}",
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def _fd_render_kelola(q, user, slots):
    lines = ["🐾 <b>Kelola Ternak & Kebun</b>\n━━━━━━━━━━━━━━━"]; buttons = []
    for s in slots:
        info = fd_get_item_info(s)
        if not info: continue
        status = fd_slot_status(s); sid = s["id"]
        if status == "lapar":
            lines.append(f"{info['emoji']} {info['name']} — 🍽️ Lapar")
            buttons.append([InlineKeyboardButton(f"🍽️ Kasih Makan {info['name']}", callback_data=f"fd_feed_{sid}")])
        elif status == "tunggu":
            lines.append(f"{info['emoji']} {info['name']} — ⏳ {fmt_countdown(parse_dt(s['ready_at']))}")
        elif status == "siap":
            lines.append(f"{info['emoji']} {info['name']} — ✅ Siap Panen!")
            buttons.append([InlineKeyboardButton(f"✅ Panen {info['name']}!", callback_data=f"fd_panen_{sid}")])
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="fd_back")])
    await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def _fd_do_feed(q, user, slot_id: int):
    res = await sb("GET", "farmday_slots", {"id": f"eq.{slot_id}", "user_id": f"eq.{user.id}"})
    if not res: await q.answer("❌ Slot tidak ditemukan!", show_alert=True); return
    slot = res[0]; sess = await fd_get_session()
    if not sess or not await fd_session_active(sess): await q.answer("❌ Event sudah selesai!", show_alert=True); return
    if fd_slot_status(slot) != "lapar": await q.answer("⚠️ Sudah dikasih makan atau sedang menunggu!", show_alert=True); return
    info = fd_get_item_info(slot); now = now_wib(); ready_at = now + timedelta(seconds=info["wait_secs"])
    await sb("PATCH", "farmday_slots", {"id": f"eq.{slot_id}"}, {"feed_at": now.isoformat(), "ready_at": ready_at.isoformat(), "harvested_at": None})
    ws = info["wait_secs"]; wt = f"{ws//60}m {ws%60}s" if ws >= 60 else f"{ws}s"
    await q.answer(f"✅ {info['emoji']} {info['name']} dikasih makan! Panen dalam {wt}~", show_alert=True)
    slots = await fd_get_slots(user.id, sess["id"])
    await _fd_render_kelola(q, user, slots)

async def _fd_do_panen(q, user, slot_id: int):
    res = await sb("GET", "farmday_slots", {"id": f"eq.{slot_id}", "user_id": f"eq.{user.id}"})
    if not res: await q.answer("❌ Slot tidak ditemukan!", show_alert=True); return
    slot = res[0]; sess = await fd_get_session()
    if not sess or not await fd_session_active(sess): await q.answer("❌ Event sudah selesai!", show_alert=True); return
    if fd_slot_status(slot) != "siap": await q.answer("⏳ Belum siap dipanen!", show_alert=True); return
    info = fd_get_item_info(slot); hasil_key = info["hasil"]; qty = 2 if info.get("double") else 1
    fd_inv = await fd_get_inv(user.id); inv_count = fd_inv_count(fd_inv)
    _cdel(_user_cache, user.id); u = await get_user(user.id)
    auto_sold = inv_count + qty > FARMDAY_INV_MAX
    if not auto_sold:
        fd_inv[hasil_key] = (fd_inv.get(hasil_key) or 0) + qty
        await fd_set_inv(user.id, fd_inv)
    await update_user(user.id, {"farmday_points": (u.get("farmday_points") or 0)+info["poin"], "farmday_modal": (u.get("farmday_modal") or 0)+info["fc"]})
    _cdel(_user_cache, user.id)
    await sb("PATCH", "farmday_slots", {"id": f"eq.{slot_id}"}, {"harvested_at": now_wib().isoformat(), "feed_at": None, "ready_at": None})
    finfo    = FARMDAY_HASIL_INFO.get(hasil_key, {"emoji": "📦", "name": hasil_key})
    sold_txt = f"📦 Inv penuh! Auto-jual → +{info['fc']} FC" if auto_sold else f"{finfo['emoji']} {finfo['name']} ×{qty} → Inventori"
    await q.answer(f"✅ Panen!\n{sold_txt}\n+{info['poin']} poin | +{info['fc']} FC", show_alert=True)
    slots = await fd_get_slots(user.id, sess["id"]); await _fd_render_kelola(q, user, slots)

async def _fd_panen_all(q, user, sess):
    slots = await fd_get_slots(user.id, sess["id"]); siap = [s for s in slots if fd_slot_status(s)=="siap"]
    if not siap: await q.answer("Tidak ada yang siap dipanen!", show_alert=True); return
    fd_inv = await fd_get_inv(user.id); total_poin=0; total_fc=0; hasil_lines=[]
    for slot in siap:
        info = fd_get_item_info(slot)
        if not info: continue
        hasil_key = info["hasil"]; qty = 2 if info.get("double") else 1
        if fd_inv_count(fd_inv)+qty <= FARMDAY_INV_MAX:
            fd_inv[hasil_key] = (fd_inv.get(hasil_key) or 0)+qty
            finfo = FARMDAY_HASIL_INFO.get(hasil_key,{"emoji":"📦","name":hasil_key})
            hasil_lines.append(f"{finfo['emoji']} {finfo['name']} ×{qty}")
        total_poin+=info["poin"]; total_fc+=info["fc"]
        await sb("PATCH","farmday_slots",{"id":f"eq.{slot['id']}"},{"harvested_at":now_wib().isoformat(),"feed_at":None,"ready_at":None})
    await fd_set_inv(user.id, fd_inv)
    _cdel(_user_cache, user.id); u = await get_user(user.id)
    await update_user(user.id, {"farmday_points":(u.get("farmday_points") or 0)+total_poin, "farmday_modal":(u.get("farmday_modal") or 0)+total_fc})
    _cdel(_user_cache, user.id)
    await q.answer(f"✅ Panen {len(siap)} slot!\n{chr(10).join(hasil_lines)}\n+{total_poin} poin | +{total_fc} FC", show_alert=True)
    await _fd_render_main(q, user, sess)

async def _fd_do_store_buy(q, user, store_key: str, context):
    if not FARMDAY_STORE_ACTIVE: await q.answer("❌ Farm Store belum dibuka!", show_alert=True); return
    item = FARMDAY_STORE_ITEMS.get(store_key)
    if not item: await q.answer("❌ Item tidak ditemukan!", show_alert=True); return
    _cdel(_user_cache, user.id); u = await get_user(user.id)
    fd_poin = u.get("farmday_points") or 0
    if fd_poin < item["poin"]: await q.answer(f"❌ Poin kurang! Butuh {item['poin']}, punya {fd_poin}.", show_alert=True); return
    await update_user(user.id, {"farmday_points": fd_poin - item["poin"]}); _cdel(_user_cache, user.id)
    itype = item["type"]
    if itype == "item":
        inv = await get_inv(user.id); inv[item["inv_key"]] = (inv.get(item["inv_key"]) or 0)+item["qty"]
        await set_inv(user.id, inv)
    elif itype == "koin":
        await add_koin(user.id, item["amount"], "farmstore_tukar")
    elif itype == "pet":
        _def_ability = PET_DEFAULT_ABILITY.get(item["pet_type"])
        await sb("POST","pets",data={"owner1_id":user.id,"owner2_id":None,"name":item["name"],"pet_type":item["pet_type"],"xp":0,"level":1,"hunger":0,"happiness":100,"health":100,"poop_count":0,"is_sleeping":False,"is_dirty":False,"is_missing":False,"is_married":False,"is_child":False,"last_decay":now_wib().isoformat(),"special_ability":_def_ability})
    elif itype == "ternak_special":
        fd_inv = await fd_get_inv(user.id); fd_inv[item["key"]] = (fd_inv.get(item["key"]) or 0)+1
        await fd_set_inv(user.id, fd_inv)
    await q.answer(f"✅ Berhasil tukar {item['name']}!", show_alert=True)
    _cdel(_user_cache, user.id); u2 = await get_user(user.id)
    await _fd_show_store(q, u2.get("farmday_points") or 0, edit=True)
    await log(context, f"🌾 Farm Store: {fmt_user(user)} tukar {item['name']} ({item['poin']} poin)")


def main():
    global _BOT
    app = (
        Application.builder()
        .token(TOKEN)
        .concurrent_updates(True)
        .build()
    )
    _BOT = app.bot
    app.add_handler(CommandHandler("send",          cmd_send))
    app.add_handler(CommandHandler("levelup",       cmd_levelup))
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("menu",         cmd_menu))
    app.add_handler(CommandHandler("join",         cmd_join))
    app.add_handler(CommandHandler("skip",         cmd_skip))
    app.add_handler(CommandHandler("deletepet",    cmd_deletepet))
    app.add_handler(CommandHandler("admin",        cmd_admin))
    app.add_handler(CommandHandler("riwayat",      cmd_riwayat))
    app.add_handler(CommandHandler("createpet",    cmd_createpet))
    app.add_handler(CommandHandler("addkoin",      cmd_addkoin))
    app.add_handler(CommandHandler("delivery",     cmd_delivery))
    app.add_handler(CommandHandler("recoverpet",   cmd_recoverpet))
    app.add_handler(CommandHandler("recovercarpaws", cmd_recovercarpaws))
    app.add_handler(CommandHandler("confirmrecover", cmd_confirmrecover))
    app.add_handler(CommandHandler("buatitem",     cmd_buatitem))
    app.add_handler(CommandHandler("broadcast",         cmd_broadcast))
    app.add_handler(CommandHandler("broadcastforward",  cmd_broadcastforward))
    app.add_handler(CommandHandler("carterganteng", cmd_cheat))
    app.add_handler(CommandHandler("thr",           cmd_thr))
    app.add_handler(CommandHandler("custompetevent", cmd_custompetevent))
    app.add_handler(CommandHandler("topupbonus",     cmd_topupbonus))
    app.add_handler(CommandHandler("astrotopup",      cmd_astrotopup))
    app.add_handler(CommandHandler("iduladha2026",    cmd_iduladha2026))
    app.add_handler(CommandHandler("idcard",          cmd_idcard))
    app.add_handler(CommandHandler("makanantopup",    cmd_makanantopup))
    app.add_handler(CommandHandler("astro2_create",  cmd_astro2_create))
    app.add_handler(CommandHandler("astro2_close",   cmd_astro2_close))
    app.add_handler(CommandHandler("astropaws2",     cmd_astropaws2))
    app.add_handler(CommandHandler("explore2",       cmd_explore2))
    app.add_handler(CommandHandler("astro2_bag",     cmd_astro2_bag))
    app.add_handler(CommandHandler("astro2topup",    cmd_astro2topup))
    app.add_handler(CommandHandler("astro2_list",    cmd_astro2_list))
    app.add_handler(CommandHandler("astro2_stats",   cmd_astro2_stats))
    app.add_handler(CommandHandler("astro_create",   cmd_astro_create))
    app.add_handler(CommandHandler("astro_close",    cmd_astro_close))
    app.add_handler(CommandHandler("astropaws",      cmd_astropaws))
    app.add_handler(CommandHandler("explore",        cmd_explore))
    app.add_handler(CommandHandler("astro_bag",      cmd_astro_bag))
    app.add_handler(CommandHandler("astro_stats",    cmd_astro_stats))
    app.add_handler(CommandHandler("astro_list",     cmd_astro_list))
    app.add_handler(CommandHandler("remove",         cmd_astro_remove))
    app.add_handler(CommandHandler("aquaset",        cmd_aqua_set))
    app.add_handler(CommandHandler("aquaclose",      cmd_aqua_close))
    app.add_handler(CommandHandler("aquastats",      cmd_aqua_stats))
    app.add_handler(CommandHandler("aquatopup",      cmd_aqua_topup))
    app.add_handler(CommandHandler("aquainv",        cmd_aqua_inventory))
    app.add_handler(CommandHandler("aquatails",      aqua_cmd))
    app.add_handler(CommandHandler("mancing",        aqua_mancing_cmd))
    app.add_handler(CommandHandler("jalan",          aqua_jalan_cmd))
    app.add_handler(CommandHandler("farmday",          cmd_farmday))
    app.add_handler(CommandHandler("farmshop",         cmd_farmshop))
    app.add_handler(CommandHandler("farmstore",        cmd_farmstore))
    app.add_handler(CommandHandler("farmrank",         cmd_farmrank))
    app.add_handler(CommandHandler("farmtopup",        cmd_farmtopup))
    app.add_handler(CommandHandler("remove_farm",      cmd_remove_farm))
    app.add_handler(CommandHandler("farmday_create",   cmd_farmday_create))
    app.add_handler(CommandHandler("farmday_close",    cmd_farmday_close))
    app.add_handler(CommandHandler("farmstore_toggle", cmd_farmstore_toggle))
    app.add_handler(CommandHandler("farmtopup_toggle", cmd_farmtopup_toggle))
    app.add_handler(CommandHandler("addfarmpoin",      cmd_addfarmpoin))
    app.add_handler(CommandHandler("task",             cmd_task))
    app.add_handler(CommandHandler("misi",             cmd_task))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(InlineQueryHandler(inline_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_error_handler(error_handler)

    from datetime import time as dtime
    app.job_queue.run_once(job_startup_recovery, when=10)
    app.job_queue.run_repeating(job_hunger_tick, interval=900, first=60)
    app.job_queue.run_repeating(job_poop_tick,   interval=900, first=90)
    app.job_queue.run_daily(job_bath_reminder, time=dtime(hour=8, minute=0, tzinfo=WIB))
    app.job_queue.run_daily(job_sleep_start, time=dtime(hour=22, minute=0, tzinfo=WIB))
    app.job_queue.run_daily(job_sleep_end, time=dtime(hour=7, minute=0, tzinfo=WIB))
    app.job_queue.run_repeating(job_runaway_check, interval=1800, first=300)
    app.job_queue.run_repeating(job_delivery_tick, interval=600, first=60)
    app.job_queue.run_daily(job_cleanup, time=dtime(hour=3, minute=0, tzinfo=WIB))
    app.job_queue.run_repeating(job_work_tick, interval=300, first=120)
    app.job_queue.run_repeating(job_sekolah_tick, interval=300, first=150)
    app.job_queue.run_repeating(job_aqua_tick,    interval=60,  first=30)
    app.job_queue.run_repeating(job_child_allowance_tick, interval=10800, first=600)
    app.job_queue.run_repeating(job_level_unlock_check, interval=1800, first=180)
    # Jobs baru: ability passif
    app.job_queue.run_daily(job_ability_daily_coin, time=dtime(hour=9, minute=0, tzinfo=WIB))
    app.job_queue.run_repeating(job_ability_self_heal, interval=10800, first=300)
    app.job_queue.run_repeating(job_astro_tick,  interval=60, first=30)
    app.job_queue.run_repeating(job_astro2_tick, interval=60, first=35)

    print("=" * 50)
    print("🏪 The Carpet Shop — Bot aktif!")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print("✅ Fitur: Nickname, Sleep 22-07, Transfer koin, Settings, Aksesoris, Hemat egress")
    print("=" * 50)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()