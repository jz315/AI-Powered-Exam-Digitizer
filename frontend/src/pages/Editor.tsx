import { Button } from "@/components/ui/button";
import { RotateCcw, Copy, FileText, Download, Loader2, Code2 } from "lucide-react";
import { useJsonEditor } from "@/hooks/useJsonEditor";
import {
  EditorCard,
  ValidationPanel,
  QuickActionsPanel,
  FormatGuidePanel,
} from "@/components/editor";

export function EditorPanel() {
  const {
    code,
    setCode,
    validationStatus,
    setValidationStatus,
    issues,
    isValidating,
    isImporting,
    errorCount,
    warningCount,
    handleEditorDidMount,
    handleManualValidate,
    handleFormat,
    handleCopy,
    handleCopyPrompt,
    handleImportToBank,
    handleIssueClick,
  } = useJsonEditor();

  return (
    <div className="flex flex-col h-full gap-4 p-6 stagger-children">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl gradient-primary shadow-glow">
            <Code2 className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">JSON编辑器</h1>
            <p className="text-muted-foreground">
              编辑、验证和修正OCR结果，导入题库
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleFormat} className="hover-lift">
            <RotateCcw className="mr-2 h-4 w-4" /> 格式化
          </Button>
          <Button variant="outline" onClick={handleCopy} className="hover-lift">
            <Copy className="mr-2 h-4 w-4" /> 复制
          </Button>
          <Button variant="outline" onClick={handleCopyPrompt} className="hover-lift">
            <FileText className="mr-2 h-4 w-4" /> 复制Prompt
          </Button>
          <Button 
            onClick={handleImportToBank} 
            disabled={validationStatus !== "valid" || isImporting} 
            className="btn-primary-gradient"
          >
            {isImporting ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> 导入中...</>
            ) : (
              <><Download className="mr-2 h-4 w-4" /> 导入题库</>
            )}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full min-h-0">
        <EditorCard
          code={code}
          validationStatus={validationStatus}
          isValidating={isValidating}
          errorCount={errorCount}
          warningCount={warningCount}
          onCodeChange={(value) => {
            setCode(value);
            setValidationStatus("unknown");
          }}
          onEditorMount={handleEditorDidMount}
        />

        <div className="flex flex-col gap-6 lg:col-span-1 overflow-y-auto">
          <ValidationPanel
            issues={issues}
            validationStatus={validationStatus}
            isValidating={isValidating}
            errorCount={errorCount}
            warningCount={warningCount}
            onValidate={handleManualValidate}
            onIssueClick={handleIssueClick}
          />

          <QuickActionsPanel
            validationStatus={validationStatus}
            isImporting={isImporting}
            onCopyPrompt={handleCopyPrompt}
            onImportToBank={handleImportToBank}
          />

          <FormatGuidePanel />
        </div>
      </div>
    </div>
  );
}
