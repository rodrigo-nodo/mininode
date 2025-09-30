from dataclasses import dataclass
from typing import List
from .config import get_settings

@dataclass
class ChatMessage:
    role: str
    content: str

class LLMClient:
    def __init__(self):
        from openai import OpenAI  # import diferido
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY no está definido.")
        self._openai = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.DEFAULT_MODEL

    async def chat(self, messages: List[ChatMessage]) -> str:
        resp = self._openai.chat.completions.create(
            model=self._model,
            messages=[m.__dict__ for m in messages],
            temperature=0.2,
        )
        return resp.choices[0].message.content
