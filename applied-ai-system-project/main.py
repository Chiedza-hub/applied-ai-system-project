from datetime import datetime
from pawpal_system import Owner, Pet, CareTask

# Create owner
owner = Owner(name="Jordan", email="jordan@email.com", phone="555-1234")

# Create two pets
mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
luna = Pet(name="Luna", species="cat", breed="Siamese", age=5)

owner.add_pet(mochi)
owner.add_pet(luna)

# Add tasks OUT OF ORDER to demonstrate sorting
mochi.schedule.add_task(CareTask(
    title="Evening walk",
    category="exercise",
    priority="medium",
    due_date=datetime.today().replace(hour=17, minute=0, second=0, microsecond=0),
    recurrence="daily",
))

mochi.schedule.add_task(CareTask(
    title="Feed breakfast",
    category="feeding",
    priority="high",
    due_date=datetime.today().replace(hour=7, minute=30, second=0, microsecond=0),
    recurrence="daily",
))

mochi.schedule.add_task(CareTask(
    title="Morning walk",
    category="exercise",
    priority="high",
    due_date=datetime.today().replace(hour=8, minute=0, second=0, microsecond=0),
    recurrence="daily",
))

luna.schedule.add_task(CareTask(
    title="Administer flea medication",
    category="medical",
    priority="high",
    due_date=datetime.today().replace(hour=10, minute=0, second=0, microsecond=0),
    recurrence="weekly",
))

luna.schedule.add_task(CareTask(
    title="Clean litter box",
    category="grooming",
    priority="medium",
    due_date=datetime.today().replace(hour=9, minute=0, second=0, microsecond=0),
    recurrence="daily",
))

luna.schedule.add_task(CareTask(
    title="Afternoon nap check",
    category="wellness",
    priority="low",
    due_date=datetime.today().replace(hour=14, minute=0, second=0, microsecond=0),
))

# Mark recurring tasks complete — next occurrences should be auto-created
feed_task = mochi.schedule.tasks[1]  # Feed breakfast (daily)
flea_task = luna.schedule.tasks[0]   # Flea medication (weekly)
mochi.schedule.complete_task(feed_task.task_id)
luna.schedule.complete_task(flea_task.task_id)

print("=== Conflict Detection (warnings printed on add_task) ===")
# Same-pet conflict: Mochi gets a second task at 8:00 AM (same as Morning walk)
mochi.schedule.add_task(CareTask(
    title="Vet check-in call",
    category="medical",
    priority="high",
    due_date=datetime.today().replace(hour=8, minute=0, second=0, microsecond=0),
))

# Cross-pet conflict: Luna gets a task at 5:00 PM (same as Mochi's Evening walk)
luna.schedule.add_task(CareTask(
    title="Luna's dinner",
    category="feeding",
    priority="high",
    due_date=datetime.today().replace(hour=17, minute=0, second=0, microsecond=0),
))

def print_tasks(tasks, label):
    print(f"\n--- {label} ---")
    if not tasks:
        print("  (none)")
        return
    for task in tasks:
        pet_name = task.assigned_pet.name if task.assigned_pet else "Unknown"
        date_str = task.due_date.strftime("%b %d %I:%M %p")
        status = "✓" if task.is_completed else "○"
        recur = f" [{task.recurrence}]" if task.recurrence else ""
        print(f"  {status} [{date_str}] {task.title} — {pet_name} ({task.priority} priority){recur}")


# 1. Recurrence: show completed task + auto-created next occurrence
print("=== Recurrence Demo ===")
print_tasks(mochi.schedule.sort_by_time(), "Mochi — all tasks after completing 'Feed breakfast' (daily)")
print_tasks(luna.schedule.sort_by_time(), "Luna — all tasks after completing 'Flea medication' (weekly)")

# 2. Sort Mochi's tasks by time (earliest first)
print("\n=== Mochi's Schedule — Sorted by Time ===")
print_tasks(mochi.schedule.sort_by_time(), "Earliest to Latest")
print_tasks(mochi.schedule.sort_by_time(reverse=True), "Latest to Earliest")

# 3. Filter by completion status
print("\n=== Mochi's Tasks by Status ===")
print_tasks(mochi.schedule.filter_by_status(completed=False), "Pending")
print_tasks(mochi.schedule.filter_by_status(completed=True), "Completed")

# 4. Filter Luna's schedule by pet name
print("\n=== Filter Luna's Tasks by Pet Name ===")
print_tasks(luna.schedule.filter_by_pet_name("Luna"), "Assigned to Luna")
print_tasks(luna.schedule.filter_by_pet_name("Mochi"), "Assigned to Mochi (should be none)")

# 5. Full conflict scan across all pets
print("\n=== Full Conflict Scan (owner.get_all_conflicts) ===")
conflicts = owner.get_all_conflicts()
if conflicts:
    for warning in conflicts:
        print(f"  ⚠  {warning}")
else:
    print("  No conflicts found.")
