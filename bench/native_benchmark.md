# Native gf2x benchmark

This file documents the current native reduction-only benchmark.  Planned
input distributions, application benchmarks, formal evidence gates, and
artifact requirements are tracked in
[the experimental TODO](../paper/exp_todo.md).

The native reducer implementations live in `src/`; public headers are under
`include/`; benchmark scripts and entrypoints live under `bench/scripts/`.

`bench/scripts/reduction_benchmark.c` drives the reduction-only microbenchmark
through the common `reduction_method` API in `include/reduction.h`. GS, serial sparse
folding, naive long division, Barrett, the opt-in dense linear map, and an
opt-in ordinary-loop López--Dahab reducer or compiled fixed-modulus reducer
all expose the same timed
`reduce_into(input, context, output)` contract to the benchmark. Method setup,
input generation, output allocation, correctness checks, and checksum
consumption are outside the timed region.

Naive long division is the generic polynomial-remainder correctness and
portability reference.  It is independent of sparse schedules and accepts any
monic degree-$m$ binary modulus.  Its `Naive_ns` field is contextual rather
than a claim that this straightforward implementation is a tuned generic or
sparse performance competitor.

## Portable scalar boundary validation

`make check` differentially compares GS, Serial, Naive, Barrett, and
ordinary-loop López--Dahab wherever its degree assumption holds, around
$W$, $2W$, and $3W$ word boundaries as well as on deterministic random degrees
through 512.  Reducer outputs are deliberately allocated two words larger
than their minimum capacity and prefilled with ones, so the suite verifies
both degree-$m$ top-word masking and zeroed output tails.  The support profiles
include empty, dense, sparse, constant-free, endpoint, aligned/unaligned, and
unrestricted tap sets.

The dedicated dense-map suite compares its basis columns and random inputs
against Naive long division over the same boundary-oriented modulus profiles.

The separate `sparse_shift_correctness_check` exhausts right-shift distances
from zero through two words beyond source capacity for small source and
destination sizes.  It also exercises the shared two-word gather primitive at
every bit offset $0,\ldots,W-1$.  Run the same reducer, GS stage/component,
and shared-shift suites with memory and undefined-behavior instrumentation via:

```text
make check-sanitize
```

This uses ASan with leak detection and UBSan with fail-fast behavior.  Passing
the suite establishes coverage of the exercised scalar paths; it is not a
formal proof that arbitrary C object sizes cannot overflow `size_t`.

The shared header is also the fairness boundary for scalar sparse shifts.
Both GS and Serial use `sparse_assign_right_shift` to extract the high part.
For feedback, GS gathers an output word from an adjacent source pair with
`sparse_right_shift_word`, whereas Serial loads a source word once and scatters
its `sparse_right_shift_low` and `sparse_right_shift_carry` contributions.
Those three functions implement the same word/bit decomposition; sharing them
does not erase the algorithms' genuinely different schedules and traversals.

## Input Distribution Registry

Every result row carries an `input_distribution` label. The frozen names and
mathematical contracts are:

| Name | Input polynomial $A$ with $\deg A<2m$ | Status |
|---|---|---|
| `uniform-full-range:v1` | $A=L+x^mH$, where $L$ and $H$ are independent uniform $m$-bit polynomials | Implemented; primary reduction-only corpus |

All reducers in one comparison consume the same materialized
`uniform-full-range:v1` inputs.

## Timed-Boundary Registry

Every timing row carries a `timing_scope` label. The frozen operation boundary
is:

| Name | Included inside the timed operation | Excluded from the timed operation | Status |
|---|---|---|---|
| `reduction-steady-state:v1` | Calls to `reduce_into(input, plan, output)` over a materialized input batch | Plan/setup construction, input generation, allocation, correctness checks, checksum consumption, and reporting | Implemented |

The benchmark times a batch with one clock interval and divides by the number
of reductions; it does not place clock calls around individual calls. Every
method must retain the same mathematical operation $A\mapsto A\bmod g$ for
$\deg A<2m$. Reusable setup is deliberately handled by the separate
setup-accounting contract rather than hidden inside one method's timed
operation.

The two Barrett products call the upstream `gf2x_mul` API. The reciprocal
polynomial is precomputed outside the timed reduction path.

## Sampling and Stability Protocol

