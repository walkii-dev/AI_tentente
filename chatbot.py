from typing import List, Optional, Tuple
from google import genai
from google.genai import types

from config import Config
from memory_db import InMemoryChatDatabase, db as default_db
from skill_loader import skill_loader
from handoff_manager import HandoffManager


class GeminiTelegramBotService:
    """
    Serviço central do Bot do Telegram com Google Gemini (google-genai),
    base de conhecimento em memória (RAG), horário oficial de Brasília e transbordo humano.
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
        self.base_skill_prompt = skill_loader.load_skill_prompt(active_skill)

        if not self.db.get_messages(self.session_id):
            self.reset()

    def reset(self) -> None:
        """Reinicia o histórico da conversa e o score no banco de dados em memória."""
        self.db.clear_history(self.session_id)
        self.db.add_message(self.session_id, role="system", content=self.base_skill_prompt)

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
        """Busca dados da empresa no SQLite em memória e injeta no contexto."""
        results = self.db.search_knowledge(user_message, limit=3)
        if not results:
            return user_message

        knowledge_text = "\n\n".join(
            [f"[{item['category']}] {item['title']}:\n{item['content']}" for item in results]
        )

        return (
            f"{user_message}\n\n"
            f"--- INFORMAÇÕES OFICIAIS DA EMPRESA (CONSULTE PARA RESPONDER CASO PERTINENTE) ---\n"
            f"{knowledge_text}\n"
            f"----------------------------------------------------------------------------------"
        )

    def _build_gemini_contents(self) -> List[types.Content]:
        raw_messages = self.db.get_messages(self.session_id)
        contents: List[types.Content] = []

        for msg in raw_messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                continue

            gemini_role = "model" if role in ("assistant", "model") else "user"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content)],
                )
            )

        return contents

    def _get_dynamic_system_instruction(self) -> str:
        """Injeta dinamicamente a data, hora exata de Brasília e status de expediente humano."""
        time_info = HandoffManager.get_brasilia_time_info()
        status_expediente = (
            "ABERTO (dentro do horário de atendimento humano)"
            if time_info["is_in_business_hours"]
            else "FECHADO (fora do horário de atendimento humano)"
        )

        time_context = (
            f"\n\n### CONTEXTO TEMPORAL EM TEMPO REAL (HORÁRIO OFICIAL DE BRASÍLIA):\n"
            f"- Data e Hora Atual: {time_info['formatted']}\n"
            f"- Dia da semana: {time_info['weekday']}\n"
            f"- Horário: {time_info['time_str']} (Fuso {self.config.timezone})\n"
            f"- Expediente do Suporte Humano da Empresa: {status_expediente} "
            f"(Segunda a Sexta, das {self.config.support_start_hour:02d}h às {self.config.support_end_hour:02d}h).\n"
            f"- REGRA FUNDAMENTAL: Você SEMPRE sabe a hora e a data atual exata. NUNCA pergunte as horas ou a data para o cliente!"
        )

        return f"{self.base_skill_prompt}{time_context}"

    def send_message(self, user_message: str) -> str:
        """
        Recebe a mensagem do Telegram, avalia transbordo,
        consulta base da empresa e gera resposta com o Gemini.
        """
        is_transferred, notice = self.check_and_update_handoff(user_message)
        if is_transferred:
            return notice

        enriched_user_message = self._build_context_with_knowledge(user_message)
        self.db.add_message(self.session_id, role="user", content=enriched_user_message)
        contents = self._build_gemini_contents()

        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self._get_dynamic_system_instruction(),
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                ),
            )
            full_content = response.text or ""
            self.db.add_message(self.session_id, role="model", content=full_content)

            if notice:
                return f"{notice}\n\n{full_content}"
            return full_content

        except Exception as exc:
            messages = self.db.get_messages(self.session_id)
            if messages and messages[-1]["role"] == "user":
                self.db.clear_history(self.session_id)
                for msg in messages[:-1]:
                    self.db.add_message(self.session_id, msg["role"], msg["content"])
            raise exc
