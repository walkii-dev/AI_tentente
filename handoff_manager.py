from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Tuple, Optional
from config import config


class HandoffManager:
    """
    Gerencia a pontuação de necessidade de atendimento humano e verifica
    se a empresa está em horário de atendimento comercial considerando o horário de Brasília.
    """

    WEEKDAY_NAMES = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo",
    ]

    SCORE_TRIGGERS = {
        "atendente": 10,
        "humano": 10,
        "pessoa": 8,
        "falar com alguem": 12,
        "falar com alguém": 12,
        "suporte humano": 12,
        "especialista": 6,

        "reclamação": 8,
        "reclamacao": 8,
        "cancelar": 8,
        "cancelamento": 8,
        "procon": 15,
        "processo": 15,
        "estorno": 8,
        "reembolso": 6,
        "raiva": 7,
        "absurdo": 7,
        "pessimo": 7,
        "péssimo": 7,
        "horrível": 7,
        "horrivel": 7,
        "nao funciona": 6,
        "não funciona": 6,
        "nao resolveu": 8,
        "não resolveu": 8,
        "incompetente": 10,

        "cobrança indevida": 10,
        "cobranca indevida": 10,
        "urgente": 6,
        "urgência": 6,
    }

    @classmethod
    def get_brasilia_time(cls) -> datetime:
        """Retorna o datetime exato atual no fuso horário de Brasília (America/Sao_Paulo)."""
        try:
            return datetime.now(ZoneInfo(config.timezone))
        except Exception:
            return datetime.now()

    @classmethod
    def get_brasilia_time_info(cls) -> dict:
        """Retorna um dicionário com data, hora, dia da semana e status do expediente em Brasília."""
        now = cls.get_brasilia_time()
        is_in_hours = cls.is_within_business_hours(now)
        day_name = cls.WEEKDAY_NAMES[now.weekday()]
        return {
            "datetime": now,
            "iso": now.isoformat(),
            "formatted": now.strftime("%d/%m/%Y às %H:%M:%S"),
            "time_str": now.strftime("%H:%M"),
            "date_str": now.strftime("%d/%m/%Y"),
            "weekday": day_name,
            "is_in_business_hours": is_in_hours,
        }

    @classmethod
    def calculate_message_score(cls, message: str) -> int:
        normalized = message.lower()
        score = 0
        for trigger, pts in cls.SCORE_TRIGGERS.items():
            if trigger in normalized:
                score += pts
        return score

    @classmethod
    def is_within_business_hours(cls, now: Optional[datetime] = None) -> bool:
        """
        Verifica se o horário (por padrão em Brasília) está dentro da janela comercial:
        Seg-Sex das 09h às 18h.
        """
        if now is None:
            now = cls.get_brasilia_time()

        if now.weekday() not in config.support_workdays:
            return False

        return config.support_start_hour <= now.hour < config.support_end_hour

    @classmethod
    def evaluate_handoff(cls, current_score: int, now: Optional[datetime] = None) -> Tuple[bool, bool, str]:
        if now is None:
            now = cls.get_brasilia_time()

        needs_handoff = current_score >= config.handoff_threshold
        in_hours = cls.is_within_business_hours(now)
        time_info = cls.get_brasilia_time_info()

        if not needs_handoff:
            return False, in_hours, ""

        if in_hours:
            reason = (
                f"🚨 **Transferência Solicitada!** (Pontuação: {current_score}/{config.handoff_threshold})\n"
                f"Horário atual de Brasília: {time_info['formatted']} ({time_info['weekday']}).\n"
                f"Estamos em horário de atendimento comercial (Segunda a Sexta, das {config.support_start_hour:02d}h às {config.support_end_hour:02d}h).\n"
                "A conversa está sendo encaminhada para a fila de um atendente humano."
            )
            return True, True, reason
        else:
            reason = (
                f"⚠️ **Atenção:** A conversa atingiu critérios para atendimento humano (Pontuação: {current_score}/{config.handoff_threshold}).\n"
                f"Porém, no **Horário de Brasília** agora são **{time_info['time_str']}** de {time_info['weekday']}.\n"
                f"Nosso atendimento com suporte humano funciona exclusivamente de Segunda a Sexta, das {config.support_start_hour:02d}h às {config.support_end_hour:02d}h.\n"
                "Por isso, a conversa permanecerá com o assistente virtual 24/7 até o retorno da equipe humana."
            )
            return False, False, reason
