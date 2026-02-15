import { Button } from "@/components/ui/button";
import { Trash2, Sparkles, Tag, ShoppingCart } from "lucide-react";

interface BulkActionsProps {
  selectedCount: number;
  onBulkGenerateTags: () => void;
  onBulkGenerateAnswers: () => void;
  onAddToCart: () => void;
  onBulkDelete: () => void;
}

export function BulkActions({
  selectedCount,
  onBulkGenerateTags,
  onBulkGenerateAnswers,
  onAddToCart,
  onBulkDelete,
}: BulkActionsProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <Button 
        variant="outline" 
        size="sm"
        onClick={onBulkGenerateTags}
        className="animate-fade-in border-cyan-500/50 text-cyan-600 hover:bg-cyan-500/10"
      >
        <Tag className="mr-2 h-4 w-4" /> AI打标签 ({selectedCount})
      </Button>
      <Button 
        variant="outline" 
        size="sm"
        onClick={onBulkGenerateAnswers}
        className="animate-fade-in border-purple-500/50 text-purple-600 hover:bg-purple-500/10"
      >
        <Sparkles className="mr-2 h-4 w-4" /> AI答案 ({selectedCount})
      </Button>
      <Button 
        variant="outline" 
        size="sm"
        onClick={onAddToCart}
        className="animate-fade-in border-accent/50 text-accent hover:bg-accent/10"
      >
        <ShoppingCart className="mr-2 h-4 w-4" /> 加入试卷篮 ({selectedCount})
      </Button>
      <Button 
        variant="destructive" 
        size="sm"
        onClick={onBulkDelete}
        className="animate-fade-in"
      >
        <Trash2 className="mr-2 h-4 w-4" /> 删除 ({selectedCount})
      </Button>
    </div>
  );
}
