---
applyTo: ".github/workflows/**/*.yml,.github/workflows/**/*.yaml"
---

When editing GitHub Actions workflows in this repository:
- Keep permissions as least-privileged as practical.
- Pin third-party actions to immutable SHAs when possible.
- Preserve existing workflow triggers unless the task explicitly requests trigger changes.
- Prefer small, auditable workflow diffs.
