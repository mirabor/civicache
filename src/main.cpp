#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <memory>
#include <iomanip>
#include <unordered_map>
#include <chrono>
#include <cstring>

#include "cache.h"
#include "trace_gen.h"
#include "workload_stats.h"
#include "shards.h"
#include "hash_util.h"

// ==================== Helpers ====================

static void print_usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [options]\n"
              << "Options:\n"
              << "  --trace <file>         Use a trace CSV instead of synthetic generation\n"
              << "  --cache-sizes <list>   Comma-separated cache size fractions (default: 0.001,0.005,0.01,0.02,0.05,0.1)\n"
              << "  --policies <list>      Comma-separated policies: lru,fifo,clock,s3fifo,sieve (default: all)\n"
              << "  --output-dir <dir>     Output directory (default: results)\n"
              << "  --num-requests <n>     Number of synthetic requests (default: 500000)\n"
              << "  --num-objects <n>      Number of unique objects for synthetic trace (default: 50000)\n"
              << "  --alpha <a>            Zipf alpha for single run (default: 0.8)\n"
              << "  --alpha-sweep          Run alpha sensitivity sweep\n"
              << "  --shards               Run SHARDS MRC construction\n"
              << "  --shards-exact         Also compute exact stack distances (slow, small traces only)\n"
              << "  --replay-zipf          Resample a real trace with Zipf popularity (use with --trace)\n"
              << "  -h, --help             Show this help\n";
}

static std::vector<std::string> split(const std::string& s, char delim) {
    std::vector<std::string> tokens;
    std::istringstream iss(s);
    std::string token;
    while (std::getline(iss, token, delim)) {
        if (!token.empty()) tokens.push_back(token);
    }
    return tokens;
}

// Compute total working set size in bytes (sum of first-seen object sizes)
static uint64_t working_set_bytes(const std::vector<TraceEntry>& trace) {
    uint64_t total = 0;
    std::unordered_map<std::string, bool> seen;
    for (auto& e : trace) {
        if (!seen.count(e.key)) {
            seen[e.key] = true;
            total += e.size;
        }
    }
    return total;
}

// Create a cache policy by name
static std::unique_ptr<CachePolicy> make_policy(const std::string& name, uint64_t capacity) {
    if (name == "lru")    return std::make_unique<LRUCache>(capacity);
    if (name == "fifo")   return std::make_unique<FIFOCache>(capacity);
    if (name == "clock")  return std::make_unique<CLOCKCache>(capacity);
    if (name == "s3fifo") return std::make_unique<S3FIFOCache>(capacity);
    if (name == "sieve")  return std::make_unique<SIEVECache>(capacity);
    return nullptr;
}

static void run_simulation(const std::vector<TraceEntry>& trace, CachePolicy& policy) {
    policy.reset();
    for (auto& e : trace) {
        policy.access(e.key, e.size);
    }
}

// ==================== Main ====================

