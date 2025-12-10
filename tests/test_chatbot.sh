#!/bin/sh

API_KEY=${API_KEY:-sk-test123}
USER_ID=${USER_ID:-7cfab52b-5b9e-4af7-9cfb-e3c218adad5c}
TASK_ID=${TASK_ID:-019ae992-10d4-78e2-966a-f2d073c1ee1a}
THREAD_ID=${THREAD_ID:-4cce0a0a-278b-4402-81c9-f1dfa400678c}
MESSAGE_ID=${MESSAGE_ID:-00000000-0000-0000-0000-000000000000}

#
# Create Chatbot Task
#
curl -i http://localhost:33001/api/v1/chatbot/task \
  --request POST \
  --header 'Content-Type: application/json' \
  --header "x-api-key: $API_KEY" \
  --data @- <<EOF
{
  "user_id": "$USER_ID",
  "translation_memory": "default-translation-memory",
  "translation_role": "",
  "title": "New Task",
  "description": ""
}
EOF


#
# Get Chatbot Tasks
#
curl -s "http://localhost:33001/api/v1/chatbot/task/$USER_ID?skip=0&limit=100" \
  --header "x-api-key: $API_KEY" | jq -r .


#
# Update Chatbot Task
#
curl -s "http://localhost:33001/api/v1/chatbot/task/$TASK_ID" \
  --request PUT \
  --header 'Content-Type: application/json' \
  --header "x-api-key: $API_KEY" \
  --data @- <<EOF | jq -r .
{
  "title": "Updated Task",
  "description": "Updated Description"
}
EOF


#
# Delete Chatbot Task
#
curl -i "http://localhost:33001/api/v1/chatbot/task/$TASK_ID" \
  --request DELETE \
  --header "x-api-key: $API_KEY"


#
# Create Chatbot Message in Normal Mode
#
curl -i http://localhost:33001/api/v1/chatbot/message \
  --request POST \
  --header 'Content-Type: application/json' \
  --header "x-api-key: $API_KEY" \
  --data @- <<EOF
{
  "user_id": "$USER_ID",
  "task_id": "$TASK_ID",
  "content": "Hello, how are you?",
  "files": [
    {
      "url": "https://example.com/file.pdf",
      "name": "file.pdf",
      "mime_type": "application/pdf",
      "extension": "pdf",
      "size": 1000
    }
  ]
}
EOF


#
# Create Chatbot Message in HITL Mode
#
curl -i http://localhost:33001/api/v1/chatbot/message \
  --request POST \
  --header 'Content-Type: application/json' \
  --header "x-api-key: $API_KEY" \
  --data @- <<EOF
{
  "hitl_mode": true,
  "hitl_message_id": "$MESSAGE_ID",
  "user_id": "$USER_ID",
  "task_id": "$TASK_ID",
  "content": "Target language is Korean, country is South Korea, audience is adults, purpose is web novel translation"
}
EOF


#
# Get Chatbot Messages
#
curl -i "http://localhost:33001/api/v1/chatbot/message/$TASK_ID?skip=0&limit=100" \
  --header "x-api-key: $API_KEY"


#
# Update Chatbot Message
#
curl -i "http://localhost:33001/api/v1/chatbot/message/$MESSAGE_ID" \
  --request PUT \
  --header 'Content-Type: application/json' \
  --header "x-api-key: $API_KEY" \
  --data @- <<EOF
{
  "content": "Updated Content: Hello, how are you?",
  "files": [
    {
      "url": "https://example.com/file.pdf",
      "name": "file.pdf",
      "mime_type": "application/pdf",
      "extension": "pdf",
      "size": 1000
    }
  ]
}
EOF


#
# Delete Chatbot Message
#
curl -i "http://localhost:33001/api/v1/chatbot/message/$MESSAGE_ID" \
  --request DELETE \
  --header "x-api-key: $API_KEY"
