#!/bin/bash

DEBUG=1
INFILE=${1}
EPIC_ID=''
STORY_ID=''

SUMMARY_FOUND=0
DESCRIPTION=''

# @see https://j.mp/3qAGH1q for WTF about the three slashes (plus spaces) below

get_description() {
    EOD_REX="^---$"
    if [[ ${1} =~ ${EOD_REX} ]]; then
        printf "${DESCRIPTION}\\\ "
        SUMMARY_FOUND=0
        return 0
    else
        [[ ! -z ${1} ]] && DESCRIPTION="${DESCRIPTION}\\\ ${1}"
        return 1
    fi
}

while read "LINE"; do

    if [[ ${SUMMARY_FOUND} -eq 1 ]]; then
        get_description "${LINE}"
        RES=$?   
        if [[ ${RES} -eq 0 ]]; then
            jira create --noedit -p DRT -o summary="GCore CDN" -o description="${DESCRIPTION}"
            exit 0
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
        if [[ DEBUG -eq 1 ]]; then
            echo 'jira create --noedit -p DRT -o summary="'${STORY}'" -o "epiclink"="'${EPIC_ID}'"'
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
        if [[ DEBUG -eq 1 ]]; then
            echo 'jira subtask --noedit -p DRT -o summary="'${SUBTASK}'" ${STORY_ID}'
        else	
            RES=$(jira subtask --noedit -p DRT -o summary="${SUBTASK}" ${STORY_ID})
            SUBTASK_ID=$(echo ${RES} | awk '{print $2}')
            echo "RES: ${RES}"
            echo "SUBTASK_ID: ${SUBTASK_ID}"
        fi
    fi

done < ${INFILE}