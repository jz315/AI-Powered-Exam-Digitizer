import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Upload, RefreshCw } from "lucide-react";

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (jsonData: string) => Promise<boolean>;
  saving: boolean;
}

export function ImportDialog({
  open,
  onOpenChange,
  onImport,
  saving,
}: ImportDialogProps) {
  const [importJson, setImportJson] = useState("");

  const handleImport = async () => {
    const success = await onImport(importJson);
    if (success) {
      setImportJson("");
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" /> 导入题目
          </DialogTitle>
          <DialogDescription>
            粘贴试卷 JSON 数据导入题目（目前仅支持 sections 格式）。
          </DialogDescription>
        </DialogHeader>
        <Textarea 
          placeholder='{"sections": [{"type": "problem", "questions": [...]}]}'
          value={importJson}
          onChange={(e) => setImportJson(e.target.value)}
          className="min-h-[200px] font-mono text-sm"
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleImport} disabled={saving || !importJson.trim()} className="btn-primary-gradient">
            {saving ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
            导入
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
