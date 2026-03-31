import { useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { Plus, Trash2, BookOpen } from "lucide-react";
import { useLocation } from "wouter";

export default function TextbookList() {
  const { user } = useAuth();
  const [, setLocation] = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    subject: "",
    grade: "3",
    semester: "1",
    publisher: "",
    file: null as File | null,
  });

  const { data: textbooks = [], isLoading, refetch } = trpc.textbook.list.useQuery();
  const createMutation = trpc.textbook.create.useMutation({
    onSuccess: () => {
      toast.success("지도서가 업로드되었습니다.");
      setIsOpen(false);
      setFormData({
        title: "",
        subject: "",
        grade: "3",
        semester: "1",
        publisher: "",
        file: null,
      });
      refetch();
    },
    onError: (error) => {
      toast.error(error.message || "업로드에 실패했습니다.");
    },
  });

  const deleteMutation = trpc.textbook.delete.useMutation({
    onSuccess: () => {
      toast.success("지도서가 삭제되었습니다.");
      refetch();
    },
    onError: (error) => {
      toast.error(error.message || "삭제에 실패했습니다.");
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "application/pdf") {
      setFormData({ ...formData, file });
    } else {
      toast.error("PDF 파일만 업로드 가능합니다.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.file) {
      toast.error("파일을 선택해주세요.");
      return;
    }

    const buffer = await formData.file.arrayBuffer();
    createMutation.mutate({
      title: formData.title,
      subject: formData.subject,
      grade: parseInt(formData.grade),
      semester: parseInt(formData.semester),
      publisher: formData.publisher,
      fileBuffer: new Uint8Array(buffer) as any,
      fileName: formData.file.name,
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">지도서 관리</h1>
            <p className="text-muted-foreground mt-2">교과목별 지도서를 관리하고 차시별 내용을 추출하세요.</p>
          </div>
          <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="w-4 h-4" />
                새 지도서 추가
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>지도서 업로드</DialogTitle>
                <DialogDescription>
                  PDF 형식의 지도서를 업로드하세요. 자동으로 차시가 감지됩니다.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="title">지도서 제목</Label>
                  <Input
                    id="title"
                    placeholder="예: 3학년 수학 지도서"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="subject">교과목</Label>
                  <Input
                    id="subject"
                    placeholder="예: 수학, 국어, 영어"
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="grade">학년</Label>
                    <Select value={formData.grade} onValueChange={(value) => setFormData({ ...formData, grade: value })}>
                      <SelectTrigger id="grade">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[1, 2, 3, 4, 5, 6].map((g) => (
                          <SelectItem key={g} value={g.toString()}>{g}학년</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="semester">학기</Label>
                    <Select value={formData.semester} onValueChange={(value) => setFormData({ ...formData, semester: value })}>
                      <SelectTrigger id="semester">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1학기</SelectItem>
                        <SelectItem value="2">2학기</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="publisher">출판사 (선택)</Label>
                  <Input
                    id="publisher"
                    placeholder="출판사명"
                    value={formData.publisher}
                    onChange={(e) => setFormData({ ...formData, publisher: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="file">PDF 파일</Label>
                  <Input
                    id="file"
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    required
                  />
                </div>
                <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "업로드 중..." : "업로드"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">로딩 중...</p>
          </div>
        ) : textbooks.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <BookOpen className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">등록된 지도서가 없습니다.</p>
              <p className="text-sm text-muted-foreground mt-2">위의 "새 지도서 추가" 버튼으로 지도서를 업로드하세요.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {textbooks.map((textbook) => (
              <Card
                key={textbook.id}
                className="cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => setLocation(`/textbook/${textbook.id}`)}
              >
                <CardHeader>
                  <CardTitle className="text-lg">{textbook.title}</CardTitle>
                  <CardDescription>
                    {textbook.grade}학년 {textbook.semester}학기 · {textbook.subject}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    {textbook.publisher && <p>출판사: {textbook.publisher}</p>}
                    <p>페이지: {textbook.totalPages || "정보 없음"}</p>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="w-full mt-4 gap-2"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteMutation.mutate({ id: textbook.id });
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="w-4 h-4" />
                    삭제
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
