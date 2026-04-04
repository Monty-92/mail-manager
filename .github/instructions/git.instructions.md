---
description: "Use when performing git operations: committing, branching, pushing, creating pull requests, merging, or managing version control workflow. Covers Conventional Commits, branch naming, PR creation, rebase-and-merge strategy, and agent commit prompting."
---

# Git Workflow

## Branch Strategy

All work happens on feature branches. **Never commit directly to `main`.**

### Branch Naming

Format: `type/short-description` (lowercase, hyphen-separated)

| Prefix | Use |
|--------|-----|
| `feat/` | New features or capabilities |
| `fix/` | Bug fixes |
| `refactor/` | Code restructuring without behavior change |
| `chore/` | Tooling, config, dependencies |
| `docs/` | Documentation-only changes |
| `test/` | Test additions or fixes |
| `ci/` | CI/CD pipeline changes |

Examples: `feat/add-preprocessing-service`, `fix/oauth-token-refresh`, `docs/update-api-reference`, `chore/upgrade-fastapi`

### Branch Lifecycle

1. Create from latest `main`: `git checkout main && git pull && git checkout -b type/description`
2. Make atomic commits on the branch (see Commit Discipline below)
3. Push branch: `git push -u origin type/description`
4. Open a pull request (see PR Workflow below)
5. After merge, delete the branch: `git branch -d type/description`

## Conventional Commits

All commit messages **must** use [Conventional Commits](https://www.conventionalcommits.org/) format.

### Format

```
type(scope): subject

[optional body]

[optional footer]
```

- **type**: required — one of the prefixes below
- **scope**: optional — the service or area affected (e.g., `ingestion`, `frontend`, `db`)
- **subject**: required — imperative mood, lowercase, no trailing period, max ~72 chars
- **body**: optional — explain *what* and *why*, not *how*. Wrap at 72 chars.
- **footer**: optional — `BREAKING CHANGE:` or issue references (`Closes #42`)

### Prefixes

| Prefix | When to Use | Example |
|--------|-------------|---------|
| `feat` | New feature or capability | `feat(ingestion): add Outlook delta sync` |
| `fix` | Bug fix | `fix(router): handle expired OAuth tokens` |
| `docs` | Documentation only | `docs: update README prerequisites` |
| `refactor` | Code change with no feature/fix | `refactor(preprocessing): extract embedding logic` |
| `test` | Adding or fixing tests | `test(ingestion): add converter edge cases` |
| `chore` | Tooling, deps, config, maintenance | `chore: upgrade fastapi to 0.115` |
| `style` | Formatting, whitespace (no logic) | `style: run ruff format on all services` |
| `build` | Build system or dependencies | `build(docker): optimize multi-stage Dockerfile` |
| `perf` | Performance improvement | `perf(embedding): batch Ollama requests` |
| `ci` | CI/CD configuration | `ci: add GitHub Actions test workflow` |

### Commit Discipline

- **Atomic commits**: one logical change per commit. Don't mix a feature with a refactor.
- **Imperative mood**: "add feature" not "added feature" or "adds feature"
- **Test with the code**: if a feature needs new tests, include them in the same commit
- **No broken commits**: every commit should leave the codebase in a working state

## Pull Request Workflow

**All changes reach `main` through pull requests. No exceptions.**

### Creating a PR

Use the GitHub CLI (`gh`) or available GitHub MCP/extension tools:

```bash
gh pr create --title "feat(ingestion): add Outlook delta sync" --body "..."
```

The PR title **must** follow Conventional Commits format (it becomes the merge commit on `main`).

### PR Description Structure

```markdown
## Summary
Brief description of what this PR does and why.

## Changes
- Bullet list of specific changes made
- Group by file or logical area if many changes

## Testing
- How the changes were tested
- Which test suites were run and their results

## Checklist
- [ ] Tests pass (`uv run pytest` / `npm run lint`)
- [ ] No secrets or `.env` files included
- [ ] Living docs updated (if architecture/data model changed)
- [ ] Commit messages follow Conventional Commits
```

### Merging

- **Rebase and merge only** — maintains linear history on `main`, no merge commits
- Before merging, ensure the branch is rebased on latest `main`:
  ```bash
  git fetch origin && git rebase origin/main
  ```
- Merge via: `gh pr merge --rebase --delete-branch`
- After merge, clean up local branch: `git checkout main && git pull && git branch -d type/description`

## Agent Prompting Behavior

The agent should **proactively prompt the user** to commit and push at these natural breakpoints:

1. **After completing a feature or fix** — all code written, tests passing
2. **After completing a plan phase** — e.g., finishing "Phase C2: Preprocessing Service"
3. **Before switching to a different area of work** — e.g., moving from backend to frontend
4. **After passing test verification** — tests green = safe commit point
5. **When a logical unit of work is done** — even mid-phase (e.g., "repository layer complete")
6. **Before making risky or experimental changes** — commit stable state first

### Prompt Format

When prompting, the agent should suggest:
- The branch name (if not yet created)
- The commit message(s) with proper Conventional Commits format
- Whether to push and/or create a PR

### Workflow Integration with Plans

When the agent creates a multi-phase plan, it should:
- Include "commit and push" steps at the end of each phase
- Include "create PR" as the final step when the feature branch is complete
- Factor branch creation into the first step of each new feature/phase
- Note which phases can share a branch vs. which need separate PRs

## Pre-Commit Checklist

Before every commit, verify:
1. **Tests pass**: `uv run pytest` for affected services, `npm run lint` for frontend
2. **Linter clean**: `uv run ruff check .` for affected Python services
3. **No secrets**: no `.env`, API keys, or tokens in staged files
4. **No unintended files**: review `git diff --staged --name-only`
5. **Commit message format**: matches Conventional Commits spec
