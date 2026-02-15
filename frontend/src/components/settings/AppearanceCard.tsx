import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Palette, Trash2 } from "lucide-react";
import { THEME_OPTIONS } from "@/lib/settings-constants";

interface AppearanceCardProps {
  theme: string;
  autoSave: boolean;
  onThemeChange: (theme: string) => void;
  onAutoSaveChange: (enabled: boolean) => void;
}

export function AppearanceCard({
  theme,
  autoSave,
  onThemeChange,
  onAutoSaveChange,
}: AppearanceCardProps) {
  return (
    <>
      <Card className="bg-card border border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-4 w-4 text-primary" />
            外观与行为
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-border/50 p-4 hover:border-primary/20 transition-colors">
            <div className="space-y-0.5">
              <Label className="text-base">自动保存草稿</Label>
              <p className="text-sm text-muted-foreground">
                自动将编辑器内容保存到本地存储。
              </p>
            </div>
            <Switch checked={autoSave} onCheckedChange={onAutoSaveChange} />
          </div>

          <div className="space-y-2">
            <Label>主题</Label>
            <Select value={theme} onValueChange={onThemeChange}>
              <SelectTrigger className="bg-card border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-card border-border">
                {THEME_OPTIONS.map(option => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
      
      <Card className="bg-card border border-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2">
            <Trash2 className="h-4 w-4" />
            危险区域
          </CardTitle>
        </CardHeader>
        <CardContent>
           <Button variant="destructive" className="w-full sm:w-auto">
             <Trash2 className="mr-2 h-4 w-4" /> 清除所有数据
           </Button>
           <p className="text-xs text-muted-foreground mt-2">
             这将删除所有本地存储的设置、草稿和题库数据。
           </p>
        </CardContent>
      </Card>
    </>
  );
}
