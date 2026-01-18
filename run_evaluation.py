#!/usr/bin/env python3
"""
OCR评估主入口脚本
"""

import sys
import os
import argparse
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.config import EvaluationConfig
from src.evaluation.test_runner import EvaluationTestRunner


def setup_logging():
    """设置日志"""
    import logging

    log_dir = EvaluationConfig.OUTPUT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "evaluation.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    return logging.getLogger(__name__)


async def run_evaluation(args):
    """
    运行评估

    Args:
        args: 命令行参数
    """
    logger = setup_logging()

    # 创建配置
    config = EvaluationConfig.get_config()

    # 更新配置（从命令行参数）
    if args.sample_percent:
        config["sample_percent"] = args.sample_percent
    if args.variant:
        config["variant"] = args.variant
    if args.pdf_dir:
        config["pdf_dir"] = args.pdf_dir

    logger.info("=" * 60)
    logger.info("OCR准确性评估工具")
    logger.info("=" * 60)
    logger.info(f"评估变体: {config['variant']}")
    logger.info(f"抽样比例: {config['sample_percent'] * 100}%")
    logger.info(f"PDF目录: {config['pdf_dir']}")
    logger.info(f"输出目录: {config['output_dir']}")

    # 检查PDF目录
    pdf_dir = Path(config["pdf_dir"])
    if not pdf_dir.exists():
        logger.error(f"PDF目录不存在: {pdf_dir}")
        return 1

    # 统计PDF数量
    pdf_files = list(pdf_dir.glob("*.pdf"))
    logger.info(f"找到 {len(pdf_files)} 个PDF文件")

    # 计算抽样数量
    sample_count = max(1, min(10, int(len(pdf_files) * config["sample_percent"])))
    logger.info(f"将随机抽样 {sample_count} 个文件进行评估")

    # 确认
    if not args.force:
        response = input("\n确认开始评估？(y/n): ")
        if response.lower() != "y":
            logger.info("评估已取消")
            return 0

    # 创建测试运行器
    runner = EvaluationTestRunner(config)

    try:
        # 运行评估
        results = await runner.run_evaluation(
            variant=config["variant"], sample_percent=config["sample_percent"]
        )

        # 输出摘要
        print("\n" + "=" * 60)
        print("评估摘要")
        print("=" * 60)
        print(f"评估变体: {results['variant']}")
        print(f"测试文件数: {len(results['file_results'])}")
        print(f"综合得分: {results['metrics']['overall']['score']:.2%}")
        print(f"字符准确率: {results['metrics']['text']['char_accuracy']:.2%}")
        print(f"词语准确率: {results['metrics']['text']['word_accuracy']:.2%}")
        print(f"表格准确率: {results['metrics']['structure']['table_accuracy']:.2%}")
        print(f"标题准确率: {results['metrics']['structure']['header_accuracy']:.2%}")
        print(f"列表准确率: {results['metrics']['structure']['list_accuracy']:.2%}")
        print(
            f"平均处理时间: {results['metrics']['performance']['avg_processing_time_ms']:.1f}ms"
        )
        print(
            f"处理吞吐量: {results['metrics']['performance']['throughput_pages_per_sec']:.2f} 页/秒"
        )

        # 判断是否通过
        if results["metrics"]["overall"]["passed"]:
            print("\n✅ 评估通过！")
        else:
            print(
                f"\n❌ 评估未通过（综合得分 < {EvaluationConfig.THRESHOLDS['overall_score'] * 100}%)"
            )

        print("\n报告文件:")
        print(f"  HTML: {results['report_path']}")
        print(f"  JSON: {results['json_path']}")
        print("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"评估失败: {e}", exc_info=True)
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="OCR准确性评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置运行评估（10%抽样）
  python run_evaluation.py
  
  # 指定抽样比例
  python run_evaluation.py --sample-percent 0.2
  
  # 指定评估变体
  python run_evaluation.py --variant ocr_basic
  
  # 使用所有PDF文件
  python run_evaluation.py --sample-percent 1.0
  
  # 强制执行（不确认）
  python run_evaluation.py --force
        """,
    )

    parser.add_argument(
        "--variant",
        type=str,
        default="ocr_enhanced",
        choices=["control", "ocr_basic", "ocr_enhanced"],
        help="评估变体（默认: ocr_enhanced）",
    )

    parser.add_argument(
        "--sample-percent",
        type=float,
        default=0.1,
        help="抽样比例 0.0-1.0（默认: 0.1，即10%）",
    )

    parser.add_argument(
        "--pdf-dir",
        type=str,
        help="PDF文件目录（默认: data/evaluation/benchmarks/pdfs）",
    )

    parser.add_argument(
        "--output-dir", type=str, help="输出目录（默认: data/evaluation）"
    )

    parser.add_argument("--force", action="store_true", help="强制执行，不提示确认")

    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    # 运行评估
    return asyncio.run(run_evaluation(args))


if __name__ == "__main__":
    sys.exit(main())
