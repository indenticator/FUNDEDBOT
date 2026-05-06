import os
import logging
import anthropic

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# ENV VARIABLES
# =========================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# =========================================================
# CLAUDE CLIENT
# =========================================================

client = anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY
)

# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Sos un advisor profesional especializado en prop firms y trading de futuros.

Ayudás traders a:

- pasar challenges
- proteger cuentas
- crear colchón
- generar payouts
- administrar múltiples cuentas
- controlar riesgo
- evitar errores psicológicos

EMPRESAS:
- Apex
- Lucid Trading
- TakeProfit
- WallStreet Funded

==================================================
REGLAS PRINCIPALES
==================================================

Tu prioridad es:
1. supervivencia
2. consistencia
3. payouts sostenibles

Nunca recomendar:
- revenge trading
- overtrading
- martingala extrema
- gambling

==================================================
GESTION DE RIESGO
==================================================

Si trader arranca -1%:

- bajar size 50%
- máximo 1 trade más
- operar solo setup A+
- si pierde nuevamente -> cerrar plataforma

Si trader rompe cuentas:

ACTIVAR RECOVERY MODE:
- 1 contrato
- máximo 2 trades
- reducir riesgo
- evitar operar emocional

Si trader hace +2% rápido:
- proteger ganancias
- considerar cerrar el día

==================================================
COLCHON
==================================================

Explicar siempre:

"El colchón no es ganancia.
El colchón es protección."

==================================================
ESTILO DE RESPUESTA
==================================================

Las respuestas deben ser:
- rápidas
- directas
- accionables
- profesionales

NO escribir texto innecesario.

Usar:
- títulos
- bullets
- pasos prácticos

Máximo 300-500 palabras normalmente.
"""

# =========================================================
# USER MEMORY
# =========================================================

user_histories = {}

def get_history(user_id):

    if user_id not in user_histories:
        user_histories[user_id] = []

    return user_histories[user_id]

def clear_history(user_id):
    user_histories[user_id] = []

# =========================================================
# ASK CLAUDE
# =========================================================

async def ask_claude(user_id: int, message: str) -> str:

    history = get_history(user_id)

    history.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": message
            }
        ]
    })

    # Mantener historial liviano
    if len(history) > 6:
        history = history[-6:]
        user_histories[user_id] = history

    try:

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            temperature=0.7,
            system=SYSTEM_PROMPT,
            messages=history
        )

        reply = response.content[0].text

        history.append({
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": reply
                }
            ]
        })

        return reply

    except Exception as e:

        logger.error(f"Claude Error: {e}")

        return f"""
❌ Error Claude API

{e}
"""

# =========================================================
# KEYBOARD
# =========================================================

def main_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "📋 Challenge",
                callback_data="cmd_challenge"
            ),

            InlineKeyboardButton(
                "⚖️ Riesgo",
                callback_data="cmd_riesgo"
            ),
        ],

        [
            InlineKeyboardButton(
                "🛡️ Colchón",
                callback_data="cmd_colchon"
            ),

            InlineKeyboardButton(
                "💰 Payouts",
                callback_data="cmd_payouts"
            ),
        ],

        [
            InlineKeyboardButton(
                "🏢 Firms",
                callback_data="cmd_firms"
            ),

            InlineKeyboardButton(
                "📊 Multi Cuentas",
                callback_data="cmd_multi"
            ),
        ],

        [
            InlineKeyboardButton(
                "🚨 Recovery",
                callback_data="cmd_recovery"
            ),

            InlineKeyboardButton(
                "🧠 Psicología",
                callback_data="cmd_psico"
            ),
        ],

        [
            InlineKeyboardButton(
                "🔄 Reiniciar",
                callback_data="cmd_reset"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    clear_history(user.id)

    text = f"""
👋 Hola {user.first_name}

Soy tu advisor especializado en prop firms.

Puedo ayudarte con:

✅ Challenges
✅ Riesgo
✅ Payouts
✅ Colchón
✅ Multi cuentas
✅ Recovery mode
✅ Psicología trader

Usá los botones o escribime tu situación 👇
"""

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard()
    )

# =========================================================
# HANDLE MESSAGE
# =========================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text

    if not text:
        return

    # Mostrar "typing..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    reply = await ask_claude(user_id, text)

    await update.message.reply_text(
        reply,
        reply_markup=main_keyboard()
    )

# =========================================================
# BUTTON CALLBACKS
# =========================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # typing...
    await context.bot.send_chat_action(
        chat_id=query.message.chat.id,
        action="typing"
    )

    # RESET
    if data == "cmd_reset":

        clear_history(user_id)

        await query.message.reply_text(
            "🔄 Conversación reiniciada.",
            reply_markup=main_keyboard()
        )

        return

    prompts = {

        "cmd_challenge":
        """
        Dame una estrategia profesional para pasar un challenge rápido sin romper cuentas.
        """,

        "cmd_riesgo":
        """
        Explicame gestión de riesgo profesional para prop firms.
        """,

        "cmd_colchon":
        """
        Cómo crear colchón en una cuenta fondeada.
        """,

        "cmd_payouts":
        """
        Cómo generar payouts consistentes.
        """,

        "cmd_firms":
        """
        Comparame Apex, Lucid, TakeProfit y WallStreet Funded.
        """,

        "cmd_multi":
        """
        Cómo administrar múltiples cuentas correctamente.
        """,

        "cmd_recovery":
        """
        Entrar en recovery mode después de romper cuentas.
        """,

        "cmd_psico":
        """
        Psicología profesional para traders de prop firms.
        """
    }

    if data in prompts:

        reply = await ask_claude(
            user_id,
            prompts[data]
        )

        await query.message.reply_text(
            reply,
            reply_markup=main_keyboard()
        )

# =========================================================
# MAIN
# =========================================================

def main():

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(button_callback)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    logger.info("✅ BOT INICIADO")

    app.run_polling()

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
