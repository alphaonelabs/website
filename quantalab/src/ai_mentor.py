"""
AI Mentor module — wraps Cloudflare Workers AI to power QuantaLab's
in-lab science tutor.
"""

import json

# System prompt that shapes the AI mentor's persona and behaviour
_SYSTEM_PROMPT = """You are QuantaMentor, an enthusiastic and patient AI science tutor for QuantaLab,
an interactive virtual laboratory.  Your role is to:

1. Explain scientific concepts clearly, adapting your language to the student's apparent level.
2. Guide students through experiments with hints, not direct answers.
3. Celebrate curiosity and correct misconceptions gently.
4. Suggest follow-up experiments when a student has mastered the current one.
5. Always relate abstract theory to real-world examples.

Keep answers concise (2–4 sentences unless a deeper explanation is clearly needed).
Use simple Markdown (bold, bullet lists) to structure longer answers.
Do NOT solve homework or give direct answers to exam questions — guide instead.
"""


async def ask_mentor(env, user_message: str, history: list[dict], domain: str = "", experiment: str = "") -> str:
    """
    Send a message to the AI mentor and return the response text.

    Args:
        env:          Cloudflare Worker environment (provides env.AI binding).
        user_message: The student's question or input.
        history:      Previous turns as [{"role": "user"|"assistant", "content": "..."}].
        domain:       Current science domain (e.g. "physics").
        experiment:   Current experiment id (e.g. "pendulum").

    Returns:
        The mentor's reply as a plain string.
    """
    context_note = ""
    if domain and experiment:
        context_note = f"\n\n[Context: student is working on the '{experiment}' experiment in {domain}.]"

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT + context_note},
        *history[-10:],  # keep the last 10 turns to stay within context limits
        {"role": "user", "content": user_message},
    ]

    response = await env.AI.run(
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        {"messages": messages},
    )

    # The Workers AI response object exposes .response for text models
    if hasattr(response, "response"):
        return str(response.response)

    # Fallback: try parsing as JSON-like object
    try:
        data = json.loads(str(response))
        return data.get("response", str(response))
    except Exception:
        return str(response)
