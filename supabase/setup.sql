-- Jalankan di SQL Editor proyek baru: https://xdjurqzckgzjaaiccnyr.supabase.co
-- Membuat tabel, realtime, bucket, dan policy yang dipakai dashboard + sendscreenshoot.py

create table if not exists public.aloptama (
  id bigint generated always as identity primary key,
  kode text not null unique,
  gambar_url text,
  jenis text,
  bujur double precision,
  lintang double precision,
  status text default 'green',
  timestamp timestamptz default now()
);

alter table public.aloptama replica identity full;

do $$
begin
  if not exists (
    select 1
    from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'aloptama'
  ) then
    alter publication supabase_realtime add table public.aloptama;
  end if;
end $$;

alter table public.aloptama enable row level security;

drop policy if exists "anon all aloptama" on public.aloptama;
create policy "anon all aloptama" on public.aloptama
  for all
  to anon, authenticated
  using (true)
  with check (true);

insert into storage.buckets (id, name, public)
values ('aloptama-images', 'aloptama-images', true)
on conflict (id) do update set public = true;

drop policy if exists "anon read aloptama images" on storage.objects;
drop policy if exists "anon insert aloptama images" on storage.objects;
drop policy if exists "anon update aloptama images" on storage.objects;
drop policy if exists "anon delete aloptama images" on storage.objects;

create policy "anon read aloptama images" on storage.objects
  for select to anon, authenticated
  using (bucket_id = 'aloptama-images');

create policy "anon insert aloptama images" on storage.objects
  for insert to anon, authenticated
  with check (bucket_id = 'aloptama-images');

create policy "anon update aloptama images" on storage.objects
  for update to anon, authenticated
  using (bucket_id = 'aloptama-images')
  with check (bucket_id = 'aloptama-images');

create policy "anon delete aloptama images" on storage.objects
  for delete to anon, authenticated
  using (bucket_id = 'aloptama-images');
