import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, RefreshCw } from "lucide-react";
import { Button } from "./ui/button";
import { useGetNotionPages, useSyncToNotion } from "@workspace/api-client-react";

interface NotionSyncDialogProps {
  textbookId: number;
  isOpen: boolean;
  onClose: () => void;
}

export function NotionSyncDialog({ textbookId, isOpen, onClose }: NotionSyncDialogProps) {
  const [selectedPageId, setSelectedPageId] = useState<string>("");
  
  const { data: pages, isLoading: isLoadingPages } = useGetNotionPages({
    query: { enabled: isOpen }
  });
  
  const syncMutation = useSyncToNotion({
    mutation: {
      onSuccess: () => {
        alert("노션 동기화가 완료되었습니다.");
        onClose();
      },
      onError: () => {
        alert("동기화에 실패했습니다. 노션 연결을 확인해주세요.");
      }
    }
  });

  const handleSync = () => {
    if (!selectedPageId) return;
    syncMutation.mutate({
      id: textbookId,
      data: { notionPageId: selectedPageId }
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
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
            className="bg-card w-full max-w-md rounded-3xl shadow-2xl border border-border relative z-10 overflow-hidden"
          >
            <div className="p-6 sm:p-8">
              <button onClick={onClose} className="absolute top-6 right-6 p-2 rounded-full hover:bg-muted text-muted-foreground transition-colors">
                <X className="w-5 h-5" />
              </button>
              
              <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center mb-6 border border-slate-200 shadow-sm">
                <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
                  <path d="M4.459 4.208c.746-.306 1.488-.501 3.013-.807l8.283-1.63c.806-.153 1.25-.095 1.58.125.263.176.438.455.452.883v16.126c0 .54-.251.986-.788 1.155-.38.12-1.01.206-2.073.411l-8.627 1.636c-.732.146-1.189.06-1.493-.162-.266-.192-.442-.49-.452-.924V4.896c0-.285.029-.537.105-.688zm1.968 15.111l7.355-1.393V3.626L6.427 5.02v14.3zM14.92 7.74c0-.398-.225-.636-.593-.636-.217 0-.441.055-.74.148l-3.328.986c-.198.06-.328.18-.328.406 0 .33.208.575.568.575.195 0 .428-.052.74-.144l3.328-.985c.205-.06.353-.186.353-.35zm0 3.125c0-.398-.225-.636-.593-.636-.217 0-.441.055-.74.148l-3.328.986c-.198.06-.328.18-.328.406 0 .33.208.575.568.575.195 0 .428-.052.74-.144l3.328-.985c.205-.06.353-.186.353-.35zm0 3.063c0-.398-.225-.636-.593-.636-.217 0-.441.055-.74.148l-3.328.986c-.198.06-.328.18-.328.406 0 .33.208.575.568.575.195 0 .428-.052.74-.144l3.328-.985c.205-.06.353-.186.353-.35z"/>
                </svg>
              </div>
              
              <h2 className="text-2xl font-bold font-display text-foreground mb-2">노션으로 내보내기</h2>
              <p className="text-muted-foreground mb-6">현재 진도 현황을 노션 페이지에 표 형태로 동기화합니다.</p>

              <div className="space-y-4 mb-8">
                <label className="block text-sm font-semibold text-foreground">연결할 노션 페이지 선택</label>
                
                {isLoadingPages ? (
                  <div className="h-12 flex items-center justify-center border-2 border-border rounded-xl">
                    <RefreshCw className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                ) : pages && pages.length > 0 ? (
                  <select
                    value={selectedPageId}
                    onChange={(e) => setSelectedPageId(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border-2 border-border bg-background focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none transition-all appearance-none"
                  >
                    <option value="" disabled>페이지를 선택하세요...</option>
                    {pages.map((page) => (
                      <option key={page.id} value={page.id}>{page.title}</option>
                    ))}
                  </select>
                ) : (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
                    사용 가능한 노션 페이지가 없습니다. 노션 연동 설정을 먼저 확인해주세요.
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3">
                <Button type="button" variant="ghost" onClick={onClose}>취소</Button>
                <Button 
                  onClick={handleSync} 
                  isLoading={syncMutation.isPending} 
                  disabled={!selectedPageId || isLoadingPages}
                  className="bg-slate-900 hover:bg-slate-800 hover:shadow-slate-900/30 shadow-slate-900/20"
                >
                  동기화 시작
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
