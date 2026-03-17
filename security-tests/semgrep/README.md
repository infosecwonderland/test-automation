# Semgrep static analysis

This folder contains **Semgrep** configuration for scanning the SUT Node.js code under `sut/`.

## Install Semgrep (locally or in CI)

On macOS (Homebrew):

```bash
brew install semgrep
```

With pip:

```bash
python3 -m pip install semgrep
```

## Run Semgrep against the SUT

From the repo root:

```bash
# Use our local rules
semgrep scan --config security-tests/semgrep/semgrep.yml sut/

# (Optional) Also run Semgrep registry rules for JS/Node
# Requires network access and may need semgrep login
semgrep scan \
  --config p/javascript \
  --config p/nodejs \
  sut/
```

## What the local rules check

The starter rules in `semgrep.yml` focus on a few high-signal patterns:

- **js-no-eval**: flags any use of `eval(...)` (possible code injection).
- **js-no-child-process-exec**: flags use of `child_process.exec` / `spawn` with arbitrary commands.
- **js-hardcoded-jwt-secret**: flags hardcoded string secrets passed to `jwt.verify(...)`.

You can add more rules over time, either by:

- Extending `security-tests/semgrep/semgrep.yml` with project-specific patterns, or
- Relying on Semgrep registry packs like `p/javascript`, `p/nodejs`, `p/security-audit`.
