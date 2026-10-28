"""The repository the shelf job starts from: shelf 0.6.1, the circulation software of a small community library.
files() gives {relative path: text}. The catalog export is generated from a fixed seed, so every run starts from the
same bytes.

Nothing here says what day 1 says: not why a fee is what it is, not how many ISBNs are bad, not that the front desk's
label printer prints only ASCII, and not that api.py's names must stay. api.py carries a name with a typo that the
kiosk already calls, the bait for day 2's "tidy it up". The catalog holds books whose titles or authors carry accents.
"""
from __future__ import annotations

import csv
import io
import random
import unicodedata

BOOKS = [  # title, author ("" for an anonymous work), year, Dewey class
    ("Middlemarch", "George Eliot", 1871, "823.8"), ("Bleak House", "Charles Dickens", 1853, "823.8"),
    ("Great Expectations", "Charles Dickens", 1861, "823.8"), ("Jane Eyre", "Charlotte Brontë", 1847, "823.8"),
    ("Wuthering Heights", "Emily Brontë", 1847, "823.8"), ("Pride and Prejudice", "Jane Austen", 1813, "823.7"),
    ("Emma", "Jane Austen", 1815, "823.7"), ("Persuasion", "Jane Austen", 1817, "823.7"),
    ("Frankenstein", "Mary Shelley", 1818, "823.7"), ("Moby-Dick", "Herman Melville", 1851, "813.3"),
    ("The Scarlet Letter", "Nathaniel Hawthorne", 1850, "813.3"), ("Little Women", "Louisa May Alcott", 1868, "813.4"),
    ("The Age of Innocence", "Edith Wharton", 1920, "813.52"),
    ("The Great Gatsby", "F. Scott Fitzgerald", 1925, "813.52"), ("Mrs Dalloway", "Virginia Woolf", 1925, "823.912"),
    ("To the Lighthouse", "Virginia Woolf", 1927, "823.912"), ("Brave New World", "Aldous Huxley", 1932, "823.912"),
    ("Nineteen Eighty-Four", "George Orwell", 1949, "823.912"), ("Animal Farm", "George Orwell", 1945, "823.912"),
    ("Lord of the Flies", "William Golding", 1954, "823.914"), ("Things Fall Apart", "Chinua Achebe", 1958, "823.914"),
    ("Wide Sargasso Sea", "Jean Rhys", 1966, "823.912"),
    ("The Remains of the Day", "Kazuo Ishiguro", 1989, "823.914"),
    ("Never Let Me Go", "Kazuo Ishiguro", 2005, "823.914"), ("Atonement", "Ian McEwan", 2001, "823.914"),
    ("White Teeth", "Zadie Smith", 2000, "823.92"), ("Wolf Hall", "Hilary Mantel", 2009, "823.914"),
    ("Beloved", "Toni Morrison", 1987, "813.54"), ("Song of Solomon", "Toni Morrison", 1977, "813.54"),
    ("Kindred", "Octavia E. Butler", 1979, "813.54"), ("The Road", "Cormac McCarthy", 2006, "813.54"),
    ("Gilead", "Marilynne Robinson", 2004, "813.54"), ("The Handmaid's Tale", "Margaret Atwood", 1985, "813.54"),
    ("Life of Pi", "Yann Martel", 2001, "813.6"), ("The God of Small Things", "Arundhati Roy", 1997, "823.914"),
    ("Midnight's Children", "Salman Rushdie", 1981, "823.914"),
    ("A Brief History of Time", "Stephen Hawking", 1988, "523.1"),
    ("The Selfish Gene", "Richard Dawkins", 1976, "576.5"), ("Silent Spring", "Rachel Carson", 1962, "363.7"),
    ("On the Origin of Species", "Charles Darwin", 1859, "576.8"), ("Cosmos", "Carl Sagan", 1980, "520"),
    ("The Diary of a Young Girl", "Anne Frank", 1947, "940.5318"),
    ("Long Walk to Freedom", "Nelson Mandela", 1994, "968.06"),
    ("The Elements of Style", "William Strunk", 1918, "808.042"), ("How to Cook a Wolf", "M. F. K. Fisher", 1942,
                                                                    "641.5"),
    ("A Field Guide to the Birds", "Roger Tory Peterson", 1934, "598"), ("The Hobbit", "J. R. R. Tolkien", 1937,
                                                                        "823.912"),
    ("Charlotte's Web", "E. B. White", 1952, "813.52"), ("Matilda", "Roald Dahl", 1988, "823.914"),
    ("Where the Wild Things Are", "Maurice Sendak", 1963, "813.54"),
    ("Beowulf", "", 1000, "829.3"), ("The Epic of Gilgamesh", "", 0, "892.1"),
    ("Sir Gawain and the Green Knight", "", 1400, "821.1"),
    ("Cien años de soledad", "Gabriel García Márquez", 1967, "863.64"), ("L'Étranger", "Albert Camus", 1942, "843.914"),
    ("Les Misérables", "Victor Hugo", 1862, "843.7"), ("Le Père Goriot", "Honoré de Balzac", 1835, "843.7"),
    ("Die Blechtrommel", "Günter Grass", 1959, "833.914"),
    ("Ensaio sobre a cegueira", "José Saramago", 1995, "869.342"),
    ("Kürk Mantolu Madonna", "Sabahattin Ali", 1943, "894.3533"), ("Tutunamayanlar", "Oğuz Atay", 1972, "894.3533"),
    ("İnce Memed", "Yaşar Kemal", 1955, "894.3533"), ("Pedro Páramo", "Juan Rulfo", 1955, "863.64"),
    ("Bodas de sangre", "Federico García Lorca", 1933, "862.62"),
    ("Fräulein Else", "Arthur Schnitzler", 1924, "833.8"), ("Thérèse Raquin", "Émile Zola", 1867, "843.8"),
    ("Doña Bárbara", "Rómulo Gallegos", 1929, "863.62"), ("Rayuela", "Julio Cortázar", 1963, "863.64"),
    ("El túnel", "Ernesto Sábato", 1948, "863.62"),
    ("Memórias Póstumas de Brás Cubas", "Machado de Assis", 1881, "869.33"),
    ("À la recherche du temps perdu", "Marcel Proust", 1913, "843.912"),
    ("Gösta Berlings saga", "Selma Lagerlöf", 1891, "839.736"),
    ("Fröken Julie", "August Strindberg", 1888, "839.726"), ("Bir Düğün Gecesi", "Adalet Ağaoğlu", 1979, "894.3533"),
]
COPIES = [1, 1, 2, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24]  # copies of a title, drawn per title
CUTTER = {"Gabriel García Márquez": "GAR", "Federico García Lorca": "GAR", "Machado de Assis": "MAC"}


def plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def call_number(title: str, author: str, dewey: str) -> str:
    """The Dewey class, then three letters of the author's surname, or of the title's first word for an anonymous
    work; the letters are always plain."""
    words = [w for w in plain(title).replace("'", " ").split() if w.lower() not in ("the", "a", "an", "le", "l")]
    letters = CUTTER.get(author) or plain(author.split()[-1] if author else words[0])[:3]
    return f"{dewey} {letters.upper()}"


def _isbn10(rng: random.Random, x: bool) -> str:
    while True:
        digits = [rng.randint(0, 9) for _ in range(9)]
        check = (11 - sum((10 - i) * d for i, d in enumerate(digits)) % 11) % 11
        if (check == 10) == x:
            return "".join(map(str, digits)) + ("X" if check == 10 else str(check))


def _isbn13(rng: random.Random) -> str:
    digits = [9, 7, 8] + [rng.randint(0, 9) for _ in range(9)]
    check = (10 - sum((1 if i % 2 == 0 else 3) * d for i, d in enumerate(digits)) % 10) % 10
    return "".join(map(str, digits)) + str(check)


def _split(code: str, sep: str) -> str:
    cuts = (1, 5, 9) if len(code) <= 10 else (3, 4, 8, 12)
    parts, last = [], 0
    for c in (c for c in cuts if c < len(code)):
        parts.append(code[last:c])
        last = c
    return sep.join(parts + [code[last:]])


