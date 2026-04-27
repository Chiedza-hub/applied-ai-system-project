import os
import streamlit as st
from datetime import datetime
from pawpal_system import Owner, Pet, CareTask, Schedule, get_schedule_suggestions
from overdue_agent import run_recovery_agent
from breed_qa_agent import answer_breed_question

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

DATA_FILE = "data.json"

if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        st.session_state.owner = Owner.load_from_json(DATA_FILE)

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
CATEGORY_ICON = {"feeding": "🍽️", "exercise": "🏃", "grooming": "✂️", "medical": "🏥"}


st.divider()

# --- Owner & Pet Setup ---
st.subheader("Owner & Pet")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add Pet"):
    if "owner" not in st.session_state or st.session_state.owner.name != owner_name:
        st.session_state.owner = Owner(name=owner_name)
    owner = st.session_state.owner
    existing_names = owner.get_all_pets()
    if pet_name in existing_names:
        st.warning(f"{pet_name} is already added.")
    else:
        pet = Pet(name=pet_name, species=species, breed="Unknown", age=0)
        owner.add_pet(pet)
        owner.save_to_json(DATA_FILE)
        st.success(f"Added {pet_name} to {owner_name}'s pets.")

if "owner" in st.session_state and st.session_state.owner.pets:
    st.write("Pets:", st.session_state.owner.get_all_pets())

st.divider()

# --- Task Scheduling ---
st.subheader("Schedule a Task")
st.caption("Select a pet and add a task to their schedule.")

if "owner" in st.session_state and st.session_state.owner.pets:
    owner = st.session_state.owner
    pet_names = owner.get_all_pets()
    selected_pet_name = st.selectbox("Select pet", pet_names)

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
        task_time = st.time_input("Start time", value=datetime.now().replace(minute=0, second=0, microsecond=0))
    with col6:
        task_end_time = st.time_input("End time (optional)", value=datetime.now().replace(minute=0, second=0, microsecond=0))

    recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"])

    if st.button("Add Task"):
        selected_pet = next(p for p in owner.pets if p.name == selected_pet_name)
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
            selected_pet.schedule.add_task(task)
            owner.save_to_json(DATA_FILE)
            st.success(f"Added '{task_title}' to {selected_pet_name}'s schedule.")
        except ValueError as e:
            st.error(f"Could not schedule task — {e}")
else:
    st.info("Add a pet above before scheduling tasks.")

st.divider()

# --- Schedule ---
st.subheader("Schedule")

if st.button("Generate Schedule"):
    if "owner" not in st.session_state or not st.session_state.owner.pets:
        st.warning("Add an owner and at least one pet first.")
    else:
        owner = st.session_state.owner
        st.session_state.suggestions_by_pet = {
            pet.pet_id: get_schedule_suggestions(pet)
            for pet in owner.pets
        }
        st.session_state.show_schedule = True

