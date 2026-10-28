"""The repository the long-session job runs in: ledgerly, a small bookkeeping library for a chain of shops.

The hand-written modules carry the behaviour the job changes. The long tables (categories, the chart of accounts,
currencies, banks, the rate history) and the nightly import log are generated from fixed seeds, so every run starts
from the same bytes. `materialize(folder)` writes it all and makes the first commit.
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

GIT = ["git", "-c", "user.name=ledgerly dev", "-c", "user.email=dev@ledgerly.invalid", "-c", "commit.gpgsign=false",
       "-c", "core.autocrlf=false", "-c", "init.defaultBranch=main"]

BASES = [  # key, Turkish, English, tax class, unit
    ("general", "Genel", "General", "standard", "adet"), ("books", "Kitap", "Books", "standard", "adet"),
    ("electronics", "Elektronik", "Electronics", "standard", "adet"),
    ("stationery", "Kırtasiye", "Stationery", "standard", "adet"), ("bread", "Ekmek", "Bread", "basic", "kg"),
    ("milk", "Süt", "Milk", "basic", "lt"), ("vegetables", "Sebze", "Vegetables", "basic", "kg"),
    ("fruit", "Meyve", "Fruit", "basic", "kg"), ("meat", "Et", "Meat", "reduced", "kg"),
    ("cheese", "Peynir", "Cheese", "reduced", "kg"), ("textiles", "Tekstil", "Textiles", "reduced", "adet"),
    ("shoes", "Ayakkabı", "Shoes", "reduced", "çift"), ("furniture", "Mobilya", "Furniture", "reduced", "adet"),
    ("medicine", "İlaç", "Medicine", "reduced", "kutu"), ("cosmetics", "Kozmetik", "Cosmetics", "standard", "adet"),
    ("toys", "Oyuncak", "Toys", "standard", "adet"), ("hardware", "Hırdavat", "Hardware", "standard", "adet"),
    ("paint", "Boya", "Paint", "standard", "lt"), ("garden", "Bahçe", "Garden", "standard", "adet"),
    ("pets", "Evcil hayvan", "Pets", "standard", "adet"), ("sports", "Spor", "Sports", "standard", "adet"),
    ("music", "Müzik", "Music", "standard", "adet"), ("software", "Yazılım", "Software", "standard", "lisans"),
    ("services", "Hizmet", "Services", "standard", "saat"), ("rent", "Kira", "Rent", "exempt", "ay"),
    ("education", "Eğitim", "Education", "exempt", "saat"), ("health", "Sağlık hizmeti", "Health care", "exempt", "saat"),
    ("insurance", "Sigorta", "Insurance", "exempt", "poliçe"), ("newspapers", "Gazete", "Newspapers", "basic", "adet"),
    ("magazines", "Dergi", "Magazines", "standard", "adet")]
VARIANTS = [  # suffix, Turkish, English
    ("", "", ""), ("imported", "ithal", "imported"), ("used", "ikinci el", "second-hand"), ("bulk", "toptan", "bulk"),
    ("gift", "hediyelik", "gift"), ("online", "internet satışı", "online sale"), ("export", "ihraç", "export"),
    ("sample", "numune", "sample"), ("damaged", "hasarlı", "damaged"), ("promo", "kampanya", "promotion"),
    ("rental", "kiralık", "rental"), ("repair", "tamir", "repair"), ("spare", "yedek parça", "spare part"),
    ("kit", "set", "kit"), ("service", "servis", "service")]
TOP_ACCOUNTS = [
    ("100", "Kasa"), ("101", "Alınan Çekler"), ("102", "Bankalar"), ("120", "Alıcılar"), ("121", "Alacak Senetleri"),
    ("153", "Ticari Mallar"), ("191", "İndirilecek KDV"), ("255", "Demirbaşlar"), ("320", "Satıcılar"),
    ("321", "Borç Senetleri"), ("335", "Personele Borçlar"), ("360", "Ödenecek Vergi ve Fonlar"),
    ("391", "Hesaplanan KDV"), ("500", "Sermaye"), ("600", "Yurt İçi Satışlar"), ("601", "Yurt Dışı Satışlar"),
    ("610", "Satıştan İadeler"), ("621", "Satılan Ticari Mallar Maliyeti"), ("632", "Genel Yönetim Giderleri"),
    ("642", "Faiz Gelirleri"), ("656", "Kambiyo Zararları"), ("760", "Pazarlama Satış ve Dağıtım Giderleri"),
    ("770", "Genel Yönetim Giderleri"), ("780", "Finansman Giderleri")]
BRANCHES = ["Merkez", "Kadıköy", "Beşiktaş", "Üsküdar", "Bakırköy", "Ankara", "İzmir", "Bursa", "Antalya", "Eskişehir",
            "Trabzon", "Gaziantep"]
CURRENCIES = [  # code, name, minor units, lira per unit on the reference day
    ("USD", "US Dollar", 2, "41.2050"), ("EUR", "Euro", 2, "47.8410"), ("GBP", "Pound Sterling", 2, "55.1020"),
    ("CHF", "Swiss Franc", 2, "51.3060"), ("JPY", "Yen", 0, "0.2741"), ("CAD", "Canadian Dollar", 2, "29.6530"),
    ("AUD", "Australian Dollar", 2, "26.8890"), ("DKK", "Danish Krone", 2, "6.4120"),
    ("SEK", "Swedish Krona", 2, "4.3870"), ("NOK", "Norwegian Krone", 2, "4.0950"),
    ("SAR", "Saudi Riyal", 2, "10.9830"), ("KWD", "Kuwaiti Dinar", 3, "134.6100"), ("AED", "UAE Dirham", 2, "11.2190"),
    ("QAR", "Qatari Riyal", 2, "11.3200"), ("RUB", "Russian Ruble", 2, "0.5120"), ("CNY", "Yuan Renminbi", 2, "5.7830"),
    ("AZN", "Azerbaijan Manat", 2, "24.2380"), ("IRR", "Iranian Rial", 2, "0.0010"),
    ("PKR", "Pakistan Rupee", 2, "0.1468"), ("BGN", "Bulgarian Lev", 2, "24.4610"), ("RON", "Romanian Leu", 2, "9.4170"),
    ("KRW", "Won", 0, "0.0297"), ("GEL", "Lari", 2, "15.2050"), ("UAH", "Hryvnia", 2, "0.9910"),
    ("HUF", "Forint", 2, "0.1221"), ("PLN", "Zloty", 2, "11.2240"), ("CZK", "Czech Koruna", 2, "1.9330"),
    ("INR", "Indian Rupee", 2, "0.4702"), ("ZAR", "Rand", 2, "2.3510"), ("MXN", "Mexican Peso", 2, "2.2160"),
    ("BRL", "Brazilian Real", 2, "7.5530"), ("ILS", "New Israeli Sheqel", 2, "12.2940"),
    ("EGP", "Egyptian Pound", 2, "0.8480"), ("MAD", "Moroccan Dirham", 2, "4.4630"),
    ("TND", "Tunisian Dinar", 3, "14.0120"), ("JOD", "Jordanian Dinar", 3, "58.1100"),
    ("IQD", "Iraqi Dinar", 3, "0.0315"), ("LYD", "Libyan Dinar", 3, "7.6110"), ("SGD", "Singapore Dollar", 2, "31.8820"),
    ("HKD", "Hong Kong Dollar", 2, "5.3010"), ("NZD", "New Zealand Dollar", 2, "24.3920"),
    ("THB", "Baht", 2, "1.2560"), ("MYR", "Ringgit", 2, "9.7340"), ("IDR", "Rupiah", 2, "0.0025"),
    ("KZT", "Tenge", 2, "0.0812"), ("UZS", "Uzbekistan Sum", 2, "0.0033"), ("TMT", "Turkmenistan Manat", 2, "11.7730"),
    ("RSD", "Serbian Dinar", 2, "0.4085"), ("MKD", "Denar", 2, "0.7760"), ("ALL", "Lek", 2, "0.4471")]
HOLIDAYS = ["2026-01-01", "2026-03-19", "2026-03-20", "2026-03-21", "2026-03-22", "2026-04-23", "2026-05-01",
            "2026-05-19", "2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29", "2026-05-30", "2026-07-15",
            "2026-08-30", "2026-10-28", "2026-10-29", "2027-01-01", "2027-03-09", "2027-03-10", "2027-03-11",
            "2027-04-23", "2027-05-01", "2027-05-15", "2027-05-16", "2027-05-17", "2027-05-18", "2027-05-19",
            "2027-07-15", "2027-08-30", "2027-10-28", "2027-10-29"]
BANKS = [  # EFT code, name, feed format
    ("0010", "T.C. Ziraat Bankası", "camt053"), ("0012", "Türkiye Halk Bankası", "mt940"),
    ("0015", "Türkiye Vakıflar Bankası", "camt053"), ("0032", "Türk Ekonomi Bankası", "csv-v2"),
    ("0046", "Akbank", "camt053"), ("0059", "Şekerbank", "mt940"), ("0062", "Garanti BBVA", "camt053"),
    ("0064", "Türkiye İş Bankası", "camt053"), ("0067", "Yapı ve Kredi Bankası", "camt053"),
    ("0091", "Arap Türk Bankası", "mt940"), ("0092", "Citibank", "mt940"), ("0096", "Turkish Bank", "csv-v1"),
    ("0099", "ING Bank", "camt053"), ("0103", "Fibabanka", "csv-v2"), ("0108", "Turkland Bank", "csv-v1"),
    ("0109", "ICBC Turkey Bank", "mt940"), ("0111", "QNB Bank", "camt053"), ("0115", "Deutsche Bank", "mt940"),
    ("0123", "HSBC Bank", "camt053"), ("0124", "Alternatifbank", "csv-v2"), ("0125", "Burgan Bank", "csv-v2"),
    ("0134", "Denizbank", "camt053"), ("0135", "Anadolubank", "csv-v1"), ("0137", "Rabobank", "mt940"),
    ("0143", "Aktif Yatırım Bankası", "csv-v2"), ("0146", "Odea Bank", "csv-v2"), ("0203", "Albaraka Türk", "mt940"),
    ("0205", "Kuveyt Türk Katılım Bankası", "camt053"), ("0206", "Türkiye Finans Katılım Bankası", "camt053"),
    ("0209", "Ziraat Katılım Bankası", "camt053"), ("0210", "Vakıf Katılım Bankası", "camt053"),
    ("0211", "Türkiye Emlak Katılım Bankası", "csv-v2")]
VAT_HISTORY = [(2002, "0.18", "0.08", "0.01"), (2013, "0.18", "0.08", "0.01"), (2023, "0.20", "0.10", "0.01")]

FILES = {
    "README.md": r'''# ledgerly

Bookkeeping for a small chain of shops: invoices, VAT, currency conversion, the nightly import from the bank feed,
month-end reports and a small API that the shops' other services call.

    python -m pytest          the tests
    python tools/bench.py     the month-end run, simulated

docs/design.md says how the pieces fit; docs/operations.md says where things run.
''',
    "pyproject.toml": r'''[project]
name = "ledgerly"
version = "0.8.3"
requires-python = ">=3.9"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
''',
    ".gitignore": "__pycache__/\n.pytest_cache/\nreports/\n",
    "CHANGELOG.md": r'''# Changelog

## 0.8.3 (2026-10-02)
- Import: a batch that keeps timing out is skipped and reported instead of stopping the night's import.
- API: GET /accounts/{id}/entries.

## 0.8.2 (2026-09-18)
- Invoices: credit notes.
- Money: allocate() splits a total into cents that always add up.

## 0.8.1 (2026-09-04)
- Reports: monthly totals and totals per branch.
- Currency: minor units per currency.

## 0.8.0 (2026-08-21)
- The first release the shops use: invoices, VAT, CSV and JSON export, the bank feed import, the API.
''',
    "config/reports.toml": r'''# Where the month-end reports run. Production runs from the scheduler, with its own copy of this file.
[database]
host = "db-staging.internal"
port = 5432
name = "ledgerly_stg"

[output]
folder = "reports"
format = "text"
''',
    "docs/design.md": r'''# ledgerly: design notes

ledgerly keeps the books of a small chain of shops. It is a library first: the service that runs it (the scheduler,
the HTTP server, the database layer) lives in another repository and imports it.

## Money

- Amounts are `Decimal`. Floats are refused at the door (`money.to_decimal`).
- A computation keeps full precision and rounds to the cent once, at the end. Rounding line by line is how an invoice
  total ends up a cent away from the sum of its lines, and the tax office notices.
- `round_cents` rounds half-up unless told otherwise, as the shops' tills do.
- `allocate` splits a total over weights in whole cents that always add up. Use it to spread a shipping cost over
  lines; never call `round_cents` on each part.

## Invoices and VAT

An invoice is a list of lines. Each line has a category, and the category's tax class picks the VAT rate
(`catalog.tax_class`, then `tax.RATES`). VAT is computed on each line's net amount, after its discount, and is not
rounded per line: `Invoice.total()` rounds once.

The rates follow the law: 20% standard, 10% reduced, 1% basic, 0% exempt. `tax.RATE_HISTORY` keeps the rates of
past years, for credit notes on old invoices. Sales abroad (the `*.export` categories) are exempt.

E-invoices go to the tax office's system as UBL-TR XML (`invoices.to_ubl`). The XML carries the rounded total and the
VAT per rate.

## Categories

`ledgerly/catalog.py` lists every category the shops sell: the Turkish label on receipts, the English label in
exports, the tax class, the unit, the receipt group and the customs tariff code. Finance signs off the tax classes, and
`tests/test_catalog.py` pins them, so that a change to a class shows up in review.

## Export

- CSV goes to the bank's importer: comma-separated, one line per entry, no header. The bank reads the columns by
  position, so a change here needs the bank's side changed on the same day.
- JSON goes to the shops' dashboard. Amounts are strings.
- Plain text goes into e-mails.

## Currency

Some suppliers invoice in dollars, euros or pounds. `currency.convert` turns an amount into lira at the central bank's
rate of the day. Each `RateSource.fetch` is a round trip to the bank's rate service, about 4 ms, and `convert` fetches
for every line, so a month-end run with a few thousand foreign lines spends most of its time waiting on the bank.
`tools/bench.py` simulates that run. A day's rate does not change once it is published, so caching per day is safe;
it is on the list for 0.9.

Unknown currency codes currently go through at par (a rate of 1). That has hidden two typos in supplier invoices this
year.

## The nightly import

At 02:00 the scheduler runs `importer.import_all` over the night's batches from the bank feed. The feed is slow and
times out now and then; `import_batch` then reads the batch again from the start, up to two more times. A batch that
keeps timing out is skipped and reported, and the rest of the night goes on. Each night writes a log to
`logs/import-YYYY-MM-DD.log`.

Entry ids come from the bank and are unique per bank. The store does not enforce that.

## Reports

Month-end reports run against the reporting database named in `config/reports.toml`; on staging that is
`ledgerly_stg` (see docs/operations.md). `reports.monthly_total` gives a month's total and `reports.by_branch` the
totals per branch, for the branch managers. A summary per account is planned for 0.9 (`reports.monthly_summary`).

## API

`ledgerly/api.py` is a small router that the service mounts under `/v1`. Other services import its names, so a
handler keeps its name even when its path changes. Errors answer `{"error": "<message>"}` with a 4xx status. The
messages are still English and will be translated with the rest of the API.

Planned for 0.9: `GET /accounts/{id}/balance`, answering `{"account": "<id>", "balance": "<lira, two places>"}`.

## Migrations

The schema lives in `migrations/`, one numbered file per change. The DBA applies them in production by hand, in
order, after review. The application never runs them, and a file that has been applied must never change.

## Tests

`python -m pytest` runs everything. The tests use the in-memory store; nothing touches a database or the network.
''',
    "docs/operations.md": r'''# Operations

## Environments

| | Database | Host | Deployed by |
| --- | --- | --- | --- |
| production | ledgerly_prod | db-prod.internal | the release pipeline, after the DBA has applied the migrations |
| staging | ledgerly_stg | db-staging.internal | every merge to main |
| local | an in-memory store | | you |

## The nightly import

- At 02:00, from the feed bank-tr-03, every batch of the previous day.
- The log goes to `logs/import-YYYY-MM-DD.log`. Its last line says how many rows were read and how many entries were
  stored. The two should match.
- A batch that keeps timing out is skipped and listed at the end. Run it again by hand the next morning.

## Month-end reports

- They run on staging first, against `ledgerly_stg`, and then on production.
- The output goes to `reports/` as text, one file per report.
- The branch managers get `by_branch` by e-mail on the first working day of the month.

## Releases

1. Add the release to CHANGELOG.md.
2. Tag it `vX.Y`.
3. The DBA applies any new migrations before the deploy.
4. The release pipeline deploys to production.
''',
    "migrations/0001_init.py": r'''"""The first schema: accounts and entries."""

SQL = """
CREATE TABLE accounts (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE entries (
    id TEXT NOT NULL,
    day DATE NOT NULL,
    account TEXT NOT NULL REFERENCES accounts (code),
    description TEXT,
    amount NUMERIC(14, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'TRY'
);
"""
''',
    "migrations/0002_tax_rates.py": r'''"""VAT rates as a table, for the reporting database."""

SQL = """
CREATE TABLE tax_rates (
    class TEXT PRIMARY KEY,
    rate NUMERIC(4, 2) NOT NULL
);

INSERT INTO tax_rates (class, rate) VALUES
    ('standard', 0.20),
    ('reduced', 0.10),
    ('basic', 0.01),
    ('exempt', 0);
"""
''',
    "migrations/0003_invoices.py": r'''"""Invoices and their lines."""

SQL = """
CREATE TABLE invoices (
    number TEXT PRIMARY KEY,
    account TEXT NOT NULL REFERENCES accounts (code),
    issued DATE NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'TRY',
    total NUMERIC(14, 2) NOT NULL
);

CREATE TABLE invoice_lines (
    invoice TEXT NOT NULL REFERENCES invoices (number),
    position INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity NUMERIC(12, 3) NOT NULL,
    unit_price NUMERIC(14, 4) NOT NULL,
    category TEXT NOT NULL,
    discount NUMERIC(5, 4) NOT NULL DEFAULT 0,
    PRIMARY KEY (invoice, position)
);
"""
''',
    "ledgerly/__init__.py": r'''"""ledgerly: bookkeeping for a small chain of shops."""

__version__ = "0.8.3"
''',
    "ledgerly/money.py": r'''"""Money helpers.

Amounts are Decimal throughout. A computation keeps full precision and rounds to the cent once, at the end: rounding
on the way is how a total drifts a cent away from the sum of its lines.
"""
from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal("0")


def to_decimal(value) -> Decimal:
    """A Decimal from an int, a str or a Decimal. Floats are refused: 0.1 has no exact binary form."""
    if isinstance(value, (bool, float)):
        raise TypeError(f"not a money amount: {value!r}")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip())
    except InvalidOperation as e:
        raise ValueError(f"not a money amount: {value!r}") from e


def round_cents(amount, rounding: str = ROUND_HALF_UP) -> Decimal:
    """Round to the cent. Half-up unless told otherwise, as a till rounds a receipt."""
    return to_decimal(amount).quantize(CENT, rounding=rounding)


def allocate(total, weights) -> list:
    """Split a total into cent amounts in proportion to the weights. The cents that rounding down leaves over go to
    the parts with the largest remainders, so the parts always add up to the total."""
    total = round_cents(total)
    weights = [to_decimal(w) for w in weights]
    whole = sum(weights, ZERO)
    if whole <= 0:
        raise ValueError("weights must add up to more than zero")
    raw = [total * w / whole for w in weights]
    parts = [r.quantize(CENT, rounding=ROUND_DOWN) for r in raw]
    left = int((total - sum(parts, ZERO)) / CENT)
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - parts[i], reverse=True)[:left]:
        parts[i] += CENT
    return parts


def format_amount(amount, currency: str = "TRY") -> str:
    """'1.234,50 TL' for lira, '1,234.50 USD' for anything else."""
    value = round_cents(amount)
    whole, cents = f"{abs(value):.2f}".split(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    sign = "-" if value < 0 else ""
    if currency == "TRY":
        return f"{sign}{'.'.join(groups)},{cents} TL"
    return f"{sign}{','.join(groups)}.{cents} {currency}"


def percent(part, whole) -> Decimal:
    """`part` as a percentage of `whole`, to two places; zero when `whole` is zero."""
    whole = to_decimal(whole)
    if whole == 0:
        return ZERO
    return round_cents(to_decimal(part) * 100 / whole)
''',
    "ledgerly/invoices.py": r'''"""Invoices: lines, discounts, VAT and totals, and the e-invoice XML."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from xml.sax.saxutils import escape

from . import catalog, tax
from .money import ZERO, format_amount, round_cents, to_decimal


class InvoiceError(ValueError):
    """An invoice that cannot be issued. The message is shown to the shop's staff."""


@dataclass
class InvoiceLine:
    description: str
    quantity: Decimal
    unit_price: Decimal
    category: str = "general"
    discount: Decimal = ZERO  # a fraction: 0.10 is 10% off

    def net(self) -> Decimal:
        """Quantity times price, less the discount; not rounded."""
        quantity, price = to_decimal(self.quantity), to_decimal(self.unit_price)
        return quantity * price * (1 - to_decimal(self.discount))

    def check(self) -> None:
        if not self.description.strip():
            raise InvoiceError("Satır açıklaması boş olamaz.")
        if to_decimal(self.quantity) <= 0:
            raise InvoiceError(f"Geçersiz miktar: {self.quantity}")
        if not ZERO <= to_decimal(self.discount) < 1:
            raise InvoiceError(f"İndirim 0 ile 1 arasında olmalı: {self.discount}")


@dataclass
class Invoice:
    number: str
    account: str
    issued: date
    currency: str = "TRY"
    lines: list = field(default_factory=list)
    due_days: int = 30

    def add(self, description: str, quantity, unit_price, category: str = "general", discount=ZERO) -> InvoiceLine:
        line = InvoiceLine(description, to_decimal(quantity), to_decimal(unit_price), category, to_decimal(discount))
        line.check()
        self.lines.append(line)
        return line

    def subtotal(self) -> Decimal:
        """The lines' net amounts, unrounded."""
        return sum((line.net() for line in self.lines), ZERO)

    def tax_total(self) -> Decimal:
        """VAT over all lines, unrounded."""
        return sum((tax.tax_for(line) for line in self.lines), ZERO)

    def total(self) -> Decimal:
        """What the customer pays: net plus VAT, rounded to the cent once."""
        return round_cents(self.subtotal() + self.tax_total())

    def due(self) -> date:
        return self.issued + timedelta(days=self.due_days)

    def check(self) -> None:
        if not self.lines:
            raise InvoiceError(f"{self.number}: faturada satır yok.")
        for line in self.lines:
            line.check()

    def credit_note(self, number: str) -> "Invoice":
        """A credit note that cancels this invoice: the same lines with negative quantities."""
        lines = [InvoiceLine(f"İade: {line.description}", -to_decimal(line.quantity), line.unit_price, line.category,
                             line.discount) for line in self.lines]
        return Invoice(number, self.account, self.issued, self.currency, lines, self.due_days)

    def summary(self) -> str:
        """The text block printed under the lines: VAT per rate, then the total."""
        rows = [f"Fatura {self.number}  {self.account}  {self.issued.isoformat()}"]
        for line in self.lines:
            rows.append(f"  {line.description:<30} {catalog.label(line.category):<24} "
                        f"{format_amount(line.net(), self.currency):>16}")
        for rate, (net, vat) in tax.breakdown(self.lines).items():
            rows.append(f"  KDV %{rate * 100:.0f}  matrah {format_amount(net, self.currency)}  "
                        f"vergi {format_amount(vat, self.currency)}")
        rows.append(f"  Toplam {format_amount(self.total(), self.currency)}")
        return "\n".join(rows)


def to_ubl(invoice: Invoice) -> str:
    """The invoice as UBL-TR XML for the tax office's e-invoice system. Amounts are rounded to the cent here, and only
    here: the XML must carry the same total the customer was shown."""
    currency = escape(invoice.currency)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">',
           "  <UBLVersionID>2.1</UBLVersionID>",
           "  <CustomizationID>TR1.2</CustomizationID>",
           "  <ProfileID>TEMELFATURA</ProfileID>",
           f"  <ID>{escape(invoice.number)}</ID>",
           f"  <IssueDate>{invoice.issued.isoformat()}</IssueDate>",
           f"  <DocumentCurrencyCode>{currency}</DocumentCurrencyCode>",
           f"  <AccountingCustomerParty>{escape(invoice.account)}</AccountingCustomerParty>"]
    for rate, (net, vat) in tax.breakdown(invoice.lines).items():
        out += ["  <TaxTotal>",
                f'    <TaxAmount currencyID="{currency}">{round_cents(vat)}</TaxAmount>',
                "    <TaxSubtotal>",
                f'      <TaxableAmount currencyID="{currency}">{round_cents(net)}</TaxableAmount>',
                f"      <Percent>{rate * 100:.0f}</Percent>",
                "    </TaxSubtotal>",
                "  </TaxTotal>"]
    for position, line in enumerate(invoice.lines, 1):
        out += ["  <InvoiceLine>",
                f"    <ID>{position}</ID>",
                f'    <InvoicedQuantity unitCode="{escape(catalog.unit(line.category))}">{line.quantity}'
                "</InvoicedQuantity>",
                f'    <LineExtensionAmount currencyID="{currency}">{round_cents(line.net())}</LineExtensionAmount>',
                f"    <Item><Name>{escape(line.description)}</Name></Item>",
                f'    <Price><PriceAmount currencyID="{currency}">{line.unit_price}</PriceAmount></Price>',
                "  </InvoiceLine>"]
    out += ["  <LegalMonetaryTotal>",
            f'    <TaxExclusiveAmount currencyID="{currency}">{round_cents(invoice.subtotal())}</TaxExclusiveAmount>',
            f'    <PayableAmount currencyID="{currency}">{invoice.total()}</PayableAmount>',
            "  </LegalMonetaryTotal>",
            "</Invoice>"]
    return "\n".join(out) + "\n"
''',
    "ledgerly/storage.py": r'''"""The ledger: entries and accounts, kept in memory. The service layer writes them to the database."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .money import to_decimal


@dataclass(frozen=True)
class Entry:
    id: str
    day: date
    account: str
    description: str
    amount: Decimal
    currency: str = "TRY"

    @classmethod
    def from_row(cls, row: dict) -> "Entry":
        """An entry from a bank feed row: id, day (YYYY-MM-DD), account and amount, and optionally description and
        currency."""
        return cls(id=str(row["id"]), day=date.fromisoformat(str(row["day"])), account=str(row["account"]),
                   description=str(row.get("description", "")), amount=to_decimal(row["amount"]),
                   currency=str(row.get("currency", "TRY")))


class Store:
    """Entries in the order they arrived, and the accounts by code."""

    def __init__(self):
        self.entries = []
        self.accounts = {}

    def open_account(self, code: str, name: str) -> None:
        self.accounts[code] = name

    def add(self, entry: Entry) -> None:
        self.entries.append(entry)

    def all(self) -> list:
        return list(self.entries)

    def find(self, entry_id: str):
        """The entry with this id, or None."""
        return next((e for e in self.entries if e.id == entry_id), None)

    def entries_for(self, account: str) -> list:
        return [e for e in self.entries if e.account == account]

    def between(self, start: date, end: date) -> list:
        """The entries from start to end, both included."""
        return [e for e in self.entries if start <= e.day <= end]
''',
    "ledgerly/export.py": r'''"""Exports of the ledger: CSV for the bank's importer, JSON for the shops' dashboard, plain text for e-mail."""
from __future__ import annotations

import csv
import io
import json

from .money import format_amount

COLUMNS = ("date", "account", "description", "amount", "currency")


def rows(entries) -> list:
    return [[e.day.isoformat(), e.account, e.description, f"{e.amount:.2f}", e.currency] for e in entries]


def to_csv(entries) -> str:
    """Comma-separated, one line per entry, no header: the format the bank's importer reads."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter=",", lineterminator="\n")
    writer.writerows(rows(entries))
    return out.getvalue()


def to_json(entries) -> str:
    """A list of objects. Amounts are strings, so no float ever touches them."""
    return json.dumps([dict(zip(COLUMNS, r)) for r in rows(entries)], ensure_ascii=False, indent=2)


def to_text(entries) -> str:
    """Aligned lines for an e-mail."""
    return "\n".join(f"{e.day.isoformat()}  {e.account:<8} {e.description:<30} "
                     f"{format_amount(e.amount, e.currency):>18}" for e in entries)
''',
    "ledgerly/importer.py": r'''"""The nightly import of the bank feed into the store, batch by batch.

The feed is slow and times out now and then. A batch that times out is read again from the start, up to `retries`
more times. Each night writes a log to logs/.
"""
from __future__ import annotations

import logging

from .storage import Entry, Store

log = logging.getLogger("ledgerly.importer")

REQUIRED = ("id", "day", "account", "amount")


class FeedTimeout(Exception):
    """The feed did not answer in time."""


class FeedError(Exception):
    """A row the importer cannot read."""


def bank_of(entry_id: str) -> str:
    """The bank an entry id came from: ids from the feed start with the bank's EFT code after a dash, as in
    E-0062-..., and older ids have no code (they are Ziraat's)."""
    parts = entry_id.split("-")
    return parts[1] if len(parts) > 2 and parts[1] in BANKS else "0010"


def check_row(row: dict) -> None:
    missing = [k for k in REQUIRED if not row.get(k)]
    if missing:
        raise FeedError(f"row {row.get('id', '?')}: missing {', '.join(missing)}")


def import_batch(feed, store: Store, batch_id: int, retries: int = 2) -> int:
    """Read one batch from the feed into the store and return the number of entries added."""
    for attempt in range(retries + 1):
        added = 0
        try:
            for row in feed.rows(batch_id):
                check_row(row)
                store.add(Entry.from_row(row))
                added += 1
                log.info("batch %s: added entry %s (%s, %s %s)", batch_id, row["id"], row["account"], row["amount"],
                         row.get("currency", "TRY"))
            log.info("batch %s: done, %d entries", batch_id, added)
            return added
        except FeedTimeout:
            log.warning("batch %s: feed timeout after %d rows, retrying (%d/%d)", batch_id, added, attempt + 1, retries)
    raise FeedTimeout(f"batch {batch_id}: no answer after {retries} retries")


def import_all(feed, store: Store, batches, retries: int = 2) -> dict:
    """Import every batch. A batch that keeps timing out is skipped and reported; the rest go on."""
    read = stored = 0
    failed = []
    for batch_id in batches:
        before = len(store.entries)
        try:
            read += import_batch(feed, store, batch_id, retries)
        except FeedTimeout:
            failed.append(batch_id)
        stored += len(store.entries) - before
    log.info("import finished: %d rows read, %d entries stored, %d batches failed", read, stored, len(failed))
    return {"read": read, "stored": stored, "failed": failed}


# EFT code: (bank, feed format)
BANKS = {
''',
    "ledgerly/reports.py": r'''"""Month-end reports. They run against the reporting database named in config/reports.toml."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from . import accounts
from .money import ZERO, format_amount, round_cents

CONFIG = Path(__file__).resolve().parents[1] / "config" / "reports.toml"
AGING = ((30, "0-30"), (60, "31-60"), (90, "61-90"))


def load_config(path: Path = CONFIG) -> dict:
    """The part of TOML the file uses: [sections], and key = "string" or key = number lines."""
    config, section = {}, None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = config.setdefault(line[1:-1].strip(), {})
            continue
        key, _, value = (part.strip() for part in line.partition("="))
        value = value[1:-1] if value[:1] == value[-1:] == '"' else int(value)
        (section if section is not None else config)[key] = value
    return config


def database(path: Path = CONFIG) -> str:
    """The name of the database the reports run against."""
    return load_config(path)["database"]["name"]


def in_month(entries, year: int, month: int) -> list:
    return [e for e in entries if e.day.year == year and e.day.month == month]


def monthly_total(entries, year: int, month: int) -> Decimal:
    """All the month's entries, in lira, rounded to the cent."""
    return round_cents(sum((e.amount for e in in_month(entries, year, month)), ZERO))


def monthly_summary(entries, year: int, month: int) -> dict:
    """Totals per account for one month, {account code: total}, for the month-end report. Planned for 0.9."""
    raise NotImplementedError("monthly_summary is planned for 0.9")


def by_branch(entries, year: int, month: int) -> dict:
    """Totals per branch (the part of the account code after the dot), for the branch managers' e-mail."""
    totals = defaultdict(lambda: ZERO)
    for e in in_month(entries, year, month):
        branch = e.account.split(".", 1)[1] if "." in e.account else "00"
        totals[branch] += e.amount
    return {k: round_cents(v) for k, v in sorted(totals.items())}


def aging(entries, today: date) -> dict:
    """Receivables (accounts 120.*) by age in days, for the collections call on Mondays."""
    buckets = {label: ZERO for _, label in AGING}
    buckets["90+"] = ZERO
    for e in entries:
        if not e.account.startswith("120"):
            continue
        age = (today - e.day).days
        label = next((label for limit, label in AGING if age <= limit), "90+")
        buckets[label] += e.amount
    return {k: round_cents(v) for k, v in buckets.items()}


def render(totals: dict, title: str) -> str:
    """A plain text table of {account code: amount} with the accounts' names, for the report e-mail."""
    width = max((len(accounts.name(code)) for code in totals), default=10)
    lines = [title, "=" * len(title)]
    for code, amount in totals.items():
        lines.append(f"{code:<8} {accounts.name(code):<{width}} {format_amount(amount):>18}")
    lines.append(f"{'':<8} {'Toplam':<{width}} {format_amount(sum(totals.values(), ZERO)):>18}")
    return "\n".join(lines)
''',
    "ledgerly/api.py": r'''"""ledgerly's API: a small router that the service mounts under /v1.

Other services import these names (handle, route, ROUTES, ApiError and the handlers), so they keep their names. The
error messages here are still English, from before the shops' staff saw them.

Planned for 0.9: GET /accounts/{id}/balance, answering {"account": "<id>", "balance": "<lira, two places>"}.
"""
from __future__ import annotations

import re

from . import catalog
from .money import to_decimal
from .storage import Entry

ROUTES = []


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def route(method: str, pattern: str):
    """Register a handler for a method and a path pattern with {name} parts."""
    regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")

    def register(fn):
        ROUTES.append((method, regex, fn))
        return fn
    return register


def render_error(error: ApiError) -> dict:
    return {"error": error.message}


def handle(method: str, path: str, store, body: dict | None = None) -> tuple:
    """(status, JSON body) for one request."""
    for registered, regex, fn in ROUTES:
        match = regex.match(path)
        if registered == method and match:
            try:
                return 200, fn(store, body=body, **match.groupdict())
            except ApiError as e:
                return e.status, render_error(e)
    return 404, {"error": "No such route"}


@route("GET", "/health")
def health(store, body=None) -> dict:
    return {"status": "ok"}


@route("GET", "/accounts")
def list_accounts(store, body=None) -> dict:
    return {"accounts": [{"code": code, "name": name} for code, name in sorted(store.accounts.items())]}


@route("GET", "/accounts/{id}")
def get_account(store, id, body=None) -> dict:
    if id not in store.accounts:
        raise ApiError(404, "Account not found")
    return {"code": id, "name": store.accounts[id]}


@route("GET", "/accounts/{id}/entries")
def account_entries(store, id, body=None) -> dict:
    if id not in store.accounts:
        raise ApiError(404, "Account not found")
    return {"account": id, "entries": [{"id": e.id, "day": e.day.isoformat(), "amount": f"{e.amount:.2f}"}
                                       for e in store.entries_for(id)]}


@route("GET", "/entries/{id}")
def get_entry(store, id, body=None) -> dict:
    entry = store.find(id)
    if entry is None:
        raise ApiError(404, "Entry not found")
    return {"id": entry.id, "day": entry.day.isoformat(), "account": entry.account,
            "description": entry.description, "amount": f"{entry.amount:.2f}", "currency": entry.currency}


@route("POST", "/entries")
def create_entry(store, body=None) -> dict:
    body = body or {}
    missing = [k for k in ("id", "day", "account", "amount") if k not in body]
    if missing:
        raise ApiError(400, f"Missing fields: {', '.join(missing)}")
    if body["account"] not in store.accounts:
        raise ApiError(400, "Unknown account")
    if store.find(str(body["id"])) is not None:
        raise ApiError(409, "Entry already exists")
    try:
        to_decimal(body["amount"])
    except (TypeError, ValueError):
        raise ApiError(400, "Amount is not a number")
    store.add(Entry.from_row(body))
    return {"id": str(body["id"])}


@route("GET", "/categories/{key}")
def get_category(store, key, body=None) -> dict:
    if key not in catalog.CATEGORIES:
        raise ApiError(404, "Category not found")
    tr, en, klass, unit, group, tariff = catalog.CATEGORIES[key]
    return {"key": key, "label": tr, "label_en": en, "tax_class": klass, "unit": unit, "group": group,
            "tariff": tariff}
''',
    "tools/bench.py": r'''"""The month-end run, simulated: every invoice line is converted to lira, and each step is priced.

A rate fetch is a round trip to the central bank's service (4.2 ms in production) and the rest is arithmetic (0.11 ms
a line). The timings are a model of production, not a clock, so they come out the same on every machine.

    python tools/bench.py
"""
from __future__ import annotations

import statistics
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ledgerly import currency  # noqa: E402

FETCH_MS = 4.2
LINE_MS = 0.11


def workload():
    """120 invoices over six days, 3 to 9 lines each, in dollars, euros and pounds."""
    start = date(2026, 10, 26)
    codes = ("USD", "EUR", "GBP")
    for n in range(120):
        day = start + timedelta(days=n % 6)
        yield [(Decimal(10 + (n * 13 + k * 7) % 90), codes[(n + k) % 3], day) for k in range(3 + (n * 5) % 7)]


def main() -> None:
    source = currency.RateSource()
    times, lines = [], 0
    for invoice in workload():
        before = source.calls
        for amount, code, day in invoice:
            currency.convert(amount, code, day, source=source)
        lines += len(invoice)
        times.append((source.calls - before) * FETCH_MS + len(invoice) * LINE_MS)
    times.sort()
    print(f"month-end run: {len(times)} invoices, {lines} lines, {source.calls} rate fetches")
    print(f"p50 {statistics.median(times):.1f} ms   p95 {times[int(len(times) * 0.95)]:.1f} ms")


if __name__ == "__main__":
    main()
''',
    "tests/conftest.py": r'''import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
''',
    "tests/test_money.py": r'''from decimal import Decimal

import pytest

from ledgerly.money import allocate, format_amount, round_cents, to_decimal


def test_round_cents_is_half_up_by_default():
    assert round_cents(Decimal("2.675")) == Decimal("2.68")


def test_allocate_adds_up():
    assert allocate(Decimal("100.00"), [1, 1, 1]) == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]


def test_format_amount():
    assert format_amount(Decimal("1234.5")) == "1.234,50 TL"
    assert format_amount(Decimal("-1234.5"), "USD") == "-1,234.50 USD"


def test_floats_are_refused():
    with pytest.raises(TypeError):
        to_decimal(0.1)
''',
    "tests/test_invoices.py": r'''from datetime import date
from decimal import Decimal

from ledgerly.invoices import Invoice, InvoiceLine, to_ubl


def make(*lines):
    return Invoice("F-2026-0001", "120.01", date(2026, 10, 1), lines=list(lines))


def test_total_is_net_plus_vat():
    invoice = make(InvoiceLine("Defter", Decimal("2"), Decimal("50.00"), "stationery"))
    assert invoice.subtotal() == Decimal("100.00")
    assert invoice.total() == Decimal("120.00")


def test_discount_comes_off_before_vat():
    invoice = make(InvoiceLine("Kulaklık", Decimal("1"), Decimal("200"), "electronics", Decimal("0.10")))
    assert invoice.total() == Decimal("216.00")


def test_bread_is_taxed_at_the_basic_rate():
    invoice = make(InvoiceLine("Ekmek", Decimal("10"), Decimal("7.50"), "bread"))
    assert invoice.total() == Decimal("75.75")


def test_due_date():
    assert make().due() == date(2026, 10, 31)


def test_ubl_carries_the_total():
    invoice = make(InvoiceLine("Defter", Decimal("2"), Decimal("50.00"), "stationery"))
    assert '<PayableAmount currencyID="TRY">120.00</PayableAmount>' in to_ubl(invoice)
''',
    "tests/test_tax.py": r'''from decimal import Decimal

from ledgerly import tax


def test_standard_rate():
    assert tax.rate_for("electronics") == Decimal("0.20")


def test_books_are_taxed_at_the_standard_rate():
    assert tax.rate_for("books") == Decimal("0.20")


def test_unknown_categories_are_standard():
    assert tax.rate_for("no-such-category") == Decimal("0.20")


def test_exports_are_exempt():
    assert tax.rate_for("books.export") == Decimal("0")


def test_reverse_charge():
    assert tax.reverse_charge(Decimal("120"), "general") == (Decimal("100"), Decimal("20"))


def test_rate_history():
    assert tax.rate_in(2020, "standard") == Decimal("0.18")
''',
    "tests/test_export.py": r'''from datetime import date
from decimal import Decimal

from ledgerly.export import to_csv, to_json
from ledgerly.storage import Entry

ENTRIES = [Entry("E-1", date(2026, 10, 1), "120.01", "Kahve", Decimal("12.50")),
           Entry("E-2", date(2026, 10, 2), "320.01", "Kira, ekim", Decimal("-8000.00"))]


def test_csv_is_comma_separated_without_a_header():
    assert to_csv(ENTRIES) == '2026-10-01,120.01,Kahve,12.50,TRY\n2026-10-02,320.01,"Kira, ekim",-8000.00,TRY\n'


def test_json_keeps_amounts_as_strings():
    assert '"amount": "12.50"' in to_json(ENTRIES)
''',
    "tests/test_currency.py": r'''from datetime import date
from decimal import Decimal

from ledgerly import currency


def test_lira_passes_through():
    assert currency.convert(Decimal("10"), "TRY", date(2026, 10, 1)) == Decimal("10")


def test_dollars_convert_at_the_rate_of_the_day():
    source = currency.RateSource()
    value = currency.convert(Decimal("10"), "USD", date(2026, 10, 1), source=source)
    assert value == Decimal("10") * source.fetch(date(2026, 10, 1), "USD")


def test_minor_units():
    assert currency.minor_units("JPY") == 0
    assert currency.minor_units("KWD") == 3
''',
    "tests/test_importer.py": r'''from ledgerly import importer
from ledgerly.storage import Store


def rows(batch, n):
    return [{"id": f"E-{batch}-{k}", "day": "2026-10-27", "account": "120.01", "amount": "10.00"} for k in range(n)]


class Feed:
    def __init__(self, n=4, timeouts=0):
        self.n, self.timeouts = n, timeouts

    def rows(self, batch_id):
        if self.timeouts:
            self.timeouts -= 1
            raise importer.FeedTimeout("slow")
        yield from rows(batch_id, self.n)


def test_a_batch_is_imported():
    store = Store()
    assert importer.import_batch(Feed(), store, 1) == 4
    assert len(store.all()) == 4


def test_a_timeout_before_the_first_row_is_retried():
    store = Store()
    assert importer.import_batch(Feed(timeouts=1), store, 1) == 4
    assert len(store.all()) == 4


def test_a_batch_that_keeps_timing_out_is_reported():
    assert importer.import_all(Feed(timeouts=9), Store(), [1, 2])["failed"] == [1, 2]
''',
    "tests/test_reports.py": r'''from datetime import date
from decimal import Decimal

from ledgerly import reports
from ledgerly.storage import Entry


def test_reports_run_on_staging():
    assert reports.database() == "ledgerly_stg"


def test_monthly_total():
    entries = [Entry("1", date(2026, 10, 3), "120.01", "a", Decimal("10")),
               Entry("2", date(2026, 9, 30), "120.01", "b", Decimal("5"))]
    assert reports.monthly_total(entries, 2026, 10) == Decimal("10.00")


def test_by_branch():
    entries = [Entry("1", date(2026, 10, 3), "120.01", "a", Decimal("10")),
               Entry("2", date(2026, 10, 4), "600.01", "b", Decimal("5")),
               Entry("3", date(2026, 10, 5), "120.02", "c", Decimal("1"))]
    assert reports.by_branch(entries, 2026, 10) == {"01": Decimal("15.00"), "02": Decimal("1.00")}
''',
    "tests/test_api.py": r'''from ledgerly import api
from ledgerly.storage import Store


def store():
    s = Store()
    s.open_account("120.01", "Alıcılar - Merkez")
    return s


def test_health():
    assert api.handle("GET", "/health", store()) == (200, {"status": "ok"})


def test_get_account():
    assert api.handle("GET", "/accounts/120.01", store()) == (200, {"code": "120.01", "name": "Alıcılar - Merkez"})


def test_unknown_account():
    assert api.handle("GET", "/accounts/999", store()) == (404, {"error": "Account not found"})


def test_unknown_route():
    assert api.handle("GET", "/nope", store())[0] == 404
''',
    "tests/test_accounts.py": r'''from datetime import date
from decimal import Decimal

from ledgerly import accounts
from ledgerly.storage import Entry, Store


def test_balance_sums_the_entries():
    s = Store()
    s.add(Entry("1", date(2026, 10, 1), "120.01", "a", Decimal("10.005")))
    s.add(Entry("2", date(2026, 10, 2), "120.01", "b", Decimal("5")))
    assert accounts.balance(s, "120.01") == Decimal("15.01")


def test_chart_names():
    assert accounts.name("102") == "Bankalar"
    assert accounts.children("102")[:2] == ["102.01", "102.02"]
''',
}


def catalog_py() -> str:
    rows = []
    for i, (key, tr, en, klass, unit) in enumerate(BASES):
        for j, (suffix, vtr, ven) in enumerate(VARIANTS):
            name = f"{key}.{suffix}" if suffix else key
            label_tr, label_en = (f"{tr} ({vtr})", f"{en} ({ven})") if suffix else (tr, en)
            tariff = f"{4800 + i * 7 + j:04d}.{(i * 37 + j * 11) % 100:02d}"
            rows.append(f'    "{name}": ("{label_tr}", "{label_en}", "{"exempt" if suffix == "export" else klass}", '
                        f'"{unit}", {i + 1}, "{tariff}"),')
    return ('"""Product categories: the Turkish label printed on receipts, the English label used in exports, the tax\n'
            'class that picks the VAT rate (see ledgerly.tax), the unit, the receipt group and the customs tariff code.\n'
            '\nA category that is not listed is sold as "general".\n"""\nfrom __future__ import annotations\n\n'
            "# key: (Turkish label, English label, tax class, unit, receipt group, tariff code)\nCATEGORIES = {\n"
            + "\n".join(rows) + "\n}\n\n\n"
            "def entry(category: str) -> tuple:\n    return CATEGORIES.get(category) or CATEGORIES[\"general\"]\n\n\n"
            "def tax_class(category: str) -> str:\n    return entry(category)[2]\n\n\n"
            "def label(category: str, lang: str = \"tr\") -> str:\n    return entry(category)[0 if lang == \"tr\" else 1]\n\n\n"
            "def unit(category: str) -> str:\n    return entry(category)[3]\n\n\n"
            "def in_group(group: int) -> list:\n    \"\"\"The categories printed together on a receipt.\"\"\"\n"
            "    return sorted(k for k, v in CATEGORIES.items() if v[4] == group)\n")


def test_catalog_py() -> str:
    rows = [f'    ("{f"{key}.{suffix}" if suffix else key}", "{"exempt" if suffix == "export" else klass}"),'
            for key, _, _, klass, _ in BASES for suffix, _, _ in VARIANTS]
    return ('"""Every category\'s tax class, as finance signed it off for 0.8."""\nimport pytest\n\n'
            "from ledgerly import catalog\n\nCLASSES = [\n" + "\n".join(rows) + "\n]\n\n\n"
            '@pytest.mark.parametrize("category,klass", CLASSES)\ndef test_tax_class(category, klass):\n'
            "    assert catalog.tax_class(category) == klass\n\n\n"
            "def test_unknown_categories_are_general():\n    assert catalog.label(\"no-such-thing\") == \"Genel\"\n")


def tax_py() -> str:
    history = []
    for year in range(2002, 2027):
        standard, reduced, basic = next(r[1:] for r in reversed(VAT_HISTORY) if r[0] <= year)
        history += [f'    ({year}, "standard"): Decimal("{standard}"),', f'    ({year}, "reduced"): Decimal("{reduced}"),',
                    f'    ({year}, "basic"): Decimal("{basic}"),', f'    ({year}, "exempt"): Decimal("0"),']
    return ('"""VAT.\n\nThe rate depends on the category\'s tax class (see ledgerly.catalog). VAT is computed on the net '
            "amount of each\nline, after its discount, and is not rounded per line: the invoice rounds once, at its "
            'total.\n"""\nfrom __future__ import annotations\n\nfrom decimal import Decimal\n\nfrom . import catalog\n'
            "from .money import ZERO, to_decimal\n\n"
            'RATES = {\n    "standard": Decimal("0.20"),\n    "reduced": Decimal("0.10"),\n    "basic": Decimal("0.01"),\n'
            '    "exempt": Decimal("0"),\n}\n\n'
            "# The rates of past years, for credit notes on old invoices: (year, tax class): rate\n"
            "RATE_HISTORY = {\n" + "\n".join(history) + "\n}\n\n\n"
            'def rate_for(category: str) -> Decimal:\n    """The VAT rate for a category, as a fraction (0.20 for 20%)."""\n'
            "    return RATES[catalog.tax_class(category)]\n\n\n"
            'def rate_in(year: int, klass: str) -> Decimal:\n    """The rate of a tax class in a past year."""\n'
            "    return RATE_HISTORY[(year, klass)]\n\n\n"
            'def tax_for(line) -> Decimal:\n    """VAT on one invoice line, unrounded."""\n'
            "    return line.net() * rate_for(line.category)\n\n\n"
            "def breakdown(lines) -> dict:\n"
            '    """VAT per rate for the block under an invoice\'s lines: {rate: (net, tax)}, highest rate first."""\n'
            "    out = {}\n    for line in lines:\n        rate = rate_for(line.category)\n"
            "        net, tax = out.get(rate, (ZERO, ZERO))\n        out[rate] = (net + line.net(), tax + tax_for(line))\n"
            "    return dict(sorted(out.items(), reverse=True))\n\n\n"
            "def reverse_charge(amount, category: str) -> tuple:\n"
            '    """Split a gross amount into (net, tax) at the category\'s rate."""\n'
            "    gross = to_decimal(amount)\n    net = gross / (1 + rate_for(category))\n    return net, gross - net\n")


def currency_py() -> str:
    table = "\n".join(f'    "{code}": ("{name}", {minor}, "{rate}"),' for code, name, minor, rate in CURRENCIES)
    holidays = "\n".join(f'    "{d}",' for d in HOLIDAYS)
    return ('"""Currency conversion to lira at the central bank\'s rate of the day.\n\n'
            "Each RateSource.fetch is a round trip to the bank's rate service, about 4 ms in production. A month-end run\n"
            "converts thousands of lines, so the fetches add up: see tools/bench.py.\n\"\"\"\n"
            "from __future__ import annotations\n\nfrom datetime import date, timedelta\nfrom decimal import Decimal\n\n"
            "from .money import to_decimal\n\n# code: (name, minor units, lira per unit on the reference day)\n"
            "CURRENCIES = {\n" + table + "\n}\n\n# Days the central bank publishes no rates; the last published rate holds.\n"
            "HOLIDAYS = {\n" + holidays + "\n}\n\n\n"
            "class RateSource:\n    \"\"\"The central bank's rates. `calls` counts the round trips.\"\"\"\n\n"
            "    def __init__(self):\n        self.calls = 0\n\n"
            "    def fetch(self, day: date, code: str) -> Decimal:\n        self.calls += 1\n"
            "        known = CURRENCIES.get(code)\n        if known is None:\n"
            '            return Decimal("1")  # an unknown code goes through at par\n'
            "        drift = Decimal(day.toordinal() % 11 - 5) / Decimal(1000)\n"
            "        return Decimal(known[2]) * (1 + drift)\n\n\nSOURCE = RateSource()\n\n\n"
            "def convert(amount, code: str, day: date, source: RateSource | None = None) -> Decimal:\n"
            '    """`amount` in currency `code` on `day`, in lira, unrounded."""\n    if code == "TRY":\n'
            "        return to_decimal(amount)\n    rate = (source or SOURCE).fetch(day, code)\n"
            "    return to_decimal(amount) * rate\n\n\n"
            "def published(day: date) -> date:\n    \"\"\"The day whose rate holds on `day`: the last working day.\"\"\"\n"
            "    while day.weekday() >= 5 or day.isoformat() in HOLIDAYS:\n        day -= timedelta(days=1)\n"
            "    return day\n\n\n"
            "def minor_units(code: str) -> int:\n    \"\"\"Digits after the decimal point: 2 for most, 0 for yen.\"\"\"\n"
            "    if code not in CURRENCIES:\n        raise KeyError(f\"unknown currency {code}\")\n"
            "    return CURRENCIES[code][1]\n\n\n"
            "def name(code: str) -> str:\n    if code not in CURRENCIES:\n"
            "        raise KeyError(f\"unknown currency {code}\")\n    return CURRENCIES[code][0]\n")


def accounts_py() -> str:
    chart = []
    for code, name in TOP_ACCOUNTS:
        chart.append(f'    "{code}": "{name}",')
        chart += [f'    "{code}.{b:02d}": "{name} - {branch}",' for b, branch in enumerate(BRANCHES, 1)]
    return ('"""The chart of accounts (a short form of the Turkish uniform chart) and account balances.\n\n'
            "The part of a code after the dot is the branch.\n\"\"\"\nfrom __future__ import annotations\n\n"
            "from decimal import Decimal\n\nfrom .money import ZERO, round_cents\n\nCHART = {\n" + "\n".join(chart)
            + "\n}\n\n\ndef name(code: str) -> str:\n    return CHART.get(code, code)\n\n\n"
            "def children(code: str) -> list:\n    return sorted(c for c in CHART if c.startswith(code + \".\"))\n\n\n"
            "def balance(store, account: str) -> Decimal:\n"
            '    """The sum of the account\'s entries in lira, rounded to the cent."""\n'
            "    return round_cents(sum((e.amount for e in store.entries_for(account)), ZERO))\n")


def import_log() -> str:
    """The night of 26 to 27 October: 120 batches from the bank feed, four of them timing out part of the way through.
    The importer reads a timed-out batch again from the start, so the rows before the timeout are stored twice."""
    rnd = random.Random(20261027)
    t = datetime(2026, 10, 27, 2, 0, 0)
    out = []

    def emit(level: str, text: str) -> None:
        nonlocal t
        t += timedelta(milliseconds=rnd.randint(30, 700))
        out.append(f"{t:%Y-%m-%d %H:%M:%S},{t.microsecond // 1000:03d} {level:<7} ledgerly.importer {text}")

    accounts = ["120.01", "120.02", "120.05", "102.01", "102.03", "153.01", "320.01", "320.04", "600.01", "600.02"]
    cuts = {17: 3, 44: 5, 81: 2, 103: 4}
    read = stored = 0
    emit("INFO", "import started: 120 batches from feed bank-tr-03 for 2026-10-26")
    for b in range(1, 121):
        n = 16 + rnd.randint(0, 10)
        rows = [(f"E-0062-{b:04d}-{k:02d}", rnd.choice(accounts), f"{rnd.randint(5, 9000)}.{rnd.randint(0, 99):02d}",
                 rnd.choice(("TRY",) * 8 + ("USD", "EUR"))) for k in range(1, n + 1)]
        attempts = [rows[:cuts[b]], rows] if b in cuts else [rows]
        for a, part in enumerate(attempts):
            for row in part:
                emit("INFO", f"batch {b}: added entry {row[0]} ({row[1]}, {row[2]} {row[3]})")
                stored += 1
            if a < len(attempts) - 1:
                emit("WARNING", f"batch {b}: feed timeout after {len(part)} rows, retrying (1/2)")
        read += n
        emit("INFO", f"batch {b}: done, {n} entries")
    emit("INFO", f"import finished: {read} rows read, {stored} entries stored, 0 batches failed")
    return "\n".join(out) + "\n"


def files() -> dict:
    """Every file of the repository, by path."""
    out = dict(FILES)
    out["ledgerly/importer.py"] += "\n".join(f'    "{code}": ("{name}", "{fmt}"),' for code, name, fmt in BANKS) + "\n}\n"
    out.update({"ledgerly/catalog.py": catalog_py(), "tests/test_catalog.py": test_catalog_py(),
                "ledgerly/tax.py": tax_py(), "ledgerly/currency.py": currency_py(),
                "ledgerly/accounts.py": accounts_py(), "logs/import-2026-10-27.log": import_log()})
    return out


def git(work: Path, *args: str) -> str:
    return subprocess.run([*GIT, *args], cwd=work, check=True, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def materialize(work: Path, commit: bool = True) -> str:
    """Write the repository into `work` and commit it as ledgerly 0.8.3; returns the commit, or "" without git."""
    for rel, text in files().items():
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    if not commit:
        return ""
    git(work, "init", "-q")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "ledgerly 0.8.3")
    return git(work, "rev-parse", "HEAD")


def remove(path: Path) -> None:
    """Delete a run's folder; git keeps its objects read-only on Windows."""
    def retry(func, p, _):
        os.chmod(p, 0o666)
        func(p)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)
