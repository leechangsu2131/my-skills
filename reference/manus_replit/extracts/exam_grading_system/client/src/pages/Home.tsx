import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getLoginUrl } from "@/const";
import { useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { Plus, BookOpen, BarChart3 } from "lucide-react";

export default function Home() {
  const { user, isAuthenticated } = useAuth();
  const [, setLocation] = useLocation();
  const sessionsQuery = trpc.grading.listSessions.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-3xl">학생 시험지 자동 채점 시스템</CardTitle>
            <CardDescription>PDF 기반 자동 채점 및 분석 플랫폼</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" size="lg" onClick={() => (window.location.href = getLoginUrl())}>
              로그인
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const sessions = sessionsQuery.data || [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-8 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold">채점 시스템</h1>
              <p className="text-gray-600 mt-1">안녕하세요, {user?.name}님</p>
            </div>
            <Button onClick={() => setLocation("/create-session")} size="lg">
              <Plus className="w-5 h-5 mr-2" />
              새 세션 생성
            </Button>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="max-w-6xl mx-auto px-8 py-12">
        {/* 통계 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                총 세션
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold">{sessions.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                진행 중
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold">0</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                완료됨
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold">0</p>
            </CardContent>
          </Card>
        </div>

        {/* 세션 목록 */}
        <Card>
          <CardHeader>
            <CardTitle>최근 세션</CardTitle>
            <CardDescription>생성된 채점 세션 목록</CardDescription>
          </CardHeader>
          <CardContent>
            {sessions.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500 mb-4">생성된 세션이 없습니다.</p>
                <Button onClick={() => setLocation("/create-session")}>첫 세션 생성하기</Button>
              </div>
            ) : (
              <div className="space-y-4">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition"
                    onClick={() => setLocation(`/session/${session.id}`)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-lg">{session.sessionName}</h3>
                        <p className="text-gray-600 text-sm mt-1">{session.description}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">문항: {session.totalQuestions}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(session.createdAt).toLocaleDateString("ko-KR")}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
