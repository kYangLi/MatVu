# Releasing MatVu

## Checklist

1. Working tree clean, all tests green:

   ```bash
   git status --short
   .venv/bin/python -m pytest
   ```

2. Bump the version in `src/matvu/__init__.py`, add a `CHANGELOG.md` entry and
   commit (`release: x.y.z`).

3. Build and validate the artifacts:

   ```bash
   rm -rf dist && uv build
   uvx twine check dist/*
   sha256sum dist/*
   ```

4. Optional dry run on TestPyPI (create a token at
   https://test.pypi.org/manage/account/token/):

   ```bash
   uv publish --publish-url https://test.pypi.org/legacy/ --token <token>
   ```

5. Upload to PyPI (token from https://pypi.org/manage/account/token/ — the
   first upload needs an account-scoped token, project-scoped tokens can be
   used afterwards):

   ```bash
   uv publish --token <token>
   ```

6. Verify the install in a fresh environment:

   ```bash
   uv venv /tmp/matvu-check && uv pip install --python /tmp/matvu-check/bin/python matvu
   /tmp/matvu-check/bin/matvu --version
   ```

7. Create a GitHub Release for the new tag (e.g. `vX.Y.Z`) — the
   `release.yml` workflow then builds, checks and publishes automatically
   (see below).

## Automated releases (GitHub Actions)

Two workflows live in `.github/workflows/`:

- `test.yml` — runs the full test suite on Python 3.10–3.13 for pushes to
  `main` and for pull requests.
- `release.yml` — triggered by a published GitHub Release (or manually):
  builds sdist + wheel, runs `twine check`, publishes to PyPI with
  **Trusted Publishing** (OIDC, no token stored anywhere), and attaches the
  wheel/sdist to the GitHub Release.

One-time setup on PyPI — add a *pending publisher* at
<https://pypi.org/manage/account/publishing/>:

| Field | Value |
| --- | --- |
| PyPI project name | `matvu` |
| Owner | *your GitHub account* |
| Repository | `MatVu` |
| Workflow name | `release.yml` |
| Environment | `pypi` |

After that, releasing is just: bump the version → commit → tag → publish a
GitHub Release; the workflow uploads the artifacts.

## Git remote

Push access is configured per machine with a dedicated SSH key kept outside
the repository; the remote is:

```bash
git remote add origin git@github.com:<account>/MatVu.git
```
