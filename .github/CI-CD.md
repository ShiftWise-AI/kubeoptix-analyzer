# CI/CD Audit and Operations

## Findings (2026-10-09)

The original main push trigger was present and the latest main run succeeded.
Confirmed gaps: no tests/security gates, mutable Action tags, no publishing
dependency on GitFlow validation, and cancellation of main runs. All 21 branches
across the seven repositories required only `check-flow`, no approval, and no
up-to-date branch. Repository secrets were empty; organization secret access
could not be verified because the available token received 403.

## Pipeline Contract

PRs targeting `develop`, `stage`, or `main`, pushes to those branches, and merge
queues run GitFlow, pytest, workflow syntax validation, dependency/secret scans,
container build, non-root inspection, and final-image configuration, secret,
and vulnerability scans. `ci-required` fails on any failed, skipped, or cancelled
dependency. Trivy v0.69.3 blocks HIGH/CRITICAL even when no fix is available.
Actions use full SHAs and actionlint v1.7.7 is checksum-verified. The GitHub token
has only `contents: read`; checkout credentials are not persisted.

Only a main push or valid `vMAJOR.MINOR.PATCH` tag logs in and publishes the
already-scanned image to `quay.io/parraes/kubeoptix-analyzer`. Main retains
`latest` and `sha-<commit>`, releases version and SHA tags. Release commits must
belong to main history. PRs, stage/develop, and merge queues never access Quay
secrets. Main runs are not actively cancelled, though GitHub can coalesce
pending concurrent runs.

## GitHub and Quay Configuration

Applied and verified for main/stage/develop: require `check-flow` plus
`ci-required` from GitHub Actions, up-to-date branch, at least one approval,
dismiss stale reviews, require approval of the last push, enforce for admins,
and prohibit force pushes/deletion. Existing checks are preserved. An APPROVE
review can still be submitted while checks fail; integration is blocked.

Publish the updated workflows on the existing feature branch, open a PR to
develop, obtain a green gate and independent review, then promote
`develop -> stage -> main`. PRs without the new check remain blocked. Confirm
organization Actions policies allow the pinned actions. Protect `v*` tags with
a ruleset restricting creation to release maintainers and forbidding mutation.
`GITHUB_TOKEN`-generated pushes cannot trigger another push workflow; release
automation should use an approved GitHub App when creating tags.

Use a dedicated Quay robot with repository Write, not organization Admin.
Set `QUAY_USERNAME` (full `namespace+robot`) and `QUAY_PASSWORD` (robot token)
as repository secrets or restricted organization secrets including this repo.
Enter/rotate credentials in a secure UI or CLI prompt, never in logs, command
arguments, source, or shell tracing. Enable Quay vulnerability notifications.

## Validation and Remaining Acceptance

All 14 workflows passed actionlint; aggregate gate failures and 63 GitFlow cases
passed. The 21 remote protections were verified. Analyzer: 28 tests passed on
local Python 3.14. CI uses Python 3.12; clean dependency installation and image
build/scan still need GitHub execution. Source scans found no HIGH/CRITICAL
findings or secrets. No changed workflows were committed, pushed, or executed
remotely; no image was published. Acceptance requires a blocked failing PR,
a reviewed green promotion to main, and successful publication of the scanned
image with matching Quay digest.

## PR Failure Remediation (2026-10-09)

PR #28 was blocked by Python dependencies and vulnerable Node dependencies in
the bundled Cursor SDK. cursor-sdk 1.0.37 still embeds the affected Undici/Busboy,
so a separate build stage patches its bridge using npm overrides for Undici
6.28.1 and Busboy 3.2.1. npm/build tools are not copied into the runtime. msgpack,
urllib3, and setuptools are also fixed. Bridge imports and 28 Python 3.12 tests
passed on the real image. Authenticated Cursor sessions were not exercised.

Two embedded build inventories are excluded from the final-image scan:
`**/pip/_vendor/bom.cdx.json` and
`**/virtualenv-*.dist-info/sboms/virtualenv.cdx.json`. The latter nests historical
pip build components and falsely reports msgpack 1.1.2, setuptools 70.3.0, and
urllib3 2.7.0 even though the installed versions are 1.2.3, 84.0.0, and 2.8.0.
The inventories remain in the image for inspection. Actual package METADATA,
Node packages, binaries, secrets, and runtime configuration are still scanned;
no global CVE ignore or ignore-unfixed exception was added.

The resulting image scan passed. pip check additionally reports the pre-existing
KubeDiagrams 0.8.0 / PyGraphviz 2.0.1 metadata conflict; this change does not claim
to fix it or silently downgrade the working renderer. The updated PR requires
the new GitHub checks and independent review before merging.