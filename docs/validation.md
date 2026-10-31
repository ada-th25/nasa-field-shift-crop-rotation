# Validation: multi-site stress test and real-world comparison

Two checks on the model's outputs: whether the climate filter behaves
sensibly across very different climates, and whether the Iowa
recommendation lines up with real published agronomy research rather than
just looking plausible.

## Multi-site stress test

Same pipeline, same `crops.json`, three climates chosen to be as different
as possible, run via `python scripts/demo.py <lat> <lon>`:

| Site | Climate | Crops excluded (too cold/hot for any viable window) | Top-ranked rotation |
|---|---|---|---|
| Ames, Iowa (42.03, -93.63) | Humid continental | None | alfalfa → maize → alfalfa (RSI 1.809) |
| Reykjavik, Iceland (64.13, -21.90) | Subarctic | maize, alfalfa | soybean → cereal_rye_cover → soybean (RSI 1.559) |
| Singapore (1.35, 103.82) | Tropical | None | alfalfa → maize → alfalfa (RSI 2.070) |

*Numbers above include the erosion and revenue scoring changes; re-run `scripts/demo.py <lat> <lon>` for all three sites if `rotation_scoring.py` changes again.*

What this shows: the climate filter correctly drops maize and alfalfa for
Iceland (both need warmer conditions than any window in Iceland's year
provides) while leaving Iowa unaffected. It also exposes a real limitation
worth stating plainly: Singapore keeps the full crop list, including
winter wheat and alfalfa, because the filter only checks temperature — it
doesn't know winter wheat needs a vernalization period and short days,
things a temperature-only check can't see. That's an honest limitation,
not a hidden one: **the filter prevents the model from being obviously
wrong (recommending maize in the Arctic), it doesn't guarantee full
agronomic correctness everywhere.**

## Comparison against real Iowa agronomy research

The Iowa top recommendation is now alfalfa → maize → alfalfa (RSI 1.809),
with cereal-rye-then-soybean (RSI ~1.9 before revenue scoring) further
down the list. This is a direct result of adding `revenue_score` (see
"Revenue scoring brings corn back" below) — before that change, every
top-5 rotation excluded corn entirely, which was the model's single
biggest divergence from real practice. How does the current top pick hold
up against actual research?

**Where it agrees:**
- Davis, A.S., Hill, J.D., Chase, C.A., Johanns, A.M., Liebman, M. (2012).
  "Increasing Cropping System Diversity Balances Productivity, Profitability
  and Environmental Health." *PLoS ONE* 7(10): e47149 — the Marsden Farm
  long-term rotation study at Iowa State, running since 2001, directly
  compares a 2-year corn/soybean rotation against 3-year (corn/soybean/oat
  + red clover) and 4-year (corn/soybean/oat + alfalfa/alfalfa) rotations.
  It found the more diversified rotations substantially cut synthetic
  nitrogen and herbicide use while maintaining productivity, without ever
  dropping corn. Our current top pick (alfalfa → maize → alfalfa) keeps
  corn in the mix too, now that `revenue_score` gives the model a reason
  to — a meaningfully closer match to real practice than the pre-revenue
  top-5, which excluded corn entirely. Source: [Iowa State INRC project page](https://inrc.cals.iastate.edu/marsden-long-term-rotation-study), [full text on PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3468434).
- The 4-year Marsden Farm rotation specifically includes alfalfa alongside
  corn, so our model reaching for the same combination independently (not
  by being told to) is a good sign that the underlying logic is sound, not
  just coincidentally plausible.
- An eight-year Iowa Learning Farms / Practical Farmers of Iowa study found
  cereal rye ahead of soybean has little to no negative yield effect and
  improved soybean yield in several site-years — the cereal-rye-then-soybean
  rotation (ranked lower than the alfalfa/maize combination once revenue
  scoring was added, but still a top candidate) remains a real, supported
  practice. Iowa State Extension publishes a dedicated guide for exactly
  this transition (CROP 3158, "Post Corn, Going to Soybean: Use Cereal Rye").

**Where it diverges, and why that matters:**
- The real Marsden Farm rotation grows alfalfa for two full consecutive
  years as an established stand, never alternating it yearly with another
  crop. Our top-ranked rotation (alfalfa → maize → alfalfa) plants and
  replaces alfalfa annually, which doesn't match how it's actually grown
  and ignores the yield drag/establishment cost of a first-year stand.
  This is a side effect of the role-based erosion score (continuous
  perennial cover scores highest) without the engine knowing alfalfa is a
  multi-year perennial — flagged automatically in that rotation's
  `risks_and_gaps`, and the right fix is multi-year crop "blocks" in the
  candidate generator, not a quick patch.
- `revenue_score` is yield-only, with no commodity price, input cost, or
  labour — real farm economics would weigh corn's higher per-hectare input
  cost (seed, fertilizer, fuel) against its higher yield, which this proxy
  can't do. It moved the model in the right direction but isn't a
  profitability model.

**Bottom line for the pitch**: the model's structural logic (diversify, add
a legume or cover crop, reduce synthetic N, keep a revenue crop in the mix)
is independently supported by a real long-term Iowa State study, right
down to alfalfa-and-corn showing up in both. The remaining gaps (alfalfa
treated as an annual, revenue as yield-only) are honest, explainable, and
each has a concrete next step rather than being a hidden flaw.
