#pragma once
#include <cstdint>
#include <string>
#include <unordered_map>
#include <list>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <deque>

struct TraceEntry {
    uint64_t timestamp;
    std::string key;
    uint64_t size; // object size in bytes
};

struct CacheStats {
    uint64_t hits = 0;
    uint64_t misses = 0;
    uint64_t byte_hits = 0;
    uint64_t byte_misses = 0;

    double miss_ratio() const {
        uint64_t total = hits + misses;
        return total == 0 ? 0.0 : (double)misses / total;
    }
    double byte_miss_ratio() const {
        uint64_t total = byte_hits + byte_misses;
        return total == 0 ? 0.0 : (double)byte_misses / total;
    }
};

// Abstract base class
class CachePolicy {
public:
    virtual ~CachePolicy() = default;
    virtual bool access(const std::string& key, uint64_t size) = 0; // returns true on hit
    virtual std::string name() const = 0;
    virtual void reset() = 0;
    
    CacheStats stats;
    
    void record(bool hit, uint64_t size) {
        if (hit) { stats.hits++; stats.byte_hits += size; }
        else     { stats.misses++; stats.byte_misses += size; }
    }
};

// ==================== LRU ====================
class LRUCache : public CachePolicy {
    uint64_t capacity_;
    uint64_t current_size_ = 0;
    std::list<std::pair<std::string, uint64_t>> order_; // key, size
    std::unordered_map<std::string, std::list<std::pair<std::string, uint64_t>>::iterator> map_;

public:
    LRUCache(uint64_t capacity) : capacity_(capacity) {}
    
    bool access(const std::string& key, uint64_t size) override {
        auto it = map_.find(key);
        if (it != map_.end()) {
            current_size_ -= it->second->second;
            it->second->second = size;
            current_size_ += size;
            order_.splice(order_.end(), order_, it->second);
            record(true, size);
            return true;
        }
        // Miss: insert
        while (current_size_ + size > capacity_ && !order_.empty()) {
            current_size_ -= order_.front().second;
            map_.erase(order_.front().first);
            order_.pop_front();
        }
        order_.push_back({key, size});
        map_[key] = std::prev(order_.end());
        current_size_ += size;
        record(false, size);
        return false;
    }
    
    std::string name() const override { return "LRU"; }
    void reset() override { order_.clear(); map_.clear(); current_size_ = 0; stats = {}; }
};

// ==================== FIFO ====================
class FIFOCache : public CachePolicy {
    uint64_t capacity_;
    uint64_t current_size_ = 0;
    std::list<std::pair<std::string, uint64_t>> queue_;
    std::unordered_map<std::string, std::list<std::pair<std::string, uint64_t>>::iterator> map_;

public:
    FIFOCache(uint64_t capacity) : capacity_(capacity) {}
    
    bool access(const std::string& key, uint64_t size) override {
        auto it = map_.find(key);
        if (it != map_.end()) {
            current_size_ -= it->second->second;
            it->second->second = size;
            current_size_ += size;
            record(true, size);
            return true;
        }
        while (current_size_ + size > capacity_ && !queue_.empty()) {
            current_size_ -= queue_.front().second;
            map_.erase(queue_.front().first);
            queue_.pop_front();
        }
        queue_.push_back({key, size});
        map_[key] = std::prev(queue_.end());
        current_size_ += size;
        record(false, size);
        return false;
    }
    
    std::string name() const override { return "FIFO"; }
    void reset() override { queue_.clear(); map_.clear(); current_size_ = 0; stats = {}; }
};

// ==================== CLOCK ====================
class CLOCKCache : public CachePolicy {
    uint64_t capacity_;
    uint64_t current_size_ = 0;
    
    struct Entry {
        std::string key;
        uint64_t size;
        bool referenced;
    };
    
    std::vector<Entry> buffer_;
    std::unordered_map<std::string, size_t> map_; // key -> index
    size_t hand_ = 0;
    size_t count_ = 0;

public:
    CLOCKCache(uint64_t capacity) : capacity_(capacity) {
        buffer_.reserve(1024);
    }
    
