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

# Quick run with defaults (synthetic Zipf, alpha=0.8). Writes to congress subdir
# per D-06; callers override --output-dir to target other workloads.
run: $(TARGET)
	mkdir -p results/congress
	./$(TARGET) --output-dir results/congress

# Full run: MRC + alpha sweep + SHARDS into results/congress/
run-sweep: $(TARGET)
	mkdir -p results/congress
	./$(TARGET) --alpha-sweep --shards --output-dir results/congress

# Generate plots from results/congress/ (default --workload=congress).
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
	$(PLOT_PYTHON) scripts/plot_results.py

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