One native invocation reports the median of `batch_repeats` timed batches.
Within each setup and reduction repeat, the first measured method advances
cyclically, so no reducer is permanently assigned to the cold/ramp-up or
late/hot position.
Choose a repeat count divisible by the number of enabled methods to balance
every method across every position exactly; the frozen count of 12 works for
both the three-method (`no-naive`) and four-method configurations. Every row
records `timing_order=cyclic-method-rotation:v1`.
For paper measurements, run one discarded whole-invocation warm-up followed
by 31 independent measurement trials over the same materialized support and
deterministically reproduced input corpus. Preserve all 31 rows, then report
their median. Do not delete or winsorize outliers; report dispersion from the
retained rows. Use a deterministic nonparametric bootstrap over the retained
trial medians and mark a point uncertain when the relative half-width of its
95% median confidence interval exceeds 1%; additional trials may narrow that
interval, but must be retained and reported rather than replacing unfavorable
measurements.

The phase-diagram driver implements this protocol with
`--warmup-runs 1 --measurement-trials 31`. Its default remains one trial so
contract tests and exploratory runs stay short. Every raw row records
`inputs`, `batch_repeats`, `warmup_runs`, `measurement_trials`, and
`measurement_trial`, together with
`aggregation=median-of-trial-medians:no-outlier-removal:v1`. The frozen
paper-facing inner count is twelve batch repeats. A final run must retain the
same input count across compared methods and record that count rather than
hiding it in the aggregation step.

On the primary machine, an exploratory calibration pinned to logical CPU 10
split 310 independent runs into ten disjoint groups of 31. For the tested
representative support under cyclic method rotation and 12 batch repeats, the
group-median CV was 0.802% for GS, 0.148% for Serial, and 0.020% for Barrett.
This calibrates the sampling rule; it is not a paper performance result and
must be rerun on the final artifact commit. Measurements made under the old
fixed GS--Serial--Naive--Barrett order are not comparable to this protocol.

Primary-machine runs use GCC with
`-O3 -std=c11 -Wall -Wextra`, 64-bit `word_t`, and the dynamically resolved
gf2x shared library. Run the driver under `taskset` on one recorded logical
CPU. Record the exact compiler version, linked gf2x path, CPU model and
affinity, governor, energy-performance preference, and turbo state with the
raw run. Do not pool rows collected under different compiler, linkage,
affinity, or frequency policies.

## Setup-Accounting Registry

Every row also carries `setup_scope=modulus-plan:v1`. Starting from already
materialized $m$, taps, and $g$, one setup sample times construction of a fresh
reusable reducer plan. Destruction happens after the clock stops. The
benchmark takes the median of `repeats` fresh constructions, then constructs a
separate plan for correctness checking and steady-state reduction timing.

The included method-specific work is:

| Method | Included in setup |
|---|---|
| GS | feedback-stage schedule, shift descriptors, and plan-owned scratch allocation |
| Serial | tap descriptors, sorting, and plan-owned state allocation |
| Naive | its current lightweight context allocation |
| Barrett | reciprocal $\mu$, Barrett plan construction, and plan-owned scratch allocation |
| LopezDahabLoop | tap descriptors and plan-owned $2m$-bit work buffer |
| Dense | construction of the packed fixed-modulus map and plan-owned high-part scratch allocation |
| Generated | shared-object loading, ABI/modulus validation, and generated plan scratch allocation |

Argument parsing, shared modulus materialization, input/output benchmark
buffers, correctness checks, reporting, and teardown are excluded uniformly.
The CSV preserves `GS_setup_ns`, `Serial_setup_ns`, `Naive_setup_ns`,
`BarrettGF2X_setup_ns`, `LopezDahabLoop_setup_ns`, and `Dense_setup_ns`
separately from the steady-state
reduction fields. `Generated_setup_ns` is the loaded-plan component; its
source generation and compilation are reported separately by the generated
driver. For
an explicitly stated number $K$ of reductions using one plan, derive

\[
T_{\mathrm{total}}(K)=T_{\mathrm{setup}}+K T_{\mathrm{reduce}},
\qquad
\bar T(K)=T_{\mathrm{reduce}}+\frac{T_{\mathrm{setup}}}{K}.
\]

Do not bake a particular $K$ into the raw CSV. The dense reducer counts map
construction and allocation as setup and reports stored-map capacity through
`Dense_plan_bytes`. The generated reducer reports `Generated_generation_ns`,
`Generated_compile_ns`, `Generated_setup_ns`, and their sum
`Generated_full_setup_ns`, so compilation is neither discarded nor hidden in
steady-state reduction.

