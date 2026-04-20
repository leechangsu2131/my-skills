import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight, Loader2 } from "lucide-react";
import PdfDropZone from "./PdfDropZone";
import type { AnswerKey, StudentAnswer, ExamResult } from "@/types/exam";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";

interface ExamUploadStepProps {
  answerKeys: AnswerKey[];
  onComplete: (results: ExamResult[]) => void;
}

const ExamUploadStep = ({ answerKeys, onComplete }: ExamUploadStepProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const processExams = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setProgress(0);

    const results: ExamResult[] = [];

    for (let i = 0; i < files.length; i++) {
      try {
        const file = files[i];
        const reader = new FileReader();
        const base64 = await new Promise<string>((resolve, reject) => {
          reader.onload = () => resolve((reader.result as string).split(',')[1]);
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });

        const { data, error } = await supabase.functions.invoke('ocr-extract', {
          body: {
            image: base64,
            type: 'student-exam',
            questionCount: answerKeys.length,
          },
        });

        if (error) throw error;

        const studentAnswers: StudentAnswer[] = data?.answers || [];
        const gradingResults = answerKeys.map(ak => {
          const sa = studentAnswers.find(a => a.questionNumber === ak.questionNumber);
          const studentAns = sa?.answer?.trim() || '';
          const isCorrect = studentAns.toLowerCase() === ak.answer.toLowerCase().trim();
          return {
            questionNumber: ak.questionNumber,
            studentAnswer: studentAns,
            correctAnswer: ak.answer,
            isCorrect,
            points: ak.points,
            earnedPoints: isCorrect ? ak.points : 0,
            type: ak.type,
          };
        });

        const totalScore = gradingResults.reduce((sum, r) => sum + r.earnedPoints, 0);
        const maxScore = gradingResults.reduce((sum, r) => sum + r.points, 0);
        const correctCount = gradingResults.filter(r => r.isCorrect).length;

        results.push({
          studentName: data?.studentName || file.name.replace('.pdf', ''),
          fileName: file.name,
          answers: studentAnswers,
          results: gradingResults,
          totalScore,
          maxScore,
          correctCount,
          totalQuestions: answerKeys.length,
          pdfFile: file,
        });
      } catch (err) {
        toast({
          title: `오류: ${files[i].name}`,
          description: "시험지 OCR에 실패했습니다.",
          variant: "destructive",
        });
      }

      setProgress(((i + 1) / files.length) * 100);
    }

    setLoading(false);
    if (results.length > 0) {
      onComplete(results);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="p-4 rounded-lg bg-muted/50 border border-border">
        <p className="text-sm text-muted-foreground">
          등록된 답안: <span className="font-semibold text-foreground">{answerKeys.length}문항</span> · 
          총 배점: <span className="font-semibold text-foreground">{answerKeys.reduce((s, a) => s + a.points, 0)}점</span>
        </p>
      </div>

      <PdfDropZone
        onFilesSelected={handleFilesSelected}
        multiple
        label="학생 시험지 PDF 업로드"
        description="한 명 또는 여러 명의 시험지를 드래그하거나 클릭하여 업로드하세요"
        files={files}
        onRemoveFile={removeFile}
      />

      {loading && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>OCR 및 채점 진행 중... ({Math.round(progress)}%)</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      <Button
        onClick={processExams}
        disabled={files.length === 0 || loading}
        className="w-full"
        size="lg"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" /> 처리 중...
          </>
        ) : (
          <>
            OCR 및 채점 시작 <ArrowRight className="w-4 h-4 ml-2" />
          </>
        )}
      </Button>
    </div>
  );
};

export default ExamUploadStep;
