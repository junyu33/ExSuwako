CC ?= gcc
GF2X_PREFIX ?= /usr/local
CFLAGS ?= -O3 -std=c11 -Wall -Wextra

TARGET = build/barrett_gf2x_benchmark
SERIAL_CHECK = build/serial_correctness_check
SERIAL_TARGET = build/gs_serial_benchmark
SOURCES = src/exp.c src/GS.c src/barrett.c src/naive.c src/serial.c
SERIAL_CHECK_SOURCES = tests/check_serial.c src/GS.c src/naive.c src/serial.c
SERIAL_SOURCES = src/serial_exp.c src/GS.c src/serial.c

all: $(TARGET)

$(TARGET): $(SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ $(SOURCES) \
		-L$(GF2X_PREFIX)/lib -lgf2x

$(SERIAL_CHECK): $(SERIAL_CHECK_SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		$(SERIAL_CHECK_SOURCES) -L$(GF2X_PREFIX)/lib -lgf2x

$(SERIAL_TARGET): $(SERIAL_SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ \
		$(SERIAL_SOURCES) -L$(GF2X_PREFIX)/lib -lgf2x

serial-benchmark: $(SERIAL_TARGET)

check-serial: $(SERIAL_CHECK)
	$(SERIAL_CHECK)

clean:
	rm -f $(TARGET) $(SERIAL_CHECK) $(SERIAL_TARGET)
