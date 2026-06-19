import subprocess
import asyncio
import os
import time
import glob
from telegram import Update, Message
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.error import NetworkError, TimedOut, RetryAfter
from telegram.request import HTTPXRequest

TOKEN = "8344830757:AAEjLa5GOqZGNPyorCwdfzZzkedtnXFL_xk"
OWNER_ID = 8513979925
CLAUDE_PATH = "/root/.nvm/versions/node/v22.22.3/bin/claude"
WORK_DIR = "/root/bot"
SESSION_DIR = os.path.expanduser("~/.claude/projects/-root-bot")

_fresh_next = False
_session_id = None  # tracks current Claude session for --resume

def get_latest_session_id() -> str | None:
    files = glob.glob(os.path.join(SESSION_DIR, "*.jsonl"))
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    return os.path.basename(latest).replace(".jsonl", "")

SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

def fmt_elapsed(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    return f"{m}m {s}s"

async def progress_ticker(msg: Message, stop_event: asyncio.Event):
    start = time.time()
    i = 0
    while not stop_event.is_set():
        await asyncio.sleep(5)
        if stop_event.is_set():
            break
        elapsed = int(time.time() - start)
        spin = SPINNERS[i % len(SPINNERS)]
        try:
            await msg.edit_text(
                f"{spin} Lagi dikerjain... ({fmt_elapsed(elapsed)})\n"
                f"<i>Claude lagi mikir, sabar ya...</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        i += 1

async def run_claude(prompt: str, status_msg: Message, fresh: bool = False) -> str:
    global _session_id
    stop_event = asyncio.Event()
    ticker = asyncio.create_task(progress_ticker(status_msg, stop_event))
    try:
        env = os.environ.copy()
        env["PATH"] = "/root/.nvm/versions/node/v22.22.3/bin:" + env.get("PATH", "")
        args = [CLAUDE_PATH, "-p", prompt, "--allowedTools", "Bash,Read,Write,Edit"]
        if not fresh:
            if _session_id:
                args.extend(["--resume", _session_id])
            else:
                args.append("--continue")
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=WORK_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        # Capture session ID for next run
        _session_id = get_latest_session_id()
        output = stdout.decode().strip()
        if not output and stderr:
            output = stderr.decode().strip()
        return output or "✅ Done (no output)"
    except asyncio.TimeoutError:
        return "⏱️ Timeout (5 menit). Coba pecah jadi task lebih kecil."
    except Exception as e:
        return f"❌ Error: {e}"
    finally:
        stop_event.set()
        ticker.cancel()
        try:
            await ticker
        except asyncio.CancelledError:
            pass

async def send_long(update: Update, text: str):
    MAX = 4000
    if len(text) <= MAX:
        await update.message.reply_text(text)
        return
    for i in range(0, len(text), MAX):
        await update.message.reply_text(text[i:i+MAX])
        await asyncio.sleep(0.3)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _fresh_next
    if update.effective_user.id != OWNER_ID:
        return
    if update.effective_chat.type in ("group", "supergroup"):
        return
    prompt = update.message.text.strip()
    if not prompt:
        return
    fresh = _fresh_next
    _fresh_next = False
    msg = await update.message.reply_text("⠋ Lagi dikerjain... (0s)\n<i>Claude lagi mikir, sabar ya...</i>", parse_mode="HTML")
    result = await run_claude(prompt, msg, fresh=fresh)
    await msg.delete()
    await send_long(update, result)

async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _fresh_next
    if update.effective_user.id != OWNER_ID:
        return
    prompt = " ".join(context.args).strip() if context.args else ""
    if not prompt:
        await update.message.reply_text("❓ Kasih prompt-nya dong.\n\nContoh: /ai restart pets.py")
        return
    fresh = _fresh_next
    _fresh_next = False
    msg = await update.message.reply_text("⠋ Lagi dikerjain... (0s)\n<i>Claude lagi mikir, sabar ya...</i>", parse_mode="HTML")
    result = await run_claude(prompt, msg, fresh=fresh)
    await msg.delete()
    await send_long(update, result)

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _fresh_next, _session_id
    if update.effective_user.id != OWNER_ID:
        return
    _fresh_next = True
    _session_id = None
    await update.message.reply_text("🔄 Session direset. Kirim prompt berikutnya untuk mulai percakapan baru.")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    is_group = update.effective_chat.type in ("group", "supergroup")
    if is_group:
        await update.message.reply_text(
            "👋 Claude siap di group!\n\n"
            "Gunakan: /ai <prompt>\n\n"
            "Contoh:\n"
            "• /ai restart pets.py\n"
            "• /ai tambahin fitur X ke carp.py"
        )
    else:
        await update.message.reply_text(
            "👋 Claude siap!\n\n"
            "Kirim prompt apapun dan aku kerjain langsung di server.\n\n"
            "Contoh:\n"
            "• restart pets.py\n"
            "• push index.html ke github\n"
            "• tambahin fitur X ke carp.py\n"
            "• buatin bot baru untuk Y"
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, (TimedOut, NetworkError)):
        return
    if isinstance(err, RetryAfter):
        await asyncio.sleep(err.retry_after)
        return
    import logging
    logging.getLogger(__name__).error(f"Error: {err}", exc_info=err)

def main():
    request = HTTPXRequest(
        connect_timeout=10.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=10.0,
        connection_pool_size=8,
    )
    app = (
        Application.builder()
        .token(TOKEN)
        .request(request)
        .get_updates_request(HTTPXRequest(
            connect_timeout=10.0,
            read_timeout=60.0,
            write_timeout=30.0,
            pool_timeout=10.0,
        ))
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ai", cmd_ai))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    print("✅ Claude Telegram bot jalan...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        timeout=30,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=15,
        pool_timeout=10,
    )

if __name__ == "__main__":
    main()
