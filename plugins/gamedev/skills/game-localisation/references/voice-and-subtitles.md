# Voice and subtitles

Read this at step 6 before a recording session is booked and before subtitle timing is built. The sources for this area are the engine documentation and the platforms' own accessibility guidance; there is no universal figure for line length or reading speed, so this file sets out the method and leaves the numbers to the targets you adopt and write down.

## Contents

- [Decide the depth per language](#decide-the-depth-per-language)
- [The recording script](#the-recording-script)
- [Timing](#timing)
- [Subtitles as their own deliverable](#subtitles-as-their-own-deliverable)
- [Missing clips and fallbacks](#missing-clips-and-fallbacks)
- [Review checks](#review-checks)

## Decide the depth per language

Voice is the most expensive localisation deliverable, so decide it language by language and write it into the list from step 1. The usual options are original voice with translated subtitles, localised voice with subtitles, and localised voice with the option of original voice. Each affects the build: a localised voice bank is an audio asset set per language, which engines serve by remapping per locale (Godot's resource remapping lists localised voices as a use: <https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>), and its size is a `game-assets` decision.

Let the player choose voice language and subtitle language separately. Keep both in the settings and default each to the player's language where it is available, then to the fallback you chose.

## The recording script

A voice actor performing a translated line sees only what the script gives them. The same missing-context fault that affects a string table affects a recording, with a higher cost to fix. For each line:

| Field | What it holds |
| --- | --- |
| Line key | The same key as the subtitle entry |
| Speaker and listener | Who is talking, and to whom |
| Situation | What has just happened, and what the scene is doing |
| Emotion and effort | Whispering, shouting, in pain, out of breath |
| Previous and next line | Enough to place the line in the exchange |
| Time budget | The duration of the source take, and whether the line is locked to an animation, a lip shape or a cut |
| Reference | The source audio or a capture of the scene |
| Pronunciation | Names, invented words and abbreviations, with a spoken form |
| Variants | Gender or number variants of the line, each as its own take |

Lines that are shouts, grunts and effort sounds are not translated text; record them as audio, keyed like any other line, and do not forget that they exist in the table at all.

## Timing

A translation is rarely the same spoken length as the source line. When it runs longer, it overruns a cut-scene, a mouth animation, a dialogue window or a door that opens on a beat. Handle it in three places.

1. **In translation.** Give the translator the source duration and ask for a line that fits it. A longer line is allowed only where the scene can stretch.
2. **In the scene.** Drive animations and cuts from the audio clip's length wherever possible, so a longer line extends the scene rather than breaking it. For lines locked to the picture, record to picture.
3. **In the check.** Compare each localised clip's length with its slot automatically, as part of the build. A clip outside its slot is a defect before anyone listens.

Where lip-sync matters, say so per line, and decide before recording whether lip movement is authored per language or generated from the audio, since it changes what the recording session must deliver.

## Subtitles as their own deliverable

A subtitle is a string with timing. The text belongs to the subtitle language; the timing belongs to the audio it is shown over.

- **Key the cue timing to the voice clip that is playing,** not to the subtitle entry. Voice and subtitle languages are chosen separately, so one German subtitle may sit over German, English or Japanese audio of three different lengths; timing stored on the entry can match only one of them. Keep the timing with the scene or the clip (or keyed by the voice and subtitle pair), and treat the subtitle's reading time as a constraint on its text.
- **Derive display time from a reading-speed target you set per language** and from the clip length, then let a script flag any subtitle that needs more time than any voice clip it can be paired with provides. Do not adopt a number from a forum post; take it from the accessibility guidance of your platforms or a recognised subtitle standard, and write the source next to the value.
- **Set line-length limits per language and script,** as pixel widths on the real font. Languages without spaces, and right-to-left languages, break differently; see `scripts-fonts-and-rtl.md`.
- **Plan for the subtitle box in pseudo-localisation,** so that an expanded string shows whether the box wraps, grows or clips.
- **Include speaker names and non-speech information** (sounds that matter to the story) as entries, since subtitles carry them for players who rely on them. The accessibility treatment of subtitle size, background and speaker colour belongs to `accessibility-audit`.
- **Give a foreign-language line inside a scene its own subtitle entry,** so each language can decide whether to translate it or leave it.

## Missing clips and fallbacks

Decide in advance what plays when a line has no clip for the chosen voice language: the source-language clip with a subtitle, silence with a subtitle, or a visible key. Make the fallback the first of these in a shipped build, and make the visible key the behaviour of a development build so the gap is found. Log every fallback to a report; a silent fallback is how an untranslated voice bank ships unnoticed.

## Review checks

- Every voiced line has a subtitle entry in every shipped subtitle language, by a script rather than by eye.
- Every clip fits its slot, by a script.
- A native speaker plays each language and notes lines that sound wrong in the scene, as in `linguistic-qa.md`.
- The text of a subtitle matches what the actor says. A last-minute change to the recording that is not reflected in the table is the common cause of a mismatch, so route changes through the table.
