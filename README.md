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

```bash
# Ensure Python 3.11+
python --version

# Install dependencies
python -m pip install -r requirements.txt

# Run with your markdown file
python main.py -i example.md
```

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

## Wishlist

* Update local files with updates from JIRA
* Support for editing checklists