import { useOcr } from "@/hooks/useOcr";
import {
  FileDropzone,
  OcrConfigPanel,
  OcrPreview,
  OcrResult,
} from "@/components/ocr";
import { AlertCircle } from "lucide-react";

export function OcrPanel() {
  const {
    file,
    ocrStatus,
    progress,
    result,
    previewImage,
    config,
    showAdvanced,
    setShowAdvanced,
    onDrop,
    startOcr,
    copyResult,
    setLayoutModel,
    setOcrEngine,
    setOcrModel,
    setDeepseekProvider,
    setDeepseekBaseUrl,
    setRouterMode,
    setOutsideRatio,
    setMinTextRatio,
    setGeminiProbe,
    setPageRange,
    setDpi,
    setLayoutThreads,
    navigate,
  } = useOcr();

  return (
    <div className="container mx-auto p-6 h-full flex flex-col gap-6 max-w-full">
      <div className="flex items-center justify-between pb-2 border-b">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">PDF OCR</h1>
          <p className="text-muted-foreground text-sm mt-1">
            提取文档中的数学公式和文本
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0">
        <div className="lg:col-span-4 flex flex-col gap-6 overflow-y-auto pr-1">
          <FileDropzone file={file} onDrop={onDrop} />

          <OcrConfigPanel
            config={config}
            ocrStatus={ocrStatus}
            progress={progress}
            file={file}
            showAdvanced={showAdvanced}
            onShowAdvancedChange={setShowAdvanced}
            onLayoutModelChange={setLayoutModel}
            onOcrEngineChange={setOcrEngine}
            onOcrModelChange={setOcrModel}
            onDeepseekProviderChange={setDeepseekProvider}
            onDeepseekBaseUrlChange={setDeepseekBaseUrl}
            onRouterModeChange={setRouterMode}
            onOutsideRatioChange={setOutsideRatio}
            onMinTextRatioChange={setMinTextRatio}
            onGeminiProbeChange={setGeminiProbe}
            onPageRangeChange={setPageRange}
            onDpiChange={setDpi}
            onLayoutThreadsChange={setLayoutThreads}
            onStartOcr={startOcr}
          />

          {ocrStatus === "error" && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span>处理出错，请重试</span>
            </div>
          )}
        </div>

        <div className="lg:col-span-8 flex flex-col gap-6 h-full min-h-0">
          <OcrPreview previewImage={previewImage} />
          <OcrResult
            result={result}
            onCopy={copyResult}
            onOpenEditor={() => navigate("/editor")}
          />
        </div>
      </div>
    </div>
  );
}