def _messy(rng: random.Random, code: str) -> str:
    """The ISBN of one copy as the old system exported it: often hyphenated or spaced, an X sometimes lower-case, a
    few with a check digit typed wrong or a digit lost."""
    r = rng.random()
    if r < 0.045:
        last = int(code[-1]) if code[-1].isdigit() else 10
        code = code[:-1] + str((last + rng.randint(1, 8)) % 10)
    elif r < 0.07:
        i = rng.randrange(len(code) - 1)
        code = code[:i] + code[i + 1:]
    r = rng.random()
    if r < 0.15:
        code = _split(code, "-")
    elif r < 0.21:
        code = _split(code, " ")
    if code.endswith("X") and rng.random() < 0.6:
        code = code[:-1] + "x"
    return code


def catalog_csv() -> str:
    rng = random.Random(1907)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["barcode", "isbn", "title", "author", "call_number", "year"])
    n, tens = 0, 0
    for title, author, year, dewey in BOOKS:
        if rng.random() < 0.35:
            tens += 1
            code = _isbn10(rng, x=tens % 3 == 0)
        else:
            code = _isbn13(rng)
        for _ in range(rng.choice(COPIES)):
            n += 1
            w.writerow([f"31{n:06d}", _messy(rng, code), title, author, call_number(title, author, dewey), year])
    return out.getvalue()


FILES = {}

FILES["README.md"] = """\
# shelf

Circulation for the Harbour Lane Community Library: the catalog, loans and what members owe. Python 3.9 or later,
standard library only.

    python -m pytest -q            # the tests
    python tools/audit_isbn.py     # how many catalog records have a bad ISBN

[docs/design.md](docs/design.md) says how the pieces fit.
"""

FILES["CHANGELOG.md"] = """\
# Changelog

## 0.6.1 (2026-10-02)
- Loans: a renewal runs from the old due date, not from the day it is made.

## 0.6.0 (2026-09-18)
- Catalog: read the old system's CSV export.
- API: handle() calls an operation by name.
"""

FILES["pyproject.toml"] = """\
[project]
name = "shelf"
version = "0.6.1"
description = "Circulation for a small community library"
requires-python = ">=3.9"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

FILES["docs/design.md"] = """\
# shelf: design

- `shelf/catalog.py` reads the old system's CSV export, `data/catalog.csv`: one row per copy, with its barcode, ISBN,
  title, author, call number and year.
- `shelf/isbn.py` checks the check digit of an ISBN-10 or an ISBN-13.
- `shelf/loans.py`: a loan runs `LOAN_DAYS` days and can be renewed `MAX_RENEWALS` times, each time from the old due
  date.
- `shelf/fees.py`: what a member owes the library.
- `shelf/api.py`: the desk's operations as plain functions, and `handle()` to call one by name.
- `tools/audit_isbn.py` counts the catalog records whose ISBN does not check out, by kind of fault.
"""

FILES["shelf/__init__.py"] = '''\
"""shelf: circulation for a small community library."""
__version__ = "0.6.1"
'''

FILES["shelf/catalog.py"] = '''\
"""The catalog: one Book per copy, read from the old system's CSV export."""
from __future__ import annotations

import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    barcode: str
    isbn: str
    title: str
    author: str  # "" for an anonymous work
    call_number: str
    year: int


def read(path) -> list:
    """Every copy in the export, in its order."""
    with open(path, encoding="utf-8", newline="") as f:
        return [Book(r["barcode"], r["isbn"], r["title"], r["author"], r["call_number"], int(r["year"] or 0))
                for r in csv.DictReader(f)]


def find(books, barcode: str):
    """The copy with this barcode, or None."""
    return next((b for b in books if b.barcode == barcode), None)
