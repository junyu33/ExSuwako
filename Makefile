CC ?= gcc
GF2X_PREFIX ?= /usr/local
CFLAGS ?= -O3 -std=c11 -Wall -Wextra

TARGET = build/barrett_gf2x_benchmark
SOURCES = src/exp.c src/GS.c src/barrett.c src/naive.c

all: $(TARGET)

$(TARGET): $(SOURCES) include/*.h
	mkdir -p build
	$(CC) $(CFLAGS) -Iinclude -I$(GF2X_PREFIX)/include -o $@ $(SOURCES) \
		-L$(GF2X_PREFIX)/lib -lgf2x

clean:
	rm -f $(TARGET)
