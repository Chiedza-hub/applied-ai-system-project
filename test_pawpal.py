import pytest
from datetime import datetime, timedelta
from pawpal_system import Owner, Pet, CareTask, get_schedule_suggestions


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


# --- Schedule Suggestion Tests ---

VALID_PRIORITIES = {"high", "medium", "low"}
VALID_CATEGORIES = {"feeding", "exercise", "grooming", "medical"}
REQUIRED_KEYS = {"title", "category", "priority", "recurrence", "suggested_time", "duration_minutes", "reason"}


def make_dog(age=3):
    return Pet(name="Rex", species="dog", breed="Labrador", age=age)

def make_cat(age=4):
    return Pet(name="Luna", species="cat", breed="Siamese", age=age)

def make_other(age=2):
    return Pet(name="Pip", species="other", breed="Unknown", age=age)


def test_suggestions_have_required_fields():
    """Every suggestion dict must contain all required keys."""
    for pet in [make_dog(), make_cat(), make_other()]:
        for sugg in get_schedule_suggestions(pet):
            assert REQUIRED_KEYS.issubset(sugg.keys()), (
                f"Missing keys in suggestion '{sugg.get('title')}': "
                f"{REQUIRED_KEYS - sugg.keys()}"
            )


def test_suggestions_have_valid_priorities():
    for pet in [make_dog(), make_cat(), make_other()]:
        for sugg in get_schedule_suggestions(pet):
            assert sugg["priority"] in VALID_PRIORITIES


def test_suggestions_have_valid_categories():
    for pet in [make_dog(), make_cat(), make_other()]:
        for sugg in get_schedule_suggestions(pet):
            assert sugg["category"] in VALID_CATEGORIES


def test_adult_dog_gets_two_feedings():
    suggs = get_schedule_suggestions(make_dog(age=3))
    feedings = [s for s in suggs if s["title"] == "Feeding"]
    assert len(feedings) == 2


def test_young_pet_gets_three_feedings():
    """Pets under 2 years old should get 3 daily feedings."""
    suggs = get_schedule_suggestions(make_dog(age=1))
    feedings = [s for s in suggs if s["title"] == "Feeding"]
    assert len(feedings) == 3


def test_age_zero_treated_as_adult_gets_two_feedings():
    """Age=0 (unknown) should not trigger the young-pet path — default to adult schedule."""
    suggs = get_schedule_suggestions(make_dog(age=0))
    feedings = [s for s in suggs if s["title"] == "Feeding"]
    assert len(feedings) == 2


def test_dog_suggestions_include_exercise():
    titles = [s["title"] for s in get_schedule_suggestions(make_dog())]
    assert "Walk / Exercise" in titles


def test_cat_suggestions_exclude_exercise():
    titles = [s["title"] for s in get_schedule_suggestions(make_cat())]
    assert "Walk / Exercise" not in titles


def test_other_species_suggestions_exclude_exercise():
    titles = [s["title"] for s in get_schedule_suggestions(make_other())]
    assert "Walk / Exercise" not in titles


def test_vet_checkup_always_included():
    for pet in [make_dog(), make_cat(), make_other()]:
        titles = [s["title"] for s in get_schedule_suggestions(pet)]
        assert "Vet Checkup" in titles, f"Vet Checkup missing for {pet.species}"


def test_bath_always_included():
    for pet in [make_dog(), make_cat(), make_other()]:
        titles = [s["title"] for s in get_schedule_suggestions(pet)]
        assert "Bath" in titles


def test_teeth_brushing_always_included():
    for pet in [make_dog(), make_cat(), make_other()]:
        titles = [s["title"] for s in get_schedule_suggestions(pet)]
        assert "Teeth Brushing" in titles


def test_young_pet_vet_reason_mentions_age():
    """Young-pet vet reason should communicate urgency of frequent visits."""
    suggs = get_schedule_suggestions(make_dog(age=1))
    vet = next(s for s in suggs if s["title"] == "Vet Checkup")
    reason_lower = vet["reason"].lower()
    assert "young" in reason_lower or "first year" in reason_lower


def test_adult_pet_vet_reason_mentions_biannual():
    suggs = get_schedule_suggestions(make_dog(age=3))
    vet = next(s for s in suggs if s["title"] == "Vet Checkup")
    assert "biannual" in vet["reason"].lower()


def test_cat_bath_reason_differs_from_dog_bath_reason():
    cat_bath = next(s for s in get_schedule_suggestions(make_cat()) if s["title"] == "Bath")
    dog_bath = next(s for s in get_schedule_suggestions(make_dog()) if s["title"] == "Bath")
    assert cat_bath["reason"] != dog_bath["reason"]


def test_all_feedings_are_daily_recurring():
    for pet in [make_dog(), make_cat()]:
        for sugg in get_schedule_suggestions(pet):
            if sugg["title"] == "Feeding":
                assert sugg["recurrence"] == "daily"


def test_suggestion_reason_references_pet_name():
    """Reasons should be personalised with the pet's name."""
    pet = Pet(name="Biscuit", species="dog", breed="Beagle", age=2)
    for sugg in get_schedule_suggestions(pet):
        assert "Biscuit" in sugg["reason"], (
            f"Reason for '{sugg['title']}' does not mention the pet's name"
        )
