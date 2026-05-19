import os
from pathlib import Path
import anthropic

MODEL = "claude-sonnet-4-6"

_client = None

def _load_env():
    """Load .env from the project root if ANTHROPIC_API_KEY isn't already set."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

_load_env()


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to a .env file in the project folder or export it in your shell."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def chat(messages: list[dict], system: str = "", max_tokens: int = 4096) -> str:
    client = get_client()
    kwargs = {"model": MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text


def chat_with_vision(
    text_prompt: str,
    images: list[tuple[str, str]],  # [(base64_data, media_type), ...]
    system: str = "",
    max_tokens: int = 4096,
) -> str:
    content = []
    for b64, mtype in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mtype, "data": b64},
        })
    content.append({"type": "text", "text": text_prompt})
    return chat([{"role": "user", "content": content}], system=system, max_tokens=max_tokens)


def chat_with_web_search(prompt: str, system: str = "", max_tokens: int = 8192) -> tuple[str, list[str]]:
    """Returns (response_text, list_of_citations)."""
    client = get_client()
    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "tools": tools,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    citations = []
    full_text = []

    # Agentic loop — keep going until stop_reason is not tool_use
    while True:
        response = client.messages.create(**kwargs)
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason != "tool_use":
            for block in assistant_content:
                if hasattr(block, "text"):
                    full_text.append(block.text)
            break

        # Process tool uses
        tool_results = []
        for block in assistant_content:
            if block.type == "tool_use":
                # The API handles web_search natively; results are in subsequent response
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "",
                })
            elif hasattr(block, "text"):
                full_text.append(block.text)

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return "\n".join(full_text), citations
