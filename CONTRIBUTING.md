# Contributing to `nlearn-mcp`

Thank you for your interest in contributing to `nlearn-mcp`! This guide will help you set up your local development environment and walk you through the contribution process.

---

## 🛠️ Local Development Setup

### 1. Prerequisites
- Python 3.10 or higher.
- [uv](https://github.com/astral-sh/uv) (recommended) or standard `pip` / `venv`.

### 2. Getting the Code
Clone the repository:
```bash
git clone https://github.com/heshan-jj/nlearn-mcp.git
cd nlearn-mcp
```

### 3. Setting Up Dependencies

#### Using `uv` (Recommended)
```bash
# Sync packages and create a virtual environment (.venv)
uv sync
```

#### Using `pip`
Create a virtual environment and install dependencies in editable mode:
```bash
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

pip install -e .
```

### 4. Configuration
Create a `.env` file from the example:
```bash
# On Windows (PowerShell):
Copy-Item .env.example .env
# On macOS/Linux:
cp .env.example .env
```
Fill in `.env` with your sandbox or development credentials. **Never commit `.env` or your actual password.**

---

## 🧪 Running Tests

We use the standard library `unittest` module. Tests can be run locally without credentials (live integration tests are skipped by default):

```bash
# Run unit tests
python -m unittest discover -s tests
```

To run the live Moodle authentication integration tests (requires a valid Moodle server URL and credentials in `.env`), set `RUN_LIVE_INTEGRATION_TESTS=1` in your shell or `.env`:

```powershell
# In PowerShell:
$env:RUN_LIVE_INTEGRATION_TESTS="1"
python -m unittest discover -s tests
```

---

## 🚀 Submitting a Pull Request

1. **Create a Branch**: Create a feature branch off `master` (or `main`):
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Implement Changes**: Write clean Python code, keeping helper functions separate from FastMCP tool entrypoints.
3. **Write Tests**: Add appropriate tests in the `tests/` folder.
4. **Run Unit Tests**: Ensure all unit tests pass before committing.
5. **Commit and Push**: Write descriptive commit messages.
6. **Open a PR**: Submit a Pull Request targeting the default branch.

---

## 🔒 Security Policy
If you find a security vulnerability (such as a credentials leak or SSRF exploit path), please do not open a public issue. Instead, report it privately to the repository owner.
