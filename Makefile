CC ?= gcc
PYTHON ?= python3
GF2X_PREFIX ?= /usr/local
CFLAGS ?= -O3 -std=c11 -Wall -Wextra
ifeq ($(OS),Windows_NT)
DL_LIBS ?=
else
DL_LIBS ?= -ldl
endif
TARGET = build/reduction_benchmark
CHECK_TARGET = build/reduction_correctness_check
GS_STAGE_CHECK_TARGET = build/gs_stage_correctness_check
GS_COMPONENT_CHECK_TARGET = build/gs_component_correctness_check
SPARSE_SHIFT_CHECK_TARGET = build/sparse_shift_correctness_check
DENSE_CHECK_TARGET = build/dense_correctness_check
GENERATED_CHECK_TARGET = build/generated_correctness_check
SAN_CHECK_TARGET = build/reduction_correctness_check_sanitize
SAN_STAGE_CHECK_TARGET = build/gs_stage_correctness_check_sanitize
SAN_COMPONENT_CHECK_TARGET = build/gs_component_correctness_check_sanitize
SAN_SHIFT_CHECK_TARGET = build/sparse_shift_correctness_check_sanitize
SAN_DENSE_CHECK_TARGET = build/dense_correctness_check_sanitize
SAN_GENERATED_CHECK_TARGET = build/generated_correctness_check_sanitize
SAN_CFLAGS = -O1 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer \
	-fsanitize=address,undefined
REDUCTION_SOURCES = src/reduction.c src/GS.c src/barrett.c src/dense.c \
	src/generated.c src/lopez_dahab.c src/naive.c src/serial.c
BENCH_SOURCES = bench/scripts/reduction_benchmark.c $(REDUCTION_SOURCES)
CHECK_SOURCES = tests/check_reduction.c $(REDUCTION_SOURCES)

all: $(TARGET)

