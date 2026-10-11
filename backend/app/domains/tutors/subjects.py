"""The subjects tutors can offer and parents can post jobs for. Only these are accepted, so a subject name is
never free text: it goes into Claude's prompt when exam questions are written (spec 4 R5.2), where free text
could carry instructions ("…make every answer A"). The frontend has the same list in `lib/format.ts`
(`tests/test_subjects.py` checks they match)."""

NIGERIAN = (
    "Mathematics", "English Language", "Basic Science", "Basic Technology", "Social Studies",
    "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "Economics",
    "Literature in English", "Government", "Geography", "Agricultural Science", "Computer Studies",
    "Commerce", "Accounting", "French", "Yoruba", "Igbo", "Hausa", "Christian Religious Studies",
    "Islamic Religious Studies", "Verbal Reasoning", "Quantitative Reasoning",
)

INTERNATIONAL = (
    "Additional Mathematics", "Statistics", "Combined Science", "Computer Science", "Business Studies",
    "History", "Global Perspectives", "Environmental Management", "Psychology", "Sociology",
    "English as a Second Language", "Spanish", "German", "Mandarin Chinese", "Art and Design",
    "Design and Technology", "Music", "Physical Education", "IB Theory of Knowledge",
    "AP Calculus", "SAT", "ACT", "IELTS", "TOEFL",
)

SUBJECTS = NIGERIAN + INTERNATIONAL

_BY_KEY = {" ".join(s.lower().split()): s for s in SUBJECTS}


def canonical(name: str) -> str | None:
    """The listed spelling of `name`, ignoring capitals and extra spaces; None if it isn't listed."""
    return _BY_KEY.get(" ".join(name.lower().split()))


def listed(subjects: list[str]) -> list[str]:
    """Each subject once, in its listed spelling. Raises ValueError (a 422) naming the first one that isn't
    listed."""
    result = []
    for name in subjects:
        found = canonical(name)
        if found is None:
            raise ValueError(f"\"{name.strip()}\" isn't one of TutorLink's subjects. Choose one from the list.")
        if found not in result:
            result.append(found)
    return result
