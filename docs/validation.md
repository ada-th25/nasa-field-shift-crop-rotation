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
| Ames, Iowa (42.03, -93.63) | Humid continental | None | cereal_rye_cover → alfalfa → cereal_rye_cover (RSI 1.966) |
| Reykjavik, Iceland (64.13, -21.90) | Subarctic | maize, alfalfa | cereal_rye_cover → soybean → winter_wheat (RSI 1.780, tied with → oats) |
| Singapore (1.35, 103.82) | Tropical | None | cereal_rye_cover → alfalfa → cereal_rye_cover (RSI 2.139) |

*Numbers above are post-erosion-scoring (see "Erosion scoring and a modelling artifact it surfaced" below); re-run `scripts/demo.py` if `rotation_scoring.py` changes again.*

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

The Iowa top recommendation is a 3-year rotation that drops corn entirely
in favor of cereal rye and alfalfa, with cereal-rye-then-soybean a close
second (RSI 1.938 vs. 1.966). How does that hold up against actual
research, not just internal model logic?

**Where it agrees:**
- Davis, A.S., Hill, J.D., Chase, C.A., Johanns, A.M., Liebman, M. (2012).
  "Increasing Cropping System Diversity Balances Productivity, Profitability
  and Environmental Health." *PLoS ONE* 7(10): e47149 — the Marsden Farm
  long-term rotation study at Iowa State, running since 2001, directly
  compares a 2-year corn/soybean rotation against 3-year (corn/soybean/oat
  + red clover) and 4-year (corn/soybean/oat + alfalfa/alfalfa) rotations.
  It found the more diversified rotations substantially cut synthetic
  nitrogen and herbicide use while maintaining productivity. That's the
  same direction our model's top rotations point in: diversifying away
  from continuous corn with a small grain and a legume reduces synthetic N
  need, and the 4-year Marsden Farm rotation specifically includes alfalfa,
  so the model reaching for the same crop independently is a good sign.
  Source: [Iowa State INRC project page](https://inrc.cals.iastate.edu/marsden-long-term-rotation-study), [full text on PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3468434).
- An eight-year Iowa Learning Farms / Practical Farmers of Iowa study found
  cereal rye ahead of soybean has little to no negative yield effect and
  improved soybean yield in several site-years — i.e. the second-ranked
  rotation (cereal rye → soybean → cereal rye) is a real, supported
  practice, not an arbitrary model output. Iowa State Extension publishes a
  dedicated guide for exactly this transition (CROP 3158, "Post Corn, Going
  to Soybean: Use Cereal Rye").

**Where it diverges, and why that matters:**
- Every real rotation in the Marsden Farm study, including the most
  diversified 4-year one, still grows corn regularly — it's never dropped
  entirely, because corn is the primary revenue crop for most Iowa farms.
  Our model's current top-5 rotations exclude corn entirely. That's not
  the model discovering something the research missed — it's the gap we
  already knew about: **there's no profit/yield dimension in the scoring
  yet**, so the model has no reason to keep a high-value but
  resource-intensive crop in the mix. This cross-check gives concrete
  evidence for why the profit dimension is the right next priority, rather
  than just a nice-to-have.
- The real Marsden Farm rotation grows alfalfa for two full consecutive
  years as an established stand, never alternating it yearly with another
  crop. Our top-ranked rotation (cereal rye → alfalfa → cereal rye) plants
  and replaces alfalfa annually, which doesn't match how it's actually
  grown and ignores the yield drag/establishment cost of a first-year
  stand. This is a direct side effect of adding a role-based erosion score
  (continuous perennial cover scores highest) without the engine knowing
  alfalfa is a multi-year perennial — flagged automatically in that
  rotation's `risks_and_gaps`, and the right fix is multi-year crop
  "blocks" in the candidate generator, not a quick patch.

**Bottom line for the pitch**: the model's structural logic (diversify,
add a legume or cover crop, reduce synthetic N) is independently supported
by a real long-term Iowa State study, right down to alfalfa showing up in
both. The places it diverges from real-world practice (corn disappearing
entirely, alfalfa treated as an annual) are honest, explainable gaps tied
to features we've already scoped, not hidden flaws.
