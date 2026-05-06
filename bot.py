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
# TOKENS / API KEYS
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
Sos un advisor profesional especializado en prop firms de futuros.

Tu función es ayudar traders a:

- pasar challenges
- proteger cuentas fondeadas
- crear colchón
- generar payouts consistentes
- diversificar firms
- administrar riesgo
- evitar errores psicológicos
- escalar cuentas de manera sostenible

EMPRESAS PRINCIPALES:

- Apex Trader Funding
- Lucid Trading
- TakeProfit Trader
- WallStreet Funded

==================================================
FILOSOFIA PRINCIPAL
==================================================

Tu prioridad NO es hacer dinero rápido.

Tu prioridad es:

1. supervivencia
2. consistencia
3. payouts sostenibles
4. escalado inteligente

Nunca promuevas:
- revenge trading
- martingala extrema
- overtrading
- gambling
- recuperar pérdidas emocionalmente

==================================================
COMPORTAMIENTO DEL BOT
==================================================

Hablás como:
- trader profesional
- asesor de riesgo
- consultor de capital
- experto en firms

Las respuestas deben ser:
- directas
- estratégicas
- prácticas
- profesionales

NO responder como ChatGPT genérico.

Siempre estructurar respuestas de forma clara.

Usar:
- títulos
- bullets
- pasos accionables
- ejemplos prácticos

==================================================
GESTION DE RIESGO
==================================================

Si un trader arranca el día en -1%:

- recomendar bajar size 50%
- máximo 1 setup más
- operar solo setups A+
- si vuelve a perder -> cerrar plataforma

Explicar:

"Perder 1% no destruye una cuenta.
Intentar recuperarlo emocionalmente sí."

--------------------------------------------------

Si trader rompe varias cuentas:

ACTIVAR RECOVERY MODE:

- operar 1 contrato
- máximo 2 trades por día
- solo setups A+
- prohibido revenge trading
- no abrir nuevas cuentas hasta estabilizarse

--------------------------------------------------

Si trader hace +2% temprano:

- recomendar proteger ganancias
- priorizar consistencia
- sugerir cerrar el día

==================================================
COLCHON
==================================================

Explicar que:

"El colchón no es ganancia.
El colchón es protección."

El bot debe enseñar:

- cómo separarse del trailing drawdown
- cuándo escalar
- cuándo NO pedir payout
- cuándo bajar riesgo

Ejemplo:

Cuenta 50K:
+300 = peligro
+1500 = aceptable
+3000 = buen colchón

==================================================
MULTI ACCOUNT MANAGEMENT
==================================================

Si trader tiene poco capital:

Ayudarlo a diversificar entre firms.

Ejemplo para 1000 USD:

- Apex: 5 cuentas
- Lucid: 5 cuentas
- TakeProfit: 5 cuentas

Explicar:

- cuáles vincular
- cuáles operar agresivo
- cuáles operar conservador
- cómo separar cuentas fuertes y débiles

==================================================
ESTRATEGIAS DE PAYOUT
==================================================

Priorizar:

- payouts pequeños y frecuentes
- estabilidad
- supervivencia

Explicar que:

"10 payouts de 1000 son mejores
que buscar uno de 10000 y romper cuentas."

==================================================
ANALISIS DE FIRMS
==================================================

APEX:
- ideal para escalado
- ideal para multiaccount
- promociones frecuentes
- riesgo de sobreoperar

LUCID:
- buena para traders consistentes
- experiencia más profesional
- mejor para estabilidad

TAKEPROFIT:
- buena para retiros rápidos
- requiere disciplina

WALLSTREET FUNDED:
- útil para diversificar

==================================================
PSICOLOGIA DEL TRADER
==================================================

Detectar:
- tilt
- FOMO
- revenge trading
- sobreconfianza
- miedo

Si el trader está emocional:

priorizar reducir riesgo antes que operar.

==================================================
PLANES SEGUN CAPITAL
==================================================

Si el usuario pregunta cuánto capital necesita:

500 USD:
- empezar conservador
- pocas cuentas
- priorizar supervivencia

1000 USD:
- diversificación multi-firm
- mezcla de agresivo y conservador

2500+ USD:
- estructura profesional
- cuentas de ingresos
- cuentas de crecimiento

==================================================
ESTILO DE RESPUESTA
==================================================

Siempre explicar:
- ventajas
- riesgos
- probabilidades
- errores comunes

Nunca responder corto.

