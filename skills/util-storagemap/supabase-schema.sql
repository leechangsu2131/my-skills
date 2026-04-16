create table if not exists public.storage_map_spaces (
  space_id text primary key,
  name text not null,
  description text not null default '',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.storage_map_furniture (
  furniture_id text primary key,
  space_id text not null,
  name text not null,
  type text not null default '',
  pos_x integer not null default 0,
  pos_y integer not null default 0,
  width integer not null default 120,
  height integer not null default 80,
  color text,
  notes text not null default '',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.storage_map_zones (
  zone_id text primary key,
  furniture_id text not null,
  name text not null,
  position_desc text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.storage_map_items (
  item_id text primary key,
  name text not null,
  furniture_id text not null,
  zone_id text,
  category text not null default '기타',
  tags text[] not null default '{}',
  memo text not null default '',
  photo_url text,
  quantity integer not null default 1,
  context text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.storage_map_history (
  history_id text primary key,
  item_id text not null,
  from_furniture text,
  from_zone text,
  to_furniture text,
  to_zone text,
  moved_at timestamptz not null default timezone('utc', now()),
  note text not null default ''
);

create index if not exists idx_storage_map_furniture_space_id on public.storage_map_furniture (space_id);
create index if not exists idx_storage_map_zones_furniture_id on public.storage_map_zones (furniture_id);
create index if not exists idx_storage_map_items_furniture_id on public.storage_map_items (furniture_id);
create index if not exists idx_storage_map_items_zone_id on public.storage_map_items (zone_id);
create index if not exists idx_storage_map_history_item_id on public.storage_map_history (item_id);
create index if not exists idx_storage_map_history_moved_at on public.storage_map_history (moved_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists trg_storage_map_spaces_updated_at on public.storage_map_spaces;
create trigger trg_storage_map_spaces_updated_at
before update on public.storage_map_spaces
for each row
execute function public.set_updated_at();

drop trigger if exists trg_storage_map_furniture_updated_at on public.storage_map_furniture;
create trigger trg_storage_map_furniture_updated_at
before update on public.storage_map_furniture
for each row
execute function public.set_updated_at();

drop trigger if exists trg_storage_map_zones_updated_at on public.storage_map_zones;
create trigger trg_storage_map_zones_updated_at
before update on public.storage_map_zones
for each row
execute function public.set_updated_at();

drop trigger if exists trg_storage_map_items_updated_at on public.storage_map_items;
create trigger trg_storage_map_items_updated_at
before update on public.storage_map_items
for each row
execute function public.set_updated_at();
