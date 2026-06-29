#!/usr/bin/env python3
"""
Kernel Engineering MCP Server

Provides structured diagnostic tools for OS kernel debugging:
subsystem questions, bug patterns, hang classification,
boot flow, invariants, and patch policy checks.

Usage:
  python server.py            # runs stdio MCP server
  python server.py --transport sse  # runs SSE server
"""

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    TextContent,
    Tool,
    Prompt,
    PromptArgument,
    GetPromptResult,
    PromptMessage,
    TextContent as PromptTextContent,
)
from typing import Any
import json
import sys
import argparse
import sqlite3
import os

# ---------------------------------------------------------------------------
# Knowledge base — extracted from kernel-engineering skill
# ---------------------------------------------------------------------------

SUBSYSTEMS = {
    "memory": {
        "name": "Memory Management",
        "includes": [
            "physical frame allocator", "virtual memory", "paging",
            "page tables", "heap allocator", "memory map parsing",
            "higher-half mapping", "kernel/user address separation",
            "copy_to_user / copy_from_user", "demand paging",
            "page fault handling",
        ],
        "questions": [
            "Is the faulting address valid?",
            "Is it virtual or physical?",
            "Is the page mapped?",
            "Is the mapping present/writable/user?",
            "Is the fault caused by instruction fetch, read, or write?",
            "Is CR3/page table root correct?",
            "Is the current process using the expected address space?",
            "Is the address in kernel space or user space?",
            "Was the mapping aligned?",
            "Was the ELF segment aligned?",
            "Did the allocator return overlapping frames?",
        ],
        "patterns": [
            ("page fault at 0x0",
             "null pointer, missing mapping, or broken loader init"),
            ("page fault near valid address",
             "partial mapping or permission issue"),
            ("random crashes after allocation",
             "frame reuse or allocator corruption"),
            ("user program faults immediately",
             "ELF mapping or stack setup bug"),
            ("kernel works until process switch",
             "address space / CR3 issue"),
            ("GUI buffer corruption",
             "framebuffer mapping or shared memory aliasing"),
        ],
    },
    "interrupts": {
        "name": "Interrupts and Exceptions",
        "includes": [
            "IDT", "exception handlers", "IRQ routing",
            "PIC/APIC", "timer interrupt", "keyboard/mouse interrupts",
            "syscall interrupt/trap", "interrupt stack",
            "TSS/IST on x86_64",
        ],
        "questions": [
            "Is the IDT loaded?",
            "Is the handler address valid?",
            "Are interrupts enabled too early?",
            "Is the stack valid when interrupt fires?",
            "Is the interrupt frame decoded correctly?",
            "Are registers saved/restored correctly?",
            "Is EOI sent to the interrupt controller?",
            "Is the timer firing?",
            "Does the fault happen only after sti?",
        ],
        "patterns": [
            ("triple fault after enabling interrupts",
             "invalid IDT, bad handler, or bad stack"),
            ("keyboard/mouse not working but timer works",
             "device IRQ path problem"),
            ("timer not working", "PIT/APIC config or interrupts disabled"),
            ("random crash after syscall",
             "register save/restore ABI mismatch"),
        ],
    },
    "scheduler": {
        "name": "Scheduler and Processes",
        "includes": [
            "task structs", "process table", "ready queue",
            "context switch", "sleeping/wakeup", "time slicing",
            "PID management", "kernel/user transition",
            "process address spaces", "syscall blocking behavior",
        ],
        "questions": [
            "Which PID is currently running?",
            "Is the timer still ticking?",
            "Is the scheduler invoked?",
            "Is the current task marked runnable/sleeping/blocked?",
            "Is wakeup happening?",
            "Is context switch saving and restoring all required registers?",
            "Is the kernel stack per-task or shared?",
            "Is userspace returning to the correct RIP/RSP?",
            "Does a blocking syscall yield correctly?",
        ],
        "patterns": [
            ("screen freezes only when PID changes",
             "scheduling, sleep/yield, or blocking syscall issue"),
            ("one process starves another",
             "no preemption or bad ready queue logic"),
            ("works until userspace starts",
             "process stack/address space/syscall boundary issue"),
            ("GUI responsive only when PID 1 runs",
             "PID 2 monopolizing CPU or blocking wakeups"),
        ],
    },
    "syscalls": {
        "name": "Syscalls and ABI",
        "includes": [
            "syscall numbers", "syscall entry path",
            "register convention", "argument passing",
            "return values", "error codes", "userspace pointers",
            "copy_to_user / copy_from_user", "blocking syscalls",
            "IPC syscalls",
        ],
        "questions": [
            "Is the syscall number correct?",
            "Are arguments read from the correct registers?",
            "Are registers preserved according to ABI?",
            "Are user pointers validated?",
            "Are error codes consistent?",
            "Does the syscall block?",
            "If it blocks, does it yield?",
            "Can the syscall be re-entered?",
            "Does the syscall assume kernel pointers?",
        ],
        "patterns": [
            ("EINVAL", "wrong channel/id/argument or validation mismatch"),
            ("EFAULT", "user pointer translation/copy problem"),
            ("syscall returns garbage",
             "register convention mismatch"),
            ("crash after syscall",
             "bad return frame or clobbered registers"),
            ("system freezes in syscall",
             "blocking path without scheduler yield"),
        ],
    },
    "elf-loader": {
        "name": "ELF Loader and Userspace Loading",
        "includes": [
            "ELF header parsing", "program headers", "PT_LOAD segments",
            "page alignment", "file offset mapping", "BSS zeroing",
            "userspace stack", "entry point",
            "dynamic/static executable handling",
            "ET_EXEC vs ET_DYN", "shared memory mappings",
        ],
        "questions": [
            "Is the ELF class/endianness/architecture correct?",
            "Are PT_LOAD segments parsed correctly?",
            "Are segment virtual addresses page-aligned before mapping?",
            "Is file offset adjusted when mapping aligned pages?",
            "Is BSS zeroed?",
            "Is entry point mapped and executable?",
            "Is userspace stack mapped?",
            "Are user permissions set?",
            "Is ET_DYN load base handled consistently?",
            "Do segments collide with reserved/kernel/shared mappings?",
        ],
        "patterns": [
            ("fault at entry",
             "entry page not mapped or wrong permissions"),
            ("fault at 0x0 after process start",
             "broken stack, broken relocation, or bad segment mapping"),
            ("works for one ELF but not another",
             "alignment or segment layout issue"),
            ("shared memory collides with ELF",
             "virtual range allocator problem"),
            ("IPC works but client crashes later",
             "userspace memory or ABI issue"),
        ],
    },
    "ipc": {
        "name": "IPC",
        "includes": [
            "channels", "message queues", "blocking receive",
            "nonblocking send", "event channels", "shared memory",
            "capability or handle validation",
        ],
        "questions": [
            "Does the channel exist?",
            "Does the sender own or have access to the channel?",
            "Does the receiver wait on the correct channel?",
            "Are channel IDs confused with shared memory IDs?",
            "Is receive blocking?",
            "If receive blocks, does scheduler yield?",
            "Are message sizes validated?",
            "Is shared memory attached at the expected virtual address?",
            "Are wakeups delivered?",
        ],
        "patterns": [
            ("send succeeds but receive returns EINVAL",
             "wrong channel, handle table, or ownership"),
            ("receive blocks forever",
             "wakeup or channel routing issue"),
            ("GUI client invisible after IPC setup",
             "Flush/Attach/Register protocol issue"),
            ("shared memory appears but content wrong",
             "mapping/permission/cache/offset issue"),
        ],
    },
    "drivers": {
        "name": "Drivers",
        "includes": [
            "PS/2 keyboard/mouse", "USB input", "framebuffer",
            "virtio devices", "disks", "serial", "timers",
            "PCI enumeration",
        ],
        "questions": [
            "Is the device detected?",
            "Is the port/MMIO address correct?",
            "Are interrupts enabled and routed?",
            "Is polling needed before IRQ mode?",
            "Are status bits checked?",
            "Is initialization order correct?",
            "Is the driver writing to physical or virtual address?",
            "Does the device require memory barriers?",
        ],
        "patterns": [
            ("input works only sometimes",
             "IRQ acknowledgment or buffer handling"),
            ("mouse coordinates wrong",
             "clamp/resolution/source mismatch"),
            ("framebuffer corrupt",
             "pitch/stride/bpp mismatch"),
            ("serial works but screen frozen",
             "GUI/render path, not whole kernel"),
        ],
    },
}

