# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

I have 4 classes namely: Owner, Pet, Schedule and CareTask. 
Owner — represents the person using the app. The owner has lists of pets and manages tasks and schedules

Pet — represents an individual pet. Responsible for storing pet details (name, species, breed, age) 

CareTask — represents a single care task (e.g. feeding, grooming). Responsible for storing task details like category, priority, and due date, and checking if it's due today.

Schedule — represents a pet's care plan. Responsible for holding a collection of CareTasks and managing them — adding, removing, completing, and filtering by upcoming or overdue.


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Owner.get_tasks_for_pet() and Owner.get_pet_schedule() both search by pet_name string so if two pets have the same name, both methods return ambiguous results. I added a pet id. 
There was no way to create a Pet with a Schedule already initialized so the Schedule has to be attached after construction, which is easy to forget.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

Time — the primary constraint. Every CareTask has a due_date, conflict detection is purely time-based, and sort_by_time() organizes the whole schedule around it.
Completion status — tasks are either pending or done. The scheduler skips completed tasks in conflict checks, upcoming/overdue queries, and filters.
Time was chosen first because it's the only constraint that's objective — two things either happen at the same time or they don't. Priority and duration require judgment calls (how long is a walk? what overrides what?) that would need product decisions before they could be enforced.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

Completed tasks are never removed, they are only flagged 
is_completed = True keeps tasks in the list forever. This keeps history but means every filter and conflict scan has to skip completed tasks explicitly. 
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

Design brainstorming — I used AI to help think through the class structure (Owner, Pet, CareTask, Schedule) and how responsibilities should be divided. Prompts like "what classes would make sense for a pet care scheduling app?" helped surface the right abstractions early.

Debugging — When logic issues came up (e.g., conflict detection not working as expected, or sort_by_time() returning unexpected order), I described the behavior and asked AI to spot the issue.

Refactoring / code review — I asked AI to review methods like get_conflicts() or the Streamlit UI loop and suggest cleaner ways to structure them.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

When AI helped draft get_tasks_for_pet() and get_pet_schedule(), both methods originally looked up pets by name (a string). I accepted that initially, but when I traced through the logic myself I realized: if an owner has two pets both named "Max", both methods return ambiguous results — they'd silently match the first one found rather than the correct pet.
I pushed back and asked AI to revise the design to use a unique identifier. That's why Pet now has a pet_id field 
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

Owner pet management — get_all_pets() returns correct names; remove_pet() decreases pet count

Sorting — sort_by_time() returns chronological order even when tasks were added out of order; reverse order works; original list is not mutated; empty schedule returns empty list

Recurrence — completing a daily task automatically creates the next occurrence with the same fields but a new task_id; completing a non-recurring task creates no new task

Conflict detection — two tasks at the same time trigger a conflict; tasks at different times don't; empty schedule has no conflicts

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

3 / 5 

The core scheduling behaviors — task completion, recurrence, sorting, and same-pet conflict detection are well covered and all 15 tests pass. 

However, the following edge cases need to be implemented if time allowed:

Conflict detection only catches exact timestamp matches — if "Morning walk" is at 9:00 and "Vet visit" is at 9:01, no conflict fires. A real scheduler should flag tasks within some time window of each other (e.g. 30 minutes).

Cross-pet conflict with 3+ pets at the same time — get_all_conflicts() uses a seen dict that overwrites after the first pair, so a third pet's task at the same time would be silently missed.
---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I loved woring with AI and being the head architect. 
Asking it to implement changes and help in debugging saves so much time. 

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

The instructions were clear and easy to walk through. However, the handout is tailored for Copilot, not Claude which caused a bit of confusion when looking for some tools. 

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

There are so many edge cases to think about and each algorithm has its tradeoff. Its also tempting to be mindless when working with AI but some changes it makes are insane. 
