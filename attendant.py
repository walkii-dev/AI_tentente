from typing import List, Optional, Tuple
from google import genai
from google.genai import types

from config import Config
from memory_db import InMemoryChatDatabase, db as default_db
from skill_loader import skill_loader
from handoff_manager import HandoffManager


class SupportAttendantService:
    """
    Atendente virtual para o Telegram alimentado pelo Google Gemini.
    Gerencia a sessão do cliente, consulta a base de conhecimento (RAG),
    monitora horário de atendimento e regras de transbordo humano.
    """

    def __init__(
        self,
        config: Config,
        session_id: str,
        skill_name: Optional[str] = None,
        database: Optional[InMemoryChatDatabase] = None,
    ):
        self.config = config
        self.config.validate()
        self.client = genai.Client(api_key=self.config.api_key)
        self.session_id = session_id
        self.db = database or default_db

        active_skill = skill_name or self.config.active_skill
        self.skill_prompt = skill_loader.load_skill_prompt(active_skill)

        if not self.db.get_messages(self.session_id):
            self.reset()

    def reset(self) -> None:
        """Reinicia o histórico e pontuação da sessão."""
        self.db.clear_history(self.session_id)
        self.db.add_message(self.session_id, role="system", content=self.skill_prompt)

    def check_and_update_handoff(self, user_message: str) -> Tuple[bool, str]:
        """Calcula a pontuação da mensagem e avalia transbordo pelo horário de Brasília."""
        if self.db.is_handed_off(self.session_id):
            return True, "👤 [Sua conversa está na fila de atendimento humano. Em breve um atendente responderá.]"

        points = HandoffManager.calculate_message_score(user_message)
        current_score = self.db.add_score(self.session_id, points)

        should_handoff, is_in_hours, message = HandoffManager.evaluate_handoff(current_score)

        if should_handoff:
            self.db.set_handed_off(self.session_id, True)
            return True, message

        if not is_in_hours and current_score >= self.config.handoff_threshold:
            return False, message

        return False, ""

    def _build_context_with_knowledge(self, user_message: str) -> str:
        """Busca informações relevantes na base da empresa e anexa à mensagem."""
        results = self.db.search_knowledge(user_message, limit=3)
        if not results:
            return user_message

        knowledge_text = "\n\n".join(
            f"[{item['category']}] {item['title']}:\n{item['content']}" for item in results
        )

        return (
            f"{user_message}\n\n"
            f"--- INFORMAÇÕES OFICIAIS DA EMPRESA (BASE DE CONHECIMENTO) ---\n"
            f"{knowledge_text}\n"
            f"--------------------------------------------------------------"
        )

    def _build_gemini_contents(self) -> List[types.Content]:
        """Recupera mensagens anteriores para o histórico do Gemini."""
        return [
            types.Content(
                role="model" if msg["role"] in ("assistant", "model") else "user",
                parts=[types.Part.from_text(text=msg["content"])],
            )
            for msg in self.db.get_messages(self.session_id)
            if msg["role"] != "system"
        ]

    def _get_system_instruction(self) -> str:
        """Combina as diretrizes da skill com a hora oficial de Brasília."""
        time_info = HandoffManager.get_brasilia_time_info()
        return (
            f"{self.skill_prompt}\n\n"
            f"[CONTEXTO TEMPORAL: Horário Oficial de Brasília agora é {time_info['formatted']} ({time_info['weekday']}). "
            f"Expediente humano: {'ABERTO' if time_info['is_in_business_hours'] else 'FECHADO'} "
            f"(Segunda a Sexta, {self.config.support_start_hour:02d}h às {self.config.support_end_hour:02d}h).]"
        )

    def send_message(self, user_message: str) -> str:
        """Processa a mensagem do cliente e retorna a resposta."""
        is_transferred, notice = self.check_and_update_handoff(user_message)
        if is_transferred:
            return notice

        enriched_message = self._build_context_with_knowledge(user_message)
        self.db.add_message(self.session_id, role="user", content=enriched_message)

        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=self._build_gemini_contents(),
                config=types.GenerateContentConfig(
                    system_instruction=self._get_system_instruction(),
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                ),
            )
            full_content = response.text or ""
            self.db.add_message(self.session_id, role="model", content=full_content)

            return f"{notice}\n\n{full_content}" if notice else full_content

        except Exception as exc:
            self._rollback_last_message()
            raise exc

    def _rollback_last_message(self) -> None:
        messages = self.db.get_messages(self.session_id)
        if messages and messages[-1]["role"] == "user":
            self.db.clear_history(self.session_id)
            for msg in messages[:-1]:
                self.db.add_message(self.session_id, msg["role"], msg["content"])
