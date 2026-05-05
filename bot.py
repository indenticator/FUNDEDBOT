import os
import logging
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Sos un asistente experto en prop firms (empresas de fondeo) y trading profesional..."""

user_histories = {}

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def clear_history(user_id):
    user_histories[user_id] = []

async def ask_claude(user_id: int, message: str) -> str:
    history = get_history(user_id)

    history.append({
        "role": "user",
        "content": [{"type": "text", "text": message}]
    })

    if len(history) > 20:
        history = history[-20:]
        user_histories[user_id] = history

    try:
        response = client.messages.create(
            model="claude-3-sonnet-20240229",  # ✅ modelo compatible
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=history
        )

        reply = response.content[0].text

        history.append({
            "role": "assistant",
            "content": [{"type": "text", "text": reply}]
        })

        return reply

    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return f"Error Claude: {e}"

def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📋 Challenge", callback_data="cmd_challenge"),
            InlineKeyboardButton("⚖️ Riesgo", callback_data="cmd_riesgo"),
        ],
        [
            InlineKeyboardButton("🛡️ Colchón", callback_data="cmd_colchon"),
            InlineKeyboardButton("🔍 Comparar firms", callback_data="cmd_comparar"),
        ],
        [
            InlineKeyboardButton("🚨 Detectar scam", callback_data="cmd_scam"),
            InlineKeyboardButton("🔄 Nueva conversación", callback_data="cmd_reset"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    clear_history(user.id)

    text = (
        f"👋 Hola {user.first_name}!\n\n"
        "Soy tu asistente especializado en prop firms y trading.\n\n"
        "Escribime o usá los botones 👇"
    )

    await update.message.reply_text(text, reply_markup=main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not text:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    reply = await ask_claude(user_id, text)
    await update.message.reply_text(reply, reply_markup=main_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "cmd_reset":
        clear_history(user_id)
        await query.message.reply_text("🔄 Conversación reiniciada", reply_markup=main_keyboard())
        return

    prompts = {
        "cmd_challenge": "Dame estrategias para pasar un challenge de prop firm rápido.",
        "cmd_riesgo": "Explicame la gestión de riesgo en una prop firm según winrate.",
        "cmd_colchon": "Cómo crear un colchón de seguridad en una cuenta fondeada.",
        "cmd_comparar": "Comparame las mejores prop firms actuales.",
        "cmd_scam": "Señales de que una prop firm es scam.",
    }

    if data in prompts:
        await query.message.reply_text("Procesando...")
        reply = await ask_claude(user_id, prompts[data])
        await query.message.reply_text(reply, reply_markup=main_keyboard())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
