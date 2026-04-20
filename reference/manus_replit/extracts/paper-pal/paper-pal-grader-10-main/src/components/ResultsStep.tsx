import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Download, Check, X, FileText, Upload, ChevronDown, ChevronUp } from "lucide-react";
import type { ExamResult } from "@/types/exam";
import { useToast } from "@/hooks/use-toast";
import { annotatePdf } from "@/lib/pdf-annotator";

interface ResultsStepProps {
  results: ExamResult[];
  onUploadAnalysis: (studentIndex: number, content: string) => void;
}

const ResultsStep = ({ results, onUploadAnalysis }: ResultsStepProps) => {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);
  const [downloading, setDownloading] = useState<number | null>(null);
  const { toast } = useToast();

  const handleDownload = async (result: ExamResult, idx: number) => {
    setDownloading(idx);
    try {
      const annotatedBytes = await annotatePdf(result);
      const blob = new Blob([annotatedBytes as unknown as BlobPart], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `채점_${result.studentName}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: "다운로드 완료", description: `${result.studentName} 채점 결과 PDF가 다운로드되었습니다.` });
    } catch {
      toast({ title: "오류", description: "PDF 생성에 실패했습니다.", variant: "destructive" });
    } finally {
      setDownloading(null);
    }
  };

  const handleAnalysisUpload = (studentIdx: number) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.txt,.md,.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const text = await file.text();
      onUploadAnalysis(studentIdx, text);
      toast({ title: "분석 파일 업로드 완료", description: `${results[studentIdx].studentName}의 분석이 추가되었습니다.` });
    };
    input.click();
  };

  const handleDownloadAll = async () => {
    for (let i = 0; i < results.length; i++) {
      await handleDownload(results[i], i);
    }
  };

  const avgScore = results.length > 0
    ? (results.reduce((s, r) => s + (r.totalScore / r.maxScore) * 100, 0) / results.length).toFixed(1)
    : '0';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="glass-card">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold font-display text-foreground">{results.length}</p>
            <p className="text-xs text-muted-foreground">총 학생 수</p>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold font-display text-foreground">{avgScore}%</p>
            <p className="text-xs text-muted-foreground">평균 점수</p>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold font-display text-success">
              {results.filter(r => (r.totalScore / r.maxScore) >= 0.6).length}
            </p>
            <p className="text-xs text-muted-foreground">합격</p>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold font-display text-destructive">
              {results.filter(r => (r.totalScore / r.maxScore) < 0.6).length}
            </p>
            <p className="text-xs text-muted-foreground">미달</p>
          </CardContent>
        </Card>
      </div>

      <Button onClick={handleDownloadAll} className="w-full" variant="outline">
        <Download className="w-4 h-4 mr-2" /> 전체 채점 PDF 다운로드
      </Button>

      {/* Individual Results */}
      <div className="space-y-3">
        {results.map((result, idx) => {
          const scorePercent = (result.totalScore / result.maxScore) * 100;
          const isExpanded = expandedIdx === idx;
          return (
            <Card key={idx} className="glass-card overflow-hidden">
              <CardHeader
                className="p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-primary" />
                    <div>
                      <CardTitle className="text-sm">{result.studentName}</CardTitle>
                      <p className="text-xs text-muted-foreground">{result.fileName}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={scorePercent >= 60 ? "default" : "destructive"}>
                      {result.totalScore}/{result.maxScore}점 ({scorePercent.toFixed(0)}%)
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {result.correctCount}/{result.totalQuestions} 맞음
                    </span>
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
                </div>
              </CardHeader>
              {isExpanded && (
                <CardContent className="p-4 pt-0 space-y-4">
                  <div className="rounded-lg border border-border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-muted/50">
                          <th className="p-2 text-left font-medium text-muted-foreground">번호</th>
                          <th className="p-2 text-left font-medium text-muted-foreground">유형</th>
                          <th className="p-2 text-left font-medium text-muted-foreground">학생 답</th>
                          <th className="p-2 text-left font-medium text-muted-foreground">정답</th>
                          <th className="p-2 text-center font-medium text-muted-foreground">결과</th>
                          <th className="p-2 text-right font-medium text-muted-foreground">점수</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.results.map((r) => (
                          <tr key={r.questionNumber} className="border-t border-border">
                            <td className="p-2 text-foreground">{r.questionNumber}</td>
                            <td className="p-2 text-muted-foreground">{r.type === 'objective' ? '객관식' : '주관식'}</td>
                            <td className="p-2 text-foreground font-medium">{r.studentAnswer || '-'}</td>
                            <td className="p-2 text-muted-foreground">{r.correctAnswer}</td>
                            <td className="p-2 text-center">
                              {r.isCorrect ? (
                                <Check className="w-5 h-5 text-success mx-auto" />
                              ) : (
                                <X className="w-5 h-5 text-destructive mx-auto" />
                              )}
                            </td>
                            <td className="p-2 text-right font-semibold text-foreground">{r.earnedPoints}/{r.points}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {result.analysisContent && (
                    <div className="p-3 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs font-semibold text-muted-foreground mb-1">LLM 분석</p>
                      <p className="text-sm text-foreground whitespace-pre-wrap">{result.analysisContent}</p>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleDownload(result, idx)}
                      disabled={downloading === idx}
                    >
                      <Download className="w-4 h-4 mr-1" />
                      {downloading === idx ? '생성 중...' : '채점 PDF 다운로드'}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleAnalysisUpload(idx)}>
                      <Upload className="w-4 h-4 mr-1" /> 분석 파일 업로드
                    </Button>
                  </div>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default ResultsStep;
