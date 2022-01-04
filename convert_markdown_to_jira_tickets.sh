#!/bin/bash

DEBUG=${DEBUG:-1}
INFILE=${1}
PROJECT=${2:-'DRT'}
EPIC_ID=''
STORY_ID=''

SUMMARY_FOUND=0
EPIC_FOUND=0
STORY_FOUND=0
SUBTASK_FOUND=0
DESCRIPTION=''
CMD=''


find_issue() {
    local SUMMARY=$(echo ${1} | tr ' ' '+')
    local TOTAL=0
    local KEY=''

    CMD="./jira_api_get.sh 'search?jql=project=${PROJECT}+AND+summary~\"${SUMMARY}\"&fields=summary,description' | jq -r '[.total,.issues[].key] | @csv' 2>/dev/null | awk -F, '{print \$1, \$2}'"
    read TOTAL KEY <<< $(bash -c "${CMD}")
    if [ ! -z ${KEY} ]; then
        KEY=$(echo ${KEY} | tr -d '"')
    fi
    local RES=$?
    echo ${TOTAL} ${KEY}
}

get_issue() {
    local KEY=${1}
    local SUMMARY=''
    local DESCRIPTION=''
    local PRIORITY=''

    CMD="./jira_api_get.sh 'issue/${KEY}?fields=summary,description,priority'"
    ISSUE_JSON=$(bash -c "${CMD}")
    RES=$?

    if [ ${RES} -eq 0 ]; then
        SUMMARY=$(echo ${ISSUE_JSON} | jq -r '.fields.summary')
        DESCRIPTION=$(echo ${ISSUE_JSON} | jq -r '.fields.description')
        PRIORITY=$(echo ${ISSUE_JSON} | jq '.fields.priority.name')
    fi

    echo -E "${SUMMARY}" "${DESCRIPTION}" ${PRIORITY}

}

prepare_epic() {
    local PROJECT=${1:-DRT}
    local SUMMARY=${2}
    local DESCRIPTION=${3}

    TMPFILE=$(mktemp)
    cat data_epic.json.in | sed \
    -e 's@{{PROJECT}}@'${PROJECT}'@g' \
    -e 's@{{SUMMARY}}@'"${SUMMARY}"'@g' \
    -e 's@{{DESCRIPTION}}@'"${DESCRIPTION}"'@g' >> "${TMPFILE}"

    echo "${TMPFILE}"
}

prepare_story() {
    local PROJECT=${1:-DRT}
    local EPIC_ID=${2}
    local SUMMARY=${3}
    local DESCRIPTION=${4}

    TMPFILE=$(mktemp)
    cat data_story.json.in | sed \
    -e 's@{{PROJECT}}@'${PROJECT}'@g' \
    -e 's@{{EPIC_ID}}@'${EPIC_ID}'@g' \
    -e 's@{{SUMMARY}}@'"${SUMMARY}"'@g' \
    -e 's@{{DESCRIPTION}}@'"${DESCRIPTION}"'@g' >> "${TMPFILE}"

    echo "${TMPFILE}"
}

prepare_subtask() {
    local PROJECT=${1:-DRT}
    local PARENT_ID=${2}
    local SUMMARY=${3}
    local DESCRIPTION=${4}

    TMPFILE=$(mktemp)
    cat data_subtask.json.in | sed \
    -e 's@{{PROJECT}}@'${PROJECT}'@g' \
    -e 's@{{PARENT_ID}}@'${PARENT_ID}'@g' \
    -e 's@{{SUMMARY}}@'"${SUMMARY}"'@g' \
    -e 's@{{DESCRIPTION}}@'"${DESCRIPTION}"'@g' >> "${TMPFILE}"

    echo "${TMPFILE}"
}

detect_issue() {
    local LINE=${1}
    EPIC_REX="^#[[:space:]]"
    STORY_REX="^##[[:space:]]"
    SUBTASK_REX="^###[[:space:]]"

    if [[ ${LINE} =~ ${EPIC_REX} ]]; then
        EPIC_FOUND=1
        return 0
    elif [[ ${LINE} =~ ${STORY_REX} ]]; then
        STORY_FOUND=1
        return 0
    elif [[ ${LINE} =~ ${SUBTASK_REX} ]]; then
        SUBTASK_FOUND=1
        return 0
    fi

    return 1
}

get_description() {
    EOD_REX="^---$"
    if [[ ${1} =~ ${EOD_REX} ]]; then
        SUMMARY_FOUND=0
        return 0
    else
        DESCRIPTION+="${1}"
        DESCRIPTION+='\\n'
        return 1
    fi
}

generate_issue_hash() {

    local SUMMARY=${1}
    local DESCRIPTION=${2}
    local ISSUE_HASH=''

    ISSUE_HASH=$(echo -n "${SUMMARY}:${DESCRIPTION}" | md5 | tr -d '\n')
    echo -e ${ISSUE_HASH} 
}

check_issue_cache_hash() {
    local ISSUE_KEY=${1}
    local ISSUE_HASH=${2}

    if [ "$(grep ${ISSUE_KEY} .md2jira_cache.tsv | awk '{print $NF}' 2>/dev/null)" = "${ISSUE_HASH}" ]; then
        return 0
    else
        return 1 
    fi

}

