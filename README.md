# MD2Jira

Create and update Jira Epics, Tasks, and Sub-tasks from Markdown files.

## Prerequisites

* Python 3.9+
* A Jira Cloud instance with API access
* [UV](https://docs.astral.sh/uv/getting-started/installation/) package manager

## Setup

### 1. Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install dependencies

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 3. Create a Jira API token

Generate a token at the Atlassian [API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens) page.

Then create a `.env` file in the project root:

```bash
JIRA_EMAIL=<your_email_address>
API_TOKEN=<your_API_token>
JIRA_AUTH_KEY=$(echo -n ${JIRA_EMAIL}:${API_TOKEN} | base64 | tr -d '\n')

echo "JIRA_AUTH_KEY = \"${JIRA_AUTH_KEY}\"" > .env
echo "JIRA_PROJECT_KEY = \"<YOUR_PROJECT_KEY>\"" >> .env
echo "JIRA_PROJECT_SUBDOMAIN = \"<YOUR_SUBDOMAIN>\"" >> .env
```

`JIRA_PROJECT_KEY` is the prefix on your Jira issues (e.g. `MYP` for *MY Project*). `JIRA_PROJECT_SUBDOMAIN` is the `<subdomain>` portion of `https://<subdomain>.atlassian.net`.

### 4. Verify your setup

Run the CRUD test suite — it creates a temporary Epic in your Jira project, verifies read/update/find, then deletes it:

```bash
pytest test/test_crud.py -v
```

## Usage

```bash
# With the virtual environment active:
md2jira -i example.md

# Or without activating:
python main.py -i example.md
```

The `-p` flag overrides the project key from `.env`:

```bash
md2jira -i example.md -p OTHER_PROJECT
```

## Markdown Format

Header levels map to Jira issue types:

| Markdown | Jira Issue |
|----------|------------|
| `# Title` | Epic |
| `## Title` | Task |
| `### Title` | Sub-task |

Everything below a header becomes that issue's description. See [example.md](example.md) for a minimal example and [example-full.md](example-full.md) for comprehensive formatting (code blocks, tables, checklists, etc.).

## Optional: System-wide `md2jira` command

To run `md2jira` from any directory without activating the venv, create a wrapper script somewhere on your `PATH`:

```bash
#!/bin/bash
source /path/to/md2jira/.venv/bin/activate
md2jira "$@"
```

Make it executable with `chmod +x` and you're set.

## Running the full test suite

```bash
pytest test/ -v
```
