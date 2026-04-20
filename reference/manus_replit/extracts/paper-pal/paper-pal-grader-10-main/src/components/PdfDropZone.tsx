import { useCallback, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PdfDropZoneProps {
  onFilesSelected: (files: File[]) => void;
  multiple?: boolean;
  label: string;
  description: string;
  files: File[];
  onRemoveFile?: (index: number) => void;
}

const PdfDropZone = ({ onFilesSelected, multiple = false, label, description, files, onRemoveFile }: PdfDropZoneProps) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const droppedFiles = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
      if (droppedFiles.length > 0) {
        onFilesSelected(multiple ? droppedFiles : [droppedFiles[0]]);
      }
    },
    [onFilesSelected, multiple]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(e.target.files || []);
      if (selected.length > 0) {
        onFilesSelected(multiple ? selected : [selected[0]]);
      }
      e.target.value = '';
    },
    [onFilesSelected, multiple]
  );

  return (
    <div className="space-y-3">
      <div
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          isDragOver
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/50 hover:bg-muted/50'
        }`}
      >
        <input
          type="file"
          accept=".pdf"
          multiple={multiple}
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragOver ? 'text-primary' : 'text-muted-foreground'}`} />
        <p className="font-semibold text-foreground">{label}</p>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, idx) => (
            <div key={`${file.name}-${idx}`} className="flex items-center gap-3 p-3 rounded-lg bg-muted/50 border border-border">
              <FileText className="w-5 h-5 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate text-foreground">{file.name}</p>
                <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
              {onRemoveFile && (
                <Button variant="ghost" size="icon" className="shrink-0 h-7 w-7" onClick={() => onRemoveFile(idx)}>
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PdfDropZone;
