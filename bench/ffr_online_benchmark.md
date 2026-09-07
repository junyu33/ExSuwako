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
- data directory: ignored `bench/data/ffr-online-v1/`;
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
  --output bench/data/ffr-online-v1/representative-raw.csv \
  --inputs 8 --repeats 12 --trials 31 --cpu 0
python3 bench/scripts/analyze_ffr_online_benchmark.py \
  --input bench/data/ffr-online-v1/representative-raw.csv \
  --output bench/data/ffr-online-v1/representative-summary.csv
```

## Current exploratory run

The 45-point, 31-trial run on the primary development host produced 1,395 raw
rows.  Across the four degree slices, the minimum/median/maximum steady-state
`OnlineFFR/PlannedFFR` ratios were:

| \(m\) | minimum | median | maximum |
|---:|---:|---:|---:|
| 128 | 1.2151 | 1.6761 | 2.1973 |
| 2048 | 1.0426 | 1.0862 | 1.1791 |
| 32768 | 0.9981 | 1.0060 | 1.0094 |
| 131072 | 0.9948 | 1.0019 | 1.0059 |

Thus online descriptor generation is visible at small degree, falls to about
one percent by \(m=32768\), and is operationally negligible in the largest
slice.  Conversely, the derived \(K=1\) ratio is below one at every measured
point because OnlineFFR avoids stored-schedule construction; its overall
median is 0.9154.  These are exploratory, single-host portable-C results, not
an architecture-independent ordering.

The ignored local files are integrity-labelled by:

- raw CSV SHA-256:
  `002575ba4280f8c05583f78c0cc36f96418748dfa3082c3d5ba8557aa097431f`;
- summary CSV SHA-256:
  `1d3fdee903d361fbc23c8f8696f2c938ef1f68639b845834e13d6814fe83b6bb`.
