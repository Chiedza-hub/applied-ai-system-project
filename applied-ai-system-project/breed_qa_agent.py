from __future__ import annotations
import json
from pathlib import Path

import anthropic

_client = anthropic.Anthropic()
_GUIDES_DIR = Path(__file__).parent / "breed_guides"

# ── Tool definition ──────────────────────────────────────────────────────────

_ANSWER_TOOL = {
    "name": "provide_breed_answer",
    "description": (
        "Provide a grounded answer to a breed care question using ONLY the "
        "retrieved breed guide data. Never use general knowledge not present in the guide."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "breed_identified": {
                "type": "string",
                "description": "Exact breed name from the guide, or 'unknown' if no guide matched.",
            },
            "answer": {
                "type": "string",
                "description": (
                    "3-6 sentence answer grounded in specific numbers and details "
                    "from the breed guide (e.g. '120 minutes daily', 'every 4-6 weeks')."
                ),
            },
            "key_facts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 bullet-point facts from the guide that directly support the answer.",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": (
                    "high = exact breed found in guides; "
                    "medium = related breed or partial match; "
                    "low = no breed match, answer is generic."
                ),
            },
        },
        "required": ["breed_identified", "answer", "key_facts", "confidence"],
    },
}

# Stable system prompt — cached at runtime
_SYSTEM = (
    "You are PawPal's breed care specialist. "
    "Answer pet care questions using ONLY the breed guide data provided in the user message — "
    "never substitute or supplement with general knowledge.\n\n"
    "Rules:\n"
    "1. Cite specific numbers and details from the guide (e.g. '120 minutes of exercise daily', "
    "'brush 2-3 times per week').\n"
    "2. If the question asks about a breed not present in the provided guides, say so explicitly "
    "and set confidence to 'low'.\n"
    "3. Answers must be 3-6 sentences: concise, practical, and owner-focused.\n"
    "4. Always name the breed in your answer.\n"
    "5. Never fabricate statistics or health claims not in the guide.\n\n"
    "Always respond by calling the provide_breed_answer tool — no extra prose."
)

# ── Guide loading & retrieval ────────────────────────────────────────────────

def _load_guides() -> list[dict]:
    guides = []
    for path in _GUIDES_DIR.glob("**/*.json"):
        try:
            with open(path) as f:
                guides.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass
    return guides


def _find_relevant_guides(question: str, guides: list[dict], top_k: int = 2) -> list[dict]:
    """Return the most relevant guides for the question using name and keyword matching."""
    q = question.lower()

    # Exact breed name or alias match — highest priority
    for guide in guides:
        names = [guide.get("breed", "").lower()] + [
            a.lower() for a in guide.get("aliases", [])
        ]
        if any(name and name in q for name in names):
            return [guide]

    # Species keyword fallback
    if any(w in q for w in ["dog", "puppy", "canine"]):
        candidates = [g for g in guides if g.get("species") == "dog"]
    elif any(w in q for w in ["cat", "kitten", "feline"]):
        candidates = [g for g in guides if g.get("species") == "cat"]
    else:
        candidates = guides

    return candidates[:top_k]


# ── Public API ───────────────────────────────────────────────────────────────

def answer_breed_question(question: str) -> dict:
    """
    Retrieve relevant breed guides and answer the question with grounded advice.

    Returns:
        {
            "breed":      str,         # breed name identified
            "answer":     str,         # grounded answer
            "key_facts":  list[str],   # supporting facts from the guide
            "confidence": str,         # "high" | "medium" | "low"
            "sources":    list[str],   # breed names of guides consulted
        }
    """
    guides = _load_guides()
    if not guides:
        return {
            "breed": "unknown",
            "answer": (
                "No breed guides are available. "
                "Please ensure the breed_guides/ directory contains valid JSON files."
            ),
            "key_facts": [],
            "confidence": "low",
            "sources": [],
        }

    relevant = _find_relevant_guides(question, guides)
    context = json.dumps(relevant, indent=2)

    user_msg = (
        f"BREED GUIDE DATA:\n{context}\n\n"
        f"OWNER QUESTION: {question}\n\n"
        "Answer using only the breed guide data above."
    )

    response = _client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[_ANSWER_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "provide_breed_answer":
            inp = block.input
            return {
                "breed": inp.get("breed_identified", "unknown"),
                "answer": inp.get("answer", ""),
                "key_facts": inp.get("key_facts", []),
                "confidence": inp.get("confidence", "low"),
                "sources": [g.get("breed", "?") for g in relevant],
            }

    return {
        "breed": "unknown",
        "answer": "The agent did not return an answer. Please try again.",
        "key_facts": [],
        "confidence": "low",
        "sources": [],
    }
