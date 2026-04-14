-- Supabase Storage 'teacher_guides' 버킷 생성 및 공개 접근 허용
insert into storage.buckets (id, name, public)
values ('teacher_guides', 'teacher_guides', true)
on conflict (id) do update set public = true;

-- public 버킷이므로 누구나 읽을 수 있게 정책 설정
create policy "Public Access"
  on storage.objects for select
  using ( bucket_id = 'teacher_guides' );

-- (마이그레이션 스크립트를 위해) 익명 혹은 인증된 사용자 모두 업로드 허용
create policy "Allow Uploads"
  on storage.objects for insert
  with check ( bucket_id = 'teacher_guides' );
