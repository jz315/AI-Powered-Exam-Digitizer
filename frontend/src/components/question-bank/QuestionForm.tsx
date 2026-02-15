import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, X } from "lucide-react";
import { QUESTION_TYPES, DIFFICULTIES } from "@/lib/constants";
import type { QuestionFormData } from "@/types/question";

interface QuestionFormProps {
  formData: QuestionFormData;
  onChange: (data: QuestionFormData) => void;
}

export function QuestionForm({ formData, onChange }: QuestionFormProps) {
  const updateFormOption = (index: number, value: string) => {
    const newOptions = [...(formData.options || [])];
    newOptions[index] = value;
    onChange({ ...formData, options: newOptions });
  };

  const addOption = () => {
    onChange({ ...formData, options: [...(formData.options || []), ""] });
  };

  const removeOption = (index: number) => {
    const newOptions = (formData.options || []).filter((_, i) => i !== index);
    onChange({ ...formData, options: newOptions });
  };

  return (
    <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
      <div className="space-y-2">
        <Label>题目类型</Label>
        <Select 
          value={formData.type} 
          onValueChange={(v) => onChange({ ...formData, type: v })}
        >
          <SelectTrigger className="input-premium">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {QUESTION_TYPES.map(t => (
              <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>题目内容 *</Label>
        <Textarea 
          placeholder="输入题目内容（支持LaTeX：$x^2$）"
          value={formData.content}
          onChange={(e) => onChange({ ...formData, content: e.target.value })}
          className="min-h-[100px] font-mono text-sm"
        />
      </div>

      {(formData.type === "single_choice" || formData.type === "multiple_choice") && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>选项</Label>
            <Button type="button" variant="ghost" size="sm" onClick={addOption}>
              <Plus className="h-3 w-3 mr-1" /> 添加
            </Button>
          </div>
          {formData.options?.map((opt, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="text-sm font-bold text-primary w-6">{String.fromCharCode(65 + idx)}.</span>
              <Input 
                value={opt}
                onChange={(e) => updateFormOption(idx, e.target.value)}
                placeholder={`选项 ${String.fromCharCode(65 + idx)}`}
                className="input-premium flex-1"
              />
              {(formData.options?.length || 0) > 2 && (
                <Button type="button" variant="ghost" size="icon" onClick={() => removeOption(idx)} className="h-8 w-8 text-destructive">
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>难度</Label>
          <Select 
            value={formData.difficulty || "medium"} 
            onValueChange={(v) => onChange({ ...formData, difficulty: v })}
          >
            <SelectTrigger className="input-premium">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DIFFICULTIES.map(d => (
                <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>答案</Label>
          <Input 
            value={formData.answer || ""}
            onChange={(e) => onChange({ ...formData, answer: e.target.value })}
            placeholder="如：A 或 2x+1"
            className="input-premium"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>标签（逗号分隔）</Label>
        <Input 
          value={formData.tags?.join(", ") || ""}
          onChange={(e) => onChange({ 
            ...formData, 
            tags: e.target.value.split(",").map(t => t.trim()).filter(Boolean) 
          })}
          placeholder="如：代数, 函数"
          className="input-premium"
        />
      </div>

      <div className="space-y-2">
        <Label>解析 / 解答过程</Label>
        <Textarea 
          placeholder="输入解析或解答过程（可选）"
          value={formData.analysis || ""}
          onChange={(e) => onChange({ ...formData, analysis: e.target.value })}
          className="min-h-[80px] font-mono text-sm"
        />
      </div>
    </div>
  );
}
