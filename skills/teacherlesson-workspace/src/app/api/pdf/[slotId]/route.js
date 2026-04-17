import { supabase } from '@/lib/supabase';
import { NextResponse } from 'next/server';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

export async function GET(_request, { params }) {
    try {
        const resolvedParams = await Promise.resolve(params);
        const slotId = resolvedParams?.slotId;
        if (!slotId) {
            return NextResponse.json({ error: 'slot id is required' }, { status: 400 });
        }

        const { data, error } = await supabase
            .from('lesson_slots')
            .select('lesson:lesson_lessons(pdf_path, title)')
            .eq('id', slotId)
            .single();

        if (error) return NextResponse.json({ error: error.message }, { status: 500 });

        const pdfPath = data?.lesson?.pdf_path;
        if (!pdfPath) {
            return NextResponse.json({ error: 'pdf path not found' }, { status: 404 });
        }

        const normalizedPath = path.normalize(pdfPath);
        const fileBuffer = await readFile(normalizedPath);
        return new NextResponse(fileBuffer, {
            status: 200,
            headers: {
                'Content-Type': 'application/pdf',
                'Cache-Control': 'no-store',
            },
        });
    } catch (e) {
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}
