# Portion estimation from photos

## Scale anchors (find one before estimating anything)

Look for a known-size object in the frame and calibrate everything against it:

| Anchor | Typical size |
| --- | --- |
| Dinner plate | 26-28 cm diameter |
| Side/salad plate | 18-20 cm |
| Standard fork | 18-19 cm long |
| Tablespoon | 15 ml bowl, ~20 cm long |
| Soda can | 12 cm tall, 6.6 cm diameter |
| Smartphone | ~15 x 7 cm |
| Credit card | 8.6 x 5.4 cm |
| Coffee mug | 250-350 ml |
| Slice of sandwich bread | 11-12 cm square |
| Adult hand in frame | palm ~10 cm wide |

If no anchor exists, assume a 27 cm dinner plate and say so.

## Hand-unit system (for stating assumptions users can verify)

| Unit | Approx. equivalent | Typical use |
| --- | --- | --- |
| Palm (no fingers) | 85-120g cooked meat/fish | protein portions |
| Fist | ~1 cup / 150-200g | rice, pasta, potatoes, fruit |
| Cupped hand | ~30-40g | nuts, chips, granola |
| Thumb | ~1 tbsp / 15g | oil, butter, nut butter, cheese |
| Thumb tip | ~1 tsp / 5g | sugar, mayo |

## Reading volume from a photo

- **Height matters more than it looks.** A mounded fist of rice vs a flat spread can differ 2x. Look at shadows and how food sits against fork tines or plate rim.
- **Bowls hide volume.** A "small" bowl of pasta is often 350-450g cooked. Assume bowls are fuller than they appear; estimate from bowl diameter x apparent fill depth.
- **Coverage fraction**: estimate what fraction of the plate each item covers, then multiply by typical density per plate-area (a dinner-plate fully covered 2 cm deep in rice ≈ 400-500g).
- **Stacked/layered foods** (lasagna, burgers, sandwiches): count layers, estimate per layer.

## Cooking method multipliers (apply to the base food)

| Method | Effect |
| --- | --- |
| Grilled/steamed/boiled | baseline |
| Pan-fried | +1 to 2 tsp absorbed oil per portion (+40-90 kcal) |
| Deep-fried | 1.5-2.5x the raw item's calories (batter + oil) |
| Breaded + fried | add ~30-40% for breading, then frying oil |
| Roasted vegetables | +1 tbsp oil per 2 servings typical |
| Restaurant sauté | assume 1-2 tbsp oil/butter per dish (+120-240 kcal) |

## Cooked vs raw weight

- Rice/pasta/grains: cooked weight ≈ 2.5-3x raw. 100g raw rice ≈ 280-300g cooked ≈ 360 kcal either way.
- Meat: loses ~25% weight cooking. 100g cooked chicken breast ≈ 130g raw.
- Vegetables: lose 10-50% water depending on method; calorie impact is small.

## Context adjustments

- **Restaurant meal**: portions typically 20-40% larger than home, more fat. Bias the estimate up and widen the range.
- **Fast food with visible branding**: use published values for that chain's items when identifiable; they're far more accurate than visual estimation.
- **Homemade**: ask or assume moderate oil use (1 tbsp per dish).
- **Partially eaten plate**: estimate the original portion, then multiply by fraction remaining eaten.

## Uncertainty communication

Always output a range. Width guidance:

- Simple, clearly visible items (an apple, packaged yogurt): ±10%
- Mixed plate, visible components: ±20%
- Casseroles, curries, soups, dressed salads: ±30%
- Unknown restaurant dish with sauce: ±35% and say the sauce is the wildcard
