import { useAuth } from "@/_core/hooks/useAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { trpc } from "@/lib/trpc";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { useLocation } from "wouter";

interface GradingDashboardProps {
  sessionId: number;
}

export default function GradingDashboard({ sessionId }: GradingDashboardProps) {
  const { user } = useAuth();
  const sessionQuery = trpc.grading.getSession.useQuery({ sessionId });
  const resultsQuery = trpc.grading.getGradingResults.useQuery({ sessionId });
  const studentsQuery = trpc.grading.getSessionStudents.useQuery({ sessionId });
  const [, setLocation] = useLocation();

  if (!user) {
    return <div>로그인이 필요합니다.</div>;
  }

  const session = sessionQuery.data;
  const results = resultsQuery.data || [];
  const students = studentsQuery.data || [];

  // 통계 계산
  const totalStudents = students.length;
  const gradedStudents = results.length;
  const averageScore = results.length > 0
    ? (results.reduce((sum, r) => {
        const [correct, total] = r.score.split("/").map(Number);
        return sum + (correct / total);
      }, 0) / results.length * 100).toFixed(1)
    : 0;

  // 점수 분포 데이터
  const scoreDistribution = results.map((r) => {
    const [correct, total] = r.score.split("/").map(Number);
    const percentage = Math.round((correct / total) * 100);
    const student = students.find((s) => s.id === r.studentAnswerId);
    return {
      name: student?.studentName || "Unknown",
      score: percentage,
      correct,
      total,
    };
  });

  // 점수 등급 분포
  const gradeDistribution = [
    { name: "A (90~100)", value: scoreDistribution.filter((s) => s.score >= 90).length, color: "#10b981" },
    { name: "B (80~89)", value: scoreDistribution.filter((s) => s.score >= 80 && s.score < 90).length, color: "#3b82f6" },
    { name: "C (70~79)", value: scoreDistribution.filter((s) => s.score >= 70 && s.score < 80).length, color: "#f59e0b" },
    { name: "D (60~69)", value: scoreDistribution.filter((s) => s.score >= 60 && s.score < 70).length, color: "#ef4444" },
    { name: "F (0~59)", value: scoreDistribution.filter((s) => s.score < 60).length, color: "#6b7280" },
  ].filter((g) => g.value > 0);

  const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#6b7280"];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* 헤더 */}
        <div>
          <h1 className="text-3xl font-bold">{session?.sessionName} - 채점 결과 대시보드</h1>
          <p className="text-gray-600 mt-2">{session?.description}</p>
        </div>

        {/* 통계 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">총 학생 수</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{totalStudents}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">채점 완료</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{gradedStudents}</p>
              <p className="text-xs text-gray-500 mt-1">
                {totalStudents > 0 ? ((gradedStudents / totalStudents) * 100).toFixed(0) : 0}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">평균 점수</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{averageScore}%</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">총 문항</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{session?.totalQuestions}</p>
            </CardContent>
          </Card>
        </div>

        {/* 차트 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* 학생별 점수 분포 */}
          <Card>
            <CardHeader>
              <CardTitle>학생별 점수</CardTitle>
              <CardDescription>각 학생의 채점 결과</CardDescription>
            </CardHeader>
            <CardContent>
              {scoreDistribution.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={scoreDistribution}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                    <YAxis />
                    <Tooltip formatter={(value) => `${value}%`} />
                    <Bar dataKey="score" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-500 text-center py-8">채점 결과가 없습니다.</p>
              )}
            </CardContent>
          </Card>

          {/* 점수 등급 분포 */}
          <Card>
            <CardHeader>
              <CardTitle>점수 등급 분포</CardTitle>
              <CardDescription>학생들의 등급 분포</CardDescription>
            </CardHeader>
            <CardContent>
              {gradeDistribution.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={gradeDistribution}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}명`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {gradeDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-500 text-center py-8">채점 결과가 없습니다.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 상세 결과 테이블 */}
        <Card>
          <CardHeader>
            <CardTitle>상세 채점 결과</CardTitle>
            <CardDescription>모든 학생의 채점 결과 목록</CardDescription>
          </CardHeader>
          <CardContent>
            {scoreDistribution.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4">학생명</th>
                      <th className="text-left py-3 px-4">점수</th>
                      <th className="text-left py-3 px-4">정답률</th>
                      <th className="text-left py-3 px-4">등급</th>
                      <th className="text-left py-3 px-4">작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scoreDistribution.map((item, index) => {
                      const percentage = item.score;
                      let grade = "F";
                      let gradeColor = "text-gray-600";

                      if (percentage >= 90) {
                        grade = "A";
                        gradeColor = "text-green-600";
                      } else if (percentage >= 80) {
                        grade = "B";
                        gradeColor = "text-blue-600";
                      } else if (percentage >= 70) {
                        grade = "C";
                        gradeColor = "text-yellow-600";
                      } else if (percentage >= 60) {
                        grade = "D";
                        gradeColor = "text-orange-600";
                      }

                      return (
                        <tr key={index} className="border-b hover:bg-gray-50">
                          <td className="py-3 px-4">{item.name}</td>
                          <td className="py-3 px-4 font-semibold">{item.correct}/{item.total}</td>
                          <td className="py-3 px-4">{percentage}%</td>
                          <td className={`py-3 px-4 font-bold ${gradeColor}`}>{grade}</td>
                          <td className="py-3 px-4">
                            <button
                              className="text-blue-600 hover:underline text-sm"
                              onClick={() => {
                                const student = students.find((s) => s.id === results[index]?.studentAnswerId);
                                if (student) {
                                  setLocation(`/result/${sessionId}/${student.id}`);
                                }
                              }}
                            >
                              상세보기
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">채점 결과가 없습니다.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
