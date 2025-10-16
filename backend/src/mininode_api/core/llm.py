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

# Helper functions kept in core to avoid duplication
async def summarize_text(source_text: str, lang: str = "es", extra_instruction: str | None = None) -> str:
    if not source_text:
        return ""
    llm = LLMClient()
    sys = ChatMessage(role="system", content=f"Eres un analista que resume contenido fielmente en {lang}. Evita inventar.")
    user_prompt = (extra_instruction.strip() + "\n\n" if extra_instruction else "") + "Resume en 4-7 frases claras:\n\n" + source_text
    usr = ChatMessage(role="user", content=user_prompt)
    return await llm.chat([sys, usr])

async def compare_summaries(blocks: list[str], lang: str = "es") -> str:
    if not blocks:
        return ""
    llm = LLMClient()
    sys = ChatMessage(role="system", content=f"Eres un analista que compara resúmenes en {lang}.")
    usr = ChatMessage(
        role="user",
        content=(
            "Compara los siguientes resúmenes (similitudes, diferencias, y conclusión breve sobre posicionamiento):\n\n"
            + "\n\n---\n\n".join(blocks)
        ),
    )
    return await llm.chat([sys, usr])
