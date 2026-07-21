# Native gf2x benchmark

The native benchmark is split into `src/GS.c`, `src/naive.c`, `src/barrett.c`,
and `src/exp.c`; public headers are under `include/`.
The two Barrett products call the upstream `gf2x_mul` API. The reciprocal
polynomial is precomputed outside the timed reduction path.

The benchmark requires a native gf2x installation. Set `GF2X_PREFIX` to its
installation prefix and build with MinGW or GCC:

```text
make GF2X_PREFIX=/path/to/gf2x
build/barrett_gf2x_benchmark 12 64 5 > bench/barrett_gf2x_benchmark.csv
```

Arguments are `supports`, `inputs`, and `repeats`. The output is reduction-only
timing in nanoseconds per input. Correctness is checked against both reducers
before each timed trial.

For a large `m` run that skips naive long division, pass a custom `m` and the
`no-naive` flag:

```text
build/barrett_gf2x_benchmark 6 8 5 1000000 no-naive > bench/barrett_gf2x_1e6.csv
```
