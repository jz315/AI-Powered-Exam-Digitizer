
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus, Trash2, FileText, Settings, RefreshCw, X, ArrowRight, Download, GripVertical, Save } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface Question {
  id: string;
  type: string;
  content: string;
  options?: string[];
  answer?: string;
  tags?: string[];
  sub_questions?: Question[];
}

interface ApiResponse {
  questions: Question[];
}

function SortableQuestionItem({ 
  question, 
  index, 
  renderContent, 
  onRemove 
}: { 
  question: Question; 
  index: number; 
  renderContent: (c: string) => React.ReactNode; 
  onRemove: (id: string) => void; 
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: question.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="group relative pl-0 mb-8 pb-6 border-b border-dashed border-slate-100 last:border-0 hover:bg-slate-50/50 -mx-4 px-4 rounded-lg transition-colors bg-white z-10"
    >
      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
         <div {...attributes} {...listeners} className="cursor-move p-1 text-slate-400 hover:text-slate-600">
           <GripVertical className="w-5 h-5" />
         </div>
        <Button
          size="icon"
          variant="ghost"
          className="text-red-400 hover:text-red-600 hover:bg-red-50 h-8 w-8"
          onClick={() => onRemove(question.id)}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
      <div className="flex gap-2">
        <span className="font-bold text-slate-900 mt-0.5">{index + 1}.</span>
        <div className="flex-1">
          <div className="mb-2 text-slate-800">
            {renderContent(question.content)}
          </div>

          {question.options && (
            <div className="grid grid-cols-2 gap-x-8 gap-y-2 mt-3">
              {question.options.map((opt, i) => (
                <div key={i} className="flex gap-2">
                  <span className="font-bold">{String.fromCharCode(65 + i)}.</span>
                  <span>{renderContent(opt.replace(/^[A-Z]\.\s*/, ''))}</span>
                </div>
              ))}
            </div>
          )}

          {question.sub_questions && question.sub_questions.length > 0 && (
            <div className="mt-2 space-y-2">
              {question.sub_questions.map((sub, idx) => (
                <div key={idx} className="flex gap-2 text-sm pl-0">
                  <span className="font-medium">({idx + 1})</span>
                  <div>{renderContent(sub.content)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>(() => {
    const saved = localStorage.getItem('paper_basket_ordered');
    return saved ? JSON.parse(saved) : [];
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [generating, setGenerating] = useState(false);
  
  const [showSettings, setShowSettings] = useState(false);
  const [paperTitle, setPaperTitle] = useState(() => localStorage.getItem('paper_title') || "数学模拟试卷");
  const [paperSubject, setPaperSubject] = useState(() => localStorage.getItem('paper_subject') || "Mathematics");
  
  const [activeFilter, setActiveFilter] = useState('全部题目');

  useEffect(() => {
    localStorage.setItem('paper_basket_ordered', JSON.stringify(selectedIds));
  }, [selectedIds]);

  useEffect(() => {
    localStorage.setItem('paper_title', paperTitle);
    localStorage.setItem('paper_subject', paperSubject);
  }, [paperTitle, paperSubject]);

  const fetchQuestions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/questions');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: ApiResponse = await response.json();
      setQuestions(data.questions || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch questions');
      console.error("Fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePDF = async () => {
    if (selectedIds.length === 0) return;
    setGenerating(true);
    
    const orderedQuestions = selectedIds
      .map(id => questions.find(q => q.id === id))
      .filter((q): q is Question => !!q);

    const sections = [];
    
    const choiceQuestions = orderedQuestions.filter(q => 
      q.type === 'single_choice' || q.type === 'multiple_choice' || q.type === 'choice'
    );
    if (choiceQuestions.length > 0) {
      sections.push({
        title: "选择题",
        type: "single_choice",
        questions: choiceQuestions
      });
    }

    const fillQuestions = orderedQuestions.filter(q => q.type === 'fill');
    if (fillQuestions.length > 0) {
      sections.push({
        title: "填空题",
        type: "fill",
        questions: fillQuestions
      });
    }

    const problemQuestions = orderedQuestions.filter(q => 
      !['single_choice', 'multiple_choice', 'choice', 'fill'].includes(q.type)
    );
    if (problemQuestions.length > 0) {
      sections.push({
        title: "解答题",
        type: "problem",
        questions: problemQuestions
      });
    }

    try {
      const examData = {
        meta: {
           title: paperTitle,
           subject: paperSubject
        },
        sections: sections
      };

      const response = await fetch('http://127.0.0.1:8000/api/generate-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          exam_data: examData,
          title: paperTitle
        }),
      });

      if (!response.ok) {
        throw new Error('PDF generation failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${paperTitle}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
      console.error(e);
      alert("生成 PDF 失败。请确保后端服务正在运行。");
    } finally {
      setGenerating(false);
    }
  };

  const toggleSelection = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(prev => prev.filter(item => item !== id));
    } else {
      setSelectedIds(prev => [...prev, id]);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, []);

  const renderContent = (content: string) => {
    const parts = content.split(/(\$[^$]+\$|\\\[[\s\S]*?\\\])/g);
    
    return (
      <span>
        {parts.map((part, index) => {
          if (part.startsWith('$') && part.endsWith('$')) {
            return <InlineMath key={index} math={part.slice(1, -1)} />;
          } else if (part.startsWith('\\[') && part.endsWith('\\]')) {
            return <BlockMath key={index} math={part.slice(2, -2)} />;
          } else {
            return part.split('\n').map((line, i) => (
               <span key={`${index}-${i}`}>
                 {line}
                 {i < part.split('\n').length - 1 && <br />}
               </span>
            ));
          }
        })}
      </span>
    );
  };

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (active.id !== over?.id) {
      setSelectedIds((items) => {
        const oldIndex = items.indexOf(String(active.id));
        const newIndex = items.indexOf(String(over?.id));
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const filteredQuestions = questions.filter(q => {
    if (activeFilter === '全部题目') return true;
    if (q.tags?.some(t => t.includes(activeFilter))) return true;
    if (q.content.includes(activeFilter)) return true;
    
    return false;
  });

  const selectedQuestionsOrdered = selectedIds
    .map(id => questions.find(q => q.id === id))
    .filter((q): q is Question => !!q);

  return (
    <div className="min-h-screen bg-slate-50 relative">
      {showSettings && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center">
           <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowSettings(false)} />
           <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md relative z-10 animate-in zoom-in-95 duration-200">
             <div className="flex justify-between items-center mb-6">
               <h2 className="text-xl font-bold flex items-center gap-2">
                 <Settings className="w-5 h-5" />
                 试卷设置
               </h2>
               <Button variant="ghost" size="icon" onClick={() => setShowSettings(false)}>
                 <X className="w-5 h-5" />
               </Button>
             </div>
             
             <div className="space-y-4">
               <div className="space-y-2">
                 <label className="text-sm font-medium text-slate-700">试卷标题</label>
                 <input 
                   type="text" 
                   value={paperTitle}
                   onChange={(e) => setPaperTitle(e.target.value)}
                   className="flex h-10 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50"
                   placeholder="例如：2024年期末数学考试"
                 />
               </div>
               
               <div className="space-y-2">
                 <label className="text-sm font-medium text-slate-700">学科名称 (English)</label>
                 <input 
                   type="text" 
                   value={paperSubject}
                   onChange={(e) => setPaperSubject(e.target.value)}
                   className="flex h-10 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent"
                   placeholder="e.g. Mathematics"
                 />
                 <p className="text-xs text-slate-500">将显示在试卷左上角</p>
               </div>
             </div>

             <div className="mt-8 flex justify-end gap-2">
               <Button variant="outline" onClick={() => setShowSettings(false)}>取消</Button>
               <Button onClick={() => setShowSettings(false)}>
                 <Save className="w-4 h-4 mr-2" />
                 保存设置
               </Button>
             </div>
           </div>
        </div>
      )}

      {showPreview && (
        <div className="fixed inset-0 z-[60] flex">
          <div 
            className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity" 
            onClick={() => setShowPreview(false)}
          />
          
          <div className="absolute right-0 top-0 bottom-0 w-full max-w-2xl bg-white shadow-xl flex flex-col animate-in slide-in-from-right duration-300">
            <div className="p-4 border-b flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                <h2 className="font-semibold text-lg">试卷预览 (拖拽排序)</h2>
                <Badge variant="secondary" className="ml-2">{selectedQuestionsOrdered.length} 题</Badge>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setShowPreview(false)}>
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-8 bg-white">
              {selectedQuestionsOrdered.length === 0 ? (
                <div className="text-center py-20 text-slate-400">
                  <div className="mb-4 flex justify-center">
                    <FileText className="w-12 h-12 opacity-20" />
                  </div>
                  <p>暂无已选题目。</p>
                  <Button variant="link" onClick={() => setShowPreview(false)}>返回选题</Button>
                </div>
              ) : (
                <div className="max-w-none prose prose-slate">
                  <div className="text-center mb-8 border-b-2 border-black pb-4">
                    <h1 className="text-2xl font-bold mb-2">{paperTitle}</h1>
                    <div className="flex justify-between text-sm text-slate-600">
                      <span>学科: {paperSubject}</span>
                      <span>总分: 100 分</span>
                    </div>
                  </div>
                  
                  <DndContext 
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <SortableContext 
                      items={selectedIds}
                      strategy={verticalListSortingStrategy}
                    >
                      {selectedQuestionsOrdered.map((q, index) => (
                        <SortableQuestionItem
                          key={q.id}
                          index={index}
                          question={q}
                          renderContent={renderContent}
                          onRemove={toggleSelection}
                        />
                      ))}
                    </SortableContext>
                  </DndContext>
                </div>
              )}
            </div>

            <div className="p-4 border-t bg-slate-50 flex justify-between items-center gap-4">
              <div className="text-xs text-slate-500">
                准备导出了吗？这将通过后台生成 LaTeX PDF 文件。
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowPreview(false)}>
                  继续编辑
                </Button>
                <Button 
                  className="bg-blue-600 hover:bg-blue-700 gap-2"
                  onClick={handleGeneratePDF}
                  disabled={generating}
                >
                  {generating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      导出 PDF
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <header className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-slate-900 text-white p-1.5 rounded-lg">
              <FileText className="w-5 h-5" />
            </div>
            <h1 className="font-bold text-xl tracking-tight">Math Digitizer Pro</h1>
            <Badge variant="secondary" className="ml-2">Web 客户端</Badge>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="outline" size="sm" onClick={fetchQuestions}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowSettings(true)}>
              <Settings className="w-4 h-4 mr-2" />
              设置
            </Button>
            <Button size="sm">
              <Plus className="w-4 h-4 mr-2" />
              新建试卷
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-3 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">题库分类</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {['全部题目', '代数', '几何', '微积分'].map((subject) => (
                  <Button
                    key={subject}
                    onClick={() => setActiveFilter(subject)}
                    variant={activeFilter === subject ? 'secondary' : 'ghost'}
                    className={`w-full justify-start font-normal shadow-none border-0 ${
                      activeFilter === subject 
                        ? 'bg-slate-100 text-slate-900 font-medium' 
                        : 'bg-transparent text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {subject}
                  </Button>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="col-span-9 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold tracking-tight">题目列表</h2>
              <span className="text-sm text-slate-500">
                {loading ? '加载中...' : `共显示 ${filteredQuestions.length} 条结果`}
              </span>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
                <strong className="font-bold">错误: </strong>
                <span className="block sm:inline">{error}</span>
                <p className="mt-2 text-sm">请确保后端服务已启动: <code>python server.py</code></p>
              </div>
            )}

            {!loading && filteredQuestions.length === 0 && !error && (
               <div className="text-center py-10 text-slate-500">
                 {activeFilter === '全部题目' 
                   ? '暂未找到题目。请先在 Python 应用中导入一些题目。' 
                   : `在 "${activeFilter}" 分类下暂无题目。`}
               </div>
            )}

            <div className="space-y-6">
              {filteredQuestions.map((q) => (
                <Card 
                  key={q.id} 
                  className={`group hover:shadow-md transition-shadow ${selectedIds.includes(q.id) ? 'border-blue-500 bg-blue-50/10' : ''}`}
                >
                  <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge>{q.type}</Badge>
                        <span className="text-xs text-slate-400 font-mono">ID: {q.id}</span>
                        {q.tags?.map(tag => (
                           <Badge key={tag} variant="outline" className="text-slate-500">{tag}</Badge>
                        ))}
                      </div>
                    </div>
                    <div className={`flex gap-2 ${selectedIds.includes(q.id) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity`}>
                      <Button className="h-8 w-8 text-slate-500 hover:text-red-600 bg-transparent shadow-none hover:bg-red-50 p-0">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                      <Button 
                        size="sm" 
                        className="h-8"
                        variant={selectedIds.includes(q.id) ? "secondary" : "default"}
                        onClick={() => toggleSelection(q.id)}
                      >
                        {selectedIds.includes(q.id) ? "移除" : "加入试卷"}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <div className="prose prose-slate max-w-none text-slate-800">
                      <div>
                        {renderContent(q.content)}
                      </div>

                      {q.options && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                          {q.options.map((opt, i) => (
                            <div key={i} className="flex items-start gap-3 p-3 rounded-md border border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors">
                              <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-slate-100 text-slate-600 text-xs font-bold border border-slate-200 mt-0.5">
                                {String.fromCharCode(65 + i)}
                              </span>
                              <span className="text-slate-700 leading-snug">
                                {renderContent(opt.replace(/^[A-Z]\.\s*/, ''))}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {q.sub_questions && q.sub_questions.length > 0 && (
                        <div className="mt-4 space-y-3 pl-4 border-l-2 border-slate-100">
                          {q.sub_questions.map((sub, idx) => (
                            <div key={idx} className="text-sm">
                              <span className="font-semibold mr-2">({idx + 1})</span>
                              {renderContent(sub.content)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </main>

      {selectedIds.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] p-4 z-50 animate-in slide-in-from-bottom duration-300">
          <div className="container mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-slate-900 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold text-sm">
                {selectedIds.length}
              </div>
              <span className="font-medium text-slate-700">已选题目</span>
              <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-600 hover:bg-red-50" onClick={() => setSelectedIds([])}>
                清空全部
              </Button>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={() => setShowPreview(true)}>
                预览试卷 <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
              <Button 
                className="bg-blue-600 hover:bg-blue-700 text-white shadow-md"
                onClick={handleGeneratePDF}
                disabled={generating}
              >
                {generating ? '生成中...' : '生成 PDF'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
