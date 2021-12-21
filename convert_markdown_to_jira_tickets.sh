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

# @see https://j.mp/3qAGH1q for WTF about the three slashes (plus spaces) below

find_issue() {
    local SUMMARY=$(echo ${1} | tr ' ' '+')
    local TOTAL=0
    local KEY=''

    CMD="./jira_api_get.sh 'search?jql=project=${PROJECT}+AND+summary~\"${SUMMARY}\"&fields=summary' | jq -r '[.total,.issues[].key] | @csv' 2>/dev/null | awk -F, '{print \$1, \$2}'"
    read TOTAL KEY <<< $(bash -c "${CMD}")
    if [ ! -z ${KEY} ]; then
        KEY=$(echo ${KEY} | tr -d '"')
    fi
    local RES=$?
    #echo "RES: ${RES}, TOTAL: ${TOTAL}, KEY: "$(echo ${KEY} | tr -d '"')
    echo ${TOTAL} ${KEY}
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
    local EPIC_REX="^#[[:space:]]"
    local STORY_REX="^##[[:space:]]"
    local SUBTASK_REX="^###[[:space:]]"

    if [[ ${LINE} =~ ${EPIC_REX} ]]; then
        EPIC_FOUND=1
    elif [[ ${LINE} =~ ${STORY_REX} ]]; then
        STORY_FOUND=1
    elif [[ ${LINE} =~ ${SUBTASK_REX} ]]; then
        SUBTASK_FOUND=1
    fi
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

while read "LINE"; do

    # echo "LINE (${SUMMARY_FOUND}): ${LINE}"

    if [[ ${SUMMARY_FOUND} -eq 1 ]]; then
        get_description "${LINE}"
        RES=$?   
        if [[ ${RES} -eq 0 ]]; then
            DESCRIPTION=$(echo "${DESCRIPTION}" | sed -e 's@^[\]*\ \([[:alpha:]]\)@\1@g')

            if [[ ${STORY_FOUND} -eq 1 ]]; then

                read KEYS_FOUND KEY <<< $(find_issue "${STORY}")
                
                if [[ ${KEYS_FOUND} = 0 ]]; then
                    STORY_TMPFILE=$(prepare_story ${PROJECT} ${EPIC_ID} "${STORY}" "${DESCRIPTION}")
                    RES=$(bash -c "./test_cli.sh ${STORY_TMPFILE}")
                    STORY_ID=$(echo ${RES} | jq -r '.key')
                    echo "${RES}"
                    echo "STORY_ID: ${STORY_ID}"
                else 
                    echo "Story \"${KEY}: ${STORY}\" found, skipping ..."
                fi

                STORY_FOUND=0

            elif [[ ${SUBTASK_FOUND} ]]; then

                read KEYS_FOUND KEY <<< $(find_issue "${SUBTASK}")
                
                if [[ ${KEYS_FOUND} = 0 ]]; then
                    SUBTASK_TMPFILE=$(prepare_subtask ${PROJECT} ${STORY_ID} "${SUBTASK}" "${DESCRIPTION}")
                    echo "SUBTASK_TMPFILE: ${SUBTASK_TMPFILE}"
                    RES=$(bash -c "./test_cli.sh ${SUBTASK_TMPFILE}")
                    SUBTASK_ID=$(echo ${RES} | jq -r '.key')
                    echo "SUBTASK_ID: ${SUBTASK_ID}"
                else 
                    echo "Sub-task \"${KEY}: ${SUBTASK}\" found, skipping ..."
                fi

                SUBTASK_FOUND=0

            fi
            SUMMARY_FOUND=0
        fi
    else
        DESCRIPTION=''
    fi

    EPIC_REX="^#[[:space:]]"
    if [[ ${LINE} =~ ${EPIC_REX} ]]; then
        EPIC=$(echo ${LINE} | sed -e 's@'${EPIC_REX}'@@')
        echo "Epic: ${EPIC}"

        read KEYS_FOUND KEY <<< $(find_issue "${EPIC}")

        if [[ ${KEYS_FOUND} = 0 ]]; then
            echo "EPIC NOT FOUND"
            EPIC_TMPFILE=$(prepare_epic ${PROJECT} "${EPIC}" "fooey_desc")
            echo "EPIC_TMPFILE: ${EPIC_TMPFILE}"
            RES=$(bash -c "./test_cli.sh ${EPIC_TMPFILE}")
            EPIC_ID=$(echo ${RES} | jq -r '.key')
            echo "RES: ${RES}"
            echo "EPIC_ID: ${EPIC_ID}"
        else 
            echo "EPIC \"${KEY}: ${EPIC}\" FOUND"
        fi
        
    fi

    STORY_REX="^##[[:space:]]"
    if [[ ${LINE} =~ ${STORY_REX} ]]; then
        echo "Story: ${LINE}"
        STORY=$(echo ${LINE} | sed -e 's@'${STORY_REX}'@@')
        SUMMARY_FOUND=1
        STORY_FOUND=1
    fi

    SUBTASK_REX="^###[[:space:]]"
    if [[ ${LINE} =~ ${SUBTASK_REX} ]]; then
        echo "Subtask: ${LINE}"
        SUBTASK=$(echo ${LINE} | sed -e 's@'${SUBTASK_REX}'@@')
        SUMMARY_FOUND=1
        SUBTASK_FOUND=1
    fi

done < "${INFILE}"