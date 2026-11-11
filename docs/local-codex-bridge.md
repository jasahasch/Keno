# Supervised local Codex bridge

This bridge retrieves explicitly owner-approved GitHub issues from `jasahasch/Keno` and runs one assignment at a time in a disposable public-source Git worktree. It never opens, scans, migrates, resets, or reconciles the permanent research workspace. Issue #1 is the initial assignment; mapping the actual SynFart directory remains a separate local verification step, not an inferred success.

The latest owner directive governs this implementation. Read the root README, applicable `AGENTS.md`, `multi_keno/README.md`, `docs/workspace.md`, `docs/publication.md`, `docs/mathematics.md`, and framework governance/architecture before executing work. Historical governance statements about the absence of Git describe an older research delivery, not the current public repository. The preservation rules and mathematical evidence boundaries remain in force. No applicable `AGENTS.md` was found during implementation.

## Requirements and trust boundary

Linux, Python 3.10+, Git, GitHub CLI (`gh`), Bubblewrap (`bwrap`) with functioning unprivileged namespaces, and a Linux Codex CLI binary supporting `exec --ignore-user-config --ignore-rules --ephemeral` are required. Run as an ordinary user, never root. The implementation is standard-library Python.

Authenticate the trusted host's GitHub CLI with the owner account and authenticate the host Codex CLI (`codex login`) or configure `OPENAI_API_KEY` locally through your normal credential manager. Do not put credentials into an issue, source file, command history, or this document. `gh auth status` must succeed. The gateway reads API-key or existing ChatGPT OAuth credentials on the trusted host; `auth.json` is never exposed to the agent. OAuth refresh is not automated: renew an expired login locally. API usage may incur charges.

The owner trusts the bridge source, host OS and installed executables. GitHub issues and model-generated commands are untrusted. Approval does not make their content safe to execute on the host. The agent receives only public-source files, a disposable home and temporary directory, and read-only system binaries/libraries. Its Git metadata is masked, public historical `outputs/` are mounted read-only, and project `.codex` configuration is masked. Private home directories, local research, original `.git`, GitHub tokens, bridge state and backups are not mounted. Codex authentication files and API keys are not mounted either.

Bubblewrap creates filesystem, process, IPC and network namespaces with dropped capabilities. There is no host network access, including localhost services. Inside the namespace a loopback relay forwards to a Unix socket served by the trusted host gateway. That gateway accepts only POST `/v1/responses`, sends requests to the fixed `https://api.openai.com/v1/responses` endpoint (API key) or `https://chatgpt.com/backend-api/codex/responses` endpoint (existing Codex OAuth), and holds the API key outside the sandbox. Redirects are refused. No arbitrary CONNECT, GitHub, tool download, credential forwarding or private-network requests are supported. Dependency installation and MCP integrations are deliberately unavailable to an assignment.

This is a defense against accidental or model-induced access to private research, not a defense against a compromised kernel or another malicious process already running as the same OS user. The source-only clone must itself be public-safe: no symlinks, submodules, database or credential-looking tracked paths. Source publication also rejects changes to historical outputs, hidden configuration, database/backup paths, binary files, oversized files and common secret indicators. A human still reviews every source diff; pattern scanning cannot prove absence of secrets.

## Install without changing the permanent workspace

Use a separate clone or a reviewed checkout of this PR. Do not clone over the live research directory. Once merged, an example separate checkout is:

```bash
git clone https://github.com/jasahasch/Keno.git "$HOME/keno-bridge-source"
cd "$HOME/keno-bridge-source"
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest -v tools.keno_bridge.test_bridge
gh auth status
python3 -m tools.keno_bridge.bridge inspect --issue 1
```

If the path already exists, inspect it first; do not overwrite it or reset it. Until merged, clone and select the reviewed PR branch instead. The bridge's default private state directory is `$HOME/.local/state/keno-bridge`, created with mode 0700 and a repository identity marker. Existing nonempty unrelated directories and paths inside Git checkouts are refused; never use a research directory as bridge state. Logs and assignment snapshots may contain sensitive model text: keep this directory private and out of Git. The same state directory must be used for all invocations on this host; choosing a different directory defeats the local duplicate ledger. There is no distributed multi-host execution claim.

## Approval and supervised execution

`inspect` retrieves the open issue and all comments and prints its current title, body, assignment digest and approval comment ID. Read these before authorizing a run. For new assignments, the repository owner must post exactly:

```text
/keno approve ASSIGNMENT_SHA256
```

The digest binds repository, issue number, title and body. Quoted approvals, other authors, label-only approval, closed issues and pull requests do not qualify. Editing the title/body requires new approval. Issue #1 alone also accepts the existing owner approval comment `6784188375`; this narrowly scoped compatibility exception still requires the supervisor to approve the exact current digest at the terminal. Comments other than the selected approval are not executed or added to the assignment prompt.

