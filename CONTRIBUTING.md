# Contributing

Rules for working on this repo during the challenge. Keep it lightweight, we have a weekend.

## Branches

- `main` is always demo-able. Never push directly to `main`, open a pull request instead.
- One branch per person per area, e.g. `data_science_<name>`, `frontend_<name>`, `plantsweather_<name>`.
- Rebase or merge `main` into your branch at the start of each working session so you are not integrating stale code the night before the deadline:
  ```
  git fetch origin
  git merge origin/main
  ```
- Delete your branch after it's merged, or keep it if you're still iterating.

## Commits

- Small, frequent commits over one giant end-of-day commit. Push at least once per session so work isn't only local.
- Commit message style: short imperative summary line (`add NASA POWER client`, not `added` or `adding`).

## Pull requests / merges

- Open a PR into `main` when a piece is working end to end, even if small. Don't wait for "finished".
- At least one other teammate should glance at the diff before merging if there's time; if not, self-merge rather than blocking.
- `@ada-th25` (git lead) handles conflict resolution on `main` if a merge gets messy. Ping them rather than force-pushing over someone else's branch.
- Never use `git push --force` on `main` or on a branch someone else is also committing to.

## Directory ownership

See `README.md` for the full repo structure. Ownership:

- `backend/app/data/`, `backend/app/engine/`, `data/` — data science (NASA/SoilGrids clients, scoring engine, crop dataset)
- `backend/app/main.py`, `backend/app/schemas.py` — API contract, owned jointly (data science defines the shape, frontend consumes it)
- `frontend/` — frontend
- `docs/` — shared, anyone can add example payloads or notes

If you need to touch a file outside your area, flag it in the team chat first so you're not stepping on someone's in-progress work.
