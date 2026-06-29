# YOU OS / ZiqaKernel Agent Accelerator

Agent-agnostic skill + slash-command + MCP package for Rust `no_std` kernel work.

Compatible with: Claude Code, OpenCode, Kilo Code, Kiro-style agents, Codex, Gemini CLI, Cursor, Windsurf, and any MCP-capable client.

## What This Provides

```text
AGENTS.md                         always-on repo rules
.agents/skills/you-os-kernel-accelerator/  master workflow skill
.agents/skills/rust-kernel-development/    Rust no_std kernel discipline
.agents/skills/you-os-*-debug/             subsystem triage skills
.agents/mcp-server/                        MCP tools: diagnose, errmem, project rules
.opencode/commands/zk*.md                  OpenCode slash commands
.kilo/commands/zk*.md                      Kilo workflows
.claude/skills/zk*/SKILL.md                Claude slash commands
```

## Slash Commands

Use these instead of typing a long prompt every time:

```text
/zk         master router
/zk-fix     Ponytail bugfix workflow
/zk-plan    safe planning workflow
/zk-review  kernel patch review
/zk-elf     ELF/userspace loading
/zk-sched   scheduler/PID/sleep/yield
/zk-gui     GUI/framebuffer/compositor
/zk-mem     paging/page fault/allocator/SHM
/zk-ipc     IPC/SHM/event/Flush
/zk-input   keyboard/mouse/HID/cursor/input routing
/zk-driver  PCI/VirtIO/MMIO/IRQ/DMA/device init
```

## Install / Refresh

```bash
./scripts/install-zk-agent.sh
```

The script creates/refreshes AGENTS.md, OpenCode commands, Kilo commands, and Claude skill commands.

## MCP Server

Install deps once:

```bash
.agents/mcp-server/setup.sh
```

Project MCP config:

```json
{
  "mcpServers": {
    "kernel-engineering": {
      "command": "/home/jemo/Projects/my-os-reorganized/.agents/mcp-server/run-mcp.sh",
      "args": [],
      "env": {}
    }
  }
}
```

MCP tools include:

```text
kernel.diagnose
kernel.boot_flow
kernel.subsystem_questions
kernel.bug_patterns
kernel.hang_classify
kernel.invariants
kernel.patch_policy
kernel.debug_workflow
kernel.architecture_types
kernel.build_mistakes
kernel.project_rules
kernel.errmem_search
kernel.errmem_add
```

## Rust Kernel Policy

Use `rust-kernel-development` with `rust-development`:

- `rust-development`: general Rust, ownership, lifetimes, cargo, clippy, idioms.
- `rust-kernel-development`: `no_std`, `alloc`, panic handler, unsafe invariants, atomics, MMIO, interrupts, inline asm, FFI, bootimage.

## Publish

Commit the package files:

```bash
git add AGENTS.md .agents .opencode/commands .kilo/commands .claude/skills/zk* scripts/install-zk-agent.sh mcp.json
git commit -m "add YOU OS kernel agent accelerator"
```

Consumers can copy `.agents/`, `.opencode/commands`, `.kilo/commands`, `.claude/skills/zk*`, `AGENTS.md`, `mcp.json`, and `scripts/install-zk-agent.sh` into their kernel repo.
