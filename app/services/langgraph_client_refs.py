from typing import Any

from langgraph_sdk.schema import StreamPart

#
# Example StreamPart data from LangGraph SDK.
# Use these as reference when analyzing the parse_chunk() function in langgraph_client.py.
#
# Output from the LangGraph client example:
#
#   async for chunk in client.runs.stream(
#       thread["thread_id"],
#       graph_name,
#       input={"messages": [HumanMessage(content=user_input)]},
#       config=config,
#       stream_mode=["updates", "tasks", "events"],
#   ):
#       analyzed_chunk(chunk)
#
#   or (HITL mode)
#
#   async for chunk in client.runs.stream(
#       thread["thread_id"],
#       graph_name,
#       input=None,
#       command=Command(resume=resume_msg),
#       config=config,
#       stream_mode=["updates", "tasks", "events"],
#   ):
#       analyzed_chunk(chunk)
#

StreamPart(
    event="metadata",
    data={
        "run_id": "019ae54a-ef8f-743a-8173-16d4a7c64f91",
        "attempt": 1,
    },
)

StreamPart(
    event="tasks",
    data={
        "id": "002e3388-6354-d3cf-b8e3-0895479fe96e",
        "name": "upload_original_text",
        "input": {
            "messages": [
                {
                    "content": "안녕?",
                    "additional_kwargs": {},
                    "response_metadata": {},
                    "type": "human",
                    "name": None,
                    "id": "37d08ee7-e44e-40cd-a458-32761d97a95c",
                }
            ],
        },
        "triggers": ["branch:to:upload_original_text"],
    },
)

StreamPart(
    event="updates",
    data={
        "upload_original_text": {
            "options": {
                "llm_model": "claude-sonnet-4-20250514",
                "temperature": 0.0,
            },
            "keys": {
                "original_text": "19125091-685e-4626-ae49-fe031270125f",
                "translation_rules": "5fcfd2f1-b192-4a5e-8986-47a5380774f6",
            },
            "messages": [],
        }
    },
)

StreamPart(
    event="tasks",
    data={
        "id": "002e3388-6354-d3cf-b8e3-0895479fe96e",
        "name": "upload_original_text",
        "error": None,
        "result": {
            "options": {
                "llm_model": "claude-sonnet-4-20250514",
                "temperature": 0.0,
            },
            "keys": {
                "original_text": "19125091-685e-4626-ae49-fe031270125f",
                "translation_rules": "5fcfd2f1-b192-4a5e-8986-47a5380774f6",
            },
            "messages": [],
        },
        "interrupts": [],
    },
)

StreamPart(
    event="tasks",
    data={
        "id": "d814f74f-17fb-2d32-ac87-22361d71dc72",
        "name": "analyze_original_text",
        "input": {
            "messages": [
                {
                    "content": "안녕?",
                    "additional_kwargs": {},
                    "response_metadata": {},
                    "type": "human",
                    "name": None,
                    "id": "37d08ee7-e44e-40cd-a458-32761d97a95c",
                }
            ],
            "options": {
                "llm_model": "claude-sonnet-4-20250514",
                "temperature": 0.0,
            },
            "keys": {
                "original_text": "19125091-685e-4626-ae49-fe031270125f",
                "translation_rules": "5fcfd2f1-b192-4a5e-8986-47a5380774f6",
            },
        },
        "triggers": ["branch:to:analyze_original_text"],
    },
)

StreamPart(
    event="updates",
    data={
        "__interrupt__": [
            {
                "value": {
                    "call_chain": [
                        "ask_user_for_clarifying_task",
                        "__human_in_the_loop",
                        "interrupt",
                    ],
                    "next_node": "check_analyzed_result_by_llm",
                    "cause": "ASKU found",
                    "msg": (
                        "번역/현지화 작업을 진행하기 위해 몇 가지 정보가 필요합니다. 다음 사항들을 알려주시겠습니까?\n"
                        "\n"
                        "1. 목표 언어: 어떤 언어로 번역하시겠습니까?\n"
                        "2. 목표 국가: 어느 국가를 대상으로 하시겠습니까?\n"
                        "3. 대상 독자: 누구를 위한 번역인가요? (어린이, 청소년, 성인, 노인, 일반 대중 등)\n"
                        "4. 번역 목적: 이 번역의 목적이나 용도는 무엇인가요?\n"
                        "\n"
                        "이 정보들을 제공해 주시면 더 정확하고 적절한 번역을 제공할 수 있습니다."
                    ),
                },
                "id": "f9dff66cdb4d0284925e6df7eddef25c",
            }
        ]
    },
)

