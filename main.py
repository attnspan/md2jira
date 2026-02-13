import argparse
from src import md2jira

def main():
    """MD2Jira: Convert Markdown into corresponding JIRA issues"""
    md2j = md2jira.MD2Jira(args)
    md2j.parse_markdown()

parser = argparse.ArgumentParser(description=main.__doc__)

parser.add_argument('-i', dest='INFILE', type=str, help='Input markdown file', required=True)
parser.add_argument('-p',
    dest='JIRA_PROJECT_KEY',
    help='"KEY" of target JIRA project',
    type=str
)
parser.add_argument('-v', '--verbose',
    action='store_true',
    default=False,
    help='Enable verbose output (show diff details during update detection)'
)
args = parser.parse_args()

if __name__=="__main__":
    main()
