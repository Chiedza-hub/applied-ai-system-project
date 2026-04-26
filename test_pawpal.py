import pytest
from datetime import datetime, timedelta
from pawpal_system import Owner, Pet, CareTask


# --- Fixtures ---

def make_pet():
    return Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)

def make_task(title="Morning walk", priority="high", days_offset=0):
    return CareTask(
        title=title,
        category="exercise",
        priority=priority,
        due_date=datetime.now() + timedelta(days=days_offset),
    )


# --- Tests ---

def test_task_completion_changes_status():
    pet = make_pet()
    task = make_task()
    pet.schedule.add_task(task)

    assert task.is_completed is False
    pet.schedule.complete_task(task.task_id)
    assert task.is_completed is True


def test_adding_task_increases_pet_task_count():
    pet = make_pet()
    assert len(pet.schedule.tasks) == 0

    pet.schedule.add_task(make_task("Feed breakfast", days_offset=0))
    pet.schedule.add_task(make_task("Evening walk", days_offset=1))

    assert len(pet.schedule.tasks) == 2


def test_overdue_tasks_returned_correctly():
    pet = make_pet()
    overdue_task = make_task("Vet visit", days_offset=-2)
    future_task = make_task("Grooming", days_offset=3)

    pet.schedule.add_task(overdue_task)
    pet.schedule.add_task(future_task)

    overdue = pet.schedule.get_overdue_tasks()
    assert len(overdue) == 1
    assert overdue[0].title == "Vet visit"


def test_owner_get_all_pets_returns_names():
    owner = Owner(name="Jordan")
    owner.add_pet(Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3))
    owner.add_pet(Pet(name="Luna", species="cat", breed="Siamese", age=5))

    names = owner.get_all_pets()
    assert names == ["Mochi", "Luna"]


def test_remove_pet_decreases_owner_pet_count():
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
    owner.add_pet(pet)

    assert len(owner.pets) == 1
    owner.remove_pet(pet.pet_id)
    assert len(owner.pets) == 0


# --- Sorting Tests ---

def test_sort_by_time_returns_chronological_order():
    pet = make_pet()
    t1 = CareTask(title="Morning walk", category="exercise", priority="high",
                  due_date=datetime.now() + timedelta(hours=8))
    t2 = CareTask(title="Lunch feeding", category="feeding", priority="medium",
                  due_date=datetime.now() + timedelta(hours=12))
    t3 = CareTask(title="Evening walk", category="exercise", priority="high",
                  due_date=datetime.now() + timedelta(hours=18))

    # Add out of order
    pet.schedule.add_task(t3)
    pet.schedule.add_task(t1)
    pet.schedule.add_task(t2)

    sorted_tasks = pet.schedule.sort_by_time()
    assert [t.title for t in sorted_tasks] == ["Morning walk", "Lunch feeding", "Evening walk"]


def test_sort_by_time_reverse_returns_latest_first():
    pet = make_pet()
    t1 = CareTask(title="Morning walk", category="exercise", priority="high",
                  due_date=datetime.now() + timedelta(hours=8))
    t2 = CareTask(title="Evening walk", category="exercise", priority="high",
                  due_date=datetime.now() + timedelta(hours=18))

    pet.schedule.add_task(t1)
    pet.schedule.add_task(t2)

    sorted_tasks = pet.schedule.sort_by_time(reverse=True)
    assert sorted_tasks[0].title == "Evening walk"
    assert sorted_tasks[1].title == "Morning walk"


def test_sort_by_time_does_not_mutate_original_list():
    pet = make_pet()
    t1 = CareTask(title="First added", category="exercise", priority="low",
                  due_date=datetime.now() + timedelta(hours=18))
    t2 = CareTask(title="Second added", category="feeding", priority="low",
                  due_date=datetime.now() + timedelta(hours=6))

    pet.schedule.add_task(t1)
    pet.schedule.add_task(t2)

    original_order = [t.title for t in pet.schedule.tasks]
    pet.schedule.sort_by_time()

    assert [t.title for t in pet.schedule.tasks] == original_order


