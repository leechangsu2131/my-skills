import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, UploadCloud, FileText } from "lucide-react";
import { Button } from "./ui/button";
import { useCreateTextbook } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { getGetTextbooksQueryKey } from "@workspace/api-client-react";

interface UploadTextbookDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UploadTextbookDialog({ isOpen, onClose }: UploadTextbookDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("");
  
  const queryClient = useQueryClient();
  const createMutation = useCreateTextbook({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetTextbooksQueryKey() });
        setFile(null);
        setTitle("");
        setSubject("");
        setGrade("");
        onClose();
      }
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title) return;
    
    createMutation.mutate({
      data: {
        file,
        title,
        subject: subject || undefined,
        grade: grade || undefined,
      }
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 sm:px-0">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="bg-card w-full max-w-lg rounded-3xl shadow-2xl border border-border relative z-10 overflow-hidden"
          >
            <div className="p-6 sm:p-8">
              <button
                onClick={onClose}
                className="absolute top-6 right-6 p-2 rounded-full hover:bg-muted text-muted-foreground transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
              
              <h2 className="text-2xl font-bold font-display text-foreground mb-2">새 교과서 등록</h2>
              <p className="text-muted-foreground mb-8">PDF 지도서를 업로드하면 AI가 단원 구조를 분석합니다.</p>

              <form onSubmit={handleSubmit} className="space-y-6">
                {/* File Upload Area */}
                <div className="relative group">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                    required
                  />
                  <div className={`w-full p-8 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center transition-all duration-200 ${file ? 'border-primary bg-primary/5' : 'border-border bg-muted/30 group-hover:bg-muted group-hover:border-primary/40'}`}>
                    {file ? (
                      <>
                        <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center mb-3">
                          <FileText className="w-6 h-6 text-primary" />
                        </div>
                        <p className="font-medium text-foreground text-center">{file.name}</p>
                        <p className="text-xs text-muted-foreground mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                      </>
                    ) : (
                      <>
                        <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center mb-3">
                          <UploadCloud className="w-6 h-6 text-primary" />
                        </div>
                        <p className="font-medium text-foreground">클릭하거나 파일을 드래그하여 업로드</p>
                        <p className="text-xs text-muted-foreground mt-1">PDF 파일만 지원됩니다</p>
                      </>
                    )}
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-foreground mb-1.5">교과서 이름 *</label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="예: 5학년 1학기 수학 지도서"
                      className="w-full px-4 py-3 rounded-xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none transition-all font-medium placeholder:font-normal"
                      required
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold text-foreground mb-1.5">과목</label>
                      <input
                        type="text"
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        placeholder="수학"
                        className="w-full px-4 py-3 rounded-xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-foreground mb-1.5">학년/학기</label>
                      <input
                        type="text"
                        value={grade}
                        onChange={(e) => setGrade(e.target.value)}
                        placeholder="5학년 1학기"
                        className="w-full px-4 py-3 rounded-xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none transition-all"
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-4 flex justify-end gap-3">
                  <Button type="button" variant="ghost" onClick={onClose}>
                    취소
                  </Button>
                  <Button type="submit" isLoading={createMutation.isPending} disabled={!file || !title}>
                    AI 분석 시작하기
                  </Button>
                </div>
              </form>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
