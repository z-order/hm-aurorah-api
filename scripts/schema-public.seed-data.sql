/*
   -- Run this SQL to seed data for required au_* tables 

   Option 1: Using environment from .env.local
   $ psql $POSTGRES_URL < schema.sql
  
   Option 2: Using psql command line
   $ psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -f schema.sql
  
   Option 3: Manually connect and execute:
   $ psql postgresql://your_user:your_password@your_host/your_database < schema.sql
*/

CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;

-- Seed data for au_system_ai_agents
INSERT INTO au_system_ai_agents (ai_agent_id, ai_agent_title, ai_agent_keyword, ui_sort_order, description)
VALUES
    ('task_translation_a1', 'Aurorah-A1', 'AI Translation', 'A01', 'AI agent for translation tasks'),
    ('task_translation_a2', 'Aurorah-A2', 'AI Translation + Proofreading', 'A02', 'AI agent for translation with proofreading')
ON CONFLICT (ai_agent_id) DO NOTHING;


-- Seed data for au_system_llm_models
INSERT INTO au_system_llm_models (llm_model_id, llm_model_title, llm_model_keyword, ui_sort_order, provider)
VALUES
    -- Anthropic models
    ('claude-opus-4-5-20251101', 'Anthropic Claude 4.5 Opus', 'Flagship', 'A01', 'anthropic'),
    ('claude-sonnet-4-5-20250929', 'Anthropic Claude 4.5 Sonnet', 'Balanced', 'A02', 'anthropic'),
    ('claude-haiku-4-5-20251001', 'Anthropic Claude 4.5 Haiku', 'Fast', 'A03', 'anthropic'),
    ('claude-4-opus', 'Anthropic Claude 4 Opus', 'High quality', 'A04', 'anthropic'),
    ('claude-sonnet-4-20250514', 'Anthropic Claude 4 Sonnet', 'Balanced', 'A05', 'anthropic'),
    ('claude-3.5-sonnet', 'Anthropic Claude 3.5 Sonnet', 'Legacy/Stable', 'A06', 'anthropic'),
    ('claude-3-opus', 'Anthropic Claude 3 Opus', 'Legacy/Stable', 'A07', 'anthropic'),
    ('claude-3.5-haiku', 'Anthropic Claude 3.5 Haiku', 'Legacy/Stable', 'A08', 'anthropic'),
    ('claude-3-5-sonnet-20240620', 'Anthropic Claude 3.5 Sonnet (20240620)', 'Legacy/Stable', 'A09', 'anthropic'),
    -- OpenAI models
    ('gpt-5.2', 'OpenAI GPT-5.2', 'Flagship', 'B01', 'openai'),
    ('gpt-5.1', 'OpenAI GPT-5.1', 'High quality', 'B02', 'openai'),
    ('gpt-5', 'OpenAI GPT-5', 'Balanced', 'B03', 'openai'),
    ('gpt-5-mini', 'OpenAI GPT-5 Mini', 'Balanced', 'B04', 'openai'),
    ('gpt-5-nano', 'OpenAI GPT-5 Nano', 'Fast', 'B05', 'openai'),
    ('gpt-5-chat', 'OpenAI GPT-5 Chat', 'Conversational', 'B06', 'openai'),
    ('gpt-4.1', 'OpenAI GPT-4.1', 'High quality', 'B07', 'openai'),
    ('gpt-4.1-mini', 'OpenAI GPT-4.1 Mini', 'Balanced', 'B08', 'openai'),
    ('gpt-4o', 'OpenAI GPT-4o', 'Legacy/Stable', 'B09', 'openai'),
    ('gpt-4o-mini', 'OpenAI GPT-4o Mini', 'Legacy/Stable', 'B10', 'openai'),
    ('o3', 'OpenAI o3', 'Reasoning', 'B11', 'openai'),
    ('o4-mini', 'OpenAI o4 Mini', 'Reasoning', 'B12', 'openai'),
    ('gpt-4-turbo', 'OpenAI GPT-4 Turbo', 'Legacy/Stable', 'B13', 'openai'),
    -- Google Gemini models
    ('gemini-3-pro-preview', 'Google Gemini 3 Pro', 'Flagship', 'C01', 'google'),
    ('gemini-3-flash-preview', 'Google Gemini 3 Flash', 'Fast', 'C02', 'google'),
    ('gemini-2.5-pro', 'Google Gemini 2.5 Pro', 'High quality', 'C03', 'google'),
    ('gemini-2.5-flash', 'Google Gemini 2.5 Flash', 'Balanced', 'C04', 'google'),
    ('gemini-2.5-flash-lite', 'Google Gemini 2.5 Flash Lite', 'Fast', 'C05', 'google'),
    -- xAI Grok models
    ('grok-4-1-fast-reasoning', 'xAI Grok 4.1 Fast (Reasoning)', 'Fast', 'D01', 'xai'),
    ('grok-4-1-fast-non-reasoning', 'xAI Grok 4.1 Fast (Non-Reasoning)', 'Fast', 'D02', 'xai'),
    ('grok-4-fast-reasoning', 'xAI Grok 4 Fast (Reasoning)', 'Fast', 'D03', 'xai'),
    ('grok-4-fast-non-reasoning', 'xAI Grok 4 Fast (Non-Reasoning)', 'Fast', 'D04', 'xai'),
    ('grok-4-0709', 'xAI Grok 4', 'Flagship', 'D05', 'xai'),
    ('grok-3', 'xAI Grok 3', 'Legacy/Stable', 'D06', 'xai'),
    ('grok-3-mini', 'xAI Grok 3 Mini', 'Legacy/Stable', 'D07', 'xai')
ON CONFLICT (llm_model_id) DO NOTHING;
-- Note: Excluded models with open_to_use=False: gpt-3.5-turbo-16k, gemini-1.5-pro, gemini-1.5-flash