BOOT_FLOW = [
    "1. Firmware / emulator configuration",
    "2. Bootloader protocol",
    "3. Kernel binary format",
    "4. Linker script",
    "5. Entry symbol",
    "6. Stack setup",
    "7. CPU mode transition",
    "8. GDT/IDT/TSS setup",
    "9. Paging setup",
    "10. Heap/frame allocator setup",
    "11. Interrupt enable point",
    "12. First scheduler entry",
    "13. First userspace transition",
]

HANGS = {
    "visual freeze": {
        "description": "GUI stops updating, but timer/serial/scheduler may still run",
        "checks": [
            "serial logs", "timer ticks", "PID switches",
            "framebuffer present path", "compositor dirty flag",
            "input events",
        ],
    },
    "scheduler freeze": {
        "description": "Timer may tick, but runnable tasks do not progress",
        "checks": [
            "current PID", "ready queue", "sleep queue",
            "wakeups", "blocking syscalls", "interrupt return path",
        ],
    },
    "deadlock": {
        "description": "No progress due to lock or wait condition",
        "checks": [
            "spinlocks", "interrupt-disabled regions",
            "wait queues", "nested locks",
        ],
    },
    "panic": {
        "description": "Kernel intentionally stops after detecting fatal condition",
        "checks": [
            "panic message", "backtrace", "faulting subsystem",
        ],
    },
    "triple fault": {
        "description": "CPU resets due to unhandled exception or broken handler",
        "checks": [
            "IDT", "stack", "page fault handler",
            "double fault handler", "interrupt enable point",
        ],
    },
}

