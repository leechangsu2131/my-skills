// Step 2: JSON 파일 → Supabase 업로드 (Node.js fetch 사용)
// 실행: node scripts/upload_to_supabase.mjs

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// .env.local 읽기
const envPath = join(__dirname, '..', '.env.local');
const env = Object.fromEntries(
    readFileSync(envPath, 'utf-8')
        .split('\n')
        .filter(line => line.trim() && !line.startsWith('#'))
        .map(line => line.split('=').map((p, i) => i === 0 ? p.trim() : line.slice(line.indexOf('=') + 1).trim()))
);

const SUPABASE_URL = env['NEXT_PUBLIC_SUPABASE_URL'];
const SUPABASE_KEY = env['NEXT_PUBLIC_SUPABASE_ANON_KEY'];

if (!SUPABASE_URL || SUPABASE_URL.includes('your-project')) {
    console.error('❌ .env.local에 SUPABASE_URL이 없습니다.');
    process.exit(1);
}

const dataDir = join(__dirname, 'migrated_data');

async function supabasePost(table, rows, options = {}) {
    if (!rows.length) return [];
    const url = `${SUPABASE_URL}/rest/v1/${table}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'apikey': SUPABASE_KEY,
            'Authorization': `Bearer ${SUPABASE_KEY}`,
            'Prefer': 'return=representation',
        },
        body: JSON.stringify(rows),
    });
    if (!res.ok) {
        const err = await res.text();
        throw new Error(`[${table}] HTTP ${res.status}: ${err}`);
    }
    return res.json();
}

async function supabaseGet(table, select = '*') {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}?select=${select}`, {
        headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` },
    });
    if (!res.ok) throw new Error(`GET ${table} failed: ${res.status}`);
    return res.json();
}

function readJson(filename) {
    try {
        return JSON.parse(readFileSync(join(dataDir, filename), 'utf-8'));
    } catch {
        console.warn(`  ⚠️  ${filename} 없음 — 건너뜀`);
        return [];
    }
}

async function main() {
    console.log('='.repeat(55));
    console.log('🚀 Step 2: JSON → Supabase 업로드');
    console.log(`🔗 ${SUPABASE_URL}`);
    console.log('='.repeat(55));

    // 1. subjects
    const subjects = readJson('subjects.json');
    console.log(`\n📤 과목 ${subjects.length}개 업로드 중...`);
    let subjectMap = {};
    try {
        const result = await supabasePost('subjects', subjects);
        subjectMap = Object.fromEntries(result.map(r => [r.name, r.id]));
        console.log(`   ✅ ${result.length}개 완료`);
    } catch (e) {
        console.log(`   ⚠️  INSERT 실패 (이미 있음) → 기존 조회`);
        const existing = await supabaseGet('subjects', 'id,name');
        subjectMap = Object.fromEntries(existing.map(r => [r.name, r.id]));
        console.log(`   ℹ️  기존 ${Object.keys(subjectMap).length}개 사용`);
    }

    // 2. units
    const units = readJson('units.json');
    console.log(`\n📤 단원 ${units.length}개 업로드 중...`);
    const unitRows = units
        .map(u => ({ subject_id: subjectMap[u.subject_name], name: u.name, sort_order: u.sort_order }))
        .filter(u => u.subject_id);
    let unitMap = {};
    if (unitRows.length) {
        try {
            const result = await supabasePost('units', unitRows);
            unitMap = Object.fromEntries(result.map(r => [`${r.subject_id}::${r.name}`, r.id]));
            console.log(`   ✅ ${result.length}개 완료`);
        } catch (e) {
            console.log(`   ⚠️  단원 업로드 실패: ${e.message}`);
        }
    }

    // 3. lessons (배치 처리)
    const lessons = readJson('lessons.json');
    console.log(`\n📤 수업(차시) ${lessons.length}개 업로드 중...`);
    const lessonRows = lessons
        .map(l => {
            const subjectId = subjectMap[l.subject_name];
            const unitId = subjectId ? unitMap[`${subjectId}::${l.unit_name}`] : undefined;
            return {
                legacy_lesson_id: l.legacy_lesson_id,
                subject_id: subjectId,
                unit_id: unitId || null,
                lesson_number: l.lesson_number,
                title: l.title,
                pdf_path: l.pdf_path,
                start_page: l.start_page,
                end_page: l.end_page,
                note: l.note,
                extension_count: l.extension_count || 0,
                sort_order: l.sort_order,
            };
        })
        .filter(l => l.subject_id);

    // 배치 단위로 나눠 업로드 (Supabase 기본 최대 1000행)
    const BATCH = 200;
    let lessonResult = [];
    for (let i = 0; i < lessonRows.length; i += BATCH) {
        const batch = lessonRows.slice(i, i + BATCH);
        const res = await supabasePost('lessons', batch);
        lessonResult.push(...res);
        process.stdout.write(`   ${lessonResult.length}/${lessonRows.length}\r`);
    }
    const lessonIdMap = Object.fromEntries(
        lessonResult.filter(r => r.legacy_lesson_id).map(r => [r.legacy_lesson_id, r.id])
    );
    console.log(`   ✅ ${lessonResult.length}개 완료      `);

    // 4. lesson_slots
    const slots = readJson('lesson_slots.json');
    console.log(`\n📤 슬롯 ${slots.length}개 업로드 중...`);
    const slotRows = slots
        .map(s => {
            const lessonId = lessonIdMap[s.legacy_lesson_id];
            if (!lessonId || !s.slot_date) return null;
            return {
                lesson_id: lessonId,
                slot_date: s.slot_date,
                slot_period: s.slot_period,
                slot_order: s.slot_order || 1,
                status: ['planned', 'done'].includes(s.status) ? s.status : 'planned',
                source: s.source || 'migrated',
                memo: s.memo || null,
            };
        })
        .filter(Boolean);

    let slotResult = [];
    for (let i = 0; i < slotRows.length; i += BATCH) {
        const res = await supabasePost('lesson_slots', slotRows.slice(i, i + BATCH));
        slotResult.push(...res);
        process.stdout.write(`   ${slotResult.length}/${slotRows.length}\r`);
    }
    console.log(`   ✅ ${slotResult.length}개 완료      `);

    console.log('\n' + '='.repeat(55));
    console.log('🎉 Supabase 업로드 완료!');
    console.log('='.repeat(55));
}

main().catch(err => {
    console.error('\n❌ 업로드 실패:', err.message);
    process.exit(1);
});
