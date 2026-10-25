# 13: CI scanners and image pinning

**What to build:** CI catches leaked secrets and known vulnerabilities in the image and dependencies, and the base images do not move under the build.

**Blocked by:** 04. Secret-free image and hardened runtime.

**Status:** ready-for-agent

- [ ] CI runs gitleaks, osv-scanner, and trivy image.
- [ ] Base images are pinned by digest.
- [ ] Dependabot or Renovate keeps the Python and Bun lockfiles current.
- [ ] A planted secret and a planted vulnerable dependency each fail the relevant check.
- [ ] A clean build passes.
- [ ] Demo: run the scanners against the hardened image and the repository.
