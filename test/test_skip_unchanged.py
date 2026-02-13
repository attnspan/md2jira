"""Unit tests for change-detection / skip-unchanged logic.

These tests mock the JIRA API so they can run without credentials.
They verify that:
  - Issues whose local hash matches the cache are skipped (no API update)
  - Issues not in the cache fall back to remote comparison
  - Identical remote content is detected as unchanged and seeds the cache
  - Changed remote content triggers an update
  - ADF descriptions are properly converted to plain text
  - Description normalisation handles whitespace edge-cases
"""

import argparse
import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

from src.md2jira import MD2Jira, Issue, IssueType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**overrides):
    """Build a minimal args namespace for MD2Jira."""
    defaults = {
        'INFILE': 'example.md',
        'JIRA_PROJECT_KEY': 'TEST',
        'verbose': False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_md2jira(**arg_overrides):
    """Instantiate MD2Jira with env vars stubbed out."""
    env = {
        'JIRA_PROJECT_SUBDOMAIN': 'fake',
        'JIRA_DOMAIN': 'atlassian.net',
        'JIRA_AUTH_KEY': 'dW5zZXQ6dW5zZXQ=',
        'JIRA_PROJECT_KEY': 'TEST',
    }
    with patch.dict(os.environ, env, clear=False):
        return MD2Jira(_make_args(**arg_overrides))


# ---------------------------------------------------------------------------
# adf_to_text
# ---------------------------------------------------------------------------

class TestAdfToText:
    """Verify that Atlassian Document Format dicts are converted to text."""

    def setup_method(self):
        self.md2j = _make_md2jira()

    def test_none_returns_empty(self):
        assert self.md2j.adf_to_text(None) == ''

    def test_plain_string_passthrough(self):
        assert self.md2j.adf_to_text('hello') == 'hello'

    def test_simple_paragraph(self):
        adf = {
            'type': 'doc',
            'version': 1,
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {'type': 'text', 'text': 'Hello world'}
                    ]
                }
            ]
        }
        assert self.md2j.adf_to_text(adf) == 'Hello world'

    def test_multiple_paragraphs(self):
        adf = {
            'type': 'doc',
            'version': 1,
            'content': [
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'First'}]
                },
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'Second'}]
                },
            ]
        }
        result = self.md2j.adf_to_text(adf)
        assert 'First' in result
        assert 'Second' in result

    def test_inline_nodes_concatenated(self):
        """Multiple text nodes inside one paragraph are joined without newlines."""
        adf = {
            'type': 'paragraph',
            'content': [
                {'type': 'text', 'text': 'Hello '},
                {'type': 'text', 'text': 'world'},
            ]
        }
        assert self.md2j.adf_to_text(adf) == 'Hello world'

    def test_empty_doc(self):
        adf = {'type': 'doc', 'version': 1, 'content': []}
        assert self.md2j.adf_to_text(adf) == ''


# ---------------------------------------------------------------------------
# _normalise_for_compare
# ---------------------------------------------------------------------------

class TestNormaliseForCompare:
    def test_empty_string(self):
        assert MD2Jira._normalise_for_compare('') == ''

    def test_none(self):
        assert MD2Jira._normalise_for_compare(None) == ''

    def test_strips_outer_whitespace(self):
        assert MD2Jira._normalise_for_compare('  hello  ') == 'hello'

    def test_strips_trailing_whitespace_per_line(self):
        assert MD2Jira._normalise_for_compare('a  \nb  ') == 'a\nb'

    def test_collapses_blank_lines(self):
        text = 'a\n\n\n\nb'
        assert MD2Jira._normalise_for_compare(text) == 'a\n\nb'

    def test_identical_after_normalise(self):
        a = '  hello\n\n\nworld  '
        b = 'hello\n\nworld'
        assert MD2Jira._normalise_for_compare(a) == MD2Jira._normalise_for_compare(b)


# ---------------------------------------------------------------------------
# diff_issue_against_remote
# ---------------------------------------------------------------------------

class TestDiffIssueAgainstRemote:
    def setup_method(self):
        self.md2j = _make_md2jira()

    def test_identical_issues_no_change(self):
        local  = Issue(IssueType.Epic, 'TEST-1', 'My Epic', 'Some description')
        remote = Issue(IssueType.Epic, 'TEST-1', 'My Epic', 'Some description')
        assert self.md2j.diff_issue_against_remote(local, remote) is False

    def test_different_summary_detected(self):
        local  = Issue(IssueType.Epic, 'TEST-1', 'My Epic v2', 'desc')
        remote = Issue(IssueType.Epic, 'TEST-1', 'My Epic v1', 'desc')
        assert self.md2j.diff_issue_against_remote(local, remote) is True

    def test_different_description_detected(self):
        local  = Issue(IssueType.Epic, 'TEST-1', 'Epic', 'new desc')
        remote = Issue(IssueType.Epic, 'TEST-1', 'Epic', 'old desc')
        assert self.md2j.diff_issue_against_remote(local, remote) is True

    def test_whitespace_differences_ignored(self):
        local  = Issue(IssueType.Epic, 'TEST-1', 'Epic', '  hello\n\n\nworld  ')
        remote = Issue(IssueType.Epic, 'TEST-1', 'Epic', 'hello\n\nworld')
        assert self.md2j.diff_issue_against_remote(local, remote) is False

    def test_none_description_treated_as_empty(self):
        local  = Issue(IssueType.Epic, 'TEST-1', 'Epic', '')
        remote = Issue(IssueType.Epic, 'TEST-1', 'Epic', '')
        # Force remote description to None to simulate missing field
        remote.description = None
        assert self.md2j.diff_issue_against_remote(local, remote) is False

    def test_verbose_prints_changed_fields(self, capsys):
        md2j = _make_md2jira(verbose=True)
        local  = Issue(IssueType.Epic, 'TEST-1', 'Epic', 'new')
        remote = Issue(IssueType.Epic, 'TEST-1', 'Epic', 'old')
        md2j.diff_issue_against_remote(local, remote)
        captured = capsys.readouterr()
        assert '[diff]' in captured.out
        assert 'description' in captured.out