StreamPart(
    event="tasks",
    data={
        "id": "d814f74f-17fb-2d32-ac87-22361d71dc72",
        "name": "analyze_original_text",
        "error": None,
        "result": {},
        "interrupts": [
            {
                "value": {
                    "call_chain": [
                        "ask_user_for_clarifying_task",
                        "__human_in_the_loop",
                        "interrupt",
                    ],
                    "next_node": "check_analyzed_result_by_llm",
                    "cause": "ASKU found",
                    "msg": (
                        "번역/현지화 작업을 진행하기 위해 몇 가지 정보가 필요합니다. 다음 사항들을 알려주시겠습니까?\n"
                        "\n"
                        "1. 목표 언어: 어떤 언어로 번역하시겠습니까?\n"
                        "2. 목표 국가: 어느 국가를 대상으로 하시겠습니까?\n"
                        "3. 대상 독자: 누구를 위한 번역인가요? (어린이, 청소년, 성인, 노인, 일반 대중 등)\n"
                        "4. 번역 목적: 이 번역의 목적이나 용도는 무엇인가요?\n"
                        "\n"
                        "이 정보들을 제공해 주시면 더 정확하고 적절한 번역을 제공할 수 있습니다."
                    ),
                },
                "id": "f9dff66cdb4d0284925e6df7eddef25c",
            }
        ],
    },
)

StreamPart(
    event="events",
    data={
        "event": "on_chat_model_stream",
        "data": {
            "chunk": {
                "content": [{"partial_json": ' "정보를 제공해 주셔', "type": "input_json_delta", "index": 0}],
                "additional_kwargs": {},
                "response_metadata": {"model_provider": "anthropic"},
                "type": "AIMessageChunk",
                "name": None,
                "id": "lc_run--a6d4ddc3-dd70-49c5-8296-cb64eb51002b",
                "tool_calls": [],
                "invalid_tool_calls": [
                    {
                        "name": None,
                        "args": ' "정보를 제공해 주셔',
                        "id": None,
                        "error": None,
                        "type": "invalid_tool_call",
                    }
                ],
                "usage_metadata": None,
                "tool_call_chunks": [
                    {
                        "name": None,
                        "args": ' "정보를 제공해 주셔',  # I will take this as a tool call chunk
                        "id": None,
                        "index": 0,
                        "type": "tool_call_chunk",
                    }
                ],
                "chunk_position": None,
            }
        },
        "run_id": "a6d4ddc3-dd70-49c5-8296-cb64eb51002b",
        "name": "ChatAnthropic",
        "tags": ["seq:step:1"],
        "metadata": {
            "created_by": "system",
            "graph_id": "task_translation",
            "assistant_id": "a60947f5-b34c-59a5-afa9-552e54277b6f",
            "run_attempt": 1,
            "langgraph_version": "1.0.4",
            "langgraph_api_version": "0.5.27",
            "langgraph_plan": "developer",
            "langgraph_host": "self-hosted",
            "langgraph_api_url": "http://127.0.0.1:2024",
            "user_id": "user01",
            "langgraph_auth_user_id": "",
            "langgraph_request_id": "739ab6e4-865f-433e-a6f0-fbfcc93f38e0",
            "run_id": "019ae54c-d6be-7597-a898-22d423adc0a2",
            "thread_id": "077ad454-702f-40f4-be84-b43190e2fc6e",
            "langgraph_step": 6,
            "langgraph_node": "check_analyzed_result_by_llm",
            "langgraph_triggers": ["branch:to:check_analyzed_result_by_llm"],
            "langgraph_path": ["__pregel_pull", "check_analyzed_result_by_llm"],
            "langgraph_checkpoint_ns": "analyze_original_text:d814f74f-17fb-2d32-ac87-22361d71dc72|check_analyzed_result_by_llm:e33342e7-e121-f94d-8e0e-ebd114cc40c3",
            "checkpoint_ns": "analyze_original_text:d814f74f-17fb-2d32-ac87-22361d71dc72",
            "ls_provider": "anthropic",
            "ls_model_name": "claude-sonnet-4-20250514",
            "ls_model_type": "chat",
            "ls_temperature": 0.0,
            "ls_max_tokens": 64000,
        },
        "parent_ids": [
            "019ae54c-d6be-7597-a898-22d423adc0a2",
            "551b6aa2-d725-4f1d-9c43-a34b8f47b8b1",
            "088fd08c-9bd3-4e7b-bf7c-0df14b15a857",
            "aa0e69f2-d86c-4945-a07f-2ea476963fa2",
        ],
    },
)


