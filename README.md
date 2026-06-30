# YOU OS / ZiqaKernel Agent Accelerator

Comprehensive toolkit for Rust `no_std` kernel development, diagnostic skills, and integrated MCP server for structured reasoning.

## 1. Quick Start & Auto-Update

Run this in your kernel project root to automatically install or **update** to the latest version of all skills, commands, and MCP rules:

```bash
npx zk-skill-package@latest
```

*This ensures you always have the latest improvements without manual intervention.*

*This requires Node.js installed.*

## 2. MCP Server Configuration & Usage

The MCP server provides real-time tools for kernel engineering.

### Configuration
Add the following to your agent's MCP configuration (e.g., `~/.claude/mcp.json` or `.mcp.json`):

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

### Usage Example
Audit a subsystem for unsafe blocks using the `kernel.security_audit` tool:
```
/mcp call kernel.security_audit '{"subsystem": "memory"}'
```

## Features

- **Master Skill**: `you-os-kernel-accelerator` provides diagnostic framework, Ponytail policy, and Rust kernel discipline.
- **MCP Server Tools**:
  - **Diagnosis**: `kernel.diagnose`, `kernel.analyze_serial`
  - **Incident Tracking**: `kernel.errmem_search/add`
  - **Security Auditing**: `kernel.security_audit`, `kernel.invariant_check`, `kernel.patch_policy`
  - **Architecture**: `kernel.project_rules`, `kernel.graph_query`
- **Slash Commands**: `/zk`, `/zk-fix`, `/zk-plan`, `/zk-review`, `/zk-elf`, `/zk-sched`, `/zk-gui`, `/zk-mem`, `/zk-ipc`, `/zk-input`, `/zk-driver`.

## Troubleshooting

- **Server not connecting?** Ensure the `command` path in `mcp.json` is absolute and the script is executable (`chmod +x run-mcp.sh`).
- **Tools not appearing?** Verify the MCP server script correctly outputs the JSON-RPC tool list when run directly.

## Manual Installation (Alternative)

If you prefer to clone and install manually:

```bash
# Clone and install
git clone https://github.com/Ali-Jemo/zk-skill-package .agents-temp
chmod +x .agents-temp/scripts/install-zk-agent.sh
./.agents-temp/scripts/install-zk-agent.sh
rm -rf .agents-temp
```

## License

MIT
