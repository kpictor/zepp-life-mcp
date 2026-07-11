import json
import urllib.parse

har_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/quantumult-x-2026-07-10-122218.har"

with open(har_path, 'r', encoding='utf-8', errors='ignore') as f:
    data = json.load(f)

targets = [
    "RespiratoryRate", "LactateThreshold", "Food", "Emotion", "LifeLoad", "hrv_sdnn", "sport_route", "relaxMusic/sleepReport", "training/plan/schedules"
]

found = set()

for entry in data['log']['entries']:
    url = entry['request']['url']
    if entry['response']['status'] == 200:
        for t in targets:
            if t in url and t not in found:
                try:
                    text = entry['response']['content']['text']
                    if len(text) > 500:
                        print(f"\n--- SAMPLE FOR {t} (Truncated) ---")
                        print(text[:500] + "...")
                    else:
                        print(f"\n--- SAMPLE FOR {t} ---")
                        print(text)
                    found.add(t)
                except:
                    pass

