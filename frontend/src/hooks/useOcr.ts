import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import type {
  ApiKeysStatus,
  OcrStatus,
  OcrConfig,
  LayoutModel,
  OcrEngine,
  DeepseekProvider,
  RouterMode,
} from "@/types/ocr";
import { DEFAULT_OCR_CONFIG } from "@/lib/ocr-constants";
import { API_BASE } from "@/lib/constants";

export function useOcr() {
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [apiKeysStatus, setApiKeysStatus] = useState<ApiKeysStatus>({
    gemini: false,
    aliyun: false,
    deepseek_modelverse: false,
    deepseek_siliconflow: false,
    deepseek_custom: false,
  });

  const [ocrStatus, setOcrStatus] = useState<OcrStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<string>("");
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const [config, setConfig] = useState<OcrConfig>(DEFAULT_OCR_CONFIG);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (config.ocrEngine === "gemini") {
      setConfig((prev) => ({ ...prev, ocrModel: "gemini-2.0-flash" }));
    } else if (config.ocrEngine === "aliyun") {
      setConfig((prev) => ({ ...prev, ocrModel: "qwen-vl-max" }));
    }
  }, [config.ocrEngine]);

  useEffect(() => {
    fetch(`${API_BASE}/api/web-settings`)
      .then((res) => res.json())
      .then((data) => {
        if (data.api_keys) {
          setApiKeysStatus({
            gemini: data.api_keys.gemini,
            aliyun: data.api_keys.aliyun,
            deepseek_modelverse: data.api_keys.deepseek_modelverse,
            deepseek_siliconflow: data.api_keys.deepseek_siliconflow,
            deepseek_custom: data.api_keys.deepseek_custom,
          });
        }
      })
      .catch(() => {});
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setOcrStatus("idle");
      setProgress(0);
      setResult("");
      setPreviewImage(null);
    }
  }, []);

  const pollJobStatus = useCallback(async (id: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/ocr/status/${id}`);
        if (!response.ok) {
          throw new Error("Status check failed");
        }

        const data = await response.json();

        if (data.progress !== undefined) {
          setProgress(data.progress);
        }

        if (data.preview_image) {
          setPreviewImage(data.preview_image);
        }

        if (data.status === "completed") {
          setOcrStatus("completed");
          setResult(data.result || "");
          toast.success("处理完成");
        } else if (data.status === "error") {
          setOcrStatus("error");
          toast.error("处理失败: " + data.error);
        } else {
          setTimeout(poll, 1000);
        }
      } catch {
        setOcrStatus("error");
        toast.error("状态查询失败");
      }
    };
    poll();
  }, []);

  const startOcr = async (layoutOnly: boolean = false) => {
    if (!file) {
      toast.error("请先选择PDF文件");
      return;
    }

    const needsOcrKey =
      !layoutOnly &&
      (config.ocrEngine === "gemini"
        ? !apiKeysStatus.gemini
        : !apiKeysStatus.aliyun);

    const getDeepseekKeyConfigured = () => {
      if (config.deepseekProvider === "modelverse")
        return apiKeysStatus.deepseek_modelverse;
      if (config.deepseekProvider === "siliconflow")
        return apiKeysStatus.deepseek_siliconflow;
      return apiKeysStatus.deepseek_custom;
    };
    const needsDeepseekKey =
      (config.layoutModel === "deepseek_ocr" ||
        config.layoutModel === "auto_router") &&
      !getDeepseekKeyConfigured();

    if (needsOcrKey || needsDeepseekKey) {
      toast.error("请先在系统设置中配置 API Key");
      navigate("/settings");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("layout_model", config.layoutModel);
    formData.append("ocr_engine", config.ocrEngine);
    formData.append("ocr_model", config.ocrModel);
    formData.append("page_range", config.pageRange);
    formData.append("dpi", config.dpi);
    formData.append("layout_threads", config.layoutThreads);
    formData.append("layout_only", layoutOnly.toString());

    if (
      config.layoutModel === "deepseek_ocr" ||
      config.layoutModel === "auto_router"
    ) {
      formData.append("deepseek_provider", config.deepseekProvider);
      if (config.deepseekProvider === "custom") {
        formData.append("deepseek_base_url", config.deepseekBaseUrl);
      }
    }

    if (config.layoutModel === "auto_router") {
      formData.append("router_mode", config.routerMode);
      formData.append("outside_ratio", config.outsideRatio);
      formData.append("min_text_ratio", config.minTextRatio);
      formData.append("gemini_probe", config.geminiProbe.toString());
      if (config.geminiProbe) {
        formData.append("gemini_probe_model", config.geminiProbeModel);
      }
    }

    setOcrStatus("processing");
    setProgress(0);
    setResult("");
    setPreviewImage(null);

    try {
      const response = await fetch(`${API_BASE}/api/ocr/upload-pdf`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      pollJobStatus(data.job_id);
    } catch (error) {
      setOcrStatus("error");
      toast.error("上传失败: " + String(error));
    }
  };

  const copyResult = () => {
    navigator.clipboard.writeText(result);
    toast.success("已复制");
  };

  const updateConfig = <K extends keyof OcrConfig>(
    key: K,
    value: OcrConfig[K]
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  return {
    file,
    apiKeysStatus,
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
    updateConfig,
    setLayoutModel: (v: LayoutModel) => updateConfig("layoutModel", v),
    setOcrEngine: (v: OcrEngine) => updateConfig("ocrEngine", v),
    setOcrModel: (v: string) => updateConfig("ocrModel", v),
    setDeepseekProvider: (v: DeepseekProvider) =>
      updateConfig("deepseekProvider", v),
    setDeepseekBaseUrl: (v: string) => updateConfig("deepseekBaseUrl", v),
    setRouterMode: (v: RouterMode) => updateConfig("routerMode", v),
    setOutsideRatio: (v: string) => updateConfig("outsideRatio", v),
    setMinTextRatio: (v: string) => updateConfig("minTextRatio", v),
    setGeminiProbe: (v: boolean) => updateConfig("geminiProbe", v),
    setPageRange: (v: string) => updateConfig("pageRange", v),
    setDpi: (v: string) => updateConfig("dpi", v),
    setLayoutThreads: (v: string) => updateConfig("layoutThreads", v),
    navigate,
  };
}
