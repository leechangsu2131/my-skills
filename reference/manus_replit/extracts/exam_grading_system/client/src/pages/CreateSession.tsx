import { useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { trpc } from "@/lib/trpc";
import { useLocation } from "wouter";
import { toast } from "sonner";

export default function CreateSession() {
  const { user } = useAuth();
  const [, setLocation] = useLocation();
  const [sessionName, setSessionName] = useState("");
  const [description, setDescription] = useState("");
  const [totalQuestions, setTotalQuestions] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const createSessionMutation = trpc.grading.createSession.useMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!sessionName.trim()) {
      toast.error("시험명을 입력해주세요.");
      return;
    }

    setIsLoading(true);
    try {
      const result = await createSessionMutation.mutateAsync({
        sessionName,
        description: description || undefined,
        totalQuestions: totalQuestions ? parseInt(totalQuestions) : undefined,
      });

      toast.success("채점 세션이 생성되었습니다.");
      if (result && 'id' in result) {
        setLocation(`/session/${result.id}`);
      } else {
        setLocation("/");
      }
    } catch (error) {
      toast.error("세션 생성에 실패했습니다.");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!user) {
    return <div>로그인이 필요합니다.</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="text-3xl">새 채점 세션 생성</CardTitle>
            <CardDescription>시험 정보를 입력하여 새로운 채점 세션을 생성합니다.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">시험명 *</label>
                <Input
                  placeholder="예: 2024년 1학기 중간고사"
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">설명</label>
                <Textarea
                  placeholder="시험에 대한 설명을 입력하세요."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isLoading}
                  rows={4}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">총 문항 수</label>
                <Input
                  type="number"
                  placeholder="예: 50"
                  value={totalQuestions}
                  onChange={(e) => setTotalQuestions(e.target.value)}
                  disabled={isLoading}
                  min="1"
                />
              </div>

              <div className="flex gap-4">
                <Button type="submit" disabled={isLoading} className="flex-1">
                  {isLoading ? "생성 중..." : "세션 생성"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setLocation("/")}
                  disabled={isLoading}
                  className="flex-1"
                >
                  취소
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