Plan storage uses `plan_storage_model=requested-owned-bytes:v1`. It sums each
reducer's context structure and the byte capacities of every heap buffer owned
for the plan's lifetime. GS includes its round and shift descriptors plus the
state and sentinel; Serial includes tap descriptors and both state buffers;
Naive includes its lightweight context; Barrett includes its adapter context,
reciprocal, plan, and both reusable product buffers; LopezDahabLoop includes
its tap descriptors and reusable $2m$-bit work buffer; Dense includes its packed
$m\times m$ row-major matrix and reusable high-part buffer; Generated includes
the loader wrapper and generated state buffer, while mapped code is reported
through separate code-size fields. Shared modulus storage,
benchmark inputs and outputs, allocator metadata and slack, temporary
setup-only allocations, generated code, and external-library transient
workspace are excluded.

The benchmark reads `GS_plan_bytes`, `Serial_plan_bytes`, `Naive_plan_bytes`,
`BarrettGF2X_plan_bytes`, `LopezDahabLoop_plan_bytes`, `Dense_plan_bytes`, and
`Generated_plan_bytes` from
the separately constructed plans only after
all setup samples have stopped. Thus storage inspection cannot enter
`T_setup`, and the inspected plans are the same plans subsequently used for
correctness and steady-state timing. The contract tests require the storage
model and values to be present and deterministic, while setup timings remain
separate nonnegative observations rather than being inferred from storage.

## Seed and Regression Registry

The native xorshift generator is deterministic. Its nonzero C seed controls
random support sampling and `uniform-full-range:v1` inputs and is emitted in
every native CSV row. Artifact commands must pass the seed explicitly even
when a driver has a deterministic default. The phase-diagram driver's Python
seed deterministically generates nonzero per-invocation C seeds; every derived
row preserves the actual C seed, exact taps, stable `sample_id`, and
provenance. Repeating the same driver seed is contract-tested to reproduce all
nontiming identity and geometry fields.

Native correctness testing uses the fixed seed
`0xd1b54a32d192ed03`; the theorem-falsification suites record their own fixed
seeds in source and, where supported, output. A native mismatch prints its
suite, seed, degree, trial, complete taps, compared methods, and exact
little-endian input words.
After minimizing a failure, encode its input as mathematical bit exponents in
`tests/reduction_regressions.h`; `make check` replays that corpus before the
random suites. Bit exponents keep the case independent of machine word width.

Benchmark-only anomalous supports belong in
`bench/manifests/regression_supports.jsonl` with a stable identifier and
provenance. The manifest is replayed by the experiment contract test. Local
timing CSV remains exploratory and ignored; do not promote environmental
jitter into a modulus regression unless the exact support reproducibly
triggers the anomaly under the frozen platform protocol.

The benchmark requires a native gf2x installation. Set `GF2X_PREFIX` to its
installation prefix and build with MinGW or GCC:

```text
make GF2X_PREFIX=/path/to/gf2x
build/reduction_benchmark 12 64 5
```

Random-mode arguments are `supports`, `inputs`, `repeats`, `m`, `s`, `seed`,
and optional `no-naive` and `with-dense` flags. The output is reduction-only
timing in
nanoseconds per input. Correctness is checked across all enabled reducers
before each timed trial.

For a large `m` run that skips naive long division, pass the `no-naive` flag:

```text
build/reduction_benchmark 6 8 5 1000000 8 0x9e3779b97f4a7c15 no-naive
```

To benchmark one exact modulus support, use the canonical ascending tap list:

```text
build/reduction_benchmark --taps 0,7,12 8 5 283 0x1 no-naive
```

The exact-mode arguments are `--taps LIST`, `inputs`, `repeats`, `m`, `seed`,
and optional `no-serial`, `no-naive`, `with-dense`, `with-lopez-dahab`,
`generated=PATH`, or `trials=N`.  The last option emits $N$ independently
timed rows for the same exact support in one process; every row regenerates the
same deterministic inputs from `seed`.  It is an experiment-driver primitive,
not a change to the reduction timing scope.
`LIST` is comma-separated, strictly
increasing, duplicate-free, and contains only exponents in `[0,m)`; use `-`
for the empty support. The CSV serializes taps with semicolons so the complete
support occupies one field.

`no-serial` disables Serial plan construction, correctness comparison, and
timing rather than merely hiding its result.  Such rows emit
`Serial_enabled=0` and zero for all Serial setup, storage, timing, and ratio
fields.  The high-weight crossover extension uses this mode after the primary
panels have already established that Serial is noncompetitive there; GS and
Barrett remain enabled on every point, and eligible `*-ld.jsonl` points also
enable ordinary-loop López--Dahab.

The dense baseline is a fixed-modulus matrix implementation rather than a
sparse competitor. Enable it only as the fourth method replacing Naive:

```text
build/reduction_benchmark --taps 0,7,12 8 12 283 0x1 no-naive with-dense
```

