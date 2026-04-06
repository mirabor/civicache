#!/usr/bin/env python3
"""
Congress.gov API trace collector.

Queries the Congress.gov API for bills, amendments, and roll-call votes,
logging each request as a trace CSV row: timestamp,key,size

Usage:
    export CONGRESS_API_KEY=your_key
    python3 scripts/collect_trace.py --requests 5000 --output traces/congress_trace.csv

The trace format matches what the cache simulator expects.
"""

import argparse
import csv
import os
import random
import sys
import time

import requests

BASE_URL = "https://api.congress.gov/v3"

# Endpoint templates and their parameter ranges
ENDPOINTS = {
    "bill": {
        "path": "/bill/{congress}/{type}/{number}",
        "congresses": list(range(93, 120)),  # 93rd through 119th
        "types": ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"],
    },
    "amendment": {
        "path": "/amendment/{congress}/{type}/{number}",
        "congresses": list(range(93, 120)),
        "types": ["hamdt", "samdt"],
    },
    "vote": {
        "path": "/roll-call-vote/{congress}/{chamber}/{session}/{number}",
        "congresses": list(range(101, 120)),
        "chambers": ["house", "senate"],
    },
}

# Weight toward 119th Congress (current)
CURRENT_CONGRESS = 119
CURRENT_CONGRESS_WEIGHT = 0.6  # 60% of bill/amendment requests target current


def get_api_key():
    key = os.environ.get("CONGRESS_API_KEY")
    if not key:
        print("Error: set CONGRESS_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    return key


def pick_congress(congresses):
    """Pick a congress number, weighted toward the current one."""
    if CURRENT_CONGRESS in congresses and random.random() < CURRENT_CONGRESS_WEIGHT:
        return CURRENT_CONGRESS
    return random.choice(congresses)


def generate_bill_request():
    congress = pick_congress(ENDPOINTS["bill"]["congresses"])
    bill_type = random.choice(ENDPOINTS["bill"]["types"])
    # Number ranges vary; HR bills go up to ~10000 in busy congresses
    max_num = 9000 if congress == CURRENT_CONGRESS else 5000
    number = random.randint(1, max_num)
    path = f"/bill/{congress}/{bill_type}/{number}"
    return path


def generate_amendment_request():
    congress = pick_congress(ENDPOINTS["amendment"]["congresses"])
    amdt_type = random.choice(ENDPOINTS["amendment"]["types"])
    number = random.randint(1, 3000)
    path = f"/amendment/{congress}/{amdt_type}/{number}"
    return path


def generate_vote_request():
    congress = pick_congress(ENDPOINTS["vote"]["congresses"])
    chamber = random.choice(ENDPOINTS["vote"]["chambers"])
    session = random.choice([1, 2])
    number = random.randint(1, 700)
    path = f"/roll-call-vote/{congress}/{chamber}/{session}/{number}"
    return path


def generate_request():
    """Pick a random endpoint type with realistic weights."""
    r = random.random()
    if r < 0.6:
        return generate_bill_request()
    elif r < 0.85:
        return generate_amendment_request()
    else:
        return generate_vote_request()


def collect_trace(api_key, num_requests, max_duration, output_path):
    """Collect API trace, respecting rate limits."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "key", "size"])

        start_time = time.time()
        session = requests.Session()
        session.params = {"api_key": api_key, "format": "json"}

        for i in range(num_requests):
            elapsed = time.time() - start_time
            if max_duration and elapsed >= max_duration:
                print(f"Reached time limit ({max_duration}s) after {i} requests")
                break

            endpoint = generate_request()
            url = BASE_URL + endpoint
            timestamp = int(time.time() * 1000)

            try:
                resp = session.get(url, timeout=10)
                size = len(resp.content)
                # Use endpoint path as the cache key
                key = endpoint.lstrip("/")
                writer.writerow([timestamp, key, size])

                if (i + 1) % 100 == 0:
                    print(f"  [{i+1}/{num_requests}] {elapsed:.0f}s elapsed, "
                          f"last: {key} ({size} bytes, HTTP {resp.status_code})")

            except requests.RequestException as e:
                print(f"  Request failed: {e}", file=sys.stderr)
                # Still log as a miss with 0 size
                writer.writerow([timestamp, endpoint.lstrip("/"), 0])

            # Rate limit: 1 request per second
            time.sleep(1.0)

    total_time = time.time() - start_time
    print(f"\nDone. Collected {min(i + 1, num_requests)} requests in {total_time:.0f}s")
    print(f"Trace saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Collect Congress.gov API trace")
    parser.add_argument("--requests", type=int, default=5000,
                        help="Number of requests to make (default: 5000)")
    parser.add_argument("--duration", type=int, default=14400,
                        help="Max duration in seconds (default: 14400 = 4 hours)")
    parser.add_argument("--output", default="traces/congress_trace.csv",
                        help="Output CSV path")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    api_key = get_api_key()

    print(f"Collecting {args.requests} requests (max {args.duration}s)")
    print(f"API key: {api_key[:8]}...")
    collect_trace(api_key, args.requests, args.duration, args.output)


if __name__ == "__main__":
    main()
