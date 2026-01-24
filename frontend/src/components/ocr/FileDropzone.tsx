import { useDropzone } from "react-dropzone";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { FileText, Upload } from "lucide-react";

interface FileDropzoneProps {
  file: File | null;
  onDrop: (acceptedFiles: File[]) => void;
}

export function FileDropzone({ file, onDrop }: FileDropzoneProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
  });

  return (
    <Card className="border-dashed shadow-sm">
      <CardContent className="p-0">
        <div
          {...getRootProps()}
          className={cn(
            "flex flex-col items-center justify-center p-8 text-center cursor-pointer transition-colors hover:bg-muted/50 min-h-[160px]",
            isDragActive && "bg-muted/50 border-primary/20",
            !file && "py-12"
          )}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="space-y-3">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mx-auto text-primary">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <p className="font-medium text-sm truncate max-w-[240px]">
                  {file.name}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <Button variant="ghost" size="sm" className="h-8 text-xs">
                更换文件
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center mx-auto text-muted-foreground">
                <Upload className="h-5 w-5" />
              </div>
              <p className="text-sm font-medium">点击或拖拽上传 PDF</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