INVARIANTS = [
    "Kernel memory must not overlap userspace memory.",
    "Page mappings must be aligned to page boundaries.",
    "User pointers must be validated before kernel access.",
    "Interrupt handlers must preserve required registers.",
    "Blocking syscalls must yield or wake correctly.",
    "Process state transitions must be explicit.",
    "Shared memory must have clear ownership and mapping rules.",
    "Device drivers must not assume fixed resolution unless initialized.",
    "Kernel stacks must not be shared unsafely between tasks.",
    "Syscall ABI must be stable across userspace and kernel.",
]

PATCH_AVOID = [
    "large rewrites",
    "unrelated refactors",
    "style-only edits",
    "touching drivers when bug is in scheduler",
    "touching scheduler when bug is in ELF loading",
    "changing resolution/input/rendering when debugging memory or syscall bugs",
    "masking symptoms with sleeps unless timing is the actual bug",
    "adding global state without explaining lifecycle and ownership",
]

DEBUG_ORDER = [
    "Read the exact error/log",
    "Classify the failure stage",
    "Identify the subsystem",
    "Search prior project memory if available",
    "Read relevant code",
    "State the current hypothesis",
    "Add minimal instrumentation if evidence is insufficient",
    "Make the smallest patch",
    "Run the smallest relevant test",
    "Compare expected vs actual behavior",
    "Record the final root cause",
]

ARCH_TYPES = {
    "monolithic": {
        "description": "Most OS services run in kernel space",
        "useful_when": ["performance matters", "early-stage project",
                        "syscall and driver model not yet mature"],
        "risks": ["large trusted codebase", "harder isolation",
                  "bugs are more destructive"],
    },
    "microkernel": {
        "description": "Minimal kernel: scheduler, IPC, basic memory only",
        "useful_when": ["isolation matters", "service restartability",
                        "security boundaries matter"],
        "risks": ["IPC complexity", "performance overhead",
                  "harder early bootstrapping"],
    },
    "hybrid": {
        "description": "Mix of monolithic and microkernel",
        "useful_when": ["performance + modularity needed",
                        "full microkernel too complex"],
        "risks": ["design complexity tradeoffs"],
    },
    "exokernel": {
        "description": "Exposes hardware safely; user libraries implement abstractions",
        "useful_when": ["research", "specialized performance systems"],
        "risks": ["difficult design", "uncommon ecosystem",
                  "high userspace complexity"],
    },
    "unikernel": {
        "description": "App and kernel built into a single specialized image",
        "useful_when": ["cloud appliances", "embedded systems",
                        "specialized services"],
        "risks": ["weak general-purpose process model",
                  "less flexible for desktop/server OS"],
    },
}

