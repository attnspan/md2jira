# MD2Jira -- Stay Organized in JIRA ... without ... using ... JIRA?

`MD2Jira` is an application designed to allow individuals to create and update JIRA tickets by simply feeding specifically formatted `Markdown` files to the app. 

## Features

* Create JIRA _Epic_, _Story_ and _Sub-task_ issues in JIRA
* Edit the _description_ fields of created issues

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
### Usage

```
python -m pip install -r requirements.txt
python main.py -i example.md
```

### Run Tests

```
python -m pip install -r requirements.txt
python -m pytest test
```

## Example Markdown Format

Please see the [example.md](example.md) file for examples of different formatting options.

## Wishlist

* Update local files with updates from JIRA
* Support for editing checklists