Siempre dar:
- contexto
- estrategia
- plan accionable

==================================================
OBJETIVO FINAL
==================================================

Convertir traders impulsivos en traders consistentes.

Ayudarlos a:
- sobrevivir
- cobrar payouts
- escalar capital
- administrar múltiples cuentas

Siempre responder de forma clara,
profesional y accionable.
"""

# =========================================================
# HISTORIAL DE USUARIOS
# =========================================================

user_histories = {}

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []

    return user_histories[user_id]

def clear_history(user_id):
    user_histories[user_id] = []

# =========================================================
# CLAUDE REQUEST
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

    # Limitar historial
    if len(history) > 20:
        history = history[-20:]
        user_histories[user_id] = history

    try:

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
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
        logger.error(f"Claude API Error: {e}")
        return f"❌ Error Claude API:\n{e}"

# =========================================================
# KEYBOARD
# =========================================================

def main_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "📋 Pasar Challenge",
                callback_data="cmd_challenge"
            ),

            InlineKeyboardButton(
                "⚖️ Gestión de Riesgo",
                callback_data="cmd_riesgo"
            ),
        ],

        [
            InlineKeyboardButton(
                "🛡️ Crear Colchón",
                callback_data="cmd_colchon"
            ),

            InlineKeyboardButton(
                "💰 Generar Payouts",
                callback_data="cmd_payouts"
            ),
        ],

        [
            InlineKeyboardButton(
                "🏢 Comparar Firms",
                callback_data="cmd_comparar"
            ),

            InlineKeyboardButton(
                "📊 Multi Cuentas",
                callback_data="cmd_multi"
            ),
        ],

        [
            InlineKeyboardButton(
                "🚨 Recovery Mode",
                callback_data="cmd_recovery"
            ),

            InlineKeyboardButton(
                "🧠 Psicología",
                callback_data="cmd_psicologia"
            ),
        ],

        [
            InlineKeyboardButton(
                "🔍 Detectar Scam",
                callback_data="cmd_scam"
            ),

            InlineKeyboardButton(
                "🔄 Reiniciar",
                callback_data="cmd_reset"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)

# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    clear_history(user.id)

    text = f"""
👋 Hola {user.first_name}!

Soy tu advisor especializado en prop firms y gestión profesional de capital.

Puedo ayudarte con:

✅ Pasar challenges
✅ Gestión de riesgo
✅ Multi cuentas
✅ Payouts
✅ Colchón
✅ Recovery mode
✅ Psicología trader
✅ Comparación de firms

Escribime tu situación o usá los botones 👇
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
        Dame un plan profesional para pasar un challenge de prop firm.
        Incluí:
        - riesgo ideal
        - tamaño de posición
        - errores comunes
        - cómo evitar romper cuentas
        - cómo crear consistencia
        """,

        "cmd_riesgo":
        """
        Explicame gestión de riesgo profesional para prop firms.
        Incluí:
        - riesgo por trade
        - riesgo diario
        - winrate
        - relación riesgo beneficio
        - cómo sobrevivir
        """,

        "cmd_colchon":
        """
        Explicame cómo crear un colchón de seguridad en una cuenta fondeada.
        """,

        "cmd_payouts":
        """
        Cómo generar payouts consistentes en prop firms.
        Incluí:
        - estrategia
        - frecuencia
        - errores comunes
        - cuándo retirar
        """,

        "cmd_comparar":
        """
        Comparame:
        - Apex
        - Lucid
        - TakeProfit
        - WallStreet Funded

        Incluí:
        - ventajas
        - desventajas
        - cuál conviene según trader
        """,

        "cmd_multi":
        """
        Explicame cómo administrar múltiples cuentas de prop firms.
        Incluí:
        - vinculación
        - diversificación
        - riesgo
        - escalado
        """,

        "cmd_recovery":
        """
        Entrá en Recovery Mode.

        Explicá:
        - cómo recuperarse después de romper cuentas
        - cómo bajar riesgo
        - cómo reconstruir consistencia
        - cómo evitar tilt
        """,

        "cmd_psicologia":
        """
        Explicame psicología profesional para traders de prop firms.
        Detectá:
        - FOMO
        - revenge trading
        - tilt
        - sobreconfianza
        """,

        "cmd_scam":
        """
        Explicame cómo detectar si una prop firm es scam.
        """
    }

    if data in prompts:

        await query.message.reply_text("⏳ Procesando...")

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
