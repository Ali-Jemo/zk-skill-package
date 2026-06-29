# YOU OS / ZiqaKernel Agent Accelerator

Comprehensive agentic toolkit for Rust `no_std` kernel development. Provides diagnostic skills, slash commands, and an MCP server for structured reasoning and database-backed incident tracking.

## Installation (Recommended)

Run this in your kernel project root to automatically set up all skills, commands, and MCP rules:

```bash
npx zk-skill-package
```

*This requires Node.js installed.*

## Manual Installation (Alternative)

If you prefer to clone and install manually:

```bash
# Clone
git clone https://github.com/Ali-Jemo/zk-skill-package .agents-temp
# Run setup script
chmod +x .agents-temp/scripts/install-zk-agent.sh
./.agents-temp/scripts/install-zk-agent.sh
rm -rf .agents-temp
```

## Features

- **Slash Commands**: `/zk`, `/zk-fix`, `/zk-plan`, `/zk-review`, `/zk-elf`, `/zk-sched`, `/zk-gui`, `/zk-mem`, `/zk-ipc`, `/zk-input`, `/zk-driver`.
- **Master Skill**: `you-os-kernel-accelerator` provides a comprehensive diagnostic framework, Ponytail policy, and Rust kernel discipline.
- **MCP Server**: Real tools for kernel diagnosis (`kernel.diagnose`, `kernel.analyze_serial`), incident tracking (`kernel.errmem_search/add`), architectural lookups (`kernel.project_rules`), and knowledge graph queries (`kernel.graph_query`).
- **Rust Kernel Skill**: `rust-kernel-development` integrates `no_std`, `unsafe` invariants, and bare-metal Rust discipline.

## MCP Server Setup

Add this to your agent's MCP configuration (e.g., `~/.claude/mcp.json` or `.mcp.json`):

```json
{
  "mcpServers": {
    "kernel-engineering": {
      "command": "/path/to/project/.agents/mcp-server/run-mcp.sh",
      "args": [],
      "env": {}
    }
  }
}
```

## Usage

### Slash Commands
Once installed, use slash commands directly:
```
/zk-fix "your bug symptom"
/zk-sched "describe scheduler issue"
```

## License

MIT
