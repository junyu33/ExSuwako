# Native gf2x benchmark

`barrett_gf2x_benchmark.c` compares the C Generalized Suwako reducer, naive
polynomial long division, and Barrett reduction whose two polynomial products
call the upstream `gf2x_mul` API. The reciprocal polynomial is precomputed
outside the timed reduction path.

The benchmark requires a native gf2x installation. Set `GF2X_PREFIX` to its
installation prefix and build with MinGW:

```text
make -C src/native GF2X_PREFIX=C:/path/to/gf2x
src/native/barrett_gf2x_benchmark.exe 12 64 5 > bench/barrett_gf2x_benchmark.csv
```

Arguments are `supports`, `inputs`, and `repeats`. The output is reduction-only
timing in nanoseconds per input. Correctness is checked against both reducers
before each timed trial.
