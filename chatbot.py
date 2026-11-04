from typing import Generator, List, Optional, Tuple
from google import genai
from google.genai import types

from config import Config
from memory_db import InMemoryChatDatabase, db as default_db
from skill_loader import skill_loader
from handoff_manager import HandoffManager


class GeminiChatbot:
    """
    Gerencia a sessão de chat, conexão com a API Google Gemini (google-genai),
    banco de dados em memória, base de conhecimento da empresa (RAG),
    sistema de pontuação e transbordo para atendente humano.
    """

    def __init__(
        self,
        config: Config,
        session_id: str = "default_session",
        skill_name: Optional[str] = None,
        database: Optional[InMemoryChatDatabase] = None,
    ):
        self.config = config
        self.config.validate()
        self.client = genai.Client(api_key=self.config.api_key)
        self.session_id = session_id
        self.db = database or default_db

        active_skill = skill_name or self.config.active_skill
        self.system_prompt = skill_loader.load_skill_prompt(active_skill)

        # Se for uma sessão nova no banco em memória, inicializa com o system instruction da skill
        if not self.db.get_messages(self.session_id):
            self.reset()

    def reset(self) -> None:
        """Reinicia o histórico da conversa e a pontuação no banco de dados em memória."""
        self.db.clear_history(self.session_id)
        self.db.add_message(self.session_id, role="system", content=self.system_prompt)

    def check_and_update_handoff(self, user_message: str) -> Tuple[bool, str]:
        """
        Calcula os pontos da mensagem, atualiza a pontuação acumulada da sessão no banco
        e avalia se deve transferir para um humano ou manter na IA por estar fora do horário.
        Retorna (is_transferred: bool, notification_text: str).
        """
        # Se já foi transferido para um humano
        if self.db.is_handed_off(self.session_id):
            return True, "👤 [Sessão já sob atendimento humano. Aguarde um instante.]"

        # Calcula pontos da mensagem e atualiza o total no banco
        points = HandoffManager.calculate_message_score(user_message)
        current_score = self.db.add_score(self.session_id, points)

        should_handoff, is_in_hours, message = HandoffManager.evaluate_handoff(current_score)

        if should_handoff:
            # Transfere e marca status no banco
            self.db.set_handed_off(self.session_id, True)
            return True, message

        # Se atingiu a pontuação mas está FORA do horário, não transfere e avisa
        if not is_in_hours and current_score >= self.config.handoff_threshold:
            return False, message

        return False, ""

    def _build_context_with_knowledge(self, user_message: str) -> str:
        """Consulta o banco por informações relevantes da empresa (RAG)."""
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

    def _get_generation_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
        )

    def send_message_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        Envia a mensagem, verifica pontuação de atendimento humano e transmite via streaming.
        """
        is_transferred, notice = self.check_and_update_handoff(user_message)
        if notice:
            yield f"\n{notice}\n\n"

        if is_transferred:
            return

        enriched_user_message = self._build_context_with_knowledge(user_message)
        self.db.add_message(self.session_id, role="user", content=enriched_user_message)
        contents = self._build_gemini_contents()

        try:
            response_stream = self.client.models.generate_content_stream(
                model=self.config.model,
                contents=contents,
                config=self._get_generation_config(),
            )

            assistant_reply = []
            for chunk in response_stream:
                if chunk.text:
                    assistant_reply.append(chunk.text)
                    yield chunk.text

            full_content = "".join(assistant_reply)
            self.db.add_message(self.session_id, role="model", content=full_content)

        except Exception as exc:
            self._rollback_last_user_message()
            raise exc

    def send_message(self, user_message: str) -> str:
        """
        Envia a mensagem, processa pontuação/transbordo e retorna resposta completa (para Telegram).
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
                config=self._get_generation_config(),
            )
            full_content = response.text or ""
            self.db.add_message(self.session_id, role="model", content=full_content)

            if notice:
                return f"{notice}\n\n{full_content}"
            return full_content

        except Exception as exc:
            self._rollback_last_user_message()
            raise exc

    def _rollback_last_user_message(self) -> None:
        messages = self.db.get_messages(self.session_id)
        if messages and messages[-1]["role"] == "user":
            self.db.clear_history(self.session_id)
            for msg in messages[:-1]:
                self.db.add_message(self.session_id, msg["role"], msg["content"])
