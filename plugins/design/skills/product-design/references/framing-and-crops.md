# Framing and crops

Read this at step 3, once the claim and the slot are written down. The frame tells the
viewer what kind of product this is; the crop tells them there is more of it than they can
see.

## Contents

- Destinations
- Frame types
- Cropping rules
- Composition inside the frame

## Destinations

Measure the real slot in the page when one exists; the figures below are starting points
for when it does not, and a platform's current guidance wins over this table for a social
card.

| Destination | Typical shape | Where the focus sits | Notes |
| --- | --- | --- | --- |
| Landing-page hero | Wide, often about 16:10 or 16:9, or a tall crop beside a headline | Toward the side away from the headline, above the fold line on a laptop viewport | Seen first and briefly; one region legible, the rest structure |
| Feature card in a grid | Whatever the cell is, often near square | The centre third of the card | Shown beside other cards, so its tier-one region is small; zoom in hard |
| Docs page | The content column's width, often 640 to 800 CSS pixels wide | Where the surrounding text points | A docs page that teaches a task needs a real screenshot instead; hand that to `screenshot-rot` |
| Changelog entry | Column width, short height | The changed control or value | Show the change, not the whole screen it lives on |
| Social card | Commonly 1200 by 630 pixels, about 1.91:1 | Centre, clear of the edges that platforms crop or overlay | Viewed at thumbnail size in a feed, so the legibility floor applies to the thumbnail |

When one visual ships to several destinations, design for the smallest and crop outward
for the larger ones, rather than shrinking the largest. A crop built for a hero and then
shrunk into a card loses its focus to illegibility.

## Frame types

Each frame costs space in chrome. It earns that space only by telling the viewer something
the interface alone does not.

| Frame | Tells the viewer | Use when | Keep the chrome to |
| --- | --- | --- | --- |
| None, interface on the page | Nothing extra | The page already says what kind of product this is | Nothing |
| Browser window | It runs in a browser, at an address | The product is a web app and that is part of the pitch | A plain bar with three dots or none, and a short, invented or the user's own address |
| Desktop app window | It is a native app | The product installs on a computer | A title bar with the product's own name |
| Phone | It is on your phone | The product is mobile, or the claim is about being reachable anywhere | A rounded rectangle with a thin bezel, drawn in CSS; no brand-specific details |
| Notification | It reaches you without opening the product | The claim is an alert, a reminder or a message | One notification, the product's own icon, a real-sounding but invented message |
| Terminal | It is a command-line tool | The product is used from a shell | A dark rectangle, a prompt, one command and its output |
| Bento grid | It does several things | The claim is breadth, with each cell carrying one feature | One focus per cell, and no more cells than the reader will look at, usually four to six |

Draw frames as simple generic shapes. A traced device frame or operating-system chrome
copied from someone else's artwork carries their terms; step 2 of the skill covers
permission.

## Cropping rules

1. **Crop to the slot, not to the product.** Start from the slot's aspect ratio and fit
   the interface into it, never the other way round.
2. **Run off one or two edges.** An interface that ends inside the frame on all four sides
   reads as a small, finished thing. Letting the sidebar or the table run off the right
   or bottom edge says the product continues.
3. **Cut through structure, not content.** A crop line may pass through a panel, a gap
   between rows or the empty part of a chart. It may not pass through a line of text, an
   icon or the middle of a button, which reads as an error.
4. **Keep the anchor.** Keep one element that orients the viewer: the product's name or
   logo, a recognisable navigation edge, or a page title. Without it, a crop is an
   abstract arrangement of boxes.
5. **Never crop the focus.** If the focus does not fit whole, zoom the whole interface out
   or simplify further; do not cut it.

## Composition inside the frame

- Put the focus on a third line of the frame, not dead centre, unless the slot is a small
  square card.
- Leave margin around the focus equal to at least one of the product's larger spacing
  steps, so it does not touch the frame edge.
- A tilt or perspective transform reduces legibility and is often what makes a mock look
  generic. Use one only when the page's design direction calls for it, and then check
  legibility on the transformed render, not the flat one.
- A shadow under the frame belongs to the page's depth stance, not to the mock. Match the
  page.