    bool access(const std::string& key, uint64_t size) override {
        auto it = map_.find(key);
        if (it != map_.end()) {
            current_size_ -= buffer_[it->second].size;
            buffer_[it->second].size = size;
            current_size_ += size;
            buffer_[it->second].referenced = true;
            record(true, size);
            return true;
        }
        // Evict until enough space
        while (current_size_ + size > capacity_ && count_ > 0) {
            evict_one();
        }
        // Insert
        if (count_ < buffer_.size()) {
            // Find an empty slot (from eviction)
            size_t idx = hand_;
            for (size_t i = 0; i < buffer_.size(); i++) {
                size_t pos = (hand_ + i) % buffer_.size();
                if (buffer_[pos].key.empty()) { idx = pos; break; }
            }
            buffer_[idx] = {key, size, false};
            map_[key] = idx;
        } else {
            buffer_.push_back({key, size, false});
            map_[key] = buffer_.size() - 1;
        }
        current_size_ += size;
        count_++;
        record(false, size);
        return false;
    }
    
    void evict_one() {
        while (true) {
            if (hand_ >= buffer_.size()) hand_ = 0;
            auto& e = buffer_[hand_];
            if (!e.key.empty()) {
                if (e.referenced) {
                    e.referenced = false;
                } else {
                    current_size_ -= e.size;
                    map_.erase(e.key);
                    e.key.clear();
                    count_--;
                    hand_ = (hand_ + 1) % buffer_.size();
                    return;
                }
            }
            hand_ = (hand_ + 1) % buffer_.size();
        }
    }
    
    std::string name() const override { return "CLOCK"; }
    void reset() override { buffer_.clear(); map_.clear(); hand_ = 0; count_ = 0; current_size_ = 0; stats = {}; }
};

// ==================== S3-FIFO ====================
// Small FIFO (10%) -> Main FIFO (90%), with ghost filter
// Per Yang et al. (SOSP '23): items enter small on miss (unless in ghost,
// then go directly to main). On eviction from small, items with freq > 0
// promote to main; freq == 0 items go to ghost.
class S3FIFOCache : public CachePolicy {
    uint64_t total_capacity_;
    uint64_t small_capacity_;
    uint64_t main_capacity_;

    // Small FIFO queue with frequency tracking
    struct SmallEntry {
        std::string key;
        uint64_t size;
        uint8_t freq; // incremented on hit while in small
    };
    std::list<SmallEntry> small_queue_;
    std::unordered_map<std::string, std::list<SmallEntry>::iterator> small_map_;
    uint64_t small_size_ = 0;

    // Main FIFO queue with frequency bits
    struct MainEntry {
        std::string key;
        uint64_t size;
        uint8_t freq; // 0-3
    };
    std::list<MainEntry> main_queue_;
    std::unordered_map<std::string, std::list<MainEntry>::iterator> main_map_;
    uint64_t main_size_ = 0;

    // Ghost filter: FIFO-ordered for correct eviction
    std::deque<std::string> ghost_queue_;
    std::unordered_set<std::string> ghost_set_;

public:
    S3FIFOCache(uint64_t capacity) : total_capacity_(capacity) {
        small_capacity_ = std::max((uint64_t)1, capacity / 10);
        main_capacity_ = capacity - small_capacity_;
    }

    bool access(const std::string& key, uint64_t size) override {
        // Check main
        auto mit = main_map_.find(key);
        if (mit != main_map_.end()) {
            main_size_ -= mit->second->size;
            mit->second->size = size;
            main_size_ += size;
            if (mit->second->freq < 3) mit->second->freq++;
            record(true, size);
            return true;
        }
        // Check small — increment freq on hit
        auto sit = small_map_.find(key);
        if (sit != small_map_.end()) {
            small_size_ -= sit->second->size;
            sit->second->size = size;
            small_size_ += size;
            if (sit->second->freq < 3) sit->second->freq++;
            record(true, size);
            return true;
        }
        // Miss: if in ghost, insert into main; otherwise into small
        if (ghost_set_.count(key)) {
            ghost_set_.erase(key);
            // Remove from ghost queue (lazy: just leave stale entries, cleaned on trim)
            while (main_size_ + size > main_capacity_ && !main_queue_.empty()) {
                evict_main();
            }
            main_queue_.push_back({key, size, 0});
            main_map_[key] = std::prev(main_queue_.end());
            main_size_ += size;
        } else {
            while (small_size_ + size > small_capacity_ && !small_queue_.empty()) {
                evict_small();
            }
            small_queue_.push_back({key, size, 0});
            small_map_[key] = std::prev(small_queue_.end());
            small_size_ += size;
        }
        record(false, size);
        return false;
    }

