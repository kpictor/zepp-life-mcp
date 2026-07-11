import json
import urllib.parse
from collections import defaultdict

har_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/quantumult-x-2026-07-10-122218.har"

with open(har_path, 'r', encoding='utf-8', errors='ignore') as f:
    data = json.load(f)

endpoints = defaultdict(int)
params_seen = defaultdict(set)

for entry in data['log']['entries']:
    url = entry['request']['url']
    method = entry['request']['method']
    
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path
    
    # filter for likely health/fitness APIs
    if "huami.com" in domain or "zepp" in domain or "xiaomi" in domain or "mi.com" in domain:
        endpoint = f"{method} {domain}{path}"
        endpoints[endpoint] += 1
        
        # collect some query params to understand what they are fetching
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'type' in query_params:
            for t in query_params['type']:
                params_seen[f"{endpoint} (type param)"].add(t)
        if 'eventType' in query_params:
            for t in query_params['eventType']:
                params_seen[f"{endpoint} (eventType param)"].add(t)

print("=== UNIQUE ENDPOINTS ===")
for ep, count in sorted(endpoints.items(), key=lambda x: x[1], reverse=True):
    print(f"{count:4d} {ep}")

print("\n=== TYPES SEEN IN PARAMS ===")
for k, v in params_seen.items():
    print(f"{k}: {', '.join(v)}")
