import { supabase } from '@/lib/supabase';
import { NextResponse } from 'next/server';

function compareSlotOrder(a, b) {
    if (a.slot_date !== b.slot_date) return a.slot_date.localeCompare(b.slot_date);
    if (a.slot_period !== b.slot_period) return (a.slot_period ?? 0) - (b.slot_period ?? 0);
    if (a.slot_order !== b.slot_order) return (a.slot_order ?? 0) - (b.slot_order ?? 0);
    return String(a.id).localeCompare(String(b.id));
}

function nextSlotOrderInGroup(rows) {
    const values = rows
        .map((row) => Number(row.slot_order))
        .filter((value) => Number.isFinite(value));
    if (values.length === 0) return rows.length + 1;
    return Math.max(...values) + 1;
}

function buildFutureTemplate(subjectRows) {
    const sorted = [...subjectRows].sort(compareSlotOrder);
    const last = sorted[sorted.length - 1];
    if (!last) return null;

    const dates = sorted.map((row) => row.slot_date).filter(Boolean);
    let gapDays = 7;
    for (let i = 1; i < dates.length; i += 1) {
        const prev = new Date(`${dates[i - 1]}T00:00:00`);
        const cur = new Date(`${dates[i]}T00:00:00`);
        const diff = Math.round((cur - prev) / (1000 * 60 * 60 * 24));
        if (diff > 0) gapDays = diff;
    }

    const nextDate = new Date(`${last.slot_date}T00:00:00`);
    nextDate.setDate(nextDate.getDate() + gapDays);
    const yyyy = nextDate.getFullYear();
    const mm = String(nextDate.getMonth() + 1).padStart(2, '0');
    const dd = String(nextDate.getDate()).padStart(2, '0');

    return {
        slot_date: `${yyyy}-${mm}-${dd}`,
        slot_period: last.slot_period,
        slot_order: last.slot_order,
    };
}

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

            const targetSlotKey = {
                slot_date: currentSlot.slot_date,
                slot_period: currentSlot.slot_period,
            };
            if (!targetSlotKey.slot_date) {
                return NextResponse.json({ error: 'target slot has no date' }, { status: 400 });
            }

            const targetGroupRows = subjectSlots.filter(
                (s) => s.slot_date === targetSlotKey.slot_date
                    && Number(s.slot_period) === Number(targetSlotKey.slot_period)
            );
            const targetGroupIds = new Set(targetGroupRows.map((r) => r.id));

            const targetGroupEndIndex = subjectSlots.reduce((acc, row, idx) => (
                targetGroupIds.has(row.id) ? idx : acc
            ), -1);
            if (targetGroupEndIndex < 0) {
                return NextResponse.json({ error: 'target slot group not found' }, { status: 400 });
            }

            const nextPlannedRow = subjectSlots
                .slice(targetGroupEndIndex + 1)
                .find((row) => row.status === 'planned');
            if (!nextPlannedRow) {
                return NextResponse.json({ error: 'there is no later lesson to pull forward' }, { status: 400 });
            }

            const plannedSubjectRows = subjectSlots.filter((row) => row.status === 'planned');
            const sourceIndex = plannedSubjectRows.findIndex((row) => row.id === nextPlannedRow.id);
            if (sourceIndex < 0) {
                return NextResponse.json({ error: 'next planned row not found in subject flow' }, { status: 400 });
            }

            const shiftRows = plannedSubjectRows.slice(sourceIndex + 1);
            const shiftTemplates = plannedSubjectRows
                .slice(sourceIndex)
                .map((row) => ({
                    slot_date: row.slot_date,
                    slot_period: row.slot_period,
                    slot_order: row.slot_order,
                }));

            let updatedSlots = 0;

            const nextSlotOrder = nextSlotOrderInGroup(targetGroupRows);
            const { error: pullUpdateError } = await supabase
                .from('lesson_slots')
                .update({
                    slot_date: targetSlotKey.slot_date,
                    slot_period: targetSlotKey.slot_period,
                    slot_order: nextSlotOrder,
                })
                .eq('id', nextPlannedRow.id);
            if (pullUpdateError) throw pullUpdateError;
            updatedSlots += 1;

            for (let i = 0; i < shiftRows.length; i += 1) {
                const row = shiftRows[i];
                const tpl = shiftTemplates[i + 1];
                if (!tpl) continue;
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