BUILD_COMMON_MISTAKES = [
    "wrong target architecture",
    "host libc accidentally linked",
    "missing panic handler",
    "wrong linker script address",
    "wrong entry symbol",
    "non-page-aligned LOAD segments",
    "sections loaded at unexpected virtual addresses",
    "bootloader expects Multiboot/Limine/UEFI format but image does not match",
    "stack not initialized before calling Rust/C code",
]

PROJECT_RULES = {
    "key_architectural_rules": [
        "FFI Strategy: Zig hotpath FFI in build.rs. Use src/zig_ffi.rs.",
        "Resource System: Scheme-based (URL-like) resources (e.g., tcp://, pipe://).",
        "IPC: Fixed-size ring-buffer channels + shared memory.",
        "Memory: LZ4 compression tiered swap.",
        "Compositor: Orbital (Zig).",
    ],
    "directory_boundaries": {
        "src/abi/": "ABI plugins (Linux, Redox, WASM)",
        "src/scheme/": "Resource URL handlers",
        "gui/": "Orbital/Zig compositor",
        "third_party/rmm/": "Frame allocator",
    },
}

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

app = Server("kernel-engineering")
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.memory/errmem.db"))


def _init_errmem_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY,
            symptom TEXT NOT NULL,
            subsystem TEXT NOT NULL,
            root_cause TEXT,
            files_changed TEXT,
            verification TEXT
        )
    """)
    conn.close()


# --- Tools ---

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="kernel.subsystem_questions",
            description="Get diagnostic questions and common bug patterns for a kernel subsystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "subsystem": {
                        "type": "string",
                        "description": "Subsystem name: memory, interrupts, scheduler, syscalls, elf-loader, ipc, drivers",
                        "enum": list(SUBSYSTEMS.keys()),
                    }
                },
                "required": ["subsystem"],
            },
        ),
        Tool(
            name="kernel.boot_flow",
            description="Get the boot flow checklist (13 ordered steps)",
            inputSchema={
                "type": "object",
                "properties": {
                    "step": {
                        "type": "integer",
                        "description": "Optional: get details for a specific step (1-13)",
                    }
                },
            },
        ),
        Tool(
            name="kernel.diagnose",
            description="Given an error description, identify likely subsystem and provide diagnostic checklist",
            inputSchema={
                "type": "object",
                "properties": {
                    "symptom": {
                        "type": "string",
                        "description": "Error symptom description (e.g. 'page fault at 0x0', 'triple fault after sti')",
                    }
                },
                "required": ["symptom"],
            },
        ),
        Tool(
            name="kernel.hang_classify",
            description="Classify a hang or freeze type from symptom description",
            inputSchema={
                "type": "object",
                "properties": {
                    "symptom": {
                        "type": "string",
                        "description": "Hang/freeze symptom description",
                    }
                },
                "required": ["symptom"],
            },
        ),
        Tool(
            name="kernel.invariants",
            description="Get the list of kernel invariants that must be preserved",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="kernel.patch_policy",
            description="Get patch policy rules and common pitfalls to avoid",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="kernel.debug_workflow",
            description="Get the 11-step kernel debugging discipline workflow",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="kernel.architecture_types",
            description="Get kernel architecture type descriptions, tradeoffs, and risks",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Optional: filter to a specific architecture type",
                        "enum": list(ARCH_TYPES.keys()),
                    }
                },
            },
        ),
        Tool(
            name="kernel.build_mistakes",
            description="Get common kernel build mistakes checklist",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="kernel.bug_patterns",
            description="Search all subsystems for matching bug patterns by symptom keyword",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to search for in bug patterns",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="kernel.project_rules",
            description="Get ZiqaKernel-specific architectural rules and directory boundaries",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="kernel.errmem_search",
            description="Search past incident database for symptoms",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for symptoms or root cause",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="kernel.errmem_add",
            description="Record a new incident into the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "symptom": {"type": "string", "description": "Symptom description"},
                    "subsystem": {"type": "string", "description": "Subsystem"},
                    "root_cause": {"type": "string", "description": "Root cause"},
                    "files": {"type": "string", "description": "Files changed"},
                    "verification": {"type": "string", "description": "Verification method"},
                },
                "required": ["symptom", "subsystem"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    result = _dispatch_tool(name, arguments)
    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


def _dispatch_tool(name: str, args: dict[str, Any]) -> Any:
    if name == "kernel.subsystem_questions":
        sub = args["subsystem"]
        data = SUBSYSTEMS.get(sub)
        if not data:
            return {"error": f"Unknown subsystem '{sub}'. Choose: {list(SUBSYSTEMS.keys())}"}
        return {
            "subsystem": data["name"],
            "includes": data["includes"],
            "diagnostic_questions": data["questions"],
            "common_bug_patterns": [
                {"symptom": s, "likely_cause": c} for s, c in data["patterns"]
            ],
        }

    elif name == "kernel.boot_flow":
        if "step" in args:
            step = args["step"]
            if 1 <= step <= len(BOOT_FLOW):
                return {"step": step, "check": BOOT_FLOW[step - 1]}
            return {"error": f"Step must be 1-{len(BOOT_FLOW)}"}
        return {"boot_flow_checklist": BOOT_FLOW}

    elif name == "kernel.diagnose":
        symptom = args["symptom"].lower()
        matches = []
        for sub_name, data in SUBSYSTEMS.items():
            for pattern, cause in data["patterns"]:
                if pattern.lower() in symptom:
                    matches.append({
                        "subsystem": sub_name,
                        "matched_pattern": pattern,
                        "likely_cause": cause,
                        "diagnostic_questions": data["questions"],
                    })
        for hang_type, info in HANGS.items():
            if hang_type in symptom:
                matches.append({
                    "subsystem": "hang",
                    "matched_pattern": hang_type,
                    "likely_cause": info["description"],
                    "diagnostic_questions": info["checks"],
                })
        if not matches:
            return {
                "message": "No specific pattern matched. General debug workflow:",
                "debug_steps": DEBUG_ORDER,
            }
        return {"matches": matches}

    elif name == "kernel.hang_classify":
        symptom = args["symptom"].lower()
        best = None
        best_score = 0
        for hang_type, info in HANGS.items():
            keywords = hang_type.split() + [
                k for k in info["checks"]
            ]
            score = sum(1 for k in keywords if k in symptom)
            if score > best_score:
                best_score = score
                best = hang_type
        if best:
            info = HANGS[best]
            return {
                "classification": best,
                "description": info["description"],
                "checks": info["checks"],
            }
        return {
            "message": "Could not classify hang type from description. Known types:",
            "types": list(HANGS.keys()),
        }

    elif name == "kernel.invariants":
        return {"invariants": INVARIANTS}

    elif name == "kernel.patch_policy":
        return {
            "rules": [
                "Touch only files identified by evidence",
                "Change the fewest lines possible",
                "No architecture rewrites unless explicitly asked",
                "Preserve all kernel invariants",
                "Run the smallest relevant test before committing",
            ],
            "avoid": PATCH_AVOID,
        }

    elif name == "kernel.debug_workflow":
        return {
            "workflow": DEBUG_ORDER,
            "rule": "Never jump directly from symptom to patch.",
        }

    elif name == "kernel.architecture_types":
        if "type" in args:
            arch = args["type"]
            data = ARCH_TYPES.get(arch)
            if not data:
                return {"error": f"Unknown type '{arch}'. Choose: {list(ARCH_TYPES.keys())}"}
            return {arch: data}
        return ARCH_TYPES

    elif name == "kernel.build_mistakes":
        return {"common_mistakes": BUILD_COMMON_MISTAKES}

    elif name == "kernel.bug_patterns":
        query = args["query"].lower()
        results = []
        for sub_name, data in SUBSYSTEMS.items():
            for pattern, cause in data["patterns"]:
                if query in pattern.lower() or query in cause.lower():
                    results.append({
                        "subsystem": sub_name,
                        "pattern": pattern,
                        "cause": cause,
                    })
        return {"matches": results} if results else {"matches": [], "message": "No matching patterns found"}

    elif name == "kernel.project_rules":
        return PROJECT_RULES

    elif name == "kernel.errmem_search":
        query = args["query"]
        _init_errmem_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT * FROM incidents WHERE symptom LIKE ? OR root_cause LIKE ?", 
                              (f"%{query}%", f"%{query}%"))
        results = cursor.fetchall()
        conn.close()
        return {"incidents": [
            {"id": row[0], "symptom": row[1], "subsystem": row[2], "root_cause": row[3], "files": row[4], "verification": row[5]} 
            for row in results
        ]}

    elif name == "kernel.errmem_add":
        _init_errmem_db()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO incidents (symptom, subsystem, root_cause, files_changed, verification) VALUES (?, ?, ?, ?, ?)",
                     (args["symptom"], args["subsystem"], args.get("root_cause"), args.get("files"), args.get("verification")))
        conn.commit()
        conn.close()
        return {"message": "Incident recorded."}

    return {"error": f"Unknown tool: {name}"}


# --- Prompts ---

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="kernel-debug",
            description="Template for starting a kernel debugging session",
            arguments=[
                PromptArgument(
                    name="symptom",
                    description="The error symptom or observed behavior",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="kernel-patch-plan",
            description="Template for planning a kernel patch",
            arguments=[
                PromptArgument(
                    name="subsystem",
                    description="Affected subsystem",
                    required=True,
                ),
                PromptArgument(
                    name="description",
                    description="What the patch addresses",
                    required=True,
                ),
            ],
        ),
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    if name == "kernel-debug":
        symptom = (arguments or {}).get("symptom", "")
        if symptom:
            msg = f"""## Kernel Debug Session

