import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional


class InMemoryChatDatabase:
    """
    Banco de dados relacional em memória (SQLite :memory:) com cache compartilhado para:
    - Histórico de conversas por usuário/sessão (chat_history)
    - Memória chave-valor do usuário (user_memory)
    - Base de conhecimento institucional/produtos da empresa (company_knowledge)
    - Pontuação e status de transbordo da sessão (session_status)
    """

    DEFAULT_DATA_FILE = Path(__file__).resolve().parent / "data" / "company_knowledge.json"

    def __init__(self, uri: bool = True):
        db_path = "file:aichat_memdb?mode=memory&cache=shared" if uri else ":memory:"
        self.conn = sqlite3.connect(db_path, uri=uri, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self.load_company_knowledge()

    def _init_tables(self) -> None:
        with self.conn:
            # Histórico de conversas
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
            # Memória chave-valor do usuário
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
            # Base de conhecimento da empresa
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS company_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL
                );
                """
            )
            # Controle de pontuação e transbordo por sessão
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_status (
                    session_id TEXT PRIMARY KEY,
                    score INTEGER DEFAULT 0,
                    is_handed_off BOOLEAN DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_session ON chat_history (session_id);"
            )

    # -----------------------------
    # Gestão de Histórico de Chat
    # -----------------------------
    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?);",
                (session_id, role, content),
            )

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
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
        with self.conn:
            self.conn.execute("DELETE FROM chat_history WHERE session_id = ?;", (session_id,))
            self.reset_session_score(session_id)

    # ------------------------------------
    # Gestão de Pontuação e Transbordo
    # ------------------------------------
    def add_score(self, session_id: str, points: int) -> int:
        """Adiciona pontos à sessão e retorna o novo total."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO session_status (session_id, score, is_handed_off, updated_at)
                VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    score = score + excluded.score,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (session_id, points),
            )
        return self.get_session_score(session_id)

    def get_session_score(self, session_id: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT score FROM session_status WHERE session_id = ?;", (session_id,))
        row = cursor.fetchone()
        return row["score"] if row else 0

    def set_handed_off(self, session_id: str, handed_off: bool = True) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO session_status (session_id, score, is_handed_off, updated_at)
                VALUES (?, 0, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    is_handed_off = excluded.is_handed_off,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (session_id, 1 if handed_off else 0),
            )

    def is_handed_off(self, session_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_handed_off FROM session_status WHERE session_id = ?;", (session_id,))
        row = cursor.fetchone()
        return bool(row["is_handed_off"]) if row else False

    def reset_session_score(self, session_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE session_status SET score = 0, is_handed_off = 0 WHERE session_id = ?;",
                (session_id,),
            )

    # -----------------------------
    # Memória Chave-Valor do Usuário
    # -----------------------------
    def set_memory(self, session_id: str, key: str, value: str) -> None:
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
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT value FROM user_memory WHERE session_id = ? AND key = ?;",
            (session_id, key),
        )
        row = cursor.fetchone()
        return row["value"] if row else None

    # ----------------------------------------
    # Base de Conhecimento da Empresa (RAG)
    # ----------------------------------------
    def load_company_knowledge(self, file_path: Optional[Path] = None) -> int:
        target_path = file_path or self.DEFAULT_DATA_FILE
        if not target_path.exists():
            return 0

        with open(target_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        with self.conn:
            self.conn.execute("DELETE FROM company_knowledge;")
            for item in items:
                self.conn.execute(
                    "INSERT INTO company_knowledge (category, title, content) VALUES (?, ?, ?);",
                    (item.get("category", "Geral"), item.get("title", ""), item.get("content", "")),
                )
        return len(items)

    def search_knowledge(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        words = [w.strip().lower() for w in query.replace("?", "").replace("!", "").replace(",", "").split() if len(w) > 2]
        
        cursor = self.conn.cursor()
        if not words:
            cursor.execute("SELECT category, title, content FROM company_knowledge LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [{"category": r["category"], "title": r["title"], "content": r["content"]} for r in rows]

        where_clauses = []
        params = []
        for word in words:
            term = f"%{word}%"
            where_clauses.append("(category LIKE ? OR title LIKE ? OR content LIKE ?)")
            params.extend([term, term, term])

        sql = f"""
            SELECT category, title, content,
            (
                {" + ".join(["(CASE WHEN LOWER(title) LIKE ? THEN 3 WHEN LOWER(content) LIKE ? THEN 1 ELSE 0 END)" for _ in words])}
            ) as relevance
            FROM company_knowledge
            WHERE {" OR ".join(where_clauses)}
            ORDER BY relevance DESC
            LIMIT ?;
        """
        
        relevance_params = []
        for word in words:
            relevance_params.extend([f"%{word}%", f"%{word}%"])
        
        full_params = relevance_params + params + [limit]

        try:
            cursor.execute(sql, full_params)
            rows = cursor.fetchall()
            return [{"category": r["category"], "title": r["title"], "content": r["content"]} for r in rows]
        except Exception:
            cursor.execute("SELECT category, title, content FROM company_knowledge LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [{"category": r["category"], "title": r["title"], "content": r["content"]} for r in rows]


# Instância global do banco em memória
db = InMemoryChatDatabase()
