# SupportOps AI working agreements

## Start and resume

Read SPEC.md, PLAN.md and PROGRESS.md before implementation. Treat these files as the project contract. Preserve user changes. Check the repository status before edits and commits. Use official documentation for current library interfaces.

## Autonomous execution

Implement the next incomplete milestone, run relevant checks, fix failures, review the diff, record evidence and continue. Make routine reversible decisions independently. Record meaningful assumptions in PROGRESS.md. Keep scope within SPEC.md.

The user authorizes subordinate agents for independent implementation and review. The main agent coordinates their work, assigns distinct ownership and integrates results. Only the main agent creates commits. Keep the user in one main chat.

Use a persistent Goal when the user activates implementation. Completion requires the evidence in SPEC.md. A successful scaffold or exhausted budget does not constitute completion. If blocked, complete independent work and report the exact prerequisite. Never evade execution permissions.

## Git

The user owns publishing. Never push, open PRs, publish releases or change remote configuration. Never rewrite existing history or discard user changes.

Create small local commits for validated milestones when Git write access is available. Use the existing user identity, expected to be Petr Semiguk <semiguksg@gmail.com>. Check both author and committer. Do not invent an identity or add AI co-author trailers. Inspect commit metadata after committing. If installed tooling forces attribution, report that configuration issue before further commits rather than silently rewriting history.

Stage explicit project paths after inspecting the diff. Never commit secrets, downloaded datasets, environments, logs or credentials. If commits are blocked, preserve working files and record pending commits. Do not claim they exist.

## Checks and evidence

For behavior changes run focused tests, then required build/lint/type checks. Add tests for business rules, authorization, idempotency, retries and checkpoint recovery. Exercise the real UI/API path for completed user flows. Keep test doubles and live integration results explicitly distinguished.

Do not weaken assertions or change acceptance criteria solely to make tests pass. Commit only coherent changes. Record command, result and unresolved limitations in PROGRESS.md after each milestone.

## Permissions and expenses

Local implementation, project dependencies, tests and container configuration are authorized within available permissions. Store secrets outside tracked files. Never print credentials.

Prepare Azure infrastructure as code and deployment instructions. Paid resource creation, deployment and billable LLM calls require separately supplied credentials and an explicit budget authorization. Continue local work with clearly labeled test adapters while these prerequisites are missing.

Do not send real customer messages. Use demo channels and simulated shop actions. Keep raw external data isolated and preserve dataset attribution and license records.

## Communication

Use Russian for user updates and clear English names in code. Report meaningful progress and blockers concisely. At interruption or limits, leave the next executable step and exact verification status in PROGRESS.md.
