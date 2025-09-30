from dataclasses import dataclass
from typing import List
from .config import get_settings

@dataclass
class ChatMessage:
    role: str
    content: str

class LLMClient:
    def __init__(self):
        # Deja que el SDK lea OPENAI_API_KEY del entorno (no pasamos api_key aquí)
        from openai import OpenAI
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            # Mensaje claro si falta variable
            raise RuntimeError("OPENAI_API_KEY no está definido en el entorno del servidor.")
        self._openai = OpenAI()  # usará OPENAI_API_KEY del entorno
        self._model = settings.DEFAULT_MODEL

    async def chat(self, messages: List[ChatMessage]) -> str:
        # Si el SDK o el modelo falla, la excepción sube (la veremos en el ping/debug)
        resp = self._openai.chat.completions.create(
            model=self._model,
            messages=[m.__dict__ for m in messages],
            temperature=0.2,
        )
        return resp.choices[0].message.content
