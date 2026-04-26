from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4
import json
import os


@dataclass
class CareTask:
    title: str
    category: str
    priority: str
    assigned_pet: Pet = None
    due_date: datetime = field(default_factory=datetime.now)
    is_completed: bool = False
    notes: str = ""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    recurrence: str = None  # "daily", "weekly", or None
    duration_minutes: int = 0

    def reschedule(self, new_date: datetime):
        """Update the task's due date to new_date."""
        self.due_date = new_date

    def is_due_today(self) -> bool:
        """Return True if the task is due today."""
        return self.due_date.date() == datetime.today().date()

    def to_dict(self) -> dict:
        """Serialize the task to a dictionary."""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "category": self.category,
            "priority": self.priority,
            "due_date": self.due_date.isoformat(),
            "is_completed": self.is_completed,
            "notes": self.notes,
            "assigned_pet": self.assigned_pet.name if self.assigned_pet else None,
            "duration_minutes": self.duration_minutes,
        }


def _task_end(task: "CareTask") -> datetime:
    if task.duration_minutes and task.duration_minutes > 0:
        return task.due_date + timedelta(minutes=task.duration_minutes)
    return task.due_date


def _tasks_overlap(a: "CareTask", b: "CareTask") -> bool:
    a_start, b_start = a.due_date, b.due_date
    a_end = _task_end(a)
    b_end = _task_end(b)
    # Point-in-time tasks get a 1-second window so exact-time matches are caught
    if a_end == a_start:
        a_end = a_start + timedelta(seconds=1)
    if b_end == b_start:
        b_end = b_start + timedelta(seconds=1)
    return a_start < b_end and b_start < a_end


def _time_range_str(task: "CareTask") -> str:
    start = task.due_date.strftime("%I:%M %p")
    end = _task_end(task)
    if end == task.due_date:
        return start
    return f"{start}–{end.strftime('%I:%M %p')}"


@dataclass
class Schedule:
    pet: Pet = None
    tasks: list = field(default_factory=list)
    reminders_enabled: bool = True

    def add_task(self, task: CareTask):
        """Add a task to the schedule and assign it to this pet.
        Raises ValueError if the task overlaps an existing incomplete task.
        """
        task.assigned_pet = self.pet
        warning = self._check_conflict(task)
        if warning:
            raise ValueError(warning)
        self.tasks.append(task)

    def _check_conflict(self, new_task: CareTask) -> str:
        """Return a warning string if new_task overlaps an existing incomplete task, else empty string."""
        pet_name = self.pet.name if self.pet else "Unknown"
        conflict = next(
            (t for t in self.tasks if not t.is_completed and _tasks_overlap(t, new_task)),
            None,
        )
        if conflict:
            return (
                f"Conflict for {pet_name}: '{new_task.title}' "
                f"({_time_range_str(new_task)}) overlaps with '{conflict.title}' "
                f"({_time_range_str(conflict)})."
            )
        return ""

    def get_conflicts(self) -> list:
        """Return a list of warning strings for all time-range conflicts in this schedule."""
        pet_name = self.pet.name if self.pet else "Unknown"
        active = [t for t in self.tasks if not t.is_completed]
        warnings = []
        reported = set()
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                if _tasks_overlap(a, b):
                    key = tuple(sorted([a.task_id, b.task_id]))
                    if key not in reported:
                        reported.add(key)
                        warnings.append(
                            f"Conflict for {pet_name}: '{a.title}' ({_time_range_str(a)}) "
                            f"overlaps with '{b.title}' ({_time_range_str(b)})."
                        )
        return warnings

    def remove_task(self, task_id: str):
        """Remove a task from the schedule by its ID."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def get_upcoming_tasks(self, days: int = 7) -> list:
        """Return incomplete tasks due within the next N days."""
        cutoff = datetime.today() + timedelta(days=days)
        return [
            t for t in self.tasks
            if not t.is_completed and t.due_date <= cutoff
        ]

    def get_overdue_tasks(self) -> list:
        """Return incomplete tasks whose due date has already passed."""
        now = datetime.now()
        return [
            t for t in self.tasks
            if not t.is_completed and t.due_date < now
        ]

    def complete_task(self, task_id: str):
        """Mark a task as completed by its ID, raising ValueError if not found.
        If the task recurs daily or weekly, a new instance is scheduled automatically.
        """
        for task in self.tasks:
            if task.task_id == task_id:
                task.is_completed = True
                if task.recurrence == "daily":
                    next_due = task.due_date + timedelta(days=1)
                elif task.recurrence == "weekly":
                    next_due = task.due_date + timedelta(weeks=1)
                else:
                    return
                next_task = CareTask(
                    title=task.title,
                    category=task.category,
                    priority=task.priority,
                    due_date=next_due,
                    notes=task.notes,
                    recurrence=task.recurrence,
                    duration_minutes=task.duration_minutes,
                )
                self.add_task(next_task)
                return
        raise ValueError(f"No task with id {task_id}")

    def sort_by_time(self, reverse: bool = False) -> list:
        """Return tasks sorted by due_date. Pass reverse=True for latest-first."""
        return sorted(self.tasks, key=lambda t: t.due_date, reverse=reverse)

    def filter_by_status(self, completed: bool) -> list:
        """Return tasks matching the given completion status."""
        return [t for t in self.tasks if t.is_completed == completed]

    def filter_by_pet_name(self, name: str) -> list:
        """Return tasks assigned to a pet with the given name (case-insensitive)."""
        return [t for t in self.tasks if t.assigned_pet and t.assigned_pet.name.lower() == name.lower()]


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age: int
    pet_id: str = field(default_factory=lambda: str(uuid4()))
    medications: list = field(default_factory=list)
    schedule: Schedule = field(default=None)

    def __post_init__(self):
        """Initialize a Schedule for this pet if one was not provided."""
        if self.schedule is None:
            self.schedule = Schedule(pet=self)

    def get_active_tasks(self) -> list:
        """Return all incomplete tasks for this pet."""
        return [t for t in self.schedule.tasks if not t.is_completed]

    def get_task_history(self) -> list:
        """Return all completed tasks for this pet."""
        return [t for t in self.schedule.tasks if t.is_completed]

    def add_medication(self, med: str):
        """Add a medication to this pet's medication list."""
        self.medications.append(med)

    def remove_medication(self, med: str):
        """Remove a medication from this pet's medication list."""
        self.medications = [m for m in self.medications if m != med]


