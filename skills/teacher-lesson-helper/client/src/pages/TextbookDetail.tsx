import { useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { ArrowLeft, Download, BookMarked } from "lucide-react";
import { useLocation } from "wouter";
import { Streamdown } from "streamdown";

interface TextbookDetailProps {
  textbookId: number;
}

export default function TextbookDetail({ textbookId }: TextbookDetailProps) {
  const { user } = useAuth();
  const [, setLocation] = useLocation();
  const [selectedLesson, setSelectedLesson] = useState<number | null>(null);
  const [lessonInput, setLessonInput] = useState("");

  const { data: textbook, isLoading: textbookLoading } = trpc.textbook.getById.useQuery(
    { id: textbookId },
    { enabled: !!textbookId }
  );

  const { data: lessons = [], isLoading: lessonsLoading } = trpc.lesson.listByTextbook.useQuery(
    { textbookId },
    { enabled: !!textbookId }
  );

  const { data: currentLesson, isLoading: lessonLoading } = trpc.lesson.getByNumber.useQuery(
    { textbookId, lessonNumber: selectedLesson || 0 },
    { enabled: !!textbookId && selectedLesson !== null }
  );

  const handleSelectLesson = (lessonNumber: number) => {
    setSelectedLesson(lessonNumber);
    setLessonInput("");
  };

  const handleSearchLesson = () => {
    const num = parseInt(lessonInput, 10);
    if (!isNaN(num) && num > 0) {
      setSelectedLesson(num);
    } else {
      toast.error("유효한 차시 번호를 입력하세요.");
    }
  };

  const handleDownloadPDF = () => {
    if (!currentLesson) return;
    
    const content = `${currentLesson.title || `차시 ${currentLesson.lessonNumber}`}\n\n${currentLesson.content}`;
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lesson-${currentLesson.lessonNumber}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("다운로드가 시작되었습니다.");
  };

  if (textbookLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  if (!textbook) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">지도서를 찾을 수 없습니다.</p>
            <Button className="mt-4" onClick={() => setLocation("/")}>
              돌아가기
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <Button
          variant="ghost"
          className="gap-2 mb-6"
          onClick={() => setLocation("/")}
        >
          <ArrowLeft className="w-4 h-4" />
          돌아가기
        </Button>

        <div className="mb-8">
          <h1 className="text-3xl font-bold">{textbook.title}</h1>
          <p className="text-muted-foreground mt-2">
            {textbook.grade}학년 {textbook.semester}학기 · {textbook.subject}
            {textbook.publisher && ` · ${textbook.publisher}`}
          </p>
        </div>

        <Tabs defaultValue="lessons" className="space-y-4">
          <TabsList>
            <TabsTrigger value="lessons">차시 목록</TabsTrigger>
            <TabsTrigger value="search">차시 검색</TabsTrigger>
          </TabsList>

          <TabsContent value="lessons" className="space-y-4">
            {lessonsLoading ? (
              <p className="text-muted-foreground">차시 목록을 로딩 중...</p>
            ) : lessons.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center">
                  <BookMarked className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground">감지된 차시가 없습니다.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {lessons.map((lesson) => (
                  <Card
                    key={lesson.id}
                    className={`cursor-pointer transition-all ${
                      selectedLesson === lesson.lessonNumber
                        ? "ring-2 ring-primary"
                        : "hover:shadow-md"
                    }`}
                    onClick={() => handleSelectLesson(lesson.lessonNumber)}
                  >
                    <CardHeader>
                      <CardTitle className="text-lg">차시 {lesson.lessonNumber}</CardTitle>
                      {lesson.title && (
                        <CardDescription>{lesson.title}</CardDescription>
                      )}
                    </CardHeader>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="search" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>차시 검색</CardTitle>
                <CardDescription>차시 번호를 입력하여 해당 내용을 조회하세요.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Label htmlFor="lesson-input">차시 번호</Label>
                    <Input
                      id="lesson-input"
                      type="number"
                      min="1"
                      placeholder="예: 1, 2, 3..."
                      value={lessonInput}
                      onChange={(e) => setLessonInput(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleSearchLesson()}
                    />
                  </div>
                  <Button onClick={handleSearchLesson} className="mt-6">
                    검색
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {selectedLesson !== null && (
          <div className="mt-8 space-y-4">
            {lessonLoading ? (
              <p className="text-muted-foreground">차시 내용을 로딩 중...</p>
            ) : currentLesson ? (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>차시 {currentLesson.lessonNumber}</CardTitle>
                      {currentLesson.title && (
                        <CardDescription className="mt-2">{currentLesson.title}</CardDescription>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2"
                      onClick={handleDownloadPDF}
                    >
                      <Download className="w-4 h-4" />
                      다운로드
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <Streamdown>{currentLesson.content || "내용이 없습니다."}</Streamdown>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="py-8 text-center">
                  <p className="text-muted-foreground">해당 차시를 찾을 수 없습니다.</p>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
