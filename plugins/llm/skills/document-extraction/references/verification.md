# Verifying extracted values

Read this at step 5, when you build the checks that decide what is accepted, and again when you measure the pipeline. A value is accepted because it passed checks that do not rely on the reader that produced it. How confident a model sounds is not one of them.

## Contents

- [Order of checks](#order-of-checks)
- [Arithmetic cross-checks](#arithmetic-cross-checks)
- [Format and plausibility checks](#format-and-plausibility-checks)
- [The second independent extraction](#the-second-independent-extraction)
- [What gets held](#what-gets-held)
- [Measuring the pipeline](#measuring-the-pipeline)

## Order of checks

Run the cheap deterministic checks first, then the second reading, and record which checks each value passed. A value that passed only a format check has not been verified; it has been shown to be well-formed.

1. Arithmetic cross-checks.
2. Format and plausibility checks.
3. A second independent extraction, compared field by field.
4. Human review of whatever the first three held.

## Arithmetic cross-checks

The document contains its own redundancy, and most financial documents carry plenty. Use every relation the page states.

- Each line: quantity times unit price equals the line amount.
- The line amounts sum to the printed subtotal.
- Subtotal plus tax, tip and shipping, minus discount, equals the total.
- Tax divided by the taxable amount matches the printed rate, to within rounding.
- A column of a table sums to a printed totals row; the rows of a statement walk from the opening balance to the closing balance.
- Page totals sum to a document total on a multi-page invoice.

Compare with exact decimal arithmetic and zero tolerance by default. A one-cent difference is a misreading until the document shows a rounding rule (a printed rounding line, or tax computed per line), and a tolerance chosen to make a check pass hides the misreadings the check exists to catch. When a document does round, model the rule explicitly and write it into the check.

```python
import re
from decimal import Decimal

# A normalised value: an optional minus, digits, and at most one "." with digits after it.
NORMALISED = re.compile(r"-?\d+(?:\.\d+)?")
# At most one currency marker before or after the number in `raw`, such as "EUR " or
# " USD", and nothing else: a trailing "-" or "(" is sign syntax for money() to reject.
MARKED = re.compile(r"(?:([A-Z]{3}|[$€£¥])\s*)?(.*?)(?:\s*([A-Z]{3}|[$€£¥]))?")
# Symbols that name exactly one currency. "$", "£" and "¥" each name several ("¥" is
# both yen and yuan), so the document's own mapping has to resolve them.
SYMBOLS = {"€": "EUR"}


def printed(field, decimal_sep=".", symbols=SYMBOLS):
    """The amount the record's ``raw`` text shows, or None when it is unparseable or its
    currency marker disagrees with the record's ``currency``."""
    text, sign = field["raw"].strip(), ""
    if text[:1] in ("-", "+"):  # "-€5.00"
        sign, text = text[0], text[1:]
    if text.startswith("(") and text.endswith(")"):  # "(€5.00)", "(5.00 EUR)"
        if sign:
            return None
        sign, text = "-", text[1:-1].strip()
    marked = MARKED.fullmatch(text)
    if marked is None:  # no single-line amount, such as digits split by a newline
        return None
    lead, number, trail = marked.groups()
    if lead and trail:
        return None
    marker = lead or trail
    if marker and symbols.get(marker, marker) != field.get("currency"):
        return None  # "$5.00" on a record that says EUR is a misread currency
    return money(sign + number, decimal_sep)


def money(raw, decimal_sep="."):
    """Parse a printed amount. The separator comes from the document, not a guess.

    Grouping must be well formed (``1,234`` but not ``1,,234``, ``12,34`` or ``123,``), and
    the sign is one leading ``-``/``+`` or one pair of parentheses; anything else is None.
    """
    thousands = "," if decimal_sep == "." else "."
    t, d = re.escape(thousands), re.escape(decimal_sep)
    body = rf"(?:\d{{1,3}}(?:{t}\d{{3}})+|\d+)(?:{d}\d+)?"
    # A space inside the number is rejected, not deleted: "12 34" is a misread, not 1234.
    match = re.fullmatch(rf"([-+]?)({body})|\(({body})\)", raw.strip())
    if match is None:
        return None
    sign, signed_digits, bracketed = match.groups()
    text = (signed_digits or bracketed).replace(thousands, "").replace(decimal_sep, ".")
    value = Decimal(text)
    return -value if sign == "-" or bracketed is not None else value


def num(field, decimal_sep=".", magnitude=False, symbols=SYMBOLS):
    """A field record's normalised value as a Decimal; None when absent, malformed, with
    no printed ``raw`` text, or when it disagrees with that text."""
    if not field or not isinstance(field.get("value"), str):
        return None
    if NORMALISED.fullmatch(field["value"]) is None:
        return None  # normalised values carry no grouping mark and no other sign syntax
    value = Decimal(field["value"])
    raw = field.get("raw")
    if not isinstance(raw, str):
        return None  # a value with no transcription behind it is not evidence
    shown = printed(field, decimal_sep, symbols)
    if shown is None or (abs(shown) if magnitude else shown) != value:
        return None  # a normaliser that changed the number is a misreading, not a value
    return value


def charge(field, decimal_sep=".", magnitude=False, symbols=SYMBOLS):
    """A total component: zero when the document prints none, None when unknown.

    A charge the page does not contain adds nothing to the total, so a field recorded as
    ``absent`` counts as zero. One that is printed but could not be read, or a record the
    extraction omitted altogether, leaves the total unchecked: an omitted record says
    nothing about whether the page has the charge.
    """
    if field and field.get("value") is None and field.get("confidence_basis") == "absent":
        return Decimal(0)
    return num(field, decimal_sep, magnitude, symbols)


def check_totals(doc, decimal_sep=".", symbols=SYMBOLS):
    """Return the failed checks; an empty list means the arithmetic closes.

    ``doc`` holds field records as extraction-schema.md defines them, with amounts as
    decimal strings, so every value goes through ``num`` before any arithmetic.
    """
    failures = []
    lines = doc.get("line_items") or []
    for i, item in enumerate(lines):
        qty, unit, amount = (
            num(item.get(k), decimal_sep, symbols=symbols)
            for k in ("quantity", "unit_price", "amount")
        )
        if None in (qty, unit, amount):
            failures.append(f"line {i}: not checkable, an operand is missing")
        elif qty * unit != amount:
            failures.append(f"line {i}: {qty} x {unit} != {amount}")
    amounts = [num(item.get("amount"), decimal_sep, symbols=symbols) for item in lines]
    subtotal, total = (
        num(doc.get("subtotal"), decimal_sep, symbols=symbols),
        num(doc.get("total"), decimal_sep, symbols=symbols),
    )
    if None in amounts:
        failures.append("a line amount is missing, so the subtotal cannot be checked")
    elif not lines:
        failures.append("subtotal not checkable: no line items")
    elif subtotal is None:
        failures.append("subtotal not checkable: it is missing or unreadable")
    elif sum(amounts) != subtotal:
        failures.append(f"lines sum to {sum(amounts)}, subtotal printed {subtotal}")
    # a discount is stored as a magnitude, so -5.00 or (5.00) printed reconciles with 5.00
    parts = {
        k: charge(doc.get(k), decimal_sep, k == "discount", symbols)
        for k in ("tax", "tip", "shipping", "discount")
    }
    unread = [k for k, v in parts.items() if v is None]
    if subtotal is None or total is None or unread:
        missing = unread or ["subtotal or total"]
        failures.append(f"total not checkable: {', '.join(missing)} missing or unreadable")
    else:
        # a discount printed as -5.00 or (5.00) still takes 5.00 off
        built = subtotal + parts["tax"] + parts["tip"] + parts["shipping"] - abs(parts["discount"])
        if built != total:
            failures.append(f"components give {built}, total printed {total}")
    return failures
```

A check that cannot run because an input is null is itself a result: record it as `not checkable`, never as passed. A document with only a total and no lines gets no arithmetic assurance, and the second reading has to carry it.

## Format and plausibility checks

| Value | Check |
| --- | --- |
| Date | Parses under the document's own convention; not in the future for a past event; within the range the batch could contain. An ambiguous day and month is held, not guessed. |
| Currency and separators | One convention per document; a mix of `1,234.56` and `1.234,56` on one page means a misread. |
| Identifier with a check digit | The check digit validates (IBAN, Luhn-checked card and account numbers). A failure is a misread of the number, and the fix is a human reading it, not a repair by the model. |
| Identifier with a known shape | Length and character set for its type; flag a letter O where only digits are valid, and the reverse. Confusions to look for: 0 and O, 1 and l, 5 and S, 8 and B. |
| Enumerations | Value is in the permitted set; a near-match is held, not snapped to the nearest. |

## The second independent extraction

Independence is the point, so choose a reader whose failures are not correlated with the first.

- A vision model and an OCR engine fail differently: a vision model can repair a digit it cannot make out into a plausible one, while OCR tends to confuse look-alike characters without inventing a value. Where the file is a born-digital PDF, the text layer is a third, exact reader, and a disagreement with it points first at the vision reader.
- Two calls to the same model on the same image share the same weaknesses. If a second model is not available, change what the model sees: a tighter crop of the field's region at higher scale, or a different strip boundary, and a prompt that asks only for that field.
- The second reader never sees the first reader's answer.

Compare after normalising both values with the same function. Equal normalised values and agreeing regions are agreement. Anything else on a numeric, date or identifier field is a disagreement.

Send a disagreement to a human with three things on one screen: the crop of the source region, the first candidate and the second candidate. Do not resolve it with a third call, a vote or a preference for the more confident reader. Two readers can share a systematic error, and a majority of them only makes it look settled. Disagreement on a free-text field such as a merchant name or a description can be accepted with the more complete reading when the values are equal after normalisation; it is numeric, date and identifier fields where a wrong value does damage.

## What gets held

A value goes to review when any of these is true: a check failed, a check could not run on a field that matters, the readers disagree, the field is handwritten, the region is under the size at which the model is documented to be unreliable (see `references/preprocessing-and-limits.md`), or the confidence is `low`. Return the held list with the document. A document with held fields is not complete, and the caller has to be able to tell.

## Measuring the pipeline

Do not judge the pipeline by how its output looks. Build a labelled set of real documents from the population you will process, including the worst scans, the folded receipts and the unfamiliar layouts, label the fields by hand, and report per field type:

- Exact-match accuracy of the final accepted values.
- The held rate, since a pipeline that holds everything is accurate and useless.
- Wrong while accepted: accepted values that are wrong, which is the number that decides whether the pipeline can run unattended. Read each one, and decide which check should have caught it.
- Whether each check earns its place: how many errors each caught that the others did not.

Published benchmark scores for a model on public document sets do not substitute for this. Your documents differ from theirs, and a score transfers to your population only as far as the populations match. Rerun the labelled set when the model, the preprocessing or the prompt changes.
