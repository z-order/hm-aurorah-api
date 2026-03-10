#!/bin/sh

API_KEY=${API_KEY:-sk-Mo316Hkrt6Bhy4TPNbISq7hJYwWXPwtM898Yil91GfpstCGrhzLJDB0oDgjSOp5EBEyE_AJ0p-VkXoSKIxeKKA}
FILE_ID=${FILE_ID:-019bfe17-3418-7241-b52b-9d5f3987258d}
RSMQ_CHANNEL_ID=${RSMQ_CHANNEL_ID:-00000000-0000-0000-0000-000000000000}
BASE_URL=${BASE_URL:-http://localhost:33001}


#
# Get File Task (existing task if any)
#
curl -s "$BASE_URL/api/v1/file/task/$FILE_ID" \
  --header "x-api-key: $API_KEY" | jq -r .


#
# Open File Task (sync: txt/srt/vtt/csv/tsv | async: docx/pptx/xlsx/hwpx/pdf/epub/video)
# Async response includes rsmq_channel_id; set RSMQ_CHANNEL_ID from it to subscribe below.
#
curl -i "$BASE_URL/api/v1/file/task/open/$FILE_ID" \
  --request POST \
  --header "x-api-key: $API_KEY"


#
# Subscribe to SSE stream (use rsmq_channel_id from open response when async)
#
curl -N "$BASE_URL/api/v1/mq/channels/$RSMQ_CHANNEL_ID/events" \
  --header "x-api-key: $API_KEY"
