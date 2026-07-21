CC ?= gcc
GF2X_PREFIX ?= C:/local/gf2x
CFLAGS ?= -O3 -std=c11 -Wall -Wextra

TARGET = barrett_gf2x_benchmark
SRC = exp.c gs.c barrett.c naive.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -I$(GF2X_PREFIX)/include -o $@ $< \
		-L$(GF2X_PREFIX)/lib -lgf2x

clean:
	rm -f $(TARGET)
