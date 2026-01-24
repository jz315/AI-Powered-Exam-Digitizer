import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GripVertical, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Question } from "@/types/paper-editor";
import { getBadgeClass, getTypeLabel } from "@/lib/paper-editor-constants";

interface DraggableQuestionCardProps {
  question: Question;
  onAdd: () => void;
  isInPaper: boolean;
}

export function DraggableQuestionCard({
  question,
  onAdd,
  isInPaper,
}: DraggableQuestionCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id: `bank-${question.id}`,
      data: { type: "bank-question", question },
    });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "group relative p-4 rounded-xl border bg-card transition-all duration-200",
        isInPaper
          ? "border-primary/20 bg-primary/5 opacity-60"
          : "border-border/40 hover:border-primary/40 hover:shadow-md hover:-translate-y-0.5"
      )}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-start gap-3">
        <div className="mt-1 cursor-grab active:cursor-grabbing text-muted-foreground/30 group-hover:text-muted-foreground transition-colors">
          <GripVertical className="h-4 w-4" />
        </div>

        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex items-center justify-between">
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] h-5 px-1.5 border font-normal",
                getBadgeClass(question.type)
              )}
            >
              {getTypeLabel(question.type)}
            </Badge>
            {question.difficulty && (
              <span className="text-[10px] text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded">
                {question.difficulty}
              </span>
            )}
          </div>

          <div className="text-sm text-foreground/80 line-clamp-3 leading-relaxed font-serif">
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {question.content}
            </ReactMarkdown>
          </div>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "absolute right-2 top-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-all",
            isInPaper && "hidden"
          )}
          onClick={(e) => {
            e.stopPropagation();
            onAdd();
          }}
        >
          <div className="rounded-full bg-primary/10 p-1 text-primary hover:bg-primary hover:text-primary-foreground transition-colors">
            <Plus className="h-4 w-4" />
          </div>
        </Button>
      </div>
    </div>
  );
}
