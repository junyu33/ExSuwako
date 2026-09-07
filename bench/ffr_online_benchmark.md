# Schedule-Free FFR Representative Slices

This is a separate exploratory experiment family.  It does not append fields
or rows to the frozen `paper-v1` reduction artifact.

`PlannedFFR` is the existing FFR implementation: modulus setup materializes
all doubled feedback descriptors and the final assembly descriptors.
`OnlineFFR` borrows the same canonical tap list and allocates only reusable
state plus one tap-sized descriptor scratch array.  Every call derives the
active doubled descriptors and assembly descriptors from the original taps;
no descriptor set is reused as the next call's schedule. Both paths invoke the same scalar feedback-stage and
low-part assembly kernels.

The frozen exploratory contract is:

- manifest: `bench/manifests/ffr-online-v1/representative-slices.jsonl`;
- data directory: ignored `bench/data/ffr-online-v2/` for the clean retained
  run; the earlier dirty-worktree run remains isolated under
  `bench/data/ffr-online-v1/`;
- input distribution: `uniform-full-range:v1`;
- timing scope: `ffr-online-steady-state:v1`;
- setup scope: `ffr-online-workspace:v1`;
- 8 shared inputs, one discarded full warm-up, 12 batch repeats, 31 retained
  trials, and cyclic two-method order;
- portable scalar C on one pinned CPU, with no gf2x operation in either timed
  path.

The 45 manifest points use

\[
m\in\{128,2048,32768,131072\},\qquad
\Delta_{\min}\in\{1,64,m/4\},
\]

with \(h\in\{3,9,65\}\) at \(m=128\) and
\(h\in\{3,9,65,513\}\) otherwise.  All supports are deterministic,
constant-free controlled spreads.  The summary reports steady-state medians
and a paired bootstrap interval for `OnlineFFR/PlannedFFR`.  Its \(K=1\)
columns are the declared derived quantity
\(T_{\rm setup}+T_{\rm reduce}\), not a directly timed end-to-end interval.

Recreate and run the experiment with:

```sh
make freeze-ffr-online-manifest ffr-online-benchmark
python3 bench/scripts/collect_ffr_online_benchmark.py \
  --binary build/ffr_online_benchmark \
  --manifest bench/manifests/ffr-online-v1/representative-slices.jsonl \
  --output bench/data/ffr-online-v2/representative-raw.csv \
  --inputs 8 --repeats 12 --trials 31 --cpu 0
python3 bench/scripts/analyze_ffr_online_benchmark.py \
  --input bench/data/ffr-online-v2/representative-raw.csv \
  --output bench/data/ffr-online-v2/representative-summary.csv
```

## Retained clean run

The 45-point, 31-trial run from clean commit `48bd09d` on the primary
development host produced 1,395 raw rows. Across the four degree slices, the
minimum/median/maximum steady-state
`OnlineFFR/PlannedFFR` ratios were:

| \(m\) | minimum | median | maximum |
|---:|---:|---:|---:|
| 128 | 1.2199 | 1.6631 | 2.1762 |
| 2048 | 1.0448 | 1.0905 | 1.1561 |
| 32768 | 1.0000 | 1.0056 | 1.0132 |
| 131072 | 0.9980 | 1.0022 | 1.0054 |

Thus online descriptor generation is visible at small degree, falls to about
one percent by \(m=32768\), and is operationally negligible in the largest
slice.  Conversely, the derived \(K=1\) ratio is below one at every measured
point because OnlineFFR avoids stored-schedule construction; its overall
median is 0.9163.  These are representative, single-host portable-C results, not
an architecture-independent ordering.

The ignored local files are integrity-labelled by:

- raw CSV SHA-256:
  `25964f8ee1a181ab7bddcd6b51b483501dd7c0df569f6c75b958bcb4dbc0de62`;
- summary CSV SHA-256:
  `4f0deddf198ed72b14ee7a9ad8a12bb28b02695c293a917eeb8917b975b7c57f`.
