create table public.guardrail_interactions (
  conversation_id text not null,
  created_at timestamp with time zone not null default now(),
  check_type public.guardrail_check_type not null,
  input_list jsonb null,
  response_object jsonb null,
  compliant boolean null,
  action_taken text null,
  rules_violated text[] null,
  is_flagged boolean null default false,
  user_comment text null,
  feedback_type text null,
  schema_validation_error boolean null default false,
  constraint guardrail_interactions_unique_check unique (conversation_id, check_type)
) TABLESPACE pg_default;

create index IF not exists idx_guardrail_interactions_conv_id on public.guardrail_interactions using btree (conversation_id) TABLESPACE pg_default;
create index IF not exists idx_guardrail_interactions_compliant on public.guardrail_interactions using btree (compliant) TABLESPACE pg_default;
create index IF not exists idx_guardrail_interactions_flagged on public.guardrail_interactions using btree (is_flagged) TABLESPACE pg_default;
