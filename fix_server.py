import sys
import re

file_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/src/zepp_life_mcp/server.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add timedelta to imports
content = content.replace("from datetime import datetime", "from datetime import datetime, timedelta")

# 2. Add to list_tools (at the end of the Tool list)
tools_to_add = """
        Tool(
            name="get_respiratory_rate",
            description="Get continuous respiratory rate data during sleep or rest.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD), defaults to 7 days ago"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD), defaults to today"
                    }
                }
            }
        ),
        Tool(
            name="get_sport_routes",
            description="Get GPS sport routes (e.g., from Komoot or watch).",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD), defaults to 30 days ago"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD), defaults to today"
                    }
                }
            }
        ),
        Tool(
            name="get_training_plans",
            description="Get structured training plans or Zepp Coach schedules.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]"""
content = re.sub(r'(\s+Tool\([^]]+)(\n\s+\])', r'\1' + tools_to_add, content)

# 3. Add to dt_map for auto-sync
dt_map_addition = """
                "query_pai": "pai",
                "get_respiratory_rate": "respiratory_rate",
                "get_sport_routes": "sport_routes",
                "get_training_plans": "training_plans"
            }"""
content = content.replace('"query_pai": "pai"\n            }', dt_map_addition)

# 4. Add branches to call_tool
branches = """
        elif name == "get_respiratory_rate":
            result = await _handle_get_respiratory_rate(arguments)
        elif name == "get_sport_routes":
            result = await _handle_get_sport_routes(arguments)
        elif name == "get_training_plans":
            result = await _handle_get_training_plans(arguments)
        else:"""
content = content.replace("        else:", branches, 1)

# 5. Define handler functions
handlers = """
async def _handle_get_respiratory_rate(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = query_service.get_user_id()
        if not user_id:
            return {"status": "error", "error": "No user configured or logged in."}

        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else end_dt - timedelta(days=7)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        records = query_service.db.query_respiratory_rate_samples(user_id, start_str, end_str)
        
        return {
            "status": "ok",
            "source": query_service.connection_status["mode"],
            "count": len(records),
            "data": records
        }
    except Exception as e:
        logger.exception("Failed to get respiratory rate")
        return {"status": "error", "error": str(e)}

async def _handle_get_sport_routes(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = query_service.get_user_id()
        if not user_id:
            return {"status": "error", "error": "No user configured or logged in."}

        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else end_dt - timedelta(days=30)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        records = query_service.db.query_sport_routes(user_id, start_str, end_str)
        
        return {
            "status": "ok",
            "source": query_service.connection_status["mode"],
            "count": len(records),
            "data": records
        }
    except Exception as e:
        logger.exception("Failed to get sport routes")
        return {"status": "error", "error": str(e)}

async def _handle_get_training_plans(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = query_service.get_user_id()
        if not user_id:
            return {"status": "error", "error": "No user configured or logged in."}

        records = query_service.db.query_training_plans(user_id)
        
        return {
            "status": "ok",
            "source": query_service.connection_status["mode"],
            "count": len(records),
            "data": records
        }
    except Exception as e:
        logger.exception("Failed to get training plans")
        return {"status": "error", "error": str(e)}


async def _connect_adapter_async(adapter):"""
content = content.replace("async def _connect_adapter_async(adapter):", handlers)

# 6. Remove the bad @mcp.tool blocks (from @mcp.tool() down to async def main():)
content = re.sub(r'@mcp\.tool\(\).*?(?=\nasync def main\(\):)', '', content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("server patched")
