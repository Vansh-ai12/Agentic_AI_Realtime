-- ============================================
-- EXTENSIONS
-- ============================================
create extension if not exists vector;
create extension if not exists pgcrypto;

-- ============================================
-- LAYER 1: AUTH (extends Supabase's auth.users)
-- ============================================
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz default now()
);

-- ============================================
-- LAYER 2: DATA SOURCE CONNECTIONS
-- ============================================
create table connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  source text not null check (source in ('notion', 'gmail')),
  access_token text,        -- store encrypted in production, not plain
  refresh_token text,
  status text default 'active' check (status in ('active', 'expired', 'revoked')),
  last_synced_at timestamptz,
  created_at timestamptz default now(),
  unique (user_id, source)
);

-- ============================================
-- LAYER 3: INGESTED CONTENT (RAG core)
-- ============================================
create table documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  connection_id uuid references connections(id) on delete cascade,
  source text not null,
  external_id text not null,       -- Notion page id / Gmail thread id
  title text,
  raw_content text,
  source_updated_at timestamptz,   -- when it last changed at the source
  created_at timestamptz default now(),
  unique (connection_id, external_id)
);

create table chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  embedding vector(1536),          -- adjust dim to match your embedding model
  created_at timestamptz default now()
);

create index chunks_embedding_idx on chunks
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ============================================
-- LAYER 4: MEMORY
-- ============================================
create table memory_short_term (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  session_id uuid not null,
  key_fact text not null,
  created_at timestamptz default now(),
  expires_at timestamptz default (now() + interval '1 day')
);

create table memory_long_term (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  summary text not null,
  embedding vector(1536),
  source_run_id uuid,               -- links back to the run it came from
  created_at timestamptz default now()
);

create index memory_long_term_embedding_idx on memory_long_term
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ============================================
-- LAYER 5: AGENT EXECUTION + RETRY LOOP
-- ============================================
create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  query text not null,
  status text default 'in_progress' check (status in ('in_progress', 'resolved', 'unresolved')),
  total_attempts int default 0,
  total_tokens int default 0,
  total_latency_ms int,
  created_at timestamptz default now(),
  completed_at timestamptz
);

create table agent_attempts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references agent_runs(id) on delete cascade,
  attempt_number int not null,
  planner_subquestions jsonb,
  synthesizer_answer text,
  critic_verdict text check (critic_verdict in ('approve', 'reject')),
  critic_reason text,
  tokens_used int,
  latency_ms int,
  created_at timestamptz default now()
);

-- ============================================
-- LAYER 6: TOKEN / COST TRACKING
-- ============================================
create table token_logs (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references agent_runs(id) on delete cascade,
  attempt_id uuid references agent_attempts(id) on delete cascade,
  agent_role text check (agent_role in ('planner', 'retriever', 'synthesizer', 'critic')),
  model text,
  tokens_in int,
  tokens_out int,
  created_at timestamptz default now()
);

-- ============================================
-- LAYER 7: EVAL (reserved for Week 4)
-- ============================================
create table eval_cases (
  id uuid primary key default gen_random_uuid(),
  category text check (category in ('normal', 'adversarial', 'missing_data', 'edge_case')),
  query text not null,
  expected_answer text,
  created_at timestamptz default now()
);

create table eval_results (
  id uuid primary key default gen_random_uuid(),
  eval_case_id uuid references eval_cases(id) on delete cascade,
  run_id uuid references agent_runs(id) on delete cascade,
  passed boolean,
  notes text,
  created_at timestamptz default now()
);

-- ============================================
-- ROW LEVEL SECURITY (basic user-scoped access)
-- ============================================
alter table profiles enable row level security;
alter table connections enable row level security;
alter table documents enable row level security;
alter table memory_short_term enable row level security;
alter table memory_long_term enable row level security;
alter table agent_runs enable row level security;

create policy "Users manage their own profile" on profiles
  for all using (auth.uid() = id);

create policy "Users manage their own connections" on connections
  for all using (auth.uid() = user_id);

create policy "Users manage their own documents" on documents
  for all using (auth.uid() = user_id);

create policy "Users manage their own short-term memory" on memory_short_term
  for all using (auth.uid() = user_id);

create policy "Users manage their own long-term memory" on memory_long_term
  for all using (auth.uid() = user_id);

create policy "Users manage their own runs" on agent_runs
  for all using (auth.uid() = user_id);