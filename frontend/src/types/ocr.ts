export interface ApiKeysStatus {
  gemini: boolean;
  aliyun: boolean;
  deepseek_modelverse: boolean;
  deepseek_siliconflow: boolean;
  deepseek_custom: boolean;
}

export type OcrStatus = "idle" | "processing" | "completed" | "error";

export type LayoutModel = "auto_router" | "doclayout_yolo" | "deepseek_ocr" | "pp_doclayout";

export type OcrEngine = "gemini" | "aliyun";

export type DeepseekProvider = "modelverse" | "siliconflow" | "custom";

export type RouterMode = "any" | "textness" | "second_pass";

export interface OcrConfig {
  layoutModel: LayoutModel;
  ocrEngine: OcrEngine;
  ocrModel: string;
  deepseekProvider: DeepseekProvider;
  deepseekBaseUrl: string;
  routerMode: RouterMode;
  outsideRatio: string;
  minTextRatio: string;
  geminiProbe: boolean;
  geminiProbeModel: string;
  pageRange: string;
  dpi: string;
  layoutThreads: string;
}

export interface OcrJobResponse {
  job_id: string;
}

export interface OcrStatusResponse {
  status: OcrStatus;
  progress?: number;
  result?: string;
  error?: string;
  preview_image?: string;
}

export interface LayoutModelOption {
  value: LayoutModel;
  label: string;
}
