import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://127.0.0.1:5000/api";

export function useScheduleData() {
    const [data, setData] = useState({ views: [], subjects: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [toast, setToast] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);

    const showToast = (msg, type = "success") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/dashboard`);
            if (!res.ok) throw new Error("서버 응답 오류");
            const json = await res.json();
            setData({ views: json.views || [], subjects: json.subjects || [] });
        } catch (e) {
            setError(e.message);
            showToast("데이터 로드 실패: " + e.message, "error");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const markDone = async (item) => {
        setIsProcessing(item._row || item.행번호);
        try {
            const res = await fetch(`${API_BASE}/done`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ subject: item.과목, target_date: item.계획일 })
            });
            if (!res.ok) throw new Error("서버 에러");
            showToast(`✅ "${item.수업내용}" 완료 처리됨`);
            await loadData();
        } catch (e) {
            showToast("업데이트 실패: " + e.message, "error");
        } finally {
            setIsProcessing(null);
        }
    };

    const pushSchedule = async (subj, days, fromDate = null) => {
        setIsProcessing(`push-${subj}`);
        try {
            const res = await fetch(`${API_BASE}/push`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ subject: subj, days, from_date: fromDate || null })
            });
            if (!res.ok) throw new Error("서버 에러");
            showToast(`📅 ${subj} 연기 완료`);
            await loadData();
        } catch (e) {
            showToast("실패: " + e.message, "error");
        } finally {
            setIsProcessing(null);
        }
    };

    const extendSchedule = async (subj) => {
        setIsProcessing(`ext-${subj}`);
        try {
            const res = await fetch(`${API_BASE}/extend`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ subject: subj })
            });
            if (!res.ok) throw new Error("서버 에러");
            showToast(`⏳ ${subj} 연장 완료`);
            await loadData();
        } catch (e) {
            showToast("실패: " + e.message, "error");
        } finally {
            setIsProcessing(null);
        }
    };

    return {
        ...data,
        loading,
        error,
        toast,
        isProcessing,
        loadData,
        markDone,
        pushSchedule,
        extendSchedule,
    };
}
