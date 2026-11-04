import os
from pathlib import Path
from typing import Dict, Optional


class SkillLoader:

    DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent / "skills"

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or self.DEFAULT_SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def load_skill_prompt(self, skill_name_or_filename: str) -> str:
        filename = skill_name_or_filename
        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        skill_path = self.skills_dir / filename
        if not skill_path.exists():
            raise FileNotFoundError(
                f"Skill '{filename}' não encontrada no diretório: {self.skills_dir}"
            )

        content = skill_path.read_text(encoding="utf-8")
        return self._extract_instructions(content)

    @staticmethod
    def _extract_instructions(content: str) -> str:
        content = content.strip()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content

skill_loader = SkillLoader()