import { Button } from "@/components/ui/button";
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Plus, Edit, RefreshCw } from "lucide-react";
import { QuestionForm } from "../QuestionForm";
import type { Question, QuestionFormData } from "@/types/question";

interface QuestionDialogProps {
  mode: "add" | "edit";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  formData: QuestionFormData;
  onFormChange: (data: QuestionFormData) => void;
  onSubmit: () => Promise<boolean>;
  saving: boolean;
  editingQuestion?: Question | null;
}

export function QuestionDialog({
  mode,
  open,
  onOpenChange,
  formData,
  onFormChange,
  onSubmit,
  saving,
  editingQuestion,
}: QuestionDialogProps) {
  const handleSubmit = async () => {
    const success = await onSubmit();
    if (success) {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {mode === "add" ? (
              <><Plus className="h-5 w-5 text-primary" /> 添加新题目</>
            ) : (
              <><Edit className="h-5 w-5 text-primary" /> 编辑题目</>
            )}
          </DialogTitle>
          <DialogDescription>
            {mode === "add" 
              ? "创建新题目添加到题库。支持LaTeX数学公式。"
              : `修改题目信息。ID: ${editingQuestion?.id}`
            }
          </DialogDescription>
        </DialogHeader>
        <QuestionForm formData={formData} onChange={onFormChange} />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleSubmit} disabled={saving} className="btn-primary-gradient">
            {saving ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : (mode === "add" ? <Plus className="mr-2 h-4 w-4" /> : <Edit className="mr-2 h-4 w-4" />)}
            {mode === "add" ? "创建题目" : "保存更改"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