# ---------------------------------------------------------------------------
# process_issue — skip-unchanged behaviour
# ---------------------------------------------------------------------------

class TestProcessIssueSkipUnchanged:
    """Verify that process_issue skips updates when content is unchanged."""

    def setup_method(self):
        self.md2j = _make_md2jira()

    @patch.object(MD2Jira, 'find_issue')
    @patch.object(MD2Jira, 'check_issue_cache_hash', return_value=True)
    @patch.object(MD2Jira, 'update_issue')
    def test_cache_hit_skips_update(self, mock_update, mock_cache, mock_find):
        """When the cache hash matches, update_issue must NOT be called."""
        remote = Issue(IssueType.Epic, 'TEST-1', 'My Epic', 'desc')
        mock_find.return_value = remote

        local = Issue(IssueType.Epic, '', 'My Epic', 'desc')
        self.md2j.process_issue(local)

        mock_update.assert_not_called()

    @patch.object(MD2Jira, 'find_issue')
    @patch.object(MD2Jira, 'check_issue_cache_hash', return_value=True)
    @patch.object(MD2Jira, 'update_issue')
    def test_cache_hit_prints_skipping(self, mock_update, mock_cache, mock_find, capsys):
        """Cache-hit path should print 'up to date, skipping'."""
        remote = Issue(IssueType.Epic, 'TEST-1', 'My Epic', 'desc')
        mock_find.return_value = remote

        local = Issue(IssueType.Epic, '', 'My Epic', 'desc')
        self.md2j.process_issue(local)

        captured = capsys.readouterr()
        assert 'up to date, skipping' in captured.out

    @patch.object(MD2Jira, 'find_issue')
    @patch.object(MD2Jira, 'check_issue_cache_hash', return_value=False)
    @patch.object(MD2Jira, 'update_issue')
    @patch.object(MD2Jira, 'update_issue_cache')
    def test_cache_miss_identical_remote_seeds_cache(
        self, mock_cache_update, mock_update, mock_cache_check, mock_find
    ):
        """Cache miss with identical remote content should seed the cache,
        not call update_issue."""
        remote = Issue(IssueType.Epic, 'TEST-1', 'My Epic', 'Same description')
        mock_find.return_value = remote

        local = Issue(IssueType.Epic, '', 'My Epic', 'Same description')
        self.md2j.process_issue(local)

        mock_update.assert_not_called()
        mock_cache_update.assert_called_once()

    @patch.object(MD2Jira, 'find_issue')
    @patch.object(MD2Jira, 'check_issue_cache_hash', return_value=False)
    @patch.object(MD2Jira, 'update_issue')
    @patch.object(MD2Jira, 'update_issue_cache')
    @patch.object(MD2Jira, 'prepare_issue', return_value='{}')
    def test_cache_miss_different_remote_triggers_update(
        self, mock_prepare, mock_cache_update, mock_update, mock_cache_check, mock_find
    ):
        """Cache miss with differing remote content should call update_issue."""
        remote = Issue(IssueType.Epic, 'TEST-1', 'My Epic', 'old description')
        mock_find.return_value = remote

        local = Issue(IssueType.Epic, '', 'My Epic', 'new description')
        self.md2j.process_issue(local)

        mock_update.assert_called_once()
        mock_cache_update.assert_called_once()

    @patch.object(MD2Jira, 'find_issue', return_value=None)
    @patch.object(MD2Jira, 'create_issue')
    @patch.object(MD2Jira, 'prepare_issue', return_value='{}')
    def test_new_issue_creates(self, mock_prepare, mock_create, mock_find):
        """When the issue doesn't exist remotely, it should be created."""
        created = Issue(IssueType.Epic, 'TEST-99', 'Brand New Epic', 'desc')
        mock_create.return_value = created

        local = Issue(IssueType.Epic, '', 'Brand New Epic', 'desc')
        self.md2j.process_issue(local)

        mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# Verbose output
# ---------------------------------------------------------------------------

class TestVerboseOutput:
    def test_cache_hit_verbose(self, capsys):
        md2j = _make_md2jira(verbose=True)

        with patch.object(MD2Jira, 'find_issue') as mock_find, \
             patch.object(MD2Jira, 'check_issue_cache_hash', return_value=True), \
             patch.object(MD2Jira, 'update_issue') as mock_update:

            remote = Issue(IssueType.Epic, 'TEST-1', 'Epic', 'desc')
            mock_find.return_value = remote

            local = Issue(IssueType.Epic, '', 'Epic', 'desc')
            md2j.process_issue(local)

            captured = capsys.readouterr()
            assert '[cache-hit]' in captured.out
            mock_update.assert_not_called()

    def test_cache_miss_verbose(self, capsys):
        md2j = _make_md2jira(verbose=True)

        with patch.object(MD2Jira, 'find_issue') as mock_find, \
             patch.object(MD2Jira, 'check_issue_cache_hash', return_value=False), \
             patch.object(MD2Jira, 'update_issue'), \
             patch.object(MD2Jira, 'update_issue_cache'):

            remote = Issue(IssueType.Epic, 'TEST-1', 'Epic', 'same desc')
            mock_find.return_value = remote

            local = Issue(IssueType.Epic, '', 'Epic', 'same desc')
            md2j.process_issue(local)

            captured = capsys.readouterr()
            assert '[cache-miss]' in captured.out
