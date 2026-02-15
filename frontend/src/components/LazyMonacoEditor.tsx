import { Suspense, lazy } from "react";
import { Loader2 } from "lucide-react";
import type { EditorProps } from "@monaco-editor/react";

const MonacoEditor = lazy(() => import("@monaco-editor/react"));

interface LazyMonacoEditorProps extends EditorProps {
  fallbackHeight?: string;
}

function EditorFallback({ height = "100%" }: { height?: string }) {
  return (
    <div 
      className="flex items-center justify-center bg-muted/50 rounded-lg"
      style={{ height }}
    >
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="text-sm">加载编辑器...</span>
      </div>
    </div>
  );
}

export function LazyMonacoEditor({ fallbackHeight = "400px", ...props }: LazyMonacoEditorProps) {
  return (
    <Suspense fallback={<EditorFallback height={fallbackHeight} />}>
      <MonacoEditor {...props} />
    </Suspense>
  );
}

export default LazyMonacoEditor;
