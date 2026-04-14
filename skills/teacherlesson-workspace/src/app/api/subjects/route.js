import { supabase } from '@/lib/supabase';
import { NextResponse } from 'next/server';

// GET /api/subjects
export async function GET() {
    const { data, error } = await supabase
        .from('subjects')
        .select('id, name, color, sort_order')
        .order('sort_order');

    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
    return NextResponse.json(data || []);
}
