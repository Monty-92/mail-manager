---
description: "Stabilize the current repo state (resolve conflicts, merge branches, fix builds) then produce a comprehensive completion plan without implementing it. Use when: resuming stalled work, onboarding to a messy repo, or checkpoint-planning after a break."
argument-hint: "Optional: describe the target end-state or feature goal"
agent: agent
---

# Stabilize & Plan

You have two sequential objectives. Complete **Phase 1** fully before starting **Phase 2**.

---

## Phase 1 — Stabilize Current State

Bring the repository to a clean, healthy baseline. Work through each step in order; skip any that are already satisfied.

### 1. Git Hygiene

1. Run `git status` and `git stash list` to understand the working tree.
2. If there are uncommitted changes, assess whether they are intentional work-in-progress or leftover debris:
   - **WIP worth keeping** → stage and commit on the current branch with a proper Conventional Commit message.
   - **Debris / experiments** → stash or discard (confirm with me before discarding).
3. Identify the current branch and its relationship to the default branch (`main` / `master`):
   - `git log --oneline HEAD..origin/main` — are there upstream commits to incorporate?
   - `git log --oneline origin/main..HEAD` — are there local commits not yet merged?
4. If the current branch is behind the default branch, **rebase** (not merge) onto the latest default branch:
   ```
   git fetch origin
   git rebase origin/<default-branch>
   ```
   Resolve any conflicts interactively — explain each conflict and your resolution rationale before proceeding.
5. Check for other open local or remote feature branches (`git branch -a`). For each:
   - Determine if it contains work that should be merged before planning.
   - If yes, integrate it via rebase onto the current branch or the default branch as appropriate.
   - If it is stale / abandoned, flag it for my review — do not delete without confirmation.

### 2. Dependency & Build Health

1. Install / sync dependencies (detect the package manager from lock files: `uv.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Pipfile.lock`, `go.sum`, etc.).
2. Run the project's build or compile step. Fix any build errors.
3. If the project uses Docker / Docker Compose, verify containers come up healthy (`docker compose ps` or equivalent). Fix Dockerfile or compose issues as needed.
4. Run database migrations if a migration system is detected and the DB is available.

### 3. Test & Lint Baseline

1. Run the full test suite. Record which tests pass, fail, or error.
2. Run linters / formatters. Auto-fix what the tooling allows.
3. Fix any **pre-existing** test failures or lint errors that are clearly broken (missing imports, syntax errors, stale mocks). Do **not** refactor or improve passing code.
4. If some failures require deeper work, document them as known issues for Phase 2 rather than blocking stabilization.

### 4. Commit the Stable State

1. Stage and commit all stabilization changes with clear Conventional Commit messages (e.g., `fix(build): resolve rebase conflicts`, `chore(deps): sync lock files`).
2. Push the branch: `git push -u origin <branch>`.
3. Confirm the repo is now in a **green, pushable state**: clean working tree, tests passing (or known failures documented), build succeeding.

**Stop and summarize what you did in Phase 1 before continuing.** Include:
- Branches merged or rebased
- Conflicts resolved (and how)
- Build / test issues fixed
- Known issues deferred to the plan

---

## Phase 2 — Comprehensive Completion Plan

Now produce a detailed, actionable plan that takes the project from its current stabilized state to **completion**. If I provided a target end-state above, plan toward that. Otherwise, infer the intended end-state from project docs (`README`, `PROJECT_OVERVIEW`, `PLAN`, `TODO`, open issues/PRs, and incomplete features in code).

### Plan Requirements

1. **Discover scope**: Read project documentation, open issues/PRs, TODO/FIXME comments, and incomplete features to understand what "done" looks like.
2. **Organize into phases**: Group work into logical, sequential phases (e.g., `Phase 1: Core API`, `Phase 2: Frontend Integration`). Each phase should be independently shippable or at least independently testable.
3. **For each phase, specify**:
   - **Objective**: one-sentence summary of what this phase achieves.
   - **Tasks**: numbered list of concrete implementation tasks (file-level granularity where possible).
   - **Testing**: what tests to write or run to verify the phase.
   - **Git checkpoint**: the branch name, commit convention, and whether a PR should be opened at the end of the phase.
   - **Dependencies**: which phases or external factors must be complete first.
   - **Estimated complexity**: Low / Medium / High — to help with prioritization.
4. **Known risks & open questions**: List anything ambiguous, blocked, or requiring a decision from me.
5. **Out of scope**: Explicitly note anything you considered but excluded, and why.

### Plan Format

Present the plan as structured Markdown with clear headings, numbered tasks, and a phase dependency graph (ASCII or Mermaid). The plan should be copy-pasteable into a project doc.

### Constraints

- **Do NOT implement any part of the plan.** Planning only.
- **Do NOT refactor or improve code** that is already working — save that for a plan phase if warranted.
- Respect existing project conventions (commit style, branch naming, test patterns, directory structure).
- If the project has a living planning document (e.g., `PLAN.md`, `TODO.md`), reconcile your plan with it — call out discrepancies.
