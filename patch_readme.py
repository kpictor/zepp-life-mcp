import sys

file_path = "/Users/dicrix/Documents/GitHub/DayLi/vendor/zepp-life-mcp/README.md"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add to Real-time
rt_replacement = """| **心率** | `heart_rate` | 最高可达每分钟 | `timestamp`, `bpm`, `sample_type` | 实时压力推断、活跃状态追踪、静息心率提取 |
| **全天压力** | `stress` | 每 5 分钟 (佩戴时) | `timestamp`, `stress_score` (0-100), `level` | 情绪追踪、工作疲劳度评估、"何时该休息"的生理学信号 |
| **血氧** | `blood_oxygen`| 每天周期性及睡眠期 | `timestamp`, `spo2_pct` | 睡眠呼吸中止指标、高原适应性 |
| **呼吸速率 (新)** | `RespiratoryRate` | 睡眠期间连续 | `timestamp`, `rate` (估算) | 睡眠呼吸中止指标、深度疲劳恢复、睡眠医疗级监测 |"""
content = content.replace("| **心率** | `heart_rate` | 最高可达每分钟 | `timestamp`, `bpm`, `sample_type` | 实时压力推断、活跃状态追踪、静息心率提取 |\n| **全天压力** | `stress` | 每 5 分钟 (佩戴时) | `timestamp`, `stress_score` (0-100), `level` | 情绪追踪、工作疲劳度评估、\"何时该休息\"的生理学信号 |\n| **血氧** | `blood_oxygen`| 每天周期性及睡眠期 | `timestamp`, `spo2_pct` | 睡眠呼吸中止指标、高原适应性 |", rt_replacement)

# Add to Event triggered
et_replacement = """| **运动记录** | `workouts` | 运动结束后生成 | `activity_type`, `duration_minutes`, `avg_heart_rate_bpm` | 训练日志、卡路里消耗追踪 |
| **运动轨迹 (新)** | `sport_route` | 户外运动后生成 | 轨迹路线ID，经纬度边界，累计爬升 | 地形分析，运动难度与爬升的关系，地图可视化 |"""
content = content.replace("| **运动记录** | `workouts` | 运动结束后生成 | `activity_type`, `duration_minutes`, `avg_heart_rate_bpm` | 训练日志、卡路里消耗追踪 |", et_replacement)

# Add new section for Training Plans before "高阶 Firstbeat 分析数据"
tp_section = """### 智能教练与训练规划 (Proactive Coaching)

这些端点不再仅仅是“被动”记录，而是包含用户**未来**的训练日程安排（例如 Zepp Coach 生成的计划）。这能极大提升 AI 的预测和主动规划能力。

| 数据类型 | 英文标识 | 频率 | 核心指标 | 适用场景 |
|---------|----------|------|---------|----------|
| **训练计划日程** | `training_plans` | 周期性获取 | 计划的起始时间，课程描述，目标 | 智能体可以通过日程提前调整你的作息建议（如“明早有高强度跑，今晚早点睡”） |

### 高阶 Firstbeat 分析数据"""
content = content.replace("### 高阶 Firstbeat 分析数据", tp_section)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("readme patched")
