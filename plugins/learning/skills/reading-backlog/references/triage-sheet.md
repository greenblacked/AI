# Triage sheet

Read at steps 1 to 3.

## The sheet

One row per item, in a spreadsheet or a plain table.

```markdown
| Source | Title | Format | Saved | Age (days) | Over 90? | Task this quarter | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Read-later | Queue design notes | Article | 2026-09-02 | 50 | no | Choose a queue for billing rewrite | Keep |
| Shelf | Designing Data-Intensive Applications | Book | 2025-11-01 | 355 | yes | none | Archive |
```

Verdicts: keep, archive. Everything over 90 days is archive without review. Everything under 90 days needs a task, or it is archived too.

## Where the items live

| Source | How to get the list |
| --- | --- |
| Read-later app | Use its export (most offer CSV or HTML) and keep the saved date column |
| Browser bookmarks | Export bookmarks to an HTML file; the add date is included in most browsers |
| Open tabs | Close them to a bookmark folder and mark their age unknown, so they count as older than 90 days; count that folder |
| Files and PDFs | List the folder with modified dates, for example `ls -lt` sorted by time |
| Books | Walk the shelf and the e-reader; use the purchase date if you have it, otherwise treat as old |
| Starred emails | Search the starred label and note the received date |

Where the date is missing, treat the item as older than 90 days. Guessing young is how the pile survives.

## Writing the task line

A task line names a piece of work or a decision with an end: a project, a talk, a purchase, a review. It is something you could be asked about.

| Weak | Strong |
| --- | --- |
| Interesting for later | Decide between two queue designs by 14 November |
| Should know this | Prepare the talk on incident reviews for the March meetup |
| Good author | none, so archive |

## The allowance

Keep one named interest slot, such as one book chosen for pleasure, outside the task rule. It counts toward the three open items.

## Archive layout

One folder, tag or list called Archive with the year and quarter. Do not sort inside it. Search covers the retrieval, and a task that needs a topic later is the time to look.
