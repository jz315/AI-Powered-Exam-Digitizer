import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import type { WebSettings, LLMConfig, ApiKeyType } from "@/types/settings";
import { API_BASE, DEFAULT_SETTINGS, DEFAULT_LLM_CONFIG } from "@/lib/settings-constants";

export function useSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [config, setConfig] = useState<WebSettings>(DEFAULT_SETTINGS);
  
  const [keyInputs, setKeyInputs] = useState<Record<ApiKeyType, string>>({
    llm: "",
    gemini: "",
    aliyun: "",
    deepseek_modelverse: "",
    deepseek_siliconflow: "",
    deepseek_custom: "",
  });

  const loadSettings = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/web-settings`);
      if (res.ok) {
        const data = await res.json();
        const localTheme = localStorage.getItem("theme");
        if (localTheme) {
          data.theme = localTheme;
        }
        setConfig(data);
      }
    } catch (e) {
      console.error("Failed to load settings:", e);
      toast.error("加载设置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/web-settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm: config.llm,
          theme: config.theme,
          auto_save: config.auto_save,
        }),
      });
      
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        toast.success("设置保存成功");
      } else {
        toast.error("保存失败");
      }
    } catch (e) {
      console.error("Failed to save settings:", e);
      toast.error("保存设置失败");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveApiKey = async (keyType: ApiKeyType) => {
    const keyValue = keyInputs[keyType];
    if (!keyValue?.trim()) {
      toast.error("请输入 API Key");
      return;
    }
    
    setSavingKey(keyType);
    try {
      const res = await fetch(`${API_BASE}/api/web-settings/set-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: keyValue, key_type: keyType }),
      });
      
      const data = await res.json();
      if (data.success) {
        await loadSettings();
        setKeyInputs(prev => ({ ...prev, [keyType]: "" }));
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
    } catch (e) {
      console.error("Failed to save API key:", e);
      toast.error("保存 API Key 失败");
    } finally {
      setSavingKey(null);
    }
  };

  const handleTestKey = async () => {
    setTesting(true);
    try {
      const res = await fetch(`${API_BASE}/api/web-settings/test-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: keyInputs.llm || null }),
      });
      
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
    } catch (e) {
      console.error("Failed to test API key:", e);
      toast.error("验证 API Key 失败");
    } finally {
      setTesting(false);
    }
  };

  const handleReset = () => {
    setConfig(prev => ({
      ...prev,
      llm: DEFAULT_LLM_CONFIG,
      theme: "dark",
      auto_save: true,
    }));
    toast.info("设置已重置为默认值（未保存）");
  };

  const updateLLM = (key: keyof LLMConfig, value: string) => {
    setConfig(prev => ({
      ...prev,
      llm: { ...prev.llm, [key]: value },
    }));
  };

  const updateConfig = <K extends keyof WebSettings>(key: K, value: WebSettings[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const updateKeyInput = (keyType: ApiKeyType, value: string) => {
    setKeyInputs(prev => ({ ...prev, [keyType]: value }));
  };

  const applyTheme = (theme: string) => {
    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      document.documentElement.classList.toggle("dark", prefersDark);
      localStorage.setItem("theme", prefersDark ? "dark" : "light");
    } else {
      document.documentElement.classList.toggle("dark", theme === "dark");
      localStorage.setItem("theme", theme);
    }
    toast.success("主题已切换");
  };

  return {
    loading,
    saving,
    testing,
    savingKey,
    config,
    keyInputs,
    handleSave,
    handleSaveApiKey,
    handleTestKey,
    handleReset,
    updateLLM,
    updateConfig,
    updateKeyInput,
    applyTheme,
  };
}
