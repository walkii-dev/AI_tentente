import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import config
from chatbot import GeminiTelegramBotService
from memory_db import db
from handoff_manager import HandoffManager

# Configuração de logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def get_user_bot(user_id: int) -> GeminiTelegramBotService:
    """
    Recupera ou instancia a sessão isolada do usuário no Telegram.
    Cada usuário do Telegram possui seu histórico, pontuação e estado separados no banco em memória.
    """
    session_id = f"telegram_{user_id}"
    return GeminiTelegramBotService(config=config, session_id=session_id, database=db)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /start."""
    user = update.effective_user
    bot = get_user_bot(user.id)
    bot.reset()
    time_info = HandoffManager.get_brasilia_time_info()

    welcome_text = (
        f"Olá, {user.first_name}! 🤖\n\n"
        f"Sou seu assistente virtual inteligente alimentado pelo **Google Gemini** ({config.model}).\n\n"
        f"🕒 **Horário de Brasília:** {time_info['time_str']} ({time_info['weekday']})\n"
        f"🏢 **Atendimento Humano:** Segunda a Sexta, das {config.support_start_hour:02d}h às {config.support_end_hour:02d}h\n"
        "💡 **Atendimento IA:** 24 horas por dia, 7 dias por semana\n\n"
        "Envie qualquer mensagem para conversar ou use os comandos:\n"
        "/limpar - Reinicia a conversa e zera a memória da sessão\n"
        "/ajuda - Exibe informações de suporte"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /ajuda."""
    time_info = HandoffManager.get_brasilia_time_info()
    status = "Aberto" if time_info["is_in_business_hours"] else "Fechado"
    help_text = (
        "📌 **Comandos Disponíveis:**\n"
        "/start - Inicia o bot e exibe mensagem de boas-vindas\n"
        "/limpar - Limpa o histórico da conversa e reinicia a sessão\n"
        "/ajuda - Mostra esta mensagem\n\n"
        f"🕒 **Status do Suporte Humano:** {status} (Horário de Brasília: {time_info['time_str']})"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /limpar."""
    user = update.effective_user
    bot = get_user_bot(user.id)
    bot.reset()
    await update.message.reply_text("🧹 O histórico e a memória da nossa conversa foram reiniciados com sucesso!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa a mensagem recebida pelo Telegram, consulta base da empresa e responde."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    user_id = update.effective_user.id
    bot = get_user_bot(user_id)

    # Indicador de "digitando..." no chat do Telegram
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    try:
        reply_text = bot.send_message(user_text)
        await update.message.reply_text(reply_text)
    except Exception as e:
        logger.error(f"Erro ao processar mensagem do usuário {user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ Desculpe, ocorreu uma instabilidade ao gerar a resposta: {e}"
        )


def main() -> None:
    """Ponto de entrada do Bot Telegram."""
    try:
        config.validate_telegram()
    except ValueError as err:
        logger.error(f"Erro de configuração: {err}")
        print(f"\n[ERRO DE CONFIGURAÇÃO]: {err}\n")
        return

    logger.info("Iniciando Bot do Telegram com Google Gemini...")
    application = Application.builder().token(config.telegram_bot_token).build()

    # Comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ajuda", help_command))
    application.add_handler(CommandHandler("limpar", clear_command))

    # Mensagens de texto
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
