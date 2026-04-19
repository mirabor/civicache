CXX      := g++
CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -Iinclude -MMD -MP
LDFLAGS  :=

SRCDIR := src
INCDIR := include
OBJDIR := build

SOURCES := $(wildcard $(SRCDIR)/*.cpp)
OBJECTS := $(patsubst $(SRCDIR)/%.cpp, $(OBJDIR)/%.o, $(SOURCES))
TARGET  := cache_sim

.PHONY: all clean run run-sweep plots

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

$(OBJDIR)/%.o: $(SRCDIR)/%.cpp | $(OBJDIR)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(OBJDIR):
	mkdir -p $(OBJDIR)

-include $(OBJECTS:.o=.d)

clean:
	rm -rf $(OBJDIR) $(TARGET)

# Quick run with defaults (synthetic Zipf, alpha=0.8). Writes to congress subdir
# per D-06; callers override --output-dir to target other workloads.
run: $(TARGET)
	mkdir -p results/congress
	./$(TARGET) --output-dir results/congress

# Full run: MRC + alpha sweep + SHARDS into results/congress/
run-sweep: $(TARGET)
	mkdir -p results/congress
	./$(TARGET) --alpha-sweep --shards --output-dir results/congress

# Generate plots from results/congress/ (default --workload=congress)
plots:
	python3 scripts/plot_results.py
