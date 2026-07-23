"""日志中文概括 — 英文/代码/报错类 Windows 事件转为可读中文"""
from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 6 * 3600
_AI_TIMEOUT = 3.0

_TECH_PATTERNS = (
    r"0x[0-9a-fA-F]{4,}",
    r"\bHRESULT\b",
    r"\bException\b",
    r"\bError\b",
    r"\bfailed\b",
    r"\btimeout\b",
    r"\\\\",
    r"\[[A-Za-z_]+\]",
    r"\{[0-9a-fA-F-]{8,}\}",
    r"::",
    r"\.dll\b",
    r"\.exe\b",
    r"Service Control Manager",
    r"Application Error",
    r"INPUT_SUPPRESS",
    r"Power Manager",
    r"could not be shut down",
    r"RestartManager",
    r"Output Queue",
)

# (pattern, 中文说明) — 按优先级排列
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"input_suppress|power manager", re.I),
     "电源管理切换了输入抑制策略，一般属于正常系统通知。"),
    (re.compile(r"histenapo|post_mfx|output queue|audio|apo", re.I),
     "音频驱动处理队列异常或为空，多为驱动层提示，通常可忽略。"),
    (re.compile(r"could not be shut down|restartmanager|restart manager", re.I),
     "关机或重启时某个程序未能正常退出，可能占用文件导致延迟。"),
    (re.compile(r"microsoft office|sdx helper|office", re.I),
     "Microsoft Office 相关进程退出异常，可能影响 Office 更新或后台任务。"),
    (re.compile(r"service.*did not respond|service control manager", re.I),
     "系统服务未及时响应，可能是服务卡住或启动超时。"),
    (re.compile(r"application error|faulting application", re.I),
     "某个应用程序发生崩溃，Windows 已记录错误模块信息。"),
    (re.compile(r"distributedcom|dcom|0x800", re.I),
     "组件服务(DCOM)调用失败，常见于权限或远程组件不可用。"),
    (re.compile(r"disk|ntfs|volsnap|storage", re.I),
     "磁盘或存储子系统出现异常，建议检查磁盘健康与空间。"),
    (re.compile(r"network|tcp|dhcp|dns|winsock", re.I),
     "网络组件出现异常，可能影响联网或本地服务通信。"),
    (re.compile(r"kernel-power|unexpected shutdown", re.I),
     "系统发生过意外断电或异常关机，可能导致未保存数据丢失。"),
    (re.compile(r"timeout|timed out", re.I),
     "操作超时，目标服务或设备未在限定时间内响应。"),
    (re.compile(r"access denied|permission|0x5\b", re.I),
     "访问被拒绝，当前进程可能缺少所需权限。"),
    (re.compile(r"memory|page fault|out of memory", re.I),
     "内存资源紧张或发生内存访问异常。"),
    (re.compile(r"driver|\.sys\b", re.I),
     "驱动程序相关异常，可能影响硬件或系统稳定性。"),
    (re.compile(r"win32k", re.I),
     "Windows 图形/输入子系统(Win32k)上报事件，多与显示或输入策略有关。"),
    (re.compile(r"update|windows update|wuauserv", re.I),
     "Windows 更新服务出现问题，可能影响补丁安装。"),
    (re.compile(r"firewall|defender|security", re.I),
     "安全或防火墙组件上报异常，建议检查安全软件状态。"),
]


def _cn_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(re.findall(r"[\u4e00-\u9fff]", text)) / len(text)


def _has_latin(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]{3,}", text))


def needs_summarize(message: str, level: str = "") -> bool:
    msg = (message or "").strip()
    if len(msg) < 4:
        return False
    if _cn_ratio(msg) >= 0.35:
        return False
    if level in ("警告", "错误", "严重") and _has_latin(msg):
        return True
    if any(re.search(p, msg, re.I) for p in _TECH_PATTERNS):
        return True
    ascii_words = len(re.findall(r"[A-Za-z]{3,}", msg))
    return ascii_words >= 2 and _cn_ratio(msg) < 0.15


def _rule_summary(message: str) -> tuple[str, bool]:
    msg = message.strip()
    for pat, desc in _RULES:
        if pat.search(msg):
            return desc, True
    m = re.search(r"Event ID[:\s]+(\d+)", msg, re.I)
    if m:
        return f"Windows 系统事件 ID {m.group(1)}，建议到事件查看器查看详情。", True
    m = re.search(r"0x[0-9a-fA-F]{4,}", msg)
    if m:
        return f"系统报错，错误码 {m.group(0)}，通常表示组件调用或资源访问失败。", True
    if re.search(r"failed|error|warning", msg, re.I):
        return "系统组件报告异常，可能影响相关功能，建议查看事件查看器。", True
    if _has_latin(msg):
        return "系统上报了一条英文技术日志，已自动转换为简要说明。", False
    return msg, False


def _ai_summary(message: str) -> str | None:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key or httpx is None:
        return None

    model = os.getenv("HUD_LOG_MODEL", "qwen-turbo")
    prompt = (
        "你是 Windows 运维助手。把下面系统日志/报错用一句简短中文解释（不超过40字）。"
        "要求：只说人话、不要英文、不要代码、不要引号。\n\n"
        f"{message[:500]}"
    )
    try:
        resp = httpx.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 100,
            },
            timeout=_AI_TIMEOUT,
        )
        resp.raise_for_status()
        text = (
            resp.json().get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        text = re.sub(r"^[\"'「『]|[\"'」』]$", "", text)
        if text and _cn_ratio(text) >= 0.3:
            return text[:80]
    except Exception:
        pass
    return None


def enrich_log_row(row: dict[str, Any], *, allow_ai: bool = False) -> dict[str, Any]:
    level = str(row.get("level", ""))
    raw = str(row.get("raw") or row.get("message", "")).strip()
    if not raw:
        return row

    if row.get("summarized") and row.get("raw") and _cn_ratio(str(row.get("message", ""))) >= 0.25:
        return row

    if not needs_summarize(raw, level):
        return {**row, "message": raw, "raw": None, "summarized": False}

    rule_text, matched = _rule_summary(raw)
    if matched:
        summary = rule_text
    elif allow_ai:
        summary = _ai_summary(raw) or rule_text
    else:
        summary = rule_text

    return {
        **row,
        "message": summary,
        "raw": raw,
        "summarized": True,
    }
