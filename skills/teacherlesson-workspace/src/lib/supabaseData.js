/**
 * Supabase data fetching helpers
 * Server-side only — uses service role when available, falls back to anon key
 */

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, '');
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// SSL 우회 (Windows 환경 대응) — 개발용
if (process.env.NODE_ENV === 'development') {
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
}

async function sbFetch(path, options = {}) {
    if (!SUPABASE_URL || SUPABASE_URL.includes('your-project')) return null;
    const url = `${SUPABASE_URL}/rest/v1${path}`;
    try {
        const res = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                apikey: SUPABASE_KEY,
                Authorization: `Bearer ${SUPABASE_KEY}`,
                Prefer: 'return=representation',
                ...options.headers,
            },
        });
        if (!res.ok) {
            const err = await res.text();
            console.error(`[Supabase] ${path} → ${res.status}: ${err}`);
            return null;
        }
        return res.json();
    } catch (e) {
        console.error(`[Supabase] fetch error: ${e.message}`);
        return null;
    }
}

/** 오늘 날짜를 기준으로 대시보드 데이터 로드 */
export async function loadDashboardData(weekStart, weekEnd) {
    const [subjects, slots, lessons] = await Promise.all([
        sbFetch('/subjects?select=id,name,color,sort_order&order=sort_order'),
        sbFetch(
            `/lesson_slots?select=id,slot_date,slot_period,slot_order,status,memo,lesson:lessons(id,legacy_lesson_id,lesson_number,title,note,subject:subjects(id,name,color),unit:units(name))&slot_date=gte.${weekStart}&slot_date=lte.${weekEnd}&order=slot_date,slot_period`
        ),
        sbFetch('/lessons?select=id,legacy_lesson_id,lesson_number,title,subject:subjects(name,color),unit:units(name)&order=sort_order'),
    ]);

    return { subjects, slots, lessons };
}

/** 슬롯 상태 업데이트 */
export async function updateSlotStatus(slotId, status) {
    return sbFetch(`/lesson_slots?id=eq.${slotId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
    });
}

/** 활동 로그 추가 */
export async function logActivity(action, subject, details) {
    return sbFetch('/activity_logs', {
        method: 'POST',
        body: JSON.stringify({ action, subject, details }),
    });
}
