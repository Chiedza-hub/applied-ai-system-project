import os
import streamlit as st
from datetime import datetime
from pawpal_system import Owner, Pet, CareTask, Schedule

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

DATA_FILE = "data.json"

if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        st.session_state.owner = Owner.load_from_json(DATA_FILE)

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
CATEGORY_ICON = {"feeding": "🍽️", "exercise": "🏃", "grooming": "✂️", "medical": "🏥"}


def get_schedule_suggestions(pet: Pet) -> list:
    """Return species- and age-aware care schedule suggestions for a pet."""
    species = pet.species.lower()
    age = pet.age
    is_young = 0 < age < 2
    name = pet.name
    suggestions = []

    # --- Feedings ---
    if is_young:
        feeding_times = ["7:00 AM", "12:00 PM", "6:00 PM"]
        feeding_reason = (
            f"{name} is under 2 years old and needs 3 meals per day to support rapid growth, "
            f"stable blood sugar, and healthy development."
        )
    else:
        feeding_times = ["7:00 AM", "6:00 PM"]
        feeding_reason = (
            f"Adult {species}s thrive on two consistent daily meals. Regular feeding times "
            f"support healthy digestion, stable energy levels, and help prevent overeating."
        )
    for t in feeding_times:
        suggestions.append({
            "title": "Feeding",
            "category": "feeding",
            "priority": "high",
            "recurrence": "daily",
            "suggested_time": t,
            "duration_minutes": 15,
            "reason": feeding_reason,
        })

    # --- Bath ---
    if species == "cat":
        bath_reason = (
            f"Cats are naturally self-grooming, but a bath every 4–6 weeks reduces shedding, "
            f"minimizes hairballs, and keeps {name}'s skin healthy — especially for indoor cats."
        )
    elif species == "dog":
        bath_reason = (
            f"Monthly baths keep {name}'s coat clean and odor-free, prevent skin irritation, "
            f"and give you a chance to check for ticks, lumps, or skin issues."
        )
    else:
        bath_reason = (
            f"Regular bathing every 4–6 weeks helps maintain {name}'s coat and skin health."
        )
    suggestions.append({
        "title": "Bath",
        "category": "grooming",
        "priority": "medium",
        "recurrence": "weekly",
        "suggested_time": "10:00 AM",
        "duration_minutes": 30,
        "reason": bath_reason,
    })

    # --- Vet Checkup ---
    if is_young:
        vet_reason = (
            f"{name} is young and needs frequent vet visits — every 3–4 weeks during the first year "
            f"for vaccinations, deworming, and growth monitoring."
        )
    else:
        vet_reason = (
            f"Biannual vet checkups allow your vet to catch health issues early, keep {name}'s "
            f"vaccinations current, and monitor age-related changes before they become serious."
        )
    suggestions.append({
        "title": "Vet Checkup",
        "category": "medical",
        "priority": "high",
        "recurrence": None,
        "suggested_time": "9:00 AM",
        "duration_minutes": 60,
        "reason": vet_reason,
    })

    # --- Nail Trim ---
    if species == "cat":
        nail_reason = (
            f"Cat nails grow quickly — trimming every 2–3 weeks prevents painful ingrown nails, "
            f"reduces scratching damage, and keeps {name} comfortable."
        )
    else:
        nail_reason = (
            f"Trimming {name}'s nails every 3–4 weeks prevents overgrowth that can cause "
            f"joint strain, affect gait, and lead to painful nail breaks."
        )
    suggestions.append({
        "title": "Nail Trim",
        "category": "grooming",
        "priority": "medium",
        "recurrence": None,
        "suggested_time": "11:00 AM",
        "duration_minutes": 20,
        "reason": nail_reason,
    })

    # --- Exercise (dogs only) ---
    if species == "dog":
        suggestions.append({
            "title": "Walk / Exercise",
            "category": "exercise",
            "priority": "high",
            "recurrence": "daily",
            "suggested_time": "8:00 AM",
            "duration_minutes": 30,
            "reason": (
                f"Dogs need daily physical activity for cardiovascular health, weight management, "
                f"and mental stimulation. A morning walk helps {name} stay calm and focused all day."
            ),
        })

    # --- Dental Care ---
    suggestions.append({
        "title": "Teeth Brushing",
        "category": "grooming",
        "priority": "low",
        "recurrence": "daily",
        "suggested_time": "8:00 PM",
        "duration_minutes": 10,
        "reason": (
            f"Brushing {name}'s teeth regularly reduces plaque buildup, prevents gum disease, "
            f"and avoids costly dental procedures — a quick daily habit with big long-term benefits."
        ),
    })

    return suggestions


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
