import sys

file_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/src/zepp_life_mcp/services/sync_service.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_branches = """        elif data_type == "respiratory_rate":
            if hasattr(self.adapter, "iter_respiratory_rate"):
                records = self.adapter.iter_respiratory_rate(start_date, end_date)
                async for sample in self._iterate_records(records):
                    if self.db.insert_respiratory_rate_sample(sample):
                        added += 1
                    else:
                        updated += 1
                    if last_ts is None or sample.timestamp > last_ts:
                        last_ts = sample.timestamp

        elif data_type == "sport_routes":
            if hasattr(self.adapter, "iter_sport_routes"):
                records = self.adapter.iter_sport_routes(start_date, end_date)
                async for route in self._iterate_records(records):
                    if self.db.insert_sport_route(route):
                        added += 1
                    else:
                        updated += 1
                    if last_ts is None or (route.collected_at and route.collected_at > last_ts):
                        last_ts = route.collected_at

        elif data_type == "training_plans":
            if hasattr(self.adapter, "iter_training_plans"):
                records = self.adapter.iter_training_plans()
                async for plan in self._iterate_records(records):
                    if self.db.insert_training_plan(plan):
                        added += 1
                    else:
                        updated += 1
                    if last_ts is None or (plan.collected_at and plan.collected_at > last_ts):
                        last_ts = plan.collected_at

        else:"""

content = content.replace("        else:", new_branches)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("sync_service patched")
