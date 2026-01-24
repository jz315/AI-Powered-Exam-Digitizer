import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { RotateCcw, Save, Key, Cpu, Palette, Settings2, Loader2 } from "lucide-react";
import { useSettings } from "@/hooks/useSettings";
import { ApiKeyCard, LLMConfigCard, AppearanceCard } from "@/components/settings";
import { API_KEY_CONFIGS } from "@/lib/settings-constants";
import type { ApiKeyType } from "@/types/settings";

export function SettingsPanel() {
  const {
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
  } = useSettings();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-6 p-6 max-w-4xl mx-auto w-full stagger-children">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl gradient-primary shadow-glow">
            <Settings2 className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">系统设置</h1>
            <p className="text-muted-foreground">
              管理API密钥、模型配置和应用偏好
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReset} className="hover-lift">
            <RotateCcw className="mr-2 h-4 w-4" /> 重置
          </Button>
          <Button onClick={handleSave} disabled={saving} className="btn-primary-gradient">
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            保存更改
          </Button>
        </div>
      </div>

      <Tabs defaultValue="keys" className="flex-1">
        <TabsList className="grid w-full grid-cols-3 lg:w-[450px] glass p-1">
          <TabsTrigger value="keys" className="data-[state=active]:gradient-primary data-[state=active]:text-white data-[state=active]:shadow-glow transition-all">
            <Key className="h-4 w-4 mr-2" /> API密钥
          </TabsTrigger>
          <TabsTrigger value="model" className="data-[state=active]:gradient-primary data-[state=active]:text-white data-[state=active]:shadow-glow transition-all">
            <Cpu className="h-4 w-4 mr-2" /> 模型
          </TabsTrigger>
          <TabsTrigger value="appearance" className="data-[state=active]:gradient-primary data-[state=active]:text-white data-[state=active]:shadow-glow transition-all">
            <Palette className="h-4 w-4 mr-2" /> 外观
          </TabsTrigger>
        </TabsList>

        <TabsContent value="keys" className="space-y-4 mt-6">
          {API_KEY_CONFIGS.map((keyConfig) => (
            <ApiKeyCard
              key={keyConfig.id}
              config={keyConfig}
              apiKeysStatus={config.api_keys}
              keyInput={keyInputs[keyConfig.id as ApiKeyType]}
              savingKey={savingKey}
              testing={keyConfig.hasTestButton ? testing : undefined}
              onKeyInputChange={(value) => updateKeyInput(keyConfig.id as ApiKeyType, value)}
              onSave={() => handleSaveApiKey(keyConfig.id as ApiKeyType)}
              onTest={keyConfig.hasTestButton ? handleTestKey : undefined}
            />
          ))}
        </TabsContent>

        <TabsContent value="model" className="space-y-4 mt-6">
          <LLMConfigCard
            config={config.llm}
            onProviderChange={(v) => updateLLM("provider", v)}
            onModelChange={(v) => updateLLM("model", v)}
            onBaseUrlChange={(v) => updateLLM("base_url", v)}
          />
        </TabsContent>

        <TabsContent value="appearance" className="space-y-4 mt-6">
          <AppearanceCard
            theme={config.theme}
            autoSave={config.auto_save}
            onThemeChange={(v) => {
              updateConfig("theme", v);
              applyTheme(v);
            }}
            onAutoSaveChange={(c) => updateConfig("auto_save", c)}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
