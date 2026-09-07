# Paper Artifact Contract

This directory tracks the reproducibility contract, not the benchmark CSV
payload. The repository policy keeps all local and released measurement CSV
files outside Git. A copy of the external dataset must be placed at
`DATA_ROOT/paper-v1-raw.csv`; its row count and SHA-256 are frozen in
[`paper-v1.json`](paper-v1.json).

The canonical dataset contains 67,576 retained paper-grade trial rows from
three explicitly recorded experiment commits. Every row contains the complete
tap set, command, seed, compiler, flags, linked gf2x path, machine, affinity,
frequency policy, timing/setup/storage contracts, and binary digest. The
artifact driver rejects a missing, modified, or non-paper-grade dataset before
running an analysis.

The winner analyzer normally rejects mixed experiment metadata. The artifact
uses its explicit `--allow-metadata-cohorts` mode: all environment fields must
still agree, while each recorded Git commit must map one-to-one to exactly one
benchmark binary digest. This preserves the three documented collection
cohorts without pretending that their commit identifiers are identical.

From a clean checkout, with the external dataset available under `bench/data`,
the principal commands are:

```text
make check
make artifact-cost-model
make artifact-microbenchmark ARTIFACT_CPU=0
make artifact-paper
make artifact-rabin
```

- `make check` is the correctness command.
- `make artifact-cost-model` is the measured cost-model command.
- `make artifact-microbenchmark` is a short, metadata-complete native
  reduction run over the permanent regression manifest; it is an artifact
  smoke test, not a recollection of the 67,576-row paper dataset.
- `make artifact-paper` verifies the external dataset and regenerates the
  winner analysis, region summaries, phase/depth/slice/setup/work figures,
  random-support geometry, cost-model summaries, and paper table sources.
- `make artifact-rabin` independently verifies
  `DATA_ROOT/rabin-main-5d91ddc.csv` against
  [`rabin-v1.json`](rabin-v1.json), then rebuilds the complete-test summary
  and Rabin E2E figure.  Its 465 rows come from one clean experiment commit
  and are not mixed with the reduction-only dataset.

Override `ARTIFACT_DATA` and `ARTIFACT_OUTPUT` when the CSV payload and derived
outputs live outside the checkout. The committed config contains expected
hashes for every derived output. `artifact-report.json` records the invoked
commands, environment, experiment commits, binary digests, and observed output
hashes; it is generated locally and is not part of the deterministic hash set.

The artifact establishes the reported primary portable-scalar platform only.
It makes no architecture-independent speed claim and therefore does not
require or imply a second-machine result.

[`validation-4465388.json`](validation-4465388.json) records the current
fresh-worktree validation of the 26-output paper artifact and the two-output
Rabin artifact. The predecessor 24-output audit remains preserved in
[`validation-68af036.json`](validation-68af036.json). Complete correctness
logs, short microbenchmark CSV and metadata, and generated artifact reports
remain beside the external CSV payload and are authenticated by the hashes in
the corresponding records.