StreamPart(
    event="events",
    data={
        "event": "on_chat_model_stream",
        "data": {
            "chunk": {
                "content": "┼Hey",  # I will take this as a text chunk
                "additional_kwargs": {},
                "response_metadata": {"model_provider": "anthropic"},
                "type": "AIMessageChunk",
                "name": None,
                "id": "lc_run--c8613e46-7046-49c6-8bcc-ed4293b6ac5e",
                "tool_calls": [],
                "invalid_tool_calls": [],
                "usage_metadata": None,
                "tool_call_chunks": [],
                "chunk_position": None,
            }
        },
        "run_id": "c8613e46-7046-49c6-8bcc-ed4293b6ac5e",
        "name": "ChatAnthropic",
        "tags": ["seq:step:1"],
        "metadata": {
            "created_by": "system",
            "graph_id": "task_translation",
            "assistant_id": "a60947f5-b34c-59a5-afa9-552e54277b6f",
            "run_attempt": 1,
            "langgraph_version": "1.0.4",
            "langgraph_api_version": "0.5.27",
            "langgraph_plan": "developer",
            "langgraph_host": "self-hosted",
            "langgraph_api_url": "http://127.0.0.1:2024",
            "user_id": "user01",
            "langgraph_auth_user_id": "",
            "langgraph_request_id": "739ab6e4-865f-433e-a6f0-fbfcc93f38e0",
            "run_id": "019ae54c-d6be-7597-a898-22d423adc0a2",
            "thread_id": "077ad454-702f-40f4-be84-b43190e2fc6e",
            "langgraph_step": 3,
            "langgraph_node": "translation_5step_allinone",
            "langgraph_triggers": ["branch:to:translation_5step_allinone"],
            "langgraph_path": ["__pregel_pull", "translation_5step_allinone"],
            "langgraph_checkpoint_ns": "translation_5step_allinone:9a36b33f-73b1-2285-a757-55db40805b45",
            "checkpoint_ns": "translation_5step_allinone:9a36b33f-73b1-2285-a757-55db40805b45",
            "ls_provider": "anthropic",
            "ls_model_name": "claude-sonnet-4-20250514",
            "ls_model_type": "chat",
            "ls_temperature": 0.0,
            "ls_max_tokens": 64000,
        },
        "parent_ids": ["019ae54c-d6be-7597-a898-22d423adc0a2", "eb856676-b1bf-4fc4-8f49-04a70d2e3699"],
    },
)

