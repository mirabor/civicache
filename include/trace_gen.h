#pragma once
#include <vector>
#include <string>
#include <cstdint>
#include <random>
#include <algorithm>
#include <cmath>
#include "cache.h"

// Zipf distribution generator using inverse CDF sampling
class ZipfGenerator {
    std::vector<double> cdf_;
    std::mt19937_64 rng_;
    std::uniform_real_distribution<double> dist_{0.0, 1.0};

public:
    ZipfGenerator(uint64_t n, double alpha, uint64_t seed = 42);
    uint64_t next();
};

// Load a trace CSV (timestamp,key,size) with a one-line header
std::vector<TraceEntry> load_trace(const std::string& filename);

// Generate a synthetic Zipf-distributed trace with log-normal object sizes
std::vector<TraceEntry> generate_zipf_trace(uint64_t num_requests, uint64_t num_objects,
                                             double alpha, uint64_t seed = 42);
