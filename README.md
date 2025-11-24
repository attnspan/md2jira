# MD2Jira -- Interact with the Jira API from the command line.

`MD2Jira` is an application designed to allow individuals to create and update JIRA tickets by simply feeding specifically formatted `Markdown` files to the app. 

## Features

* Create JIRA _Epic_, _Task_ and _Sub-task_ issues in JIRA
* Edit the _description_ fields of created issues
* Support for modern Jira API v3 with Atlassian Document Format (ADF)
* Robust error handling and retry logic

## Requirements

* **Python 3.11+** (required for modern dependencies)
* **Jira Cloud or Server** with API v3 support
* **Valid Jira API Token** with appropriate permissions

## Setup

### Authentication via JIRA API Key

#### Create JIRA API Token

* Navigate to JIRA [API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens) page
* Create and save your API Token in the password management tool of choice

#### Generate Authentication Token 

Run the following command(s) to generate the _base64_-encoded string you'll need for API calls

```
JIRA_EMAIL=<your_email_address>
API_TOKEN=<your_API_Token>
JIRA_AUTH_KEY=$(echo -n ${JIRA_EMAIL}:${API_TOKEN} | base64 | tr -d '\n')
```

### _.env_ File Setup

`MD2Jira` stores your JIRA authentication key in a file called _.env_. Run the following command to put the `JIRA_AUTH_KEY` value you generated (above) into your _.env_ file: 

```
echo "JIRA_AUTH_KEY = \"${JIRA_AUTH_KEY}\"" > .env
```

You'll also want to add your default JIRA "Project KEY" and subdomain to the _.env_ file. This is the prefix at the beginning of each JIRA issue, e.g. `MYP` for _MY Project_

```
JIRA_PROJECT_KEY=<YOUR_JIRA_PROJECT_KEY>
JIRA_PROJECT_SUBDOMAIN=<YOUR_JIRA_PROJECT_SUBDOMAIN>
echo "JIRA_PROJECT_KEY = \"${JIRA_PROJECT_KEY}\"" >> .env
echo "JIRA_PROJECT_SUBDOMAIN = \"${JIRA_PROJECT_SUBDOMAIN}\"" >> .env
```
### Installation & Usage

#### Quick Start (Traditional)

```bash
# Ensure Python 3.11+
python --version

# Install dependencies
python -m pip install -r requirements.txt

# Run with your markdown file
python main.py -i example.md
```

#### Modern Setup (UV - Recommended for Development)

**Prerequisites:** [UV installed](https://docs.astral.sh/uv/)

```bash
# Install UV (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# One-time setup
cd ~/workspace/md2jira

# Create virtual environment (super fast!)
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install as CLI tool (editable mode)
uv pip install -e .

# Now run from anywhere
md2jira -i example.md
```

**Why UV?**
- 10-100x faster than pip
- Automatic dependency resolution
- Creates isolated virtual environments
- Editable install means code changes reflect immediately

See the [Development](#development) section below for more details.

### Run Tests

```bash
# Install dependencies (if not already done)
python -m pip install -r requirements.txt

# Run full test suite
python -m pytest test/ -v

# Expected: 14/14 tests passing
```

## Upgrading from v1.x

If upgrading from a previous version:

1. **Update Python**: Ensure you have Python 3.11 or later
2. **Update Dependencies**: Run `pip install -r requirements.txt`
3. **Test Connection**: Verify your Jira instance works with the new API
4. **Issue Types**: Note that Story types now create Task issues

See [CHANGELOG.md](CHANGELOG.md) for detailed migration information.

## Example Markdown Format

Please see the [example.md](example.md) file for examples of different formatting options.

## Troubleshooting

### Common Issues

**"410 Gone" errors**: This indicates you're using an outdated version. Update to v2.0+ which uses Jira API v3.

**Python version errors**: Ensure you're using Python 3.11+. Use `pyenv` or `conda` to manage versions.

**Test failures**: If tests fail intermittently, it may be due to Jira indexing delays. The test suite includes automatic retries.

**ADF format issues**: Modern Jira returns descriptions in Atlassian Document Format. This version handles both ADF and plain text.

### Getting Help

1. Check the [CHANGELOG.md](CHANGELOG.md) for recent changes
2. Review the test suite for usage examples
3. Ensure your `.env` file is properly configured
4. Verify your Jira API token has the necessary permissions

## Development

### Project Structure

```
md2jira/
├── main.py              # CLI entry point
├── src/
│   └── md2jira.py      # Core functionality
├── test/               # Test suite (pytest)
├── pyproject.toml      # Modern Python packaging
├── requirements.txt    # Dependencies
└── .env                # Jira credentials (not in git)
```

### Development Setup with UV

This project uses modern Python packaging with `pyproject.toml` and UV for fast dependency management.

#### Initial Setup

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
cd ~/workspace/md2jira

# Create virtual environment
uv venv

# Activate it
source .venv/bin/activate

# Install in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

#### Wrapper Script

A wrapper script at `~/bin/md2jira` allows running from anywhere without activating the venv:

```bash
#!/bin/bash
source ~/workspace/md2jira/.venv/bin/activate
md2jira "$@"
```

Make it executable:
```bash
chmod +x ~/bin/md2jira
```

Now you can run `md2jira -i file.md` from anywhere!

#### Making Changes

Since the package is installed in editable mode (`-e`), changes to the source code take effect immediately:

```bash
# Edit code
vim src/md2jira.py

# Test immediately (no reinstall needed)
md2jira -i test-file.md

# Run tests
pytest test/ -v
```

#### Adding Dependencies

```bash
# Using UV (fast)
uv pip install new-package
uv pip freeze > requirements.txt

# Update pyproject.toml manually
vim pyproject.toml
```

### Why UV?

This project recommends **[UV](https://github.com/astral-sh/uv)** (by the Astral team, creators of Ruff) instead of traditional `pyenv` + `venv` + `pip`:

**Benefits:**
- **10-100x faster** than pip for package installation
- **Single tool** replaces pyenv, venv, and pip
- **Better dependency resolution** with automatic conflict detection
- **Modern Python standard** - increasingly adopted by the community
- **Written in Rust** for maximum performance

**Resources:**
- [Official UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub Repository](https://github.com/astral-sh/uv)
- [UV Announcement Blog Post](https://astral.sh/blog/uv)

**Traditional tools still work!** If you prefer pip/venv, the traditional installation method above works perfectly fine.

---

## Wishlist

* Update local files with updates from JIRA
* Support for editing checklists