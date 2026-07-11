"""Cloud session adapter for direct API access to Zepp Life."""

import base64
import json
import logging
import os
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any

import httpx
from dotenv import find_dotenv, load_dotenv, set_key

from zepp_life_mcp.adapters.base import DataAdapter
from zepp_life_mcp.models import (
    BodyMeasurement,
    DailyActivity,
    HeartRateSample,
    PAISample,
    SleepSession,
    SleepStage,
    SpO2Sample,
    StressSample,
    Workout,
    RespiratoryRateSample,
    SportRoute,
    TrainingPlan,
)

logger = logging.getLogger(__name__)


class CloudSessionAdapter(DataAdapter):
    """Adapter for accessing Zepp Life cloud APIs."""

    ZEPP_API_BASE = "https://api-mifit.huami.com"
    ZEPP_AUTH_BASE = "https://account.huami.com"
    ZEPP_USER_API = "https://api-user.huami.com"
    ZEPP_WEIGHT_API = "https://api-mifit.zepp.com"
    ZEPP_EVENTS_API = "https://api-mifit.zepp.com"

    def __init__(
        self,
        app_token: str | None = None,
        user_id: str | None = None,
        region: str = "eu",
    ):
        self.app_token = app_token
        self.user_id = user_id
        self.region = region
        self._connected = False
        self._client: httpx.AsyncClient | None = None
        self._available_types: list[str] = []

    def _auto_login(self) -> bool:
        """Attempt to auto-login using credentials from environment."""
        username = os.environ.get("ZEPP_USERNAME")
        password = os.environ.get("ZEPP_PASSWORD")
        if not username or not password:
            return False

        try:
            logger.info("Token missing or expired. Attempting auto-login...")
            from huami_token.zepp import ZeppSession
            session = ZeppSession(username=username, password=password)
            session.login()

            self.app_token = session.app_token
            self.user_id = session.user_id

            # Save to .env if it exists
            env_file = find_dotenv()
            if env_file:
                set_key(env_file, "ZEPP_APP_TOKEN", self.app_token)
                set_key(env_file, "ZEPP_USER_ID", self.user_id)
                logger.info(f"Saved new token and user_id to {env_file}")
            else:
                logger.warning("No .env file found to save the new token.")
            return True
        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            return False

    async def connect(self) -> bool:
        load_dotenv()
        if not self.app_token and not self._auto_login():
            logger.error("No app_token provided and auto-login failed")
            return False

        def _create_client(token: str):
            return httpx.AsyncClient(
                base_url=self.ZEPP_API_BASE,
                headers={
                    "apptoken": token,
                    "appPlatform": "web",
                    "appname": "com.xiaomi.hm.health",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

        self._client = _create_client(self.app_token)

        try:
            user_info = await self._get_user_info()
            if user_info:
                self.user_id = user_info.get("user_id") or self.user_id
                self._connected = True
                self._available_types = ["daily_activity", "sleep", "workouts", "heart_rate", "body_measurements", "blood_oxygen", "stress", "pai", "respiratory_rate", "sport_routes", "training_plans"]
                logger.info(f"Connected to Zepp API as user {self.user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to validate token: {e}")

        # If user_info failed (token expired), try auto-login
        if self._auto_login():
            if self._client:
                await self._client.aclose()
            self._client = _create_client(self.app_token)
            try:
                user_info = await self._get_user_info()
                if user_info:
                    self.user_id = user_info.get("user_id") or self.user_id
                    self._connected = True
                    self._available_types = ["daily_activity", "sleep", "workouts", "heart_rate", "body_measurements", "blood_oxygen", "stress", "pai", "respiratory_rate", "sport_routes", "training_plans"]
                    logger.info(f"Connected to Zepp API as user {self.user_id}")
                    return True
            except Exception as e:
                logger.error(f"Failed to validate token after auto-login: {e}")

        return False

    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    def get_user_id(self) -> str | None:
        return self.user_id

    def get_available_data_types(self) -> list[str]:
        return self._available_types.copy()

    def _parse_band_data(self, data: dict) -> Any:
        """Parse band data from API response."""
        try:
            if "data" in data:
                encoded = data["data"]
                if isinstance(encoded, (list, dict)):
                    return encoded
                decoded = base64.b64decode(encoded)
                return json.loads(decoded)
        except Exception as e:
            logger.error(f"Failed to parse band data: {e}")

        return data

    def _decode_band_summary(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            return json.loads(base64.b64decode(value))
        except Exception:
            return {}

    def _iter_band_summary_entries(self, payload: Any) -> list[tuple[str, dict[str, Any]]]:
        entries: list[tuple[str, dict[str, Any]]] = []
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                date_str = str(item.get("date_time") or item.get("date") or "")
                summary = self._decode_band_summary(item.get("summary"))
                if date_str and summary:
                    entries.append((date_str, summary))
        elif isinstance(payload, dict):
            for date_str, day_data in payload.items():
                if isinstance(day_data, dict):
                    entries.append((str(date_str), day_data))
        return entries

    def _parse_heart_rate_data(self, encoded_data: str) -> list[tuple[int, int]]:
        try:
            decoded = base64.b64decode(encoded_data)
            hr_values: list[tuple[int, int]] = []
            for i, value in enumerate(decoded):
                if value not in (255, 254, 0) and 30 <= value <= 240:
                    hr_values.append((i, value))
            return hr_values
        except Exception as e:
            logger.error(f"Failed to parse heart rate data: {e}")
            return []

    async def _get_user_info(self) -> dict | None:
        if not self._client:
            return None

        try:
            response = await self._client.get(
                "/v1/sport/run/history.json",
                params={"limit": 1},
            )
            if response.status_code == 200:
                return {"user_id": self.user_id, "valid": True}
        except Exception as e:
            logger.error(f"Failed to validate token: {e}")

        return None

    async def _discover_data_types(self) -> list[str]:
        types = []

        try:
            response = await self._client.get(
                "/v1/data/band_data.json",
                params={
                    "query_type": "summary",
                    "device_type": "android_phone",
                    "userid": self.user_id,
                    "from_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "to_date": datetime.now().strftime("%Y-%m-%d"),
                },
            )
            if response.status_code == 200:
                data = response.json()
                parsed = self._parse_band_data(data)
                for _, day_data in self._iter_band_summary_entries(parsed):
                    if day_data.get("stp"):
                        types.append("daily_activity")
                    if day_data.get("slp"):
                        types.append("sleep")
                    break
        except Exception:
            pass

        try:
            response = await self._client.get(
                "/v1/sport/run/history.json",
                params={"limit": 1},
            )
            if response.status_code == 200:
                types.append("workouts")
        except Exception:
            pass

        try:
            response = await self._client.get(
                "/v1/data/band_data.json",
                params={
                    "query_type": "detail",
                    "device_type": "android_phone",
                    "userid": self.user_id,
                    "from_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "to_date": datetime.now().strftime("%Y-%m-%d"),
                },
            )
            if response.status_code == 200:
                for item in response.json().get("data", []):
                    if self._parse_heart_rate_data(item.get("data_hr", "")):
                        types.append("heart_rate")
                        break
        except Exception:
            pass

        try:
            url = f"{self.ZEPP_WEIGHT_API}/users/{self.user_id}/members/-1/weightRecords?limit=1"
            response = await self._client.get(url)
            if response.status_code == 200:
                types.append("body_measurements")
        except Exception:
            pass

        # Check events
        try:
            url = f"{self.ZEPP_EVENTS_API}/users/{self.user_id}/events"
            for ev_type, label in [("blood_oxygen", "blood_oxygen"), ("all_day_stress", "stress"), ("PaiHealthInfo", "pai")]:
                response = await self._client.get(url, params={
                    "eventType": ev_type,
                    "from": int((datetime.now() - timedelta(days=7)).timestamp() * 1000),
                    "to": int(datetime.now().timestamp() * 1000),
                    "limit": 1
                })
                if response.status_code == 200 and response.json().get("items"):
                    types.append(label)
        except Exception:
            pass

        return list(set(types))

    async def iter_daily_activity(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[DailyActivity]:
        if not self._client or not self.is_connected():
            return
            yield

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")

        try:
            response = await self._client.get(
                "/v1/data/band_data.json",
                params={
                    "query_type": "detail",
                    "device_type": "android_phone",
                    "userid": self.user_id,
                    "from_date": start_date,
                    "to_date": end_date,
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch activity: {response.status_code}")
                return

            data = response.json()
            parsed_data = self._parse_band_data(data)

            for date_str, day_data in self._iter_band_summary_entries(parsed_data):
                steps_data = day_data.get("stp", {})
                if steps_data:
                    # Calculate active minutes
                    active_mins = None
                    wk = steps_data.get("wk")
                    rn = steps_data.get("rn")
                    if wk is not None or rn is not None:
                        active_mins = (int(wk) if wk else 0) + (int(rn) if rn else 0)

                    # Set collected_at
                    now = datetime.now()
                    today_str = now.strftime("%Y-%m-%d")
                    if date_str == today_str:
                        collected_at = now
                    else:
                        try:
                            # Set to end of the day for past days
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                            collected_at = dt.replace(hour=23, minute=59, second=59)
                        except Exception:
                            collected_at = None

                    yield DailyActivity(
                        id=f"cloud_{date_str}",
                        provider="zepp_life",
                        source_type="cloud_session",
                        user_id=self.user_id or "unknown",
                        date=date_str,
                        steps=steps_data.get("ttl", 0),
                        distance_m=steps_data.get("dis", 0),
                        active_kcal=steps_data.get("cal", 0),
                        active_minutes=active_mins,
                        collected_at=collected_at,
                    )

        except Exception as e:
            logger.error(f"Error fetching activity: {e}")

    async def iter_sleep_sessions(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[SleepSession]:
        if not self._client or not self.is_connected():
            return
            yield

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")

        try:
            response = await self._client.get(
                "/v1/data/band_data.json",
                params={
                    "query_type": "summary",
                    "device_type": "android_phone",
                    "userid": self.user_id,
                    "from_date": start_date,
                    "to_date": end_date,
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch sleep: {response.status_code}")
                return

            data = response.json()
            parsed_data = self._parse_band_data(data)

            for date_str, day_data in self._iter_band_summary_entries(parsed_data):
                sleep_data = day_data.get("slp", {})
                if not sleep_data:
                    continue

                start_ts = sleep_data.get("st")
                end_ts = sleep_data.get("ed")
                rem_mins = sleep_data.get("rs", sleep_data.get("rn", sleep_data.get("rm", 0)))
                asleep_minutes = sleep_data.get("dp", 0) + sleep_data.get("lt", 0) + rem_mins

                if not start_ts or not end_ts or (end_ts <= start_ts and asleep_minutes <= 0):
                    continue

                start_dt = datetime.fromtimestamp(start_ts)
                end_dt = datetime.fromtimestamp(end_ts)
                duration = int((end_dt - start_dt).total_seconds() / 60)
                if duration < 0:
                    duration = asleep_minutes

                stages = []
                stage_data = sleep_data.get("stage", [])
                calc_asleep = 0
                for stage in stage_data:
                    mode = stage.get("mode")
                    if mode == 5:
                        stage_type = "deep"
                    elif mode == 4:
                        stage_type = "light"
                    elif mode == 8 or mode == 3:
                        stage_type = "rem"
                    else:
                        stage_type = "awake"
                    stage_stop = stage.get("stop", stage.get("end", 0))
                    stage_duration = max(0, stage_stop - stage.get("start", 0) + 1)
                    if stage_duration:
                        stages.append(SleepStage(stage=stage_type, minutes=stage_duration))
                        if stage_type != "awake":
                            calc_asleep += stage_duration

                if calc_asleep > 0:
                    asleep_minutes = calc_asleep
                elif "wk" in sleep_data and duration > 0 and duration >= sleep_data["wk"]:
                    asleep_minutes = duration - sleep_data["wk"]

                total_duration = max(duration, asleep_minutes)
                yield SleepSession(
                    id=f"cloud_sleep_{date_str}",
                    provider="zepp_life",
                    source_type="cloud_session",
                    user_id=self.user_id or "unknown",
                    sleep_id=f"sleep_{date_str}",
                    start_at=start_dt,
                    end_at=end_dt,
                    duration_minutes=total_duration,
                    time_asleep_minutes=asleep_minutes,
                    time_awake_minutes=max(0, total_duration - asleep_minutes),
                    is_nap=False,
                    stages=stages,
                )

                # Parse naps
                odd_stages = sleep_data.get("odd_stage", [])
                for idx, nap in enumerate(odd_stages):
                    nap_start_min = nap.get("start")
                    nap_stop_min = nap.get("stop")
                    if nap_start_min is None or nap_stop_min is None:
                        continue
                    
                    # Zepp API uses minutes since 00:00 of the PREVIOUS day
                    base_dt = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
                    nap_start_dt = base_dt + timedelta(minutes=nap_start_min)
                    nap_end_dt = base_dt + timedelta(minutes=nap_stop_min)
                    nap_duration = int((nap_end_dt - nap_start_dt).total_seconds() / 60)
                    
                    if nap_duration <= 0:
                        continue
                        
                    yield SleepSession(
                        id=f"cloud_nap_{date_str}_{idx}",
                        provider="zepp_life",
                        source_type="cloud_session",
                        user_id=self.user_id or "unknown",
                        sleep_id=f"nap_{date_str}_{idx}",
                        start_at=nap_start_dt,
                        end_at=nap_end_dt,
                        duration_minutes=nap_duration,
                        time_asleep_minutes=nap_duration,
                        time_awake_minutes=0,
                        is_nap=True,
                        stages=[SleepStage(stage="light", minutes=nap_duration)]
                    )

        except Exception as e:
            logger.error(f"Error fetching sleep: {e}")

    async def iter_heart_rate(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[HeartRateSample]:
        if not self._client or not self.is_connected():
            return
            yield

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=7)
            start_date = start_dt.strftime("%Y-%m-%d")

        try:
            response = await self._client.get(
                "/v1/data/band_data.json",
                params={
                    "query_type": "detail",
                    "device_type": "android_phone",
                    "userid": self.user_id,
                    "from_date": start_date,
                    "to_date": end_date,
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch heart rate: {response.status_code}")
                return

            data = response.json()

            for item in data.get("data", []):
                date_str = item.get("date_time", "")
                hr_data = item.get("data_hr", "")

                if hr_data:
                    hr_values = self._parse_heart_rate_data(hr_data)
                    base_time = datetime.strptime(date_str, "%Y-%m-%d")

                    for minute, bpm in hr_values:
                        timestamp = base_time + timedelta(minutes=minute)
                        yield HeartRateSample(
                            id=f"cloud_hr_{date_str}_{minute}",
                            provider="zepp_life",
                            source_type="cloud_session",
                            user_id=self.user_id or "unknown",
                            timestamp=timestamp,
                            bpm=bpm,
                            sample_type="passive",
                        )

        except Exception as e:
            logger.error(f"Error fetching heart rate: {e}")

    async def iter_workouts(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[Workout]:
        if not self._client or not self.is_connected():
            return
            yield

        try:
            response = await self._client.get(
                "/v1/sport/run/history.json",
                params={"limit": 100},
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch workouts: {response.status_code}")
                return

            data = response.json()

            for item in data.get("data", {}).get("summary", []):
                start_time = item.get("start_time")
                end_time = item.get("end_time")
                run_time = item.get("run_time", 0)
                end_ts = int(float(end_time)) if end_time else None
                duration_sec = int(float(run_time)) if run_time else 0
                start_ts = (
                    int(float(start_time))
                    if start_time
                    else (end_ts - duration_sec if end_ts else None)
                )

                if start_ts:
                    workout_date = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d")

                    if start_date and workout_date < start_date:
                        continue
                    if end_date and workout_date > end_date:
                        continue

                duration_min = int(float(run_time)) // 60 if run_time else 0

                sport_type_map = {
                    "1": "running",
                    "6": "walking",
                    "8": "treadmill",
                    "9": "cycling",
                    "10": "indoor_cycling",
                    "11": "treadmill",
                    "12": "elliptical",
                    "13": "rowing",
                    "14": "pool_swimming",
                    "16": "freestyle",
                    "17": "jump_rope",
                    "93": "table_tennis",
                    "94": "badminton",
                    "104": "core_training",
                    "107": "strength_training",
                }
                raw_type = str(item.get("type", "unknown"))
                mapped_type = sport_type_map.get(raw_type, raw_type)

                yield Workout(
                    id=f"cloud_{item.get('trackid')}",
                    provider="zepp_life",
                    source_type="cloud_session",
                    user_id=self.user_id or "unknown",
                    workout_id=str(item.get("trackid")),
                    activity_type=mapped_type,
                    start_at=datetime.fromtimestamp(start_ts) if start_ts else datetime.now(),
                    end_at=datetime.fromtimestamp(end_ts) if end_ts else datetime.now(),
                    duration_minutes=duration_min,
                    distance_m=float(item.get("dis", 0)) if item.get("dis") else None,
                    calories_kcal=float(item.get("calorie", 0)) if item.get("calorie") else None,
                    avg_heart_rate_bpm=int(float(item.get("avg_heart_rate")))
                    if item.get("avg_heart_rate")
                    else None,
                    max_heart_rate_bpm=int(float(item.get("max_heart_rate")))
                    if item.get("max_heart_rate")
                    else None,
                )

        except Exception as e:
            logger.error(f"Error fetching workouts: {e}")

    async def iter_body_measurements(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[BodyMeasurement]:
        if not self._client or not self.is_connected():
            return
            yield

        try:
            url = f"{self.ZEPP_WEIGHT_API}/users/{self.user_id}/members/-1/weightRecords"
            params = {"limit": 200}

            response = await self._client.get(url, params=params)

            if response.status_code != 200:
                logger.error(f"Failed to fetch weight: {response.status_code}")
                return

            data = response.json()

            for item in data.get("items", []):
                record_time = item.get("generatedTime")
                if record_time:
                    record_date = datetime.fromtimestamp(record_time).strftime("%Y-%m-%d")

                    if start_date and record_date < start_date:
                        continue
                    if end_date and record_date > end_date:
                        continue

                summary = item.get("summary", {})

                yield BodyMeasurement(
                    id=f"cloud_weight_{item.get('id', record_time)}",
                    provider="zepp_life",
                    source_type="cloud_session",
                    user_id=self.user_id or "unknown",
                    timestamp=datetime.fromtimestamp(record_time)
                    if record_time
                    else datetime.now(),
                    weight_kg=summary.get("weight", 0),
                    bmi=summary.get("bmi"),
                    body_fat_pct=summary.get("fatRate"),
                    muscle_mass_kg=summary.get("muscleRate"),
                    water_pct=summary.get("bodyWaterRate"),
                    bone_mass_kg=summary.get("boneMass"),
                    visceral_fat_score=int(summary.get("visceralFat", 0))
                    if summary.get("visceralFat")
                    else None,
                    basal_metabolism_kcal=int(summary.get("metabolism", 0))
                    if summary.get("metabolism")
                    else None,
                    metabolic_age=int(summary.get("muscleAge", 0))
                    if summary.get("muscleAge")
                    else None,
                    protein_pct=summary.get("proteinRatio"),
                    skeletal_muscle_kg=summary.get("skeletalMuscle"),
                    body_balance_score=int(summary.get("bodyBalanceScore", 0))
                    if summary.get("bodyBalanceScore")
                    else None,
                )

        except Exception as e:
            logger.error(f"Error fetching weight: {e}")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False

    async def iter_blood_oxygen(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[SpO2Sample]:
        if not self._client or not self.is_connected():
            return
            yield

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")

        try:
            from_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            to_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59).timestamp() * 1000)

            url = f"{self.ZEPP_EVENTS_API}/users/{self.user_id}/events"
            response = await self._client.get(
                url,
                params={
                    "eventType": "blood_oxygen",
                    "from": from_ts,
                    "to": to_ts,
                    "limit": 1000
                },
            )

            if response.status_code == 200:
                for item in response.json().get("items", []):
                    ts = item.get("timestamp")
                    if not ts:
                        continue
                    extra = item.get("extra")
                    if extra:
                        try:
                            extra_data = json.loads(extra)
                            spo2 = extra_data.get("spo2")
                            if spo2 is not None:
                                if isinstance(spo2, list) and spo2:
                                    spo2 = spo2[0]
                                elif isinstance(spo2, list):
                                    spo2 = None
                            if spo2 is not None:
                                yield SpO2Sample(
                                    id=f"cloud_spo2_{ts}",
                                    provider="zepp_life",
                                    source_type="cloud_session",
                                    user_id=self.user_id or "unknown",
                                    timestamp=datetime.fromtimestamp(ts / 1000.0),
                                    spo2_pct=int(spo2)
                                )
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Error fetching blood oxygen: {e}")

    async def iter_stress(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[StressSample]:
        if not self._client or not self.is_connected():
            return
            yield

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")

        try:
            from_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            to_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59).timestamp() * 1000)

            url = f"{self.ZEPP_EVENTS_API}/users/{self.user_id}/events"
            response = await self._client.get(
                url,
                params={
                    "eventType": "all_day_stress",
                    "from": from_ts,
                    "to": to_ts,
                    "limit": 1000
                },
            )

            if response.status_code == 200:
                for item in response.json().get("items", []):
                    # Extract detailed points from data field
                    data_str = item.get("data")
                    if data_str:
                        try:
                            stress_dump = json.loads(data_str)
                            for point in stress_dump:
                                ts = point.get("time")
                                val = point.get("value")
                                if ts and val:
                                    level = "low"
                                    if val >= 80:
                                        level = "high"
                                    elif val >= 60:
                                        level = "medium"

                                    yield StressSample(
                                        id=f"cloud_stress_{ts}",
                                        provider="zepp_life",
                                        source_type="cloud_session",
                                        user_id=self.user_id or "unknown",
                                        timestamp=datetime.fromtimestamp(ts / 1000.0) if ts > 10000000000 else datetime.fromtimestamp(ts),
                                        stress_score=int(val),
                                        level=level
                                    )
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Error fetching stress: {e}")

    async def iter_pai(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncIterator[PAISample]:
        if not self._client or not self.is_connected():
            return
            yield

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")

        try:
            from_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            to_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59).timestamp() * 1000)

            url = f"{self.ZEPP_EVENTS_API}/users/{self.user_id}/events"
            response = await self._client.get(
                url,
                params={
                    "eventType": "PaiHealthInfo",
                    "from": from_ts,
                    "to": to_ts,
                    "limit": 1000
                },
            )

            if response.status_code == 200:
                for item in response.json().get("items", []):
                    ts = item.get("timestamp")
                    if not ts:
                        continue
                    extra = item.get("extra")
                    if extra:
                        try:
                            extra_data = json.loads(extra)
                            daily_pai = float(extra_data.get("dailyPai", 0))
                            total_pai = float(extra_data.get("totalPai", 0))
                            dt_str = datetime.fromtimestamp(ts / 1000.0).strftime("%Y-%m-%d")
                            yield PAISample(
                                id=f"cloud_pai_{ts}",
                                provider="zepp_life",
                                source_type="cloud_session",
                                user_id=self.user_id or "unknown",
                                date=dt_str,
                                pai_score=daily_pai,
                                total_pai=total_pai
                            )
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Error fetching PAI: {e}")

    async def get_advanced_sport_stats(self, stat_type: str, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
        import uuid
        if not self._client or not self.is_connected():
            return []
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
        url = f"{self.ZEPP_EVENTS_API}/v2/watch/users/{self.user_id}/WatchSportStatistics/{stat_type}"
        params = {}
        if stat_type in ["VO2_MAX", "SPORT_LOAD"]:
            params = {
                "startDay": start_date,
                "endDay": end_date,
                "limit": 900,
                "isReverse": "true"
            }
        else:
            params = {"r": str(uuid.uuid4())}
            url = f"{self.ZEPP_EVENTS_API}/watch/users/{self.user_id}/WatchSportStatistics/{stat_type}"
            
        try:
            res = await self._client.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                if "items" in data:
                    return data["items"]
                return [data]
        except Exception as e:
            logger.error(f"Error fetching {stat_type}: {e}")
        return []

    async def get_events(self, event_type: str, start_date: str | None = None, end_date: str | None = None, sub_type: str | None = None) -> list[dict]:
        import uuid
        if not self._client or not self.is_connected():
            return []
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
        from_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        to_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59).timestamp() * 1000)
        
        url = f"{self.ZEPP_EVENTS_API}/v2/users/me/events"
        params = {
            "eventType": event_type,
            "from": from_ts,
            "to": to_ts,
            "limit": 200,
            "r": str(uuid.uuid4())
        }
        if sub_type:
            params["subType"] = sub_type
            
        try:
            res = await self._client.get(url, params=params)
            if res.status_code == 200:
                return res.json().get("items", [])
        except Exception as e:
            logger.error(f"Error fetching events {event_type}: {e}")
        return []


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
