# YOU OS / ZiqaKernel Agent Accelerator

This repository provides a complete agentic toolkit for YOU OS / ZiqaKernel kernel development. It includes slash commands for major agentic CLIs, a kernel-engineering skill package, and an MCP server for structured diagnostics.

## Features

- **Slash Commands**: `/zk`, `/zk-fix`, `/zk-plan`, `/zk-review`, `/zk-elf`, `/zk-sched`, `/zk-gui`, `/zk-mem`, `/zk-ipc`, `/zk-input`, `/zk-driver`.
- **Master Skill**: `you-os-kernel-accelerator` provides a comprehensive diagnostic framework.
- **MCP Server**: Real tools for kernel diagnosis, boot flow checks, and error memory tracking.
- **Project Rules**: `you-os-project-rules` and `AGENTS.md` for team discipline.
- **Ponytail Patching**: Automated minimal-change development policy.

## Installation

Run the installation script in your kernel project root:

```bash
chmod +x scripts/install-zk-agent.sh
./scripts/install-zk-agent.sh
```

This will set up `AGENTS.md`, slash commands in `.opencode/` and `.kilo/`, and skills in `.claude/`.

## MCP Server Setup

1. Install dependencies:
   ```bash
   .agents/mcp-server/setup.sh
   ```
2. Add to your agent's MCP configuration:

```json
{
  "mcpServers": {
    "kernel-engineering": {
      "command": "/path/to/repo/.agents/mcp-server/run-mcp.sh",
      "args": [],
      "env": {}
    }
  }
}
```

## Usage

### Slash Commands
Once installed, use slash commands directly in your agent interface:
```
/zk-fix "your bug symptom here"
/zk-sched "describe scheduler issue"
```

### Skill Tools
If you use an MCP-capable client, you have access to specialized kernel tools:
- `kernel.diagnose`: Symptom analysis
- `kernel.boot_flow`: Boot troubleshooting
- `kernel.errmem_search`: Search incident history

## License

MIT
