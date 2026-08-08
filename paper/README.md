# Paper Branch Contract

`main` is the venue-neutral research trunk.  Its paper-facing documents cover
the generalized-Suwako mathematical core, verified prior-art boundary, and
classical evaluation plan.  The `raw/` directory is a complete provenance
archive; a raw note is not, by itself, part of the manuscript scope.

Venue branches are curated projections rather than copies of this directory:

- `math-comp` retains the mathematical core and classical applications, and
  may omit raw records that do not serve that manuscript.
- `eurocrypt` retains the core together with cryptographic and
  reversible-circuit research tracks.

After a venue branch is curated, import shared corrections from `main` by
selective cherry-pick.  Do not merge all paper notes wholesale, because that
would reintroduce out-of-scope material.
