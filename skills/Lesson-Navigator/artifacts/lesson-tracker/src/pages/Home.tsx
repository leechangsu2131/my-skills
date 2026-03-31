import { useState } from "react";
import { Link } from "wouter";
import { motion } from "framer-motion";
import { Plus, BookOpen, Trash2, Loader2 } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { UploadTextbookDialog } from "@/components/UploadTextbookDialog";
import { useGetTextbooks, useDeleteTextbook } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { getGetTextbooksQueryKey } from "@workspace/api-client-react";

export default function Home() {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const { data: textbooks, isLoading } = useGetTextbooks();
  const queryClient = useQueryClient();
  
  const deleteMutation = useDeleteTextbook({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getGetTextbooksQueryKey() })
    }
  });

  const handleDelete = (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    if (confirm("정말로 이 교과서를 삭제하시겠습니까? 관련 진도 데이터도 모두 삭제됩니다.")) {
      deleteMutation.mutate({ id });
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'pending': return <Badge variant="secondary">대기 중</Badge>;
      case 'analyzing': return <Badge variant="warning" className="animate-pulse">AI 분석 중...</Badge>;
      case 'ready': return <Badge variant="success">분석 완료</Badge>;
      case 'error': return <Badge variant="destructive">분석 실패</Badge>;
      default: return null;
    }
  };

  return (
    <Shell>
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold font-display text-foreground">내 교과서</h1>
            <p className="text-muted-foreground mt-1">등록된 지도서를 관리하고 진도를 체크하세요.</p>
          </div>
          <Button size="lg" onClick={() => setIsUploadOpen(true)} className="w-full sm:w-auto shadow-xl shadow-primary/20">
            <Plus className="w-5 h-5 mr-2" />
            새 교과서 등록
          </Button>
        </div>

        {isLoading ? (
          <div className="h-64 flex flex-col items-center justify-center">
            <Loader2 className="w-10 h-10 animate-spin text-primary/50 mb-4" />
            <p className="text-muted-foreground font-medium">교과서 목록을 불러오는 중...</p>
          </div>
        ) : textbooks?.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-20 px-4 text-center bg-white rounded-3xl border border-border shadow-sm"
          >
            <img 
              src={`${import.meta.env.BASE_URL}images/empty-books.png`} 
              alt="Empty books illustration" 
              className="w-48 h-48 mb-6 object-contain mix-blend-multiply"
            />
            <h3 className="text-xl font-bold text-foreground mb-2">아직 등록된 교과서가 없습니다</h3>
            <p className="text-muted-foreground max-w-md mb-8">
              상단의 버튼을 눌러 PDF 지도서를 업로드하면,<br/>AI가 자동으로 단원 구조를 분석하여 진도 트래커를 만들어 줍니다.
            </p>
            <Button onClick={() => setIsUploadOpen(true)} variant="outline" size="lg">
              첫 교과서 등록하기
            </Button>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {textbooks?.map((book, i) => (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                key={book.id}
              >
                <Link 
                  href={`/textbooks/${book.id}`}
                  className={`block bg-card rounded-3xl p-6 border transition-all duration-300 ${book.status === 'ready' ? 'hover-card-effect border-border/60 hover:border-primary/30' : 'opacity-80 border-dashed border-border'}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex gap-2">
                      {renderStatusBadge(book.status)}
                      {book.grade && <Badge variant="outline">{book.grade}</Badge>}
                    </div>
                    <button 
                      onClick={(e) => handleDelete(book.id, e)}
                      className="p-2 -mr-2 -mt-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-full transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <h3 className="text-xl font-bold text-foreground mb-1 line-clamp-2">{book.title}</h3>
                  <p className="text-sm text-muted-foreground mb-6 flex items-center gap-1.5">
                    <BookOpen className="w-4 h-4" /> {book.subject || '과목 미지정'}
                  </p>
                  
                  {book.status === 'ready' && book.totalLessons > 0 && (
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="font-semibold text-primary">진도율</span>
                        <span className="text-muted-foreground font-medium">
                          {book.completedLessons} / {book.totalLessons} 차시
                        </span>
                      </div>
                      <div className="w-full bg-secondary/20 rounded-full h-2.5 overflow-hidden">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.round((book.completedLessons / book.totalLessons) * 100)}%` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                          className="bg-primary h-full rounded-full"
                        />
                      </div>
                    </div>
                  )}

                  {book.status === 'analyzing' && (
                    <div className="flex items-center gap-3 text-sm font-medium text-amber-600 bg-amber-50 p-3 rounded-xl">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      AI가 목차를 분석하고 있습니다...
                    </div>
                  )}
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <UploadTextbookDialog 
        isOpen={isUploadOpen} 
        onClose={() => setIsUploadOpen(false)} 
      />
    </Shell>
  );
}