`with-dense` requires `no-naive`, preserving an exactly balanced four-method
rotation when the repeat count is divisible by four. The benchmark rejects a
packed matrix above 64 MiB before setup; `Dense_enabled` and
`Dense_matrix_limit_bytes` make this policy explicit in every row. Disabled
runs emit zero for all Dense timing and storage fields and allocate no matrix.
The phase-diagram driver exposes the same policy as `--with-dense
--no-naive`.

For the ordinary-loop Algorithm 2 comparison, use exact taps satisfying
$m>W$ and $\deg q\le m-W$. Equality is a tested word-aligned extension of
the paper's strict assumption:

```text
build/reduction_benchmark --taps 0,5,7,12 64 24 283 0x1 \
  no-naive with-lopez-dahab
```

This enables GS, Serial, Barrett, and `LopezDahabLoop` in the same balanced
four-method rotation. The CSV reports its plan storage, setup time,
steady-state time, and ratio to GS; it generates or compiles no
modulus-specific source.

The phase-diagram driver exposes the same baseline for exact-support manifests:

```text
python3 bench/scripts/phase_diagram_benchmark.py \
  --binary build/reduction_benchmark \
  --manifest ld-supports.jsonl --output bench/data/ld-phase.csv \
  --inputs 8 --repeats 12 --seed 1 --no-naive --with-lopez-dahab
```

For manifest runs, `--measurement-trials N` is sent to the native process as
one exact-support batch.  `--warmup-runs K` prepends $K$ same-process rows and
discards them before assigning measurement-trial indices.  This removes
per-trial process startup from the sweep without placing it inside any
reducer's measured interval.  If a long run is interrupted, rerun the identical
command with `--resume`: the driver retains only complete samples, discards a
partial final sample, and rejects changes in the manifest, metadata, method
set, timing contract, or trial count. CSV output is appended once per complete
support, avoiding quadratic whole-file rewrites while retaining that recovery
boundary.

Every manifest entry must satisfy $m>W$ and $\deg q\le m-W$ or the native
benchmark rejects it before timing. `--with-lopez-dahab` requires
`--no-naive`, requires manifest mode, and is mutually exclusive with
`--with-dense`; either opt-in therefore retains a balanced four-method
comparison with GS, Serial, and Barrett. Dense remains a diagnostic baseline
subject to its matrix-size limit. Whether either opt-in belongs in a final
winner panel is decided from the formal sweep, not assumed from its presence.

Generate an exact controlled grid before running the phase driver:

```text
python3 bench/scripts/generate_controlled_supports.py \
  --output bench/data/controlled-m512.jsonl --m 512 \
  --h 2 3 5 9 17 33 --delta-min 1 2 4 8 16 64 128 256
python3 bench/scripts/phase_diagram_benchmark.py \
  --binary build/reduction_benchmark \
  --manifest bench/data/controlled-m512.jsonl \
  --output bench/data/controlled-m512.csv \
  --inputs 8 --repeats 12 --seed 1 --no-naive
```

The generator emits the full feasible Cartesian product of the requested
$h$ and $\Delta_{\min}$ axes, fixing the highest tap and deterministically
spreading all remaining taps. Its default `absent` policy is constant-free;
`--constant-policy present` creates a separately labelled constant-present
grid. If even one requested cell cannot realize the requested weight, gap,
and constant policy simultaneously, generation fails instead of silently
producing an incomplete grid. This deterministic grid controls geometry; it
does not replace the separate fixed-weight random-support distribution.

For a formal fixed-weight distribution, materialize the exact supports before
timing and then summarize trials separately from support-to-support variation:

```text
python3 bench/scripts/generate_fixed_weight_supports.py \
  --output bench/data/random-fixed-weight-m512.jsonl \
  --m 512 --h 2 3 5 9 17 33 65 --samples 256 \
  --seed 0x4558535557414b4f --constant-policy absent
python3 bench/scripts/phase_diagram_benchmark.py \
  --binary build/reduction_benchmark \
  --manifest bench/data/random-fixed-weight-m512.jsonl \
  --output bench/data/random-fixed-weight-raw.csv --inputs 8 --repeats 12 \
  --warmup-runs 1 --measurement-trials 31 --seed 1 --no-naive
python3 bench/scripts/summarize_fixed_weight.py \
  --input bench/data/random-fixed-weight-raw.csv \
  --supports bench/data/random-fixed-weight-supports.csv \
  --summary bench/data/random-fixed-weight-summary.csv
```

