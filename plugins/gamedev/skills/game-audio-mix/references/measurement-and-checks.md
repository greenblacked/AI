# Measurement and checks

## Contents

capture routine, results table, ducking starting points, listening checklist, interpreting the numbers

## Capture routine

1. Fix the build and the settings: default volume sliders, the output mode under test, no OS-level enhancements, and the same master volume as shipped.
2. Run the reference route from a clean start, from a scripted input replay where possible.
3. Record the final mix after the master bus, not before. A capture taken before the limiter or the night-mode compressor measures a signal nobody hears.
4. Save one file per scene per output mode, named with the build number.
5. Measure each with the ffmpeg command in the skill, and record the output.

## Results table

| Build | Mode | Scene | Integrated LUFS | Loudness range | True peak dBTP | Within target | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 412 | TV | Combat | | | | | |

A long scene with silence measures lower than a short loud one; measure each scene over a representative duration and note it. If the platform guidance specifies gating or a measurement window, follow it.

## Ducking starting points

These are first guesses to be adjusted by listening and metering, not standards.

| Setting | Starting point | Symptom if wrong |
| --- | --- | --- |
| Attack | A few milliseconds to tens | Too slow: first syllable lost under music |
| Release | Several hundred milliseconds | Too fast: music pumps between words |
| Depth | A few decibels | Too deep: music vanishes and returns audibly |
| Key source | The voice bus | Wrong key: ducks on silence or on a non-speech bus |
| Targets | Music and ambience | Ducking sfx hides gameplay cues |

## Listening checklist

- Dialogue scene at full combat load, subtitles off, on laptop speakers.
- The same on headphones and on the television at a normal listening level.
- The same in night or handheld mode.
- Quiet exploration: can you hear the ambience without it being a hiss at high volume?
- Heavy combat: is any single effect piercing, and does the limiter engage frequently?
- Transitions: cutscene into gameplay, menu into game, pause and resume. Look for sudden jumps in level.
- Settings extremes: sliders at zero and at maximum do what the label says.

## Interpreting the numbers

- Integrated loudness above target in combat only: the effects bus is too hot. Lower the category with the loudest peaks, not master.
- Integrated loudness fine but true peak above the limit: a few transients. Check the limiter's ceiling and look for inter-sample peaks, which a true-peak meter finds and a sample-peak meter misses.
- Large loudness range in a scene: acceptable in a cinematic, a problem on handheld. That is what the compressor mode is for.
- Dialogue scene measures well but fails listening: the number says level, not intelligibility. Fix the spectral competition.
