# Native gf2x benchmark

`barrett_gf2x_benchmark.c` compares the C Generalized Suwako reducer, naive
polynomial long division, and Barrett reduction whose two polynomial products
call the upstream `gf2x_mul` API. The reciprocal polynomial is precomputed
outside the timed reduction path.

The benchmark requires a native gf2x installation. Set `GF2X_PREFIX` to its
installation prefix and build with MinGW or GCC:

```text
make -C src/native GF2X_PREFIX=/path/to/gf2x
src/native/barrett_gf2x_benchmark 12 64 5 > bench/barrett_gf2x_benchmark.csv
```

Arguments are `supports`, `inputs`, and `repeats`. The output is reduction-only
timing in nanoseconds per input. Correctness is checked against both reducers
before each timed trial.

For a large `m` run that skips naive long division, pass a custom `m` and the
`no-naive` flag:

```text
src/native/barrett_gf2x_benchmark 6 8 5 1000000 no-naive > bench/barrett_gf2x_1e6.csv
```
