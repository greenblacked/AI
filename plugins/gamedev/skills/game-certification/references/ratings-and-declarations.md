# Age ratings, content questionnaires and data declarations

Read this at steps 3 and 4. These are the parts of a submission that are answered by a person filling in a form, checked against a build, and revocable after launch if the two disagree.

## Contents

- [Start the rating first](#start-the-rating-first)
- [Rating routes by territory](#rating-routes-by-territory)
- [Questionnaire answers that get under-reported](#questionnaire-answers-that-get-under-reported)
- [Paid random items](#paid-random-items)
- [The SDK inventory](#the-sdk-inventory)
- [Privacy and data declarations](#privacy-and-data-declarations)
- [Children's audiences](#childrens-audiences)
- [Keeping the declarations true after launch](#keeping-the-declarations-true-after-launch)

## Start the rating first

The rating gates the store listing on most platforms, it costs nothing to begin, and the automated route returns a result almost immediately — so there is no reason for it to be late, and it is late constantly. Start it as soon as the content is known, not when the build is done. If an answer would change later, the questionnaire can be retaken; an unstarted one cannot.

## Rating routes by territory

| Route | Covers | Shape |
| --- | --- | --- |
| IARC questionnaire | ESRB, PEGI, USK, ClassInd, ACB, GRAC in one pass, for digital releases on participating storefronts including Google Play, the Microsoft Store and the Nintendo eShop | Free, automated, near-immediate, retakeable |
| ESRB direct | Physical releases in North America | A submission with a fee and materials to prepare |
| CERO | Japan | Its own submission, fee and timeline |
| USK | Physical media in Germany, where a rating is a legal requirement | Its own submission and timeline |
| Storefront's own scheme | Steam and other PC storefronts that use self-declared content descriptors rather than a board rating | A form on the storefront, checked against the build |
| National regimes | Territories that require their own approval rather than a board rating | Start early, or exclude the territory deliberately |

Decide the territory list before the ratings, because the list is what decides how many of these you are doing.

## Questionnaire answers that get under-reported

Not from dishonesty, usually — the questions ask about categories the team does not think of its game in:

- **Gambling and simulated gambling.** Includes mechanics with no real-money stake, and includes loot boxes on most forms.
- **In-game purchases, and whether randomised items are among them.** Two separate questions on several forms, and the second one is the one that is missed.
- **User-to-user interaction.** Text chat, voice, emotes, asynchronous messages, and player names visible to others. A leaderboard carrying player-supplied names is interaction.
- **User-generated content.** Level editors, custom art, custom names, and anything shareable between players.
- **Links out of the game.** A store link, a social link, a Discord invite, or a web view — content you do not control that the rating will assume the worst about.
- **Content in the extremes rather than the average.** The questionnaire asks about the most extreme instance, not the tone of the game. One scene decides the answer.
- **Content behind a rare unlock, a secret, or a dev menu reachable in the retail build.** It is in the game.

Where an answer is genuinely borderline, ask rather than guess, and record the answer you were given. A rating obtained on wrong answers is revocable after launch, and a storefront removal is worse than the higher rating would have been.

## Paid random items

Separate from the rating, several storefronts require the odds of paid randomised items to be disclosed in the game or on the store page, in a stated form and place. Some platforms require it even when the randomised item is bought with an intermediate currency, which is exactly the structure teams assume is exempt.

Treat this as a build requirement rather than a metadata one when the disclosure has to appear in-game, because it then has a UI, a localisation and a data source that have to exist before content lock.

## The SDK inventory

Every declaration in the next section is written from this table, and the table is built by looking at the build rather than by asking the team:

| SDK | Version | Collects by default | Configured off? | Privacy manifest present? |
| --- | --- | --- | --- | --- |
| Analytics | | Device id, session, coarse location | | |
| Crash reporting | | Device model, OS, stack, sometimes user id | | |
| Ads or mediation | | Advertising identifier, often more | | |
| Attribution | | Advertising identifier, install referrer | | |
| Engine telemetry | | Varies, and is on by default in some engines | | |
| Login or social | | Account identifiers, friend lists | | |

Two things this catches that nothing else does: a library collecting an advertising identifier nobody asked for, and an engine's own analytics left enabled in a project template. Both make an otherwise honest declaration false.

## Privacy and data declarations

- **Apple.** App Privacy details describing what is collected, by whom, and whether it is linked to the user or used to track. App Tracking Transparency is required when tracking happens at all, and the prompt's presence has to match the declaration. Bundled SDKs need privacy manifests, and certain APIs need a declared reason; a missing manifest rejects at upload rather than in review.
- **Google Play.** The Data safety form, which is checked against observed app behaviour. It has to cover third-party SDKs, not only your own code.
- **Consoles.** Platform-specific declarations covering data collection, online features, and any communication between players.
- **Privacy policy.** Mandatory once anything is collected, at a URL that resolves and describes this game. A link to a company page that never mentions the product is a common rejection.
- **Regional law.** GDPR consent for anything non-essential in the EU, and the equivalent regimes elsewhere. A consent prompt that the build does not actually honour is worse than no prompt.

## Children's audiences

If the game is directed at children, or has a mixed audience:

- Declare it accurately on each store's family or children's programme.
- Advertising and analytics restrictions become hard requirements rather than settings, and an ads SDK left in place is both a policy breach and a legal exposure under COPPA and its regional equivalents.
- Personalised advertising, behavioural tracking and advertising identifiers are usually prohibited for the child-directed portion of the audience.
- Any interaction feature — chat, UGC, links out — is held to a stricter standard, and several will need to be disabled for that audience rather than moderated.

This is the one declaration whose consequences outlast the store, which is why it is the one to escalate rather than to guess at.

## Keeping the declarations true after launch

A declaration is a statement about the current build, and a patch can falsify it silently:

- Adding or updating an SDK changes what is collected. Re-check the inventory on any dependency change, which is where `dependency-triage` and this file meet.
- Adding chat, UGC, a link out or a randomised purchase changes the rating answers, and the questionnaire has to be retaken before that patch ships.
- Enabling a previously dark monetisation feature changes both. It is a submission concern even when the code was already there.

Put the inventory and the questionnaire answers in the repository next to the release checklist, so the diff that adds an SDK sits next to the declaration it invalidates.
