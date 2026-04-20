import { Check } from "lucide-react";
import type { AppStep } from "@/types/exam";

const steps: { key: AppStep; label: string }[] = [
  { key: 'upload-answer-key', label: '답안지 등록' },
  { key: 'upload-exams', label: '시험지 업로드' },
  { key: 'review-answers', label: '답안 확인' },
  { key: 'grading', label: '채점 중' },
  { key: 'results', label: '결과' },
];

const StepIndicator = ({ currentStep }: { currentStep: AppStep }) => {
  const currentIdx = steps.findIndex(s => s.key === currentStep);

  return (
    <div className="flex items-center gap-1 py-6">
      {steps.map((step, idx) => {
        const isDone = idx < currentIdx;
        const isCurrent = idx === currentIdx;
        return (
          <div key={step.key} className="flex items-center gap-1 flex-1">
            <div className="flex items-center gap-2 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold shrink-0 transition-colors ${
                  isDone
                    ? 'bg-success text-success-foreground'
                    : isCurrent
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {isDone ? <Check className="w-4 h-4" /> : idx + 1}
              </div>
              <span
                className={`text-xs font-medium hidden sm:block ${
                  isCurrent ? 'text-foreground' : 'text-muted-foreground'
                }`}
              >
                {step.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`h-0.5 flex-1 mx-1 rounded ${
                  idx < currentIdx ? 'bg-success' : 'bg-border'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
};

export default StepIndicator;