@dataclass
class Owner:
    name: str
    email: str = ""
    phone: str = ""
    pets: list = field(default_factory=list)

    def add_pet(self, pet: Pet):
        """Add a pet to this owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: str):
        """Remove a pet from this owner's list by pet ID."""
        self.pets = [p for p in self.pets if p.pet_id != pet_id]

    def get_all_pets(self) -> list:
        """Return the names of all pets owned by this owner."""
        return [p.name for p in self.pets]

    def get_all_tasks(self) -> list:
        """Return all tasks across every pet owned by this owner."""
        return [task for pet in self.pets for task in pet.schedule.tasks]

    def get_todays_schedule(self) -> list:
        """Return all tasks due today across every pet."""
        today = datetime.today().date()
        return [t for t in self.get_all_tasks() if t.due_date.date() == today]

    def get_tasks_for_pet(self, pet_id: str) -> list:
        """Return all tasks for a specific pet by pet ID, raising ValueError if not found."""
        for pet in self.pets:
            if pet.pet_id == pet_id:
                return pet.schedule.tasks
        raise ValueError(f"No pet with id {pet_id}")

    def get_pet_schedule(self, pet_id: str) -> Schedule:
        """Return the Schedule for a specific pet by pet ID, raising ValueError if not found."""
        for pet in self.pets:
            if pet.pet_id == pet_id:
                return pet.schedule
        raise ValueError(f"No pet with id {pet_id}")

    def save_to_json(self, filepath: str = "data.json"):
        """Serialize the owner, their pets, and all tasks to a JSON file."""
        data = {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "pets": [
                {
                    "name": pet.name,
                    "species": pet.species,
                    "breed": pet.breed,
                    "age": pet.age,
                    "pet_id": pet.pet_id,
                    "medications": pet.medications,
                    "tasks": [
                        {
                            "task_id": t.task_id,
                            "title": t.title,
                            "category": t.category,
                            "priority": t.priority,
                            "due_date": t.due_date.isoformat(),
                            "is_completed": t.is_completed,
                            "notes": t.notes,
                            "recurrence": t.recurrence,
                            "duration_minutes": t.duration_minutes,
                        }
                        for t in pet.schedule.tasks
                    ],
                }
                for pet in self.pets
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str = "data.json") -> Owner:
        """Load an Owner and all associated pets and tasks from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        owner = cls(name=data["name"], email=data.get("email", ""), phone=data.get("phone", ""))
        for pet_data in data.get("pets", []):
            pet = Pet(
                name=pet_data["name"],
                species=pet_data["species"],
                breed=pet_data["breed"],
                age=pet_data["age"],
                pet_id=pet_data["pet_id"],
                medications=pet_data.get("medications", []),
            )
            for t in pet_data.get("tasks", []):
                task = CareTask(
                    task_id=t["task_id"],
                    title=t["title"],
                    category=t["category"],
                    priority=t["priority"],
                    due_date=datetime.fromisoformat(t["due_date"]),
                    is_completed=t["is_completed"],
                    notes=t.get("notes", ""),
                    recurrence=t.get("recurrence"),
                    duration_minutes=t.get("duration_minutes", 0),
                )
                task.assigned_pet = pet
                pet.schedule.tasks.append(task)
            owner.add_pet(pet)
        return owner

    def get_all_conflicts(self) -> list:
        """Return warning strings for every time-range conflict across all pets."""
        warnings = []
        for pet in self.pets:
            warnings.extend(pet.schedule.get_conflicts())
        # Cross-pet conflicts: tasks from different pets whose ranges overlap
        active = [t for t in self.get_all_tasks() if not t.is_completed]
        reported = set()
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                pet_a = a.assigned_pet.name if a.assigned_pet else "Unknown"
                pet_b = b.assigned_pet.name if b.assigned_pet else "Unknown"
                if pet_a != pet_b and _tasks_overlap(a, b):
                    key = tuple(sorted([a.task_id, b.task_id]))
                    if key not in reported:
                        reported.add(key)
                        warnings.append(
                            f"Cross-pet conflict: '{a.title}' ({pet_a}, {_time_range_str(a)}) "
                            f"overlaps with '{b.title}' ({pet_b}, {_time_range_str(b)})."
                        )
        return warnings
