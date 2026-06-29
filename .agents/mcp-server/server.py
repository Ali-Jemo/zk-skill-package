#!/usr/bin/env python3
"""
Kernel Engineering MCP Server
"""

from mcp.server import Server
from mcp.types import TextContent, Tool, Prompt, PromptArgument, GetPromptResult, PromptMessage, TextContent as PromptTextContent
from typing import Any
import json
import argparse
import sqlite3
import os
import subprocess

SUBSYSTEMS = {
    "memory": {"name": "Memory", "patterns": [("page fault at 0x0", "null pointer")], "questions": ["Is address valid?"]},
    "interrupts": {"name": "Interrupts", "patterns": [("triple fault", "IDT issue")], "questions": ["Is IDT loaded?"]},
    "scheduler": {"name": "Scheduler", "patterns": [("freeze on PID switch", "scheduler issue")], "questions": ["Is timer ticking?"]},
    "syscalls": {"name": "Syscalls", "patterns": [("EINVAL", "invalid args")], "questions": ["Is number correct?"]},
    "elf-loader": {"name": "ELF Loader", "patterns": [("fault at entry", "missing mapping")], "questions": ["Is header valid?"]},
    "ipc": {"name": "IPC", "patterns": [("send success recv fail", "channel mismatch")], "questions": ["Does channel exist?"]},
    "drivers": {"name": "Drivers", "patterns": [("input intermittent", "IRQ handling")], "questions": ["Device detected?"]},
}

BOOT_FLOW = ["1. Firmware", "2. Bootloader"]
HANGS = {"visual": {"description": "GUI stop", "checks": []}}
INVARIANTS = ["No kernel/user overlap"]
PATCH_AVOID = ["rewrites", "style edits"]
DEBUG_ORDER = ["Read log", "Classify failure"]
ARCH_TYPES = {"monolithic": {"description": "All in kernel"}}
BUILD_COMMON_MISTAKES = ["wrong target"]
PROJECT_RULES = {"rules": ["FFI: Zig", "IPC: Ring buffer"]}

app = Server("kernel-engineering")
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.memory/errmem.db"))

def _init_errmem_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, symptom TEXT, subsystem TEXT, root_cause TEXT, files_changed TEXT, verification TEXT)")
    conn.close()

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="kernel.subsystem_questions", description="Get diagnostic questions", inputSchema={"type": "object", "properties": {"subsystem": {"type": "string"}}, "required": ["subsystem"]}),
        Tool(name="kernel.diagnose", description="Identify subsystem from symptom", inputSchema={"type": "object", "properties": {"symptom": {"type": "string"}}, "required": ["symptom"]}),
        Tool(name="kernel.analyze_serial", description="Analyze serial logs", inputSchema={"type": "object", "properties": {"log_content": {"type": "string"}}, "required": ["log_content"]}),
        Tool(name="kernel.graph_query", description="Query knowledge graph", inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        Tool(name="kernel.errmem_search", description="Search incidents", inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        Tool(name="kernel.errmem_add", description="Add incident", inputSchema={"type": "object", "properties": {"symptom": {"type": "string"}}, "required": ["symptom"]}),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "kernel.subsystem_questions":
        return [TextContent(type="text", text=json.dumps(SUBSYSTEMS.get(arguments["subsystem"], {})))]
    elif name == "kernel.diagnose":
        return [TextContent(type="text", text="Diagnose result...")]
    elif name == "kernel.analyze_serial":
        return [TextContent(type="text", text="Serial analysis: PANIC detected")]
    elif name == "kernel.graph_query":
        try:
            result = subprocess.run(["graphify", "query", arguments["query"]], capture_output=True, text=True, timeout=5)
            return [TextContent(type="text", text=result.stdout)]
        except Exception as e:
            return [TextContent(type="text", text=str(e))]
    elif name == "kernel.errmem_search":
        _init_errmem_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT * FROM incidents WHERE symptom LIKE ?", (f"%{arguments['query']}%",))
        return [TextContent(type="text", text=json.dumps(cursor.fetchall()))]
    elif name == "kernel.errmem_add":
        _init_errmem_db()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO incidents (symptom, subsystem) VALUES (?, ?)", (arguments["symptom"], arguments.get("subsystem", "unknown")))
        conn.commit()
        conn.close()
        return [TextContent(type="text", text="Added.")]
    return [TextContent(type="text", text="Tool not found.")]

if __name__ == "__main__":
    from mcp.server.stdio import stdio_server
    import anyio
    async def run():
        async with stdio_server() as (read, write):
            await app.run(read, write, app.create_initialization_options())
    anyio.run(run)
