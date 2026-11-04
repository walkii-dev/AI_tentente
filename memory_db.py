import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


class InMemoryChatDatabase:
    """
    Banco de dados relacional em memória (SQLite :memory:)
    para persistência durante o ciclo de vida da aplicação de:
    - Sessões e histórico de conversas por usuário/chat
    - Dados arbitrários de memória/chave-valor por usuário
    """

    def __init__(self, uri: bool = True):
        # Usamos uma URI compartilhada em memória para permitir conexões concorrentes
        # no mesmo processo se necessário (ex: bot assíncrono).
        db_path = "file:aichat_memdb?mode=memory&cache=shared" if uri else ":memory:"
        self.conn = sqlite3.connect(db_path, uri=uri, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self) -> None:
        with self.conn:
            # Tabela de histórico de mensagens por sessão/usuário
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            # Tabela de memória em chave-valor por sessão/usuário (ex: preferências, dados)
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memory (
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, key)
                );
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_session ON chat_history (session_id);"
            )

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Salva uma mensagem no histórico da sessão."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?);",
                (session_id, role, content),
            )

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Recupera mensagens do histórico no formato esperado pela API OpenAI/DeepSeek."""
        query = "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id ASC"
        params: List[object] = [session_id]

        if limit:
            query = f"SELECT role, content FROM ({query} DESC LIMIT ?) ORDER BY id ASC"
            params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def clear_history(self, session_id: str) -> None:
        """Remove todo o histórico da sessão."""
        with self.conn:
            self.conn.execute(
                "DELETE FROM chat_history WHERE session_id = ?;",
                (session_id,),
            )

    def set_memory(self, session_id: str, key: str, value: str) -> None:
        """Armazena ou atualiza uma variável na memória do usuário."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO user_memory (session_id, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (session_id, key, value),
            )

    def get_memory(self, session_id: str, key: str) -> Optional[str]:
        """Obtém uma variável da memória do usuário."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT value FROM user_memory WHERE session_id = ? AND key = ?;",
            (session_id, key),
        )
        row = cursor.fetchone()
        return row["value"] if row else None


# Instância global do banco em memória
db = InMemoryChatDatabase()

