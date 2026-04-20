import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { trpc } from "@/lib/trpc";
import { useLocation } from "wouter";
import { Download, ArrowLeft, CheckCircle, XCircle } from "lucide-react";

interface ResultDetailProps {
  sessionId: number;
  studentAnswerId: number;
}

export default function ResultDetail({ sessionId, studentAnswerId }: ResultDetailProps) {
  const { user } = useAuth();
  const [, setLocation] = useLocation();
  const resultsQuery = trpc.grading.getGradingResults.useQuery({ sessionId });
  const studentsQuery = trpc.grading.getSessionStudents.useQuery({ sessionId });

  if (!user) {
    return <div>로그인이 필요합니다.</div>;
  }

  const results = resultsQuery.data || [];
  const students = studentsQuery.data || [];
  const result = results.find((r) => r.studentAnswerId === studentAnswerId);
  const student = students.find((s) => s.id === studentAnswerId);

  if (!result || !student) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <Button variant="outline" onClick={() => setLocation(`/dashboard/${sessionId}`)} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            돌아가기
          </Button>
          <Card>
            <CardContent className="py-12">
              <p className="text-center text-gray-500">결과를 찾을 수 없습니다.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const questionResults = result.questionResults ? JSON.parse(result.questionResults) : [];
  const analysisData = result.analysisData ? JSON.parse(result.analysisData) : null;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* 헤더 */}
        <div>
          <Button variant="outline" onClick={() => setLocation(`/dashboard/${sessionId}`)} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            돌아가기
          </Button>
          <h1 className="text-3xl font-bold">{student.studentName} - 채점 결과</h1>
        </div>

        {/* 점수 카드 */}
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50">
          <CardContent className="py-8">
            <div className="grid grid-cols-3 gap-8">
              <div className="text-center">
                <p className="text-gray-600 mb-2">점수</p>
                <p className="text-4xl font-bold text-blue-600">{result.score}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-600 mb-2">정답률</p>
                <p className="text-4xl font-bold text-green-600">
                  {((result.correctCount / result.totalQuestions) * 100).toFixed(1)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-gray-600 mb-2">채점 일시</p>
                <p className="text-lg">{new Date(result.gradedAt).toLocaleDateString("ko-KR")}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 문항별 결과 */}
        <Card>
          <CardHeader>
            <CardTitle>문항별 채점 결과</CardTitle>
            <CardDescription>각 문항의 정오 여부</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {questionResults.length > 0 ? (
                questionResults.map((q: any, index: number) => (
                  <div
                    key={index}
                    className={`p-4 border rounded-lg ${
                      q.correct ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 mt-1">
                        {q.correct ? (
                          <CheckCircle className="w-6 h-6 text-green-600" />
                        ) : (
                          <XCircle className="w-6 h-6 text-red-600" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start mb-2">
                          <h3 className="font-semibold">문항 {q.questionNum}</h3>
                          <span className={`text-sm font-medium ${q.correct ? "text-green-600" : "text-red-600"}`}>
                            {q.correct ? "정답" : "오답"}
                          </span>
                        </div>
                        <div className="space-y-1 text-sm">
                          <p>
                            <span className="text-gray-600">정답:</span>
                            <span className="ml-2 font-semibold text-green-600">{q.correctAnswer}</span>
                          </p>
                          <p>
                            <span className="text-gray-600">답안:</span>
                            <span className={`ml-2 font-semibold ${q.correct ? "text-green-600" : "text-red-600"}`}>
                              {q.studentAnswer || "(답변 없음)"}
                            </span>
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-center py-8">문항 정보가 없습니다.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 분석 데이터 */}
        {analysisData && (
          <Card>
            <CardHeader>
              <CardTitle>LLM 분석 결과</CardTitle>
              <CardDescription>AI가 분석한 오답 원인 및 개선 방안</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-50 p-4 rounded-lg">
                <pre className="whitespace-pre-wrap text-sm">{JSON.stringify(analysisData, null, 2)}</pre>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 액션 버튼 */}
        <div className="flex gap-4">
          {result.resultPdfUrl && (
            <Button className="flex-1" onClick={() => result.resultPdfUrl && window.open(result.resultPdfUrl, "_blank")}>
              <Download className="w-4 h-4 mr-2" />
              결과 PDF 다운로드
            </Button>
          )}
          <Button variant="outline" className="flex-1" onClick={() => setLocation(`/dashboard/${sessionId}`)}>
            대시보드로 돌아가기
          </Button>
        </div>
      </div>
    </div>
  );
}
