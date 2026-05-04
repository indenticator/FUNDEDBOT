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

SYSTEM_PROMPT = """Sos un asistente experto en prop firms (empresas de fondeo) y trading profesional, con foco en ayudar a traders a MAXIMIZAR sus chances de pasar challenges rapidamente y gestionar su capital de forma profesional. Hablás en español rioplatense, de forma directa, práctica y sin rodeos. Respondé de forma concisa ya que es un chat de Telegram (máximo 3-4 párrafos por respuesta).

=== CONOCIMIENTO BASE DE PROP FIRMS ===
FTMO: 2 fases, profit target 10%+5%, max drawdown 10% relativo o 5% diario, reparto hasta 90%, MT4/MT5/cTrader, muy respetada, challenge desde ~€155. NO permite trading en noticias de alto impacto en algunos planes.
MyFundedFX: 1 o 3 fases, drawdown 5% diario / 10% total, reparto 80-85%, MT4/MT5, permite EAs, permite trading en noticias.
The5ers: sin tiempo limite, crecimiento organico, reparto 50-100%, muy conservadora para el riesgo, excelente reputacion.
FundedNext: 1 o 2 fases, reparto hasta 95%, parte de ganancias en evaluacion, MT4/MT5, permite crypto.
Apex Trader Funding: solo futuros CME, sin drawdown diario, modelo suscripcion mensual, muy popular EEUU.
E8 Funding: drawdown 8% total / 5% diario, reparto 80%, permite swing y noticias, muy flexible.
Topstep: solo futuros, suscripcion mensual, buena reputacion.
True Forex Funds: 2 fases, drawdown 5%/10%, reparto 80%, pagos muy rapidos.
The Funded Trader: multiples modelos, drawdown 6-12%, reparto 75-90%.

=== ESTRATEGIAS PARA PASAR CHALLENGES RAPIDO ===
1. APERTURA DE SESION: Operar primeros 30-60 min de Londres (8:00-9:00 GMT) o NY (13:30-14:30 GMT). Con 1-2 ops bien ejecutadas se puede pasar en 5-8 dias. Riesgo: 1-2% por trade.
2. APERTURA EXPLOSIVA: Dia 1 con 2-3% en trade con confluencia fuerte. Si sale bien, resto con 0.5%.
3. LOS 2-3 DIAS: Dia 1: 1.5% riesgo, target 4-5%. Dia 2: 0.75%, target 7-8%. Dia 3: 0.5%, cerrar al 10%.
4. CON EAs: Scalping EA apertura Londres, 0.5% por trade, max 3 ops simultaneas. Desactivar 30min antes de noticias.
5. NEWS TRADING: NFP, CPI, Fed. Entrar 2-3 seg DESPUES del dato. Solo en firms que lo permiten (MyFundedFX, E8, TFT).

=== GESTION DE RIESGO ===
CHALLENGE: WR<50%: 0.5%/trade | WR 50-65%: 1%/trade | WR>65%: 1.5-2%/trade. NUNCA mas de 3% en un trade. Limite diario: usar solo 60% del limite de la firm.
FONDEADA: Bajar 25-30% respecto al challenge. Ultima semana del mes: reducir a la mitad.
SESIONES: EURUSD/GBPUSD: Londres 8-12 GMT | NAS100/US500: NY 13:30-15:30 GMT | GER40: Frankfurt 7-10 GMT | XAUUSD: ambas sesiones.

=== COLCHON (BUFFER) ===
Etapa 1 (0-5% profit): operar normal, alejarse del drawdown.
Etapa 2 (5-8% profit): reducir riesgo 30-40%, usar trailing stops.
Etapa 3 (8-10% profit): riesgo minimo 0.25-0.5%, solo setups A+.
REGLA DE ORO: No dejar que el profit baje mas del 30-40% de su maximo en un dia. Ej: llegaste al 7%, no bajes del 4.5%.

=== SENALES DE SCAM ===
Banderas rojas: sin empresa registrada, reglas que cambian al fondear, demoras en pagos, profit split que baja, spreads artificiales en cuenta real, soporte desaparece al pedir retiro, exigen deposito adicional.
Firms confiables: FTMO, The5ers, Topstep, E8, MyFundedFX, FundedNext, Apex.
Verificar siempre en Trustpilot y Reddit r/Forex.

=== PSICOLOGIA ===
- La fondeada se opera MAS conservador que el challenge.
- 2 ops perdidas seguidas: PARAR el dia.
- El revenge trading mata cuentas fondeadas.
- Llevar journal de cada trade.

Respondé siempre en español rioplatense. Usá saltos de linea y emojis moderados para facilitar lectura en Telegram. Sé conciso pero completo."""

user_histories = {}

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def clear_history(user_id):
    user_histories[user_id] = []

