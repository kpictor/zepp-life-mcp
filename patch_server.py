import sys

file_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/src/zepp_life_mcp/server.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_tools = """
@mcp.tool()
async def get_respiratory_rate(
    start_date: str | None = None,
    end_date: str | None = None,
    ctx: Context | None = None,
) -> str:
    \"\"\"Get continuous respiratory rate data during sleep or rest.
    
    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 7 days ago
        end_date: End date (YYYY-MM-DD), defaults to today
    \"\"\"
    try:
        user_id = query_service.get_user_id()
        if not user_id:
            return "Error: No user configured or logged in."

        # Parse dates
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else end_dt - timedelta(days=7)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        records = query_service.db.query_respiratory_rate_samples(user_id, start_str, end_str)
        
        if not records:
            return f"No respiratory rate records found between {start_str} and {end_str}."

        result = {
            "status": "ok",
            "source": query_service.connection_status["mode"],
            "count": len(records),
            "data": records
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.exception("Failed to get respiratory rate")
        return f"Error: {e!s}"

@mcp.tool()
async def get_sport_routes(
    start_date: str | None = None,
    end_date: str | None = None,
    ctx: Context | None = None,
) -> str:
    \"\"\"Get GPS sport routes (e.g., from Komoot or watch).
    
    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 30 days ago
        end_date: End date (YYYY-MM-DD), defaults to today
    \"\"\"
    try:
        user_id = query_service.get_user_id()
        if not user_id:
            return "Error: No user configured or logged in."

        # Parse dates
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else end_dt - timedelta(days=30)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        records = query_service.db.query_sport_routes(user_id, start_str, end_str)
        
        if not records:
            return f"No sport routes found between {start_str} and {end_str}."

        result = {
            "status": "ok",
            "source": query_service.connection_status["mode"],
            "count": len(records),
            "data": records
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.exception("Failed to get sport routes")
        return f"Error: {e!s}"

@mcp.tool()
async def get_training_plans(
    ctx: Context | None = None,
) -> str:
    \"\"\"Get structured training plans or Zepp Coach schedules.
    
    This includes future scheduled workouts.
    \"\"\"
    try:
        user_id = query_service.get_user_id()
        if not user_id:
            return "Error: No user configured or logged in."

        records = query_service.db.query_training_plans(user_id)
        
        if not records:
            return f"No training plans found."

        result = {
            "status": "ok",
            "source": query_service.connection_status["mode"],
            "count": len(records),
            "data": records
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.exception("Failed to get training plans")
        return f"Error: {e!s}"

def main():"""

content = content.replace("def main():", new_tools)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("server patched")
