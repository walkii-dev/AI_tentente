import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()


@dataclass
class Config:
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
    active_skill: str = os.getenv("ACTIVE_SKILL", "support_agent.md")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Fuso Horário de Brasília
    timezone: str = os.getenv("TIMEZONE", "America/Sao_Paulo")

    # Regras de Transbordo para Atendente Humano
    handoff_threshold: int = int(os.getenv("HANDOFF_THRESHOLD", "15"))  # Pontos para transbordo
    support_start_hour: int = int(os.getenv("SUPPORT_START_HOUR", "9"))  # 09h
    support_end_hour: int = int(os.getenv("SUPPORT_END_HOUR", "18"))     # 18h
    # 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta, 5=Sábado, 6=Domingo
    support_workdays: tuple = (0, 1, 2, 3, 4)

    def validate(self):
        if not self.api_key or self.api_key == "sua_chave_aqui":
            raise ValueError(
                "GEMINI_API_KEY não foi configurada. Crie ou edite o arquivo .env com sua chave do Google AI Studio (https://aistudio.google.com/app/apikey)."
            )

    def validate_telegram(self):
        self.validate()
        if not self.telegram_bot_token or self.telegram_bot_token == "seu_token_do_telegram_aqui":
            raise ValueError(
                "TELEGRAM_BOT_TOKEN não foi configurado no .env. Obtenha seu token com o @BotFather no Telegram."
            )


config = Config()
