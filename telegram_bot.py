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
from chatbot import GeminiChatbot
from memory_db import db

# Configuração de logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def get_user_bot(user_id: int) -> GeminiChatbot:
    session_id = f"telegram_{user_id}"
    return GeminiChatbot(config=config, session_id=session_id, database=db)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    bot = get_user_bot(user.id)
    bot.reset()
    welcome_text = (
        f"Olá, {user.first_name}! 🤖\n\n"
        f"Sou seu assistente virtual alimentado pelo Google Gemini ({config.model}).\n"
        f"Skill ativa: *{config.active_skill}*\n\n"
        "Envie qualquer mensagem para conversar ou use os comandos:\n"
        "/limpar - Reinicia o histórico da conversa em memória\n"
        "/ajuda - Mostra esta mensagem de ajuda"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /ajuda."""
    help_text = (
        "Comandos disponíveis:\n"
        "/start - Inicia o bot e exibe boas-vindas\n"
        "/limpar - Limpa a memória da conversa atual no banco em memória\n"
        "/ajuda - Exibe informações de uso"
    )
    await update.message.reply_text(help_text)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /limpar."""
    user = update.effective_user
    bot = get_user_bot(user.id)
    bot.reset()
    await update.message.reply_text("🧹 O histórico da nossa conversa foi reiniciado no banco de dados!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Encaminha o texto recebido para a API do Gemini e responde o usuário."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    user_id = update.effective_user.id
    bot = get_user_bot(user_id)

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
            f"⚠️ Desculpe, ocorreu um erro ao gerar a resposta: {e}"
        )


def main() -> None:
    try:
        config.validate_telegram()
    except ValueError as err:
        logger.error(f"Erro de configuração: {err}")
        print(f"\n[ERRO]: {err}\n")
        return

    logger.info("Iniciando o bot do Telegram...")
    application = Application.builder().token(config.telegram_bot_token).build()

    # Handlers de comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ajuda", help_command))
    application.add_handler(CommandHandler("limpar", clear_command))

    # Handler para mensagens de texto
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Inicia o polling do bot
    application.run_polling()


if __name__ == "__main__":
    main()
