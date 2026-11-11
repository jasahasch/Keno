# Source publication checklist

[publication-files.txt](../publication-files.txt) is the release allowlist. The root ignore file mirrors it. The [builder](../tools/build_publication.py) packages only those paths, checks them for common secret and private-path indicators, and emits a manifest with SHA-256 hashes. The allowlist excludes databases, snapshots, search logs, backup deltas, caches, temporary files and private configuration. Ignoring files does not untrack them in an existing checkout. Review the staged path list and any existing Git history before a first push.

```bash
python3 tools/build_publication.py /tmp/keno-source.zip
```

The archive is the review candidate. Its generic fixture, Record A verification and Phase 4 ledger check work without private research databases. This is a source release. The legacy worker requires an existing research workspace to resume historical runs. The Cleopatra proposal remains unverified.

Before publishing, select the intended GitHub repository and confirm the redistribution license and treatment of externally sourced mathematical inputs. Review the candidate archive in a normal Git checkout and authorize the push separately.

## Prepare the reviewed archive for a new empty repository

Confirm the destination, visibility, and license before staging. Use a separate empty directory, leaving the research workspace in place. Set `release_zip` to the absolute path of the validated ZIP and `repo_url` to the approved remote URL.

```bash
stage_dir=$(mktemp -d)
unzip -q "$release_zip" -d "$stage_dir"
cd "$stage_dir"
git init -b main
git add --pathspec-from-file=publication-files.txt
git diff --cached --name-only
git diff --cached --check
git status --short
```

Review the staged contents and license. For an approved existing repository, clone it into a separate directory and create a review branch with `git switch -c keno-source-release`. Compare each allowlisted file before merging it into the clone, especially any existing `.gitignore`. Use the same allowlist staging and review commands after resolving differences. Keep the existing history and remote.

After staging review and approval, commit with `git commit -m "Add reproducible Keno mathematical research platform"`. For a new empty repository, configure the approved URL with `git remote add origin "$repo_url"`. Check the URL with `git remote -v`. After separate push authorization, run `git push -u origin main` for a new empty repository, or `git push -u origin keno-source-release` for the existing repository review branch. If the remote has unexpected history, stop and review the existing-repository path.