    void evict_small() {
        auto& front = small_queue_.front();
        std::string key = front.key;
        uint64_t sz = front.size;
        uint8_t freq = front.freq;
        small_map_.erase(key);
        small_size_ -= sz;
        small_queue_.pop_front();

        if (freq > 0) {
            // Re-accessed while in small: promote to main
            while (main_size_ + sz > main_capacity_ && !main_queue_.empty()) {
                evict_main();
            }
            main_queue_.push_back({key, sz, 0});
            main_map_[key] = std::prev(main_queue_.end());
            main_size_ += sz;
        } else {
            // Not re-accessed: add to ghost
            ghost_set_.insert(key);
            ghost_queue_.push_back(key);
            // Trim ghost FIFO from the front (oldest first)
            size_t ghost_max = total_capacity_ / 100 + 1000;
            while (ghost_queue_.size() > ghost_max) {
                ghost_set_.erase(ghost_queue_.front());
                ghost_queue_.pop_front();
            }
        }
    }

    void evict_main() {
        while (!main_queue_.empty()) {
            auto& front = main_queue_.front();
            if (front.freq > 0) {
                front.freq--;
                main_queue_.splice(main_queue_.end(), main_queue_, main_queue_.begin());
            } else {
                main_size_ -= front.size;
                main_map_.erase(front.key);
                main_queue_.pop_front();
                return;
            }
        }
    }

    std::string name() const override { return "S3-FIFO"; }
    void reset() override {
        small_queue_.clear(); small_map_.clear(); small_size_ = 0;
        main_queue_.clear(); main_map_.clear(); main_size_ = 0;
        ghost_queue_.clear(); ghost_set_.clear(); stats = {};
    }
};

// ==================== SIEVE ====================
// SIEVE: lazy promotion with a hand pointer
class SIEVECache : public CachePolicy {
    uint64_t capacity_;
    uint64_t current_size_ = 0;
    
    struct Node {
        std::string key;
        uint64_t size;
        bool visited;
    };
    
    std::list<Node> queue_;
    std::unordered_map<std::string, std::list<Node>::iterator> map_;
    std::list<Node>::iterator hand_;
    bool hand_valid_ = false;

public:
    SIEVECache(uint64_t capacity) : capacity_(capacity) {}
    
    bool access(const std::string& key, uint64_t size) override {
        auto it = map_.find(key);
        if (it != map_.end()) {
            current_size_ -= it->second->size;
            it->second->size = size;
            current_size_ += size;
            it->second->visited = true;
            record(true, size);
            return true;
        }
        // Miss: evict until space
        while (current_size_ + size > capacity_ && !queue_.empty()) {
            evict_one();
        }
        // Insert at head
        queue_.push_front({key, size, false});
        map_[key] = queue_.begin();
        current_size_ += size;
        record(false, size);
        return false;
    }
    
    void evict_one() {
        if (!hand_valid_ || hand_ == queue_.end()) {
            hand_ = std::prev(queue_.end()); // tail
            hand_valid_ = true;
        }
        while (hand_->visited) {
            hand_->visited = false;
            if (hand_ == queue_.begin()) {
                hand_ = std::prev(queue_.end());
            } else {
                --hand_;
            }
        }
        auto victim = hand_;
        // Move hand before erasing
        if (hand_ == queue_.begin()) {
            hand_ = std::prev(queue_.end());
            // But if queue will be size 1, handle after erase
            if (hand_ == victim) hand_valid_ = false;
        } else {
            --hand_;
        }
        current_size_ -= victim->size;
        map_.erase(victim->key);
        queue_.erase(victim);
        if (queue_.empty()) hand_valid_ = false;
    }
    
    std::string name() const override { return "SIEVE"; }
    void reset() override { queue_.clear(); map_.clear(); current_size_ = 0; hand_valid_ = false; stats = {}; }
};
