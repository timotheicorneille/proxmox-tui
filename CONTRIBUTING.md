# Contributing

## Branches

| Prefix | Use |
|--------|-----|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `chore/` | Maintenance, deps, tooling |
| `docs/` | Documentation only |
| `refactor/` | Code change with no behavior change |

Examples: `feat/vm-search`, `fix/clone-timeout`, `docs/api-token-setup`

`main` is always stable and runnable.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/) — lowercase, no period at the end.

```
feat: add VM search filter
fix: handle missing ipconfig in detail panel
chore: bump textual to 0.72
docs: clarify token setup in README
refactor: extract status formatting to helper
```

Breaking changes: append `!` after the type.

```
feat!: replace config.toml with env vars
```

## Pull requests

- One PR per topic
- PR title follows the same conventional commit format
- Squash on merge
