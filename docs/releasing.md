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

7. Tag and push (after the GitHub repository exists):

   ```bash
   git tag v0.1.0 && git push origin main --tags
   ```

## Later: automated releases

Once the GitHub repository exists, configure PyPI *Trusted Publishing*
(publisher: GitHub Actions, workflow `release.yml`, environment `pypi`) and a
workflow that builds and uploads on tag pushes. No long-lived token is needed
then.
