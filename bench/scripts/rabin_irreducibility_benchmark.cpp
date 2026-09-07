#define _POSIX_C_SOURCE 200809L

extern "C" {
#include "gf2_square.h"
#include "reduction.h"
}

#include <NTL/GF2X.h>
#include <NTL/GF2XFactoring.h>

#include <algorithm>
#include <chrono>
#include <cerrno>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using Clock = std::chrono::steady_clock;

enum class MethodKind { FFR, Barrett, Serial, LopezDahab, NTL };

struct Timings {
    double total_ns;
    double setup_ns;
    double chain_ns;
    double check_ns;
};

struct ReferenceChain {
    NTL::GF2X half;
    NTL::GF2X final;
};

static double elapsed_ns(Clock::time_point start, Clock::time_point stop) {
    return std::chrono::duration<double, std::nano>(stop - start).count();
}

static size_t parse_size(const char *text, const char *name) {
    if (!text || !*text || *text == '-')
        throw std::runtime_error(std::string("invalid ") + name);
    char *end = nullptr;
    errno = 0;
    unsigned long long value = std::strtoull(text, &end, 10);
    if (errno == ERANGE || !end || *end
            || value > std::numeric_limits<size_t>::max())
        throw std::runtime_error(std::string("invalid ") + name);
    return static_cast<size_t>(value);
}

static std::vector<size_t> parse_taps(const std::string &text, size_t m) {
    std::vector<size_t> taps;
    size_t start = 0;
    while (start < text.size()) {
        size_t comma = text.find(',', start);
        std::string item = text.substr(start, comma - start);
        size_t tap = parse_size(item.c_str(), "tap");
        if (tap >= m || (!taps.empty() && tap <= taps.back()))
            throw std::runtime_error("taps must be sorted, distinct, and below m");
        taps.push_back(tap);
        if (comma == std::string::npos) break;
        start = comma + 1;
        if (start == text.size()) throw std::runtime_error("empty tap");
    }
    if (taps.empty()) throw std::runtime_error("Rabin modulus needs taps");
    return taps;
}

static std::string serialize_taps(const std::vector<size_t> &taps) {
    std::string result;
    for (size_t i = 0; i < taps.size(); ++i) {
        if (i) result += ';';
        result += std::to_string(taps[i]);
    }
    return result;
}

static NTL::GF2X modulus_to_ntl(size_t m, const std::vector<size_t> &taps) {
    NTL::GF2X modulus;
    NTL::SetCoeff(modulus, static_cast<long>(m));
    for (size_t tap : taps) NTL::SetCoeff(modulus, static_cast<long>(tap));
    return modulus;
}

static NTL::GF2X poly_to_ntl(const poly_t &poly, size_t bits) {
    NTL::GF2X result;
    for (size_t word_index = 0; word_index < poly.n; ++word_index) {
        word_t word = poly.v[word_index];
        while (word) {
            unsigned offset = static_cast<unsigned>(__builtin_ctzl(word));
            size_t exponent = word_index * WORD_BITS + offset;
            if (exponent < bits)
                NTL::SetCoeff(result, static_cast<long>(exponent));
            word &= word - 1;
        }
    }
    return result;
}

static poly_t make_modulus(size_t m, const std::vector<size_t> &taps) {
    poly_t modulus = poly_new(poly_words_for_bits(m + 1));
    poly_set_bit(&modulus, m);
    for (size_t tap : taps) poly_set_bit(&modulus, tap);
    return modulus;
}

static reduction_method make_method(MethodKind kind,
                                    const std::vector<size_t> &taps,
                                    const poly_t &modulus, size_t m) {
    switch (kind) {
    case MethodKind::FFR:
        return reduction_make_gs(taps.data(), taps.size(), m);
    case MethodKind::Barrett:
        return reduction_make_barrett(&modulus, m);
    case MethodKind::Serial:
        return reduction_make_serial(taps.data(), taps.size(), m);
    case MethodKind::LopezDahab:
        return reduction_make_lopez_dahab(taps.data(), taps.size(), m);
    case MethodKind::NTL:
        break;
    }
    throw std::runtime_error("NTL is not a matched reducer");
}

