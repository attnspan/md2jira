#!/bin/bash

DEBUG=1
INFILE=${1}
EPIC_ID=''
STORY_ID=''

SUMMARY_FOUND=0
EPIC_FOUND=0
STORY_FOUND=0
SUBTASK_FOUND=0
DESCRIPTION=''
CMD=''

# @see https://j.mp/3qAGH1q for WTF about the three slashes (plus spaces) below

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
        #DESCRIPTION="${DESCRIPTION}\\\\\ ${1}"
        DESCRIPTION+="${1}"
        DESCRIPTION+='\\ '
        return 1
    fi
}

while read "LINE"; do

    echo "LINE (${SUMMARY_FOUND}): ${LINE}"

    if [[ ${SUMMARY_FOUND} -eq 1 ]]; then
        get_description "${LINE}"
        RES=$?   
        if [[ ${RES} -eq 0 ]]; then
            #DESCRIPTION=$(echo "${DESCRIPTION}" | sed -e 's@[\]* \([[:alpha:]]\)@\1@g')
            DESCRIPTION=$(echo "${DESCRIPTION}" | sed -e 's@^[\]*\ \([[:alpha:]]\)@\1@g')
            CMD+=" -o description='"${DESCRIPTION}"'"
            if [[ ${SUBTASK_FOUND} -eq 1 ]]; then
                CMD+=" ${STORY_ID}"
            fi
            echo "${CMD}"
            RES=$(bash -c "${CMD}")
            if [[ ${STORY_FOUND} -eq 1 ]]; then
                STORY_ID=$(echo ${RES} | awk '{print $2}')
                echo "${RES}"
                echo "STORY_ID: ${STORY_ID}"
                STORY_FOUND=0
            elif [[ ${SUBTASK_FOUND} ]]; then
                SUBTASK_ID=$(echo ${RES} | awk '{print $2}')
                echo "SUBTASK_ID: ${SUBTASK_ID}"
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
        if [[ DEBUG -eq 1 ]]; then
            echo 'jira epic create --noedit -p DRT -o summary="'${EPIC}'" -o "epic-name"="'${EPIC}'"'
        else
            RES=$(jira epic create --noedit -p DRT -o summary="${EPIC}" -o "epic-name"="${EPIC}")
            EPIC_ID=$(echo ${RES} | awk '{print $2}')
            echo "RES: ${RES}"
            echo "EPIC_ID: ${EPIC_ID}"
        fi
    fi

    STORY_REX="^##[[:space:]]"
    if [[ ${LINE} =~ ${STORY_REX} ]]; then
        echo "Story: ${LINE}"
        STORY=$(echo ${LINE} | sed -e 's@'${STORY_REX}'@@')
        SUMMARY_FOUND=1
        STORY_FOUND=1
        if [[ DEBUG -eq 1 ]]; then
            CMD='jira create --noedit -p DRT -o summary="'${STORY}'"'
            [[ ! -z ${EPIC_ID} ]] && CMD="${CMD} -o \"epiclink\"=\"${EPIC_ID}\""
        else
            RES=$(jira create --noedit -p DRT -o summary="${STORY}" -o "epiclink"="${EPIC_ID}")
            STORY_ID=$(echo ${RES} | awk '{print $2}')
            echo "RES: ${RES}"
            echo "STORY_ID: ${STORY_ID}"
        fi
    fi

    SUBTASK_REX="^###[[:space:]]"
    if [[ ${LINE} =~ ${SUBTASK_REX} ]]; then
        echo "Subtask: ${LINE}"
        SUBTASK=$(echo ${LINE} | sed -e 's@'${SUBTASK_REX}'@@')
        SUMMARY_FOUND=1
        SUBTASK_FOUND=1
        if [[ DEBUG -eq 1 ]]; then
            CMD='jira subtask --noedit -p DRT -o summary="'${SUBTASK}'"'
        else	
            RES=$(jira subtask --noedit -p DRT -o summary="${SUBTASK}")
            SUBTASK_ID=$(echo ${RES} | awk '{print $2}')
            echo "RES: ${RES}"
            echo "SUBTASK_ID: ${SUBTASK_ID}"
        fi
    fi

done < ${INFILE}