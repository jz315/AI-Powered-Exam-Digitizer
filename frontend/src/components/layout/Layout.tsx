import { useState } from "react";
import { useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { useTheme } from "@/hooks/useTheme";
import { NavItem } from "./NavItem";
import {
  BookOpen,
  ScanText,
  FileJson,
  Settings,
  Menu,
  Moon,
  Sun,
  FileEdit,
  ChevronRight,
  Hexagon,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/ocr", icon: ScanText, label: "智能 OCR" },
  { to: "/editor", icon: FileJson, label: "JSON 编辑器" },
  { to: "/bank", icon: BookOpen, label: "题库管理" },
  { to: "/paper-editor", icon: FileEdit, label: "试卷排版" },
  { to: "/settings", icon: Settings, label: "系统设置" },
] as const;

export const Layout = ({ children }: { children: React.ReactNode }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground font-sans selection:bg-primary/20">
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/5 rounded-full blur-[120px] animate-pulse-slow" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-violet-500/5 rounded-full blur-[120px] animate-pulse-slow" style={{ animationDelay: "1s" }} />
        <div className="absolute inset-0 bg-grid-pattern opacity-[0.4]" />
      </div>

      <aside
        className={cn(
          "relative z-20 flex flex-col m-3 rounded-2xl border border-white/5 shadow-2xl transition-all duration-500 cubic-bezier(0.4, 0, 0.2, 1)",
          sidebarOpen ? "w-72" : "w-20",
          "glass-panel"
        )}
      >
        <div className="flex items-center justify-between p-5 mb-2">
          {sidebarOpen ? (
            <div className="flex items-center gap-3 animate-in-fade-slide">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500 blur-md opacity-40 animate-pulse" />
                <div className="relative bg-gradient-to-br from-blue-500 to-violet-600 w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg">
                  <Hexagon className="w-6 h-6 fill-white/20 stroke-white" />
                </div>
              </div>
              <div className="flex flex-col">
                <h1 className="font-display font-bold text-xl leading-none tracking-tight text-white">
                  Math<span className="text-blue-400">Digitizer</span>
                </h1>
                <span className="text-[10px] text-muted-foreground uppercase tracking-widest mt-1 font-semibold">
                  Enterprise Edition
                </span>
              </div>
            </div>
          ) : (
             <div className="w-full flex justify-center">
                 <div className="bg-gradient-to-br from-blue-500 to-violet-600 w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg">
                  <Hexagon className="w-6 h-6 fill-white/20 stroke-white" />
                </div>
             </div>
          )}
        </div>

        <nav className="flex-1 px-3 space-y-1.5 overflow-y-auto scrollbar-hide py-2">
          {NAV_ITEMS.map((item) => (
            <NavItem
              key={item.to}
              to={item.to}
              icon={item.icon}
              label={item.label}
              expanded={sidebarOpen}
            />
          ))}
        </nav>

        <div className="p-4 mt-auto border-t border-white/5 space-y-2">
           <Button
            variant="ghost"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full justify-between group hover:bg-white/5 text-muted-foreground hover:text-white transition-colors"
          >
            {sidebarOpen && <span className="text-xs font-medium ml-1">收起侧边栏</span>}
            <Menu className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            onClick={toggleTheme}
            className={cn(
              "w-full hover:bg-white/5 text-muted-foreground hover:text-white transition-colors",
              sidebarOpen ? "justify-start px-4" : "justify-center px-0"
            )}
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4 text-yellow-300" />
            ) : (
              <Moon className="h-4 w-4 text-slate-400" />
            )}
            {sidebarOpen && <span className="ml-3 text-sm font-medium">{theme === "dark" ? "浅色模式" : "深色模式"}</span>}
          </Button>
        </div>
      </aside>

      <main className="flex-1 relative z-10 m-3 ml-0 rounded-2xl overflow-hidden glass border border-white/5 shadow-2xl flex flex-col">
         {location.pathname !== "/paper-editor" && (
           <div className="h-16 border-b border-white/5 flex items-center px-8 bg-black/20 backdrop-blur-md sticky top-0 z-10 shrink-0">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="hover:text-foreground transition-colors cursor-pointer">首页</span>
                <ChevronRight className="h-4 w-4 opacity-50" />
                <span className="text-foreground font-medium">
                  {NAV_ITEMS.find(i => i.to === location.pathname)?.label || "Dashboard"}
                </span>
              </div>
              <div className="ml-auto flex items-center gap-4">
                 <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 border-2 border-white/10 shadow-lg" />
              </div>
           </div>
         )}

         <div className={cn(
           "flex-1 overflow-auto scrollbar-thin relative",
           location.pathname === "/paper-editor" ? "" : ""
         )}>
            <div className={cn(
              "animate-in-fade-slide h-full",
              location.pathname === "/paper-editor" ? "p-0" : "p-6 max-w-7xl mx-auto"
            )}>
               {children}
            </div>
         </div>
      </main>

      <Toaster position="top-right" theme={theme as "light" | "dark"} className="font-sans" />
    </div>
  );
};