async def ask_claude(user_id: int, message: str) -> str:
    history = get_history(user_id)
    history.append({"role": "user", "content": message})
    if len(history) > 20:
        history = history[-20:]
        user_histories[user_id] = history
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=history
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return "Hubo un error al procesar tu consulta. Intentá de nuevo en unos segundos."

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
        "Soy tu asistente especializado en *prop firms* y trading profesional.\n\n"
        "Puedo ayudarte con:\n"
        "📋 Estrategias para pasar challenges rápido\n"
        "⚖️ Gestión de riesgo según tu perfil\n"
        "🛡️ Cómo armar tu colchón de seguridad\n"
        "🔍 Comparar prop firms\n"
        "🚨 Detectar si una firm es scam\n\n"
        "Escribime directo o usá los botones de abajo 👇"
    )
    await update.message.reply_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📌 *Comandos disponibles:*\n\n"
        "/start — Menú principal\n"
        "/challenge — Estrategias para pasar el challenge\n"
        "/riesgo — Gestión de riesgo por perfil\n"
        "/colchon — Cómo armar el buffer de seguridad\n"
        "/comparar — Comparar prop firms\n"
        "/scam — Detectar señales de scam\n"
        "/reset — Limpiar conversación\n"
        "/help — Esta ayuda\n\n"
        "También podés escribirme directamente cualquier pregunta sobre prop firms 💬"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Quiero saber las mejores estrategias para pasar un challenge de prop firm rápido. Dame las opciones principales con detalle."
    await update.message.reply_text("📋 Cargando estrategias de challenge...", reply_markup=main_keyboard())
    reply = await ask_claude(update.effective_user.id, msg)
    await update.message.reply_text(reply, reply_markup=main_keyboard())

async def riesgo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Explicame cómo manejar el riesgo por trade en una prop firm según mi perfil de trader. Dame los porcentajes recomendados según winrate y si estoy en challenge o fondeado."
    await update.message.reply_text("⚖️ Calculando gestión de riesgo...", reply_markup=main_keyboard())
    reply = await ask_claude(update.effective_user.id, msg)
    await update.message.reply_text(reply, reply_markup=main_keyboard())

async def colchon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Explicame cómo armar el colchón de seguridad en una cuenta de prop firm. Dame la estrategia en etapas y la regla de oro."
    await update.message.reply_text("🛡️ Cargando estrategia de colchón...", reply_markup=main_keyboard())
    reply = await ask_claude(update.effective_user.id, msg)
    await update.message.reply_text(reply, reply_markup=main_keyboard())

async def comparar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "¿Cuáles son las mejores prop firms actualmente y cómo se comparan entre sí? Dame un resumen de las principales con sus ventajas y desventajas."
    await update.message.reply_text("🔍 Comparando prop firms...", reply_markup=main_keyboard())
    reply = await ask_claude(update.effective_user.id, msg)
    await update.message.reply_text(reply, reply_markup=main_keyboard())

async def scam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "¿Cuáles son las señales de que una prop firm es scam? Dame las banderas rojas principales y cómo verificar si una firm es confiable."
    await update.message.reply_text("🚨 Cargando señales de alerta...", reply_markup=main_keyboard())
    reply = await ask_claude(update.effective_user.id, msg)
    await update.message.reply_text(reply, reply_markup=main_keyboard())

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await update.message.reply_text(
        "🔄 Conversación reiniciada. ¿En qué te puedo ayudar?",
        reply_markup=main_keyboard()
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "cmd_reset":
        clear_history(user_id)
        await query.message.reply_text("🔄 Conversación reiniciada. ¿En qué te puedo ayudar?", reply_markup=main_keyboard())
        return

    prompts = {
        "cmd_challenge": "Quiero saber las mejores estrategias para pasar un challenge de prop firm rápido. Dame las opciones principales.",
        "cmd_riesgo": "Explicame cómo manejar el riesgo por trade en una prop firm. Dame los porcentajes recomendados según winrate.",
        "cmd_colchon": "Explicame cómo armar el colchón de seguridad en una cuenta de prop firm en etapas.",
        "cmd_comparar": "Comparame las mejores prop firms actualmente con sus ventajas y desventajas.",
        "cmd_scam": "¿Cuáles son las señales de que una prop firm es scam? Dame las banderas rojas principales.",
    }

    loading_msgs = {
        "cmd_challenge": "📋 Cargando estrategias...",
        "cmd_riesgo": "⚖️ Calculando gestión de riesgo...",
        "cmd_colchon": "🛡️ Cargando estrategia de colchón...",
        "cmd_comparar": "🔍 Comparando prop firms...",
        "cmd_scam": "🚨 Analizando señales de alerta...",
    }

    if data in prompts:
        await query.message.reply_text(loading_msgs[data])
        reply = await ask_claude(user_id, prompts[data])
        await query.message.reply_text(reply, reply_markup=main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if not text:
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await ask_claude(user_id, text)
    await update.message.reply_text(reply, reply_markup=main_keyboard())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("challenge", challenge_command))
    app.add_handler(CommandHandler("riesgo", riesgo_command))
    app.add_handler(CommandHandler("colchon", colchon_command))
    app.add_handler(CommandHandler("comparar", comparar_command))
    app.add_handler(CommandHandler("scam", scam_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