$(TARGET): $(BENCH_SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ $(BENCH_SOURCES) \
		-L$(GF2X_PREFIX)/lib -lgf2x $(DL_LIBS)

$(CHECK_TARGET): $(CHECK_SOURCES) include/*.h tests/reduction_regressions.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		$(CHECK_SOURCES) -L$(GF2X_PREFIX)/lib -lgf2x $(DL_LIBS)

$(GS_STAGE_CHECK_TARGET): tests/check_gs_stage.c src/GS.c include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_gs_stage.c -L$(GF2X_PREFIX)/lib -lgf2x

$(GS_COMPONENT_CHECK_TARGET): tests/check_gs_components.c src/GS.c include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_gs_components.c -L$(GF2X_PREFIX)/lib -lgf2x

$(SPARSE_SHIFT_CHECK_TARGET): tests/check_sparse_shift.c include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_sparse_shift.c -L$(GF2X_PREFIX)/lib -lgf2x

$(DENSE_CHECK_TARGET): tests/check_dense.c src/dense.c src/naive.c include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_dense.c src/dense.c src/naive.c \
		-L$(GF2X_PREFIX)/lib -lgf2x

$(GENERATED_CHECK_TARGET): tests/check_generated.c src/generated.c \
		src/naive.c include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_generated.c src/generated.c src/naive.c \
		-L$(GF2X_PREFIX)/lib -lgf2x $(DL_LIBS)

$(SAN_CHECK_TARGET): $(CHECK_SOURCES) include/*.h tests/reduction_regressions.h
	mkdir -p build
	$(CC) $(SAN_CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		$(CHECK_SOURCES) -L$(GF2X_PREFIX)/lib -lgf2x $(DL_LIBS)

$(SAN_STAGE_CHECK_TARGET): tests/check_gs_stage.c src/GS.c include/*.h
	mkdir -p build
	$(CC) $(SAN_CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_gs_stage.c -L$(GF2X_PREFIX)/lib -lgf2x

$(SAN_COMPONENT_CHECK_TARGET): tests/check_gs_components.c src/GS.c include/*.h
	mkdir -p build
	$(CC) $(SAN_CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_gs_components.c -L$(GF2X_PREFIX)/lib -lgf2x

$(SAN_SHIFT_CHECK_TARGET): tests/check_sparse_shift.c include/*.h
	mkdir -p build
	$(CC) $(SAN_CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_sparse_shift.c -L$(GF2X_PREFIX)/lib -lgf2x

$(SAN_DENSE_CHECK_TARGET): tests/check_dense.c src/dense.c src/naive.c include/*.h
	mkdir -p build
	$(CC) $(SAN_CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_dense.c src/dense.c src/naive.c \
		-L$(GF2X_PREFIX)/lib -lgf2x

$(SAN_GENERATED_CHECK_TARGET): tests/check_generated.c src/generated.c \
		src/naive.c include/*.h
	mkdir -p build
	$(CC) $(SAN_CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		tests/check_generated.c src/generated.c src/naive.c \
		-L$(GF2X_PREFIX)/lib -lgf2x $(DL_LIBS)

serial-benchmark: $(TARGET)

freeze-winner-manifests:
	$(PYTHON) bench/scripts/freeze_winner_manifests.py \
		--output-dir bench/manifests/paper

check: $(CHECK_TARGET) $(GS_STAGE_CHECK_TARGET) \
	$(GS_COMPONENT_CHECK_TARGET) $(SPARSE_SHIFT_CHECK_TARGET) \
	$(DENSE_CHECK_TARGET) $(GENERATED_CHECK_TARGET) $(TARGET)
	$(CHECK_TARGET)
	$(GS_STAGE_CHECK_TARGET)
	$(GS_COMPONENT_CHECK_TARGET)
	$(SPARSE_SHIFT_CHECK_TARGET)
	$(DENSE_CHECK_TARGET)
	$(PYTHON) tests/check_generated_reducer.py \
		--checker $(GENERATED_CHECK_TARGET) --binary $(TARGET) --cc "$(CC)" \
		--include include --gf2x-include $(GF2X_PREFIX)/include
	$(PYTHON) tests/check_experiment_contract.py --binary $(TARGET)
	$(PYTHON) tests/check_cost_model_analysis.py
	$(PYTHON) tests/check_phase_geometry_plot.py
	$(PYTHON) tests/check_controlled_supports.py
	$(PYTHON) tests/check_fixed_weight_summary.py
	$(PYTHON) tests/check_fixed_weight_manifest.py
	$(PYTHON) tests/check_winner_panels.py
	$(PYTHON) tests/check_benchmark_metadata.py --binary $(TARGET)
	$(MAKE) check-theory

check-theory:
	$(PYTHON) tests/check_theory_round1_gf2.py
	$(PYTHON) tests/check_theory_round2_algebras.py

check-sanitize: $(SAN_CHECK_TARGET) $(SAN_STAGE_CHECK_TARGET) \
	$(SAN_COMPONENT_CHECK_TARGET) $(SAN_SHIFT_CHECK_TARGET) \
	$(SAN_DENSE_CHECK_TARGET) $(SAN_GENERATED_CHECK_TARGET) $(TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_STAGE_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_COMPONENT_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_SHIFT_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_DENSE_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(PYTHON) tests/check_generated_reducer.py \
		--checker $(SAN_GENERATED_CHECK_TARGET) --binary $(TARGET) --cc "$(CC)" \
		--cflags "$(SAN_CFLAGS)" --include include \
		--gf2x-include $(GF2X_PREFIX)/include

check-serial: check

clean:
	rm -f $(TARGET) $(CHECK_TARGET) $(GS_STAGE_CHECK_TARGET) \
		$(GS_COMPONENT_CHECK_TARGET) $(SPARSE_SHIFT_CHECK_TARGET) \
		$(DENSE_CHECK_TARGET) \
		$(GENERATED_CHECK_TARGET) \
		$(SAN_CHECK_TARGET) $(SAN_STAGE_CHECK_TARGET) \
		$(SAN_COMPONENT_CHECK_TARGET) $(SAN_SHIFT_CHECK_TARGET) \
		$(SAN_DENSE_CHECK_TARGET) $(SAN_GENERATED_CHECK_TARGET)