The summarizer first computes one median per exact support across retained
measurement trials. Within each fixed $(m,h)$ cell it then reports the median
and nearest-rank p90 and p99 across distinct supports for GS, Serial, Barrett,
their primary ratios, and the support-geometry metrics. Enabled optional
methods are included consistently. The default contract requires 100 unique
supports, 31 complete trials per support, 12 batch repeats, and one warm-up
invocation. Duplicate supports, mixed timing contracts, incomplete trial
indices, and non-fixed-weight provenance are rejected rather than silently
pooled or removed. The formal design requests 256 unique supports per cell;
For the frozen constant-free panels, the sampling universe is
$\{1,\ldots,m-1\}$; if $\binom{m-1}{h-1}<256$, the manifest generator
exhausts that complete population and reports the cap explicitly. The
generator's default `either` policy remains available for explicitly labelled
ring-level exploratory samples.

Classify controlled winner points and render the measured panels with:

```text
python3 bench/scripts/analyze_winner_panels.py \
  --input bench/data/controlled-core.csv bench/data/controlled-ld.csv \
  --points bench/data/winner-points.csv \
  --comparisons bench/data/winner-comparisons.csv \
  --summary bench/data/winner-summary.csv
python3 bench/scripts/plot_winner_panels.py \
  --input bench/data/winner-points.csv \
  --output bench/data/winner-panels.svg --columns 3
python3 bench/scripts/summarize_winner_regions.py \
  --input bench/data/winner-points.csv \
  --detail bench/data/winner-regions.csv \
  --summary bench/data/winner-region-summary.csv
python3 bench/scripts/plot_phase_slices.py \
  --input bench/data/winner-points.csv \
  --output bench/data/fixed-gap-weight.svg \
  --kind weight --selections 1 64
python3 bench/scripts/plot_phase_slices.py \
  --input bench/data/winner-points.csv \
  --output bench/data/fixed-weight-gap.svg \
  --kind gap --selections 9 65
```

`paired-bootstrap-one-percent:v1` uses 10,000 deterministic bootstrap
resamples. A unique winner must be stable to the 1% relative-half-width rule,
at least 1% faster in median time than every competitor, and have every
trial-paired ratio interval strictly below one. All other measured points are
retained with an explicit uncertainty reason. The renderer draws one
equal-area block per measured coordinate, labels the axes by
$\log_2(h-1)$ and $\log_2(m/\Delta_{\min})$, uses three columns (six main
degrees form a $2\times3$ figure), and leaves unmeasured cells blank. An
optional `--boundary-input` winner table must contain exactly the measured
coordinates; adjacent predicted winner changes are overlaid as pair-labelled,
high-contrast boundaries without interpolating across missing cells. The
summary recommends 63 and then 127 trials when more than 5% of a panel remains
timing-unstable. Dense screen rows additionally report whether any stable
point lies within 1.10 times the fastest primary method and therefore requires
a new five-method contract.

The region summarizer keeps one row per exact $(m,\Delta_{\min})$ slice and
compresses its measured winner runs in increasing $h$. Its reported
`persistent_Barrett_h` is the earliest stable Barrett point after which every
later stable measured point is also Barrett; uncertain cells are retained but
do not create a false crossover. The summary separates the hard-feedback
$\Delta_{\min}<W$ rows from the López--Dahab-applicable
$\Delta_{\min}\ge W$ rows and records when no persistent Barrett region was
observed within the sampled weight range.

The two slice plots use the same six fixed-$m$ panels and plot
$\log_2(T_{\rm method}/T_{\rm GS})$, with zero as the measured crossover.
The fixed-gap view varies $\log_2(h-1)$ at $\Delta_{\min}=1$ and $64$; the
fixed-weight view varies $\log_2(m/\Delta_{\min})$ at $h=9$ and $65$.
L\'opez--Dahab appears only where its measurement is present, and hollow gray
markers retain points whose winner classification is not unique. These are
controlled-support slices of measured medians, not interpolated boundaries or
fixed-weight random-support quantiles.

### Paper-grade run metadata

The tracked winner suite is regenerated with `make freeze-winner-manifests`.
It freezes the six main controlled panels, six high-weight crossover
extensions, six constant-free random panels, five
intermediate controlled panels, three constant-present sensitivity suites,
the large-degree slices, and the Dense diagnostic screen. Controlled points
are split into `*-core.jsonl` and `*-ld.jsonl`: the latter contains exactly
the points with $\Delta_{\min}\ge64$ at which the tested ordinary-loop
López--Dahab implementation joins GS and BarrettGF2X. Formal high-weight
invocations use `--no-serial`; retained primary-panel rows provide the
separate Serial screening evidence.

