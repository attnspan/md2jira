#!/usr/bin/env python

import os
import shutil
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

        self.args         = args
        self.baseurl      = 'https://{}.atlassian.net/rest/api/2'.format(os.environ.get('JIRA_PROJECT_SUBDOMAIN'))
        self.http         = urllib3.PoolManager(ca_certs=certifi.where())
        self.epic_re      = re.compile(r'^#\s+')
        self.story_re     = re.compile(r'^##\s+')
        self.subtask_re   = re.compile(r'^###\s+')
        self.checklist_re = re.compile(r'^\* \[(.*)\] (.*)$')
        self.epic_id      = ''
        self.parent_id    = ''

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
            if len(resp.data) > 0:
                json_loads   = json.loads(resp.data.decode('utf-8'))
                if 'errors' in json_loads:
                    for error in json_loads['errors']:
                        print('{}: {}'.format(error, json_loads['errors'][error]))

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
            if issue.type is IssueType.Story and hasattr(issue, 'epic_id'):
                created_issue.epic_id = issue.epic_id
            if issue.type is IssueType.Subtask and hasattr(issue, 'parent_id'):
                created_issue.parent_id = issue.parent_id
            return created_issue
        return None

    def read_issue(self, issue_key): 
        """Read issue directly via JIRA 'issue' API"""
        url  = '{}/issue/{}?fields=summary,description,priority,issuetype,customfield_10262'.format(self.baseurl, issue_key)
        resp = self.jira_http_call(url)
        json_loads = json.loads(resp.data.decode('utf-8'))
        if 'fields' in json_loads:
            fields = json_loads['fields']
            issue = Issue(
                IssueType.__dict__[fields['issuetype']['name'].replace('-','')],
                json_loads['key'],
                fields['summary'],
                fields['description'],
                fields['customfield_10262'] 
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
                issue.description,
                issue.checklist.text
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
        url         ='{}/search?jql=project={}+AND+summary~\"{}\"&fields=summary,description,priority,issuetype,customfield_10262'.format(self.baseurl, self.args.JIRA_PROJECT_KEY, summary_encoded.replace(' ', '+'))
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
                fields['description'],
                fields['customfield_10262'] 
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

                if issue_type is IssueType.Checklist:
                    if hasattr(issues[-1], 'checklist') is False:
                        issues[-1].checklist = Checklist()
                    matches = re.match(self.checklist_re, stripped)
                    status, item_text = matches.group(1, 2)
                    item   = ChecklistItem(item_text, status)
                    issues[-1].checklist.append(item)

                elif issue_type is IssueType.NONE:
                    issues[-1].description += '{}\n'.format(self.md2wiki(stripped))

                else:
                    self.process_issue(issues[-1])
                    issues.append(Issue(issue_type, '', summary))

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
        elif self.checklist_re.match(str):
            issue_type = IssueType.Checklist
        
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
                issue_hash   = self.generate_issue_hash(issue)
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

        if issue.checklist.text != remote_issue.checklist.text:
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
        
        if hasattr(issue, 'checklist') and len(issue.checklist.items) > 0:
            checklist_text = self.format_checklist(issue.checklist)
            out_json['fields']['customfield_10262'] = checklist_text

        return json.dumps(out_json)

    def md2wiki(self, str):
        """Convert certain markdown to JIRA Wiki format"""
        regex = {
            'link': re.compile(r'^(.*)\[([^\]]+)\]\(([^\)]+)\)(.*)$')
        }
        replacements = {
            'link': r'\1[\2|\3]\4'
        }

        for format in regex:
            matches = re.match(regex[format], str)
            if matches is not None:
                str     = re.sub(regex[format], replacements[format], str)
        return str

    def format_checklist(self, checklist):
        # @see https://is.gd/uhaViF
        '''
        # Default checklist
        * [open] Checklist Item A
        * [in progress] Checklist Item B
        * [done] Checklist Item C
        '''
        output = '# Default Checklist\n' # raw format


        for item in checklist.items:
            status = item.status.name.lower().replace('_', ' ')
            output += '* [{}] {}\n'.format(status, item.text)

        return output

    def generate_issue_hash(self, issue): 
        str    = '{}:{}:{}'.format(issue.summary, issue.description.strip(), issue.checklist.text.strip())
        result = hashlib.md5(str.encode())
        return result.hexdigest()

    def check_issue_cache_hash(self, issue_key, issue_hash):
        result = False
        with open('.md2jira_cache.py.tsv', 'r') as fh:
            for line in fh:
                key, summary, hash = '{}'.format(line.rstrip()).split('\t')
                if key == issue_key: 
                    result = (hash == issue_hash)
        return result

    def update_issue_cache(self, issue): 
        hash = self.generate_issue_hash(issue)
        if self.check_issue_cache_hash(issue.key, hash) is False:
            # Temp file
            tmpfile = tempfile.NamedTemporaryFile(delete=False)
            # Write everything _but_ changed issue out
            with open('.md2jira_cache.py.tsv', 'r') as fh:
                for line in fh:
                    if line.startswith(issue.key) is False:
                        tmpfile.write(bytes(line,'utf-8'))

                fields = [issue.key, '"{}"'.format(issue.summary), hash]
                tmpfile.write(bytes('{}\n'.format('\t'.join(fields)), 'utf-8'))
                shutil.copyfile(tmpfile.name, '{}/{}'.format(os.getcwd(), '.md2jira_cache.py.tsv'))

class Issue:
    def __init__(self, type, key='', summary='', description='', checklist_text=''):
        self.key            = key 
        self.type           = type
        self.summary        = summary
        self.description    = description.strip()
        self.checklist      = Checklist(checklist_text)
        self.checklist_re   = re.compile(r'^\* \[(.*)\] (.*)$')
        self.epic_id        = None
        self.parent_id      = None
        self.priority       = None
        self.assignee       = None

        if checklist_text is None:
            checklist_text = ''

        if checklist_text and len(checklist_text) > 0: 
            self.checklist = self.process_checklist(checklist_text)

    def process_checklist(self, str):
        """Convert checklist str in to checklist"""

        # Ignore first line, which is just name of the checklist
        for item in str.rstrip().split('\n')[1:]:
            matches = re.match(self.checklist_re, item.rstrip())
            status, item_text = matches.group(1, 2)
            checklist_item   = ChecklistItem(item_text, status)
            self.checklist.append(checklist_item)

        return self.checklist

class IssueType(Enum):
    NONE      = 0
    Epic      = 1
    Story     = 2
    Subtask   = 3
    Checklist = 4

class ParserState(Enum):
    NONE                = 0 
    DETECT_ISSUE        = 1
    COLLECT_DESCRIPTION = 2
    COLLECT_CHECKLIST   = 3

class Checklist:
    def __init__(self, str):
        self.items  = []
        self.text   = str
    def __repr__(self):
        result = MD2Jira.format_checklist(self, self)
        return result
    def append(self, item):
        self.items.append(item)
        self.text = repr(self)

class ChecklistItem:
        
    def __init__(self, text, status):
        self.shorthand_mapping = {
            'x': 'DONE',
            ' ': 'OPEN',
            '>': 'IN_PROGRESS'
        }
        self.text    = text
        self.status  = ChecklistItemStatus.__dict__[self.shorthand_mapping[status].upper() if status in self.shorthand_mapping.keys() else status.replace(' ', '_').upper()]
        try: 
            self.checked = self.status == ChecklistItemStatus.DONE
        except:
            print ('yay')

class ChecklistItemStatus(Enum):

    NONE        = 0
    OPEN        = 1
    IN_PROGRESS = 2
    SKIPPED     = 3
    DONE        = 4