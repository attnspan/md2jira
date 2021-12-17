#!/bin/bash
FILE=${1:-data.json}
curl -s \
   -X POST \
   -H "Authorization: Basic ZGFuQGRlY2FnYW1lcy5jb206ZGpRaTVlYjdPTDZZOVdiRVpXSncxRkFG" \
   -H "Content-Type: application/json" \
   -d "@${FILE}" \
    "https://decagamesx.atlassian.net/rest/api/2/issue"