After building from a clean experiment commit, capture a metadata snapshot
outside the worktree and pass it to every formal phase invocation:

```text
python3 bench/scripts/capture_benchmark_metadata.py \
  --binary build/reduction_benchmark \
  --output /tmp/exsuwako-run-metadata.json --cc cc \
  --cflags '-O3 -std=c11 -Wall -Wextra' --cpu 3
python3 bench/scripts/phase_diagram_benchmark.py \
  --binary build/reduction_benchmark \
  --manifest bench/manifests/paper/main-m512-core.jsonl \
  --output bench/data/main-m512-core.csv \
  --inputs 8 --repeats 12 --warmup-runs 1 --measurement-trials 31 \
  --seed 0x9e3779b97f4a7c15 --no-naive \
  --metadata /tmp/exsuwako-run-metadata.json --paper-grade
```

`exsuwako-native-platform:v1` records the commit and dirty state, binary
SHA-256, compiler path/version/flags, resolved gf2x shared library, platform,
machine, hostname, one logical CPU, governor/EPP/turbo observations,
implementation registry, and multiplication backend. The phase driver pins
itself and all child processes to the recorded logical CPU and emits both its
complete command and each native benchmark command. `--paper-grade` rejects
a dirty or mismatched checkout, a changed binary, missing metadata, or failure
to enforce affinity. Analyze retained formal rows with
`analyze_winner_panels.py --paper-grade`; exploratory rows cannot pass that
mode.

## Fixed-Modulus Generated Reducer

`generate_fixed_reducer.py` emits one of two C plugins specialized to an exact
degree and tap list. `fixed-unrolled-gs-c:v1` expands every active feedback
stage and the final low-part assembly into literal word operations.
`lopez-dahab-algorithm2-fixed-c:v1` unrolls the top-word and final partial-word
cancellation of López--Dahab Algorithm 2. Both are currently frozen to 64-bit
`word_t`; each translation unit contains a compile-time assertion and must not
be compared across word widths without regeneration.

The López--Dahab mode accepts arbitrary modulus weight and enforces the
original assumption for $f=x^m+q$:

\[
\deg q < m-W.
\]

Parameters outside that domain are rejected before a source file is written.

Use the orchestration driver rather than retaining generated files manually:

```text
python3 bench/scripts/generated_reducer_benchmark.py \
  --binary build/reduction_benchmark \
  --output bench/data/generated-m283.csv \
  --algorithm lopez-dahab --m 283 --taps 0,5,7,12 \
  --inputs 8 --repeats 12 --seed 0x1
```

The driver generates and compiles inside a temporary directory, then invokes
the native benchmark as `no-naive generated=PATH`. Thus GS, Serial, Barrett,
and Generated retain the balanced four-method rotation. It records:

- `Generated_generation_ns`: source construction and write time;
- `Generated_compile_ns`: compilation and shared-object link time;
- `Generated_setup_ns`: repeated load, metadata validation, and plan creation;
- `Generated_full_setup_ns`: the sum of those three components;
- `Generated_source_bytes`, `Generated_shared_object_bytes`, and
  `Generated_text_bytes`: respectively UTF-8 source length, complete file
  length, and the `.text` section reported by GNU `size -A`;
- `Generated_plan_bytes`, `Generated_ns`, and `Generated/GS`: loaded-plan
  storage, steady-state reduction, and its GS ratio.

`Generated_algorithm`, `Generated_code_model`, and
`Generated_applicability` distinguish general GS specialization from the
degree-restricted López--Dahab baseline. A generated implementation is retained even
when it loses; specialization status is not a performance conclusion.

The shared-object file size is contextual; `elf-text-section:v1` is the frozen
machine-code size metric. `make check` independently verifies nineteen
generated kernels, including the López--Dahab paper example and weights up to
65, against Naive
long division before the benchmark contract is tested.

For a versionable suite of exact supports, use a JSON Lines manifest:

```json
{"sample_id":"k283-example","provenance":"hand-constructed-example:v1","m":283,"taps":[0,7,12]}
{"sample_id":"empty-283","provenance":"synthetic-boundary:v1","m":283,"taps":[]}
```

```text
python3 bench/scripts/phase_diagram_benchmark.py \
  --binary build/reduction_benchmark \
  --manifest supports.jsonl --output bench/data/exact.csv \
  --inputs 8 --repeats 5 --seed 1 --no-naive
```

Manifest taps obey the same canonical contract. `sample_id` must be nonempty
and unique, while `provenance` is a nonempty label for the modulus source or
generation rule. The driver rejects unordered, duplicate, nonintegral, and
out-of-range taps rather than normalizing them silently.