static const char *method_name(MethodKind kind) {
    switch (kind) {
    case MethodKind::FFR: return "FFR";
    case MethodKind::Barrett: return "BarrettGF2X";
    case MethodKind::Serial: return "Serial";
    case MethodKind::LopezDahab: return "LopezDahabLoop";
    case MethodKind::NTL: return "NTL-IterIrredTest";
    }
    return "unknown";
}

static ReferenceChain ntl_reference_chain(const NTL::GF2X &modulus,
                                          size_t m) {
    NTL::GF2XModulus plan(modulus);
    NTL::GF2X state;
    NTL::SetCoeff(state, 1);
    ReferenceChain result;
    for (size_t step = 1; step <= m; ++step) {
        NTL::SqrMod(state, state, plan);
        if (step == m / 2) result.half = state;
    }
    result.final = state;
    return result;
}

static bool rabin_check(const poly_t &half, const poly_t &final,
                        const NTL::GF2X &modulus, size_t m) {
    NTL::GF2X x;
    NTL::SetCoeff(x, 1);
    NTL::GF2X half_minus_x = poly_to_ntl(half, m);
    add(half_minus_x, half_minus_x, x);
    NTL::GF2X divisor;
    NTL::GCD(divisor, half_minus_x, modulus);
    return NTL::IsOne(divisor) && poly_to_ntl(final, m) == x;
}

static Timings run_matched(MethodKind kind,
                           const std::vector<size_t> &taps,
                           const poly_t &modulus,
                           const NTL::GF2X &ntl_modulus, size_t m,
                           const ReferenceChain *reference) {
    poly_t state = poly_new(poly_words_for_bits(m));
    poly_t next = poly_new(poly_words_for_bits(m));
    poly_t square = poly_new(poly_words_for_bits(2 * m));
    poly_t half = poly_new(poly_words_for_bits(m));
    poly_set_bit(&state, 1);

    Clock::time_point total_start = Clock::now();
    reduction_method method = make_method(kind, taps, modulus, m);
    Clock::time_point setup_stop = Clock::now();
    for (size_t step = 1; step <= m; ++step) {
        gf2_square_to_2m(&state, m, &square);
        method.reduce_into(&square, method.context, &next);
        std::swap(state, next);
        if (step == m / 2)
            std::memcpy(half.v, state.v, half.n * sizeof(*half.v));
    }
    Clock::time_point chain_stop = Clock::now();
    bool passed = rabin_check(half, state, ntl_modulus, m);
    Clock::time_point total_stop = Clock::now();

    if (reference && (poly_to_ntl(half, m) != reference->half
            || poly_to_ntl(state, m) != reference->final))
        throw std::runtime_error(std::string(method_name(kind))
                                 + " disagrees with NTL checkpoints");
    if (!passed)
        throw std::runtime_error(std::string(method_name(kind))
                                 + " rejected an irreducible modulus");

    reduction_method_destroy(&method);
    poly_free(&state);
    poly_free(&next);
    poly_free(&square);
    poly_free(&half);
    return {
        elapsed_ns(total_start, total_stop),
        elapsed_ns(total_start, setup_stop),
        elapsed_ns(setup_stop, chain_stop),
        elapsed_ns(chain_stop, total_stop),
    };
}

static Timings run_ntl(const NTL::GF2X &modulus) {
    Clock::time_point start = Clock::now();
    long result = NTL::IterIrredTest(modulus);
    Clock::time_point stop = Clock::now();
    if (result != 1) throw std::runtime_error("NTL rejected the pilot modulus");
    double total = elapsed_ns(start, stop);
    return {total, std::numeric_limits<double>::quiet_NaN(),
            std::numeric_limits<double>::quiet_NaN(),
            std::numeric_limits<double>::quiet_NaN()};
}

