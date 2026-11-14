# Frontend reference: rotation-deck-demo.html

A static, standalone HTML mockup of the TCG-style UI concept, built from one
real run of the scoring engine against live NASA POWER + SoilGrids data for
Ames, IA (2023). Open the file directly in a browser — no server or build
step needed, all data is embedded in a `<script type="application/json">`
block near the bottom.

What it's for: a reference for layout, interaction patterns, and which
real API fields drive which piece of UI — not a design system or component
library to reuse as-is.

## What's real vs. illustrative

- **Real**: every score, stat bar, SDG badge, risk/gap string, and the
  monthly rainfall/ET0 chart come straight from `rotation_scoring.py`
  output (see `docs/api-contract.md` for the field meanings).
- **Live-recomputed, not mocked**: the priority sliders and the "compare
  against" baseline dropdown re-run the engine's actual weighted-sum and
  impact-metric formulas in JS against the embedded per-crop numbers — not
  a fake slider that does nothing.
- **Illustrative placeholder**: the map is a schematic lat/lon grid, not a
  real tile map (external map tiles aren't available in this format) —
  only the Ames pin has real data behind it; clicking elsewhere shows an
  honest "not wired up in this demo" message.
- **Static**: there's no live backend call anywhere in this file. A real
  build would call `POST /rotations` (see `docs/api-contract.md`) instead
  of reading the embedded JSON blob.

## Where the game-inspired ideas show up

The page has a legend box near the top (just under the header) that maps
each Pokémon-TCG-style idea — stat allocation sliders, deck/hand selection,
evolution chain, stat bars, weakness indicator, achievement badges — to the
section that demonstrates it.

## rotation-quest-game.html

A pixel-RPG explainer: walk a farmer up to Professor Rotation, lose a
battle as a continuous monoculture (real numbers in the battle log —
nitrogen loss, bare-field days), then get the engine's actual top-ranked
rotation and win the rematch. All sprites are hand-coded pixel grids drawn
to canvas, so there are no image assets or licenses to worry about as-is.

It also supports swapping in real art: `SPRITE_ASSETS` near the top of the
script has one entry per character (`player`, `professor`, `monster`,
`guardian`), each `{ src, frame }`. Leave `src: null` to keep the built-in
pixel art, or point `src` at a downloaded spritesheet image and set `frame`
to `{sx, sy, sw, sh}` (the pixel rectangle of that one frame on the sheet).
Use `sprite-picker.html` to find those numbers by dragging a box over a
frame in the browser — no image editor needed.

**Picking free art**: Kenney.nl's packs are CC0 (public domain, no
attribution required, safe for a hackathon submission) — look for a
top-down RPG or farming-themed pack with a character sheet and a small
creature/monster sheet. Avoid anything using official Pokémon art or
names in the actual submission; the battle framing is an homage, not a
reskin. Whatever pack you pick, check its own license page before using it.

## sprite-picker.html

A drag-and-drop dev tool: drop a spritesheet PNG in, drag a box around one
frame, and it reads off the exact `sx, sy, sw, sh` pixel values to paste
into `SPRITE_ASSETS` above. Runs entirely in the browser; the image never
leaves the tab.

## map-editor.html

A visual, click-to-paint editor for the overworld map, pre-loaded with
`rotation-quest-game.html`'s current layout so you're editing on top of
what's already there, not starting blank. Pick a tile from the palette on
the left, click (or click-drag) across the grid to paint it, and use the
two marker buttons to move the player's start position or the professor's
spot. Drop in more PNGs from `assets/` to add new tile types on the fly —
each gets the next free digit automatically.

Hit **Export** when you're done: it generates the exact `MAP` array,
updated `player`/`professor` coordinates, and (if you added any custom
tiles) the `TILE_SRCS`/`TILE_TEXTURE_DATA` entries they need — each
block labeled with where it goes in `rotation-quest-game.html`. Paste them
in, save, and refresh the game to see the change. Runs entirely in the
browser; nothing uploads anywhere.
