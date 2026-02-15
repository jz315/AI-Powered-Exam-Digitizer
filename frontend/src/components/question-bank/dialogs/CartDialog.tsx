import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { 
  ShoppingCart, 
  X, 
  GripVertical,
  FileText,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getBadgeClass, getTypeLabel } from "@/lib/constants";
import type { CartQuestion } from "@/contexts/PaperCartContext";

interface SortableCartItemProps {
  question: CartQuestion;
  index: number;
  onRemove: () => void;
}

function SortableCartItem({ question, index, onRemove }: SortableCartItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: question.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex items-start gap-3 p-3 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted/40 transition-colors group",
        isDragging && "shadow-lg ring-2 ring-primary/50"
      )}
    >
      <button
        {...attributes}
        {...listeners}
        className="mt-1 cursor-grab active:cursor-grabbing text-muted-foreground hover:text-primary transition-colors"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <span className="text-sm font-bold text-primary shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
        {index + 1}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Badge className={cn("text-xs", getBadgeClass(question.type))}>
            {getTypeLabel(question.type)}
          </Badge>
          <span className="text-xs text-muted-foreground font-mono">ID: {question.id}</span>
        </div>
        <div className="text-sm text-foreground/80 line-clamp-2">
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
            {question.content.substring(0, 150) + (question.content.length > 150 ? "..." : "")}
          </ReactMarkdown>
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0 opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive hover:bg-destructive/10 transition-all"
        onClick={onRemove}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}

interface CartDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  cartItems: CartQuestion[];
  onRemoveFromCart: (id: string) => void;
  onClearCart: () => void;
  onReorderCart: (oldIndex: number, newIndex: number) => void;
  onGeneratePaper: () => Promise<void>;
  generatingPaper: boolean;
  paperConfig: {
    title: string;
    subtitle: string;
    school: string;
    examTime: string;
    duration: string;
  };
  onPaperConfigChange: (config: CartDialogProps["paperConfig"]) => void;
  showPaperConfig: boolean;
  onShowPaperConfigChange: (show: boolean) => void;
}

export function CartDialog({
  open,
  onOpenChange,
  cartItems,
  onRemoveFromCart,
  onClearCart,
  onReorderCart,
  onGeneratePaper,
  generatingPaper,
  paperConfig,
  onPaperConfigChange,
  showPaperConfig,
  onShowPaperConfigChange,
}: CartDialogProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = cartItems.findIndex(item => item.id === active.id);
      const newIndex = cartItems.findIndex(item => item.id === over.id);
      onReorderCart(oldIndex, newIndex);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-accent" />
            试卷篮
            {cartItems.length > 0 && (
              <Badge variant="secondary" className="ml-2">{cartItems.length} 题</Badge>
            )}
          </DialogTitle>
          <DialogDescription>
            拖拽排序题目，配置试卷信息后生成 PDF
          </DialogDescription>
        </DialogHeader>

        {cartItems.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-12 text-muted-foreground">
            <ShoppingCart className="h-16 w-16 mb-4 opacity-20" />
            <p className="text-lg font-medium">试卷篮为空</p>
            <p className="text-sm mt-1">从题库添加题目到试卷篮</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto space-y-3 py-2">
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext items={cartItems.map(q => q.id)} strategy={verticalListSortingStrategy}>
                {cartItems.map((item, index) => (
                  <SortableCartItem
                    key={item.id}
                    question={item}
                    index={index}
                    onRemove={() => onRemoveFromCart(item.id)}
                  />
                ))}
              </SortableContext>
            </DndContext>
          </div>
        )}

        {cartItems.length > 0 && (
          <div className="border-t pt-4 space-y-4">
            <button
              onClick={() => onShowPaperConfigChange(!showPaperConfig)}
              className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors w-full"
            >
              {showPaperConfig ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              试卷配置
            </button>

            {showPaperConfig && (
              <div className="grid grid-cols-2 gap-4 animate-in slide-in-from-top-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">标题</Label>
                  <Input
                    value={paperConfig.title}
                    onChange={(e) => onPaperConfigChange({ ...paperConfig, title: e.target.value })}
                    placeholder="数学"
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">副标题</Label>
                  <Input
                    value={paperConfig.subtitle}
                    onChange={(e) => onPaperConfigChange({ ...paperConfig, subtitle: e.target.value })}
                    placeholder="期中考试"
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">学校</Label>
                  <Input
                    value={paperConfig.school}
                    onChange={(e) => onPaperConfigChange({ ...paperConfig, school: e.target.value })}
                    placeholder="XX中学"
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">考试时间</Label>
                  <Input
                    value={paperConfig.examTime}
                    onChange={(e) => onPaperConfigChange({ ...paperConfig, examTime: e.target.value })}
                    placeholder="2024年6月"
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5 col-span-2">
                  <Label className="text-xs">时长（分钟）</Label>
                  <Input
                    value={paperConfig.duration}
                    onChange={(e) => onPaperConfigChange({ ...paperConfig, duration: e.target.value })}
                    placeholder="120"
                    className="h-9"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        <DialogFooter className="gap-2">
          {cartItems.length > 0 && (
            <Button variant="outline" onClick={onClearCart} className="text-destructive hover:text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              清空
            </Button>
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)}>关闭</Button>
          {cartItems.length > 0 && (
            <Button onClick={onGeneratePaper} disabled={generatingPaper} className="btn-primary-gradient">
              {generatingPaper ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
              生成试卷
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
