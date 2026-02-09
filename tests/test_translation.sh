#!/bin/sh

API_KEY=${API_KEY:-sk-8q4FLacEpHcRQVGVmvTA2Vu-o-jnUadcgbbmkBONQ7_i4-rqdEQhHwLeVOc733fr-tvJMePZroaEep58Zm63vw}
USER_ID=${USER_ID:-2df82b9b-61dc-49bb-8374-e7e3c17772db}
FILE_ID=${FILE_ID:-019bfe17-3418-7241-b52b-9d5f3987258d}
FILE_PRESET_ID=${FILE_PRESET_ID:-019c42cf-0393-7a5d-a523-6cfe5756760e}
RSMQ_CHANNEL_ID=${RSMQ_CHANNEL_ID:-00000000-0000-0000-0000-000000000000}


#
# Get File Translation For Listing
#
curl -s http://localhost:33001/api/v1/file/translation/$FILE_ID \
  --header "x-api-key: $API_KEY" | jq -r .


#
# Create File Translation
#
curl -i http://localhost:33001/api/v1/file/translation/ \
  --request POST \
  --header 'Content-Type: application/json' \
  --header "x-api-key: $API_KEY" \
  --data @- <<EOF
{
  "file_id": "$FILE_ID",
  "file_preset_id": "$FILE_PRESET_ID",
  "file_preset_json": {},
  "assignee_id": "$USER_ID"
}
EOF

#
# Subscribe to SSE Stream (use rsmq_channel_id from create response)
#
curl -N http://localhost:33001/api/v1/mq/channels/$RSMQ_CHANNEL_ID/events \
  --header "x-api-key: $API_KEY"