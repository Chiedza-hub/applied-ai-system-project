import os
import streamlit as st
from datetime import datetime
from pawpal_system import Owner, Pet, CareTask, Schedule, get_schedule_suggestions
from overdue_agent import run_recovery_agent
from breed_qa_agent import answer_breed_question

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

DATA_FILE = "data.json"

if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        st.session_state.owner = Owner.load_from_json(DATA_FILE)

if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_pet_id" not in st.session_state:
    st.session_state.selected_pet_id = None

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
CATEGORY_ICON = {"feeding": "🍽️", "exercise": "🏃", "grooming": "✂️", "medical": "🏥"}
SPECIES_ICON = {"dog": "🐕", "cat": "🐈", "other": "🐾"}


def go_to_pet(pet_id):
    st.session_state.selected_pet_id = pet_id
    st.session_state.page = "pet"


def go_home():
    st.session_state.page = "home"
    st.session_state.selected_pet_id = None


# ============================================================
# HOME PAGE
# ============================================================
if st.session_state.page == "home":
    st.title("🐾 PawPal+")
    st.caption("Your AI-powered pet care companion")
    st.divider()

    # Owner setup
    st.subheader("Owner Profile")
    owner_name = st.text_input(
        "Your name",
        value=st.session_state.owner.name if "owner" in st.session_state else "Jordan",
    )

    st.divider()

    # Pet cards
    if "owner" in st.session_state and st.session_state.owner.pets:
        owner = st.session_state.owner
        st.subheader(f"{owner.name}'s Pets")

        cols = st.columns(min(len(owner.pets), 3))
        for i, pet in enumerate(owner.pets):
            with cols[i % 3]:
                icon = SPECIES_ICON.get(pet.species, "🐾")
                overdue_count = len(pet.schedule.get_overdue_tasks())
                task_count = len(pet.schedule.tasks)

                st.markdown(f"### {icon} {pet.name}")
                st.caption(pet.species.capitalize())
                st.caption(f"{task_count} task(s) scheduled")
                if overdue_count:
                    st.caption(f"⚠️ {overdue_count} overdue")

                if st.button(f"View {pet.name}", key=f"nav_{pet.pet_id}", use_container_width=True):
                    go_to_pet(pet.pet_id)
                    st.rerun()
    else:
        st.info("No pets yet — add your first pet below to get started!")

    st.divider()

    # Add pet form
    st.subheader("Add a Pet")
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])

    if st.button("Add Pet", type="primary"):
        if "owner" not in st.session_state or st.session_state.owner.name != owner_name:
            st.session_state.owner = Owner(name=owner_name)
        owner = st.session_state.owner
        if pet_name in owner.get_all_pets():
            st.warning(f"{pet_name} is already added.")
        else:
            pet = Pet(name=pet_name, species=species, breed="Unknown", age=0)
            owner.add_pet(pet)
            owner.save_to_json(DATA_FILE)
            st.success(f"Added {pet_name}!")
            st.rerun()