int main(int argc, char* argv[]) {
    // Defaults
    std::string trace_file;
    std::string output_dir = "results";
    std::vector<double> cache_fracs = {0.001, 0.005, 0.01, 0.02, 0.05, 0.1};
    std::vector<std::string> policy_names = {"lru", "fifo", "clock", "s3fifo", "sieve"};
    uint64_t num_requests = 500000;
    uint64_t num_objects = 50000;
    double alpha = 0.8;
    bool alpha_sweep = false;
    bool run_shards = false;
    bool shards_exact = false;
    bool replay_zipf_mode = false;

    // Parse CLI arguments
    for (int i = 1; i < argc; i++) {
        if (std::strcmp(argv[i], "--trace") == 0 && i + 1 < argc) {
            trace_file = argv[++i];
        } else if (std::strcmp(argv[i], "--cache-sizes") == 0 && i + 1 < argc) {
            cache_fracs.clear();
            for (auto& s : split(argv[++i], ',')) cache_fracs.push_back(std::stod(s));
        } else if (std::strcmp(argv[i], "--policies") == 0 && i + 1 < argc) {
            policy_names = split(argv[++i], ',');
        } else if (std::strcmp(argv[i], "--output-dir") == 0 && i + 1 < argc) {
            output_dir = argv[++i];
        } else if (std::strcmp(argv[i], "--num-requests") == 0 && i + 1 < argc) {
            num_requests = std::stoull(argv[++i]);
        } else if (std::strcmp(argv[i], "--num-objects") == 0 && i + 1 < argc) {
            num_objects = std::stoull(argv[++i]);
        } else if (std::strcmp(argv[i], "--alpha") == 0 && i + 1 < argc) {
            alpha = std::stod(argv[++i]);
        } else if (std::strcmp(argv[i], "--alpha-sweep") == 0) {
            alpha_sweep = true;
        } else if (std::strcmp(argv[i], "--shards") == 0) {
            run_shards = true;
        } else if (std::strcmp(argv[i], "--shards-exact") == 0) {
            shards_exact = true;
            run_shards = true;
        } else if (std::strcmp(argv[i], "--replay-zipf") == 0) {
            replay_zipf_mode = true;
        } else if (std::strcmp(argv[i], "-h") == 0 || std::strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else {
            std::cerr << "Unknown option: " << argv[i] << "\n";
            print_usage(argv[0]);
            return 1;
        }
    }

    if (!hash_util_self_test()) {
        std::cerr << "hash_util self-test failed — aborting\n";
        return 1;
    }

    std::cout << "=== Cache Policy Simulator for Legislative Workloads ===\n\n";

    // ---------- Load or generate trace ----------
    std::vector<TraceEntry> trace;
    std::vector<TraceEntry> raw_trace; // kept for replay-zipf alpha sweep
    if (!trace_file.empty() && replay_zipf_mode) {
        std::cout << "Loading trace: " << trace_file << "\n";
        raw_trace = load_trace(trace_file);
        if (raw_trace.empty()) {
            std::cerr << "Failed to load trace.\n";
            return 1;
        }
        trace = replay_zipf(raw_trace, num_requests, alpha);
    } else if (!trace_file.empty()) {
        std::cout << "Loading trace: " << trace_file << "\n";
        trace = load_trace(trace_file);
        if (trace.empty()) {
            std::cerr << "Failed to load trace.\n";
            return 1;
        }
    } else {
        std::cout << "Generating synthetic Zipf trace (alpha=" << alpha
                  << ", n=" << num_requests << ", objects=" << num_objects << ")\n";
        trace = generate_zipf_trace(num_requests, num_objects, alpha);
    }

    // ---------- Workload characterization ----------
    auto ws = characterize(trace);
    std::cout << "\nWorkload summary:\n"
              << "  Requests: " << ws.total_requests << "\n"
              << "  Unique objects: " << ws.unique_objects << "\n"
              << "  Estimated Zipf alpha: " << std::fixed << std::setprecision(3) << ws.zipf_alpha << "\n"
              << "  One-hit-wonder ratio (10%): " << ws.one_hit_wonder_ratio << "\n"
              << "  Size (mean/median/p99): " << (int)ws.mean_size << " / "
              << (int)ws.median_size << " / " << (int)ws.p99_size << " bytes\n\n";

    uint64_t total_bytes = working_set_bytes(trace);

    // ---------- Miss ratio curves ----------
    {
        std::string csv_path = output_dir + "/mrc.csv";
        std::ofstream csv(csv_path);
        csv << "cache_frac,cache_size_bytes,policy,miss_ratio,byte_miss_ratio,accesses_per_sec\n";

        // Table header
        std::cout << std::setw(12) << "Cache%";
        for (auto& pn : policy_names) {
            std::string label = pn;
            if (pn == "s3fifo") label = "S3-FIFO";
            else for (auto& c : label) c = toupper(c);
            std::cout << std::setw(10) << label;
        }
        std::cout << "\n" << std::string(12 + 10 * policy_names.size(), '-') << "\n";

        for (double frac : cache_fracs) {
            uint64_t cache_bytes = (uint64_t)(total_bytes * frac);
            std::cout << std::setw(10) << std::setprecision(1) << (frac * 100) << "%";

            for (auto& pn : policy_names) {
                auto p = make_policy(pn, cache_bytes);
                if (!p) {
                    std::cerr << "Unknown policy: " << pn << "\n";
                    continue;
                }
                auto t_start = std::chrono::steady_clock::now();
                run_simulation(trace, *p);
                auto t_end = std::chrono::steady_clock::now();
                double elapsed = std::chrono::duration<double>(t_end - t_start).count();
                double accesses_per_sec = elapsed > 0 ? (double)trace.size() / elapsed : 0.0;

                std::cout << std::setw(10) << std::setprecision(4) << p->stats.miss_ratio();
                csv << frac << "," << cache_bytes << "," << p->name() << ","
                    << p->stats.miss_ratio() << "," << p->stats.byte_miss_ratio() << ","
                    << accesses_per_sec << "\n";
            }
            std::cout << "\n";
        }
        csv.close();
        std::cout << "\nMRC data written to " << csv_path << "\n\n";
    }

    // ---------- Alpha sensitivity sweep ----------
    if (alpha_sweep) {
        std::vector<double> alphas = {0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2};
        std::string csv_path = output_dir + "/alpha_sensitivity.csv";
        std::ofstream csv(csv_path);
        csv << "alpha,policy,miss_ratio,byte_miss_ratio,accesses_per_sec\n";

        std::cout << "Alpha Sensitivity (cache = 1% of working set)\n";
        std::cout << std::setw(8) << "Alpha";
        for (auto& pn : policy_names) {
            std::string label = pn;
            if (pn == "s3fifo") label = "S3-FIFO";
            else for (auto& c : label) c = toupper(c);
            std::cout << std::setw(10) << label;
        }
        std::cout << "\n" << std::string(8 + 10 * policy_names.size(), '-') << "\n";

        // Hoist prepare_objects out of the alpha loop: the dedupe+shuffle is
        // stable across alpha values (D-11, REFACTOR-02). Avoids O(N) redundant
        // work 7x per sweep. Empty when the raw_trace fallback is in use.
        std::vector<std::pair<std::string, uint64_t>> prepared_objects;
        if (!raw_trace.empty()) {
            prepared_objects = prepare_objects(raw_trace);  // default seed=42
        }

        for (double a : alphas) {
            auto sweep_trace = !prepared_objects.empty()
                ? generate_replay_trace(prepared_objects, num_requests, a)
                : generate_zipf_trace(num_requests, num_objects, a);
            uint64_t wb = working_set_bytes(sweep_trace);
            uint64_t cache_bytes = wb / 100;

            std::cout << std::setw(6) << std::setprecision(1) << a;
            for (auto& pn : policy_names) {
                auto p = make_policy(pn, cache_bytes);
                auto t_start = std::chrono::steady_clock::now();
                run_simulation(sweep_trace, *p);
                auto t_end = std::chrono::steady_clock::now();
                double elapsed = std::chrono::duration<double>(t_end - t_start).count();
                double accesses_per_sec = elapsed > 0 ? (double)sweep_trace.size() / elapsed : 0.0;

                std::cout << std::setw(10) << std::setprecision(4) << p->stats.miss_ratio();
                csv << a << "," << p->name() << ","
                    << p->stats.miss_ratio() << "," << p->stats.byte_miss_ratio() << ","
                    << accesses_per_sec << "\n";
            }
            std::cout << "\n";
        }
        csv.close();
        std::cout << "\nAlpha sensitivity data written to " << csv_path << "\n\n";
    }

    // ---------- One-hit-wonder analysis ----------
    {
        std::string csv_path = output_dir + "/one_hit_wonder.csv";
        std::ofstream csv(csv_path);
        csv << "window_frac,ohw_ratio\n";

        std::cout << "One-Hit-Wonder Ratio at Various Window Lengths\n";
        std::vector<double> windows = {0.01, 0.05, 0.1, 0.2, 0.5, 1.0};
        for (double w : windows) {
            double ratio = one_hit_wonder_ratio(trace, w);
            std::cout << "  Window=" << std::setw(4) << (int)(w * 100) << "% -> OHW ratio: "
                      << std::setprecision(3) << ratio << "\n";
            csv << w << "," << ratio << "\n";
        }
        csv.close();
        std::cout << "\n";
    }

    // ---------- SHARDS ----------
    if (run_shards) {
        std::cout << "=== SHARDS MRC Construction ===\n";
        std::vector<double> rates = {0.001, 0.01, 0.1};
        // MRC x-axis is in object count (stack distances are object-based)
        uint64_t max_cache = ws.unique_objects;

        std::string csv_path = output_dir + "/shards_mrc.csv";
        std::ofstream csv(csv_path);
        csv << "sampling_rate,cache_size_objects,miss_ratio\n";

        for (double rate : rates) {
            SHARDS shards(rate);
            auto t_start = std::chrono::steady_clock::now();
            shards.process(trace);
            auto t_end = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration<double>(t_end - t_start).count();

            auto mrc = shards.build_mrc(max_cache, 100);
            std::cout << "  Rate=" << rate * 100 << "% : sampled " << shards.total_sampled()
                      << " accesses (" << std::setprecision(2) << elapsed << "s)\n";

            for (auto& pt : mrc) {
                csv << rate << "," << pt.cache_size << "," << std::setprecision(6) << pt.miss_ratio << "\n";
            }
        }
        csv.close();
        std::cout << "SHARDS MRC data written to " << csv_path << "\n";

        // Exact stack distances for validation (small traces only)
        if (shards_exact) {
            if (trace.size() > 50000) {
                std::cout << "  (Skipping exact SD: trace too large, " << trace.size() << " > 50000)\n";
            } else {
                std::cout << "  Computing exact stack distances...\n";
                auto sd = exact_stack_distances(trace);
                auto exact_mrc = mrc_from_stack_distances(sd, trace.size(), max_cache, 100);

                std::string exact_path = output_dir + "/exact_mrc.csv";
                std::ofstream exact_csv(exact_path);
                exact_csv << "cache_size_objects,miss_ratio\n";
                for (auto& pt : exact_mrc) {
                    exact_csv << pt.cache_size << "," << pt.miss_ratio << "\n";
                }
                exact_csv.close();
                std::cout << "  Exact MRC written to " << exact_path << "\n";

                // Compute error metrics: MAE and max absolute error per sampling rate
                std::string err_path = output_dir + "/shards_error.csv";
                std::ofstream err_csv(err_path);
                err_csv << "sampling_rate,mae,max_abs_error,num_points\n";

                std::cout << "\n  SHARDS Error vs. Exact MRC:\n";
                std::cout << std::setw(10) << "Rate" << std::setw(10) << "MAE"
                          << std::setw(12) << "Max Error" << "\n";

                for (double rate : rates) {
                    SHARDS s(rate);
                    s.process(trace);
                    auto approx = s.build_mrc(max_cache, 100);

                    // Match points: both vectors have same num_points and step size
                    size_t n = std::min(approx.size(), exact_mrc.size());
                    double sum_err = 0, max_err = 0;
                    for (size_t j = 0; j < n; j++) {
                        double err = std::abs(approx[j].miss_ratio - exact_mrc[j].miss_ratio);
                        sum_err += err;
                        max_err = std::max(max_err, err);
                    }
                    double mae = n > 0 ? sum_err / n : 0;

                    std::cout << std::setw(8) << std::setprecision(1) << rate * 100 << "%"
                              << std::setw(10) << std::setprecision(4) << mae
                              << std::setw(12) << std::setprecision(4) << max_err << "\n";
                    err_csv << rate << "," << mae << "," << max_err << "," << n << "\n";
                }
                err_csv.close();
                std::cout << "  Error metrics written to " << err_path << "\n";
            }
        }
        std::cout << "\n";
    }

    std::cout << "Done. Results written to " << output_dir << "/\n";
    return 0;
}
