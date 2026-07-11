import sys

file_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/src/zepp_life_mcp/adapters/export_file.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
import_replace = """    HeartRateSample,
    SleepSession,
    Workout,
    RespiratoryRateSample,
    SportRoute,
    TrainingPlan,
)"""
content = content.replace("    HeartRateSample,\n    SleepSession,\n    Workout,\n)", import_replace)


methods = """
    def iter_respiratory_rate(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> Iterator[RespiratoryRateSample]:
        # Not yet implemented for CSV exports
        return iter([])

    def iter_sport_routes(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> Iterator[SportRoute]:
        # Not yet implemented for CSV exports
        return iter([])

    def iter_training_plans(self) -> Iterator[TrainingPlan]:
        # Not yet implemented for CSV exports
        return iter([])
"""

content = content + "\n" + methods

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("export patched")
