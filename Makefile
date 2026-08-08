CC ?= gcc
PYTHON ?= python3
GF2X_PREFIX ?= /usr/local
CFLAGS ?= -O3 -std=c11 -Wall -Wextra

TARGET = build/reduction_benchmark
CHECK_TARGET = build/reduction_correctness_check
BENCH_SOURCES = bench/scripts/reduction_benchmark.c src/reduction.c src/GS.c src/barrett.c src/naive.c src/serial.c
CHECK_SOURCES = tests/check_reduction.c src/reduction.c src/GS.c src/barrett.c src/naive.c src/serial.c

all: $(TARGET)

$(TARGET): $(BENCH_SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ $(BENCH_SOURCES) \
		-L$(GF2X_PREFIX)/lib -lgf2x

$(CHECK_TARGET): $(CHECK_SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		$(CHECK_SOURCES) -L$(GF2X_PREFIX)/lib -lgf2x

serial-benchmark: $(TARGET)

check: $(CHECK_TARGET)
	$(CHECK_TARGET)

check-serial: check

check-quantum-resources:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) \
		bench/scripts/quantum_reduction_resources.py --preset all > /dev/null

clean:
	rm -f $(TARGET) $(CHECK_TARGET)