# Output data for the 'updates' event
Output: dict[str, Any] = {
    "messages": [
        {
            "content": "안녕?",
            "additional_kwargs": {},
            "response_metadata": {},
            "type": "human",
            "name": None,
            "id": "5041d383-de10-4d52-ba9d-92c41bbb0629",
        },
        {
            "content": [
                {
                    "id": "toolu_015PqGt5HTfukAcdHihxyLVm",
                    "input": {
                        "summary": 'A simple Korean greeting "안녕?" (Hello?) with a formatting marker "┼1┼" at the beginning.',
                        "plot": (
                            'The text consists of a very brief Korean greeting. It starts with "┼1┼" '
                            'which appears to be a formatting or indexing marker, followed by "안녕?" '
                            'which is a casual, informal way of saying "Hello?" or "Hi?" in Korean. '
                            "This is typically used among friends, peers, or in casual social situations. "
                            "The question mark indicates it's being used as a greeting question, similar to "
                            '"How are you?" in English. The text is extremely short and represents a basic '
                            "social interaction opening."
                        ),
                        "category": "Social Communication",
                        "source_language": "Korean",
                        "source_region": "East Asia",
                        "source_country": "South Korea",
                        "source_city": "Seoul",
                        "target_language": "ASKU",
                        "target_country": "ASKU",
                        "target_city": None,
                        "task_type": "translation/localization",
                        "audience": "ASKU",
                        "purpose": "ASKU",
                        "content_grade": ["general-audience"],
                        "content_level": ["elementary"],
                        "tone_of_sentences": ["informal", "casual", "questioning", "friendly"],
                        "sentence_style": "social/casual",
                        "background": (
                            "Contemporary modern Korean casual conversation, representing everyday social "
                            "interaction in current Korean society."
                        ),
                        "analysis_detail": (
                            "A. Vocabulary and Style: The text uses extremely basic, everyday Korean vocabulary "
                            'with "안녕" being one of the most fundamental greeting words in Korean. The tone is '
                            "highly informal and casual, typical of conversations between friends or peers of "
                            "similar age/status. The question mark adds a friendly, inquisitive quality to the greeting.\n"
                            "B. Structure: The sentence structure is minimal - just a single word greeting followed by a question mark. "
                            'The "┼1┼" marker suggests this might be part of a numbered or indexed conversation/dialogue system. The brevity '
                            "creates immediacy and informality typical of modern digital communication.\n"
                            "C. Cultural Characteristics: This represents Korean casual social interaction norms "
                            'where "안녕?" serves as both a greeting and a way to check on someone\'s well-being. The informality indicates a '
                            "relationship of familiarity and equality between speakers, reflecting Korean social hierarchy considerations in language use."
                        ),
                        "asku": [
                            "target_language",
                            "target_country",
                            "audience",
                            "purpose",
                        ],
                    },
                    "name": "AnalyzeOriginalText__FirstChunk",
                    "type": "tool_use",
                }
            ],
            "additional_kwargs": {},
            "response_metadata": {
                "id": "msg_012imnjn58D49Nx2kLfFzbZ1",
                "model": "claude-sonnet-4-20250514",
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {
                    "cache_creation": {
                        "ephemeral_1h_input_tokens": 0,
                        "ephemeral_5m_input_tokens": 0,
                    },
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "input_tokens": 3138,
                    "output_tokens": 756,
                    "server_tool_use": None,
                    "service_tier": "standard",
                },
                "model_name": "claude-sonnet-4-20250514",
                "model_provider": "anthropic",
            },
            "type": "ai",
            "name": None,
            "id": "lc_run--5425c5d3-9407-4e49-a01e-d37defbf0364-0",
            "tool_calls": [
                {
                    "name": "AnalyzeOriginalText__FirstChunk",
                    "args": {
                        "summary": 'A simple Korean greeting "안녕?" (Hello?) with a formatting marker "┼1┼" at the beginning.',
                        "plot": (
                            'The text consists of a very brief Korean greeting. It starts with "┼1┼" '
                            'which appears to be a formatting or indexing marker, followed by "안녕?" '
                            'which is a casual, informal way of saying "Hello?" or "Hi?" in Korean. '
                            "This is typically used among friends, peers, or in casual social situations. "
                            "The question mark indicates it's being used as a greeting question, similar to "
                            '"How are you?" in English. The text is extremely short and represents a basic '
                            "social interaction opening."
                        ),
                        "category": "Social Communication",
                        "source_language": "Korean",
                        "source_region": "East Asia",
                        "source_country": "South Korea",
                        "source_city": "Seoul",
                        "target_language": "ASKU",
                        "target_country": "ASKU",
                        "target_city": None,
                        "task_type": "translation/localization",
                        "audience": "ASKU",
                        "purpose": "ASKU",
                        "content_grade": ["general-audience"],
                        "content_level": ["elementary"],
                        "tone_of_sentences": ["informal", "casual", "questioning", "friendly"],
                        "sentence_style": "social/casual",
                        "background": (
                            "Contemporary modern Korean casual conversation, representing everyday social "
                            "interaction in current Korean society."
                        ),
                        "analysis_detail": (
                            "A. Vocabulary and Style: The text uses extremely basic, everyday Korean vocabulary "
                            'with "안녕" being one of the most fundamental greeting words in Korean. The tone is '
                            "highly informal and casual, typical of conversations between friends or peers of "
                            "similar age/status. The question mark adds a friendly, inquisitive quality to the greeting.\n"
                            "B. Structure: The sentence structure is minimal - just a single word greeting followed by a question mark. "
                            'The "┼1┼" marker suggests this might be part of a numbered or indexed conversation/dialogue system. The brevity '
                            "creates immediacy and informality typical of modern digital communication.\n"
                            "C. Cultural Characteristics: This represents Korean casual social interaction norms "
                            'where "안녕?" serves as both a greeting and a way to check on someone\'s well-being. The informality indicates a '
                            "relationship of familiarity and equality between speakers, reflecting Korean social hierarchy considerations in language use."
                        ),
                        "asku": [
                            "target_language",
                            "target_country",
                            "audience",
                            "purpose",
                        ],
                    },
                    "id": "toolu_015PqGt5HTfukAcdHihxyLVm",
                    "type": "tool_call",
                }
            ],
            "invalid_tool_calls": [],
            "usage_metadata": {
                "input_tokens": 3138,
                "output_tokens": 756,
                "total_tokens": 3894,
                "input_token_details": {
                    "cache_creation": 0,
                    "cache_read": 0,
                    "ephemeral_5m_input_tokens": 0,
                    "ephemeral_1h_input_tokens": 0,
                },
            },
        },
        {
            "content": [
                {
                    "id": "toolu_016EiWe9K1BgzdqLJEEbEDtP",
                    "input": {
                        "message": (
                            "안녕하세요! 번역 작업을 진행하기 위해 몇 가지 정보가 필요합니다. "
                            "어떤 언어로 번역하시길 원하시나요? 그리고 어느 국가를 대상으로 하시는지, "
                            "누구를 대상 독자로 하시는지, 번역의 목적이 무엇인지 알려주시면 감사하겠습니다."
                        ),
                        "target_language": "ASKU",
                        "target_country": "ASKU",
                        "target_city": "ASKU",
                        "audience": "ASKU",
                        "purpose": "ASKU",
                        "asku": [
                            "target_language",
                            "target_country",
                            "audience",
                            "purpose",
                        ],
                    },
                    "name": "AnalyzeOriginalText__ASKU",
                    "type": "tool_use",
                }
            ],
            "additional_kwargs": {},
            "response_metadata": {
                "id": "msg_01CDCitXSBtuYVXZywAfWVuM",
                "model": "claude-sonnet-4-20250514",
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {
                    "cache_creation": {
                        "ephemeral_1h_input_tokens": 0,
                        "ephemeral_5m_input_tokens": 0,
                    },
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "input_tokens": 1781,
                    "output_tokens": 285,
                    "server_tool_use": None,
                    "service_tier": "standard",
                },
                "model_name": "claude-sonnet-4-20250514",
                "model_provider": "anthropic",
            },
            "type": "ai",
            "name": None,
            "id": "lc_run--df9a8f22-992b-40d1-8dd5-be671b97bbd9-0",
            "tool_calls": [
                {
                    "name": "AnalyzeOriginalText__ASKU",
                    "args": {
                        "message": (
                            "안녕하세요! 번역 작업을 진행하기 위해 몇 가지 정보가 필요합니다. "
                            "어떤 언어로 번역하시길 원하시나요? 그리고 어느 국가를 대상으로 하시는지, "
                            "누구를 대상 독자로 하시는지, 번역의 목적이 무엇인지 알려주시면 감사하겠습니다."
                        ),
                        "target_language": "ASKU",
                        "target_country": "ASKU",
                        "target_city": "ASKU",
                        "audience": "ASKU",
                        "purpose": "ASKU",
                        "asku": [
                            "target_language",
                            "target_country",
                            "audience",
                            "purpose",
                        ],
                    },
                    "id": "toolu_016EiWe9K1BgzdqLJEEbEDtP",
                    "type": "tool_call",
                }
            ],
            "invalid_tool_calls": [],
            "usage_metadata": {
                "input_tokens": 1781,
                "output_tokens": 285,
                "total_tokens": 2066,
                "input_token_details": {
                    "cache_creation": 0,
                    "cache_read": 0,
                    "ephemeral_5m_input_tokens": 0,
                    "ephemeral_1h_input_tokens": 0,
                },
            },
        },
        {
            "content": [
                {
                    "id": "toolu_01Q2f8fapPSzXk618H6AgQcn",
                    "input": {},
                    "name": "AnalyzeOriginalText__ASKU",
                    "type": "tool_use",
                    "index": 0,
                    "partial_json": (
                        '{"message": "감사합니다! 영어로 미국 성인 독자를 대상으로 한 웹소설 번역 작업을 진행하겠습니다. '
                        '모든 필요한 정보를 제공해 주셔서 감사합니다.", '
                        '"target_language": "English", '
                        '"target_country": "United States", '
                        '"target_city": null, '
                        '"audience": "adult", '
                        '"purpose": "Web novel translation", '
                        '"asku": []}'
                    ),
                }
            ],
            "additional_kwargs": {},
            "response_metadata": {
                "model_name": "claude-sonnet-4-20250514",
                "model_provider": "anthropic",
                "stop_reason": "tool_use",
                "stop_sequence": None,
            },
            "type": "ai",
            "name": None,
            "id": "lc_run--08fb5f53-ef1b-4865-b204-2f5882e081e2",
            "tool_calls": [
                {
                    "name": "AnalyzeOriginalText__ASKU",
                    "args": {
                        "message": (
                            "감사합니다! 영어로 미국 성인 독자를 대상으로 한 웹소설 번역 작업을 진행하겠습니다. "
                            "모든 필요한 정보를 제공해 주셔서 감사합니다."
                        ),
                        "target_language": "English",
                        "target_country": "United States",
                        "target_city": None,
                        "audience": "adult",
                        "purpose": "Web novel translation",
                        "asku": [],
                    },
                    "id": "toolu_01Q2f8fapPSzXk618H6AgQcn",
                    "type": "tool_call",
                }
            ],
            "invalid_tool_calls": [],
            "usage_metadata": {
                "input_tokens": 1964,
                "output_tokens": 210,
                "total_tokens": 2174,
                "input_token_details": {
                    "cache_creation": 0,
                    "cache_read": 0,
                },
            },
        },
    ],
    "options": {
        "llm_model": "claude-sonnet-4-20250514",
        "temperature": 0.0,
    },
    "keys": {
        "original_text": "b0fa6ccc-a8ae-47bd-aaec-f4a6988c82f1",
        "translation_rules": "8e1ed094-3aea-4b11-9579-324e131b61db",
    },
    "chunks": {
        "total_chunks": 1,
        "current_chunk_index": 0,
        "current_chunk_length": 6,
        "current_chunk_text": "┼1┼안녕?",
    },
    "asku": {
        "asku_done": True,
        "asku_found": True,
        "asku_items": [],
        "asku_assistant_message": (
            "감사합니다! 영어로 미국 성인 독자를 대상으로 한 웹소설 번역 작업을 진행하겠습니다. "
            "모든 필요한 정보를 제공해 주셔서 감사합니다."
        ),
        "asku_user_response": "",
    },
}
