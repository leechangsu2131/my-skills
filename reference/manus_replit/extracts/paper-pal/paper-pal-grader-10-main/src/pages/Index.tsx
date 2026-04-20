import { useState, useCallback } from "react";
import AppHeader from "@/components/AppHeader";
import StepIndicator from "@/components/StepIndicator";
import AnswerKeyStep from "@/components/AnswerKeyStep";
import ExamUploadStep from "@/components/ExamUploadStep";
import ResultsStep from "@/components/ResultsStep";
import type { AppStep, AnswerKey, ExamResult } from "@/types/exam";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";

const Index = () => {
  const [step, setStep] = useState<AppStep>('upload-answer-key');
  const [answerKeys, setAnswerKeys] = useState<AnswerKey[]>([]);
  const [examResults, setExamResults] = useState<ExamResult[]>([]);

  const handleAnswerKeyComplete = useCallback((keys: AnswerKey[]) => {
    setAnswerKeys(keys);
    setStep('upload-exams');
  }, []);

  const handleExamsComplete = useCallback((results: ExamResult[]) => {
    setExamResults(results);
    setStep('results');
  }, []);

  const handleUploadAnalysis = useCallback((studentIndex: number, content: string) => {
    setExamResults(prev =>
      prev.map((r, i) => (i === studentIndex ? { ...r, analysisContent: content } : r))
    );
  }, []);

  const handleReset = () => {
    setStep('upload-answer-key');
    setAnswerKeys([]);
    setExamResults([]);
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="container max-w-3xl py-4 px-4">
        <StepIndicator currentStep={step} />

        {step !== 'upload-answer-key' && (
          <div className="flex justify-end mb-4">
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <RotateCcw className="w-4 h-4 mr-1" /> 처음부터 다시
            </Button>
          </div>
        )}

        {step === 'upload-answer-key' && (
          <div className="glass-card rounded-xl p-6">
            <h2 className="text-lg font-display font-bold mb-1 text-foreground">1. 답안지 등록</h2>
            <p className="text-sm text-muted-foreground mb-6">정답과 배점을 직접 입력하거나, 답안지 PDF를 업로드하여 자동 추출합니다.</p>
            <AnswerKeyStep onComplete={handleAnswerKeyComplete} />
          </div>
        )}

        {step === 'upload-exams' && (
          <div className="glass-card rounded-xl p-6">
            <h2 className="text-lg font-display font-bold mb-1 text-foreground">2. 학생 시험지 업로드</h2>
            <p className="text-sm text-muted-foreground mb-6">학생의 시험지 PDF를 업로드하면 OCR로 답안을 추출하고 자동 채점합니다.</p>
            <ExamUploadStep answerKeys={answerKeys} onComplete={handleExamsComplete} />
          </div>
        )}

        {step === 'results' && (
          <div>
            <h2 className="text-lg font-display font-bold mb-1 text-foreground">3. 채점 결과</h2>
            <p className="text-sm text-muted-foreground mb-6">각 학생의 채점 결과를 확인하고 PDF로 다운로드하세요.</p>
            <ResultsStep results={examResults} onUploadAnalysis={handleUploadAnalysis} />
          </div>
        )}
      </main>
    </div>
  );
};

export default Index;
