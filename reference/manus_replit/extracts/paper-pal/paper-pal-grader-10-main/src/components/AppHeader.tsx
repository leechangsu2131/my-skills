import { FileCheck, GraduationCap } from "lucide-react";

const AppHeader = () => {
  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="container flex items-center gap-3 py-4">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary">
          <GraduationCap className="w-5 h-5 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-lg font-display font-bold text-foreground">시험 채점기</h1>
          <p className="text-xs text-muted-foreground">PDF 시험지 OCR · 자동 채점 · 결과 마킹</p>
        </div>
        <div className="ml-auto flex items-center gap-2 text-muted-foreground">
          <FileCheck className="w-4 h-4" />
          <span className="text-sm font-medium">Auto Grader</span>
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
