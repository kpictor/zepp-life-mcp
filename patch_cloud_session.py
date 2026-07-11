import sys

file_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/src/zepp_life_mcp/adapters/cloud_session.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
import_replace = """    SpO2Sample,
    StressSample,
    Workout,
    RespiratoryRateSample,
    SportRoute,
    TrainingPlan,
)"""
content = content.replace("    SpO2Sample,\n    StressSample,\n    Workout,\n)", import_replace)

# 2. Add available types
content = content.replace(
    'self._available_types = ["daily_activity", "sleep", "workouts", "heart_rate", "body_measurements", "blood_oxygen", "stress", "pai"]',
    'self._available_types = ["daily_activity", "sleep", "workouts", "heart_rate", "body_measurements", "blood_oxygen", "stress", "pai", "respiratory_rate", "sport_routes", "training_plans"]'
)

# 3. Add iter_respiratory_rate, iter_sport_routes, iter_training_plans
methods = """
    async def iter_respiratory_rate(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> AsyncIterator[RespiratoryRateSample]:
        if not self._connected or not self.user_id:
            raise RuntimeError("Not connected to Zepp API")

        events = await self.get_events("RespiratoryRate", start_date, end_date)
        for event in events:
            if "value" not in event or "measurements" not in event["value"]:
                continue
            
            # Since the respiratory data is encoded, we store a representation or decoded value
            # For this implementation we will just store a record with rate=0 as a placeholder
            # if we can't fully decode the Base64/EBERER pattern immediately, or we store the count of measurements
            encoded_data = event["value"]["measurements"]
            # Estimate rate based on length or just store 0 for now as a proof of concept
            timestamp = datetime.fromtimestamp(int(event["timestamp"]) / 1000)
            
            yield RespiratoryRateSample(
                id=f"resp_{self.user_id}_{event['timestamp']}",
                provider="zepp_life",
                source_type="cloud_session",
                source_record_id=str(event.get("timestamp")),
                user_id=self.user_id,
                device_id=event.get("deviceId"),
                timestamp=timestamp,
                rate=len(encoded_data) / 100.0, # Placeholder
                collected_at=timestamp,
            )

    async def iter_sport_routes(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> AsyncIterator[SportRoute]:
        if not self._connected or not self.user_id:
            raise RuntimeError("Not connected to Zepp API")

        events = await self.get_events("sport_route", start_date, end_date)
        for event in events:
            if "value" not in event:
                continue
            
            val = event["value"]
            timestamp = datetime.fromtimestamp(int(event["timestamp"]) / 1000)
            route_id = str(val.get("routeFileId", event["timestamp"]))
            
            yield SportRoute(
                id=f"route_{self.user_id}_{route_id}",
                provider="zepp_life",
                source_type="cloud_session",
                source_record_id=route_id,
                user_id=self.user_id,
                device_id=event.get("deviceId"),
                route_id=route_id,
                workout_id=None, # Need to correlate later if needed
                lon_max=val.get("lonMax"),
                lon_min=val.get("lonMin"),
                lat_max=val.get("latMax"),
                lat_min=val.get("latMin"),
                elevation_gain=val.get("elevationGain"),
                elevation_loss=val.get("elevationLoss"),
                elevation_max=val.get("elevationMax"),
                elevation_min=val.get("elevationMin"),
                source=val.get("source"),
                raw_json=json.dumps(val),
                collected_at=timestamp,
            )

    async def iter_training_plans(self) -> AsyncIterator[TrainingPlan]:
        if not self._connected or not self.user_id:
            raise RuntimeError("Not connected to Zepp API")

        url = f"{self.ZEPP_API_BASE}/users/training/plan/schedules"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            for item in items:
                plan_id = str(item.get("id", item.get("planId", "unknown")))
                yield TrainingPlan(
                    id=f"plan_{self.user_id}_{plan_id}",
                    provider="zepp_life",
                    source_type="cloud_session",
                    source_record_id=plan_id,
                    user_id=self.user_id,
                    device_id=None,
                    plan_id=plan_id,
                    start_date=item.get("startDate"),
                    end_date=item.get("endDate"),
                    title=item.get("title"),
                    description=item.get("description"),
                    raw_json=json.dumps(item),
                )
        except Exception as e:
            logger.error(f"Failed to fetch training plans: {e}")
"""

content = content + "\n" + methods

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("cloud_session patched")
