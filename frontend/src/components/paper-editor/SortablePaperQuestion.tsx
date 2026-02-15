import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PaperQuestion } from "@/types/paper-editor";

interface SortablePaperQuestionProps {
  question: PaperQuestion;
  index: number;
  sectionIndex: number;
  onRemove: () => void;
  onScoreChange: (score: number) => void;
  isSelected: boolean;
  onSelect: () => void;
}

export function SortablePaperQuestion({
  question,
  index,
  sectionIndex,
  onRemove,
  onScoreChange: _onScoreChange,
  isSelected,
  onSelect,
}: SortablePaperQuestionProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: question.id,
      data: { type: "paper-question", question, sectionIndex },
    });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0 : 1,
    zIndex: isDragging ? 999 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
      className={cn(
        "group relative flex gap-4 p-4 rounded-lg transition-all duration-200 border border-transparent",
        isSelected ? "bg-primary/5 ring-1 ring-primary/20" : "hover:bg-muted/30",
        isDragging && "opacity-0"
      )}
    >
      <div className="flex flex-col items-center gap-1 shrink-0 w-10 pt-1">
        <span className="text-lg font-bold text-foreground/40 font-serif select-none">
          {index + 1}
        </span>
        <div
          className="text-xs text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded cursor-pointer hover:bg-muted"
          title="点击修改分数"
        >
          {question.score}分
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="prose prose-sm dark:prose-invert max-w-none font-serif leading-relaxed text-foreground/90">
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
            {question.content}
          </ReactMarkdown>
        </div>

        {question.options && question.options.length > 0 && (
          <div className="grid grid-cols-2 gap-4 mt-3 pl-2">
            {question.options.map((opt, idx) => (
              <div
                key={idx}
                className="flex items-baseline gap-2 text-sm font-serif text-foreground/80"
              >
                <span className="font-semibold text-foreground/60">
                  {String.fromCharCode(65 + idx)}.
                </span>
                <div>
                  <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {opt}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="absolute right-2 top-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          {...attributes}
          {...listeners}
          className="p-1.5 text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing rounded hover:bg-muted"
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="p-1.5 text-muted-foreground hover:text-destructive rounded hover:bg-destructive/10"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
