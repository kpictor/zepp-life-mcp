"""SQLite storage layer for Zepp MCP."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from zepp_life_mcp.models import (
    BodyMeasurement,
    DailyActivity,
    HeartRateSample,
    PAISample,
    RespiratoryRateSample,
    SleepSession,
    SpO2Sample,
    SportRoute,
    StressSample,
    TrainingPlan,
    Workout,
)


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Path | str):
        """Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            # Daily activity table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_activity (
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
                    date TEXT NOT NULL,
                    steps INTEGER NOT NULL DEFAULT 0,
                    distance_m REAL NOT NULL DEFAULT 0,
                    active_kcal REAL NOT NULL DEFAULT 0,
                    total_kcal REAL,
                    floors INTEGER,
                    active_minutes INTEGER,
                    UNIQUE(user_id, date, device_id)
                )
            """)

            # Sleep sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sleep_sessions (
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
                    sleep_id TEXT NOT NULL,
                    start_at TIMESTAMP NOT NULL,
                    end_at TIMESTAMP NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    time_asleep_minutes INTEGER NOT NULL,
                    time_awake_minutes INTEGER NOT NULL,
                    sleep_score INTEGER,
                    is_nap BOOLEAN DEFAULT FALSE,
                    stages TEXT,  -- JSON array of sleep stages
                    UNIQUE(user_id, sleep_id)
                )
            """)

            # Workouts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
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
                    workout_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    start_at TIMESTAMP NOT NULL,
                    end_at TIMESTAMP NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    distance_m REAL,
                    calories_kcal REAL,
                    avg_heart_rate_bpm INTEGER,
                    max_heart_rate_bpm INTEGER,
                    avg_pace_sec_per_km REAL,
                    max_pace_sec_per_km REAL,
                    total_steps INTEGER,
                    UNIQUE(user_id, workout_id)
                )
            """)

            # Body measurements table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS body_measurements (
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
                    weight_kg REAL NOT NULL,
                    bmi REAL,
                    body_fat_pct REAL,
                    muscle_mass_kg REAL,
                    water_pct REAL,
                    bone_mass_kg REAL,
                    visceral_fat_score INTEGER,
                    basal_metabolism_kcal INTEGER,
                    metabolic_age INTEGER,
                    protein_pct REAL,
                    skeletal_muscle_kg REAL,
                    body_balance_score INTEGER,
                    UNIQUE(user_id, timestamp, device_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS heart_rate_samples (
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
                    bpm INTEGER NOT NULL,
                    sample_type TEXT NOT NULL,
                    UNIQUE(user_id, timestamp, sample_type)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS spo2_samples (
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
                    spo2_pct INTEGER NOT NULL,
                    UNIQUE(user_id, timestamp)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS stress_samples (
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
                    stress_score INTEGER NOT NULL,
                    level TEXT NOT NULL,
                    UNIQUE(user_id, timestamp)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS pai_samples (
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
                    date TEXT NOT NULL,
                    pai_score REAL NOT NULL,
                    total_pai REAL NOT NULL,
                    UNIQUE(user_id, date)
                )
            """)

            conn.execute("""
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
            """)

            conn.execute("""
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
            """)

            conn.execute("""
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
            """)

            # Sync state table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT NOT NULL UNIQUE,
                    last_sync_at TIMESTAMP,
                    last_record_timestamp TIMESTAMP,
                    records_count INTEGER DEFAULT 0
                )
            """)

            # Create indexes for better query performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_user_date
                ON daily_activity(user_id, date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sleep_user_start
                ON sleep_sessions(user_id, start_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workouts_user_start
                ON workouts(user_id, start_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_measurements_user_ts
                ON body_measurements(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_heart_rate_user_ts
                ON heart_rate_samples(user_id, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_spo2_user_ts
                ON spo2_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stress_user_ts
                ON stress_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pai_user_date
                ON pai_samples(user_id, date)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def insert_daily_activity(self, activity: DailyActivity) -> bool:
        """Insert or update daily activity record.

        Returns:
            True if record was inserted, False if updated
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO daily_activity (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, date, steps, distance_m, active_kcal,
                    total_kcal, floors, active_minutes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    steps = excluded.steps,
                    distance_m = excluded.distance_m,
                    active_kcal = excluded.active_kcal,
                    total_kcal = excluded.total_kcal,
                    floors = excluded.floors,
                    active_minutes = excluded.active_minutes,
                    updated_at = CURRENT_TIMESTAMP
                WHERE excluded.steps > daily_activity.steps
                """,
                (
                    activity.id,
                    activity.provider,
                    activity.source_type,
                    activity.source_record_id,
                    activity.user_id,
                    activity.device_id,
                    activity.timezone,
                    activity.collected_at.isoformat() if activity.collected_at else None,
                    activity.date,
                    activity.steps,
                    activity.distance_m,
                    activity.active_kcal,
                    activity.total_kcal,
                    activity.floors,
                    activity.active_minutes,
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_sleep_session(self, sleep: SleepSession) -> bool:
        """Insert or update sleep session record."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sleep_sessions (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, sleep_id, start_at, end_at, duration_minutes,
                    time_asleep_minutes, time_awake_minutes, sleep_score, is_nap, stages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, sleep_id) DO UPDATE SET
                    duration_minutes = excluded.duration_minutes,
                    time_asleep_minutes = excluded.time_asleep_minutes,
                    time_awake_minutes = excluded.time_awake_minutes,
                    sleep_score = excluded.sleep_score,
                    stages = excluded.stages,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    sleep.id,
                    sleep.provider,
                    sleep.source_type,
                    sleep.source_record_id,
                    sleep.user_id,
                    sleep.device_id,
                    sleep.timezone,
                    sleep.collected_at.isoformat() if sleep.collected_at else None,
                    sleep.sleep_id,
                    sleep.start_at.isoformat(),
                    sleep.end_at.isoformat(),
                    sleep.duration_minutes,
                    sleep.time_asleep_minutes,
                    sleep.time_awake_minutes,
                    sleep.sleep_score,
                    sleep.is_nap,
                    json.dumps([s.model_dump() for s in sleep.stages]),
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_workout(self, workout: Workout) -> bool:
        """Insert or update workout record."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO workouts (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, workout_id, activity_type, start_at, end_at,
                    duration_minutes, distance_m, calories_kcal, avg_heart_rate_bpm,
                    max_heart_rate_bpm, avg_pace_sec_per_km, max_pace_sec_per_km, total_steps
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, workout_id) DO UPDATE SET
                    duration_minutes = excluded.duration_minutes,
                    distance_m = excluded.distance_m,
                    calories_kcal = excluded.calories_kcal,
                    avg_heart_rate_bpm = excluded.avg_heart_rate_bpm,
                    max_heart_rate_bpm = excluded.max_heart_rate_bpm,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    workout.id,
                    workout.provider,
                    workout.source_type,
                    workout.source_record_id,
                    workout.user_id,
                    workout.device_id,
                    workout.timezone,
                    workout.collected_at.isoformat() if workout.collected_at else None,
                    workout.workout_id,
                    workout.activity_type,
                    workout.start_at.isoformat(),
                    workout.end_at.isoformat(),
                    workout.duration_minutes,
                    workout.distance_m,
                    workout.calories_kcal,
                    workout.avg_heart_rate_bpm,
                    workout.max_heart_rate_bpm,
                    workout.avg_pace_sec_per_km,
                    workout.max_pace_sec_per_km,
                    workout.total_steps,
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_body_measurement(self, measurement: BodyMeasurement) -> bool:
        """Insert or update body measurement record."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO body_measurements (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, timestamp, weight_kg, bmi, body_fat_pct,
                    muscle_mass_kg, water_pct, bone_mass_kg, visceral_fat_score,
                    basal_metabolism_kcal, metabolic_age, protein_pct, skeletal_muscle_kg, body_balance_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    weight_kg = excluded.weight_kg,
                    bmi = excluded.bmi,
                    body_fat_pct = excluded.body_fat_pct,
                    muscle_mass_kg = excluded.muscle_mass_kg,
                    water_pct = excluded.water_pct,
                    protein_pct = excluded.protein_pct,
                    skeletal_muscle_kg = excluded.skeletal_muscle_kg,
                    body_balance_score = excluded.body_balance_score,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    measurement.id,
                    measurement.provider,
                    measurement.source_type,
                    measurement.source_record_id,
                    measurement.user_id,
                    measurement.device_id,
                    measurement.timezone,
                    measurement.collected_at.isoformat() if measurement.collected_at else None,
                    measurement.timestamp.isoformat(),
                    measurement.weight_kg,
                    measurement.bmi,
                    measurement.body_fat_pct,
                    measurement.muscle_mass_kg,
                    measurement.water_pct,
                    measurement.bone_mass_kg,
                    measurement.visceral_fat_score,
                    measurement.basal_metabolism_kcal,
                    measurement.metabolic_age,
                    measurement.protein_pct,
                    measurement.skeletal_muscle_kg,
                    measurement.body_balance_score,
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_heart_rate_sample(self, sample: HeartRateSample) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO heart_rate_samples (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, timestamp, bpm, sample_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, timestamp, sample_type) DO UPDATE SET
                    bpm = excluded.bpm,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    sample.id,
                    sample.provider,
                    sample.source_type,
                    sample.source_record_id,
                    sample.user_id,
                    sample.device_id,
                    sample.timezone,
                    sample.collected_at.isoformat() if sample.collected_at else None,
                    sample.timestamp.isoformat(),
                    sample.bpm,
                    sample.sample_type,
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_spo2_sample(self, sample: SpO2Sample) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO spo2_samples (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, timestamp, spo2_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, timestamp) DO UPDATE SET
                    spo2_pct = excluded.spo2_pct,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    sample.id,
                    sample.provider,
                    sample.source_type,
                    sample.source_record_id,
                    sample.user_id,
                    sample.device_id,
                    sample.timezone,
                    sample.collected_at.isoformat() if sample.collected_at else None,
                    sample.timestamp.isoformat(),
                    sample.spo2_pct,
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_stress_sample(self, sample: StressSample) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO stress_samples (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, timestamp, stress_score, level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, timestamp) DO UPDATE SET
                    stress_score = excluded.stress_score,
                    level = excluded.level,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    sample.id,
                    sample.provider,
                    sample.source_type,
                    sample.source_record_id,
                    sample.user_id,
                    sample.device_id,
                    sample.timezone,
                    sample.collected_at.isoformat() if sample.collected_at else None,
                    sample.timestamp.isoformat(),
                    sample.stress_score,
                    sample.level,
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_pai_sample(self, sample: PAISample) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pai_samples (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, date, pai_score, total_pai
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, date) DO UPDATE SET
                    pai_score = excluded.pai_score,
                    total_pai = excluded.total_pai,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    sample.id,
                    sample.provider,
                    sample.source_type,
                    sample.source_record_id,
                    sample.user_id,
                    sample.device_id,
                    sample.timezone,
                    sample.collected_at.isoformat() if sample.collected_at else None,
                    sample.date,
                    sample.pai_score,
                    sample.total_pai,
                ),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()
            return cursor.rowcount > 0

    def insert_respiratory_rate_sample(self, sample: RespiratoryRateSample) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO respiratory_rate_samples (
                    id, provider, source_type, source_record_id, user_id, device_id,
                    timezone, collected_at, timestamp, rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, timestamp) DO UPDATE SET
                    rate = excluded.rate,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    sample.id,
                    sample.provider,
                    sample.source_type,
                    sample.source_record_id,
                    sample.user_id,
                    sample.device_id,
                    sample.timezone,
                    sample.collected_at.isoformat() if sample.collected_at else None,
                    sample.timestamp.isoformat(),
                    sample.rate,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def insert_sport_route(self, route: SportRoute) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
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
                """,
                (
                    route.id,
                    route.provider,
                    route.source_type,
                    route.source_record_id,
                    route.user_id,
                    route.device_id,
                    route.timezone,
                    route.collected_at.isoformat() if route.collected_at else None,
                    route.route_id,
                    route.workout_id,
                    route.lon_max,
                    route.lon_min,
                    route.lat_max,
                    route.lat_min,
                    route.elevation_gain,
                    route.elevation_loss,
                    route.elevation_max,
                    route.elevation_min,
                    route.source,
                    route.raw_json,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def insert_training_plan(self, plan: TrainingPlan) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
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
                """,
                (
                    plan.id,
                    plan.provider,
                    plan.source_type,
                    plan.source_record_id,
                    plan.user_id,
                    plan.device_id,
                    plan.timezone,
                    plan.collected_at.isoformat() if plan.collected_at else None,
                    plan.plan_id,
                    plan.start_date,
                    plan.end_date,
                    plan.title,
                    plan.description,
                    plan.raw_json,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_sync_state(self, data_type: str, last_record_ts: datetime | None = None) -> None:
        """Update sync state for a data type."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sync_state (data_type, last_sync_at, last_record_timestamp)
                VALUES (?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(data_type) DO UPDATE SET
                    last_sync_at = CURRENT_TIMESTAMP,
                    last_record_timestamp = excluded.last_record_timestamp
                """,
                (data_type, last_record_ts.isoformat() if last_record_ts else None),
            )

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_respiratory_user_ts
                ON respiratory_rate_samples(user_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sport_routes_user_route
                ON sport_routes(user_id, route_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_plans_user_plan
                ON training_plans(user_id, plan_id)
            """)

            conn.commit()

    def get_sync_state(self, data_type: str) -> dict[str, Any] | None:
        """Get sync state for a data type."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sync_state WHERE data_type = ?",
                (data_type,),
            ).fetchone()
            return dict(row) if row else None

    def query_daily_activity(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Query daily activity records."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM daily_activity
                WHERE user_id = ? AND date >= ? AND date <= ?
                ORDER BY date
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_sleep_sessions(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Query sleep session records."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sleep_sessions
                WHERE user_id = ?
                AND date(end_at) >= ? AND date(end_at) <= ?
                ORDER BY start_at
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_workouts(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Query workout records."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM workouts
                WHERE user_id = ?
                AND date(start_at) >= ? AND date(start_at) <= ?
                ORDER BY start_at
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_body_measurements(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Query body measurement records."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM body_measurements
                WHERE user_id = ?
                AND date(timestamp) >= ? AND date(timestamp) <= ?
                ORDER BY timestamp
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_heart_rate_samples(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM heart_rate_samples
                WHERE user_id = ?
                AND date(timestamp) >= ? AND date(timestamp) <= ?
                ORDER BY timestamp
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_spo2_samples(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM spo2_samples
                WHERE user_id = ?
                AND date(timestamp) >= ? AND date(timestamp) <= ?
                ORDER BY timestamp
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_stress_samples(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM stress_samples
                WHERE user_id = ?
                AND date(timestamp) >= ? AND date(timestamp) <= ?
                ORDER BY timestamp
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_pai_samples(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM pai_samples
                WHERE user_id = ? AND date >= ? AND date <= ?
                ORDER BY date
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_respiratory_rate_samples(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM respiratory_rate_samples
                WHERE user_id = ?
                AND date(timestamp) >= ? AND date(timestamp) <= ?
                ORDER BY timestamp
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_sport_routes(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sport_routes
                WHERE user_id = ?
                AND date(created_at) >= ? AND date(created_at) <= ?
                ORDER BY created_at
                """,
                (user_id, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def query_training_plans(self, user_id: str) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM training_plans
                WHERE user_id = ?
                ORDER BY start_date DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_data_coverage(self, user_id: str) -> list[dict[str, Any]]:
        """Get data coverage statistics."""
        with self._get_connection() as conn:
            results = []

            # Activity coverage
            row = conn.execute(
                """
                SELECT
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(DISTINCT date) as days_with_data
                FROM daily_activity
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row and row["first_date"]:
                results.append(
                    {
                        "data_type": "daily_activity",
                        **dict(row),
                    }
                )

            # Sleep coverage
            row = conn.execute(
                """
                SELECT
                    MIN(date(start_at)) as first_date,
                    MAX(date(start_at)) as last_date,
                    COUNT(DISTINCT date(start_at)) as days_with_data
                FROM sleep_sessions
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row and row["first_date"]:
                results.append(
                    {
                        "data_type": "sleep",
                        **dict(row),
                    }
                )

            # Workouts coverage
            row = conn.execute(
                """
                SELECT
                    MIN(date(start_at)) as first_date,
                    MAX(date(start_at)) as last_date,
                    COUNT(DISTINCT date(start_at)) as days_with_data
                FROM workouts
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row and row["first_date"]:
                results.append(
                    {
                        "data_type": "workouts",
                        **dict(row),
                    }
                )

            # Body measurements coverage
            row = conn.execute(
                """
                SELECT
                    MIN(date(timestamp)) as first_date,
                    MAX(date(timestamp)) as last_date,
                    COUNT(DISTINCT date(timestamp)) as days_with_data
                FROM body_measurements
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row and row["first_date"]:
                results.append(
                    {
                        "data_type": "body_measurements",
                        **dict(row),
                    }
                )

            row = conn.execute(
                """
                SELECT
                    MIN(date(timestamp)) as first_date,
                    MAX(date(timestamp)) as last_date,
                    COUNT(DISTINCT date(timestamp)) as days_with_data
                FROM heart_rate_samples
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row and row["first_date"]:
                results.append(
                    {
                        "data_type": "heart_rate",
                        **dict(row),
                    }
                )

            return results
