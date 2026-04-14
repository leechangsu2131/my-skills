-- ============================================================
-- Teacher Workspace — Supabase Schema
-- ============================================================

-- 과목 (Subjects)
CREATE TABLE subjects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  color TEXT DEFAULT '#005bbf',
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 교과서/지도서 (Textbooks)
CREATE TABLE textbooks (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  grade INT NOT NULL DEFAULT 3,
  semester INT NOT NULL DEFAULT 1,
  publisher TEXT,
  file_url TEXT,
  total_pages INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 단원 (Units)
CREATE TABLE units (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  textbook_id UUID REFERENCES textbooks(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sort_order INT DEFAULT 0
);

-- 수업/차시 (Lessons) — 기존 진도표 행
CREATE TABLE lessons (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  legacy_lesson_id TEXT,
  subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
  unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
  lesson_number INT,
  title TEXT,
  pdf_path TEXT,
  start_page INT,
  end_page INT,
  note TEXT,
  extension_count INT DEFAULT 0,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 수업 배치 슬롯 (Lesson Slots) — 기존 bridge sheet
CREATE TABLE lesson_slots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  lesson_id UUID REFERENCES lessons(id) ON DELETE CASCADE,
  slot_date DATE,
  slot_period INT,
  slot_order INT DEFAULT 1,
  status TEXT DEFAULT 'planned' CHECK (status IN ('planned', 'done')),
  source TEXT DEFAULT 'manual',
  memo TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 활동 로그 (Activity Logs)
CREATE TABLE activity_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  action TEXT NOT NULL,
  subject TEXT,
  details TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_lessons_subject ON lessons(subject_id);
CREATE INDEX idx_lessons_unit ON lessons(unit_id);
CREATE INDEX idx_lesson_slots_date ON lesson_slots(slot_date);
CREATE INDEX idx_lesson_slots_lesson ON lesson_slots(lesson_id);
CREATE INDEX idx_lesson_slots_status ON lesson_slots(status);

-- 초기 과목 데이터
INSERT INTO subjects (name, color, sort_order) VALUES
  ('국어', '#005bbf', 1),
  ('수학', '#e85d04', 2),
  ('사회', '#6a994e', 3),
  ('과학', '#9b5de5', 4),
  ('도덕', '#f4a261', 5),
  ('음악', '#e76f51', 6),
  ('미술', '#2a9d8f', 7),
  ('체육', '#264653', 8),
  ('영어', '#d62828', 9),
  ('실과', '#606c38', 10);
