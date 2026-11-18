const SUBJECT_ORDER = [
    "국어",
    "수학",
    "사회",
    "과학",
    "도덕",
    "영어",
    "음악",
    "미술",
    "체육",
    "창체",
];

export const SUBJECT_COLORS = {
    국어: {
        bg: "bg-amber-50",
        accent: "text-amber-700",
        border: "border-amber-200",
        fill: "#f59e0b",
        icon: "KO",
    },
    수학: {
        bg: "bg-emerald-50",
        accent: "text-emerald-600",
        border: "border-emerald-200",
        fill: "#34d399",
        icon: "MA",
    },
    사회: {
        bg: "bg-blue-50",
        accent: "text-blue-600",
        border: "border-blue-200",
        fill: "#60a5fa",
        icon: "SO",
    },
    과학: {
        bg: "bg-teal-50",
        accent: "text-teal-600",
        border: "border-teal-200",
        fill: "#2dd4bf",
        icon: "SC",
    },
    도덕: {
        bg: "bg-lime-50",
        accent: "text-lime-700",
        border: "border-lime-200",
        fill: "#84cc16",
        icon: "MO",
    },
    영어: {
        bg: "bg-indigo-50",
        accent: "text-indigo-600",
        border: "border-indigo-200",
        fill: "#818cf8",
        icon: "EN",
    },
    음악: {
        bg: "bg-orange-50",
        accent: "text-orange-600",
        border: "border-orange-200",
        fill: "#fb923c",
        icon: "MU",
    },
    미술: {
        bg: "bg-pink-50",
        accent: "text-pink-600",
        border: "border-pink-200",
        fill: "#f472b6",
        icon: "AR",
    },
    체육: {
        bg: "bg-rose-50",
        accent: "text-rose-600",
        border: "border-rose-200",
        fill: "#fb7185",
        icon: "PE",
    },
    창체: {
        bg: "bg-yellow-50",
        accent: "text-yellow-700",
        border: "border-yellow-200",
        fill: "#facc15",
        icon: "CC",
    },
};

function normalizeSubject(subject) {
    return String(subject || "").trim();
}

export function getSubjectStyle(subject) {
    return (
        SUBJECT_COLORS[normalizeSubject(subject)] || {
            bg: "bg-stone-100",
            accent: "text-stone-600",
            border: "border-stone-200",
            fill: "#a8a29e",
            icon: "ET",
        }
    );
}

export function subjectMatches(subject, selectedSubject) {
    if (!selectedSubject) {
        return true;
    }

    return normalizeSubject(subject) === normalizeSubject(selectedSubject);
}

export function sortSubjects(subjects) {
    const uniqueSubjects = Array.from(
        new Set((Array.isArray(subjects) ? subjects : []).map((subject) => normalizeSubject(subject)).filter(Boolean)),
    );
    const collator = new Intl.Collator("ko-KR");

    return uniqueSubjects.sort((left, right) => {
        const leftIndex = SUBJECT_ORDER.indexOf(left);
        const rightIndex = SUBJECT_ORDER.indexOf(right);

        if (leftIndex !== -1 || rightIndex !== -1) {
            if (leftIndex === -1) {
                return 1;
            }
            if (rightIndex === -1) {
                return -1;
            }
            return leftIndex - rightIndex;
        }

        return collator.compare(left, right);
    });
}
