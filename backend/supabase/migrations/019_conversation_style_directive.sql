-- ABOUTME: Renames the conversation style `direct` to `directive`, the client's name for it.
-- ABOUTME: Rewrites stored styles and the greeting's style buttons, then re-adds both checks.

-- The client's styles document of 2026-10-12 names the style Directive. One spelling only, as
-- in 002: two spellings of one vocabulary is how the specifications drifted apart.

alter table public.profiles drop constraint profiles_support_style_known;
alter table public.threads drop constraint threads_conversation_style_known;

update public.profiles set support_style = 'directive' where support_style = 'direct';
update public.threads set conversation_style = 'directive' where conversation_style = 'direct';

-- A greeting still waiting for its tap must open the thread in the renamed style, so its
-- button is rewritten with the label the backend now matches.
update public.messages
   set prompt_options = (
         select jsonb_agg(
                  case when option ->> 'style' = 'direct'
                       then option || '{"label": "Directive", "style": "directive"}'::jsonb
                       else option
                  end
                  order by position)
           from jsonb_array_elements(prompt_options) with ordinality as options(option, position)
       )
 where jsonb_typeof(prompt_options) = 'array'
   and prompt_options @> '[{"style": "direct"}]'::jsonb;

alter table public.profiles
  add constraint profiles_support_style_known
    check (support_style is null
           or support_style in ('supportive', 'reflective', 'directive'));

alter table public.threads
  add constraint threads_conversation_style_known
    check (conversation_style is null
           or conversation_style in ('supportive', 'reflective', 'directive'));
