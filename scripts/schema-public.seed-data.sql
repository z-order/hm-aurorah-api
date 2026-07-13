/*
   -- Run this SQL to seed data for required au_* tables 

   Option 1: Using environment from .env.local
   $ psql $POSTGRES_URL < ./schema-public.seed-data.sql
  
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
    ('claude-fable-5', 'Anthropic Claude Fable 5', 'Flagship (Mythos)', 'A01', 'anthropic'),
    ('claude-opus-4-8', 'Anthropic Claude Opus 4.8', 'Flagship', 'A02', 'anthropic'),
    ('claude-sonnet-5', 'Anthropic Claude Sonnet 5', 'Balanced', 'A03', 'anthropic'),
    ('claude-opus-4-7', 'Anthropic Claude Opus 4.7', 'High quality', 'A04', 'anthropic'),
    ('claude-opus-4-6', 'Anthropic Claude Opus 4.6', 'High quality', 'A05', 'anthropic'),
    ('claude-sonnet-4-6', 'Anthropic Claude Sonnet 4.6', 'Balanced', 'A06', 'anthropic'),
    ('claude-opus-4-5-20251101', 'Anthropic Claude 4.5 Opus', 'Legacy/Stable', 'A07', 'anthropic'),
    ('claude-sonnet-4-5-20250929', 'Anthropic Claude 4.5 Sonnet', 'Legacy/Stable', 'A08', 'anthropic'),
    ('claude-haiku-4-5-20251001', 'Anthropic Claude 4.5 Haiku', 'Fast', 'A09', 'anthropic'),
    -- OpenAI models
    ('gpt-5.6-sol', 'OpenAI GPT-5.6 Sol', 'Flagship', 'B01', 'openai'),
    ('gpt-5.6-terra', 'OpenAI GPT-5.6 Terra', 'Balanced', 'B02', 'openai'),
    ('gpt-5.6-luna', 'OpenAI GPT-5.6 Luna', 'Fast', 'B03', 'openai'),
    ('gpt-5.5', 'OpenAI GPT-5.5', 'High quality', 'B04', 'openai'),
    ('gpt-5.4', 'OpenAI GPT-5.4', 'Balanced', 'B05', 'openai'),
    ('gpt-5.4-mini', 'OpenAI GPT-5.4 Mini', 'Fast', 'B06', 'openai'),
    ('gpt-5.2', 'OpenAI GPT-5.2', 'Legacy/Stable', 'B07', 'openai'),
    ('gpt-5.1', 'OpenAI GPT-5.1', 'Legacy/Stable', 'B08', 'openai'),
    ('gpt-5', 'OpenAI GPT-5', 'Legacy/Stable', 'B09', 'openai'),
    ('gpt-5-mini', 'OpenAI GPT-5 Mini', 'Legacy/Stable', 'B10', 'openai'),
    ('gpt-5-nano', 'OpenAI GPT-5 Nano', 'Legacy/Stable', 'B11', 'openai'),
    ('gpt-5-chat', 'OpenAI GPT-5 Chat', 'Legacy/Stable', 'B12', 'openai'),
    ('gpt-4.1', 'OpenAI GPT-4.1', 'Legacy/Stable', 'B13', 'openai'),
    ('gpt-4.1-mini', 'OpenAI GPT-4.1 Mini', 'Legacy/Stable', 'B14', 'openai'),
    ('o3', 'OpenAI o3', 'Reasoning', 'B15', 'openai'),
    ('o4-mini', 'OpenAI o4 Mini', 'Reasoning', 'B16', 'openai'),
    -- Google Gemini models
    ('gemini-3.5-flash', 'Google Gemini 3.5 Flash', 'Flagship', 'C01', 'google'),
    ('gemini-3.1-pro-preview', 'Google Gemini 3.1 Pro', 'High quality', 'C02', 'google'),
    ('gemini-3.1-flash-lite', 'Google Gemini 3.1 Flash Lite', 'Fast', 'C03', 'google'),
    ('gemini-3-pro-preview', 'Google Gemini 3 Pro', 'Legacy/Stable', 'C04', 'google'),
    ('gemini-3-flash-preview', 'Google Gemini 3 Flash', 'Legacy/Stable', 'C05', 'google'),
    -- xAI Grok models
    ('grok-4.5', 'xAI Grok 4.5', 'Flagship', 'D01', 'xai'),
    ('grok-4.3', 'xAI Grok 4.3', 'High quality', 'D02', 'xai'),
    ('grok-4.20-0309-reasoning', 'xAI Grok 4.20 (Reasoning)', 'Reasoning', 'D03', 'xai'),
    ('grok-4.20-0309-non-reasoning', 'xAI Grok 4.20 (Non-Reasoning)', 'Balanced', 'D04', 'xai'),
    ('grok-4.20-multi-agent-0309', 'xAI Grok 4.20 Multi-Agent', 'Multi-Agent', 'D05', 'xai')
ON CONFLICT (llm_model_id) DO NOTHING;
-- Note: Excluded models with open_to_use=False in model.py:
--   claude-3.5-sonnet, claude-3-opus, claude-3.5-haiku, claude-3-5-sonnet-20240620,
--   gpt-5.4-pro, gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo-16k,
--   gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-1.5-pro, gemini-1.5-flash,
--   grok-4-1-fast-reasoning, grok-4-1-fast-non-reasoning, grok-4-fast-reasoning, grok-4-fast-non-reasoning, grok-3, grok-3-mini
-- Note: Excluded models retired by providers (checked 2026-07-13):
--   claude-4-opus, claude-sonnet-4-20250514 (retired by Anthropic on 2026-06-15),
--   grok-4-0709 (retired by xAI on 2026-05-15, redirected to grok-4.3)
