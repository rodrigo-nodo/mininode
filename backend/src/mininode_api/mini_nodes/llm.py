from mininode_api.core.llm import LLMClient, ChatMessage

async def summarize_text(source_text: str, lang: str = "es", extra_instruction: str | None = None) -> str:
    if not source_text:
        return ""
    llm = LLMClient()
    sys = ChatMessage(role="system", content=f"Eres un analista que resume contenido fielmente en {lang}. Evita inventar.")
    user_prompt = (extra_instruction.strip() + "\n\n" if extra_instruction else "") + \
                  "Resume en 4–7 frases claras:\n\n" + source_text
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
            "Compara los siguientes resúmenes (similitudes, diferencias, y conclusión breve sobre posicionamiento):\n\n" +
            "\n\n---\n\n".join(blocks)
        )
    )
    return await llm.chat([sys, usr])
