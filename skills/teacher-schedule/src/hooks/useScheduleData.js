import { useCallback, useEffect, useState } from "react";
import {
    getBridgeRow,
    getPdfPath,
    getPlannedDate,
    getRecordKey,
    getSubject,
    getTitle,
} from "../lib/lessonFields";

const API_BASE = "http://127.0.0.1:5000/api";

async function requestJson(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, options);
    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.status === "error") {
        throw new Error(payload.message || "요청을 처리하지 못했습니다.");
    }

    return payload;
}

async function copyTextToClipboard(value) {
    if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
        return;
    }

    const textArea = document.createElement("textarea");
    textArea.value = value;
    textArea.setAttribute("readonly", "");
    textArea.style.position = "fixed";
    textArea.style.top = "-9999px";
    textArea.style.opacity = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    textArea.setSelectionRange(0, textArea.value.length);

    const copied = typeof document.execCommand === "function" && document.execCommand("copy");
    document.body.removeChild(textArea);

    if (!copied) {
        throw new Error("클립보드 복사에 실패했습니다.");
    }
}

export function useScheduleData() {
    const [data, setData] = useState({ views: [], subjects: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [toast, setToast] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [isProcessing, setIsProcessing] = useState(null);
    const [boardDate, setBoardDate] = useState(() => new Date().toISOString().slice(0, 10));

    const showToast = useCallback((msg, type = "success") => {
        setToast({ msg, type });
        window.clearTimeout(showToast.timerId);
        showToast.timerId = window.setTimeout(() => setToast(null), 3200);
    }, []);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            if (boardDate) {
                params.set("board_date", boardDate);
            }
            const payload = await requestJson(`/dashboard${params.toString() ? `?${params.toString()}` : ""}`);
            setData({ views: payload.views || [], subjects: payload.subjects || [] });
            setLastUpdated(new Date().toISOString());
        } catch (requestError) {
            setError(requestError.message);
            showToast(`불러오기 실패: ${requestError.message}`, "error");
        } finally {
            setLoading(false);
        }
    }, [boardDate, showToast]);

    useEffect(() => {
        loadData();
        return () => window.clearTimeout(showToast.timerId);
    }, [loadData, showToast]);

    const runAction = useCallback(
        async (processingKey, path, body, successMessage) => {
            setIsProcessing(processingKey);
            try {
                const payload = await requestJson(path, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body),
                });
                showToast(payload.message || successMessage);
                await loadData();
                return payload.result;
            } catch (requestError) {
                showToast(requestError.message, "error");
                throw requestError;
            } finally {
                setIsProcessing(null);
            }
        },
        [loadData, showToast],
    );

    const markDone = useCallback(
        async (item) => {
            const recordKey = getRecordKey(item);
            const bridgeRow = getBridgeRow(item);
            const subject = getSubject(item);
            const plannedDate = getPlannedDate(item) || null;
            const title = getTitle(item);

            return runAction(
                `done-${bridgeRow || recordKey}`,
                "/done",
                {
                    subject,
                    target_date: plannedDate,
                    record_key: recordKey || null,
                    bridge_row: bridgeRow ?? null,
                },
                `"${title}" 수업을 완료 처리했습니다.`,
            );
        },
        [runAction],
    );

    const pushSchedule = useCallback(
        async (subject, days, fromDate = null) =>
            runAction(
                `push-${subject}`,
                "/push",
                { subject, days, from_date: fromDate || null },
                `${subject} 일정이 이동되었습니다.`,
            ),
        [runAction],
    );

    const extendSchedule = useCallback(
        async (subject, rowNumber = null, bridgeRow = null) =>
            runAction(
                `extend-${subject}-${bridgeRow || rowNumber || "next"}`,
                "/extend",
                {
                    subject,
                    row_number: rowNumber ?? null,
                    bridge_row: bridgeRow ?? null,
                },
                `${subject} 수업을 1차시 연장했습니다.`,
            ),
        [runAction],
    );

    const moveLesson = useCallback(
        async (item, direction) => {
            const bridgeRow = getBridgeRow(item);
            const subject = getSubject(item);
            if (!bridgeRow) {
                throw new Error("이동 가능한 배치 행을 찾지 못했습니다.");
            }

            return runAction(
                `move-${bridgeRow}-${direction}`,
                "/move",
                {
                    bridge_row: bridgeRow,
                    direction,
                    subject,
                },
                direction === "earlier" ? "수업을 앞당겼습니다." : "수업을 뒤로 보냈습니다.",
            );
        },
        [runAction],
    );

    const pullLessonForward = useCallback(
        async (item) => {
            const bridgeRow = getBridgeRow(item);
            const subject = getSubject(item);
            if (!bridgeRow) {
                throw new Error("앞당길 배치 행을 찾지 못했습니다.");
            }

            return runAction(
                `pull-${bridgeRow}`,
                "/pull",
                {
                    bridge_row: bridgeRow,
                    subject,
                },
                "다음 차시를 현재 수업 자리로 당겨왔습니다.",
            );
        },
        [runAction],
    );

    const swapLessons = useCallback(
        async (firstBridgeRow, secondBridgeRow) =>
            runAction(
                `swap-${firstBridgeRow}-${secondBridgeRow}`,
                "/swap",
                {
                    first_bridge_row: firstBridgeRow,
                    second_bridge_row: secondBridgeRow,
                },
                "두 수업 시간을 서로 바꿨습니다.",
            ),
        [runAction],
    );

    const copyPdfPath = useCallback(
        async (item) => {
            const pdfPath = getPdfPath(item);
            if (!pdfPath) {
                showToast("복사할 PDF 경로가 없습니다.", "error");
                return false;
            }

            try {
                await copyTextToClipboard(pdfPath);
                showToast("PDF 경로를 클립보드에 복사했습니다.");
                return true;
            } catch (copyError) {
                showToast(copyError.message || "PDF 경로 복사에 실패했습니다.", "error");
                return false;
            }
        },
        [showToast],
    );

    return {
        ...data,
        loading,
        error,
        toast,
        lastUpdated,
        isProcessing,
        boardDate,
        setBoardDate,
        loadData,
        markDone,
        pushSchedule,
        extendSchedule,
        moveLesson,
        pullLessonForward,
        swapLessons,
        copyPdfPath,
    };
}
