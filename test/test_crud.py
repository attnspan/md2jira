import pytest
import urllib3
from urllib.parse import urlencode, quote
import argparse
from src.md2jira import MD2Jira, Issue, IssueType

import os
from dotenv import load_dotenv
load_dotenv(override=True)

pytest.args = argparse.ArgumentParser()
pytest.args.INFILE = 'example.md'
pytest.args.JIRA_PROJECT_KEY = os.environ.get('JIRA_PROJECT_KEY')
pytest.issue = Issue(IssueType.Epic, '', 'holy, bagumba!', 'description has `TEST`')
pytest.updated_description = 'updated description with `another formatting challenge`'


class TestMD2JIRA:
    def test_create(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = pytest.issue
        issue_data = md2jira.prepare_issue(issue)
        result     = md2jira.create_issue(issue, issue_data)
        if result.key != '':
            pytest.issue     = result
            pytest.issue_key = result.key
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.Epic
        assert result.key != ''

    def test_update(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = pytest.issue
        issue.description = pytest.updated_description
        issue_data = md2jira.prepare_issue(issue)
        result     = md2jira.update_issue(issue, issue_data)
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.Epic
        assert result.key != ''
        assert result.key == issue.key
        assert result.summary == issue.summary
        assert result.description == issue.description

    def test_read(self):
        md2jira    = MD2Jira(pytest.args)
        result     = md2jira.read_issue(pytest.issue_key)
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.Epic
        assert result.key != ''
        assert result.key == pytest.issue_key
        assert result.summary == pytest.issue.summary
        assert result.description == pytest.updated_description

    def test_find(self):
        md2jira    = MD2Jira(pytest.args)
        result     = md2jira.find_issue(pytest.issue)
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.Epic
        assert result.key != ''
        assert result.key == pytest.issue_key
        assert result.summary == pytest.issue.summary
        assert result.description == pytest.updated_description

    def test_delete(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = Issue(IssueType.Epic, pytest.issue_key)
        result     = md2jira.delete_issue(issue)
        assert type(result) == urllib3.response.HTTPResponse
        assert result.reason == 'No Content'
        assert result.status == 204
