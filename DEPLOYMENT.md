# Deployment Guide

This project is designed to be pushed to GitHub and deployed to Streamlit
Community Cloud without changing the compiler implementation.

## 1. Prepare the local checkout

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pytest
```

The project targets Python 3.11 or newer. The repository contains no required
machine-specific files, credentials, API keys, or external services.

## 2. Push to GitHub

The target GitHub repository is:

<https://github.com/advik1869/compiler-phase-ordering>

Run the following commands from the project root:

```bash
git init
git add .
git status
git commit -m "Prepare compiler optimization project for deployment"
git branch -M main
git remote add origin https://github.com/advik1869/compiler-phase-ordering.git
git push -u origin main
```

Review `git status` and the staged file list before committing. Do not commit
`.venv/`, `.env` files, secrets, caches, or local IDE settings.

## 3. Deploy with Streamlit Community Cloud

1. Open Streamlit Community Cloud and sign in with GitHub.
2. Choose **Create app**.
3. Select the `advik1869/compiler-phase-ordering` repository and its `main`
   branch.
4. Set the main file path to:

   ```text
   app/streamlit_app.py
   ```

5. Use the repository's default Python configuration, which satisfies the
   `requires-python = ">=3.11"` declaration in `pyproject.toml`.
6. Deploy the app.

Streamlit Cloud installs the dependencies listed in `requirements.txt`.
The application resolves `src/`, `benchmarks/`, and `results/` relative to
its own repository location, so it does not depend on the cloud process's
working directory.

## 4. Verify a deployment

Check the deployment logs for a successful dependency installation and app
startup. Then verify each navigation section:

- **Optimize TAC**: enter TAC or upload a `.tac` file and run a pass order.
- **Compare 24 Orders**: confirm all canonical permutations complete.
- **Benchmark Dashboard**: confirm the stored 20-benchmark results load.
- **Pass Interactions**: confirm the six Phase 10 pairs are displayed.
- **About**: confirm the project description is visible.

The dashboard loads canonical result files and does not rerun the complete
480-evaluation experiment on startup.

## 5. Troubleshooting

### `ModuleNotFoundError: optimizer`

Confirm that the Streamlit entry point is exactly `app/streamlit_app.py` and
that the repository contains `src/optimizer/`. The entry point adds the
repository's `src/` directory using a path derived from `__file__`.

### Missing experiment results or plots

Confirm that `results/experiment_results.json` and `results/plots/` are
committed. Regenerate them locally with:

```bash
python3 scripts/run_experiment.py
```

### Dependency installation failure

Check that `requirements.txt` is present at the repository root and that the
selected Python version is 3.11 or newer. Review the first package-install
error in the Streamlit deployment logs.

### TAC parsing errors

Use the project's TAC grammar. For example, use `print t1`, not `print(t1)`.
The UI reports malformed TAC as a readable error rather than exposing a
traceback.

## 6. Updating the deployed app

After making and testing a change locally:

```bash
git add <changed-files>
git commit -m "Describe the change"
git push origin main
```

Streamlit Community Cloud detects the new commit and redeploys the selected
branch. If deployment fails, inspect the build and runtime logs before making
additional changes.
