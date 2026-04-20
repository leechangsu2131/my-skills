import { useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { trpc } from "@/lib/trpc";
import { useLocation } from "wouter";
import { toast } from "sonner";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";

interface GradeStudentPageProps {
  sessionId: number;
  studentAnswerId: number;
  studentName: string;
}

export default function GradeStudentPage({ sessionId, studentAnswerId, studentName }: GradeStudentPageProps) {
  const { user } = useAuth();
  const [, setLocation] = useLocation();
  const [isGrading, setIsGrading] = useState(false);
  const [gradingStatus, setGradingStatus] = useState<"idle" | "grading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");

  const sessionQuery = trpc.grading.getSession.useQuery({ sessionId });
  const studentsQuery = trpc.grading.getSessionStudents.useQuery({ sessionId });
  const answerKeyQuery = trpc.grading.getAnswerKey.useQuery({ sessionId });
  const performGradingMutation = trpc.grading.performGrading.useMutation();

  if (!user) {
    return <div>로그인이 필요합니다.</div>;
  }

  const session = sessionQuery.data;
  const student = studentsQuery.data?.find((s) => s.id === studentAnswerId);
  const displayName = student?.studentName || studentName || "Unknown";

  const handleGrade = async () => {
    if (!student) {
      toast.error("학생 정보를 찾을 수 없습니다.");
      return;
    }

    setIsGrading(true);
    setGradingStatus("grading");
    setErrorMessage("");

    try {
      const answerKey = answerKeyQuery.data;
      if (!answerKey || !answerKey.pdfUrl) {
        throw new Error("정답지가 등록되지 않았습니다.");
      }

      await performGradingMutation.mutateAsync({
        sessionId,
        studentAnswerId,
        studentPdfUrl: student.pdfUrl,
        answerKeyPdfUrl: answerKey.pdfUrl,
      });

      setGradingStatus("success");
      toast.success("채점이 완료되었습니다.");

      // 2초 후 대시보드로 이동
      setTimeout(() => {
        setLocation(`/dashboard/${sessionId}`);
      }, 2000);
    } catch (error: any) {
      setGradingStatus("error");
      const message = error?.message || "채점 중 오류가 발생했습니다.";
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsGrading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* 헤더 */}
        <div>
          <Button variant="outline" onClick={() => setLocation(`/session/${sessionId}`)} className="mb-4">
            뒤로 가기
          </Button>
          <h1 className="text-3xl font-bold">{displayName} - 채점 진행</h1>
          <p className="text-gray-600 mt-2">{session?.sessionName}</p>
        </div>

        {/* 상태 표시 */}
        {gradingStatus === "idle" && (
          <Card>
            <CardHeader>
              <CardTitle>채점 준비</CardTitle>
              <CardDescription>학생의 답안을 채점할 준비가 되었습니다.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600">학생명</p>
                  <p className="text-lg font-semibold">{displayName}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">시험명</p>
                  <p className="text-lg font-semibold">{session?.sessionName}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">총 문항</p>
                  <p className="text-lg font-semibold">{session?.totalQuestions}</p>
                </div>
              </div>

              <Button onClick={handleGrade} disabled={isGrading} size="lg" className="w-full">
                {isGrading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isGrading ? "채점 중..." : "채점 시작"}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* 진행 중 */}
        {gradingStatus === "grading" && (
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto" />
                <p className="text-lg font-semibold">채점 중입니다...</p>
                <p className="text-sm text-gray-600">PDF 처리 및 OCR 분석이 진행 중입니다.</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 성공 */}
        {gradingStatus === "success" && (
          <Card className="bg-green-50 border-green-200">
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <CheckCircle className="w-12 h-12 text-green-600 mx-auto" />
                <p className="text-lg font-semibold">채점이 완료되었습니다!</p>
                <p className="text-sm text-gray-600">대시보드로 이동 중입니다...</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 오류 */}
        {gradingStatus === "error" && (
          <Card className="bg-red-50 border-red-200">
            <CardContent className="py-12">
              <div className="text-center space-y-4">
                <AlertCircle className="w-12 h-12 text-red-600 mx-auto" />
                <p className="text-lg font-semibold">채점 중 오류가 발생했습니다.</p>
                <p className="text-sm text-gray-600">{errorMessage}</p>
                <Button onClick={handleGrade} disabled={isGrading} className="mt-4">
                  다시 시도
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
