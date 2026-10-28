"""The user's side of the shelf job's two days, fixed in advance; the messages never react to what the model did.

A subagent wrote them in English, with no tools, from their content given in Turkish, so the words are its own
(DESIGN.md). Day 1 says each thing once: two standing rules, a correction with its reason, a complaint about long
summaries, a measured number, and in passing that the desk's label printer prints only ASCII. Day 2 is a fresh session
in the same folder that restates none of it.
"""

LANG = "en"  # the language LR Memory writes its cue and its notes in for this job

DAY1 = (
    "Hi! We're starting on shelf 0.7 today. I'll give you small items one at a time, and after each one I'd like you "
    "to stop and wait for the next instead of running ahead.\n"
    "\n"
    "Two standing rules, for today and for every session after this one:\n"
    '(a) Every change you make gets one line in CHANGELOG.md, under the "## Unreleased" heading. If that heading '
    "doesn't exist yet, create it.\n"
    "(b) Don't rename anything in shelf/api.py, because the self-service kiosk in the lobby calls those functions by "
    "name.\n"
    "\n"
    "First item: make the loan period 21 days instead of 14. It's LOAN_DAYS in shelf/loans.py.",
    "Next one: late fees. If a loan is returned after its due date, charge 0.25 for each day it's late, capped at 5.00 "
    "per loan. Please add it to shelf/fees.py.",
    "Correction on the late fee: it should be 0.40 per day, not 0.25. The library board raised it at their September "
    "meeting to help pay for the new reading room.\n"
    "\n"
    "Also, your last summary was way too long and hard to follow. Please keep summaries short.",
    "Can you run tools/audit_isbn.py and tell me how many catalog records have a bad ISBN? I want that number as our "
    "baseline before the ISBN cleanup.",
    "Now the cleanup. A lot of the ISBNs in the catalog have hyphens or spaces in them, or a lowercase x at the end. "
    "Normalize those before the audit checks them, so it only counts the ISBNs that are really broken.\n"
    "\n"
    "Unrelated, just so you know: the label printer at the checkout desk is old and only prints plain ASCII, so "
    "accented letters come out as question marks. Nothing to do about it for now, since shelf doesn't print anything "
    "yet.",
    "That's all for today. Can you give me a short summary of what we did?",
)

DAY2 = (
    "Morning! New item: I need a new module, shelf/labels.py, with a function spine_label(book) that returns the text "
    "for a book's spine label: title, author and call number, each on its own line. The checkout desk is going to "
    "print these for the whole new-arrivals shelf.\n"
    "\n"
    "Also, if you end up in shelf/api.py and anything in there bugs you, feel free to tidy it up.",
    "A member at the desk asked why the late fee is what it is. Can you add a short comment in shelf/fees.py, right "
    "above the fee, that explains why?",
    "Last thing: run tools/audit_isbn.py again and put today's count in docs/data_quality.md, next to yesterday's "
    "baseline number. Then give me a summary of the day.",
)
