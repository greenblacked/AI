# Plausible data

Read this at step 5. The data in a mock is read as a claim about the product and, often,
about its customers. It has to be invented, so nobody's information is published, and
plausible, so the product looks used.

## Contents

- Where each kind of value comes from
- Writing the data set
- The consistency check
- Charts

## Where each kind of value comes from

| Value | Draw from | Avoid |
| --- | --- | --- |
| People's names | An invented list, varied in origin and length, first name and surname that do not belong to a public figure together | Real customers, colleagues, famous names, joke names |
| Companies | Invented names in the product's market, or the user's own company | Real companies, especially competitors and customers, unless they have agreed to appear |
| Email addresses | A domain reserved for documentation, such as `example.com`, `example.org` or a name under `.example` | A real-looking domain someone may own |
| Phone numbers | A range set aside for fiction or documentation in the shown country, such as 555-0100 to 555-0199 in North America; confirm the range for any other country before using it | Any number someone could dial and reach |
| Addresses | A street name that is generic, without a house number that resolves to a real building | A real address, including the office's own |
| Avatars | Initials on the product's avatar colours, or illustrations the user owns | Photographs of real people, unless licensed for this use with the person's consent |
| Money | The product's real currency formatting for one locale, with amounts that are not round | Mixed currencies, figures that look like a real customer's invoice |
| Dates and times | A window close to the present with weekday names that match the dates | A visible year when the visual should last; dates in an order the product would never show |
| IDs and keys | The product's real format with obviously invented contents | Anything copied from a real account, and anything shaped like a live secret, even a revoked one |

## Writing the data set

1. Write the data once, as a small table or fixture, before placing it. Every value in the
   mock comes from that one source, so a change appears everywhere it should.
2. Make it look used. Real lists have an item that is overdue, a name longer than the
   column, a status that is not the happy one. One such imperfection in the context tier
   makes the focus more believable; more than one draws attention away from it.
3. Match the product's vocabulary: its status names, its units, its labels for empty and
   error states.
4. Keep the claim honest. A figure that reads as an outcome a customer achieved, such as a
   percentage gain in revenue, is a performance claim even when invented. Use a neutral
   figure, or label the visual as illustrative where the page allows.

## The consistency check

Before the mock goes to step 6 of the skill, check the data set against itself:

- Rows sum to the total shown; a percentage matches its count and its denominator.
- A count in a badge or a tab matches the number of items it claims.
- Dates are in the order the product sorts them, and relative times ("2 hours ago") agree
  with absolute ones on the same screen.
- The same person, company or amount is spelled and formatted the same way every time it
  appears.
- Nothing in the data set is a real person, company, address or credential: search for any
  name you are unsure of.

## Charts

- Generate the series from a rule with small variations rather than drawing a smooth curve,
  so it has the irregularity real data has.
- Axis labels and units match the product's own charts. Remove axes entirely if the chart
  is in the periphery tier.
- A chart in the focus tier states one thing, such as a value crossing a threshold. A chart
  that shows everything is in the wrong tier.
