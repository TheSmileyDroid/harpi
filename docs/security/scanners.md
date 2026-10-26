# CI scanners

The `Security` workflow (`.github/workflows/security.yml`) runs on every push
to `main`, on every pull request, weekly on Monday, and on demand. Every job
fails the workflow when its scanner reports a finding. The workflow uses the
default `GITHUB_TOKEN` with `contents: read` and no repository secret.[^workflow]

## What each scanner covers

| Job | Tool | Input | Fails on |
| --- | --- | --- | --- |
| Secret scan | gitleaks 8.30.1 | full git history | any committed value matching a gitleaks rule |
| Dependency scan | osv-scanner 2.7.0 | `uv.lock`, `web/bun.lock` | a locked version with a known advisory |
| Image scan | trivy 0.76.1 | the image built from `Dockerfile` | HIGH or CRITICAL CVE with a fix available |

gitleaks scans the commit history of the checked-out ref, not only the working
tree, and redacts the match before printing it.[^gitleaks] osv-scanner resolves
both lockfiles against the OSV.dev database and exits non-zero when it finds a
vulnerability.[^osv] trivy reads the Debian packages and the Python packages
inside the built image.[^trivy]

The image scan is the backstop for the Python lockfile. `Dockerfile` runs
`uv sync --upgrade`, so the image resolves newer versions than `uv.lock`
records.[^dockerfile] osv-scanner checks what the lockfile pins and trivy checks
what the container runs. The Bun dependencies never reach the final image, so
osv-scanner is their only check.

## Pins

Actions are pinned by commit SHA and the images referenced by the workflow and
the `Dockerfile` by digest, so a rebuild cannot pick up a different binary.

| Reference | Version | Pin |
| --- | --- | --- |
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `aquasecurity/trivy-action` | v0.36.0 | `ed142fd0673e97e23eac54620cfb913e5ce36c25` |
| `google/osv-scanner-action/osv-scanner-action` | v2.7.0 | `b1d267aea5211fa648d9d442fa64b90dbdcbdd36` |
| `ghcr.io/gitleaks/gitleaks` | v8.30.1 | `sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f` |
| `oven/bun` | `1` | `sha256:1d22548f177f4ff38e0c15baa3c2c46c6c2060ba2d1bc573bb4720b407548f1d` |
| `ghcr.io/astral-sh/uv` | `python3.13-bookworm-slim` | `sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca` |

The trivy binary version is pinned through the action's `version` input, and
the osv-scanner action pins its own container image to the v2.7.0 release tag.
Dependabot opens a weekly pull request for each ecosystem in
`.github/dependabot.yml`: `uv` at the repository root, `bun` under `web/`,
`docker` for the `Dockerfile`, and `github-actions` for the workflow. Dependabot
supports Bun version updates but not Bun security updates, so a Bun advisory
reaches the repository through osv-scanner or the weekly version pull
request.[^dependabot]

## What the scanners do not cover

None of the three looks at request handling. SSRF, cross-tenant authorization,
cookie flags, rate limits, and headers are covered by `tests/` and the probes
in the release gate. The scanners also say nothing about the runtime
environment, secrets in logs, proxy configuration, or license compliance.
Workflow hardening, such as whether a step can be exploited through untrusted
input, is out of scope too.

## Triage a finding

1. Read the job log. gitleaks prints the rule, file, commit, and a redacted
   match. osv-scanner and trivy print the package, installed version, fixed
   version, and advisory identifier.
2. Reproduce it. `make security` runs the scanners that are installed locally;
   for the image, build it and run `trivy image harpi:local`.
3. Treat a leaked secret as live. Rotate it with
   [runbook-secret-rotation.md](runbook-secret-rotation.md), then remove it from
   history. Deleting the file leaves the value in every clone.
4. Fix a dependency by updating the lockfile with `make bootstrap`, or by
   moving the base image digest to a rebuilt tag. Re-run the workflow.
5. For a CVE with no upstream fix, the image scan already skips it because
   `ignore-unfixed` is set. A finding that still fails has a fix available.
6. Never lower the severity, add an ignore rule, or remove a scanner step to
   make the job green.

A finding that comes from a test fixture gets a narrow allowlist entry naming
the file and the rule. A rule-wide allowlist would hide the same leak in
production code.

## Local runs and CI-only checks

`make security` runs gitleaks, osv-scanner, and trivy when each binary is on
`PATH`, and prints a skip line for the ones that are missing without installing
anything.[^makefile] Trivy needs a local image; `SECURITY_IMAGE` defaults to
`harpi:local`. The workflow adds the parts the local target cannot provide: a
full-history checkout with `fetch-depth: 0`, the image build, and the pinned
scanner versions.

A planted secret fails the secret job because gitleaks exits non-zero on any
leak. A planted vulnerable dependency is not committed to the lockfiles, since
`uv.lock` and `web/bun.lock` are deployment inputs and a deliberate vulnerable
pin would have to be reverted afterwards; the dependency job relies on
osv-scanner's documented exit behaviour instead. This repository has no local
gitleaks install, so the planted-secret check is unverified until the workflow
runs it.

[^workflow]: `.github/workflows/security.yml`.
[^gitleaks]: gitleaks. "gitleaks", v8.30.1. https://github.com/gitleaks/gitleaks
[^osv]: Google. "OSV-Scanner". https://google.github.io/osv-scanner/
[^trivy]: Aqua Security. "Trivy vulnerability scanner". https://trivy.dev/latest/docs/scanner/vulnerability/
[^dockerfile]: `Dockerfile`, `FROM` lines and the `uv sync --upgrade` steps.
[^dependabot]: GitHub. "Dependabot supported ecosystems and repositories". https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories
[^makefile]: `Makefile`, target `security`.
