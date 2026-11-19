# Publish `flawd` to PyPI

Wheel builds locally as `dist/flawd-0.2.0-*.whl`. The GitHub Action
[`.github/workflows/publish-pypi.yml`](../.github/workflows/publish-pypi.yml)
publishes on `release` using Trusted Publishing (OIDC) — no long-lived token in the repo.

## One-time setup (PyPI)

1. Create/login at https://pypi.org/manage/account/
2. **Publishing → Add a new pending publisher**
   - PyPI project name: `flawd`
   - Owner: `antonrabcuk8-lgtm`
   - Repository: `flawd`
   - Workflow: `publish-pypi.yml`
   - Environment: `pypi`
3. In GitHub → Settings → Environments → create **`pypi`** (optional protection rules).
4. Create a GitHub Release (tag `v0.2.0`) — the workflow uploads the package.

## Manual fallback

```bash
python -m pip install build twine
python -m build
twine upload dist/*
# username: __token__
# password: pypi-… (API token)
```

## Name note

PyPI name `flawd` was free at publish time. An unrelated commercial product also
uses the “Flawd” brand (mutation testing / UX testing). Our package description
and homepage point at the **AI-agent crash-test catalog** so the listing stays clear.
