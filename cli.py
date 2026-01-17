import argparse
import sys
import time
from pathlib import Path

from math_digitizer.config import get_api_key, get_config, SecretKey
from math_digitizer.ocr import (
    DEFAULT_LAYOUT_MODEL,
    LAYOUT_MODEL_LABELS,
    create_layout_extractor,
    layout_model_label_from_key,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PDF layout/OCR CLI")

    parser.add_argument("pdf_path", help="Path to the PDF file")

    parser.add_argument("--out", default="output", help="Output root directory")
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI (default: 200)")
    parser.add_argument("--conf", type=float, default=0.25, help="Layout confidence (default: 0.25)")
    parser.add_argument("--ignore", default=None, help="Comma-separated labels to ignore")
    parser.add_argument("--pages", default=None, help="Page range, e.g. 1-3,5,8")
    parser.add_argument(
        "--layout-model",
        default=DEFAULT_LAYOUT_MODEL,
        choices=list(LAYOUT_MODEL_LABELS.keys()),
        help="Layout model: " + ", ".join(LAYOUT_MODEL_LABELS.keys()),
    )

    parser.add_argument("--no-config", action="store_true", help="Ignore saved config.json")

    parser.add_argument("--deepseek-provider", default=None, help="modelverse, siliconflow, custom")
    parser.add_argument("--deepseek-base-url", default=None, help="Custom DeepSeek base URL")
    parser.add_argument("--deepseek-key", default=None, help="DeepSeek API key")
    parser.add_argument("--deepseek-model", default=None, help="DeepSeek model name override")

    parser.add_argument("--gemini-key", default=None, help="Gemini API key")
    parser.add_argument("--gemini-model", default=None, help="Gemini model name")

    parser.add_argument("--layout-threads", type=int, default=None, help="DeepSeek layout threads")

    parser.add_argument("--auto-outside-ratio", type=float, default=None, help="Auto router: text outside ratio")
    parser.add_argument("--auto-min-text-ratio", type=float, default=None, help="Auto router: min text ratio")
    parser.add_argument("--auto-min-component-area", type=int, default=None, help="Auto router: min component area")
    parser.add_argument("--auto-gemini-probe", action="store_true", help="Auto router: enable Gemini probe")
    parser.add_argument(
        "--router-mode",
        default=None,
        choices=["any", "textness", "second_pass", "gemini"],
        help="Auto router mode",
    )

    parser.add_argument("--print-config", action="store_true", help="Print effective config and exit")

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists():
        print(f"[error] PDF not found: {pdf_file}")
        sys.exit(1)

    use_config = not args.no_config
    cfg = get_config() if use_config else None

    deepseek_provider = args.deepseek_provider or (cfg.deepseek.provider if cfg else "modelverse")
    deepseek_base_url = args.deepseek_base_url or (cfg.deepseek.base_url if cfg else "")
    deepseek_model = args.deepseek_model or (cfg.deepseek.model if cfg else "")

    gemini_model = args.gemini_model or (cfg.gemini.model if cfg else "gemini-1.5-flash")

    auto_outside_ratio = (
        args.auto_outside_ratio
        if args.auto_outside_ratio is not None
        else (cfg.auto_router.outside_ratio if cfg else 0.01)
    )
    auto_min_text_ratio = (
        args.auto_min_text_ratio
        if args.auto_min_text_ratio is not None
        else (cfg.auto_router.min_text_ratio if cfg else 0.0005)
    )
    auto_min_component_area = (
        args.auto_min_component_area
        if args.auto_min_component_area is not None
        else (cfg.auto_router.min_component_area if cfg else 30)
    )
    router_mode = args.router_mode or (cfg.auto_router.router_mode if cfg else "any")

    use_gemini_probe = args.auto_gemini_probe or (cfg.auto_router.gemini_probe if cfg else False)
    if router_mode in ("gemini", "probe"):
        use_gemini_probe = True

    gemini_key = (args.gemini_key or get_api_key(SecretKey.GEMINI) or "").strip()
    deepseek_key = (args.deepseek_key or get_api_key(SecretKey.for_provider(deepseek_provider)) or "").strip()

    layout_threads = args.layout_threads if args.layout_threads is not None else (cfg.layout.threads if cfg else 1)

    if args.print_config:
        print("Effective config:")
        print(f"  use_config={use_config}")
        print(f"  layout_model={args.layout_model}")
        print(f"  deepseek_provider={deepseek_provider}")
        print(f"  deepseek_base_url={deepseek_base_url or 'default'}")
        print(f"  deepseek_model={deepseek_model or 'default'}")
        print(f"  gemini_model={gemini_model}")
        print(f"  layout_threads={layout_threads}")
        print(f"  auto_outside_ratio={auto_outside_ratio}")
        print(f"  auto_min_text_ratio={auto_min_text_ratio}")
        print(f"  auto_min_component_area={auto_min_component_area}")
        print(f"  auto_gemini_probe={use_gemini_probe}")
        print(f"  router_mode={router_mode}")
        sys.exit(0)

    ignored_labels = None
    if args.ignore:
        ignored_labels = [label.strip() for label in args.ignore.split(",") if label.strip()]
        print(f"[info] ignored_labels={ignored_labels}")
    elif args.layout_model == "doclayout_yolo":
        ignored_labels = ["abandon"]
        print("[info] ignored_labels=['abandon']")

    if deepseek_provider == "custom" and not deepseek_base_url:
        print("[error] DeepSeek provider is custom but base_url is empty.")
        sys.exit(1)

    if args.layout_model in ("deepseek_ocr", "auto_router") and not deepseek_key:
        print("[error] DeepSeek key is required for deepseek_ocr/auto_router.")
        sys.exit(1)

    if use_gemini_probe and not gemini_key:
        print("[error] Gemini key is required when auto_gemini_probe is enabled.")
        sys.exit(1)

    t0 = time.time()
    label = layout_model_label_from_key(args.layout_model)
    print(f"[info] loading layout model: {label}")

    try:
        auto_cfg = None
        if args.layout_model == "auto_router":
            auto_cfg = {
                "text_outside_ratio": auto_outside_ratio,
                "min_text_ratio": auto_min_text_ratio,
                "min_component_area": auto_min_component_area,
                "use_gemini_probe": use_gemini_probe,
                "gemini_api_key": gemini_key,
                "gemini_model": gemini_model,
                "router_mode": router_mode,
            }

        extractor = create_layout_extractor(
            args.layout_model,
            deepseek_api_key=deepseek_key or None,
            deepseek_base_url=deepseek_base_url or None,
            deepseek_model=deepseek_model or None,
            auto_router_config=auto_cfg,
        )
    except Exception as e:
        print(f"[error] failed to load model: {e}")
        sys.exit(1)

    print(f"[info] start processing PDF: {pdf_file.name}")
    try:
        layout_kwargs = {}
        if args.layout_model == "deepseek_ocr" and layout_threads:
            layout_kwargs["num_workers"] = int(layout_threads)
            print(f"[info] layout_threads={layout_threads}")

        saved_files = extractor.process_pdf(
            pdf_path=pdf_file,
            output_dir=args.out,
            dpi=args.dpi,
            conf=args.conf,
            ignored_labels=ignored_labels,
            page_range=args.pages,
            **layout_kwargs,
        )

        t1 = time.time()
        print("-" * 30)
        print(f"[ok] done in {t1 - t0:.2f}s")
        print(f"[ok] files saved: {len(saved_files)}")
        print(f"[ok] output_dir: {Path(args.out) / pdf_file.stem}")
    except Exception as e:
        print(f"[error] processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
