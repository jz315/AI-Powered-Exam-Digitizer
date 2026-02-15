import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { 
  Trash2, 
  Edit, 
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Tag,
  Copy,
  ShoppingCart,
  Check,
  Star,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getBadgeClass, getTagColor, getTypeLabel, getDifficultyLabel, API_BASE } from "@/lib/constants";
import type { Question } from "@/types/question";

type SubQuestion = {
  content?: string;
  sub_questions?: unknown[];
};

interface QuestionCardProps {
  question: Question;
  isSelected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onCopy: () => void;
  onToggleStar: () => void;
  onGenerateAnswer: () => void;
  onGenerateTags: () => void;
  onToggleCart: () => void;
  isInCart: boolean;
  isGeneratingAnswer: boolean;
  isGeneratingTags: boolean;
  isAnswerExpanded: boolean;
  onToggleAnswer: () => void;
}

export function QuestionCard({
  question,
  isSelected,
  onSelect,
  onEdit,
  onDelete,
  onCopy,
  onToggleStar,
  onGenerateAnswer,
  onGenerateTags,
  onToggleCart,
  isInCart,
  isGeneratingAnswer,
  isGeneratingTags,
  isAnswerExpanded,
  onToggleAnswer,
}: QuestionCardProps) {
  const renderMarkdown = (content: string, className: string) => {
    const processedContent = content.replace(
      /!\[(.*?)\]\((.*?)\)/g, 
      (match, alt, src) => {
        if (src.startsWith('http')) return match;
        const cleanSrc = src.startsWith('/') ? src.substring(1) : src;
        if (cleanSrc.startsWith('assets/')) {
           return `![${alt}](${API_BASE}/${cleanSrc})`;
        }
        return match;
      }
    );

    return (
      <div className={cn("whitespace-pre-wrap markdown-preview", className)}>
        <ReactMarkdown 
          remarkPlugins={[remarkMath]} 
          rehypePlugins={[rehypeKatex]}
          components={{
            img: ({node, ...props}) => (
              <img {...props} className="max-w-full h-auto rounded-lg border border-border my-2 max-h-[300px] object-contain shadow-sm" />
            )
          }}
        >
          {processedContent}
        </ReactMarkdown>
      </div>
    );
  };

  const renderContent = (content: string) => renderMarkdown(content, "text-sm text-foreground/90");

  const renderSubQuestions = (subQuestions: unknown[] | undefined, level = 1) => {
    if (!Array.isArray(subQuestions) || subQuestions.length === 0) return null;

    const items = subQuestions.filter((item): item is SubQuestion => typeof item === "object" && item !== null);
    if (items.length === 0) return null;

    return (
      <div className={cn("space-y-2", level === 1 && "border-l-2 border-border/40 pl-3")}>
        {items.map((sub, idx) => {
          const label = level === 1
            ? `（${idx + 1}）`
            : level === 2
              ? `（${String.fromCharCode(97 + idx)}）`
              : `（${idx + 1}）`;
          const content = typeof sub.content === "string" ? sub.content : "";
          return (
            <div key={`${level}-${idx}`} className="space-y-2">
              <div className="flex items-start gap-2">
                <span className="text-xs text-muted-foreground shrink-0 pt-0.5">{label}</span>
                <div className="flex-1 min-w-0">
                  {content ? renderContent(content) : null}
                </div>
              </div>
              {renderSubQuestions(Array.isArray(sub.sub_questions) ? sub.sub_questions : [], level + 1)}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Card 
      className={cn(
        "glass-card overflow-hidden group transition-all",
        isSelected ? "border-primary/50 bg-primary/5" : "hover:border-primary/30"
      )}
    >
      <CardHeader className="py-3 px-4 border-b border-border/50 flex flex-row items-center justify-between space-y-0 bg-muted/20">
        <div className="flex items-center gap-3">
          <Checkbox 
            checked={isSelected}
            onCheckedChange={onSelect}
            onClick={(e) => e.stopPropagation()}
          />
          <Badge className={cn("text-xs", getBadgeClass(question.type))}>
            {getTypeLabel(question.type)}
          </Badge>
          <span className="text-xs text-muted-foreground font-mono bg-muted/50 px-2 py-0.5 rounded">ID: {question.id}</span>
          {question.difficulty && (
            <Badge variant="outline" className="text-xs">{getDifficultyLabel(question.difficulty)}</Badge>
          )}
          {question.tags?.map(tag => (
            <Badge key={tag} variant="outline" className={cn("text-xs", getTagColor(tag))}>{tag}</Badge>
          ))}
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button 
            variant="ghost" 
            size="icon" 
            className={cn(
              "h-8 w-8",
              question.starred
                ? "text-yellow-500 hover:text-yellow-600"
                : "text-muted-foreground hover:text-yellow-500 hover:bg-yellow-500/10"
            )}
            onClick={onToggleStar}
            title={question.starred ? "取消收藏" : "收藏"}
          >
            <Star className={cn("h-4 w-4", question.starred && "fill-current")} />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className={cn(
              "h-8 w-8",
              isGeneratingAnswer
                ? "text-purple-500 animate-pulse"
                : "text-muted-foreground hover:text-purple-500 hover:bg-purple-500/10"
            )}
            onClick={onGenerateAnswer}
            disabled={isGeneratingAnswer}
            title="AI 生成答案"
          >
            {isGeneratingAnswer ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className={cn(
              "h-8 w-8",
              isGeneratingTags
                ? "text-cyan-500 animate-pulse"
                : "text-muted-foreground hover:text-cyan-500 hover:bg-cyan-500/10"
            )}
            onClick={onGenerateTags}
            disabled={isGeneratingTags}
            title="AI 生成标签"
          >
            {isGeneratingTags ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Tag className="h-4 w-4" />
            )}
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className={cn(
              "h-8 w-8",
              isInCart 
                ? "text-green-500 hover:text-green-600 hover:bg-green-500/10" 
                : "text-muted-foreground hover:text-accent hover:bg-accent/10"
            )}
            onClick={onToggleCart}
            title={isInCart ? "从试卷篮移除" : "添加到试卷篮"}
          >
            {isInCart ? <Check className="h-4 w-4" /> : <ShoppingCart className="h-4 w-4" />}
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-8 w-8 text-muted-foreground hover:text-green-500 hover:bg-green-500/10"
            onClick={onCopy}
            title="复制题目"
          >
            <Copy className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-8 w-8 text-muted-foreground hover:text-primary hover:bg-primary/10"
            onClick={onEdit}
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            onClick={onDelete}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        {renderContent(question.content)}
        
        {(question.type === "single_choice" || question.type === "multiple_choice") && question.options && (
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {question.options.map((opt, idx) => (
              <div key={idx} className="text-xs bg-muted/30 p-3 rounded-lg border border-border/50 text-muted-foreground flex items-start gap-2 hover:bg-muted/50 hover:border-primary/20 transition-colors">
                <span className="font-bold text-primary shrink-0">{String.fromCharCode(65 + idx)}.</span>
                <div className="flex-1 overflow-hidden">
                  {renderMarkdown(opt, "text-xs text-muted-foreground")}
                </div>
              </div>
            ))}
          </div>
        )}

        {Array.isArray(question.sub_questions) && question.sub_questions.length > 0 && (
          <div className="mt-4">
            <div className="text-xs text-muted-foreground mb-2 flex items-center gap-2">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary/60" />
              小问
            </div>
            {renderSubQuestions(question.sub_questions)}
          </div>
        )}

        {(question.answer || question.analysis) && (
          <div className="mt-3 border-t border-border/50 pt-3">
            <button
              onClick={onToggleAnswer}
              className="flex items-center gap-2 text-xs text-muted-foreground hover:text-primary transition-colors"
            >
              {isAnswerExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              <span className="font-medium">
                {isAnswerExpanded ? "收起答案" : "查看答案"}
                {question.analysis && "/解析"}
              </span>
            </button>
            
            {isAnswerExpanded && (
              <div className="mt-2 space-y-2 animate-in slide-in-from-top-2 duration-200">
                {question.answer && (
                  <div className="text-sm bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                    <span className="font-medium text-green-600 dark:text-green-400">答案：</span>
                    <span className="ml-2 text-foreground">{question.answer}</span>
                  </div>
                )}
                {question.analysis && (
                  <div className="text-sm bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                    <span className="font-medium text-blue-600 dark:text-blue-400">解析：</span>
                    <div className="mt-1 text-foreground/80">
                      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {question.analysis}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
