import { useState } from "react";
import 'katex/dist/katex.min.css';
import { Button } from "@/components/ui/button";
import { 
  Plus, 
  RefreshCw,
  Library,
  Download,
  Upload,
  ShoppingCart,
  BookOpen,
  BarChart3,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { usePaperCart } from "@/contexts/PaperCartContext";
import { useQuestionBank } from "@/hooks/useQuestionBank";
import { API_BASE } from "@/lib/constants";
import {
  QuestionCard,
  QuestionFiltersBar,
  BulkActions,
  QuestionDialog,
  DeleteDialog,
  BulkDeleteDialog,
  ImportDialog,
  CartDialog,
  StatsDialog,
} from "@/components/question-bank";

export function QuestionBankPanel() {
  const bank = useQuestionBank();
  const { 
    cartItems, 
    addToCart, 
    removeFromCart, 
    clearCart, 
    isInCart, 
    cartCount, 
    reorderCart 
  } = usePaperCart();

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [isBulkDeleteDialogOpen, setIsBulkDeleteDialogOpen] = useState(false);
  const [isCartDialogOpen, setIsCartDialogOpen] = useState(false);
  const [isStatsDialogOpen, setIsStatsDialogOpen] = useState(false);
  
  const [generatingPaper, setGeneratingPaper] = useState(false);
  const [showPaperConfig, setShowPaperConfig] = useState(false);
  const [paperConfig, setPaperConfig] = useState({
    title: "数学",
    subtitle: "",
    school: "",
    examTime: "",
    duration: "",
  });

  const handleAddToCart = () => {
    const selectedQuestions = bank.questions.filter(q => bank.selectedIds.has(q.id));
    let addedCount = 0;
    selectedQuestions.forEach(q => {
      if (!isInCart(q.id)) {
        addToCart(q);
        addedCount++;
      }
    });
    if (addedCount > 0) {
      toast.success(`已添加 ${addedCount} 道题目到试卷篮`);
    } else {
      toast.info("选中的题目已在试卷篮中");
    }
    bank.setSelectedIds(new Set());
  };

  const handleBulkGenerateTags = async () => {
    const selectedQuestionIds = Array.from(bank.selectedIds);
    let successCount = 0;
    for (const qId of selectedQuestionIds) {
      await bank.generateTags(qId);
      successCount++;
    }
    if (successCount > 0) {
      toast.success(`已为 ${successCount} 道题目生成标签`);
    }
    bank.setSelectedIds(new Set());
  };

  const handleBulkGenerateAnswers = async () => {
    const selectedQuestionIds = Array.from(bank.selectedIds);
    let successCount = 0;
    for (const qId of selectedQuestionIds) {
      await bank.generateAnswer(qId);
      successCount++;
    }
    if (successCount > 0) {
      toast.success(`已为 ${successCount} 道题目生成答案`);
    }
    bank.setSelectedIds(new Set());
  };

  const handleGeneratePaper = async () => {
    if (cartItems.length === 0) return;
    setGeneratingPaper(true);
    try {
      const response = await fetch(`${API_BASE}/api/paper/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          questions: cartItems,
          subject: paperConfig.title,
          title: paperConfig.subtitle,
          school: paperConfig.school,
          exam_time: paperConfig.examTime,
          duration: paperConfig.duration,
        }),
      });
      const data = await response.json();
      if (data.success && data.pdf_path) {
        toast.success("生成成功！");
        const pdfUrl = `${API_BASE}/output/question_bank/generated/${data.pdf_path.split(/[/\\]/).pop()}`;
        window.open(pdfUrl, "_blank");
      } else {
        toast.error(data.message || "生成失败");
      }
    } catch (error) {
      console.error(error);
      toast.error("生成试卷失败");
    } finally {
      setGeneratingPaper(false);
    }
  };

  const isAllSelected = bank.filteredQuestions.length > 0 && 
    bank.filteredQuestions.every(q => bank.selectedIds.has(q.id));

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full overflow-y-auto" style={{ height: '100%' }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl gradient-primary shadow-glow">
            <Library className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">题库管理</h1>
            <p className="text-muted-foreground">
              管理、组织和导出数字化题目
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={() => setIsStatsDialogOpen(true)} 
            className="hover-lift"
          >
            <BarChart3 className="mr-2 h-4 w-4" /> 统计
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setIsCartDialogOpen(true)} 
            className={cn("hover-lift relative", cartCount > 0 && "border-accent/50")}
          >
            <ShoppingCart className="mr-2 h-4 w-4" />
            试卷篮
            {cartCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-accent text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-medium">
                {cartCount}
              </span>
            )}
          </Button>
          <Button variant="outline" onClick={() => setIsImportDialogOpen(true)} className="hover-lift">
            <Upload className="mr-2 h-4 w-4" /> 导入
          </Button>
          <Button variant="outline" onClick={bank.handleExport} className="hover-lift">
            <Download className="mr-2 h-4 w-4" /> 导出 {bank.selectedIds.size > 0 && `(${bank.selectedIds.size})`}
          </Button>
          <Button variant="outline" onClick={bank.fetchQuestions} className="hover-lift">
            <RefreshCw className={cn("mr-2 h-4 w-4", bank.loading && "animate-spin")} /> 刷新
          </Button>
          <Button 
            onClick={() => {
              bank.openAddDialog();
              setIsAddDialogOpen(true);
            }} 
            className="btn-primary-gradient"
          >
            <Plus className="mr-2 h-4 w-4" /> 添加题目
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex-1">
          <QuestionFiltersBar
            filters={bank.filters}
            onFiltersChange={(partial) => bank.setFilters(prev => ({ ...prev, ...partial }))}
            allTags={bank.allTags}
            filteredCount={bank.filteredQuestions.length}
            isAllSelected={isAllSelected}
            onSelectAll={bank.handleSelectAll}
          />
        </div>
        <BulkActions
          selectedCount={bank.selectedIds.size}
          onBulkGenerateTags={handleBulkGenerateTags}
          onBulkGenerateAnswers={handleBulkGenerateAnswers}
          onAddToCart={handleAddToCart}
          onBulkDelete={() => setIsBulkDeleteDialogOpen(true)}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 pb-10">
        {bank.loading ? (
          <div className="text-center py-20">
            <RefreshCw className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
            <p className="text-muted-foreground">加载中...</p>
          </div>
        ) : bank.filteredQuestions.length === 0 ? (
          <div className="text-center py-20 text-muted-foreground">
            <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p>没有找到符合条件的题目</p>
            <Button 
              onClick={() => {
                bank.openAddDialog();
                setIsAddDialogOpen(true);
              }} 
              variant="outline" 
              className="mt-4"
            >
              <Plus className="mr-2 h-4 w-4" /> 添加第一道题目
            </Button>
          </div>
        ) : (
          bank.filteredQuestions.map((q) => (
            <QuestionCard
              key={q.id}
              question={q}
              isSelected={bank.selectedIds.has(q.id)}
              onSelect={() => bank.handleSelectOne(q.id)}
              onEdit={() => {
                bank.openEditDialog(q);
                setIsEditDialogOpen(true);
              }}
              onDelete={() => {
                bank.setEditingQuestion(q);
                setIsDeleteDialogOpen(true);
              }}
              onCopy={() => {
                bank.setFormData({
                  content: q.content,
                  type: q.type,
                  options: q.options || ["", "", "", ""],
                  difficulty: q.difficulty || "medium",
                  tags: q.tags || [],
                  answer: q.answer || "",
                  analysis: q.analysis || "",
                  sub_questions: q.sub_questions || [],
                });
                setIsAddDialogOpen(true);
                toast.info("已复制题目，请修改后保存");
              }}
              onToggleStar={() => bank.toggleStar(q.id)}
              onGenerateAnswer={() => bank.generateAnswer(q.id)}
              onGenerateTags={() => bank.generateTags(q.id)}
              onToggleCart={() => {
                if (isInCart(q.id)) {
                  removeFromCart(q.id);
                  toast.success("已从试卷篮移除");
                } else {
                  addToCart(q);
                  toast.success("已添加到试卷篮");
                }
              }}
              isInCart={isInCart(q.id)}
              isGeneratingAnswer={bank.generatingIds.has(q.id)}
              isGeneratingTags={bank.taggingIds.has(q.id)}
              isAnswerExpanded={bank.expandedAnswers.has(q.id)}
              onToggleAnswer={() => {
                bank.setExpandedAnswers(prev => {
                  const next = new Set(prev);
                  if (next.has(q.id)) {
                    next.delete(q.id);
                  } else {
                    next.add(q.id);
                  }
                  return next;
                });
              }}
            />
          ))
        )}
      </div>

      <QuestionDialog
        mode="add"
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        formData={bank.formData}
        onFormChange={bank.setFormData}
        onSubmit={bank.handleCreate}
        saving={bank.saving}
      />

      <QuestionDialog
        mode="edit"
        open={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        formData={bank.formData}
        onFormChange={bank.setFormData}
        onSubmit={bank.handleUpdate}
        saving={bank.saving}
        editingQuestion={bank.editingQuestion}
      />

      <DeleteDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        question={bank.editingQuestion}
        onConfirm={bank.handleDelete}
        saving={bank.saving}
      />

      <BulkDeleteDialog
        open={isBulkDeleteDialogOpen}
        onOpenChange={setIsBulkDeleteDialogOpen}
        count={bank.selectedIds.size}
        onConfirm={bank.handleBulkDelete}
        saving={bank.saving}
      />

      <ImportDialog
        open={isImportDialogOpen}
        onOpenChange={setIsImportDialogOpen}
        onImport={bank.handleImport}
        saving={bank.saving}
      />

      <CartDialog
        open={isCartDialogOpen}
        onOpenChange={setIsCartDialogOpen}
        cartItems={cartItems}
        onRemoveFromCart={removeFromCart}
        onClearCart={clearCart}
        onReorderCart={reorderCart}
        onGeneratePaper={handleGeneratePaper}
        generatingPaper={generatingPaper}
        paperConfig={paperConfig}
        onPaperConfigChange={setPaperConfig}
        showPaperConfig={showPaperConfig}
        onShowPaperConfigChange={setShowPaperConfig}
      />

      <StatsDialog
        open={isStatsDialogOpen}
        onOpenChange={setIsStatsDialogOpen}
        questions={bank.questions}
      />
    </div>
  );
}
