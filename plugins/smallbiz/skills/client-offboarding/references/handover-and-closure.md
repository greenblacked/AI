# Handover and closure

## Contents

- Acceptance message
- Handover pack template
- Access audit checklist
- Warranty wording
- Closure record

## Acceptance message

Subject: [Project] - please confirm acceptance

Hello [name], the deliverables listed in the statement of work are complete: [list].
Please reply "accepted", or list anything you consider outstanding, by [date]. On
acceptance the [N]-day warranty window starts and the final invoice is issued. Source
files and credentials are released on payment of that invoice.

If the agreement has a deemed-acceptance clause, add: "Under clause [x], work not
queried by [date] is treated as accepted."

## Handover pack template

1. What was built: one paragraph and a list of components.
2. Where it lives: repository URLs, hosting, environments, storage, with the account
   owner for each.
3. How to run it: prerequisites, build, deploy and rollback steps written as commands
   someone can paste, tested on a clean machine or account.
4. How to edit it: where content, configuration and secrets are changed.
5. Recurring items: domain, hosting, licences, subscriptions, certificates. Columns:
   item, supplier, account holder, payment card holder, renewal date, action.
6. Known issues: defects and limits you are aware of, each with a severity.
7. Contacts: who at the client owns each area; who to call at each supplier.
8. What is not included: anything quoted but not built.

## Access audit checklist

Tick each category, then list the specific accounts under it.

- Hosting, cloud and server consoles
- Source repositories, CI and package registries
- Domain registrar and DNS
- Analytics, tag manager, ad and search consoles
- Email, chat and project-tool workspaces
- Password-manager vaults and shared drives
- API keys, tokens, webhooks and service accounts
- SSH keys, VPN profiles, certificates
- Test and staging accounts, seeded users
- Devices or numbers used to receive two-factor codes for the client's accounts

| Account | Granted by | Reaches | Action (hand over / remove self / delete) | Done on |
| --- | --- | --- | --- | --- |

## Warranty wording

"For [N] days from acceptance on [date], until [end date], I will fix defects where the
delivered work does not match the accepted scope. Report one by [channel] with steps to
reproduce. New features, changes to scope, third-party outages and changes made by others
after handover are outside it and quoted separately."

## Closure record

Use the layout in the skill's hand-back block. Keep it to one page and store it at the
top of the archived project folder. Update the "Open items" line until it is empty, then
date the record closed.
