import { supabase } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// PATCH /api/slots — 슬롯 상태 변경 (done ↔ planned)
export async function PATCH(request) {
    try {
        const { id, status } = await request.json();
        if (!id || !['done', 'planned'].includes(status)) {
            return NextResponse.json({ error: 'invalid params' }, { status: 400 });
        }

        const { data, error } = await supabase
            .from('lesson_slots')
            .update({ status })
            .eq('id', id)
            .select()
            .single();

        if (error) throw error;

        // 활동 로그
        await supabase.from('activity_logs').insert({
            action: status === 'done' ? 'lesson_done' : 'lesson_undo',
            details: `slot_id=${id}`,
        });

        return NextResponse.json(data);
    } catch (e) {
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}

// GET /api/slots?week_start=YYYY-MM-DD&week_end=YYYY-MM-DD
export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const weekStart = searchParams.get('week_start');
    const weekEnd = searchParams.get('week_end');

    let query = supabase
        .from('lesson_slots')
        .select(`
      id, slot_date, slot_period, slot_order, status, memo,
      lesson:lessons(
        id, legacy_lesson_id, lesson_number, title, note,
        subject:subjects(id, name, color),
        unit:units(name)
      )
    `)
        .order('slot_date')
        .order('slot_period');

    if (weekStart) query = query.gte('slot_date', weekStart);
    if (weekEnd) query = query.lte('slot_date', weekEnd);

    const { data, error } = await query;
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });

    // 클라이언트가 쓰기 편한 flat 구조로 변환
    const slots = (data || []).map(slot => ({
        id: slot.id,
        slot_date: slot.slot_date,
        slot_period: slot.slot_period,
        slot_order: slot.slot_order,
        status: slot.status,
        memo: slot.memo,
        lesson_id: slot.lesson?.id,
        lesson_number: slot.lesson?.lesson_number,
        title: slot.lesson?.title,
        unit: slot.lesson?.unit?.name,
        subject: slot.lesson?.subject?.name,
        subject_color: slot.lesson?.subject?.color,
        legacy_lesson_id: slot.lesson?.legacy_lesson_id,
    }));

    return NextResponse.json(slots);
}
