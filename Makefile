CC ?= gcc
PYTHON ?= python3
GF2X_PREFIX ?= /usr/local
CFLAGS ?= -O3 -std=c11 -Wall -Wextra

TARGET = build/reduction_benchmark
CHECK_TARGET = build/reduction_correctness_check
GS_STAGE_CHECK_TARGET = build/gs_stage_correctness_check
GS_COMPONENT_CHECK_TARGET = build/gs_component_correctness_check
SPARSE_SHIFT_CHECK_TARGET = build/sparse_shift_correctness_check
SAN_CHECK_TARGET = build/reduction_correctness_check_sanitize
SAN_STAGE_CHECK_TARGET = build/gs_stage_correctness_check_sanitize
SAN_COMPONENT_CHECK_TARGET = build/gs_component_correctness_check_sanitize
SAN_SHIFT_CHECK_TARGET = build/sparse_shift_correctness_check_sanitize
SAN_CFLAGS = -O1 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer \
	-fsanitize=address,undefined
BENCH_SOURCES = bench/scripts/reduction_benchmark.c src/reduction.c src/GS.c src/barrett.c src/naive.c src/serial.c
CHECK_SOURCES = tests/check_reduction.c src/reduction.c src/GS.c src/barrett.c src/naive.c src/serial.c

all: $(TARGET)

$(TARGET): $(BENCH_SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ $(BENCH_SOURCES) \
		-L$(GF2X_PREFIX)/lib -lgf2x

$(CHECK_TARGET): $(CHECK_SOURCES) include/*.h tests/reduction_regressions.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		$(CHECK_SOURCES) -L$(GF2X_PREFIX)/lib -lgf2x

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

$(SAN_CHECK_TARGET): $(CHECK_SOURCES) include/*.h tests/reduction_regressions.h
	mkdir -p build
	$(CC) $(SAN_CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		$(CHECK_SOURCES) -L$(GF2X_PREFIX)/lib -lgf2x

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

serial-benchmark: $(TARGET)

check: $(CHECK_TARGET) $(GS_STAGE_CHECK_TARGET) \
	$(GS_COMPONENT_CHECK_TARGET) $(SPARSE_SHIFT_CHECK_TARGET) $(TARGET)
	$(CHECK_TARGET)
	$(GS_STAGE_CHECK_TARGET)
	$(GS_COMPONENT_CHECK_TARGET)
	$(SPARSE_SHIFT_CHECK_TARGET)
	$(PYTHON) tests/check_experiment_contract.py --binary $(TARGET)
	$(PYTHON) tests/check_cost_model_analysis.py
	$(MAKE) check-theory

check-theory:
	$(PYTHON) tests/check_theory_round1_gf2.py
	$(PYTHON) tests/check_theory_round2_algebras.py

check-sanitize: $(SAN_CHECK_TARGET) $(SAN_STAGE_CHECK_TARGET) \
	$(SAN_COMPONENT_CHECK_TARGET) $(SAN_SHIFT_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_STAGE_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_COMPONENT_CHECK_TARGET)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 $(SAN_SHIFT_CHECK_TARGET)

check-serial: check

clean:
	rm -f $(TARGET) $(CHECK_TARGET) $(GS_STAGE_CHECK_TARGET) \
		$(GS_COMPONENT_CHECK_TARGET) $(SPARSE_SHIFT_CHECK_TARGET) \
		$(SAN_CHECK_TARGET) $(SAN_STAGE_CHECK_TARGET) \
		$(SAN_COMPONENT_CHECK_TARGET) $(SAN_SHIFT_CHECK_TARGET)
