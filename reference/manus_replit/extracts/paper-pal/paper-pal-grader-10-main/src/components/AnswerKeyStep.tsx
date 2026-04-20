import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, ArrowRight, FileUp } from "lucide-react";
import PdfDropZone from "./PdfDropZone";
import type { AnswerKey } from "@/types/exam";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";

interface AnswerKeyStepProps {
  onComplete: (answerKeys: AnswerKey[]) => void;
}

const AnswerKeyStep = ({ onComplete }: AnswerKeyStepProps) => {
  const [mode, setMode] = useState<'manual' | 'pdf'>('manual');
  const [answerKeys, setAnswerKeys] = useState<AnswerKey[]>([
    { questionNumber: 1, answer: '', type: 'objective', points: 1 },
  ]);
  const [pdfFile, setPdfFile] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const addQuestion = () => {
    setAnswerKeys(prev => [
      ...prev,
      { questionNumber: prev.length + 1, answer: '', type: 'objective', points: 1 },
    ]);
  };

  const removeQuestion = (idx: number) => {
    setAnswerKeys(prev => prev.filter((_, i) => i !== idx).map((q, i) => ({ ...q, questionNumber: i + 1 })));
  };

  const updateQuestion = (idx: number, field: keyof AnswerKey, value: string | number) => {
    setAnswerKeys(prev => prev.map((q, i) => (i === idx ? { ...q, [field]: value } : q)));
  };

  const handlePdfUpload = async () => {
    if (pdfFile.length === 0) return;
    setLoading(true);
    try {
      const file = pdfFile[0];
      const reader = new FileReader();
      const base64 = await new Promise<string>((resolve, reject) => {
        reader.onload = () => resolve((reader.result as string).split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const { data, error } = await supabase.functions.invoke('ocr-extract', {
        body: { image: base64, type: 'answer-key' },
      });

      if (error) throw error;

      if (data?.answerKeys) {
        setAnswerKeys(data.answerKeys);
        setMode('manual');
        toast({ title: "답안지 추출 완료", description: `${data.answerKeys.length}개의 문항이 추출되었습니다.` });
      }
    } catch (err) {
      toast({ title: "오류", description: "답안지 OCR에 실패했습니다.", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => {
    const valid = answerKeys.every(q => q.answer.trim() !== '');
    if (!valid) {
      toast({ title: "입력 확인", description: "모든 문항의 답을 입력해주세요.", variant: "destructive" });
      return;
    }
    onComplete(answerKeys);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex gap-2">
        <Button
          variant={mode === 'manual' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setMode('manual')}
        >
          직접 입력
        </Button>
        <Button
          variant={mode === 'pdf' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setMode('pdf')}
        >
          <FileUp className="w-4 h-4 mr-1" />
          PDF로 추출
        </Button>
      </div>

      {mode === 'pdf' ? (
        <div className="space-y-4">
          <PdfDropZone
            onFilesSelected={setPdfFile}
            label="답안지 PDF 업로드"
            description="정답이 표시된 PDF를 업로드하세요"
            files={pdfFile}
            onRemoveFile={() => setPdfFile([])}
          />
          <Button onClick={handlePdfUpload} disabled={pdfFile.length === 0 || loading} className="w-full">
            {loading ? '추출 중...' : 'OCR로 답안 추출'}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-[3rem_1fr_8rem_5rem_2.5rem] gap-2 text-xs font-semibold text-muted-foreground px-1">
            <span>번호</span>
            <span>정답</span>
            <span>유형</span>
            <span>배점</span>
            <span />
          </div>
          {answerKeys.map((q, idx) => (
            <div key={idx} className="grid grid-cols-[3rem_1fr_8rem_5rem_2.5rem] gap-2 items-center">
              <span className="text-sm font-semibold text-center text-foreground">{q.questionNumber}</span>
              <Input
                value={q.answer}
                onChange={e => updateQuestion(idx, 'answer', e.target.value)}
                placeholder="정답 입력"
                className="h-9"
              />
              <Select
                value={q.type}
                onValueChange={v => updateQuestion(idx, 'type', v)}
              >
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="objective">객관식</SelectItem>
                  <SelectItem value="subjective">주관식</SelectItem>
                </SelectContent>
              </Select>
              <Input
                type="number"
                min={1}
                value={q.points}
                onChange={e => updateQuestion(idx, 'points', parseInt(e.target.value) || 1)}
                className="h-9"
              />
              <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => removeQuestion(idx)} disabled={answerKeys.length <= 1}>
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={addQuestion} className="w-full">
            <Plus className="w-4 h-4 mr-1" /> 문항 추가
          </Button>
        </div>
      )}

      <Button onClick={handleSubmit} className="w-full" size="lg" disabled={answerKeys.length === 0}>
        다음 단계 <ArrowRight className="w-4 h-4 ml-2" />
      </Button>
    </div>
  );
};

export default AnswerKeyStep;
