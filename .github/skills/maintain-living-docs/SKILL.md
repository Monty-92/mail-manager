---
name: maintain-living-docs
description: "Review and update living documents when architecture, services, or data model changes. Use when: adding a new service, modifying the data model, changing build commands, updating the tech stack, or after any significant refactor."
---

# Maintain Living Documents

## When to Use
- After adding, removing, or modifying a service
- After changing the database schema or data model
- After changing build/run commands or prerequisites
- After modifying the tech stack or key dependencies
- When a reviewer or teammate flags stale documentation
- Periodically after major refactors

## Procedure

### 1. Audit Current State
- Read `PROJECT_OVERVIEW.md` fully — note what sections exist
- Read `README.md` fully — note setup steps and commands
- List all services in `services/` and compare against documented services
- List all migrations in `db/migrations/` and compare against documented schema

### 2. Identify Drift
For each living document, check:

**PROJECT_OVERVIEW.md:**
- Section 3 (Technical Constraints): Does the tech table match actual dependencies?
- Section 4 (Architecture): Are all services listed? Are descriptions accurate?
- Section 5 (Data Model): Do table schemas match the latest migration?
- Section 8 (Repository Structure): Does the tree match actual layout?

**README.md:**
- Are prerequisites current?
- Do quick-start commands actually work?
- Are environment variable examples complete?

### 3. Apply Updates
- Update each stale section directly — do not just flag it
- Preserve the existing document structure and formatting conventions
- Add new sections only if new architectural components warrant them
- Update ASCII diagrams if service topology changed

### 4. Verify
- Ensure internal links between documents still resolve
- Confirm no contradictions between PROJECT_OVERVIEW.md and README.md
- Verify command examples are copy-pasteable and correct