update_issue_cache() {
    local ISSUE_KEY=${1}
    local SUMMARY=${2}
    local DESCRIPTION=${3}
    local ISSUE_CACHE_FILE='./.md2jira_cache.tsv'
    local TMP_ISSUE_CACHE_FILE=$(mktemp)

    ISSUE_HASH=$(generate_issue_hash "${SUMMARY}" "${DESCRIPTION}")

    [ ! -f .md2jira_cache.tsv ] && touch ${ISSUE_CACHE_FILE}
    # If issue already exists
    if check_issue_cache_hash ${ISSUE_KEY} ${ISSUE_HASH}; then
        echo "Issue ${ISSUE_KEY}: ${SUMMARY} already cached and unchanged, skipping ..."
    else
        # Swap temp cache file with current
        cat ${ISSUE_CACHE_FILE} | grep -v ${ISSUE_KEY} > ${TMP_ISSUE_CACHE_FILE}
        echo -e "${ISSUE_KEY}\t\"${SUMMARY}\"\t${ISSUE_HASH}" >> ${TMP_ISSUE_CACHE_FILE}
        mv ${TMP_ISSUE_CACHE_FILE} ${ISSUE_CACHE_FILE}
    fi
}

while read "LINE"; do

    if [[ ${SUMMARY_FOUND} -eq 1 ]]; then
        if get_description "${LINE}"; then
            # TODO: Remember what this regex does
            DESCRIPTION=$(echo "${DESCRIPTION}" | sed -e 's@^[\]*\ \([[:alpha:]]\)@\1@g')

            read KEYS_FOUND KEY <<< $(find_issue "${SUMMARY}")

            if [[ ${KEYS_FOUND} = 1 ]]; then
                # Double check for remote update 
                TEST=$(get_issue ${KEY})
                echo "TEST: ${TEST}"
                #get_issue ${KEY}

                if [[ "${UPSTREAM_SUMMARY}" != "${SUMMARY}" ]]; then
                    echo "SUMMARY MISMATCH for ${KEY}"
                    echo "U: ${UPSTREAM_SUMMARY}"
                    echo "L: ${SUMMARY}"
                fi

                # Check if DESCRIPTION has been updated
                ISSUE_HASH=$(generate_issue_hash "${SUMMARY}" "${DESCRIPTION}")
                if check_issue_cache_hash ${KEY} ${ISSUE_HASH}; then
                    echo "${KEY} hash MATCH ... ${ISSUE_HASH}"
                else
                    echo "${KEY} hash MISMATCH ... ${ISSUE_HASH}"
                    # TODO: START_HERE_NEXT
                    # 1. Update JIRA issue with new description

                    # 2. Update issue cache
                    update_issue_cache ${KEY} "${SUMMARY}" "${DESCRIPTION}"
                fi
            else
                if [[ ${STORY_FOUND} -eq 1 ]]; then
                    # TODO: Deal with next line assuming EPIC_ID exists
                    STORY_TMPFILE=$(prepare_story ${PROJECT} ${EPIC_ID} "${SUMMARY}" "${DESCRIPTION}")
                    RES=$(bash -c "./jira_api_post.sh ${STORY_TMPFILE}")
                    STORY_ID=$(echo ${RES} | jq -r '.key')
                    echo "STORY_ID: ${STORY_ID}"
                    STORY_FOUND=0
                elif [[ ${SUBTASK_FOUND} -eq 1 ]]; then
                    SUBTASK_TMPFILE=$(prepare_subtask ${PROJECT} ${STORY_ID} "${SUMMARY}" "${DESCRIPTION}")
                    RES=$(bash -c "./jira_api_post.sh ${SUBTASK_TMPFILE}")
                    SUBTASK_ID=$(echo ${RES} | jq -r '.key')
                    echo "SUBTASK_ID: ${SUBTASK_ID}"
                    SUBTASK_FOUND=0
                fi
            fi
            SUMMARY_FOUND=0
        fi
    else
        DESCRIPTION=''
    fi

    if detect_issue "${LINE}"; then
        if [[ ${EPIC_FOUND} -eq 1 ]]; then
            EPIC=$(echo ${LINE} | sed -e 's@'${EPIC_REX}'@@')
            echo "Epic: ${EPIC}"
            TMP_DESCRIPTION="fooey_desc"

            read KEYS_FOUND KEY <<< $(find_issue "${EPIC}")

            if [[ ${KEYS_FOUND} = 0 ]]; then
                echo "EPIC NOT FOUND"
                EPIC_TMPFILE=$(prepare_epic ${PROJECT} "${EPIC}" "${TMP_DESCRIPTION}")
                echo "EPIC_TMPFILE: ${EPIC_TMPFILE}"
                RES=$(bash -c "./jira_api_post.sh ${EPIC_TMPFILE}")
                EPIC_ID=$(echo ${RES} | jq -r '.key')
                echo "RES: ${RES}"
                echo "EPIC_ID: ${EPIC_ID}"
            else 
                echo "Epic \"${KEY}: ${EPIC}\" found, skipping ..."
                # Write md5 of ticket to cache
                update_issue_cache ${KEY} "${EPIC}" "${TMP_DESCRIPTION}"
            fi

            EPIC_FOUND=0
        fi
    fi

    STORY_REX="^##[[:space:]]"
    if [[ ${LINE} =~ ${STORY_REX} ]]; then
        echo "Story: ${LINE}"
        SUMMARY=$(echo ${LINE} | sed -e 's@'${STORY_REX}'@@')
        SUMMARY_FOUND=1
        STORY_FOUND=1
    fi

    SUBTASK_REX="^###[[:space:]]"
    if [[ ${LINE} =~ ${SUBTASK_REX} ]]; then
        echo "Subtask: ${LINE}"
        SUMMARY=$(echo ${LINE} | sed -e 's@'${SUBTASK_REX}'@@')
        SUMMARY_FOUND=1
        SUBTASK_FOUND=1
    fi

done < "${INFILE}"