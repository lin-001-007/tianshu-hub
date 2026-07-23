"""系统日志 — Windows 事件 + 实时遥测动态"""
from __future__ import annotations

import json
import platform
import subprocess
import time
from typing import Any

from log_summarizer import enrich_log_row

_cache_events: list[dict[str, Any]] = []
_cache_events_ts: float = 0
_prev_metrics: dict[str, Any] | None = None

_LEVEL_CN = {
    "Critical": "严重", "Error": "错误", "Warning": "警告",
    "Information": "信息", "Verbose": "详细",
    "严重": "严重", "错误": "错误", "警告": "警告", "信息": "信息",
}


def _level_cn(level: str) -> str:
    return _LEVEL_CN.get(level, level or "信息")


def _now_str() -> str:
    return time.strftime("%H:%M:%S")


def _telemetry_feed(data: dict[str, Any], prev: dict[str, Any] | None) -> list[dict[str, Any]]:
    """根据指标变化生成实时动态日志（始终可用）"""
    rows: list[dict[str, Any]] = []
    cpu = data.get("cpu", {})
    mem = data.get("memory", {})
    disk = data.get("disk", {})
    net = data.get("network", {})
    sys = data.get("system", {})
    swap = data.get("swap", {})

    cpu_p = cpu.get("percent", 0)
    mem_p = mem.get("percent", 0)
    disk_p = disk.get("percent", 0)
    swap_p = swap.get("percent", 0)

    if cpu_p >= 90:
        rows.append({"time": _now_str(), "level": "严重", "source": "CPU", "message": f"CPU 负载极高 {cpu_p}% · {cpu.get('cores', 0)} 核 @ {cpu.get('freq_mhz', 0)} MHz"})
    elif cpu_p >= 70:
        rows.append({"time": _now_str(), "level": "警告", "source": "CPU", "message": f"CPU 负载偏高 {cpu_p}% · 频率 {cpu.get('freq_mhz', 0)} MHz"})

    if mem_p >= 90:
        rows.append({"time": _now_str(), "level": "严重", "source": "内存", "message": f"内存占用 {mem_p}% · 已用 {mem.get('used_gb', 0)} / {mem.get('total_gb', 0)} GB"})
    elif mem_p >= 75:
        rows.append({"time": _now_str(), "level": "警告", "source": "内存", "message": f"内存占用 {mem_p}% · 可用 {mem.get('available_gb', 0)} GB"})

    if swap_p >= 50:
        rows.append({"time": _now_str(), "level": "警告", "source": "交换区", "message": f"交换分区使用 {swap_p}% · 已用 {swap.get('used_gb', 0)} GB"})

    if disk_p >= 90:
        rows.append({"time": _now_str(), "level": "警告", "source": "磁盘", "message": f"磁盘空间不足 {disk_p}% · 剩余 {disk.get('free_gb', 0)} GB"})

    dr, dw = disk.get("read_mbps", 0), disk.get("write_mbps", 0)
    if dr + dw > 5:
        rows.append({"time": _now_str(), "level": "信息", "source": "磁盘I/O", "message": f"磁盘读写活跃 ↑{dw} ↓{dr} MB/s"})

    nu, nd = net.get("up_mbps", 0), net.get("down_mbps", 0)
    if nd > 1 or nu > 0.5:
        rows.append({"time": _now_str(), "level": "信息", "source": "网络", "message": f"网络流量 ↑{nu} ↓{nd} MB/s · 连接 {net.get('connections', 0)}"})

    per_core = cpu.get("per_core") or []
    if per_core:
        hot = max(range(len(per_core)), key=lambda i: per_core[i])
        if per_core[hot] >= 85:
            rows.append({"time": _now_str(), "level": "警告", "source": f"核心C{hot}", "message": f"逻辑核心 C{hot} 负载 {per_core[hot]}%"})

    rows.append({
        "time": _now_str(), "level": "信息", "source": "系统",
        "message": f"进程 {sys.get('processes', 0)} · 线程 {sys.get('threads', 0)} · 运行 {sys.get('uptime_hours', 0)}h",
    })

    bat = data.get("battery")
    if bat:
        lvl = "警告" if bat.get("percent", 100) < 20 and not bat.get("plugged") else "信息"
        plug = "充电中" if bat.get("plugged") else "放电"
        rows.append({"time": _now_str(), "level": lvl, "source": "电池", "message": f"电量 {bat.get('percent')}% · {plug}"})

    for temp in (data.get("temperatures") or [])[:2]:
        if temp.get("c", 0) >= 75:
            rows.append({
                "time": _now_str(), "level": "警告", "source": "温度",
                "message": f"{temp.get('label', 'sensor')} {temp.get('c')}°C",
            })

    if prev:
        pcpu = prev.get("cpu", {}).get("percent", 0)
        if abs(cpu_p - pcpu) >= 15:
            direction = "上升" if cpu_p > pcpu else "下降"
            rows.insert(0, {
                "time": _now_str(), "level": "信息", "source": "CPU",
                "message": f"CPU 负载{direction} {pcpu}% → {cpu_p}%",
            })

    return rows


