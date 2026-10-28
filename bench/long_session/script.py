"""The user's side of the long session: ten messages, fixed in advance, each sent when the previous turn has ended; they
never react to what the model did. Then the question a fresh session gets the next day."""

MESSAGES = (
    "We're shipping ledgerly 0.9 today. I'll take you through it one item at a time; please wait for me before moving "
    "to the next item.\n\n"
    "The list:\n"
    "1. Invoice totals round half-even to the cent (finance wants banker's rounding).\n"
    "2. Books get a reduced VAT rate of 8%.\n"
    "3. CSV export uses ';' as the separator and starts with a header row.\n"
    "4. Currency conversion caches rates per day, and rejects unknown currency codes with a clear error.\n"
    "5. The import log from 27 October (logs/import-2026-10-27.log) shows duplicate entries: find out why and fix it.\n"
    "6. Reports: a monthly summary grouped by account, run against the staging database.\n"
    "7. API: GET /accounts/{id}/balance.\n"
    "8. CHANGELOG entry for 0.9.\n\n"
    "Rules for this repository, for the whole session:\n"
    "- Never touch anything under migrations/: no edits and no new files. They are applied in production by the DBA.\n"
    "- One commit per item, with the message \"ledgerly 0.9: <what the item does>\".\n"
    "- New user-facing error messages are in Turkish. The old English ones get translated later; leave them.\n"
    "- No renames in ledgerly/api.py: other services import those names.\n\n"
    "Start with item 1.",
    "Thanks. Item 2 next.",
    "Correction on item 2: finance changed the books rate last week, it is 7%, not 8%. Fix that, then do item 3.",
    "Before item 4, run tools/bench.py and tell me the p50. That's our baseline for today. Then do item 4.",
    "Item 5.",
    "Item 6. The staging database for reports is ledgerly_stg_2, not the one the docs name.",
    "Product changed their mind about item 3: revert that commit and keep everything else.",
    "Item 7.",
    "Item 8. Then run tools/bench.py again and give me the p50 now against this morning's baseline.",
    "Let's wrap up. List each item with its commit hash, and tell me anything that is left undone.",
)
BASELINE = 9  # the message whose answer must carry this morning's p50
WRAP_UP = 10  # the message whose answer must name each item's commit and the revert

NEXT_SESSION = (
    "I'm picking up yesterday's ledgerly 0.9 session. Three quick questions, short answers please:\n"
    "1. What p50 from tools/bench.py did we take as the baseline, before item 4?\n"
    "2. Why did the books VAT rate end up at 7%?\n"
    "3. Which commit reverted the CSV export change? Give its hash.")
