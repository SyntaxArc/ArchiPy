## Summary

<!-- What changed and why. PR title: conventional commit, e.g. `fix(redis): ...` -->

Closes #

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no behavior change)
- [ ] Docs / tooling / chore
- [ ] Breaking change (avoid: deprecate with `DeprecationWarning` and keep the old path)

## How was it tested?

<!-- Behave feature / scenario names, or commands run. -->

## Checklist

- [ ] `make format` and `make lint` pass
- [ ] `make behave` (or the affected feature files) pass
- [ ] `make security` run if touching adapters, auth, crypto, or network code
- [ ] Import direction respected: `models ← configs ← helpers ← adapters`
- [ ] BDD scenarios added or updated for new behavior
- [ ] Docs updated if user-facing behavior changed
- [ ] No secrets, large generated files, or unrelated lockfile changes