int main(int argc, char **argv) try {
    size_t m = 0;
    size_t trials = 0;
    size_t warmups = 1;
    bool with_serial = true;
    std::string tap_text;
    std::string sample_id = "unspecified";
    for (int i = 1; i < argc; ++i) {
        auto need_value = [&](const char *option) -> const char * {
            if (++i == argc) throw std::runtime_error(std::string(option) + " needs a value");
            return argv[i];
        };
        if (!std::strcmp(argv[i], "--m")) m = parse_size(need_value("--m"), "m");
        else if (!std::strcmp(argv[i], "--taps")) tap_text = need_value("--taps");
        else if (!std::strcmp(argv[i], "--trials")) trials = parse_size(need_value("--trials"), "trials");
        else if (!std::strcmp(argv[i], "--warmups")) warmups = parse_size(need_value("--warmups"), "warmups");
        else if (!std::strcmp(argv[i], "--sample-id")) sample_id = need_value("--sample-id");
        else if (!std::strcmp(argv[i], "--no-serial")) with_serial = false;
        else throw std::runtime_error(std::string("unknown option: ") + argv[i]);
    }
    if (m < 2 || (m & (m - 1)) || m > static_cast<size_t>(LONG_MAX))
        throw std::runtime_error("m must be a representable power of two");
    if (!trials || !warmups)
        throw std::runtime_error("trials and warmups must be positive");
    std::vector<size_t> taps = parse_taps(tap_text, m);
    if (taps.front() != 0)
        throw std::runtime_error("an irreducible degree-above-one modulus needs tap 0");

    poly_t modulus = make_modulus(m, taps);
    NTL::GF2X ntl_modulus = modulus_to_ntl(m, taps);
    if (NTL::IterIrredTest(ntl_modulus) != 1)
        throw std::runtime_error("modulus is not irreducible according to NTL");
    ReferenceChain reference = ntl_reference_chain(ntl_modulus, m);
    std::vector<MethodKind> methods = {MethodKind::FFR, MethodKind::Barrett};
    if (with_serial) methods.push_back(MethodKind::Serial);
    methods.push_back(MethodKind::NTL);
    if (m > WORD_BITS && m - taps.back() >= WORD_BITS)
        methods.insert(methods.end() - 1, MethodKind::LopezDahab);

    for (MethodKind method : methods) {
        if (method == MethodKind::NTL) (void)run_ntl(ntl_modulus);
        else (void)run_matched(method, taps, modulus, ntl_modulus, m, &reference);
    }
    for (size_t warmup = 1; warmup < warmups; ++warmup) {
        for (MethodKind method : methods) {
            if (method == MethodKind::NTL) (void)run_ntl(ntl_modulus);
            else (void)run_matched(method, taps, modulus, ntl_modulus, m, nullptr);
        }
    }

    std::cout << "schema,sample_id,m,h,delta_min,taps,trial,order,method,"
                 "e2e_ns,setup_ns,chain_ns,check_ns,result\n";
    std::string serialized = serialize_taps(taps);
    size_t delta_min = m - taps.back();
    for (size_t trial = 0; trial < trials; ++trial) {
        for (size_t position = 0; position < methods.size(); ++position) {
            MethodKind method = methods[(trial + position) % methods.size()];
            Timings timing = method == MethodKind::NTL
                ? run_ntl(ntl_modulus)
                : run_matched(method, taps, modulus, ntl_modulus, m, nullptr);
            std::cout << "rabin-power-of-two-irred:v1," << sample_id << ','
                      << m << ',' << taps.size() + 1 << ',' << delta_min << ','
                      << serialized << ',' << trial << ',' << position << ','
                      << method_name(method) << ',' << timing.total_ns << ','
                      << timing.setup_ns << ',' << timing.chain_ns << ','
                      << timing.check_ns << ",irreducible\n";
        }
    }
    poly_free(&modulus);
    return 0;
} catch (const std::exception &error) {
    std::cerr << "rabin benchmark: " << error.what() << '\n';
    return 1;
}
