import os
import src.md2jira as md2jira
import argparse



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
args = parser.parse_args()

if __name__=="__main__":
    main()