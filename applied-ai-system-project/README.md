# PawPal+ — AI-Powered Pet Care Scheduling

> A Streamlit application that helps busy pet owners stay consistent with pet care, powered by the Anthropic Claude API for intelligent scheduling recovery and breed-specific guidance.

## Loom Walkthrough

[Watch the walkthrough](https://www.loom.com/share/9b07c2bfc7a04874bd781b8874fa824d)


---

## Original Project (Modules 1–3)

**PawPal+** was first built in Modules 1–3 as a structured pet care scheduling system. The goal was to give a busy owner a single place to manage all care tasks across multiple pets — walks, feedings, medications, grooming, and vet appointments — with automatic conflict detection so no two tasks could accidentally overlap. The system introduced recurring tasks (daily/weekly auto-scheduling), time-range conflict detection across both same-pet and cross-pet schedules, overdue task surfacing, and a Streamlit web UI that saved all data to a local JSON file between sessions.

---

## Title and Summary

**PawPal+** is an AI-augmented pet care planner that turns a reactive to-do list into a proactive, intelligent assistant. It does three things no ordinary task tracker can:

1. **Detects scheduling conflicts in real time** — adding a vet appointment that overlaps a walk raises an error before the conflict is saved.
2. **Recovers automatically from a missed-task backlog** — a Claude-powered agent inspects every overdue task, reasons about priority and pet-specific scheduling constraints, and proposes a realistic multi-day catch-up plan for the owner to confirm or dismiss.
3. **Answers breed-specific care questions with grounded, cited facts** — a RAG agent retrieves the relevant breed guide and instructs Claude to answer using only that data, so every answer cites real numbers (e.g., "120 minutes of daily exercise") instead of generic advice.

This matters because pet care is surprisingly easy to let slip. A single tool that combines scheduling, conflict prevention, AI-powered backlog recovery, and expert breed guidance removes the friction that causes owners to forget or undercare for their animals.

---

## Architecture Overview
The image below shows how the three modules — the core data system, the overdue recovery agent, and the breed Q&A agent — connect through the `Owner` and `Schedule` layers, with all AI responses passing through a human review step before any changes are written.
![PawPal+ System Architecture](final%20architecture%20image.png)

**Core data model (`pawpal_system.py`):** Four dataclasses — `Owner`, `Pet`, `Schedule`, `CareTask` — handle the full lifecycle of task management. `Schedule` enforces time-range overlap detection on every `add_task()` call, and `Owner` aggregates cross-pet conflicts. `get_schedule_suggestions()` produces species- and age-aware starter tasks without touching the AI layer.

**Overdue recovery agent (`overdue_agent.py`):** Collects every incomplete past-due task across all pets, packages them with the next 7 days of upcoming tasks for context, and calls `claude-opus-4-7` with a `propose_catch_up_plan` tool and `tool_choice: any` to force a structured JSON response. The agent respects priority rules (medical > feeding > exercise > grooming > wellness), avoids 7 am–8 pm guardrails, and spreads the backlog across multiple days. The plan is shown to the owner before any changes are written.

**Breed Q&A agent (`breed_qa_agent.py`):** Loads all 12 breed JSON guides at query time, runs keyword and alias matching to select the 1–2 most relevant guides, and passes them as grounded context to Claude with strict instructions not to supplement with general knowledge. The `provide_breed_answer` tool returns a structured answer, a list of key facts, and a confidence level (`high` / `medium` / `low`). The system prompt is marked `cache_control: ephemeral` to reduce API latency on repeated questions.

**Persistence (`data.json`):** `Owner.save_to_json()` / `Owner.load_from_json()` serialize the full owner–pet–task graph to disk so data survives Streamlit reruns.

---

## Setup Instructions

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd applied-ai-system-project

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

The key is required for the Overdue Recovery Agent and Breed Q&A features. The scheduling system itself runs without it.

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 5. Run the test suite

```bash
python -m pytest test_pawpal.py -v
```

All **28 tests** should pass.

---

## Sample Interactions

### 1. Breed Q&A — "How much exercise does a Border Collie need?"

**User input (Streamlit Q&A field):**
> How much exercise does a Border Collie need?

**AI output:**
```
Breed identified: Border Collie
Confidence: high

Answer:
Border Collies are a high-energy herding breed that require a minimum of 120 minutes of
vigorous exercise every day — significantly more than most other breeds. This is best
split across multiple sessions: a long morning run or off-leash fetch, a midday mental
stimulation activity like agility or puzzle work, and an evening walk. Without sufficient
exercise, Border Collies become destructive and anxious. They are exceptionally
intelligent and need mental challenges alongside physical activity to stay balanced.

Key facts:
• 120 minutes of daily exercise required
• High intensity — running, agility, herding trials, frisbee
• Mental stimulation is as important as physical exercise
• Under-exercised Border Collies develop destructive behaviours
```

---

### 2. Overdue Task Recovery — 3 missed tasks across 2 pets

**System state:** Jordan owns Mochi (dog) and Luna (cat). Three tasks are overdue by 1–3 days: Mochi's "Morning walk" (high, exercise, 3 days overdue), Luna's "Flea treatment" (high, medical, 2 days overdue), and Mochi's "Teeth brushing" (low, grooming, 1 day overdue).

**AI output (rendered in Streamlit):**

```
Analysis:
3 tasks are overdue across 2 pets. The highest priority is Luna's flea treatment —
medical tasks take precedence regardless of how many days overdue. Mochi's morning
walk is critical for physical and behavioural health and should be rescheduled next.
Teeth brushing is low-priority and can follow at the end of the spread. I've
distributed the tasks across 2 days to avoid overloading a single afternoon.

Proposed catch-up plan:

Task                  | Original Due   | New Slot               | Reasoning
----------------------|----------------|------------------------|----------------------------------
Luna — Flea treatment | Apr 25 9:00 AM | Apr 27 9:00 AM (today) | Medical tasks get first priority;
                      |                |                        | scheduling immediately today.
Mochi — Morning walk  | Apr 24 8:00 AM | Apr 27 10:00 AM        | High-priority exercise; placed
                      |                |                        | after flea treatment to avoid
                      |                |                        | same-time cross-pet demand.
Mochi — Teeth brush   | Apr 26 8:00 PM | Apr 28 8:00 PM         | Low-priority grooming spread
                      |                |                        | to Day 2 to keep today light.

[Confirm Plan]  [Dismiss]
```

---

### 3. Time-Range Conflict Detection — adding a task that overlaps

**User action:** Mochi already has a "Vet visit" scheduled 9:00–10:00 AM. The owner tries to add a "Morning walk" at 9:15 AM with a 45-minute duration.

**System response (Streamlit warning banner):**
```
⚠ Conflict for Mochi: 'Morning walk' (09:15 AM–10:00 AM) overlaps with
'Vet visit' (09:00 AM–10:00 AM).

Task was not saved. Please choose a different time slot.
```

The underlying task list is unchanged — the conflict is enforced at the `Schedule.add_task()` level before any write occurs.

---

## Design Decisions

### Forced tool use instead of free-form text

Both agents use `tool_choice: {"type": "any"}`, which forces Claude to call the defined tool rather than return prose. This eliminates parsing logic and guarantees a machine-readable JSON response — critical when the output needs to drive UI rendering or call `reschedule()` on real task objects. The trade-off is reduced flexibility: if Claude genuinely cannot form a plan, it still calls the tool with empty proposals rather than explaining why.

### RAG over fine-tuning for breed knowledge

Breed facts are stored as structured JSON guides and retrieved at query time rather than baked into a fine-tuned model. This makes updates cheap (edit a JSON file, no retraining), keeps hallucination risk low (the system prompt explicitly bans supplementing with general knowledge), and lets the retriever return a confidence score based on whether the exact breed was found. The downside is that the retriever is keyword-based — a question like "What should I know about herding dogs?" won't reliably surface a Border Collie guide the way "Border Collie grooming" would.

### Confirmation before writes

The recovery agent proposes a plan stored in `st.session_state.recovery_plan` — no `reschedule()` calls happen until the owner clicks "Confirm." This was a deliberate design choice: an AI suggesting a plan that silently mutates a schedule would feel unsafe and break user trust. The cost is one extra click; the benefit is the owner retains full control.

### Completed tasks are retained, not deleted

`is_completed = True` keeps tasks in the list indefinitely rather than removing them. This preserves the full care history (queryable via `get_task_history()`) and means the overdue agent can never accidentally re-schedule something the owner marked done. The trade-off is that every conflict scan and filter must explicitly skip completed tasks — a small performance cost that's negligible at the scale of a single-owner app.

### Pet identity via UUID, not name

`Pet.pet_id` is a UUID assigned at construction. Early in development, `get_tasks_for_pet()` matched by name, which broke silently when two pets shared a name. The UUID approach is unambiguous regardless of display names.

---

## Testing Summary

### Test suite: 28 tests, all passing

| Area | Tests | What is verified |
|---|---|---|
| **Core behavior** | 5 | Task completion, adding tasks, overdue detection, owner pet management |
| **Sorting** | 4 | Chronological and reverse order, non-mutation of original list, empty schedule |
| **Recurrence** | 3 | Daily auto-creates next occurrence, fields inherit correctly, non-recurring tasks don't spawn duplicates |
| **Time-range conflict detection** | 8 | Overlapping ranges, back-to-back non-overlap, contained range, point-in-time within range, cross-pet overlap and non-overlap, duration inheritance on recurrence |
| **Schedule suggestions** | 13 | Required keys, valid priorities/categories, species-based suggestions (dogs get exercise, cats don't), age-based feeding count, pet-name personalization in reasons |
| **Breed guide loading** | 8 | 12 guides load, all required keys present, valid species, daily_minutes is numeric, lifespan and care_summary present |
| **Breed guide retrieval** | 11 | Exact breed match, case-insensitive match, alias match (lab, huskies), species fallback, top-k limit, data spot-checks (Border Collie 120 min, Bulldog 30 min, Persian daily brushing) |

### What worked well

The RAG retrieval pipeline was the most satisfying piece to get right. The three-tier matching strategy — exact breed name first, then aliases (e.g. "lab" → Labrador Retriever, "huskies" → Siberian Husky), then species keyword fallback means the agent almost always surfaces the correct guide on the first try without any vector database or embeddings. Keeping the retrieval deterministic and offline also made it straightforward to unit-test: every retrieval behavior is verified against the actual JSON guides, so the test suite confirms correctness without making a single API call.


### What didn't work / gaps

- **Agent tests are intentionally offline.** `answer_breed_question()` and `run_recovery_agent()` are not called in the test suite because they require a live API key and incur cost. This means end-to-end AI behavior is validated manually, not automatically.
- **Cross-pet conflict with 3+ overlapping pets** was flagged as a known edge case: the pair-reporting logic correctly deduplicates, but a scenario where pets A, B, and C all overlap simultaneously is technically covered (all three pairs are reported), though it was not explicitly tested.
- **Conflict detection window.** The current logic treats a 1-minute gap as conflict-free. A real scheduler might want a configurable buffer (e.g., 15 minutes of transition time between tasks).
- **Confidence scoring is surfaced but not acted on.** The breed Q&A agent returns a `confidence` field (`high` / `medium` / `low`) based on whether the exact breed was matched, but the UI displays it as a label only. A next iteration could use low-confidence responses to trigger a warning or prompt the owner to confirm before acting on the advice.

---

## Reflection

### What went well

Working with AI as the head architect was the most satisfying part of this project. Using the AI to implement changes and assist with debugging saved significant time — I could describe a behavior and get working code fast, then focus my energy on reviewing the invariants and edge cases that AI tends to miss. That division of labor felt natural and productive.

The RAG retrieval pipeline was also the most technically satisfying piece. The three-tier matching strategy — exact breed name, then aliases, then species fallback — means the agent surfaces the right guide on the first try for almost any real-world query, all without a vector database or embeddings.

### What this project taught me about AI and problem-solving

The biggest lesson was that AI makes a great implementer but a poor architect. When I described a feature and asked Claude (the AI assistant) to write it, the output was fast and usually correct but it consistently chose the simplest interpretation. When `get_tasks_for_pet()` was first drafted, it matched pets by name. That works until an owner has two pets named "Max" — at which point it fails silently. I only caught this by manually tracing the code, not by accepting the AI's first answer. The fix (switching to UUID lookup) came from my own design review, not from the AI.

This shaped how I worked for the rest of the project: AI for speed and boilerplate, human judgment for invariants and edge cases. There are far more edge cases than you initially expect, and it's tempting to be uncritical when AI produces confident-looking output — but some of what it generates needs a close second look.

**On agents specifically:** Forced tool use (via `tool_choice: any`) was a game-changer for reliability. Free-form responses require fragile parsing; structured tool responses are directly usable by the application. The mental model shift from "ask Claude a question" to "ask Claude to fill out a form" made both the overdue agent and the breed Q&A agent dramatically easier to integrate.

**On trade-offs:** The hardest part was deciding which trade-offs were acceptable. Four stood out:

- **Keeping completed tasks vs. deleting them.** Retaining completed tasks as `is_completed = True` preserves the full care history and prevents the overdue agent from ever accidentally re-scheduling something the owner already did. The cost is that every filter, conflict scan, and overdue query must explicitly skip completed tasks — small now, but a performance concern if the task list grows to thousands of entries over years of use.
- **RAG retrieval vs. fine-tuning.** Storing breed knowledge as JSON files and retrieving them at query time means the knowledge base is easy to update (edit a file, no retraining) and every answer is grounded in data that can be inspected and tested. The cost is retrieval quality: the keyword-and-alias matcher works well for direct breed name questions but fails on semantic queries like "what dog needs the least exercise?" — a fine-tuned or embedding-based system would handle those better.
- **Forced tool use vs. free-form responses.** Using `tool_choice: any` guarantees a machine-readable JSON response every time, which means zero parsing logic and easy unit-testable outputs. The cost is that if Claude genuinely cannot form a valid plan — say, all 7 days are already fully booked — it still calls the tool with incomplete proposals rather than explaining why it got stuck.
- **Confirmation before writes vs. auto-apply.** Requiring the owner to click "Confirm" before any recovery plan is saved means no AI-generated change ever reaches `data.json` silently. The cost is one extra interaction step, but the benefit is that the owner remains the decision-maker — the agent advises, it does not act unilaterally. That distinction matters in a system that touches real care routines.

### What I would do differently

If I had another iteration, I would extend conflict detection to flag tasks within a configurable time buffer (e.g., 30 minutes apart) rather than requiring exact overlap — the current 1-minute gap threshold is too permissive for a real scheduling assistant. I would also add embeddings-based retrieval to the breed Q&A agent so semantic queries like "what dog needs the least exercise?" return the right guide, not just exact breed-name matches.

### Limitations and biases

The breed guide knowledge base covers 12 popular breeds, which means the system is biased toward common Western pet ownership patterns, Golden Retrievers and Siamese cats are well-covered; a Basenji or a Sphynx is not. For any unrecognized breed, the agent falls back to species-level generics and flags confidence as `low`, but a user who doesn't notice that label could act on advice that doesn't fit their animal. The overdue recovery agent also inherits whatever prioritization biases are baked into its system prompt, medical tasks are always ranked first, which is generally correct but could be wrong in context (e.g., a low-stakes vet recheck outranking a critical feeding for a diabetic pet).

### Could the AI be misused, and how would I prevent that?

The most realistic misuse vector is trust without verification, an owner accepts a recovery plan or a breed care answer without checking whether it's appropriate for their specific animal. The system mitigates this in two ways: the overdue agent requires explicit owner confirmation before writing any changes, and the breed Q&A agent exposes a `confidence` rating so low-confidence answers are visibly flagged. A stronger safeguard would be adding a disclaimer on every AI-generated response ("This is a general guide - consult your vet for medical decisions") and blocking the agent from ever scheduling medical tasks without a vet note field being filled in.

### What surprised me while testing the AI's reliability

The biggest surprise was how consistent the structured tool responses were. I expected the forced tool use (`tool_choice: any`) to occasionally produce malformed JSON or miss required fields but in every manual test run, the `propose_catch_up_plan` and `provide_breed_answer` tools returned complete, well-formed responses on the first call. What was less reliable was the *reasoning quality*: the overdue agent sometimes proposed slots that technically avoided conflicts but were impractical (e.g., scheduling a dog walk at 7:05 AM on a Saturday). The structure was always correct; the judgment occasionally needed a second look. That gap, reliable format, imperfect reasoning,is exactly why the human confirmation step exists.

---

## Project Structure

```
applied-ai-system-project/
├── app.py                  # Streamlit web interface
├── pawpal_system.py        # Core data model: Owner, Pet, Schedule, CareTask
├── overdue_agent.py        # AI overdue task recovery agent
├── breed_qa_agent.py       # RAG-based breed Q&A agent
├── test_pawpal.py          # 28-test pytest suite
├── requirements.txt        # streamlit, anthropic, pytest
├── data.json               # Persistent owner/pet/task storage
├── uml_final.png           # System design diagram
├── reflection.md           # Design and reflection notes
└── breed_guides/
    ├── dogs/               # 8 breed guides (Golden Retriever, Border Collie, etc.)
    └── cats/               # 4 breed guides (Persian, Siamese, Maine Coon, Ragdoll)
```
