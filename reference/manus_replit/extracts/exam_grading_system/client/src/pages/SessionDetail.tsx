import { useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { trpc } from "@/lib/trpc";
import { useLocation } from "wouter";
import { toast } from "sonner";
import { Upload, Download, Loader2, ChevronLeft } from "lucide-react";
import { fileToArrayBuffer, validateFile, formatFileSize } from "@/lib/fileUpload";

interface SessionDetailProps {
  sessionId: number;
}

export default function SessionDetail({ sessionId }: SessionDetailProps) {
  const { user } = useAuth();
  const [, setLocation] = useLocation();
  const [studentName, setStudentName] = useState("");
  const [studentFile, setStudentFile] = useState<File | null>(null);
  const [answerKeyFile, setAnswerKeyFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const sessionQuery = trpc.grading.getSession.useQuery({ sessionId });
  const studentsQuery = trpc.grading.getSessionStudents.useQuery({ sessionId });
  const resultsQuery = trpc.grading.getGradingResults.useQuery({ sessionId });
  const uploadStudentMutation = trpc.grading.uploadStudentAnswer.useMutation();
  const uploadAnswerKeyMutation = trpc.grading.uploadAnswerKey.useMutation();

  const handleUploadStudent = async () => {
    if (!studentFile || !studentName.trim()) {
      toast.error("학생명과 파일을 선택해주세요.");
      return;
    }

    const validation = validateFile(studentFile);
    if (!validation.valid) {
      toast.error(validation.error);
      return;
    }

    setIsUploading(true);
    try {
      // TODO: 실제 S3 업로드 구현
      // const buffer = await fileToArrayBuffer(studentFile);
      // const pdfUrl = await uploadToS3(buffer, studentFile.name);
      
      const pdfUrl = `https://example.com/student-${Date.now()}.pdf`;

      await uploadStudentMutation.mutateAsync({
        sessionId,
        studentName,
        pdfUrl,
      });

      toast.success("학생 답안이 업로드되었습니다.");
      setStudentName("");
      setStudentFile(null);
      studentsQuery.refetch();
    } catch (error) {
      toast.error("업로드에 실패했습니다.");
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleUploadAnswerKey = async () => {
    if (!answerKeyFile) {
      toast.error("정답지 파일을 선택해주세요.");
      return;
    }

    const validation = validateFile(answerKeyFile);
    if (!validation.valid) {
      toast.error(validation.error);
      return;
    }

    setIsUploading(true);
    try {
      // TODO: 실제 S3 업로드 구현
      // const buffer = await fileToArrayBuffer(answerKeyFile);
      // const pdfUrl = await uploadToS3(buffer, answerKeyFile.name);
      
      const pdfUrl = `https://example.com/answerkey-${Date.now()}.pdf`;

      await uploadAnswerKeyMutation.mutateAsync({
        sessionId,
        pdfUrl,
      });

      toast.success("정답지가 업로드되었습니다.");
      setAnswerKeyFile(null);
    } catch (error) {
      toast.error("업로드에 실패했습니다.");
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  };

  if (!user) {
    return <div>로그인이 필요합니다.</div>;
  }

  if (sessionQuery.isLoading) {
    return <div className="p-8">로딩 중...</div>;
  }

  const session = sessionQuery.data;
  const students = studentsQuery.data || [];
  const results = resultsQuery.data || [];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* 네비게이션 */}
        <div className="flex justify-between items-center">
          <Button variant="outline" onClick={() => setLocation("/")}>
            뒤로 가기
          </Button>
          <Button onClick={() => setLocation(`/dashboard/${sessionId}`)}>
            대시보드 보기
          </Button>
        </div>

        {/* 세션 정보 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-3xl">{session?.sessionName}</CardTitle>
            <CardDescription>{session?.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">총 문항 수</p>
                <p className="text-2xl font-bold">{session?.totalQuestions}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">생성일</p>
                <p className="text-lg">{session?.createdAt ? new Date(session.createdAt).toLocaleDateString("ko-KR") : "-"}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 파일 업로드 섹션 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* 학생 답안 업로드 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                학생 답안 업로드
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">학생명</label>
                <Input
                  placeholder="학생 이름"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  disabled={isUploading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">PDF 파일</label>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setStudentFile(e.target.files?.[0] || null)}
                  disabled={isUploading}
                  className="block w-full text-sm text-gray-500"
                />
                {studentFile && (
                  <p className="text-xs text-gray-500 mt-2">{studentFile.name} ({formatFileSize(studentFile.size)})</p>
                )}
              </div>
              <Button onClick={handleUploadStudent} disabled={isUploading} className="w-full">
                {isUploading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isUploading ? "업로드 중..." : "업로드"}
              </Button>
            </CardContent>
          </Card>

          {/* 정답지 업로드 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                정답지 업로드
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">정답지 PDF</label>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setAnswerKeyFile(e.target.files?.[0] || null)}
                  disabled={isUploading}
                  className="block w-full text-sm text-gray-500"
                />
                {answerKeyFile && (
                  <p className="text-xs text-gray-500 mt-2">{answerKeyFile.name} ({formatFileSize(answerKeyFile.size)})</p>
                )}
              </div>
              <Button onClick={handleUploadAnswerKey} disabled={isUploading} className="w-full">
                {isUploading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {isUploading ? "업로드 중..." : "정답지 업로드"}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* 학생 목록 */}
        <Card>
          <CardHeader>
            <CardTitle>학생 목록</CardTitle>
          </CardHeader>
          <CardContent>
            {students.length === 0 ? (
              <p className="text-gray-500">업로드된 학생이 없습니다.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-4">학생명</th>
                      <th className="text-left py-2 px-4">업로드 일시</th>
                      <th className="text-left py-2 px-4">채점 상태</th>
                      <th className="text-left py-2 px-4">점수</th>
                      <th className="text-left py-2 px-4">작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((student) => {
                      const result = results.find((r) => r.studentAnswerId === student.id);
                      return (
                        <tr key={student.id} className="border-b hover:bg-gray-50">
                          <td className="py-2 px-4">{student.studentName}</td>
                          <td className="py-2 px-4">{student.uploadedAt ? new Date(student.uploadedAt).toLocaleDateString("ko-KR") : "-"}</td>
                          <td className="py-2 px-4">
                            {result ? (
                              <span className="text-green-600 font-medium">완료</span>
                            ) : (
                              <button
                                className="text-blue-600 hover:underline text-sm"
                                onClick={() => setLocation(`/grade/${sessionId}/${student.id}`)}
                              >
                                채점 실신
                              </button>
                            )}
                          </td>
                          <td className="py-2 px-4">{result?.score || "-"}</td>
                          <td className="py-2 px-4">
                            {result && (
                              <Button size="sm" variant="outline">
                                <Download className="w-4 h-4" />
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