Set `assignment_sha` to the digest printed by `inspect`. The exact smoke command, from the separate source checkout, is:

```bash
python3 -m tools.keno_bridge.bridge run --issue 1 --approve "$assignment_sha" --smoke --timeout 300
```

Use `--codex-bin /absolute/path/to/codex` if automatic lookup resolves to a wrapper rather than the real Linux ELF executable. The bridge refuses an unavailable or failing sandbox. It does not retry with weaker permissions. A completed smoke requires Codex to return successfully, the trusted deterministic Record A/core-regression/synthetic checker to pass, and no source-file changes. The checker uses a temporary SQLite database, independently replays all 595 layouts under each objective, and checks integrity and foreign keys.

The real assignment command (after the smoke succeeds and the supervisor reviews the assignment again) is:

```bash
python3 -m tools.keno_bridge.bridge run --issue 1 --approve "$assignment_sha" --timeout 900
```

A single assignment revision has one durable reservation, including after failure, timeout, interruption or smoke. Therefore a smoke consumes that revision's reservation: inspect the smoke evidence, then use a newly owner-approved issue revision for actual implementation. There is deliberately no automatic retry/reset switch. Do not delete state to force a rerun. A recovery or repeat requires an explicit new assignment revision and renewed approval, or manual forensic recovery outside this bridge.

Unattended polling is not implemented. There is no cron, systemd timer, issue webhook execution or autonomous merge command. Do not add unattended scheduling until actual SynFart namespace isolation, Codex connectivity, timeout handling and preservation controls have passed local tests.

## Reports, source review and PRs

Each run retains a private `report.json`, assignment snapshot, baseline content hashes, worktree and bounded local logs. A SQLite primary key and exclusive process lock prevent duplicate/concurrent execution in the chosen state directory. Kernel locks release on crashes; an unfinished ledger entry still blocks execution. Timeouts kill the process group; the agent's private PID namespace constrains descendants. Codex output is limited by a 16 MiB file-size limit. Never treat an exit-zero agent response as a mathematical proof: examine the actual logs, tests and deterministic smoke result.

The trusted orchestrator automatically posts only fixed-format status metadata to the originating issue. Raw logs, model-authored summaries, assignment text, local paths, source diffs and secrets are not automatically posted. API failures leave a durable report. Retry reporting only, without rerunning execution:

```bash
python3 -m tools.keno_bridge.bridge report --run RUN_KEY
```

A marker prevents duplicate result comments after a crash between remote acceptance and local acknowledgement. Reporting requires access to the original still-open issue. If it is closed, preserve the local report and handle the communication manually.

For source changes, inspect the private worktree diff, every new file, test output and `report.json`. The trusted publisher compares literal file hashes rather than accepting an agent-controlled Git index. The report contains a `review_sha256` binding the exact changed contents and deletions. Once reviewed, explicitly publish that revision:

```bash
python3 -m tools.keno_bridge.bridge publish --run RUN_KEY --review REVIEW_SHA256
```

Only this separate command stages the approved source paths, commits, pushes a new branch without force, and creates a draft PR. It checks that the issue and approval remain current. It posts the PR URL to the issue. It never merges, closes the issue, rewrites the permanent workspace or pushes to `main`. If publication is interrupted, the ledger remains `publishing`: inspect GitHub and the retained branch manually; never rerun Codex to repair a publishing failure.

Review source with `git -C WORKTREE diff` and open each listed untracked file. No arbitrary shell command is constructed from issue text. The publisher disables Git hooks/fsmonitor, uses a new source clone and gives the agent no GitHub credentials. Publication on SynFart requires a working host `gh` account with write access. Installation of the bridge alone does not prove an issue triggered Codex.

## Implementation validation and remaining local checks

The automated suite exercises approved/unapproved revisions, owner identity, the legacy approval boundary, concurrent/durable duplicate prevention, timeout killing, report retry/recovery, source-review digests, draft PR publication, forbidden research/evidence/secret changes, sandbox arguments, API gateway destination restrictions, and a simulated end-to-end run. Test doubles for Codex and GitHub are explicitly simulations; they do not establish live agent execution.

The deterministic source smoke can also run independently from the separate public-source checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/keno_bridge/smoke.py
```

This Cloud implementation session cannot access SynFart or verify the live permanent directory. Its initial in-tool Bubblewrap probe failed; a separately approved outside-tool probe succeeded, including actual filesystem/network isolation and deterministic Keno smoke verification. Its terminal GitHub token was invalid. The connected GitHub tool can retrieve Issue #1 and post results/create PRs, but is distinct from the host `gh` authentication used by the shipped bridge. A successful live GitHub-to-local-Codex end-to-end run is not claimed until the exact supervised command succeeds on SynFart. No private historical regression fixtures were available; source-only checks do not restore research data or close Issue #1's permanent-workspace acceptance criteria.
