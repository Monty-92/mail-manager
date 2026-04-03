---
name: maintain-copilot-config
description: "Review and update GitHub Copilot customization files when conventions, architecture, or tech stack changes. Use when: changing coding standards, adding new file types, modifying service patterns, or after significant refactors."
---

# Maintain Copilot Configuration

## When to Use
- After changing the tech stack or key dependencies
- After modifying coding standards or conventions
- After adding new file patterns that need instructions
- After changing service communication patterns
- When Copilot suggestions seem misaligned with current practices
- Periodically after major refactors

## Files to Review

| File | Purpose | Update When |
|------|---------|-------------|
| `.github/copilot-instructions.md` | Workspace-wide context | Tech stack, architecture, or conventions change |
| `.github/instructions/python.instructions.md` | Python coding rules | Python patterns, deps, or tooling change |
| `.github/instructions/vue.instructions.md` | Frontend coding rules | Frontend framework, tooling, or patterns change |
| `.github/instructions/docker.instructions.md` | Docker conventions | Docker setup, base images, or build patterns change |
| `.github/instructions/sql.instructions.md` | SQL/migration rules | DB schema patterns or pgvector usage changes |
| `.github/instructions/docs.instructions.md` | Documentation rules | Doc structure or formatting conventions change |
| `.github/skills/*/SKILL.md` | On-demand workflows | Workflow steps or tooling changes |
| `.github/agents/*.agent.md` | Custom agent definitions | Agent roles or tool needs change |

## Procedure

### 1. Read All Config Files
- Read every file listed above
- Note the current state of each

### 2. Compare Against Codebase
- Check if documented tech stack matches `pyproject.toml` files and `package.json`
- Check if documented patterns match actual code in `services/` and `frontend/`
- Check if `applyTo` globs still match the actual file structure
- Check if skill procedures reference correct paths and commands

### 3. Apply Updates
- Update stale content directly
- Add new instructions files if new file patterns have emerged
- Remove or archive instructions for deprecated patterns
- Ensure `description` fields are keyword-rich for discovery

### 4. Verify
- Confirm no contradictions between workspace instructions and file-specific instructions
- Ensure skill names match their folder names
- Verify agent tool lists are minimal and appropriate
