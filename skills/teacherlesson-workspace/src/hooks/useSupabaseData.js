"use client";

import { useState, useEffect, useCallback } from "react";
import { getWeekRange, todayStr } from "@/lib/demoData";

function toLocalDateStr(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

/**
 * Supabase 데이터 훅
 * — API 라우트를 통해 실제 DB 데이터를 로드
 * — 실패 시 demoData 폴백
 */
export function useSupabaseData({ boardDate, selectedSubject }) {
    const [slots, setSlots] = useState([]);
    const [subjects, setSubjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [usingDemo, setUsingDemo] = useState(false);

    const week = getWeekRange(boardDate);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            // 1. 과목 목록
            const subjRes = await fetch("/api/subjects");
            if (!subjRes.ok) throw new Error("subjects fetch failed");
            const subjData = await subjRes.json();

            // 2. 주간 슬롯 (± 4주 범위로 넓게 가져와서 클라이언트에서 필터)
            const fourWeeksAgo = new Date(week.start + "T00:00:00");
            fourWeeksAgo.setDate(fourWeeksAgo.getDate() - 28);
            const fourWeeksLater = new Date(week.end + "T00:00:00");
            fourWeeksLater.setDate(fourWeeksLater.getDate() + 28);

            const start = toLocalDateStr(fourWeeksAgo);
            const end = toLocalDateStr(fourWeeksLater);

            const slotRes = await fetch(`/api/slots?week_start=${start}&week_end=${end}`);
            if (!slotRes.ok) throw new Error("slots fetch failed");
            const slotData = await slotRes.json();

            setSubjects(subjData);
            setSlots(slotData);
            setUsingDemo(false);
        } catch (e) {
            console.warn("[useSupabaseData] falling back to demo data:", e.message);
            // 폴백: 데모 데이터
            const { SUBJECTS, DEMO_SLOTS } = await import("@/lib/demoData");
            setSubjects(SUBJECTS);
            setSlots(DEMO_SLOTS);
            setUsingDemo(true);
        } finally {
            setLoading(false);
        }
    }, [week.start, week.end]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const markDone = useCallback(async (slotId) => {
        // 낙관적 업데이트
        setSlots((prev) =>
            prev.map((s) =>
                s.id === slotId
                    ? { ...s, status: s.status === "done" ? "planned" : "done" }
                    : s
            )
        );

        if (usingDemo) return;

        try {
            const slot = slots.find((s) => s.id === slotId);
            const newStatus = slot?.status === "done" ? "planned" : "done";
            await fetch("/api/slots", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: slotId, status: newStatus }),
            });
        } catch (e) {
            console.error("markDone failed:", e);
            await fetchData(); // 실패 시 롤백
        }
    }, [slots, usingDemo, fetchData]);

    const adjustPacing = useCallback(async (slotId, pacing) => {
        if (!['extend', 'pull_next'].includes(pacing)) return;
        if (usingDemo) return;
        try {
            const res = await fetch("/api/slots", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: slotId, pacing }),
            });
            if (!res.ok) {
                const payload = await res.json().catch(() => ({}));
                throw new Error(payload.error || "slot pacing adjust failed");
            }
            await res.json().catch(() => ({}));
            await fetchData();
            return true;
        } catch (e) {
            console.error("adjustPacing failed:", e);
            await fetchData();
            return false;
        }
    }, [usingDemo, fetchData]);

    const copyPdfPath = useCallback(async (slot) => {
        const value = slot?.pdf_path;
        if (!value) return false;
        try {
            await navigator.clipboard.writeText(value);
            return true;
        } catch {
            return false;
        }
    }, []);

    const openPdf = useCallback((slot) => {
        if (!slot?.id) return false;
        window.open(`/api/pdf/${slot.id}`, "_blank", "noopener,noreferrer");
        return true;
    }, []);

    // 필터된 슬롯 (과목 필터 적용)
    const filteredSlots = selectedSubject
        ? slots.filter((s) => s.subject === selectedSubject)
        : slots;

    // 이번 주 슬롯
    const weekSlots = filteredSlots.filter(
        (s) => s.slot_date >= week.start && s.slot_date <= week.end
    );

    // 오늘 슬롯
    const today = todayStr();
    const todaySlots = filteredSlots.filter((s) => s.slot_date === today);

    return {
        slots: filteredSlots,
        allSlots: slots,
        weekSlots,
        todaySlots,
        subjects,
        loading,
        usingDemo,
        markDone,
        adjustPacing,
        copyPdfPath,
        openPdf,
        refetch: fetchData,
    };
}
