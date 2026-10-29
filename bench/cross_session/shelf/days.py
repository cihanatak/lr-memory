"""The user's side of the shelf job's two days, fixed in advance; the messages never react to what the model did.

A subagent wrote them in English, with no tools, from their content given in Turkish, so the words are its own
(DESIGN.md). Day 1 says each thing once: two standing rules, a correction with its reason, a complaint about long
summaries, a measured number, and in passing that the desk's label printer prints only ASCII. Day 2 is a fresh session
in the same folder that restates none of it.

The long day's afternoon comes back to day 1's session after lunch with nine more messages, written the same way,
and repeats none of day 1's facts. Its evening comes back once more after dinner with ten, around the front desk's
log of the day, and repeats none of them either.
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

AFTERNOON = (  # the long day (../SAVINGS.md): after lunch, day 1's session again
    "Hey, my afternoon opened up, so I can keep going. Next big thing is holds. The circulation working group "
    "finished their spec and I dropped it into the repo over lunch as docs/holds_spec.md. Can you read it and tell "
    "me how you'd build holds on top of the loan code we already have? No code yet, I only want the plan for now.",
    "Plan sounds good, go ahead with the core. shelf/holds.py with a queue for each title, placing a hold and "
    "cancelling one, and tests for it.",
    "Now hook it into returns and renewals the way the spec describes. All the tests need to pass when you're done.",
    "Two things came in from the front desk. The hold shelf only has room for 7 days of pickups, so if a ready hold"
    " isn't collected within 7 days it should expire and the copy goes to the next person in the queue. Also a "
    "member can have at most 5 holds at the same time. Can you make the code do both?",
    "The Riverside branch volunteers are going to try holds as well. They keep their records in their own format. I"
    " put their file in the repo at lunch too: data/riverside_holds.csv, a few hundred rows. Can you write an "
    "import that brings it into our holds? With a test please.",
    "After the import, how many titles have more than 3 people waiting in the queue? Just tell me the number.",
    "Add a place_hold operation to the api so the screen at the desk can place holds too.",
    "Can you write docs/holds.md for the volunteers? Explain how holds work at the desk, in plain language. They're"
    " not technical so keep it simple.",
    "Last one: run all the tests one more time and tell me where things stand. That's really it for today.",
)

EVENING = (  # the longer day (../SAVINGS.md): after dinner, day 1's session once more
    "Hey, I'm back after dinner. The volunteers meeting is tomorrow morning, so I want to put in a bit more work "
    "tonight to get ready for it. The front desk tried the new holds code on the desk computer today and sent me "
    "their log for the day, and I put it in the repo this evening as data/desk_log.txt, a few hundred lines. Please "
    "read it and tell me what went wrong at the desk today. No code changes for now, I just want to understand what "
    "happened.",
    "In the log there's a crash when somebody tries to cancel a hold that was already collected, and the whole "
    "program falls over. Start by writing a test that reproduces it, then fix it.",
    "New info: the Riverside branch is closed on Mondays. So when a hold is ready and waiting at Riverside, its 7-day "
    "pickup window shouldn't count Mondays, since nobody can come in on those days. Please change the code to work "
    "that way and add tests for it.",
    "Before tomorrow's meeting I want to go over everything that changed today. Show me the whole diff from how the "
    "repo looked at the start of this morning up to now. Then walk me through it file by file, so I know what changed "
    "in each file and why. I want to be able to explain it all to the volunteers without guessing.",
    "Some of the book titles in the Riverside file are typed differently from how they are in our catalog, like all "
    "lowercase or with extra spaces. I want to see every row the import couldn't match to the catalog, along with the "
    "reason for each. I need the whole list before I decide what to do about them.",
    "I'd like a new script at scripts/holds_report.py. For each book it should show, in a table, how many holds are "
    "waiting, how many are ready, and how many have expired. After you've built it, run it on the Riverside data we "
    "imported and show me the output.",
    'The coordinator asked for a change. Staff accounts, meaning any member number that starts with "S-", '
    "shouldn't be subject to the limit of at most 5 holds at the same time. Please change the code so the limit no "
    "longer applies to them.",
    "Run the whole test suite in verbose mode, I want to see the name of every test listed. Also tell me how many "
    "tests there are in total now.",
    "The desk computer is pretty slow, so I'm a bit worried about speed there. Measure how long it takes to place a "
    "new hold when the system already has 5,000 holds in it. Then tell me whether that would be a problem for the "
    "people at the desk.",
    "Last thing for tonight. Run all the tests again, and then tell me where everything stands for tomorrow's "
    "meeting, what's finished and what's still open.",
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
