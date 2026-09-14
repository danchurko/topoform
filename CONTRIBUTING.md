# Contributing

Keep changes model-first and offline. Edit JSON sources, then validate the
models and inspect the generated artifact; do not commit generated HTML or
browser evidence.

## Fast checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/release.py check
```

For browser-facing changes, install Playwright and Chromium in your own
environment and run the regression suite with evidence written outside the
repository:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/run_browser.py --out "$(mktemp -d)"
```

Use `python3 scripts/diagram.py validate examples/<model>.json` while editing
a model. A release archive is created only after the package check succeeds:

```bash
release_dir="$(mktemp -d)"
python3 scripts/release.py archive --version v1.0.0 --output "$release_dir"
```

Keep licenses and provenance manifests current when changing vendored runtime
or icon assets. Do not add credentials, host-specific paths, raw screenshots,
or generated reports to the repository.
