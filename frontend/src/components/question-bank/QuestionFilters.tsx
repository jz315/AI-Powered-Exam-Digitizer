import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Search, 
  Filter,
  CheckSquare,
  Square,
  Tag,
  ArrowUpDown,
  BarChart3,
  BookOpen,
  Star,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { QUESTION_TYPES, DIFFICULTIES } from "@/lib/constants";
import type { QuestionFilters } from "@/hooks/useQuestionBank";

interface QuestionFiltersBarProps {
  filters: QuestionFilters;
  onFiltersChange: (filters: Partial<QuestionFilters>) => void;
  allTags: string[];
  filteredCount: number;
  isAllSelected: boolean;
  onSelectAll: () => void;
}

export function QuestionFiltersBar({
  filters,
  onFiltersChange,
  allTags,
  filteredCount,
  isAllSelected,
  onSelectAll,
}: QuestionFiltersBarProps) {
  return (
    <Card className="glass-card">
      <CardContent className="p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-3 w-full md:w-auto flex-1">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={onSelectAll}
            className="h-9 w-9"
            title={isAllSelected ? "取消全选" : "全选"}
          >
            {isAllSelected ? (
              <CheckSquare className="h-5 w-5 text-primary" />
            ) : (
              <Square className="h-5 w-5 text-muted-foreground" />
            )}
          </Button>
          
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="搜索题目..."
              className="pl-10 w-full input-premium"
              value={filters.searchTerm}
              onChange={(e) => onFiltersChange({ searchTerm: e.target.value })}
            />
          </div>
          
          <Select value={filters.typeFilter} onValueChange={(v) => onFiltersChange({ typeFilter: v })}>
            <SelectTrigger className="w-[150px] input-premium">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder="全部类型" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              {QUESTION_TYPES.map(t => (
                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={filters.tagFilter} onValueChange={(v) => onFiltersChange({ tagFilter: v })}>
            <SelectTrigger className="w-[150px] input-premium">
              <div className="flex items-center gap-2">
                <Tag className="h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder="全部标签" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部标签</SelectItem>
              {allTags.map(tag => (
                <SelectItem key={tag} value={tag}>{tag}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={filters.difficultyFilter} onValueChange={(v) => onFiltersChange({ difficultyFilter: v })}>
            <SelectTrigger className="w-[120px] input-premium">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder="全部难度" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部难度</SelectItem>
              {DIFFICULTIES.map(d => (
                <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={filters.sortBy} onValueChange={(v) => onFiltersChange({ sortBy: v })}>
            <SelectTrigger className="w-[130px] input-premium">
              <div className="flex items-center gap-2">
                <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder="排序" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="id">ID 升序</SelectItem>
              <SelectItem value="id-desc">ID 降序</SelectItem>
              <SelectItem value="difficulty">难度 升序</SelectItem>
              <SelectItem value="difficulty-desc">难度 降序</SelectItem>
            </SelectContent>
          </Select>
          
          <Button
            variant={filters.showStarredOnly ? "default" : "outline"}
            size="sm"
            onClick={() => onFiltersChange({ showStarredOnly: !filters.showStarredOnly })}
            className={cn(
              "h-9 px-3",
              filters.showStarredOnly 
                ? "bg-yellow-500 hover:bg-yellow-600 text-white" 
                : "hover:bg-yellow-500/10 hover:text-yellow-600 hover:border-yellow-500/50"
            )}
            title={filters.showStarredOnly ? "显示全部题目" : "仅显示收藏"}
          >
            <Star className={cn("h-4 w-4", filters.showStarredOnly && "fill-current")} />
          </Button>
        </div>
        
        <div className="flex items-center gap-2 text-sm text-muted-foreground whitespace-nowrap px-3 py-1.5 rounded-full bg-muted/50">
          <BookOpen className="h-4 w-4" />
          <span className="font-medium">{filteredCount}</span> 道题目
        </div>
      </CardContent>
    </Card>
  );
}
