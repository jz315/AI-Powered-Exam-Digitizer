import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QuestionBankPanel } from "./pages/QuestionBank";
import { OcrPanel } from "./pages/Ocr";
import { EditorPanel } from "./pages/Editor";
import { SettingsPanel } from "./pages/Settings";
import { PaperEditorPanel } from "./pages/PaperEditor";
import { PaperCartProvider } from "./contexts/PaperCartContext";
import { Layout } from "./components/layout";

function App() {
  return (
    <BrowserRouter>
      <PaperCartProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/ocr" replace />} />
            <Route path="/ocr" element={<OcrPanel />} />
            <Route path="/editor" element={<EditorPanel />} />
            <Route path="/bank" element={<QuestionBankPanel />} />
            <Route path="/paper-editor" element={<PaperEditorPanel />} />
            <Route path="/settings" element={<SettingsPanel />} />
          </Routes>
        </Layout>
      </PaperCartProvider>
    </BrowserRouter>
  );
}

export default App;
