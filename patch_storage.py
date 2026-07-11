import sys
import re

file_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/src/zepp_life_mcp/storage/__init__.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
import_replace = """    SleepSession,
    Workout,
    SpO2Sample,
    StressSample,
    PAISample,
    RespiratoryRateSample,
    SportRoute,
    TrainingPlan,
)"""
content = content.replace("    SleepSession,\n    Workout,\n    SpO2Sample,\n    StressSample,\n    PAISample,\n)", import_replace)

# 2. Add Tables in _init_db
new_tables = """
            conn.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS respiratory_rate_samples (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_record_id TEXT,
                    user_id TEXT NOT NULL,
                    device_id TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    collected_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    timestamp TIMESTAMP NOT NULL,
                    rate REAL NOT NULL,
                    UNIQUE(user_id, timestamp)
                )
            \"\"\")

            conn.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS sport_routes (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_record_id TEXT,
                    user_id TEXT NOT NULL,
                    device_id TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    collected_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    route_id TEXT NOT NULL,
                    workout_id TEXT,
                    lon_max REAL,
                    lon_min REAL,
                    lat_max REAL,
                    lat_min REAL,
                    elevation_gain REAL,
                    elevation_loss REAL,
                    elevation_max REAL,
                    elevation_min REAL,
                    source TEXT,
                    raw_json TEXT,
                    UNIQUE(user_id, route_id)
                )
            \"\"\")

            conn.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS training_plans (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_record_id TEXT,
                    user_id TEXT NOT NULL,
                    device_id TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    collected_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    plan_id TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    title TEXT,
                    description TEXT,
                    raw_json TEXT,
                    UNIQUE(user_id, plan_id)
                )
            \"\"\")

            # Sync state table"""
content = content.replace("            # Sync state table", new_tables)

# 3. Add Indexes in _init_db
new_indexes = """
            conn.execute(\"\"\"
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            \"\"\")
            conn.execute(\"\"\"
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            \"\"\")
            conn.execute(\"\"\"
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            \"\"\")

            conn.commit()"""
content = content.replace("            conn.commit()", new_indexes)

# 4. Insert methods
insert_methods = """
    def insert_respiratory_rate_sample(self, sample: RespiratoryRateSample) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                \"\"\"
                INSERT INTO respiratory_rate_samples (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, timestamp, rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, timestamp) DO UPDATE SET
                    rate = excluded.rate,
                    updated_at = CURRENT_TIMESTAMP
                \"\"\",
                (
                    sample.id, sample.provider, sample.source_type, sample.source_record_id,
                    sample.user_id, sample.device_id, sample.timezone,
                    sample.collected_at.isoformat() if sample.collected_at else None,
                    sample.timestamp.isoformat(), sample.rate
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def insert_sport_route(self, route: SportRoute) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                \"\"\"
                INSERT INTO sport_routes (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, route_id, workout_id, lon_max, lon_min,
                    lat_max, lat_min, elevation_gain, elevation_loss, elevation_max,
                    elevation_min, source, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, route_id) DO UPDATE SET
                    workout_id = excluded.workout_id,
                    raw_json = excluded.raw_json,
                    updated_at = CURRENT_TIMESTAMP
                \"\"\",
                (
                    route.id, route.provider, route.source_type, route.source_record_id,
                    route.user_id, route.device_id, route.timezone,
                    route.collected_at.isoformat() if route.collected_at else None,
                    route.route_id, route.workout_id, route.lon_max, route.lon_min,
                    route.lat_max, route.lat_min, route.elevation_gain, route.elevation_loss,
                    route.elevation_max, route.elevation_min, route.source, route.raw_json
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def insert_training_plan(self, plan: TrainingPlan) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                \"\"\"
                INSERT INTO training_plans (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, plan_id, start_date, end_date, title,
                    description, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, plan_id) DO UPDATE SET
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    title = excluded.title,
                    description = excluded.description,
                    raw_json = excluded.raw_json,
                    updated_at = CURRENT_TIMESTAMP
                \"\"\",
                (
                    plan.id, plan.provider, plan.source_type, plan.source_record_id,
                    plan.user_id, plan.device_id, plan.timezone,
                    plan.collected_at.isoformat() if plan.collected_at else None,
                    plan.plan_id, plan.start_date, plan.end_date, plan.title,
                    plan.description, plan.raw_json
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_sync_state"""
content = content.replace("    def update_sync_state", insert_methods)

# 5. Query methods
query_methods = """
    def query_respiratory_rate_samples(self, user_id: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                \"\"\"
                SELECT * FROM respiratory_rate_samples
                WHERE user_id = ?
                AND date(timestamp) >= ? AND date(timestamp) <= ?
                ORDER BY timestamp
                \"\"\",
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_sport_routes(self, user_id: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                \"\"\"
                SELECT * FROM sport_routes
                WHERE user_id = ?
                AND date(created_at) >= ? AND date(created_at) <= ?
                ORDER BY created_at
                \"\"\",
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_training_plans(self, user_id: str) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                \"\"\"
                SELECT * FROM training_plans
                WHERE user_id = ?
                ORDER BY start_date DESC
                \"\"\",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_data_coverage"""
content = content.replace("    def get_data_coverage", query_methods)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("storage patched")
