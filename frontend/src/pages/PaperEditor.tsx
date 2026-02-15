import "katex/dist/katex.min.css";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from "@dnd-kit/core";
import { restrictToWindowEdges } from "@dnd-kit/modifiers";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { Button } from "@/components/ui/button";
import {
  Trash2,
  RefreshCw,
  Download,
  Layers,
  Eye,
  EyeOff,
} from "lucide-react";
import { usePaperEditor } from "@/hooks/usePaperEditor";
import { dropAnimation } from "@/lib/paper-editor-constants";
import {
  QuestionBankPanel,
  InspectorPanel,
  PaperPreview,
} from "@/components/paper-editor";

export function PaperEditorPanel() {
  const {
    loading,
    searchTerm,
    setSearchTerm,
    typeFilter,
    setTypeFilter,
    sections,
    activeId,
    selectedQuestionId,
    setSelectedQuestionId,
    previewOpen,
    setPreviewOpen,
    paperConfig,
    setPaperConfig,
    generatingPaper,
    cartItems,
    paperQuestionIds,
    filteredQuestions,
    totalScore,
    totalQuestions,
    selectedQuestion,
    fetchQuestions,
    importFromCart,
    addQuestionToPaper,
    removeQuestion,
    updateQuestionScore,
    updateSectionTitle,
    clearSections,
    generatePDF,
    handleDragStart,
    handleDragEnd,
    findSectionIndexByQuestionId,
  } = usePaperEditor();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToWindowEdges]}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full w-full bg-zinc-50/50 dark:bg-zinc-950 text-foreground overflow-hidden font-sans">
        <QuestionBankPanel
          questions={filteredQuestions}
          loading={loading}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          typeFilter={typeFilter}
          onTypeFilterChange={setTypeFilter}
          paperQuestionIds={paperQuestionIds}
          onAddQuestion={addQuestionToPaper}
          onRefresh={fetchQuestions}
        />

        <div className="flex-1 flex flex-col relative bg-muted/30 min-h-0">
          <header className="h-14 px-4 border-b border-border/50 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-4">
              <div className="flex flex-col">
                <h1 className="font-bold text-foreground leading-tight">
                  {paperConfig.title || "未命名试卷"}
                </h1>
                <span className="text-xs text-muted-foreground">
                  {paperConfig.subject} · {paperConfig.duration}分钟 ·{" "}
                  {paperConfig.school || "通用模板"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPreviewOpen((prev) => !prev)}
                className="hover:bg-muted/60"
              >
                {previewOpen ? (
                  <EyeOff className="h-4 w-4 mr-2" />
                ) : (
                  <Eye className="h-4 w-4 mr-2" />
                )}
                {previewOpen ? "关闭预览" : "开启预览"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={importFromCart}
                disabled={cartItems.length === 0 || sections.length > 0}
              >
                <Layers className="h-4 w-4 mr-2" /> 导入试卷篮
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={clearSections}
                disabled={sections.length === 0}
                className="hover:bg-destructive/5 hover:text-destructive hover:border-destructive/30 transition-colors"
              >
                <Trash2 className="h-4 w-4 mr-2" /> 清空
              </Button>
              <Button
                className="btn-primary-gradient shadow-lg shadow-primary/20"
                onClick={generatePDF}
                disabled={sections.length === 0 || generatingPaper}
              >
                {generatingPaper ? (
                  <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                导出 PDF
              </Button>
            </div>
          </header>

          <PaperPreview
            sections={sections}
            paperConfig={paperConfig}
            totalScore={totalScore}
            previewOpen={previewOpen}
            selectedQuestionId={selectedQuestionId}
            onSelectQuestion={setSelectedQuestionId}
            onRemoveQuestion={removeQuestion}
            onScoreChange={updateQuestionScore}
            onTitleChange={updateSectionTitle}
            onClearSelection={() => setSelectedQuestionId(null)}
            onOpenPreview={() => setPreviewOpen(true)}
          />
        </div>

        <InspectorPanel
          config={paperConfig}
          setConfig={setPaperConfig}
          selectedQuestion={selectedQuestion}
          onUpdateScore={(newScore) => {
            if (selectedQuestionId) {
              const sectionIdx = findSectionIndexByQuestionId(selectedQuestionId);
              if (sectionIdx !== -1) {
                updateQuestionScore(sectionIdx, selectedQuestionId, newScore);
              }
            }
          }}
          totalScore={totalScore}
          questionCount={totalQuestions}
        />

        <DragOverlay dropAnimation={dropAnimation}>
          {activeId && activeId.startsWith("bank-") ? (
            <div className="w-80 p-4 rounded-xl bg-background shadow-2xl border border-primary/50 opacity-90 rotate-2 cursor-grabbing">
              <div className="flex items-center gap-2 mb-2">
                <div className="h-2 w-12 rounded-full bg-primary/20" />
              </div>
              <div className="h-4 w-3/4 rounded bg-muted/50" />
              <div className="h-4 w-1/2 rounded bg-muted/50 mt-2" />
            </div>
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  );
}