The manifest stores only the source fields `sample_id`, `provenance`, `m`, and
`taps`. The driver deterministically derives and emits `s`, `h`, `Delta_min`,
`feedback_stages`, `active_tap_counts`, `feedback_active_tap_sum`, and `W_fb`;
the native benchmark reads all four schedule quantities from the actual GS
plan, and the driver checks those values together with `m`, `s`, `h`, taps,
and `Delta_min` against an independent derivation.
Here `active_tap_counts` serializes

\[
h_k=\#\{t\in T:2^k(m-t)<m\}
\]

with semicolons, `feedback_active_tap_sum` is \(\sum_k h_k\), and `W_fb` is
\(\sum_{t,k}[m-2^k(m-t)]_+\). A zero-stage profile is written as `-`.
Irreducibility is not part of this general reduction contract; field-level
experiments must record it separately when their claims require it.

To render the geometry independently of any winner assignment, run:

```text
python3 bench/scripts/plot_phase_geometry.py \
  --input bench/data/phase_raw.csv \
  --output bench/data/phase_geometry.svg
```

The SVG contains one panel per fixed $m$, places modulus Hamming weight $h$ on
the horizontal axis, and places $m/\Delta_{\min}$ on a base-two logarithmic
vertical axis. Repeated measurement trials for one `sample_id` collapse to one
geometry point after their coordinates agree. The $T=\varnothing$ boundary
has no $\Delta_{\min}$ and is therefore counted and annotated separately
rather than assigned a fabricated location on the logarithmic axis. This plot
validates only the phase coordinates; it does not select or color a winner.

To validate and plot the exact feedback-depth law from the emitted native
schedule, run:

```text
python3 bench/scripts/plot_feedback_depth.py \
  --input bench/data/phase_raw.csv \
  --output bench/data/feedback_depth.svg
```

The left panel plots `feedback_stages` against $\log_2\Delta_{\min}$ for each
fixed $m$; the right panel restricts to $\Delta_{\min}=1$ and plots the same
stage count against $\log_2m$. The plotter rejects any row that differs from
$\lceil\log_2(m/\Delta_{\min})\rceil$ before rendering. This is schedule-depth
evidence, not a wall-clock latency or gate-depth measurement.

The `scalar-source-v1` model covers the complete portable-scalar
`gs_reduce_into()` data path for a canonical degree-below-$2m$ input and an
$m$-bit output. It counts only data-word operations: descriptor accesses,
indices, comparisons, branches, and scalar locals are excluded. The emitted
fields are:

| Field | Source-level meaning |
|---|---|
| `GS_source_aligned_word_contributions` | feedback/assembly contributions whose bit offset is zero |
| `GS_source_cross_word_contributions` | feedback/assembly contributions assembled across a word boundary |
| `GS_source_word_shifts` | `word_t` shifts by a nonzero bit offset |
| `GS_source_word_xors` | XOR expressions on `word_t` data |
| `GS_source_logical_word_reads` | reads from input, output, or GS state word arrays |
| `GS_source_logical_word_writes` | writes to output or GS state word arrays |
| `GS_source_scratch_words` | plan-owned mutable GS state, including its sentinel word |

Aligned contributions therefore do not count as bit shifts. Cross-word
contributions are recorded separately; the shift total also includes the
possibly unaligned extraction of the high half. The model follows the current
scalar fast paths, including adjacent-word load reuse, but it is not a count
of compiler instructions, cache accesses, hardware loads/stores, or minimum
XOR complexity. Cross-vector shifts are not applicable to this scalar model
and require a separately named SIMD model if that implementation is added.
The phase-diagram driver independently reconstructs `scalar-source-v1` from
$m$, the complete taps, and the emitted word width, and rejects mismatches.

### Cost-model correlation and residual diagnostics

`analyze_gs_cost_model.py` consumes raw phase-diagram rows and keeps the two
sides of the comparison distinct.  Its measured response is `GS_ns` under
`reduction-steady-state:v1`; its predictors are `W_fb` and the individual
`scalar-source-v1` word-XOR, word-shift, logical-read, and logical-write
counts.  Nanoseconds are not labelled as cycles, and none of the source
counts is labelled as an instruction count or hardware event.