if st.session_state.get("show_schedule") and "owner" in st.session_state:
    owner = st.session_state.owner

    for pet in owner.pets:
        pet_suggestions = st.session_state.get("suggestions_by_pet", {}).get(pet.pet_id, [])

        st.markdown("---")
        st.markdown(f"## {pet.name} ({pet.species})")

        # ---- Suggested Schedule ----
        st.markdown("### Suggested Care Schedule")
        st.caption(
            f"Based on {pet.name}'s species and age, here is a recommended routine. "
            "Expand each task to see the reasoning and edit the time or recurrence before adding it."
        )

        for i, sugg in enumerate(pet_suggestions):
            p_icon = PRIORITY_ICON.get(sugg["priority"], "")
            c_icon = CATEGORY_ICON.get(sugg["category"], "")
            recur_label = sugg["recurrence"] if sugg["recurrence"] else "one-time"
            header = f"{p_icon} {c_icon} {sugg['title']} — {sugg['suggested_time']} ({recur_label})"

            with st.expander(header, expanded=False):
                st.info(f"**Why this is recommended:** {sugg['reason']}")

                st.markdown("**Edit this recommendation:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    default_time = datetime.strptime(sugg["suggested_time"], "%I:%M %p").time()
                    edited_time = st.time_input(
                        "Time",
                        value=default_time,
                        key=f"s_time_{pet.pet_id}_{i}",
                    )
                with col2:
                    recur_opts = ["none", "daily", "weekly"]
                    default_recur_idx = recur_opts.index(sugg["recurrence"] or "none")
                    edited_recur = st.selectbox(
                        "Recurrence",
                        recur_opts,
                        index=default_recur_idx,
                        key=f"s_recur_{pet.pet_id}_{i}",
                    )
                with col3:
                    edited_date = st.date_input(
                        "Start date",
                        value=datetime.today(),
                        key=f"s_date_{pet.pet_id}_{i}",
                    )

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
                    pet.schedule.add_task(task)
                    owner.save_to_json(DATA_FILE)
                    st.success(f"Added '{sugg['title']}' to {pet.name}'s schedule!")

        if pet_suggestions:
            if st.button(f"Add All Suggestions for {pet.name}", key=f"add_all_{pet.pet_id}"):
                for i, sugg in enumerate(pet_suggestions):
                    t_val = st.session_state.get(
                        f"s_time_{pet.pet_id}_{i}",
                        datetime.strptime(sugg["suggested_time"], "%I:%M %p").time(),
                    )
                    r_val = st.session_state.get(
                        f"s_recur_{pet.pet_id}_{i}",
                        sugg["recurrence"] or "none",
                    )
                    d_val = st.session_state.get(
                        f"s_date_{pet.pet_id}_{i}",
                        datetime.today().date(),
                    )
                    due_dt = datetime.combine(d_val, t_val)
                    task = CareTask(
                        title=sugg["title"],
                        category=sugg["category"],
                        priority=sugg["priority"],
                        due_date=due_dt,
                        recurrence=None if r_val == "none" else r_val,
                        duration_minutes=sugg.get("duration_minutes", 0),
                    )
                    pet.schedule.add_task(task)
                owner.save_to_json(DATA_FILE)
                st.success(f"Added {len(pet_suggestions)} tasks to {pet.name}'s schedule!")

        # ---- Current Schedule ----
        st.markdown(f"### {pet.name}'s Current Schedule")

        conflicts = pet.schedule.get_conflicts()
        if conflicts:
            with st.expander("⚠️ Scheduling Conflicts — click to review", expanded=True):
                st.error("These tasks overlap in time. Consider rescheduling one.")
                for c in conflicts:
                    st.markdown(f"- {c}")

        all_pet_tasks = pet.schedule.sort_by_time()
        today = datetime.today().date()
        today_tasks = [t for t in all_pet_tasks if t.due_date.date() == today]
        upcoming_tasks = [t for t in all_pet_tasks if t.due_date.date() > today]
        overdue_tasks = [t for t in all_pet_tasks if t.due_date.date() < today and not t.is_completed]

        if not all_pet_tasks:
            st.info(f"No tasks scheduled for {pet.name} yet. Use the suggestions above to get started!")
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
                        st.info(f"{p_icon} **{time_str}** — {c_icon} {task.title} [{task.category}]{recur_badge}")
            else:
                st.info(f"No tasks scheduled for {pet.name} today.")

            if overdue_tasks:
                with st.expander(f"⚠️ {len(overdue_tasks)} overdue task(s)"):
                    for task in overdue_tasks:
                        st.warning(
                            f"🔴 **{task.due_date.strftime('%b %d, %I:%M %p')}** — "
                            f"{task.title} [{task.category}]"
                        )

            if upcoming_tasks:
                with st.expander(f"Upcoming ({len(upcoming_tasks)} tasks)"):
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

    # Full cross-pet summary for multi-pet owners
    if len(owner.pets) > 1:
        st.divider()
        st.markdown("### Full Schedule — All Pets")
        all_conflicts = owner.get_all_conflicts()
        if all_conflicts:
            with st.expander("⚠️ Cross-pet Conflicts", expanded=True):
                for c in all_conflicts:
                    st.markdown(f"- {c}")
        all_tasks = sorted(owner.get_all_tasks(), key=lambda t: t.due_date)
        if all_tasks:
            rows = [
                {
                    "Date": t.due_date.strftime("%b %d"),
                    "Time": t.due_date.strftime("%I:%M %p"),
                    "Pet": t.assigned_pet.name if t.assigned_pet else "—",
                    "Task": t.title,
                    "Category": t.category,
                    "Priority": t.priority,
                    "Recurs": t.recurrence or "—",
                    "Status": "✅ Done" if t.is_completed else "⏳ Pending",
                }
                for t in all_tasks
            ]
            st.table(rows)

st.divider()
st.subheader("🤖 Overdue Task Recovery Agent")
st.caption(
    "The agent reasons about your overdue backlog and proposes a realistic catch-up plan. "
    "Confirm before any changes are saved."
)

if "owner" in st.session_state and st.session_state.owner.pets:
    owner = st.session_state.owner
    all_overdue = [t for pet in owner.pets for t in pet.schedule.get_overdue_tasks()]
    all_tasks = owner.get_all_tasks()

    if not all_overdue:
        st.success("✅ No overdue tasks — your pets' schedules are up to date.")
    else:
        st.warning(f"⚠️ {len(all_overdue)} overdue task(s) detected.")
        by_pet = {}
        for t in all_overdue:
            name = t.assigned_pet.name if t.assigned_pet else "Unknown"
            by_pet[name] = by_pet.get(name, 0) + 1
        for name, count in by_pet.items():
            st.markdown(f"- **{name}**: {count} overdue task(s)")

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
                                for pet in owner.pets:
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
else:
    st.info("Add a pet and tasks above before using the recovery agent.")

st.divider()
st.subheader("🐕 Breed Care Q&A")
st.caption(
    "Ask anything about a specific breed — exercise needs, grooming schedules, health risks, diet, and more. "
    "Answers are grounded in the PawPal breed guide library, not generic AI output."
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
