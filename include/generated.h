#ifndef EXSUWAKO_GENERATED_H
#define EXSUWAKO_GENERATED_H

#include "poly.h"

#define EXSUWAKO_GENERATED_ABI_V1 1u
#define EXSUWAKO_GENERATED_ENTRY "exsuwako_generated_plugin_v1"
#ifdef _WIN32
#define EXSUWAKO_GENERATED_EXPORT __declspec(dllexport)
#else
#define EXSUWAKO_GENERATED_EXPORT __attribute__((visibility("default")))
#endif

typedef struct {
    unsigned abi_version;
    size_t m;
    size_t tap_count;
    const size_t *taps;
    void *(*plan_create)(void);
    void (*plan_destroy)(void *plan);
    size_t (*plan_storage_bytes)(const void *plan);
    void (*reduce_into)(const poly_t *input, void *plan, poly_t *output);
} generated_plugin_v1;

typedef const generated_plugin_v1 *(*generated_plugin_entry_v1)(void);

typedef struct generated_plan generated_plan;

generated_plan *generated_plan_load(const char *path, size_t m,
                                    const size_t *taps, size_t tap_count);
void generated_plan_destroy(generated_plan *plan);
size_t generated_plan_storage_bytes(const generated_plan *plan);
void generated_reduce_into(const poly_t *input, generated_plan *plan,
                           poly_t *output);

#endif
