from datetime import datetime
from typing import Tuple
from config import config


class HandoffManager:
    """
    Gerencia a pontuação de necessidade de atendimento humano e verifica
    se a empresa está em horário de atendimento comercial.
    """

    # Termos e pontuações por gravidade/urgência
    SCORE_TRIGGERS = {
        # Pedido direto de atendente humano (alta pontuação)
        "atendente": 10,
        "humano": 10,
        "pessoa": 8,
        "falar com alguem": 12,
        "falar com alguém": 12,
        "suporte humano": 12,
        "especialista": 6,

        # Frustração / Insatisfação / Reclamação
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

        # Problemas críticos de pagamento / contrato
        "cobrança indevida": 10,
        "cobranca indevida": 10,
        "urgente": 6,
        "urgência": 6,
    }

    @classmethod
    def calculate_message_score(cls, message: str) -> int:
        """Calcula a pontuação adicionada por uma única mensagem."""
        normalized = message.lower()
        score = 0
        for trigger, pts in cls.SCORE_TRIGGERS.items():
            if trigger in normalized:
                score += pts
        return score

    @classmethod
    def is_within_business_hours(cls, now: datetime = None) -> bool:
        """
        Verifica se o horário atual está dentro da janela de atendimento humano
        (ex: Seg-Sex das 09h às 18h).
        """
        if now is None:
            now = datetime.now()

        # Verifica dia da semana (0=Segunda ... 4=Sexta)
        if now.weekday() not in config.support_workdays:
            return False

        # Verifica faixa de horário (das 9h às 18h)
        return config.support_start_hour <= now.hour < config.support_end_hour

    @classmethod
    def evaluate_handoff(cls, current_score: int, now: datetime = None) -> Tuple[bool, bool, str]:
        """
        Avalia o estado do transbordo.
        Retorna:
            (should_handoff: bool, is_business_hours: bool, message: str)
        """
        needs_handoff = current_score >= config.handoff_threshold
        in_hours = cls.is_within_business_hours(now)

        if not needs_handoff:
            return False, in_hours, ""

        if in_hours:
            reason = (
                f"🚨 **Transferência Solicitada!** (Pontuação: {current_score}/{config.handoff_threshold})\n"
                f"Estamos em horário de atendimento comercial (Segunda a Sexta, das 09h às 18h).\n"
                "A conversa está sendo encaminhada para a fila de um atendente humano."
            )
            return True, True, reason
        else:
            reason = (
                f"⚠️ **Atenção:** A conversa atingiu critérios para atendimento humano (Pontuação: {current_score}/{config.handoff_threshold}), "
                f"porém estamos **fora do horário de atendimento comercial** (Segunda a Sexta, das 09h às 18h).\n"
                "Por isso, a conversa permanecerá com a nossa IA 24/7 até que o suporte humano retorne."
            )
            return False, False, reason