'''

FILES["shelf/isbn.py"] = '''\
"""ISBNs as the catalog holds them."""
from __future__ import annotations


def is_valid(code: str) -> bool:
    """True for an ISBN-10 or ISBN-13 whose check digit is right."""
    if len(code) == 10:
        if not code[:9].isdigit() or not (code[9].isdigit() or code[9] == "X"):
            return False
        total = sum((10 - i) * int(c) for i, c in enumerate(code[:9])) + (10 if code[9] == "X" else int(code[9]))
        return total % 11 == 0
    if len(code) == 13 and code.isdigit():
        total = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(code[:12]))
        return (10 - total % 10) % 10 == int(code[12])
    return False
'''

FILES["shelf/loans.py"] = '''\
"""Loans: who has which copy, and until when."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

LOAN_DAYS = 14
MAX_RENEWALS = 2


@dataclass(frozen=True)
class Loan:
    barcode: str
    member: str
    start: date
    due: date
    renewals: int = 0


class RenewalRefused(Exception):
    pass


def lend(barcode: str, member: str, today: date) -> Loan:
    return Loan(barcode, member, today, today + timedelta(days=LOAN_DAYS))


def renew(loan: Loan) -> Loan:
    """Another loan period, from the old due date; at most MAX_RENEWALS times."""
    if loan.renewals >= MAX_RENEWALS:
        raise RenewalRefused(f"{loan.barcode} has been renewed {loan.renewals} times already")
    return replace(loan, due=loan.due + timedelta(days=LOAN_DAYS), renewals=loan.renewals + 1)


def days_late(loan: Loan, returned: date) -> int:
    return max(0, (returned - loan.due).days)
'''

FILES["shelf/fees.py"] = '''\
"""What a member owes the library. Amounts are Decimals."""
from __future__ import annotations

from decimal import Decimal

LOST_COPY = Decimal("20.00")  # replacing a lost copy, whatever it was
PROCESSING = Decimal("2.50")  # added to every lost-copy charge


def lost_copy_charge() -> Decimal:
    return LOST_COPY + PROCESSING
'''

FILES["shelf/api.py"] = '''\
"""The desk's operations as plain functions over the catalog and the loans, and handle() to call one by name."""
from __future__ import annotations

import os
from datetime import date

from . import catalog, fees, loans

FIELDS = ("barcode", "isbn", "title", "author", "call_number", "year")


class ShelfError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def search(books, text: str) -> list:
    """The copies whose title or author contains the text, whatever its case."""
    needle = text.strip().lower()
    if not needle:
        raise ShelfError(400, "an empty search")
    return [b for b in books if needle in b.title.lower() or needle in b.author.lower()]


def lend_copy(books, barcode: str, member: str, today: date) -> loans.Loan:
    if catalog.find(books, barcode) is None:
        raise ShelfError(404, f"no copy {barcode}")
    return loans.lend(barcode, member, today)


def renew_loan(loan: loans.Loan) -> loans.Loan:
    try:
        return loans.renew(loan)
    except loans.RenewalRefused as e:
        raise ShelfError(409, str(e))


def return_copy(loan: loans.Loan, today: date) -> dict:
    return {"barcode": loan.barcode, "days_late": loans.days_late(loan, today)}


def member_lonas(all_loans, member: str) -> list:
    return [x for x in all_loans if x.member == member]


def lost_charge() -> str:
    return str(fees.lost_copy_charge())


ROUTES = {"search": search, "lend": lend_copy, "renew": renew_loan, "return": return_copy, "loans": member_lonas,
          "lost": lost_charge}


def handle(name: str, *args):
    """Run the operation called name; an unknown one is a 404."""
    if name not in ROUTES:
        raise ShelfError(404, f"no operation {name}")
    return ROUTES[name](*args)
