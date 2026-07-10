# Zepp Life MCP

[![CI](https://github.com/kubulashvili/zepp-life-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/kubulashvili/zepp-life-mcp/actions/workflows/ci.yml)

Zepp Life (原小米运动) 的 Model Context Protocol (MCP) Server。本项目提供本地缓存、数据同步，以及为 AI 提供的标准 MCP 工具，能够直接从 Zepp Cloud 的接口流中拉取极其丰富的健康和运动数据。

---

## 目录

- [📊 深度数据接口 Wiki](#-深度数据接口-wiki)
  - [实时 / 高频数据 (连续监测)](#实时--高频数据-连续监测)
  - [事件触发数据](#事件触发数据)
  - [每日汇总数据 (快照)](#每日汇总数据-快照)
  - [高阶 Firstbeat 分析数据](#高阶-firstbeat-分析数据)
- [🛠 安装与配置](#-安装与配置)
- [🚀 运行与命令](#-运行与命令)
- [🔌 MCP 客户端配置](#-mcp-客户端配置)
- [⚠️ 常见问题](#-常见问题)

---

## 📊 深度数据接口 Wiki

当前的实现经过逆向工程与深度拓展，已经能够覆盖 Zepp 云端 API 所暴露的几乎所有高保真健康数据。以下详细说明了到底有多少数据是可以被读取的、更新频率以及适用场景，作为后续代码开发的接口参考字典。

### 实时 / 高频数据 (连续监测)

这些端点提供详细的时间序列数组。适合在白天周期性拉取，以追踪生理状态的实时变化。

| 数据类型 | 英文标识 | 频率 | 核心指标 | 适用场景 |
|---------|----------|------|---------|----------|
| **心率** | `heart_rate` | 最高可达每分钟 | `timestamp`, `bpm`, `sample_type` | 实时压力推断、活跃状态追踪、静息心率提取 |
| **全天压力** | `stress` | 每 5 分钟 (佩戴时) | `timestamp`, `stress_score` (0-100), `level` | 情绪追踪、工作疲劳度评估、"何时该休息"的生理学信号 |
| **血氧** | `blood_oxygen`| 每天周期性及睡眠期 | `timestamp`, `spo2_pct` | 睡眠呼吸中止指标、高原适应性 |

### 事件触发数据

在完成特定行为或运动后生成的数据集。

| 数据类型 | 英文标识 | 频率 | 核心指标 | 适用场景 |
|---------|----------|------|---------|----------|
| **运动记录** | `workouts` | 运动结束后生成 | `activity_type`, `duration_minutes`, `avg_heart_rate_bpm` | 训练日志、卡路里消耗追踪 |

### 每日汇总数据 (快照)

这些数据集每天汇总或生成一次（通常在起床后或午夜）。

| 数据类型 | 英文标识 | 频率 | 核心指标 / 适用场景 |
|---------|----------|------|--------------------|
| **每日活动汇总** | `daily_activity` | 每天/累加 | 步数、距离、活动卡路里、活动分钟数 |
| **睡眠分析** | `sleep` | 睡醒/午休后 | `time_asleep_minutes`, `sleep_score`，以及深浅睡、REM 分期时间，**同时支持白日小睡 (Nap) 识别**。适合晨间报告。 |
| **身心准备度** | `readiness` | 每天睡醒后 | **隐藏端点**。包含 `rdnsScore` (准备度评分), `sleepHRV` (睡眠心率变异性), `sleepRHR` (睡眠静息心率), `phyScore` (身体评分), `mentScore` (精神评分)。**适合判断今日能量水位**。 |
| **个人活力指数** | `pai` | 每天 | `dailyPai`, `totalPai`。用于每周心血管负荷追踪。 |
| **身体数据 (体脂秤)** | `body_measurements`| 手动称重时 | 除了基础的 `weight`, `bmi` 外，最新逆向已支持**全量高阶体脂数据**：`fatRate` (体脂率), `bodyWaterRate` (水分), `muscleRate` (肌肉量), `visceralFat` (内脏脂肪), `boneMass` (骨量), `metabolism` (基础代谢) 等 10+ 项指标！ |
| **血压** | `bloodPressure` | 测量时 | `sbp` (收缩压), `dbp` (舒张压), `bpm` | 心血管健康监控 |
| **心电图 (ECG)** | `ECGHealthData` | 测量时 | 详细心电图数据 | 心脏健康、心律不齐筛查 |
| **女性健康** | `women_health` | 记录时 | `menstrualCycle`, `lastMenstrualTime` | 经期追踪与预测 |
| **心率变异性 (HRV)** | `HRVRMSSD` | 事件触发 | RMSSD 值 | 神经系统压力与恢复指标 |
| **设备充电与电量** | `Charge` | 充电时 | 充电事件 (`insight_data`, `real_data`) | 设备电池分析 |

### 高阶 Firstbeat 分析数据

这些经过高度处理的专业训练指标通过分析 HAR 文件发现，并已集成到本系统中。通过 `WatchSportStatistics` 端点或带有特定子类型的 `events` 获取。

| 数据类型 | 英文标识 | 频率 | 核心指标 | 适用场景 |
|---------|----------|------|---------|----------|
| **训练负荷与状态** | `phn` | 每天 | `atl` (疲劳度), `ctl` (体能水平), `tsb` (训练状态), `trimp` (训练冲量) | 专业体能状态追踪、防过度训练预警 |
| **恢复时间** | `exertion` | 运动后/每天 | `recoveryFactor` (恢复时间乘数), `exercisePlan` | 运动后恢复指导 |
| **最大摄氧量** | `VO2_MAX` | 合格的跑走后 | `vo2_max_run`, `vo2_max_walking` | 长期心血管健康趋势 |
| **运动负荷** | `SPORT_LOAD` | 每日汇总 | `currnetDayTrainLoad`, `wtlSum` (总训练负荷) | 确保训练负荷在最佳区间内 |

---

## 🛠 安装与配置

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 自动登录 (推荐)
在项目根目录创建一个 `.env` 文件并添加你的 Zepp 账号凭证：
```env
ZEPP_USERNAME=your_email@example.com
ZEPP_PASSWORD=your_password
```
MCP 会自动登录，获取 `apptoken` 和 `user_id`，并将其保存到 `.env` 文件中。它也会在令牌过期时自动刷新。

---

## 🚀 运行与命令

```bash
# 同步数据
zepp-life-mcp sync --start-date 2026-07-01 --end-date 2026-07-10

# 启动 MCP Server
zepp-life-mcp serve
```

其他帮助命令：
```bash
zepp-life-mcp --help
zepp-life-mcp setup --help
zepp-life-mcp doctor
```

---

## 🔌 MCP 客户端配置

在支持 MCP 的客户端（例如 Claude Desktop）中配置如下：

```json
{
  "mcpServers": {
    "zepp-life": {
      "command": "zepp-life-mcp",
      "args": ["serve"]
    }
  }
}
```

---

## ⚠️ 常见问题

- `Connection: failed`: 请验证 `.env` 中的 `apptoken` 和 `user_id`。
- `sync` 返回空数据: Zepp Cloud 可能存在延迟（有时高达 2 小时），手环数据尚未同步到云端。请在 Zepp App 首页下拉强制同步，然后再尝试。

---

> **免责声明**
> 本项目是非官方开源项目，与小米 (Xiaomi) 或 Zepp Health 无任何附属关系。
