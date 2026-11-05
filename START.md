# Start and resume instructions

Setup files are installed at the repository root. Read AGENTS.md, SPEC.md, PLAN.md and PROGRESS.md, then review effective permissions and current environment readiness. Do not modify global Codex settings or grant unrestricted computer access as an implicit setup step.

Git commits require write access to the actual Git directory. If this remains blocked, report the exact missing permission and use the application's supported permission controls. An approval policy of never is not an access grant.

Check the first local commit with git log -1 --format=fuller. Use the owner's configured identity and inspect trailers. Do not publish anything. Avoid undocumented attribution settings. If configuration support is uncertain, verify it against the installed version before using it.

## Implementation Goal

Activate only when the user requests implementation. The following text is the proposed Goal objective.

Implement the local SupportOps AI release described in SPEC.md, progressing through PLAN.md autonomously. Verify operator UI flows, real local API and PostgreSQL integration, LangGraph persistence and approval, grounded policy retrieval, n8n intake/completion and the versioned evaluation suite. Prepare and validate Azure infrastructure configuration. Distinguish offline checks from credential-dependent live integrations. Follow AGENTS.md, create reviewed local commits with the owner's identity when permitted, and leave all publishing to the user. Keep PROGRESS.md current. Complete independent work before reporting any genuine external blocker. Finish only when the applicable acceptance criteria have evidence and all unmet external prerequisites are explicitly reported.

## Resume

Read AGENTS.md, SPEC.md, PLAN.md and PROGRESS.md. Inspect the working tree and current Goal status. Reconcile the recorded state with actual files and tests, then continue the next incomplete milestone within the existing authorization. A usage limit does not mean the project is complete.