**Symptom:** {symptom}

Follow the kernel debugging discipline:
1. Classify the failure stage (boot, memory, interrupt, scheduler, syscall, userspace)
2. Identify the subsystem
3. Read exact relevant files before patching
4. State hypothesis
5. Instrument if needed
6. Smallest patch
7. Verify

Use `kernel.diagnose` and `kernel.subsystem_questions` tools to narrow down."""
        else:
            msg = """## Kernel Debug Session

Describe the symptom you're observing, then work through the 11-step debug workflow.
Use the kernel engineering tools to get subsystem-specific checklists."""
        return GetPromptResult(
            description="Kernel debug template",
            messages=[
                PromptMessage(
                    role="user",
                    content=PromptTextContent(type="text", text=msg),
                ),
            ],
        )

    if name == "kernel-patch-plan":
        args = arguments or {}
        sub = args.get("subsystem", "")
        desc = args.get("description", "")
        msg = f"""## Kernel Patch Plan

**Subsystem:** {sub}
**Description:** {desc}

### Before patching, output:

- Failure stage:
- Evidence:
- Hypothesis:
- Files to inspect:
- Files likely to change:
- Risk:
- Smallest test:

### Patch rules:
- {PATCH_AVOID}
- Preserve invariants (use `kernel.invariants`)
- Run `kernel.patch_policy` to validate

### After patch:
- Root cause:
- Files changed:
- Why this fix:
- Verification:
- Remaining risk:"""
        return GetPromptResult(
            description="Kernel patch plan template",
            messages=[
                PromptMessage(
                    role="user",
                    content=PromptTextContent(type="text", text=msg),
                ),
            ],
        )

    return GetPromptResult(
        description="Unknown prompt",
        messages=[PromptMessage(
            role="user",
            content=PromptTextContent(type="text", text="Prompt not found."),
        )],
    )


# --- Run ---

def main():
    parser = argparse.ArgumentParser(description="Kernel Engineering MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        import uvicorn

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )

        uvicorn.run(starlette_app, host=args.host, port=args.port)
    else:
        from mcp.server.stdio import stdio_server
        import anyio

        async def run_stdio():
            async with stdio_server() as (read_stream, write_stream):
                await app.run(
                    read_stream, write_stream,
                    app.create_initialization_options(),
                )

        anyio.run(run_stdio)


if __name__ == "__main__":
    main()
