#include "trace_gen.h"
#include <fstream>
#include <sstream>
#include <iostream>

// ==================== Zipf Generator ====================

ZipfGenerator::ZipfGenerator(uint64_t n, double alpha, uint64_t seed) : rng_(seed) {
    cdf_.resize(n);
    double sum = 0;
    for (uint64_t i = 0; i < n; i++) {
        sum += 1.0 / std::pow(i + 1, alpha);
    }
    double cumulative = 0;
    for (uint64_t i = 0; i < n; i++) {
        cumulative += (1.0 / std::pow(i + 1, alpha)) / sum;
        cdf_[i] = cumulative;
    }
}

uint64_t ZipfGenerator::next() {
    double r = dist_(rng_);
    return std::lower_bound(cdf_.begin(), cdf_.end(), r) - cdf_.begin();
}

// ==================== Trace I/O ====================

std::vector<TraceEntry> load_trace(const std::string& filename) {
    std::vector<TraceEntry> trace;
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Error: cannot open " << filename << "\n";
        return trace;
    }
    std::string line;
    std::getline(file, line); // skip header
    while (std::getline(file, line)) {
        std::istringstream iss(line);
        TraceEntry e;
        char delim;
        iss >> e.timestamp >> delim;
        std::getline(iss, e.key, ',');
        iss >> e.size;
        trace.push_back(e);
    }
    return trace;
}

std::vector<TraceEntry> generate_zipf_trace(uint64_t num_requests, uint64_t num_objects,
                                             double alpha, uint64_t seed) {
    ZipfGenerator zipf(num_objects, alpha, seed);
    std::mt19937_64 size_rng(seed + 1);
    // Log-normal size distribution (median ~4KB)
    std::lognormal_distribution<double> size_dist(8.3, 1.5);

    std::vector<TraceEntry> trace;
    trace.reserve(num_requests);
    for (uint64_t i = 0; i < num_requests; i++) {
        uint64_t obj = zipf.next();
        uint64_t sz = std::max((uint64_t)64, (uint64_t)size_dist(size_rng));
        sz = std::min(sz, (uint64_t)10'000'000); // cap 10MB
        trace.push_back({i, "obj_" + std::to_string(obj), sz});
    }
    return trace;
}
