import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Image as ImageIcon } from "lucide-react";

interface OcrPreviewProps {
  previewImage: string | null;
}

export function OcrPreview({ previewImage }: OcrPreviewProps) {
  return (
    <Card className="flex-1 min-h-[300px] flex flex-col shadow-sm border-border/60">
      <CardHeader className="py-3 px-5 border-b bg-muted/10 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <ImageIcon className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium">版面预览</CardTitle>
        </div>
        {previewImage && (
          <div className="flex gap-2 text-[10px]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500" /> 文本
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" /> 公式
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-500" /> 图片
            </span>
          </div>
        )}
      </CardHeader>
      <CardContent className="flex-1 p-0 bg-muted/5 relative overflow-hidden flex items-center justify-center">
        {previewImage ? (
          <div className="w-full h-full overflow-auto p-4 flex justify-center items-start">
            <img
              src={previewImage}
              alt="Layout"
              className="max-w-full shadow-sm border rounded"
            />
          </div>
        ) : (
          <div className="text-center text-muted-foreground/40">
            <ImageIcon className="h-10 w-10 mx-auto mb-2 opacity-20" />
            <p className="text-sm">暂无预览内容</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