def _collect_win_events(limit: int = 18) -> list[dict[str, Any]]:
    global _cache_events, _cache_events_ts
    now = time.time()
    if _cache_events and now - _cache_events_ts < 15:
        return _cache_events

    if platform.system() != "Windows":
        _cache_events = []
        _cache_events_ts = now
        return _cache_events

    ps = rf"""
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$out = @()
foreach ($log in @('System','Application')) {{
  try {{
    Get-WinEvent -FilterHashtable @{{LogName=$log; Level=1,2,3}} -MaxEvents 12 -ErrorAction Stop |
    ForEach-Object {{ $out += $_ }}
  }} catch {{}}
}}
if ($out.Count -eq 0) {{ exit 0 }}
$out | Sort-Object TimeCreated -Descending | Select-Object -First {limit} | ForEach-Object {{
  $msg = ($_.Message -replace '[\r\n\t]+',' ').Trim()
  if ($msg.Length -gt 220) {{ $msg = $msg.Substring(0,220) + '...' }}
  [PSCustomObject]@{{
    time = $_.TimeCreated.ToString('HH:mm:ss')
    level = $_.LevelDisplayName
    source = if ($_.ProviderName) {{ ($_.ProviderName).Substring(0, [Math]::Min(28, $_.ProviderName.Length)) }} else {{ 'System' }}
    message = $msg
  }}
}} | ConvertTo-Json -Compress -Depth 3
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
        raw = (proc.stdout or "").strip()
        if raw:
            parsed = json.loads(raw)
            rows = [parsed] if isinstance(parsed, dict) else list(parsed)
            _cache_events = [
                {
                    "time": r.get("time", _now_str()),
                    "level": _level_cn(str(r.get("level", "信息"))),
                    "source": str(r.get("source", "System"))[:28],
                    "message": str(r.get("message", "")),
                }
                for r in rows if r.get("message")
            ]
            _cache_events = [enrich_log_row(r, allow_ai=False) for r in _cache_events]
        else:
            _cache_events = []
    except Exception:
        pass

    _cache_events_ts = now
    return _cache_events


def collect_logs(metrics: dict[str, Any] | None = None, limit: int = 45, *, allow_ai: bool = False) -> list[dict[str, Any]]:
    global _prev_metrics
    data = metrics or {}
    feed = _telemetry_feed(data, _prev_metrics) if data else []
    events = _collect_win_events(limit=limit // 2)
    _prev_metrics = data if data else _prev_metrics

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in feed + events:
        key = f"{row.get('source')}|{row.get('raw') or row.get('message')}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
        if len(merged) >= limit:
            break

    # 统一概括：确保英文 Windows 事件都转为中文（含缓存中的旧数据）
    merged = [enrich_log_row(r, allow_ai=allow_ai) for r in merged]

    if not merged:
        merged = [{
            "time": _now_str(), "level": "信息", "source": "TIANSHU",
            "message": "遥测链路正常，等待系统事件…",
        }]
    return merged
