---
status: pending
priority: p3
issue_id: "018"
tags: [distribution, mcp, integration, phase-2]
dependencies: ["015"]
---

# Build MCP Server for Brand Compliance Checking

## Problem Statement

MCP (Model Context Protocol) enables integration with any AI platform. An MCP server for brand compliance checking would allow AI assistants to invoke Brand Arbiter as a tool, enabling automated compliance workflows across platforms.

## Acceptance Criteria

- [ ] MCP server exposes `scan_asset` tool (image + rules → compliance report)
- [ ] Compatible with Claude Code, Cursor, and other MCP-supporting platforms
- [ ] Published to MCP registries (Smithery, mcp.so, PulseMCP)
- [ ] Documentation for setup and integration

## Notes

- Third in distribution priority (CLI → Skill → MCP)
- Build after product-market fit is confirmed through CLI and Skill usage
- Depends on TODO-015 (CLI) — the MCP server wraps the same engine
