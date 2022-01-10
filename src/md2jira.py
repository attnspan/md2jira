#!/usr/bin/env python

import os
from dotenv import load_dotenv
import re
import tempfile
from enum import Enum
import urllib3
from urllib.parse import urlencode, quote
import certifi
import json
import hashlib

class MD2Jira:
    def __init__(self, args): 

        load_dotenv()

        self.args       = args
        self.baseurl    = 'https://{}.atlassian.net/rest/api/2'.format(os.environ.get('JIRA_PROJECT_SUBDOMAIN'))
        self.http       = urllib3.PoolManager(ca_certs=certifi.where())
        self.epic_re    = re.compile(r'^#\s+')
        self.story_re   = re.compile(r'^##\s+')
        self.subtask_re = re.compile(r'^###\s+')
        self.epic_id    = ''
        self.parent_id  = ''

    def jira_http_call(self, url, verb='GET', body=''):

        req_headers={
            'Content-Type': 'application/json',
            'Authorization': 'Basic {}'.format(os.environ.get('JIRA_AUTH_KEY'))
        }

        if verb == 'GET' or verb == 'DELETE':
            resp = self.http.request(verb, url, headers=req_headers)
        else:
            encoded_data = body.encode('utf-8')
            resp         = self.http.request(verb, url, headers=req_headers, body=encoded_data)

        return resp

    def create_issue(self, issue, issue_json):
        """Create new issue directly via JIRA 'issue' API"""
        url  = '{}/issue'.format(self.baseurl)
        resp = self.jira_http_call(url, 'POST', issue_json)
        json_loads = json.loads(resp.data.decode('utf-8'))
        if 'key' in json_loads:
            created_issue = Issue(
                IssueType.__dict__[issue.type.name.replace('-','')],
                json_loads['key'],
                issue.summary,
                issue.description
            )
            return created_issue
        return None

    def read_issue(self, issue_key): 
        """Read issue directly via JIRA 'issue' API"""
        url  = '{}/issue/{}?fields=summary,description,priority,issuetype'.format(self.baseurl, issue_key)
        resp = self.jira_http_call(url)
        json_loads = json.loads(resp.data.decode('utf-8'))
        if 'fields' in json_loads:
            fields = json_loads['fields']
            issue = Issue(
                IssueType.__dict__[fields['issuetype']['name'].replace('-','')],
                json_loads['key'],
                fields['summary'],
                fields['description']
            )
            return issue
        return None

    def update_issue(self, issue, issue_json):
        """Update existing issue directly via JIRA 'issue' API"""
        url  = '{}/issue/{}'.format(self.baseurl, issue.key)
        resp = self.jira_http_call(url, 'PUT', issue_json)
        if hasattr(resp, 'status') and resp.status == 204:
            updated_issue = Issue(
                IssueType.__dict__[issue.type.name.replace('-','')],
                issue.key,
                issue.summary,
                issue.description
            )
            return updated_issue
        return None

    def delete_issue(self, issue):
        """Delete issue directly via JIRA 'issue' API"""
        url  = '{}/issue/{}'.format(self.baseurl, issue.key)
        resp = self.jira_http_call(url, 'DELETE')
        return resp

    def find_issue(self, issue): 
        """Locate issue via JIRA 'search' API"""
        summary_encoded = issue.summary.replace('!','\\\\!')
        url         ='{}/search?jql=project={}+AND+summary~\"{}\"&fields=summary,description,priority,issuetype'.format(self.baseurl, self.args.JIRA_PROJECT_KEY, summary_encoded.replace(' ', '+'))
        resp        = self.jira_http_call(url)
        json_loads  = json.loads(resp.data.decode('utf-8'))
        found_issue = None

        if 'issues' in json_loads and len(json_loads['issues']) > 0: 
            found_issues = json_loads['issues']
            if len(found_issues) > 1:
                # Account for JQL `~` operator returning similar results
                actual_issue = [i for i in found_issues if i['fields']['summary'] == issue.summary][-1]
            else: 
                actual_issue = found_issues[-1]

            key    = actual_issue['key']
            fields = actual_issue['fields']
    
            found_issue =  Issue(
                # TODO: Learn magic, cleaner way to this
                IssueType.__dict__[fields['issuetype']['name'].replace('-','')],
                key,
                fields['summary'],
                fields['description']
            )
            return found_issue
        return None

    def parse_markdown(self):
        fh           = open(self.args.INFILE, 'r')
        lines        = fh.readlines()
        issues       = []
        issue_type   = IssueType.NONE
        parser_state = ParserState.DETECT_ISSUE
        summary      = None
        description  = ''

        for line in lines:
            stripped   = line.strip()
            issue_type = self.detect_issue(stripped)

            if issue_type is IssueType.Epic:
                summary = '{}'.format(re.sub(self.epic_re, '', stripped))
                stripped = 'EPIC FOUND: {}'.format(re.sub(self.epic_re, '', stripped))
            elif issue_type is IssueType.Story:
                summary = '{}'.format(re.sub(self.story_re, '', stripped))
                stripped = 'STORY FOUND: {}'.format(re.sub(self.story_re, '', stripped))
            elif issue_type is IssueType.Subtask:
                summary = '{}'.format(re.sub(self.subtask_re, '', stripped))
                stripped = 'Subtask FOUND: {}'.format(re.sub(self.subtask_re, '', stripped))

            if parser_state is ParserState.DETECT_ISSUE and issue_type in [IssueType.Epic, IssueType.Story, IssueType.Subtask]:
                issues.append(Issue(issue_type, '', summary))
                parser_state = ParserState.COLLECT_DESCRIPTION

            elif parser_state is ParserState.COLLECT_DESCRIPTION:
                if issue_type is IssueType.NONE:
                    issues[-1].description += '{}\n'.format(stripped)
                else:
                    self.process_issue(issues[-1])
                    issues.append(Issue(issue_type, '', summary))

            print ('XXX: {}'.format(stripped))

        # Process final issue
        self.process_issue(issues[-1])
        fh.close()

    def detect_issue(self, str):
        issue_type = IssueType.NONE

        if self.epic_re.match(str):
            issue_type = IssueType.Epic
        elif self.story_re.match(str):
            issue_type = IssueType.Story
        elif self.subtask_re.match(str):
            issue_type = IssueType.Subtask
        
        return issue_type

    def process_issue(self, issue): 
        remote_issue = self.find_issue(issue)
        if remote_issue != None:
            if remote_issue.type is IssueType.Epic:
                self.epic_id = remote_issue.key
            if remote_issue.type is IssueType.Story:
                self.parent_id = remote_issue.key
            issue.key = remote_issue.key

            issue_changed = self.diff_issue_against_remote(issue, remote_issue)
            if issue_changed is True:
                issue_data = self.prepare_issue(issue)
                self.update_issue(issue, issue_data)
                # TODO: Update issue cache
                self.update_issue_cache(issue)
            else:
                # * Check for description, etc changes
                issue_hash   = self.generate_issue_hash(issue.summary, issue.description)
                hashes_match = self.check_issue_cache_hash(issue.key, issue_hash)
                if hashes_match is False:
                    # * Update issues via JIRA API
                    issue_data = self.prepare_issue(issue)
                    self.update_issue(issue, issue_data)

                    # * Update issue cache
                    self.update_issue_cache(issue)
        else:
            # TODO: Create new issues
            issue_data   = self.prepare_issue(issue)
            create_issue = self.create_issue(issue, issue_data)

            if create_issue is not None and create_issue.type is IssueType.Epic:
                self.epic_id   = create_issue.key
            if create_issue is not None and create_issue.type is IssueType.Story:
                self.parent_id = create_issue.key
            # * Update issue cache
            self.update_issue_cache(create_issue)

    def diff_issue_against_remote(self, issue, remote_issue):
        """Determine if remote issue has changed since last local edit"""
        result = False

        if issue.summary != remote_issue.summary:
            result = True
        # TODO: Figure out what to do about need to strip() descriptions
        if issue.description.strip() != remote_issue.description:
            result = True

        return result

    def prepare_issue(self, issue): 
        """Prepare JSON data to send to JIRA API"""
        if hasattr(self.args, 'JIRA_PROJECT_KEY'):
            project_key = self.args.JIRA_PROJECT_KEY
        else:
            project_key = os.environ.get('JIRA_PROJECT_KEY')

        # Account for dash i.e '-' character in "Sub-task"
        issue_type = 'Sub-task' if issue.type is IssueType.Subtask else issue.type.name

        out_json    = {
            'fields': {
                'project': {
                    'key': project_key
                },
                'summary': issue.summary,
                'description': issue.description.strip(),
                'issuetype': {
                    'name': issue_type
                }
            }
        }

        if issue.type is IssueType.Epic:
            out_json['fields']['customfield_10011'] = issue.summary
        if issue.type is IssueType.Story and len(self.epic_id) > 0:
            out_json['fields']['customfield_10014'] = self.epic_id
        if issue.type is IssueType.Subtask and len(self.parent_id) > 0:
            out_json['fields']['parent'] = { 
                'key': self.parent_id
            } 

        return json.dumps(out_json)

    def generate_issue_hash(self, summary, description): 
        str    = '{}:{}'.format(summary, description.strip())
        result = hashlib.md5(str.encode())
        return result.hexdigest()

    def check_issue_cache_hash(self, issue_key, issue_hash):
        result = False
        with open('.md2jira_cache.py.tsv', 'r') as fh:
            for line in fh:
                key, summary, hash = '{}'.format(line.rstrip()).split('\t')
                print('YYY: {}'.format(line.rstrip()))
                if key == issue_key: 
                    result = (hash == issue_hash)
        return result

    def update_issue_cache(self, issue): 
        hash   = self.generate_issue_hash(issue.summary, issue.description)
        if self.check_issue_cache_hash(issue.key, hash) is False:
            # Temp file
            tmpfile = tempfile.NamedTemporaryFile()
            # Write everything _but_ changed issue out
            with open('.md2jira_cache.py.tsv', 'r') as fh:
                for line in fh:
                    if line.startswith(issue.key) is False:
                        tmpfile.write(bytes(line,'utf-8'))

            fields = [issue.key, '"{}"'.format(issue.summary), hash]
            tmpfile.write(bytes('{}\n'.format('\t'.join(fields)), 'utf-8'))
            os.rename(tmpfile.name, '.md2jira_cache.py.tsv')

class Issue:
    def __init__(self, type, key='', summary='', description=''):
        self.key         = key 
        self.type        = type
        self.summary     = summary
        self.description = description.strip()
        self.epic_id     = None
        self.parent_id   = None
        self.priority    = None
        self.assignee    = None

class IssueType(Enum):
    NONE    = 0
    Epic    = 1
    Story   = 2
    Subtask = 3

class ParserState(Enum):
    NONE                = 0 
    DETECT_ISSUE        = 1
    COLLECT_DESCRIPTION = 2
