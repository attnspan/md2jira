import pytest
import urllib3
from urllib.parse import urlencode, quote
import argparse
from src.md2jira import MD2Jira, Issue, IssueType

pytest.args = argparse.ArgumentParser()
pytest.args.INFILE = 'example.md'
pytest.args.JIRA_PROJECT_KEY = 'DRT'
pytest.issue_epic    = Issue(IssueType.Epic, '', 'Epic Test 001', 'description has `TEST`')
pytest.issue_story   = Issue(IssueType.Story, '', 'Story Test 001', 'description has `TEST`')
pytest.issue_subtask = Issue(IssueType.Subtask, '', 'Subtask Test 001', 'description has `TEST`')

class TestMD2JIRA:
    def test_create_epic(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = pytest.issue_epic
        issue_data = md2jira.prepare_issue(issue)
        result     = md2jira.create_issue(issue, issue_data)
        if result.key != '':
            pytest.epic_issue     = result
            pytest.epic_issue_key = result.key
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.Epic
        assert result.key != ''

    def test_create_story(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = pytest.issue_story

        md2jira.epic_id = pytest.epic_issue_key
        issue.epic_id   = pytest.epic_issue_key

        issue_data = md2jira.prepare_issue(issue)
        result     = md2jira.create_issue(issue, issue_data)
        if result.key != '':
            pytest.story_issue     = result
            pytest.story_issue_key = result.key
            md2jira.parent_id      = result.key
            issue.parent_id        = result.key
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.Story
        assert result.key != ''
        assert hasattr(result, 'epic_id')
        assert result.epic_id == issue.epic_id

    def test_create_subtask(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = pytest.issue_subtask

        md2jira.parent_id = pytest.story_issue_key
        issue.parent_id   = pytest.story_issue_key

        issue_data = md2jira.prepare_issue(issue)
        result     = md2jira.create_issue(issue, issue_data)
        if result.key != '':
            pytest.subtask_issue     = result
            pytest.subtask_issue_key = result.key
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.Subtask
        assert result.key != ''
        assert hasattr(result, 'parent_id')
        assert result.parent_id == issue.parent_id

    def test_delete_subtask(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = Issue(IssueType.Story, pytest.subtask_issue_key)
        result     = md2jira.delete_issue(issue)
        assert type(result) == urllib3.response.HTTPResponse
        assert result.reason == 'No Content'
        assert result.status == 204

    def test_delete_story(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = Issue(IssueType.Story, pytest.story_issue_key)
        result     = md2jira.delete_issue(issue)
        assert type(result) == urllib3.response.HTTPResponse
        assert result.reason == 'No Content'
        assert result.status == 204

    def test_delete_epic(self):
        md2jira    = MD2Jira(pytest.args)
        issue      = Issue(IssueType.Epic, pytest.epic_issue_key)
        result     = md2jira.delete_issue(issue)
        assert type(result) == urllib3.response.HTTPResponse
        assert result.reason == 'No Content'
        assert result.status == 204
