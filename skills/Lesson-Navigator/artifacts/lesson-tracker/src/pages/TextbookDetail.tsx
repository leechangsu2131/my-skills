import { useState } from "react";
import { useParams, Link } from "wouter";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, Circle, Clock, LayoutList, Share, ChevronRight, Play } from "lucide-react";
import { format } from "date-fns";
import { ko } from "date-fns/locale";

import { Shell } from "@/components/layout/Shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { NotionSyncDialog } from "@/components/NotionSyncDialog";

import { 
  useGetTextbook, 
  useGetCurrentLesson, 
  useCompleteLesson, 
  useUncompleteLesson,
  getGetTextbookQueryKey,
  getGetCurrentLessonQueryKey
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

export default function TextbookDetail() {
  const { id } = useParams<{ id: string }>();
  const textbookId = parseInt(id, 10);
  const [isNotionSyncOpen, setIsNotionSyncOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: textbook, isLoading: isLoadingBook } = useGetTextbook(textbookId);
  const { data: currentLessonData, isLoading: isLoadingCurrent } = useGetCurrentLesson(textbookId);

  const invalidateData = () => {
    queryClient.invalidateQueries({ queryKey: getGetTextbookQueryKey(textbookId) });
    queryClient.invalidateQueries({ queryKey: getGetCurrentLessonQueryKey(textbookId) });
  };

  const completeMutation = useCompleteLesson({ mutation: { onSuccess: invalidateData } });
  const uncompleteMutation = useUncompleteLesson({ mutation: { onSuccess: invalidateData } });

  const toggleLesson = (lessonId: number, isCompleted: boolean) => {
    if (isCompleted) {
      uncompleteMutation.mutate({ id: lessonId });
    } else {
      completeMutation.mutate({ id: lessonId, data: { taughtAt: new Date().toISOString() } });
    }
  };

  if (isLoadingBook) {
    return (
      <Shell>
        <div className="flex h-[60vh] items-center justify-center">
          <div className="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
        </div>
      </Shell>
    );
  }

  if (!textbook) {
    return (
      <Shell>
        <div className="text-center py-20">교과서를 찾을 수 없습니다.</div>
      </Shell>
    );
  }

  const progress = currentLessonData?.progress || { completed: 0, total: 0, percentage: 0 };
  const currentLesson = currentLessonData?.currentLesson;

  return (
    <Shell>
      <div className="max-w-5xl mx-auto pb-20">
        <Link href="/" className="inline-flex items-center text-sm font-semibold text-muted-foreground hover:text-primary mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" /> 목록으로 돌아가기
        </Link>

        {/* Header Section */}
        <div className="bg-white rounded-3xl p-8 border border-border shadow-sm mb-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[60px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />
          
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 relative z-10">
            <div>
              <div className="flex gap-2 mb-3">
                <Badge variant="secondary">{textbook.grade || '학년 미정'}</Badge>
                <Badge variant="outline" className="bg-white">{textbook.subject || '과목 미정'}</Badge>
              </div>
              <h1 className="text-3xl md:text-4xl font-bold font-display text-foreground tracking-tight">{textbook.title}</h1>
            </div>
            
            <div className="flex items-center gap-3">
              <Button onClick={() => setIsNotionSyncOpen(true)} variant="outline" className="bg-white">
                <Share className="w-4 h-4 mr-2" /> 노션 연동
              </Button>
            </div>
          </div>

          {/* Progress Bar inside Header */}
          <div className="mt-8 bg-muted/30 p-5 rounded-2xl border border-border/50">
            <div className="flex justify-between items-end mb-3">
              <div>
                <p className="text-sm font-semibold text-muted-foreground mb-1">전체 진도율</p>
                <p className="text-2xl font-bold text-primary font-display">{Math.round(progress.percentage)}<span className="text-lg text-muted-foreground">%</span></p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-muted-foreground mb-1">완료된 차시</p>
                <p className="text-lg font-bold text-foreground">{progress.completed} <span className="text-muted-foreground font-normal">/ {progress.total}</span></p>
              </div>
            </div>
            <div className="w-full bg-border rounded-full h-3 overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${progress.percentage}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className="bg-gradient-to-r from-primary to-teal-400 h-full rounded-full"
              />
            </div>
          </div>
        </div>

        {/* Current Lesson Highlight */}
        {currentLesson && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-10"
          >
            <div className="flex items-center gap-2 mb-4">
              <Play className="w-5 h-5 text-secondary fill-secondary" />
              <h2 className="text-xl font-bold font-display text-foreground">오늘 수업할 차례</h2>
            </div>
            
            <div className="bg-gradient-to-br from-primary to-teal-700 rounded-3xl p-1 shadow-xl shadow-primary/20">
              <div className="bg-card rounded-[22px] p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6">
                <div>
                  <Badge variant="outline" className="mb-3 border-primary/20 text-primary bg-primary/5">
                    {currentLesson.chapterNumber ? `${currentLesson.chapterNumber}단원` : '차시'}
                  </Badge>
                  <h3 className="text-2xl font-bold text-foreground mb-2">{currentLesson.title}</h3>
                  {currentLesson.pageStart && currentLesson.pageEnd && (
                    <p className="text-muted-foreground font-medium flex items-center gap-1.5">
                      <BookOpen className="w-4 h-4" /> 교과서 {currentLesson.pageStart} ~ {currentLesson.pageEnd}쪽
                    </p>
                  )}
                </div>
                
                <Button 
                  size="lg" 
                  onClick={() => toggleLesson(currentLesson.id, false)}
                  isLoading={completeMutation.isPending && completeMutation.variables?.id === currentLesson.id}
                  className="w-full md:w-auto shrink-0 px-8 rounded-2xl shadow-lg shadow-primary/25"
                >
                  <CheckCircle2 className="w-5 h-5 mr-2" />
                  수업 완료하기
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Full Lesson Tree */}
        <div>
          <div className="flex items-center gap-2 mb-6">
            <LayoutList className="w-5 h-5 text-muted-foreground" />
            <h2 className="text-xl font-bold font-display text-foreground">전체 목차 및 진도</h2>
          </div>

          <div className="bg-white rounded-3xl border border-border shadow-sm p-4 md:p-6">
            {textbook.status === 'analyzing' ? (
              <div className="py-20 text-center">
                <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-4"></div>
                <h3 className="text-lg font-bold mb-2">AI가 목차를 분석하고 있습니다</h3>
                <p className="text-muted-foreground">PDF의 분량에 따라 1~2분 정도 소요될 수 있습니다.</p>
              </div>
            ) : textbook.lessons.length === 0 ? (
              <div className="py-10 text-center text-muted-foreground">등록된 단원 정보가 없습니다.</div>
            ) : (
              <div className="space-y-1 relative">
                {/* Vertical line connecting items */}
                <div className="absolute left-[22px] top-6 bottom-6 w-px bg-border -z-10 hidden sm:block" />

                {textbook.lessons.map((lesson) => {
                  const isPending = (completeMutation.isPending || uncompleteMutation.isPending) && 
                                    (completeMutation.variables?.id === lesson.id || uncompleteMutation.variables?.id === lesson.id);
                  
                  // Visual hierarchy based on level (1 = Chapter, 2 = Unit, 3 = Lesson)
                  const indentClass = 
                    lesson.level === 1 ? "" : 
                    lesson.level === 2 ? "ml-4 sm:ml-12" : 
                    "ml-8 sm:ml-20";
                    
                  const isTopLevel = lesson.level === 1;

                  return (
                    <motion.div 
                      key={lesson.id}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className={`group flex items-start sm:items-center gap-3 sm:gap-4 p-3 rounded-2xl transition-colors hover:bg-muted/50 ${indentClass} ${isTopLevel ? 'mt-4 first:mt-0' : ''}`}
                    >
                      <button 
                        onClick={() => toggleLesson(lesson.id, lesson.isCompleted)}
                        disabled={isPending}
                        className={`shrink-0 mt-1 sm:mt-0 z-10 transition-transform active:scale-90 ${isTopLevel ? 'scale-125' : ''}`}
                      >
                        {isPending ? (
                          <Loader2 className="w-6 h-6 animate-spin text-primary" />
                        ) : lesson.isCompleted ? (
                          <CheckCircle2 className="w-6 h-6 text-primary fill-primary/10" />
                        ) : (
                          <Circle className="w-6 h-6 text-muted-foreground hover:text-primary transition-colors" />
                        )}
                      </button>

                      <div className={`flex-1 min-w-0 ${lesson.isCompleted ? 'opacity-60' : ''}`}>
                        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                          {lesson.chapterNumber && (
                            <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-md shrink-0 w-fit">
                              {lesson.chapterNumber}
                            </span>
                          )}
                          <h4 className={`font-semibold text-foreground truncate ${isTopLevel ? 'text-lg font-display' : 'text-base'} ${lesson.isCompleted ? 'line-through decoration-muted-foreground/50' : ''}`}>
                            {lesson.title}
                          </h4>
                        </div>
                        
                        {(lesson.pageStart || lesson.completedAt) && (
                          <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-muted-foreground">
                            {lesson.pageStart && (
                              <span className="flex items-center gap-1">
                                <BookOpen className="w-3.5 h-3.5" /> p.{lesson.pageStart}{lesson.pageEnd ? `-${lesson.pageEnd}` : ''}
                              </span>
                            )}
                            {lesson.completedAt && (
                              <span className="flex items-center gap-1 text-primary/80 font-medium">
                                <Clock className="w-3.5 h-3.5" /> 
                                {format(new Date(lesson.completedAt), "M월 d일 (E)", { locale: ko })} 완료
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <NotionSyncDialog 
        textbookId={textbookId}
        isOpen={isNotionSyncOpen} 
        onClose={() => setIsNotionSyncOpen(false)} 
      />
    </Shell>
  );
}
