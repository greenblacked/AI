# The event table

A worked table for a small action game. The header row is required; column order is not.

```csv
id,trigger,variants,bus,priority,max_instances,steal,duck_group,spatial
sfx.player.footstep,Player foot lands while moving,6 by surface; random without immediate repeat,sfx,20,4,quietest,none,3d
sfx.weapon.rifle_fire,Rifle shot leaves the barrel,3; round robin,sfx,60,8,oldest,none,3d
sfx.impact.ricochet,Bullet hits hard surface without hurting anything,4; random,sfx,10,3,none,none,3d
vo.guard.alert,Guard first sees the player,5; one per line index,voice,90,2,lowest-priority,voice,3d
ui.menu.confirm,Player confirms a menu choice,1,ui,50,1,oldest,none,2d
mus.combat.start,Combat state begins,2; by intensity,music,40,1,none,none,2d
```

## Choosing each value

**Priority.** Pick a handful of bands and keep to them, such as 0 to 30 ambience and incidental, 31 to 60 interface and music, 61 to 80 gameplay effects, 81 to 100 dialogue and critical warnings. Exact numbers matter less than the ordering; the point is that the order is written down and reviewable.

**Max instances.** Count the worst legitimate frame, not the average. A sound that fires in a crowd needs a lower cap than the crowd, because the extra copies blur into one. A one-shot with a long tail needs the tail counted: the instance is alive until it ends, not until it starts.

**Steal.** `oldest` keeps the newest information in the player's ears. `quietest` hides the loss best for distant, repeated sounds. `lowest-priority` is for events that share a limit with something more important. `none` drops the new request, which suits a sound whose repeats add nothing.

**Duck group.** Name the group only; how far and how fast it ducks belongs to `game-audio-mix`. Write `none` rather than leaving it blank, so a blank means unfinished.

**Spatial.** `3d` events need an emitter; check the trigger actually has one. A `3d` event fired from a menu has no position, and a `2d` event on a world object will not pan.

## Rows teams forget

- Loop start and loop stop as separate events or an explicit stop, so a loop cannot play forever.
- Pause, resume and focus loss: what stops, what continues.
- Failure and refusal sounds for interface actions.
- The silence cases: a mute-all or accessibility option that needs a visual substitute.
- Events fired by animation notifies or data files, which code searches miss; the script scans `.json` and `.tscn` by default, and any other data format only if you pass it with `--ext`, which replaces the default list rather than adding to it.

## What the script cannot know

It reads string literals. It does not know whether a call is reachable, whether the variants exist in the middleware, or whether the bus name matches a real bus. Check the last two against the middleware project export when it offers one, and treat a clean run as "table and code agree", not "the audio works".