def test_sort_empty_schedule_returns_empty_list():
    pet = make_pet()
    assert pet.schedule.sort_by_time() == []


# --- Recurrence Tests ---

def test_completing_daily_task_creates_next_day_task():
    pet = make_pet()
    due = datetime.now()
    task = CareTask(title="Feed breakfast", category="feeding", priority="high",
                    due_date=due, recurrence="daily")
    pet.schedule.add_task(task)

    task_count_before = len(pet.schedule.tasks)
    pet.schedule.complete_task(task.task_id)

    assert task.is_completed is True
    assert len(pet.schedule.tasks) == task_count_before + 1

    new_task = pet.schedule.tasks[-1]
    assert new_task.due_date.date() == (due + timedelta(days=1)).date()


def test_completing_daily_task_inherits_fields():
    pet = make_pet()
    task = CareTask(title="Feed breakfast", category="feeding", priority="high",
                    due_date=datetime.now(), recurrence="daily", notes="Use dry food")
    pet.schedule.add_task(task)
    pet.schedule.complete_task(task.task_id)

    new_task = pet.schedule.tasks[-1]
    assert new_task.title == task.title
    assert new_task.category == task.category
    assert new_task.priority == task.priority
    assert new_task.notes == task.notes
    assert new_task.recurrence == "daily"
    assert new_task.task_id != task.task_id  # fresh ID


def test_completing_non_recurring_task_creates_no_new_task():
    pet = make_pet()
    task = CareTask(title="One-time vet visit", category="medical", priority="high",
                    due_date=datetime.now(), recurrence=None)
    pet.schedule.add_task(task)

    pet.schedule.complete_task(task.task_id)

    assert task.is_completed is True
    assert len(pet.schedule.tasks) == 1  # no new task added


# --- Conflict Detection Tests ---

def test_same_time_tasks_for_same_pet_trigger_conflict():
    pet = make_pet()
    same_time = datetime(2026, 4, 1, 9, 0, 0)
    t1 = CareTask(title="Bath", category="grooming", priority="medium", due_date=same_time)
    t2 = CareTask(title="Feed", category="feeding", priority="high", due_date=same_time)

    pet.schedule.add_task(t1)
    with pytest.raises(ValueError, match="Feed"):
        pet.schedule.add_task(t2)
    assert len(pet.schedule.tasks) == 1


def test_different_time_tasks_have_no_conflict():
    pet = make_pet()
    t1 = CareTask(title="Bath", category="grooming", priority="medium",
                  due_date=datetime(2026, 4, 1, 9, 0, 0))
    t2 = CareTask(title="Feed", category="feeding", priority="high",
                  due_date=datetime(2026, 4, 1, 10, 0, 0))

    pet.schedule.add_task(t1)
    pet.schedule.add_task(t2)

    assert pet.schedule.get_conflicts() == []


def test_no_conflicts_on_empty_schedule():
    pet = make_pet()
    assert pet.schedule.get_conflicts() == []


# --- Time Range Conflict Tests ---

def test_overlapping_ranges_trigger_conflict():
    """9:00–10:00 vs 9:15–10:00 should be blocked (the 9:15 task starts inside the first window)."""
    pet = make_pet()
    t1 = CareTask(title="Vet visit", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=60)
    t2 = CareTask(title="Morning walk", category="exercise", priority="medium",
                  due_date=datetime(2026, 4, 1, 9, 15), duration_minutes=45)

    pet.schedule.add_task(t1)
    with pytest.raises(ValueError) as exc:
        pet.schedule.add_task(t2)
    assert "Vet visit" in str(exc.value)
    assert "Morning walk" in str(exc.value)
    assert len(pet.schedule.tasks) == 1


def test_back_to_back_ranges_no_conflict():
    """9:00–10:00 ending exactly when 10:00–11:00 starts should NOT conflict."""
    pet = make_pet()
    t1 = CareTask(title="Vet visit", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=60)
    t2 = CareTask(title="Grooming", category="grooming", priority="low",
                  due_date=datetime(2026, 4, 1, 10, 0), duration_minutes=60)

    pet.schedule.add_task(t1)
    pet.schedule.add_task(t2)

    assert pet.schedule.get_conflicts() == []


