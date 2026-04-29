-- Run this once in your Supabase SQL editor

create table if not exists scan_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  repo_url text,
  branch text,
  terraform_path text,
  do_project text,
  region_filter text,
  results jsonb,
  created_at timestamptz default now()
);

alter table scan_history enable row level security;

create policy "users see own history"
  on scan_history for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
