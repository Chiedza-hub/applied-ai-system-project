import os
import streamlit as st
from datetime import datetime
from pawpal_system import Owner, Pet, CareTask, Schedule

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

DATA_FILE = "data.json"

# Load persisted data on first run
if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        st.session_state.owner = Owner.load_from_json(DATA_FILE)

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
        selected_pet.schedule.add_task(task)
        owner.save_to_json(DATA_FILE)

        # Check for conflicts immediately after adding
        conflicts = selected_pet.schedule.get_conflicts()
        relevant = [c for c in conflicts if task_title in c]
        if relevant:
            st.warning(
                f"Task added, but a **scheduling conflict** was detected for {selected_pet_name}:\n\n"
                + "\n".join(f"- {c}" for c in relevant)
                + "\n\nConsider changing the due time for one of the conflicting tasks."
            )
        else:
            st.success(f"Added '{task_title}' to {selected_pet_name}'s schedule.")
else:
    st.info("Add a pet above before scheduling tasks.")

st.divider()

# --- Today's Schedule ---
st.subheader("Today's Schedule")

if st.button("Generate Schedule"):
    if "owner" not in st.session_state or not st.session_state.owner.pets:
        st.warning("Add an owner and at least one pet first.")
    else:
        owner = st.session_state.owner

        # --- Conflict banner ---
        all_conflicts = owner.get_all_conflicts()
        if all_conflicts:
            with st.expander("⚠️ Scheduling Conflicts Detected — click to review", expanded=True):
                st.error(
                    "The following tasks overlap in time. Only one task can happen at a time — "
                    "please reschedule one of the conflicting tasks."
                )
                for conflict in all_conflicts:
                    st.markdown(f"- {conflict}")

        # --- Per-pet sorted schedule ---
        for pet in owner.pets:
            sorted_tasks = pet.schedule.sort_by_time()
            todays = [t for t in sorted_tasks if t.due_date.date() == datetime.today().date()]

            st.markdown(f"### {pet.name}")

            if not todays:
                st.info(f"No tasks scheduled for {pet.name} today.")
                continue

            for task in todays:
                time_str = task.due_date.strftime("%I:%M %p")
                recur_badge = f" _(repeats {task.recurrence})_" if task.recurrence else ""
                priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "")

                if task.is_completed:
                    st.success(f"✅ **{time_str}** — {task.title} [{task.category}]{recur_badge}")
                else:
                    st.info(f"{priority_color} **{time_str}** — {task.title} [{task.category}]{recur_badge}")

        # --- Summary table across all pets ---
        all_tasks = owner.get_todays_schedule()
        if all_tasks:
            st.divider()
            st.markdown("#### Full Schedule (sorted by time)")
            sorted_all = sorted(all_tasks, key=lambda t: t.due_date)
            rows = [
                {
                    "Time": t.due_date.strftime("%I:%M %p"),
                    "Pet": t.assigned_pet.name if t.assigned_pet else "—",
                    "Task": t.title,
                    "Category": t.category,
                    "Priority": t.priority,
                    "Recurs": t.recurrence or "—",
                    "Status": "✅ Done" if t.is_completed else "⏳ Pending",
                }
                for t in sorted_all
            ]
            st.table(rows)
