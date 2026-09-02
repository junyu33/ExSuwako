/*
 * Permanent exact native reduction cases.
 *
 * Add every minimized correctness failure here using mathematical bit
 * exponents, not machine-word dumps, so the case remains portable across word
 * widths. Benchmark-only anomalies belong in
 * bench/manifests/regression_supports.jsonl with their original seed and
 * provenance.
 */

static const size_t regression_m1_input[] = {0, 1};

static const size_t regression_m17_taps[] = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
};
static const size_t regression_m17_input[] = {0, 15, 16, 17, 31, 33};

static const size_t regression_m65_taps[] = {0, 1, 64};
static const size_t regression_m65_input[] = {0, 63, 64, 65, 127, 129};

static const size_t regression_m127_taps[] = {1, 63, 126};
static const size_t regression_m127_input[] = {
    0, 62, 63, 64, 126, 127, 128, 190, 252, 253
};

static const reduction_regression_case reduction_regressions[] = {
    {
        "regression-empty-m1", 1,
        NULL, 0,
        regression_m1_input,
        sizeof(regression_m1_input) / sizeof(regression_m1_input[0])
    },
    {
        "regression-dense-m17", 17,
        regression_m17_taps,
        sizeof(regression_m17_taps) / sizeof(regression_m17_taps[0]),
        regression_m17_input,
        sizeof(regression_m17_input) / sizeof(regression_m17_input[0])
    },
    {
        "regression-word-boundary-m65", 65,
        regression_m65_taps,
        sizeof(regression_m65_taps) / sizeof(regression_m65_taps[0]),
        regression_m65_input,
        sizeof(regression_m65_input) / sizeof(regression_m65_input[0])
    },
    {
        "regression-constant-free-m127", 127,
        regression_m127_taps,
        sizeof(regression_m127_taps) / sizeof(regression_m127_taps[0]),
        regression_m127_input,
        sizeof(regression_m127_input) / sizeof(regression_m127_input[0])
    },
};