# ============================================================
# PET PAGE
# ============================================================
elif st.session_state.page == "pet":
    if "owner" not in st.session_state or not st.session_state.owner.pets:
        go_home()
        st.rerun()

    owner = st.session_state.owner
    pet = next((p for p in owner.pets if p.pet_id == st.session_state.selected_pet_id), None)

    if pet is None:
        go_home()
        st.rerun()

    # Header + back button
    if st.button("← Back to Home"):
        go_home()
        st.rerun()

    icon = SPECIES_ICON.get(pet.species, "🐾")
    st.title(f"{icon} {pet.name}")
    st.caption(f"{pet.species.capitalize()} · {owner.name}'s pet")
    st.divider()

    # ── Schedule a Task ──────────────────────────────────────
    st.subheader("Schedule a Task")

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        category = st.selectbox("Category", ["feeding", "exercise", "grooming", "medical"])
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col4, col5, col6 = st.columns(3)
    with col4:
        task_date = st.date_input("Due date", value=datetime.today())
    with col5:
        task_time = st.time_input(
            "Start time",
            value=datetime.now().replace(minute=0, second=0, microsecond=0),
        )
    with col6:
        task_end_time = st.time_input(
            "End time (optional)",
            value=datetime.now().replace(minute=0, second=0, microsecond=0),
        )

    recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"])

    if st.button("Add Task", type="primary"):
        due_dt = datetime.combine(task_date, task_time)
        end_dt = datetime.combine(task_date, task_end_time)
        duration_minutes = max(0, int((end_dt - due_dt).total_seconds() / 60))
        task = CareTask(
            title=task_title,
            category=category,
            priority=priority,
            due_date=due_dt,
            recurrence=None if recurrence == "none" else recurrence,
            duration_minutes=duration_minutes,
        )
        try:
            pet.schedule.add_task(task)
            owner.save_to_json(DATA_FILE)
            st.success(f"Added '{task_title}' to {pet.name}'s schedule.")
        except ValueError as e:
            st.error(f"Could not schedule task — {e}")

    st.divider()

    # ── Suggest Schedule (collapsible) ───────────────────────
    with st.expander("💡 Suggest Schedule", expanded=False):
        st.caption(
            f"Recommendations based on {pet.name}'s species and age. "
            "Expand each task to see the reasoning and edit details before adding."
        )

        if "suggestions_by_pet" not in st.session_state:
            st.session_state.suggestions_by_pet = {}

        if pet.pet_id not in st.session_state.suggestions_by_pet:
            st.session_state.suggestions_by_pet[pet.pet_id] = get_schedule_suggestions(pet)

        pet_suggestions = st.session_state.suggestions_by_pet[pet.pet_id]

        for i, sugg in enumerate(pet_suggestions):
            p_icon = PRIORITY_ICON.get(sugg["priority"], "")
            c_icon = CATEGORY_ICON.get(sugg["category"], "")
            recur_label = sugg["recurrence"] if sugg["recurrence"] else "one-time"

            with st.container(border=True):
                st.markdown(f"**{p_icon} {c_icon} {sugg['title']}** — {sugg['suggested_time']} · {recur_label}")
                st.caption(f"💬 {sugg['reason']}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    default_time = datetime.strptime(sugg["suggested_time"], "%I:%M %p").time()
                    edited_time = st.time_input("Time", value=default_time, key=f"s_time_{pet.pet_id}_{i}")
                with c2:
                    recur_opts = ["none", "daily", "weekly"]
                    edited_recur = st.selectbox(
                        "Recurrence",
                        recur_opts,
                        index=recur_opts.index(sugg["recurrence"] or "none"),
                        key=f"s_recur_{pet.pet_id}_{i}",
                    )
                with c3:
                    edited_date = st.date_input("Start date", value=datetime.today(), key=f"s_date_{pet.pet_id}_{i}")

                if st.button("Add to Schedule", key=f"s_add_{pet.pet_id}_{i}"):
                    due_dt = datetime.combine(edited_date, edited_time)
                    task = CareTask(
                        title=sugg["title"],
                        category=sugg["category"],
                        priority=sugg["priority"],
                        due_date=due_dt,
                        recurrence=None if edited_recur == "none" else edited_recur,
                        duration_minutes=sugg.get("duration_minutes", 0),
                    )
                    try:
                        pet.schedule.add_task(task)
                        owner.save_to_json(DATA_FILE)
                        st.success(f"Added '{sugg['title']}' to {pet.name}'s schedule!")
                    except ValueError as e:
                        st.error(f"Could not add — {e}")

        if pet_suggestions:
            col_add_all, col_regen = st.columns(2)
            with col_add_all:
                if st.button("Add All Suggestions", key=f"add_all_{pet.pet_id}"):
                    added, skipped = 0, 0
                    for i, sugg in enumerate(pet_suggestions):
                        t_val = st.session_state.get(
                            f"s_time_{pet.pet_id}_{i}",
                            datetime.strptime(sugg["suggested_time"], "%I:%M %p").time(),
                        )
                        r_val = st.session_state.get(f"s_recur_{pet.pet_id}_{i}", sugg["recurrence"] or "none")
                        d_val = st.session_state.get(f"s_date_{pet.pet_id}_{i}", datetime.today().date())
                        due_dt = datetime.combine(d_val, t_val)
                        task = CareTask(
                            title=sugg["title"],
                            category=sugg["category"],
                            priority=sugg["priority"],
                            due_date=due_dt,
                            recurrence=None if r_val == "none" else r_val,
                            duration_minutes=sugg.get("duration_minutes", 0),
                        )
                        try:
                            pet.schedule.add_task(task)
                            added += 1
                        except ValueError:
                            skipped += 1
                    owner.save_to_json(DATA_FILE)
                    msg = f"Added {added} task(s) to {pet.name}'s schedule!"
                    if skipped:
                        msg += f" ({skipped} skipped due to conflicts)"
                    st.success(msg)
            with col_regen:
                if st.button("Refresh Suggestions", key=f"regen_{pet.pet_id}"):
                    del st.session_state.suggestions_by_pet[pet.pet_id]
                    st.rerun()

    # ── Show Current Schedule (collapsible) ──────────────────
    with st.expander("📅 Show Current Schedule", expanded=False):
        conflicts = pet.schedule.get_conflicts()
        if conflicts:
            st.error("⚠️ Scheduling Conflicts — these tasks overlap in time. Consider rescheduling one.")
            for c in conflicts:
                st.markdown(f"- {c}")

        all_pet_tasks = pet.schedule.sort_by_time()
        today = datetime.today().date()
        today_tasks = [t for t in all_pet_tasks if t.due_date.date() == today]
        upcoming_tasks = [t for t in all_pet_tasks if t.due_date.date() > today]
        overdue_tasks = [t for t in all_pet_tasks if t.due_date.date() < today and not t.is_completed]

        if not all_pet_tasks:
            st.info(f"No tasks scheduled for {pet.name} yet. Use Suggest Schedule above to get started!")
        else:
            if today_tasks:
                st.markdown("**Today**")
                for task in today_tasks:
                    time_str = task.due_date.strftime("%I:%M %p")
                    recur_badge = f" _(repeats {task.recurrence})_" if task.recurrence else ""
                    p_icon = PRIORITY_ICON.get(task.priority, "")
                    c_icon = CATEGORY_ICON.get(task.category, "")
                    if task.is_completed:
                        st.success(f"✅ **{time_str}** — {c_icon} {task.title} [{task.category}]{recur_badge}")
                    else:
                        col_task, col_btn = st.columns([5, 1])
                        with col_task:
                            st.info(f"{p_icon} **{time_str}** — {c_icon} {task.title} [{task.category}]{recur_badge}")
                        with col_btn:
                            if st.button("✓ Done", key=f"complete_{task.task_id}"):
                                pet.schedule.complete_task(task.task_id)
                                owner.save_to_json(DATA_FILE)
                                st.rerun()
            else:
                st.info(f"No tasks scheduled for {pet.name} today.")

            if overdue_tasks:
                st.markdown(f"**⚠️ Overdue ({len(overdue_tasks)})**")
                for task in overdue_tasks:
                    col_task, col_btn = st.columns([5, 1])
                    with col_task:
                        st.warning(
                            f"🔴 **{task.due_date.strftime('%b %d, %I:%M %p')}** — "
                            f"{task.title} [{task.category}]"
                        )
                    with col_btn:
                        if st.button("✓ Done", key=f"complete_{task.task_id}"):
                            pet.schedule.complete_task(task.task_id)
                            owner.save_to_json(DATA_FILE)
                            st.rerun()

            if upcoming_tasks:
                st.markdown(f"**Upcoming ({len(upcoming_tasks)})**")
                rows = [
                    {
                        "Date": t.due_date.strftime("%b %d"),
                        "Time": t.due_date.strftime("%I:%M %p"),
                        "Task": t.title,
                        "Category": t.category,
                        "Priority": t.priority,
                        "Recurs": t.recurrence or "—",
                        "Status": "✅ Done" if t.is_completed else "⏳ Pending",
                    }
                    for t in upcoming_tasks
                ]
                st.table(rows)

    st.divider()

    # ── Overdue Task Recovery Agent ──────────────────────────
    st.subheader("🤖 Overdue Task Recovery Agent")
    st.caption(
        "The agent reasons about your overdue backlog and proposes a realistic catch-up plan. "
        "Confirm before any changes are saved."
    )

    all_overdue = pet.schedule.get_overdue_tasks()
    all_tasks = owner.get_all_tasks()

    if not all_overdue:
        st.success(f"✅ No overdue tasks for {pet.name} — schedule is up to date.")
    else:
        st.warning(f"⚠️ {len(all_overdue)} overdue task(s) detected.")
        for t in all_overdue:
            days_overdue = (datetime.today().date() - t.due_date.date()).days
            overdue_label = f"{days_overdue} day{'s' if days_overdue != 1 else ''} overdue"
            c_icon = CATEGORY_ICON.get(t.category, "📌")
            p_icon = PRIORITY_ICON.get(t.priority, "")
            st.markdown(
                f"- {p_icon} {c_icon} **{t.title}** — "
                f"was due {t.due_date.strftime('%b %d at %I:%M %p')} _{overdue_label}_"
            )

        if st.session_state.get("agent_error"):
            st.error(f"Agent error: {st.session_state.pop('agent_error')}")

        if st.button("🤖 Run Recovery Agent", type="primary"):
            with st.spinner("Analysing backlog and generating catch-up plan…"):
                try:
                    plan = run_recovery_agent(all_overdue, all_tasks)
                    st.session_state.recovery_plan = plan
                except Exception as e:
                    st.session_state.agent_error = str(e)
            st.rerun()

        if "recovery_plan" in st.session_state:
            plan = st.session_state.recovery_plan
            st.markdown("---")
            st.markdown("### 📋 Proposed Catch-Up Plan")
            st.info(plan.get("analysis", ""))
            proposals = plan.get("proposals", [])
            if proposals:
                for p in proposals:
                    try:
                        new_dt = datetime.fromisoformat(p["new_date"])
                        new_date_str = new_dt.strftime("%a, %b %d at %I:%M %p")
                    except Exception:
                        new_date_str = p.get("new_date", "Unknown")
                    orig_task = next((t for t in all_overdue if t.task_id == p["task_id"]), None)
                    orig_str = orig_task.due_date.strftime("%b %d at %I:%M %p") if orig_task else "Unknown"
                    p_icon = PRIORITY_ICON.get(orig_task.priority if orig_task else "low", "⚪")
                    c_icon = CATEGORY_ICON.get(orig_task.category if orig_task else "", "📌")
                    with st.expander(
                        f"{p_icon} {c_icon} **{p['title']}** — {p.get('pet', '')} → {new_date_str}",
                        expanded=True,
                    ):
                        st.markdown(f"**Was due:** {orig_str}  \n**Rescheduled to:** {new_date_str}")
                        st.caption(f"💬 {p.get('reasoning', '')}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Confirm & Apply All Changes", type="primary"):
                        applied, errors = 0, []
                        for p in proposals:
                            try:
                                new_dt = datetime.fromisoformat(p["new_date"])
                                for t in pet.schedule.tasks:
                                    if t.task_id == p["task_id"]:
                                        t.reschedule(new_dt)
                                        applied += 1
                            except Exception as e:
                                errors.append(str(e))
                        owner.save_to_json(DATA_FILE)
                        del st.session_state.recovery_plan
                        if errors:
                            st.warning(f"Applied {applied} task(s) with {len(errors)} error(s).")
                        else:
                            st.success(f"✅ Rescheduled {applied} task(s) successfully!")
                        st.rerun()
                with col2:
                    if st.button("❌ Dismiss Plan"):
                        del st.session_state.recovery_plan
                        st.rerun()

    st.divider()

    # ── Breed Care Q&A ───────────────────────────────────────
    st.subheader("🐕 Breed Care Q&A")
    st.caption(
        "Ask anything about a specific breed — exercise needs, grooming schedules, health risks, diet, and more. "
        "Answers are grounded in the PawPal breed guide library."
    )

    EXAMPLE_QUESTIONS = [
        "How much exercise does a Border Collie need?",
        "How often should I groom a Golden Retriever?",
        "What health issues should I watch for in a Maine Coon?",
        "How much should I feed a Labrador Retriever?",
        "Are Siberian Huskies good apartment dogs?",
        "How do I take care of a Persian cat's coat?",
    ]

    with st.expander("Example questions", expanded=False):
        for q in EXAMPLE_QUESTIONS:
            st.markdown(f"- {q}")

    breed_question = st.text_input(
        "Ask a breed care question",
        placeholder="e.g. How much exercise does a Border Collie need?",
        key="breed_question_input",
    )

    if st.button("🔍 Ask", type="primary", key="breed_qa_submit"):
        if not breed_question.strip():
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Retrieving breed guide and generating answer…"):
                try:
                    result = answer_breed_question(breed_question.strip())
                    st.session_state.breed_qa_result = result
                    st.session_state.breed_qa_question = breed_question.strip()
                except Exception as e:
                    st.session_state.breed_qa_error = str(e)
            st.rerun()

    if st.session_state.get("breed_qa_error"):
        st.error(f"Q&A error: {st.session_state.pop('breed_qa_error')}")

    if "breed_qa_result" in st.session_state:
        result = st.session_state.breed_qa_result
        question = st.session_state.get("breed_qa_question", "")

        confidence = result.get("confidence", "low")
        confidence_badge = {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}.get(confidence, "🔴 Low")
        sources = result.get("sources", [])
        sources_str = ", ".join(sources) if sources else "no guide matched"

        st.markdown("---")
        st.markdown(f"**Q: {question}**")
        st.info(result.get("answer", ""))

        key_facts = result.get("key_facts", [])
        if key_facts:
            with st.expander("Supporting facts from breed guide", expanded=True):
                for fact in key_facts:
                    st.markdown(f"- {fact}")

        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Source guide(s): **{sources_str}**")
        with col2:
            st.caption(f"Confidence: {confidence_badge}")

        if st.button("Clear answer", key="breed_qa_clear"):
            del st.session_state.breed_qa_result
            if "breed_qa_question" in st.session_state:
                del st.session_state.breed_qa_question
            st.rerun()
