"""系统指标采集 — 15+ 性能维度"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from typing import Any

import psutil

_prev_disk: dict[str, int] | None = None
_prev_net: dict[str, int] | None = None
_prev_ts: float | None = None
_cpu_initialized = False
_gpu_cache: dict[str, Any] | None = None
_gpu_cache_ts: float = 0.0
_GPU_CACHE_SEC = 5.0

_CPU_TEMP_KEYS = ("cpu", "core", "package", "processor", "x86", "tdie", "ccd", "socket")


def _pick_cpu_temp_c(temps: list[dict[str, Any]]) -> tuple[float | None, bool]:
    """从传感器列表中优先选取 CPU 核心温度。返回 (温度, 是否估算)。"""
    if not temps:
        return None, True
    cpu_temps = [
        t["c"]
        for t in temps
        if any(k in t.get("label", "").lower() for k in _CPU_TEMP_KEYS)
    ]
    if cpu_temps:
        return round(max(cpu_temps), 1), False
    return round(max(t["c"] for t in temps), 1), False


def _gpu_name_wmi() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        ps = (
            "$skip='Microsoft|Remote|Basic|Virtual|Sharing Monitor|Oray|Idd|Indirect';"
            "$list=Get-CimInstance Win32_VideoController | Where-Object { "
            "$_.Name -and $_.Name -notmatch $skip -and $_.AdapterRAM -gt 0 };"
            "if(-not $list){"
            "$list=Get-CimInstance Win32_VideoController | Where-Object { "
            "$_.Name -and $_.Name -notmatch $skip };"
            "};"
            "($list | Sort-Object AdapterRAM -Descending | Select-Object -First 1 -ExpandProperty Name)"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=6,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        name = (proc.stdout or "").strip()
        return name or None
    except Exception:
        return None


def _collect_gpu_win() -> dict[str, Any] | None:
    gpu_name = _gpu_name_wmi()
    try:
        ps_cmd = (
            "$ErrorActionPreference='SilentlyContinue';"
            "$s=(Get-Counter '\\GPU Engine(*)\\Utilization Percentage').CounterSamples;"
            "if(-not $s){exit 1};"
            "$m=[double]($s | Measure-Object CookedValue -Maximum).Maximum;"
            "$mem=0;"
            "$ma=(Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage' -EA SilentlyContinue).CounterSamples;"
            "if($ma){$mt=[double]($ma | Measure-Object CookedValue -Maximum).Maximum;$mem=[math]::Round($mt,1)};"
            "@{load=[math]::Round($m,1);mem=$mem} | ConvertTo-Json -Compress"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            payload = json.loads(proc.stdout.strip())
            load = float(payload.get("load", 0))
            mem = float(payload.get("mem", 0))
            if load >= 0:
                return {
                    "available": True,
                    "load_percent": load,
                    "mem_percent": mem,
                    "name": gpu_name or "GPU",
                }
    except Exception:
        pass

    if gpu_name:
        return {
            "available": True,
            "load_percent": 0.0,
            "mem_percent": 0.0,
            "name": gpu_name,
        }
    return None


def _collect_gpu() -> dict[str, Any]:
    """采集 GPU 负载（NVIDIA NVML / Windows 性能计数器 / WMI 名称）。"""
    fallback: dict[str, Any] = {
        "available": False,
        "load_percent": 0.0,
        "mem_percent": 0.0,
        "name": "未检测到 GPU",
    }
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")
        return {
            "available": True,
            "load_percent": round(float(util.gpu), 1),
            "mem_percent": round(mem.used / mem.total * 100, 1),
            "mem_used_mb": round(mem.used / 1024**2),
            "mem_total_mb": round(mem.total / 1024**2),
            "name": str(name),
        }
    except Exception:
        pass

    if sys.platform == "win32":
        win = _collect_gpu_win()
        if win:
            return win
    return fallback


def warm_caches() -> None:
    """启动时预热 GPU 等慢速采集，避免首屏显示未检测到。"""
    try:
        _collect_gpu_cached()
    except Exception:
        pass


def _collect_gpu_cached() -> dict[str, Any]:
    global _gpu_cache, _gpu_cache_ts
    now = time.time()
    if _gpu_cache is not None and now - _gpu_cache_ts < _GPU_CACHE_SEC:
        return _gpu_cache
    _gpu_cache = _collect_gpu()
    _gpu_cache_ts = now
    return _gpu_cache


def _rate(cur: int, prev: int, dt: float) -> float:
    if dt <= 0:
        return 0.0
    return max(0.0, (cur - prev) / dt / 1024 / 1024)


def collect_metrics() -> dict[str, Any]:
    global _prev_disk, _prev_net, _prev_ts, _cpu_initialized

    now = time.time()
    dt = (now - _prev_ts) if _prev_ts else 1.0

    if not _cpu_initialized:
        psutil.cpu_percent(interval=None)
        _cpu_initialized = True

    cpu = psutil.cpu_percent(interval=None)
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    io = psutil.disk_io_counters()
    net = psutil.net_io_counters()

    disk_read_mbps = disk_write_mbps = 0.0
    if io and _prev_disk and dt > 0:
        disk_read_mbps = _rate(io.read_bytes, _prev_disk["read"], dt)
        disk_write_mbps = _rate(io.write_bytes, _prev_disk["write"], dt)
    if io:
        _prev_disk = {"read": io.read_bytes, "write": io.write_bytes}

    net_up_mbps = net_down_mbps = 0.0
    if net and _prev_net and dt > 0:
        net_up_mbps = _rate(net.bytes_sent, _prev_net["sent"], dt)
        net_down_mbps = _rate(net.bytes_recv, _prev_net["recv"], dt)
    if net:
        _prev_net = {"sent": net.bytes_sent, "recv": net.bytes_recv}

    _prev_ts = now

    freq = psutil.cpu_freq()
    boot = psutil.boot_time()
    uptime_sec = now - boot

    conn_count = 0
    try:
        conn_count = len(psutil.net_connections(kind="inet"))
    except (psutil.AccessDenied, psutil.Error):
        pass

    pids = psutil.pids()
    proc_count = len(pids)

    thread_count = 0
    try:
        for p in psutil.process_iter(["num_threads"]):
            thread_count += p.info.get("num_threads") or 0
    except (psutil.AccessDenied, psutil.Error):
        thread_count = proc_count * 4

    battery = None
    try:
        bat = psutil.sensors_battery()
        if bat:
            battery = {"percent": bat.percent, "plugged": bat.power_plugged}
    except Exception:
        pass

    temps = []
    try:
        if hasattr(psutil, "sensors_temperatures"):
            for name, entries in (psutil.sensors_temperatures() or {}).items():
                for e in entries[:2]:
                    if e.current is not None:
                        temps.append({"label": f"{name}/{e.label or 'core'}", "c": round(e.current, 1)})
    except Exception:
        pass

    load_avg = list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [0, 0, 0]

    cpu_temp_c, temp_estimated = _pick_cpu_temp_c(temps)
    if cpu_temp_c is None:
        cpu_temp_c = round(38 + (cpu / 100) * 42, 1)
        temp_estimated = True

    return {
        "timestamp": now,
        "cpu": {
            "percent": round(cpu, 1),
            "per_core": [round(x, 1) for x in per_cpu],
            "cores": len(per_cpu),
            "freq_mhz": round(freq.current, 0) if freq else 0,
            "load_1m": round(load_avg[0], 2) if load_avg else 0,
            "temp_c": cpu_temp_c,
            "temp_estimated": temp_estimated,
        },
        "memory": {
            "percent": round(mem.percent, 1),
            "used_gb": round(mem.used / 1024**3, 2),
            "total_gb": round(mem.total / 1024**3, 2),
            "available_gb": round(mem.available / 1024**3, 2),
        },
        "swap": {
            "percent": round(swap.percent, 1),
            "used_gb": round(swap.used / 1024**3, 2),
        },
        "disk": {
            "percent": round(disk.percent, 1),
            "read_mbps": round(disk_read_mbps, 2),
            "write_mbps": round(disk_write_mbps, 2),
            "free_gb": round(disk.free / 1024**3, 2),
        },
        "network": {
            "up_mbps": round(net_up_mbps, 2),
            "down_mbps": round(net_down_mbps, 2),
            "connections": conn_count,
            "packets_sent": net.packets_sent if net else 0,
            "packets_recv": net.packets_recv if net else 0,
        },
        "system": {
            "processes": proc_count,
            "threads": thread_count,
            "uptime_hours": round(uptime_sec / 3600, 2),
            "uptime_sec": int(uptime_sec),
            "boot_ts": boot,
        },
        "battery": battery,
        "temperatures": temps[:6],
        "gpu": _collect_gpu_cached(),
    }


def metric_cards(data: dict[str, Any]) -> list[dict[str, Any]]:
    """扁平化 16+ 指标卡片供 HUD 展示"""
    c, m, s, d, n, sys = data["cpu"], data["memory"], data["swap"], data["disk"], data["network"], data["system"]
    cards = [
        {"id": "cpu", "label": "CPU 总负载", "value": c["percent"], "unit": "%", "group": "core"},
        {"id": "cpu_freq", "label": "CPU 频率", "value": c["freq_mhz"], "unit": "MHz", "group": "core"},
        {"id": "cpu_load", "label": "系统负载", "value": c["load_1m"], "unit": "", "group": "core"},
        {"id": "cpu_temp", "label": "CPU 核心温度", "value": c["temp_c"], "unit": "°C", "group": "core"},
        {"id": "mem", "label": "内存占用", "value": m["percent"], "unit": "%", "group": "mem"},
        {"id": "mem_used", "label": "已用内存", "value": m["used_gb"], "unit": "GB", "group": "mem"},
        {"id": "mem_avail", "label": "可用内存", "value": m["available_gb"], "unit": "GB", "group": "mem"},
        {"id": "swap", "label": "交换分区", "value": s["percent"], "unit": "%", "group": "mem"},
        {"id": "disk", "label": "磁盘使用", "value": d["percent"], "unit": "%", "group": "io"},
        {"id": "disk_r", "label": "磁盘读取", "value": d["read_mbps"], "unit": "MB/s", "group": "io"},
        {"id": "disk_w", "label": "磁盘写入", "value": d["write_mbps"], "unit": "MB/s", "group": "io"},
        {"id": "disk_free", "label": "磁盘剩余", "value": d["free_gb"], "unit": "GB", "group": "io"},
        {"id": "net_up", "label": "网络上传", "value": n["up_mbps"], "unit": "MB/s", "group": "net"},
        {"id": "net_down", "label": "网络下载", "value": n["down_mbps"], "unit": "MB/s", "group": "net"},
        {"id": "net_conn", "label": "网络连接", "value": n["connections"], "unit": "", "group": "net"},
        {"id": "proc", "label": "进程数", "value": sys["processes"], "unit": "", "group": "sys"},
        {"id": "thread", "label": "线程数", "value": sys["threads"], "unit": "", "group": "sys"},
        {"id": "uptime", "label": "运行时长", "value": sys["uptime_hours"], "unit": "h", "group": "sys"},
    ]
    if data.get("gpu", {}).get("available"):
        g = data["gpu"]
        cards.insert(4, {"id": "gpu", "label": "GPU 负载", "value": g["load_percent"], "unit": "%", "group": "core"})
        if g.get("mem_percent"):
            cards.insert(5, {"id": "gpu_mem", "label": "GPU 显存", "value": g["mem_percent"], "unit": "%", "group": "core"})
    elif data.get("gpu", {}).get("name") and data["gpu"]["name"] != "未检测到 GPU":
        g = data["gpu"]
        cards.insert(4, {"id": "gpu", "label": "GPU 负载", "value": g.get("load_percent", 0), "unit": "%", "group": "core"})
    if data.get("battery"):
        cards.append({"id": "battery", "label": "电池", "value": data["battery"]["percent"], "unit": "%", "group": "power"})
    for i, t in enumerate(data.get("temperatures") or []):
        cards.append({"id": f"temp_{i}", "label": t["label"], "value": t["c"], "unit": "°C", "group": "thermal"})
    return cards