def test_non_overlapping_ranges_no_conflict():
    """9:00–9:30 and 10:00–10:30 with a gap should NOT conflict."""
    pet = make_pet()
    t1 = CareTask(title="Feed breakfast", category="feeding", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=30)
    t2 = CareTask(title="Evening walk", category="exercise", priority="medium",
                  due_date=datetime(2026, 4, 1, 10, 0), duration_minutes=30)

    pet.schedule.add_task(t1)
    pet.schedule.add_task(t2)

    assert pet.schedule.get_conflicts() == []


def test_contained_range_triggers_conflict():
    """A task fully inside another's window (9:30–10:00 within 9:00–11:00) should be blocked."""
    pet = make_pet()
    t1 = CareTask(title="Long vet appointment", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=120)
    t2 = CareTask(title="Pill time", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 30), duration_minutes=30)

    pet.schedule.add_task(t1)
    with pytest.raises(ValueError, match="Pill time"):
        pet.schedule.add_task(t2)
    assert len(pet.schedule.tasks) == 1


def test_ranged_task_overlaps_point_in_time():
    """A point-in-time task at 9:30 should be blocked by an existing 9:00–10:00 ranged task."""
    pet = make_pet()
    t1 = CareTask(title="Vet visit", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=60)
    t2 = CareTask(title="Pill time", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 30), duration_minutes=0)

    pet.schedule.add_task(t1)
    with pytest.raises(ValueError, match="Pill time"):
        pet.schedule.add_task(t2)
    assert len(pet.schedule.tasks) == 1


def test_ranged_task_no_overlap_with_later_point_in_time():
    """A point-in-time task at 10:30 should NOT conflict with a 9:00–10:00 ranged task."""
    pet = make_pet()
    t1 = CareTask(title="Vet visit", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=60)
    t2 = CareTask(title="Afternoon pill", category="medical", priority="high",
                  due_date=datetime(2026, 4, 1, 10, 30), duration_minutes=0)

    pet.schedule.add_task(t1)
    pet.schedule.add_task(t2)

    assert pet.schedule.get_conflicts() == []


def test_cross_pet_range_overlap_triggers_conflict():
    """Overlapping ranged tasks across two pets should appear in owner.get_all_conflicts()."""
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
    luna = Pet(name="Luna", species="cat", breed="Siamese", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    t1 = CareTask(title="Mochi walk", category="exercise", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=60)
    t2 = CareTask(title="Luna grooming", category="grooming", priority="medium",
                  due_date=datetime(2026, 4, 1, 9, 30), duration_minutes=30)

    mochi.schedule.add_task(t1)
    luna.schedule.add_task(t2)

    conflicts = owner.get_all_conflicts()
    assert any("Mochi walk" in c and "Luna grooming" in c for c in conflicts)


def test_cross_pet_non_overlapping_ranges_no_conflict():
    """Non-overlapping ranged tasks across two pets should produce no cross-pet conflict."""
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
    luna = Pet(name="Luna", species="cat", breed="Siamese", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    t1 = CareTask(title="Mochi walk", category="exercise", priority="high",
                  due_date=datetime(2026, 4, 1, 9, 0), duration_minutes=60)
    t2 = CareTask(title="Luna grooming", category="grooming", priority="medium",
                  due_date=datetime(2026, 4, 1, 10, 0), duration_minutes=30)

    mochi.schedule.add_task(t1)
    luna.schedule.add_task(t2)

    assert owner.get_all_conflicts() == []


def test_recurring_task_inherits_duration_minutes():
    """Completing a recurring ranged task should create a copy with the same duration."""
    pet = make_pet()
    task = CareTask(title="Daily walk", category="exercise", priority="high",
                    due_date=datetime(2026, 4, 1, 9, 0), recurrence="daily",
                    duration_minutes=45)
    pet.schedule.add_task(task)
    pet.schedule.complete_task(task.task_id)

    new_task = pet.schedule.tasks[-1]
    assert new_task.duration_minutes == 45
    assert new_task.recurrence == "daily"
