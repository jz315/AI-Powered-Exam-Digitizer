import argparse
import sys
import time
from pathlib import Path
from layout_engine import (
    DEFAULT_LAYOUT_MODEL,
    LAYOUT_MODEL_LABELS,
    create_layout_extractor,
    layout_model_label_from_key,
)

def main():
    parser = argparse.ArgumentParser(description="PDF 版面分析工具 CLI")
    
    # 必选参数
    parser.add_argument("pdf_path", help="PDF 文件的路径")
    
    # 可选参数
    parser.add_argument("--out", default="output", help="结果输出目录")
    parser.add_argument("--dpi", type=int, default=200, help="PDF 渲染 DPI (默认 200)")
    parser.add_argument("--conf", type=float, default=0.25, help="布局模型置信度阈值 (默认 0.25)")
    parser.add_argument("--ignore", default=None, help="要忽略的标签 (逗号分隔)，默认忽略 abandon")
    parser.add_argument("--pages", default=None, help="页码范围，例如 1-3,5,8")
    parser.add_argument(
        "--layout-model",
        default=DEFAULT_LAYOUT_MODEL,
        choices=list(LAYOUT_MODEL_LABELS.keys()),
        help="布局模型: " + ", ".join(LAYOUT_MODEL_LABELS.keys()),
    )
    parser.add_argument("--auto-outside-ratio", type=float, default=0.01, help="Auto router: text outside ratio")
    parser.add_argument("--auto-min-text-ratio", type=float, default=0.0005, help="Auto router: min text ratio")
    parser.add_argument("--auto-min-component-area", type=int, default=30, help="Auto router: min component area")

    args = parser.parse_args()

    # 1. 检查文件
    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists():
        print(f"错误: 找不到文件 {pdf_file}")
        sys.exit(1)

    # 2. 解析忽略标签
    ignored_labels = None
    if args.ignore:
        ignored_labels = [label.strip() for label in args.ignore.split(",")]
        print(f"设置忽略标签: {ignored_labels}")
    else:
        if args.layout_model == "doclayout_yolo":
            ignored_labels = ["abandon"]
            print("使用默认忽略列表: ['abandon']")

    # 3. 初始化引擎
    t0 = time.time()
    label = layout_model_label_from_key(args.layout_model)
    print(f"正在加载布局模型: {label} ...")
    try:
        auto_cfg = None
        if args.layout_model == "auto_router":
            auto_cfg = {
                "text_outside_ratio": args.auto_outside_ratio,
                "min_text_ratio": args.auto_min_text_ratio,
                "min_component_area": args.auto_min_component_area,
            }
        extractor = create_layout_extractor(args.layout_model, auto_router_config=auto_cfg)
    except Exception as e:
        print(f"模型加载失败: {e}")
        sys.exit(1)

    # 4. 执行处理
    print(f"开始处理 PDF: {pdf_file.name}")
    try:
        saved_files = extractor.process_pdf(
            pdf_path=pdf_file,
            output_dir=args.out,
            dpi=args.dpi,
            conf=args.conf,
            ignored_labels=ignored_labels,
            page_range=args.pages
        )
        
        t1 = time.time()
        print("-" * 30)
        print(f"处理完成！耗时: {t1 - t0:.2f} 秒")
        print(f"共生成图片: {len(saved_files)} 张")
        print(f"输出目录: {Path(args.out) / pdf_file.stem}")
        
    except Exception as e:
        print(f"处理出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
