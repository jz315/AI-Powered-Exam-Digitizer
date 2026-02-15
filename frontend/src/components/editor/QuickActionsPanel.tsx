import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Save, FileText, Download, Loader2 } from "lucide-react";
import type { ValidationStatus } from "@/types/editor";

interface QuickActionsPanelProps {
  validationStatus: ValidationStatus;
  isImporting: boolean;
  onCopyPrompt: () => void;
  onImportToBank: () => void;
}

export function QuickActionsPanel({
  validationStatus,
  isImporting,
  onCopyPrompt,
  onImportToBank,
}: QuickActionsPanelProps) {
  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Save className="h-4 w-4 text-primary" />
          快捷操作
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button 
          variant="outline" 
          className="w-full hover-lift justify-start"
          onClick={onCopyPrompt}
        >
          <FileText className="mr-2 h-4 w-4" /> 复制 Prompt 模板
        </Button>
        <Button 
          className="w-full btn-primary-gradient justify-start"
          onClick={onImportToBank}
          disabled={validationStatus !== "valid" || isImporting}
        >
          {isImporting ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> 导入中...</>
          ) : (
            <><Download className="mr-2 h-4 w-4" /> 导入到题库</>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
