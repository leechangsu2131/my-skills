import { buildFutureTemplate, buildPullNextPlan, compareSlotOrder } from '@/utils/slotPacing.mjs';
import { supabase } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// PATCH /api/slots — 슬롯 상태 변경 (done ↔ planned)
export async function PATCH(request) {
    try {
        const { id, status, pacing } = await request.json();
        if (!id) {
            return NextResponse.json({ error: 'invalid params' }, { status: 400 });
        }

        // 슬롯 상태 토글
        if (status) {
            if (!['done', 'planned'].includes(status)) {
                return NextResponse.json({ error: 'invalid status' }, { status: 400 });
            }

            const { data, error } = await supabase
                .from('lesson_slots')
                .update({ status })
                .eq('id', id)
                .select()
                .single();

            if (error) throw error;

            await supabase.from('lesson_activity_logs').insert({
                action: status === 'done' ? 'lesson_done' : 'lesson_undo',
                details: `slot_id=${id}`,
            });

            return NextResponse.json(data);
        }

        // 진도 조정: 현재 수업 1차시 연장 / 다음 차시 당겨오기
        if (pacing) {
            if (!['extend', 'pull_next'].includes(pacing)) {
                return NextResponse.json({ error: 'invalid pacing action' }, { status: 400 });
            }

            const { data: currentSlot, error: currentSlotError } = await supabase
                .from('lesson_slots')
                .select(`
                  id, lesson_id, slot_date, slot_period, slot_order, status,
                  lesson:lesson_lessons(subject_id)
                `)
                .eq('id', id)
                .single();
            if (currentSlotError) throw currentSlotError;

            const subjectId = currentSlot.lesson?.subject_id;
            if (!subjectId) {
                return NextResponse.json({ error: 'subject not found for slot' }, { status: 400 });
            }

            const { data: allSlots, error: allSlotsError } = await supabase
                .from('lesson_slots')
                .select(`
                  id, lesson_id, slot_date, slot_period, slot_order, status,
                  lesson:lesson_lessons(subject_id)
                `);
            if (allSlotsError) throw allSlotsError;

            const subjectSlots = (allSlots || [])
                .filter((s) => s.lesson?.subject_id === subjectId)
                .sort(compareSlotOrder);

            if (pacing === 'extend') {
                const plannedSubjectRows = subjectSlots.filter((s) => s.status === 'planned');
                const targetIndex = plannedSubjectRows.findIndex((s) => s.id === id);
                if (targetIndex < 0) {
                    return NextResponse.json({ error: 'extend target must be a planned slot' }, { status: 400 });
                }

                const targetLessonId = plannedSubjectRows[targetIndex].lesson_id;
                let insertionIndex = targetIndex + 1;
                while (
                    insertionIndex < plannedSubjectRows.length
                    && plannedSubjectRows[insertionIndex].lesson_id === targetLessonId
                ) {
                    insertionIndex += 1;
                }

                const templates = plannedSubjectRows.map((row) => ({
                    slot_date: row.slot_date,
                    slot_period: row.slot_period,
                    slot_order: row.slot_order,
                }));
                const futureTemplate = buildFutureTemplate(plannedSubjectRows);
                if (!futureTemplate) {
                    return NextResponse.json({ error: 'cannot build future slot template' }, { status: 400 });
                }
                templates.push(futureTemplate);

                const clonedRow = {
                    id: '__new__',
                    lesson_id: targetLessonId,
                    status: 'planned',
                };
                const rewrittenRows = [
                    ...plannedSubjectRows.slice(0, insertionIndex),
                    clonedRow,
                    ...plannedSubjectRows.slice(insertionIndex),
                ];

                let updatedSlots = 0;
                for (let i = 0; i < rewrittenRows.length; i += 1) {
                    const row = rewrittenRows[i];
                    const tpl = templates[i];
                    if (!tpl) continue;

                    if (row.id === '__new__') {
                        const { error: insertError } = await supabase
                            .from('lesson_slots')
                            .insert({
                                lesson_id: row.lesson_id,
                                slot_date: tpl.slot_date,
                                slot_period: tpl.slot_period,
                                slot_order: tpl.slot_order,
                                status: 'planned',
                                source: 'manual_extend',
                                memo: '',
                            });
                        if (insertError) throw insertError;
                        updatedSlots += 1;
                        continue;
                    }

                    const changed = (
                        row.slot_date !== tpl.slot_date
                        || Number(row.slot_period) !== Number(tpl.slot_period)
                        || Number(row.slot_order) !== Number(tpl.slot_order)
                    );
                    if (!changed) continue;

                    const { error: updateError } = await supabase
                        .from('lesson_slots')
                        .update({
                            slot_date: tpl.slot_date,
                            slot_period: tpl.slot_period,
                            slot_order: tpl.slot_order,
                        })
                        .eq('id', row.id);
                    if (updateError) throw updateError;
                    updatedSlots += 1;
                }

                await supabase.from('lesson_activity_logs').insert({
                    action: 'lesson_extend_one_more_slot',
                    details: `slot_id=${id};updated_slots=${updatedSlots}`,
                });

                return NextResponse.json({ id, pacing, updated_slots: updatedSlots });
            }

            let updates;
            try {
                ({ updates } = buildPullNextPlan({
                    currentSlot,
                    subjectSlots,
                }));
            } catch (planError) {
                return NextResponse.json({ error: planError.message }, { status: 400 });
            }

            for (const update of updates) {
                const { error: updateError } = await supabase
                    .from('lesson_slots')
                    .update({
                        slot_date: update.slot_date,
                        slot_period: update.slot_period,
                        slot_order: update.slot_order,
                    })
                    .eq('id', update.id);
                if (updateError) throw updateError;
            }

            const updatedSlots = updates.length;

            await supabase.from('lesson_activity_logs').insert({
                action: 'lesson_pull_next_into_current',
                details: `slot_id=${id};updated_slots=${updatedSlots}`,
            });

            return NextResponse.json({ id, pacing, updated_slots: updatedSlots });
        }

        return NextResponse.json({ error: 'no action provided' }, { status: 400 });
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
      lesson:lesson_lessons(
        id, legacy_lesson_id, lesson_number, title, note, pdf_path,
        subject:lesson_subjects(id, name, color),
        unit:lesson_units(name)
      )
    `)
        .order('slot_date')
        .order('slot_period');

    if (weekStart) query = query.gte('slot_date', weekStart);
    if (weekEnd) query = query.lte('slot_date', weekEnd);

    const { data, error } = await query;
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });

    const slots = (data || []).map((slot) => ({
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
        pdf_path: slot.lesson?.pdf_path,
    }));

    return NextResponse.json(slots);
}
