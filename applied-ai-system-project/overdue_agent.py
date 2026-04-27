from __future__ import annotations
import json
from datetime import datetime, timedelta

import anthropic

_client = anthropic.Anthropic()

# ── Tool definition ──────────────────────────────────────────────────────────

_PROPOSE_TOOL = {
    "name": "propose_catch_up_plan",
    "description": (
        "Propose a realistic, conflict-aware catch-up schedule for all overdue tasks. "
        "Call this tool with your complete plan."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "analysis": {
                "type": "string",
                "description": (
                    "2–4 sentence assessment: how many tasks are overdue, "
                    "which are most critical, any conflicts noticed, "
                    "and the overall scheduling strategy."
                ),
            },
            "proposals": {
                "type": "array",
                "description": "One entry per overdue task.",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "title": {"type": "string"},
                        "pet": {"type": "string"},
                        "new_date": {
                            "type": "string",
                            "description": "Rescheduled datetime in ISO 8601 (YYYY-MM-DDTHH:MM:SS).",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "One sentence explaining why this slot was chosen.",
                        },
                    },
                    "required": ["task_id", "title", "pet", "new_date", "reasoning"],
                },
            },
        },
        "required": ["analysis", "proposals"],
    },
}

# Stable system prompt — cached at runtime (≥ 1 024 tokens is the cache minimum
# but even smaller prompts benefit from the cache_control marker).
_SYSTEM = (
    "You are a pet care scheduling assistant. "
    "When given a list of overdue tasks and an existing schedule, produce a realistic catch-up plan.\n\n"
    "Scheduling rules:\n"
    "1. Prioritise by category urgency: medical > feeding > exercise > grooming > wellness.\n"
    "2. Within the same category, sort by priority: high > medium > low.\n"
    "3. Spread tasks across multiple days — avoid piling too many tasks onto one day.\n"
    "4. Only schedule tasks between 07:00 and 20:00.\n"
    "5. Leave at least the task's duration_minutes between consecutive slots for the same pet.\n"
    "6. Never schedule a task at or before the current time.\n"
    "7. If two pets share an owner, avoid scheduling their high-effort tasks simultaneously.\n\n"
    "Always respond by calling the propose_catch_up_plan tool — do not add any extra prose."
)

# ── Helper functions ─────────────────────────────────────────────────────────

def _summarise_overdue(tasks: list) -> list[dict]:
    now = datetime.now()
    return [
        {
            "task_id": t.task_id,
            "title": t.title,
            "pet": t.assigned_pet.name if t.assigned_pet else "Unknown",
            "category": t.category,
            "priority": t.priority,
            "original_due": t.due_date.strftime("%Y-%m-%d %H:%M"),
            "days_overdue": max(0, (now - t.due_date).days),
            "duration_minutes": t.duration_minutes or 0,
        }
        for t in tasks
    ]


def _summarise_upcoming(tasks: list, days: int = 7) -> list[dict]:
    now = datetime.now()
    cutoff = now + timedelta(days=days)
    return [
        {
            "title": t.title,
            "pet": t.assigned_pet.name if t.assigned_pet else "Unknown",
            "scheduled": t.due_date.strftime("%Y-%m-%d %H:%M"),
            "duration_minutes": t.duration_minutes or 0,
        }
        for t in tasks
        if not t.is_completed and now <= t.due_date <= cutoff
    ]


# ── Public API ───────────────────────────────────────────────────────────────

def run_recovery_agent(overdue_tasks: list, all_tasks: list) -> dict:
    """
    Analyse overdue tasks and return a proposed catch-up plan.

    Returns:
        {
            "analysis":  str,   # reasoning summary
            "proposals": list,  # [{task_id, title, pet, new_date, reasoning}, …]
        }
    """
    today = datetime.now()
    overdue_data = _summarise_overdue(overdue_tasks)
    upcoming_data = _summarise_upcoming(all_tasks)

    spread_days = max(3, len(overdue_data))
    user_msg = (
        f"Today is {today.strftime('%A, %B %d, %Y at %I:%M %p')}.\n\n"
        f"OVERDUE TASKS ({len(overdue_data)} total):\n"
        f"{json.dumps(overdue_data, indent=2)}\n\n"
        f"UPCOMING SCHEDULE — next 7 days (for conflict awareness):\n"
        f"{json.dumps(upcoming_data, indent=2)}\n\n"
        f"Please analyse this backlog and call propose_catch_up_plan with a realistic schedule "
        f"spread across the next {spread_days} days."
    )

    response = _client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": _SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[_PROPOSE_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "propose_catch_up_plan":
            return block.input

    return {
        "analysis": "The agent did not return a plan. Please try again.",
        "proposals": [],
    }
