#include "generated.h"

#ifdef _WIN32
#include <windows.h>
typedef HMODULE shared_object_handle;
#else
#include <dlfcn.h>
typedef void *shared_object_handle;
#endif

struct generated_plan {
    shared_object_handle shared_object;
    const generated_plugin_v1 *plugin;
    void *plugin_plan;
};

static void *required_symbol(shared_object_handle handle, const char *name) {
#ifdef _WIN32
    FARPROC symbol = GetProcAddress(handle, name);
    if (!symbol) die("generated reducer entry point is missing");
    return (void *)(uintptr_t)symbol;
#else
    dlerror();
    void *symbol = dlsym(handle, name);
    const char *error = dlerror();
    if (error || !symbol) die("generated reducer entry point is missing");
    return symbol;
#endif
}

generated_plan *generated_plan_load(const char *path, size_t m,
                                    const size_t *taps, size_t tap_count) {
    if (!path || !*path) die("generated reducer path is missing");
    if (tap_count && !taps) die("generated reducer taps are missing");

#ifdef _WIN32
    shared_object_handle handle = LoadLibraryA(path);
#else
    shared_object_handle handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
#endif
    if (!handle) die("failed to load generated reducer shared object");

    generated_plugin_entry_v1 entry;
    *(void **)(&entry) = required_symbol(handle, EXSUWAKO_GENERATED_ENTRY);
    const generated_plugin_v1 *plugin = entry();
    if (!plugin || plugin->abi_version != EXSUWAKO_GENERATED_ABI_V1)
        die("generated reducer ABI mismatch");
    if (plugin->m != m || plugin->tap_count != tap_count)
        die("generated reducer modulus metadata mismatch");
    for (size_t i = 0; i < tap_count; ++i)
        if (plugin->taps[i] != taps[i])
            die("generated reducer tap metadata mismatch");
    if (!plugin->plan_create || !plugin->plan_destroy
            || !plugin->plan_storage_bytes || !plugin->reduce_into)
        die("generated reducer function table is incomplete");

    generated_plan *plan = malloc(sizeof(*plan));
    if (!plan) die("allocation failed");
    plan->shared_object = handle;
    plan->plugin = plugin;
    plan->plugin_plan = plugin->plan_create();
    if (!plan->plugin_plan) die("generated reducer plan creation failed");
    return plan;
}

void generated_plan_destroy(generated_plan *plan) {
    if (!plan) return;
    plan->plugin->plan_destroy(plan->plugin_plan);
#ifdef _WIN32
    FreeLibrary(plan->shared_object);
#else
    dlclose(plan->shared_object);
#endif
    free(plan);
}

size_t generated_plan_storage_bytes(const generated_plan *plan) {
    return plan
        ? sizeof(*plan) + plan->plugin->plan_storage_bytes(plan->plugin_plan)
        : 0;
}

void generated_reduce_into(const poly_t *input, generated_plan *plan,
                           poly_t *output) {
    plan->plugin->reduce_into(input, plan->plugin_plan, output);
}
