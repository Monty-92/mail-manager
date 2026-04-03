---
description: "Use when editing Markdown documentation files. Covers living document conventions, formatting rules, and maintenance requirements."
applyTo: "**/*.md"
---
# Documentation Guidelines

## Living Documents
- `PROJECT_OVERVIEW.md` is the **authoritative architecture reference** — keep it current
- `README.md` is the **quick-start guide** — keep it actionable
- When architecture changes, update both immediately

## Formatting
- Use ATX-style headers (`#`, `##`, `###`)
- Use tables for structured data (tech stacks, column definitions, command references)
- Use fenced code blocks with language identifiers
- Use relative links between project docs (e.g., `[overview](PROJECT_OVERVIEW.md)`)

## Content Rules
- Be concise — docs should be scannable, not verbose
- Include "last updated" context via meaningful section headers
- Architecture diagrams: use ASCII art or Mermaid in fenced blocks
- Command references: always show the full command, not just the tool name
