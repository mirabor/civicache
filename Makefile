CXX      := g++
CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -Iinclude -MMD -MP
LDFLAGS  :=

SRCDIR := src
INCDIR := include
OBJDIR := build

SOURCES := $(wildcard $(SRCDIR)/*.cpp)
OBJECTS := $(patsubst $(SRCDIR)/%.cpp, $(OBJDIR)/%.o, $(SOURCES))
TARGET  := cache_sim

.PHONY: all clean run run-sweep plots test

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

$(OBJDIR)/%.o: $(SRCDIR)/%.cpp | $(OBJDIR)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(OBJDIR):
	mkdir -p $(OBJDIR)

-include $(OBJECTS:.o=.d)

clean:
	rm -rf $(OBJDIR) $(TEST_OBJDIR) $(TARGET)

# Workload parameterization (Phase 3 D-12 / D-14). Default preserves prior
# behavior: plain `make run` / `make run-sweep` / `make plots` all target
# results/congress/ unchanged. To target the court trace, pass
# `WORKLOAD=court TRACE=traces/court_trace.csv`.
WORKLOAD ?= congress
WORKLOAD_RESULTS_DIR := results/$(WORKLOAD)

# Quick run with defaults (synthetic Zipf, alpha=0.8). Writes to
# results/$(WORKLOAD)/ (default: results/congress/).
run: $(TARGET)
	mkdir -p $(WORKLOAD_RESULTS_DIR)
	./$(TARGET) --output-dir $(WORKLOAD_RESULTS_DIR)

# Full run: MRC + alpha sweep into results/$(WORKLOAD)/.
# When TRACE is set, switch to replay-Zipf mode (Phase 3 court trace path)
# and drop --shards (SHARDS on court is not in Phase 3 scope; Phase 4 uses a
# separate synthetic 1M trace for SHARDS). When TRACE is empty (default),
# preserve Phase 1/2 behavior: synthetic-Zipf + SHARDS + alpha-sweep against
# results/congress/.
TRACE ?=
SWEEP_FLAGS := --alpha-sweep --shards --output-dir $(WORKLOAD_RESULTS_DIR)
ifneq ($(TRACE),)
SWEEP_FLAGS := --trace $(TRACE) --replay-zipf --alpha-sweep --output-dir $(WORKLOAD_RESULTS_DIR)
endif
run-sweep: $(TARGET)
	mkdir -p $(WORKLOAD_RESULTS_DIR)
	./$(TARGET) $(SWEEP_FLAGS)

# Generate plots from results/$(WORKLOAD)/.
#
# macOS libexpat workaround: Python 3.14's pyexpat requires a newer libexpat
# than /usr/lib/libexpat.1.dylib ships. The .venv's Python binary strips
# DYLD_LIBRARY_PATH (hardened runtime), so invoke the real Homebrew python
# directly and point DYLD_LIBRARY_PATH at the Homebrew libexpat; use
# PYTHONPATH to pick up matplotlib from the .venv's site-packages.
#
# Override by exporting PLOT_PYTHON and PLOT_PYTHONPATH if your setup differs.
PLOT_PYTHON ?= /opt/homebrew/opt/python@3.14/bin/python3.14
PLOT_PYTHONPATH ?= .venv/lib/python3.14/site-packages
plots:
	DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib \
	PYTHONPATH=$(PLOT_PYTHONPATH) \
	$(PLOT_PYTHON) scripts/plot_results.py --workload $(WORKLOAD)

# ==================== Test binary (D-04/D-05/D-07) ====================
# Standalone assertion-based test for W-TinyLFU + CountMinSketch.
# Separate build/test/ object dir so `make && make test` does not rebuild
# the main simulator (D-07). No third-party framework (D-06).
TEST_SRC     := tests/test_wtinylfu.cpp
TEST_OBJDIR  := build/test
TEST_OBJ     := $(TEST_OBJDIR)/test_wtinylfu.o
TEST_TARGET  := $(TEST_OBJDIR)/test_wtinylfu

$(TEST_OBJDIR):
	mkdir -p $(TEST_OBJDIR)

$(TEST_OBJ): $(TEST_SRC) | $(TEST_OBJDIR)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(TEST_TARGET): $(TEST_OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

# `make test` builds and runs the test binary. Non-zero exit on any failure.
test: $(TEST_TARGET)
	@echo "=== Running W-TinyLFU test suite ==="
	$(TEST_TARGET)
