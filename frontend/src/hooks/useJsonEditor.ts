import { useState, useRef, useEffect, useCallback } from "react";
import type { OnMount, Monaco } from "@monaco-editor/react";
import type * as monacoEditor from "monaco-editor";
import { toast } from "sonner";
import type { ValidationIssue, ValidationStatus } from "@/types/editor";
import { API_BASE } from "@/lib/constants";

const DEFAULT_CODE = "// 在此粘贴OCR结果进行编辑\n[]";

export function useJsonEditor() {
  const [code, setCode] = useState<string>(DEFAULT_CODE);
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>("unknown");
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [isValidating, setIsValidating] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  
  const editorRef = useRef<monacoEditor.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const decorationsRef = useRef<string[]>([]);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    
    editor.updateOptions({
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      fontSize: 14,
      wordWrap: "on",
      formatOnPaste: true,
      formatOnType: true,
      glyphMargin: true,
    });
  };

  const applyEditorDecorations = useCallback((validationIssues: ValidationIssue[]) => {
    if (!editorRef.current || !monacoRef.current) return;
    
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const model = editor.getModel();
    if (!model) return;

    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, []);

    const newDecorations = validationIssues
      .filter(issue => issue.line > 0)
      .map(issue => ({
        range: new monaco.Range(issue.line, 1, issue.line, model.getLineMaxColumn(issue.line)),
        options: {
          isWholeLine: true,
          className: issue.severity === "error" ? "bg-destructive/20" : "bg-warning/20",
          glyphMarginClassName: issue.severity === "error" ? "bg-destructive rounded-full" : "bg-warning rounded-full",
          glyphMarginHoverMessage: { value: issue.message },
          hoverMessage: { value: `**${issue.severity === "error" ? "Error" : "Warning"}**: ${issue.message}` },
        },
      }));

    decorationsRef.current = editor.deltaDecorations([], newDecorations);
  }, []);

  const validateCode = useCallback(async (content: string) => {
    if (!content.trim() || content.trim() === "[]") {
      setValidationStatus("unknown");
      setIssues([]);
      return;
    }

    setIsValidating(true);
    try {
      const response = await fetch(`${API_BASE}/api/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ json_content: content }),
      });
      
      if (!response.ok) {
        throw new Error("Validation request failed");
      }
      
      const data = await response.json();
      const validationIssues: ValidationIssue[] = data.issues || [];
      
      setIssues(validationIssues);
      setValidationStatus(data.is_valid ? "valid" : "invalid");
      applyEditorDecorations(validationIssues);
    } catch {
      try {
        JSON.parse(content);
        setValidationStatus("valid");
        setIssues([]);
        applyEditorDecorations([]);
      } catch (e: unknown) {
        const parseError = e as SyntaxError & { lineNumber?: number };
        setValidationStatus("invalid");
        const errorIssue: ValidationIssue = {
          line: parseError.lineNumber || 0,
          message: parseError.message || "JSON syntax error",
          severity: "error",
        };
        setIssues([errorIssue]);
        applyEditorDecorations([errorIssue]);
      }
    } finally {
      setIsValidating(false);
    }
  }, [applyEditorDecorations]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (code.trim() && code.trim() !== DEFAULT_CODE) {
        validateCode(code);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [code, validateCode]);

  const handleManualValidate = () => {
    validateCode(code);
    if (validationStatus === "valid") {
      toast.success("JSON格式正确！");
    }
  };

  const handleFormat = () => {
    if (editorRef.current) {
      editorRef.current.getAction("editor.action.formatDocument")?.run();
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    toast.success("已复制到剪贴板");
  };

  const handleCopyPrompt = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/prompt`);
      if (response.ok) {
        const data = await response.json();
        navigator.clipboard.writeText(data.prompt || "");
        toast.success("已复制Prompt模板");
      } else {
        const defaultPrompt = `请将以下OCR识别结果转换为结构化JSON格式...`;
        navigator.clipboard.writeText(defaultPrompt);
        toast.success("已复制默认Prompt模板");
      }
    } catch {
      const defaultPrompt = `请将以下OCR识别结果转换为结构化JSON格式，每道题目包含type、content、options(选择题)、answer等字段。`;
      navigator.clipboard.writeText(defaultPrompt);
      toast.success("已复制默认Prompt模板");
    }
  };

  const handleImportToBank = async () => {
    if (validationStatus !== "valid") {
      toast.error("请先确保JSON格式正确");
      return;
    }

    setIsImporting(true);
    try {
      const response = await fetch(`${API_BASE}/api/questions/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ json_data: code }),
      });
      
      if (!response.ok) {
        throw new Error("Import request failed");
      }
      
      const data = await response.json();
      
      if (!data.success) {
        toast.error(data.message || "导入失败");
        return;
      }
      
      if ((data.added || 0) > 0) {
        toast.success(data.message || `成功导入 ${data.added} 道题目到题库！`);
      } else {
        toast.warning(data.message || "未导入任何题目");
      }
    } catch (error) {
      toast.error("导入失败: " + String(error));
    } finally {
      setIsImporting(false);
    }
  };

  const handleIssueClick = (line: number) => {
    if (editorRef.current && line > 0) {
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
      editorRef.current.focus();
    }
  };

  const errorCount = issues.filter(i => i.severity === "error").length;
  const warningCount = issues.filter(i => i.severity === "warning").length;

  return {
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
  };
}
