import { useCallback, useEffect, useState } from "react";

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
            if (!res.ok) {
                throw new Error("Server error");
            }
            const json = await res.json();
            setData({ views: json.views || [], subjects: json.subjects || [] });
        } catch (e) {
            setError(e.message);
            showToast(`Load failed: ${e.message}`, "error");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const markDone = async (item) => {
        const recordKey = item.lesson_id || item._record_key || item._row || null;
        const bridgeRow = item._bridge_row ?? null;
        const subject = item["과목"] || item.subject || "";
        const plannedDate = item["계획일"] || item.slot_date || null;
        const title = item["수업내용"] || item.title || item.lesson_id || "lesson";

        setIsProcessing(bridgeRow || recordKey || "done");
        try {
            const res = await fetch(`${API_BASE}/done`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    subject,
                    target_date: plannedDate,
                    record_key: recordKey,
                    bridge_row: bridgeRow,
                }),
            });
            if (!res.ok) {
                throw new Error("Server error");
            }
            const json = await res.json();
            showToast(json.message || `"${title}" updated`);
            await loadData();
        } catch (e) {
            showToast(`Update failed: ${e.message}`, "error");
        } finally {
            setIsProcessing(null);
        }
    };

    const pushSchedule = async (subject, days, fromDate = null) => {
        setIsProcessing(`push-${subject}`);
        try {
            const res = await fetch(`${API_BASE}/push`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ subject, days, from_date: fromDate || null }),
            });
            if (!res.ok) {
                throw new Error("Server error");
            }
            const json = await res.json();
            showToast(json.message || `${subject} shifted`);
            await loadData();
        } catch (e) {
            showToast(`Update failed: ${e.message}`, "error");
        } finally {
            setIsProcessing(null);
        }
    };

    const extendSchedule = async (subject) => {
        setIsProcessing(`ext-${subject}`);
        try {
            const res = await fetch(`${API_BASE}/extend`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ subject }),
            });
            if (!res.ok) {
                throw new Error("Server error");
            }
            const json = await res.json();
            showToast(json.message || `${subject} extended`);
            await loadData();
        } catch (e) {
            showToast(`Update failed: ${e.message}`, "error");
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