The script first takes the median `GS_ns` across retained trials for each
exact `sample_id`.  Repeated samples of the same $(m,\mathtt{taps})$ are then
collapsed to one support-level observation, so the empty support and random
collisions cannot receive accidental statistical weight.  Spearman
correlations are computed separately within each fixed-$m$ panel, preventing
degree scaling from creating a spurious correlation.  The simple predictive
baseline is an affine fit from source word XORs to `GS_ns`, evaluated by
leave-one-support-out prediction rather than in-sample residuals.  At least
four distinct supports per fixed-$m$ panel are required.  The input must come
from one recorded environment; the analyzer also rejects missing or duplicate
measurement-trial indices and rows below the requested trial, batch-repeat,
or warm-up minima.
For each unique support it additionally reports a deterministic 10,000-resample
bootstrap 95% interval for the median.  A relative interval half-width above
1% sets `timing_status=uncertain`; uncertain observations remain in the output
and are counted in every summary rather than silently deleted.

The residual diagnostics partition each panel three ways:

- logical-access fraction as a source-level proxy for memory pressure;
- zero, one, two-to-four, and at least five feedback stages as a proxy for
  stage barriers; and
- aligned-only, mixed, and cross-word-only contributions.

A regime is flagged when its median bias or median absolute relative residual
exceeds the explicit `--mismatch-threshold` (10% by default).  These labels
identify where a simple XOR-count predictor is inadequate; they do not prove
that cache traffic, barriers, or alignment caused the residual.  Establishing
such causality requires separately named hardware-counter evidence.

For a paper-grade input with the frozen minimum of 31 retained trials per
support, run:

```text
python3 bench/scripts/analyze_gs_cost_model.py \
  --input bench/data/phase_raw.csv \
  --correlations bench/data/gs_cost_correlations.csv \
  --residuals bench/data/gs_cost_residuals.csv \
  --diagnostics bench/data/gs_cost_diagnostics.csv \
  --min-trials 31 --mismatch-threshold 0.10
```

All three outputs remain local raw/derived experiment data under
`bench/data/`.  The correlation output states `response=GS_ns` and the kind
of every predictor.  The residual output preserves each exact support and its
three diagnostic regimes.  The diagnostic output records the threshold,
sample count, and `causal_claim=none-source-proxy-only`.

The current native binary emits
`input_distribution=uniform-full-range:v1` and
`timing_scope=reduction-steady-state:v1`, together with
`setup_scope=modulus-plan:v1` and the four per-method setup timings.

## Shared Work--Feedback-Depth--Setup Tradeoff Map

This is a shared classical experiment for every paper branch.  At fixed
degree, it must report a point for each exact sampled support with:

- scheduled feedback work
  \(W_{\mathrm{fb}}=\sum_{r,k}[m-2^kd_r]_+\);
- feedback depth
  \(D_{\mathrm{fb}}=\lceil\log_2(m/\Delta_{\min})\rceil\), with the
  explicit zero-feedback boundary; and
- per-method setup time and the amortized objective
  \(T_{\mathrm{setup}}+K T_{\mathrm{reduce}}\) for stated values of \(K\).

The plot is a measured work--feedback-depth--setup tradeoff, not an
instruction-count or minimum-XOR-circuit claim.  It must keep support geometry,
input distribution, compiler, machine, seed, timing boundary, and multiplication
backend with every row.  The existing
`bench/scripts/phase_diagram_benchmark.py` supplies matched per-support timing
rows and records the exact support, active-tap profile, \(W_{\mathrm{fb}}\),
and raw per-method setup and reduction timings. The plotting step must derive
the amortized quantities for explicitly stated values of $K$; it must not add
a hidden default $K$ to the raw data.

The implemented derivation is:

```text
python3 bench/scripts/plot_setup_tradeoff.py \
  --input bench/data/phase_raw.csv \
  --amortization-data bench/data/setup-amortization.csv \
  --amortization-figure bench/data/setup-amortization.svg \
  --tradeoff-figure bench/data/work-depth-setup.svg \
  --k-values 1 2 4 8 16 32 64 128 256 512 1024 \
  --plot-methods BarrettGF2X LopezDahabLoop
```

`--k-values` and the plotted competitor set are mandatory rather than hidden
defaults. The derived CSV retains every exact support and the compiler,
gf2x, machine, affinity, frequency, seed, implementation, backend, timing,
setup, and storage-model provenance. It reports the medians of the separately
sampled setup and reduction components and then computes
$T_{\rm setup}+K T_{\rm reduce}$ and its per-reduction average. The
amortization panels summarize the median and p10--p90 range across the measured
controlled cells; those quantiles describe the designed grid, not a random
modulus population. The tradeoff panels plot every support at
$\bigl(\log_2(W_{\rm fb}+1),D_{\rm fb}\bigr)$ and color it by
$\log_2(T_{\rm setup,GS}+1)$.