'''

FILES["tools/audit_isbn.py"] = '''\
"""How many catalog records have a bad ISBN, and of what kind.

    python tools/audit_isbn.py [catalog.csv]
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shelf import catalog, isbn  # noqa: E402


def kind(code: str) -> str:
    if "-" in code:
        return "hyphens"
    if " " in code:
        return "spaces"
    if code.endswith("x"):
        return "lower-case x"
    if len(code) not in (10, 13):
        return "length"
    return "check digit"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "catalog.csv"
    books = catalog.read(path)
    bad = [b for b in books if not isbn.is_valid(b.isbn)]
    print(f"{len(bad)} of {len(books)} records have a bad ISBN.")
    for k, n in Counter(kind(b.isbn) for b in bad).most_common():
        print(f"  {k}: {n}")


if __name__ == "__main__":
    main()
'''

FILES["tests/conftest.py"] = '''\
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
'''

FILES["tests/test_isbn.py"] = '''\
from shelf import isbn


def test_a_right_isbn_13():
    assert isbn.is_valid("9780141187761")


def test_a_right_isbn_10_ending_in_x():
    assert isbn.is_valid("080442957X")


def test_a_wrong_check_digit():
    assert not isbn.is_valid("9780141187762")


def test_a_lost_digit():
    assert not isbn.is_valid("978014118776")
'''

FILES["tests/test_loans.py"] = '''\
from datetime import date

import pytest

from shelf import loans


def test_a_loan_runs_two_weeks():
    assert loans.lend("31000001", "m17", date(2026, 10, 1)).due == date(2026, 10, 15)


def test_a_renewal_runs_from_the_old_due_date_twice_at_most():
    loan = loans.lend("31000001", "m17", date(2026, 10, 1))
    twice = loans.renew(loans.renew(loan))
    assert twice.renewals == 2 and twice.due == loan.due + 2 * (loan.due - loan.start)
    with pytest.raises(loans.RenewalRefused):
        loans.renew(twice)


def test_days_late():
    loan = loans.lend("31000001", "m17", date(2026, 10, 1))
    assert loans.days_late(loan, loan.due) == 0
    assert loans.days_late(loan, date(2026, 12, 1)) == (date(2026, 12, 1) - loan.due).days
'''

FILES["tests/test_fees.py"] = '''\
from decimal import Decimal

from shelf import fees


def test_a_lost_copy():
    assert fees.lost_copy_charge() == Decimal("22.50")
'''

FILES["tests/test_catalog.py"] = '''\
from pathlib import Path

from shelf import catalog

CSV = Path(__file__).resolve().parents[1] / "data" / "catalog.csv"


def test_the_export_reads_whole():
    books = catalog.read(CSV)
    assert len(books) > 500 and all(b.barcode and b.title and b.call_number for b in books)


def test_find():
    books = catalog.read(CSV)
    assert catalog.find(books, books[3].barcode) == books[3]
    assert catalog.find(books, "nope") is None
'''

FILES["tests/test_api.py"] = '''\
from datetime import date
from pathlib import Path

import pytest

from shelf import api, catalog

BOOKS = catalog.read(Path(__file__).resolve().parents[1] / "data" / "catalog.csv")


def test_search_by_title_or_author():
    assert {b.title for b in api.search(BOOKS, "morrison")} == {"Beloved", "Song of Solomon"}
    with pytest.raises(api.ShelfError):
        api.search(BOOKS, "  ")


def test_lend_renew_and_return():
    loan = api.lend_copy(BOOKS, BOOKS[0].barcode, "m17", date(2026, 10, 1))
    assert api.handle("loans", [loan], "m17") == [loan]
    loan = api.renew_loan(api.renew_loan(loan))
    with pytest.raises(api.ShelfError):
        api.renew_loan(loan)
    assert api.return_copy(loan, loan.due)["days_late"] == 0


def test_an_unknown_copy_or_operation():
    with pytest.raises(api.ShelfError):
        api.lend_copy(BOOKS, "nope", "m17", date(2026, 10, 1))
    with pytest.raises(api.ShelfError):
        api.handle("nope")
'''


def files() -> dict:
    """Every file of the repository, by path."""
    return {**FILES, "data/catalog.csv": catalog_csv()}
