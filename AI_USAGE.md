# AI usage

This project was built with Claude Code (Anthropic) as a development
assistant throughout the hackathon. This file is the honest account of
where it was used, for judging and for anyone reading the repo.

## Tool

Claude Code, used in an interactive session alongside the team, not as an
autonomous author. Every commit carries a `Co-Authored-By: Claude Sonnet 5`
trailer, so the git history itself is a verifiable record of which changes
involved it and when.

## Where it helped

- **Backend scoring engine** (`backend/app/engine/`) — the FAO-56 reference
  ET0 calculation, the rotation scoring maths, the agronomic rules, and the
  bare-field-days metric were implemented with Claude, directed and
  reviewed by the team at each step.
- **Crop dataset** (`data/crops.json`) — when lentil and chickpea were
  added, Claude cross-checked FAO-56, GRDC and USDA NASS figures and
  flagged where published numbers disagreed across studies. Those caveats
  are recorded in the dataset's own `source` fields.
- **Tests** (`backend/tests/`) — regression tests written alongside each
  feature as it was built.
- **Documentation** (`docs/`) — drafted from the working code and checked
  against it, not written speculatively ahead of the implementation.
- **Frontend demo prototypes** (`docs/frontend-reference/`) — the Rotation
  Deck page, the Rotation Quest pixel-RPG, and their supporting tools
  (sprite picker, map editor) were built as rough internal demos to show
  the team what the product concept could look like. They are not the
  submitted frontend.

## What stayed human

Every substantive decision — which crops to add, which risks to surface,
how a rotation should be scored, what the demo should teach a judge — was
made by the team. Claude drafted and implemented; it did not choose the
project's scope, sources, or claims.

## Why this file exists

The Space Apps submission process asks what tools were used to build the
project. This is the answer for the code and documentation in this
repository.
