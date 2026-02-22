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

        # Local environment supercedes .env file
        load_dotenv(override=True)

        subdomain         = os.environ.get('JIRA_PROJECT_SUBDOMAIN')
        domain            = os.environ.get('JIRA_DOMAIN')
        domain            = domain if domain is not None else 'atlassian.net'
        checklist_field   = os.environ.get('JIRA_CHECKLIST_CUSTOMFIELD')

        if hasattr(args, 'JIRA_PROJECT_KEY') and args.JIRA_PROJECT_KEY is not None:
            self.PROJECT_KEY = args.JIRA_PROJECT_KEY
        else:
            self.PROJECT_KEY  = os.environ.get('JIRA_PROJECT_KEY')


        self.args         = args
        self.baseurl      = f'https://{subdomain}.{domain}/rest/api/2'
        self.http         = urllib3.PoolManager(ca_certs=certifi.where())
        self.epic_re      = re.compile(r'^#\s+')
        self.story_re     = re.compile(r'^##\s+')
        self.task_re      = re.compile(r'^##\s+')
        self.subtask_re   = re.compile(r'^###\s+')
        self.checklist_re = re.compile(r'^\* \[(.*)\] (.*)$')
        self.epic_id      = ''
        self.parent_id    = ''

        self.checklist_custom_field = os.environ.get('JIRA_CHECKLIST_CUSTOMFIELD')
        self.checklist_enabled      = self.checklist_custom_field is not None
        self.wba_team               = os.environ.get('JIRA_WBA_TEAM')

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
        errorMessages = json_loads['errorMessages'] if 'errorMessages' in json_loads else None
        errors = json_loads['errors'] if 'errors' in json_loads else None
        if errorMessages and len(errorMessages) > 0:
            print ('The following errors occurred:')
            print (f'{json_loads["errorMessages"][0]}')
        elif errors and len(errors) > 0:
            print ('The following errors occurred:')
            print (f'{json_loads["errors"]}')
        elif 'key' in json_loads:
            created_issue = Issue(
                IssueType.__dict__[issue.type.name.replace('-','')],
                json_loads['key'],
                issue.summary,
                issue.description,
                issue.checklist.text or ''

            )
            if issue.type is IssueType.Task and hasattr(issue, 'epic_id'):
                created_issue.epic_id = issue.epic_id
            if issue.type is IssueType.Subtask and hasattr(issue, 'parent_id'):
                created_issue.parent_id = issue.parent_id
            issue_key = json_loads['key']
            print (
                f'Created issue {issue_key}: https://wbinsights.atlassian.net/browse/{issue_key}'
            )
            return created_issue
        return None

    def read_issue(self, issue_key): 
        """Read issue directly via JIRA 'issue' API"""
        fields = 'summary,description,priority,issuetype'
        if self.checklist_custom_field:
            fields += f',{self.checklist_custom_field}'
        url  = '{}/issue/{}?fields={}'.format(self.baseurl, issue_key, fields)
        resp = self.jira_http_call(url)
        json_loads = json.loads(resp.data.decode('utf-8'))
        if 'fields' in json_loads:
            fields = json_loads['fields']
            issue = Issue(
                IssueType.__dict__[fields['issuetype']['name'].replace('-','')],
                json_loads['key'],
                fields['summary'],
                fields['description'],
                fields[self.checklist_custom_field] if self.checklist_enabled else ''
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
            print("{} updated".format(issue.key))
            return updated_issue
        else:
            print("{} NOT updated".format(issue.key))
        return None

    def delete_issue(self, issue):
        """Delete issue directly via JIRA 'issue' API"""
        url  = '{}/issue/{}'.format(self.baseurl, issue.key)
        resp = self.jira_http_call(url, 'DELETE')
        return resp

    def find_issue(self, issue): 
        """Locate issue via JIRA 'search' API"""
        summary_encoded = issue.summary.replace('!','\\\\!')
        summary_encoded = summary_encoded.replace('-','\\\\-')
        
        # Build the fields list - only include checklist field if it's configured
        fields = 'summary,description,priority,issuetype'
        if self.checklist_custom_field:
            fields += f',{self.checklist_custom_field}'
            
        # Use API v3 search/jql endpoint (v2 has been deprecated)
        api_v3_base = self.baseurl.replace('/rest/api/2', '/rest/api/3')
        url = f'{api_v3_base}/search/jql?jql=project={self.PROJECT_KEY}+AND+summary~"{summary_encoded.replace(" ", "+")}"&fields={fields}'
        
        resp        = self.jira_http_call(url)
        json_loads  = json.loads(resp.data.decode('utf-8'))
        found_issue = None

        if 'issues' in json_loads and len(json_loads['issues']) > 0:
            found_issues      = json_loads['issues']
            actual_issue_list = [i for i in found_issues if i['fields']['summary'] == issue.summary]
            if len(actual_issue_list) == 0:
                return None

            actual_issue      = actual_issue_list[0]
            key    = actual_issue['key']
            fields = actual_issue['fields']

            # Handle checklist field safely
            checklist_data = ""
            if self.checklist_custom_field and self.checklist_custom_field in fields:
                checklist_data = fields[self.checklist_custom_field]
    
            # More robust issue type mapping
            issue_type_name = fields['issuetype']['name']
            issue_type_clean = issue_type_name.replace('-','').replace(' ', '')
            
            # Try to find the matching IssueType
            try:
                issue_type = IssueType.__dict__[issue_type_clean]
            except KeyError:
                # Fallback for common mappings
                type_mapping = {
                    'SubTask': IssueType.Subtask,
                    'Task': IssueType.Task,
                    'Epic': IssueType.Epic,
                    'Story': IssueType.Story
                }
                issue_type = type_mapping.get(issue_type_clean, IssueType.Task)
            
            # Handle description field - it might be a dict with content
            description = fields.get('description', '')
            if isinstance(description, dict):
                # Simple extraction for now - just convert dict to string
                description = str(description)
            elif description is None:
                description = ''
                
            found_issue =  Issue(
                issue_type,
                key,
                fields['summary'],
                description,
                checklist_data 
            )
            return found_issue
        return None

    def parse_markdown(self):
        fh           = open(self.args.INFILE, 'r', encoding='utf-8')
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
            elif issue_type is IssueType.Task:
                summary = '{}'.format(re.sub(self.task_re, '', stripped))
                stripped = 'STORY FOUND: {}'.format(re.sub(self.task_re, '', stripped))
            elif issue_type is IssueType.Subtask:
                summary = '{}'.format(re.sub(self.subtask_re, '', stripped))
                stripped = 'Subtask FOUND: {}'.format(re.sub(self.subtask_re, '', stripped))

            if parser_state is ParserState.DETECT_ISSUE and issue_type in [IssueType.Epic, IssueType.Task, IssueType.Subtask]:
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

    def detect_issue(self, _str):
        issue_type = IssueType.NONE

        if self.epic_re.match(_str):
            issue_type = IssueType.Epic
        elif self.task_re.match(_str):
            issue_type = IssueType.Task
        elif self.subtask_re.match(_str):
            issue_type = IssueType.Subtask
        elif self.checklist_enabled and self.checklist_re.match(_str):
            issue_type = IssueType.Checklist

        return issue_type

    def process_issue(self, issue):
        remote_issue = self.find_issue(issue)
        if remote_issue != None:
            if remote_issue.type is IssueType.Epic:
                self.epic_id = remote_issue.key
            if remote_issue.type is IssueType.Task:
                self.parent_id = remote_issue.key
            issue.key = remote_issue.key
            issue.type = remote_issue.type

            issue_changed = self.diff_issue_against_remote(issue, remote_issue)
            if issue_changed is True:
                issue_data = self.prepare_issue(issue, updating=True)
                self.update_issue(issue, issue_data)
                # TODO: Update issue cache
                self.update_issue_cache(issue)
            else:
                print ("{}: \"{}\" up to date, skipping".format(issue.key, issue.summary))
        else:
            # TODO: Create new issues
            issue_data   = self.prepare_issue(issue)
            create_issue = self.create_issue(issue, issue_data)

            if create_issue is not None:
                if create_issue is not None and create_issue.type is IssueType.Epic:
                    self.epic_id   = create_issue.key
                if create_issue is not None and create_issue.type is IssueType.Task:
                    self.parent_id = create_issue.key
                # * Update issue cache
                self.update_issue_cache(create_issue)
            else:
                print('ERROR: unable to create "{}"'.format(issue.summary))

    def diff_issue_against_remote(self, issue, remote_issue):
        """Determine if remote issue has changed since last local edit"""
        result = False

        if issue.summary != remote_issue.summary:
            result = True

        """Convert certain to JIRA Wiki format to Markdown"""
        regex = {
            'link': re.compile(r'^(.*)\[([^|]+)\|([^\]]+)\](.*)$')
        }
        replacements = {
            'link': r'\1[\2](\3)\4'
        }

        # for format in regex:
        #     matches = re.match(regex[format], str)
        #     if matches is not None:
        #         str     = re.sub(regex[format], replacements[format], str)
        # return str

        wiki2md = []
        lines = issue.description.strip().split('\n')
        for line in lines:
            for format in regex:
                matches = re.match(regex[format], line)
                if matches is not None:
                    line = re.sub(regex[format], replacements[format], line)
            wiki2md.append(line.rstrip())
        
        remote_issue.description = str(remote_issue.description or '')
        if issue.description.strip() != remote_issue.description:
            result = True

        remote_issue.checklist.text = str(remote_issue.checklist.text or '')
        if issue.checklist.text != remote_issue.checklist.text:
            result = True

        return result

    def prepare_issue(self, issue, updating=False):
        """Prepare JSON data to send to JIRA API"""
        project_key = self.PROJECT_KEY

        # Account for dash i.e '-' character in "Sub-task"
        issue_type = 'Sub-Task' if issue.type is IssueType.Subtask else issue.type.name

        out_json    = {
            'fields': {
                'project': {
                    'key': project_key
                },
                'summary': issue.summary,
                'description': issue.description.strip(),
                #'components': [{"name": "App Services"}],
                'issuetype': {
                    'name': issue_type
                }
            }
        }

        if issue.type is IssueType.Epic:
            out_json['fields']['customfield_10011'] = issue.summary
        if issue.type is IssueType.Task and len(self.epic_id) > 0:
            out_json['fields']['customfield_10014'] = self.epic_id
        if issue.type is IssueType.Subtask and len(self.parent_id) > 0:
            out_json['fields']['parent'] = {
                'key': self.parent_id
            }

        if not updating and self.wba_team:
            out_json['fields']['customfield_10032'] = {
                'value': self.wba_team
            }

        if hasattr(issue, 'checklist') and len(issue.checklist.items) > 0:
            if self.checklist_enabled is False:
                for item in issue.checklist.items:
                    out_json['fields']['description'] += '\n{}'.format(item.text)
            else:
                checklist_text = self.format_checklist(issue.checklist)
                out_json['fields'][self.checklist_custom_field] = checklist_text

        return json.dumps(out_json)

    def md2wiki(self, _str):
        """Convert certain markdown to JIRA Wiki format"""
        text_replacements = {
            'link': {
                'match': re.compile(r'^(.*)\[([^\]]+)\]\(([^\)]+)\)(.*)$'),
                'pattern': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
                'replacement': r'[\1|\2]'
            }
        }

        for _token_type, _replacement_info in text_replacements.items():
            _match, _pattern, _replacement = _replacement_info.values()
            matches = re.match(_match, _str)
            if matches is not None:
                _str = _pattern.sub(_replacement, _str)

        return _str

    def wiki2md(self, issue):
        """Convert JIRA issue to Markdown"""
        output = []
        # Print Summmary w/ right header level based on IssueType
        issue_type_value      = issue.type.value
        issue_type_header_str = '#' * issue_type_value
        output.append('{} {}\n'.format(issue_type_header_str, issue.summary).rstrip())

        # Print description
        output.append('{}\n'.format(issue.description))

        # Print formatted checklist if exists
        items = issue.checklist and issue.checklist.items
        if items and len(items) > 0:
            for item in items:
                status = item.status.name
                output.append('* [{}] {}'.format(item.reverse_mapping[status], item.text))
            
        # Overwrite original file, backing up original

        result = '\n'.join(output) 

        print(result)

        return result


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
        cache_file = '.md2jira_cache.py.tsv'
        if os.path.exists(cache_file) is False:
            open(cache_file, 'a', encoding='utf-8').close()

        with open(cache_file, 'r', encoding='utf-8') as fh:
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
        self.description    = description and description.strip()
        self.checklist      = Checklist(checklist_text)
        self.checklist_re   = re.compile(r'^.*\* \[(.*)\] (.*)$')
        self.epic_id        = None
        self.parent_id      = None
        self.priority       = None
        self.assignee       = None

        if checklist_text is None:
            checklist_text = ''

        # Only process checklist if it's a string (not a dict from Jira API)
        if checklist_text and len(str(checklist_text)) > 0 and isinstance(checklist_text, str): 
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
    Task      = 3
    Subtask   = 4
    SubTask   = 5
    Checklist = 6
    WBAAccessRequest = 7
    Defect = 8

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

        if status == '' or len(status) == 0:
            status = ' '

        self.shorthand_mapping = {
            'x': 'DONE',
            ' ': 'OPEN',
            '>': 'IN_PROGRESS'
        }

        self.reverse_mapping = {}
        for v in self.shorthand_mapping:
            self.reverse_mapping[self.shorthand_mapping[v]] = v

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