import pytest
import urllib3
from src.md2jira import MD2Jira, Issue, IssueType

class TestMD2JIRA:
    def test_create(self):
        md2jira    = MD2Jira()
        issue      = Issue(IssueType.EPIC, '', 'pytest_issue_001', 'description')
        issue_data = md2jira.prepare_issue(issue)
        result     = md2jira.create_issue(issue, issue_data)
        if result.key != '':
            pytest.issue     = result
            pytest.issue_key = result.key
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.EPIC
        assert result.key != ''

    def test_update(self):
        md2jira    = MD2Jira()
        issue      = pytest.issue
        issue.description = 'i have changed this thing'
        issue_data = md2jira.prepare_issue(issue)
        result     = md2jira.update_issue(issue, issue_data)
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.EPIC
        assert result.key != ''
        assert result.key == issue.key
        assert result.summary == issue.summary
        assert result.description == issue.description

    def test_read(self):
        md2jira    = MD2Jira()
        result     = md2jira.read_issue(pytest.issue_key)
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.EPIC
        assert result.key != ''
        assert result.key == pytest.issue_key
        assert result.summary == 'pytest_issue_001'
        assert result.description == 'i have changed this thing'

    def test_find(self):
        md2jira    = MD2Jira()
        result     = md2jira.find_issue(pytest.issue)
        assert result != None
        assert type(result) == Issue
        assert result.type == IssueType.EPIC
        assert result.key != ''
        assert result.key == pytest.issue_key
        assert result.summary == 'pytest_issue_001'
        assert result.description == 'i have changed this thing'

    def test_delete(self):
        md2jira    = MD2Jira()
        issue      = Issue(IssueType.EPIC, pytest.issue_key)
        result     = md2jira.delete_issue(issue)
        assert type(result) == urllib3.response.HTTPResponse
        assert result.reason == 'No Content'
        assert result.status == 204
