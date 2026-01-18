"""
OCR评估配置文件
"""

import os
from pathlib import Path
from typing import Dict, List


class EvaluationConfig:
    """OCR评估配置"""

    # 基础配置
    BASE_DIR = Path(__file__).parent.parent.parent
    PDF_DIR = BASE_DIR / "data" / "evaluation" / "benchmarks" / "pdfs"
    OUTPUT_DIR = BASE_DIR / "data" / "evaluation"

    # 评估配置
    SAMPLE_PERCENT = 0.1  # 10%抽样
    VARIANT = "ocr_enhanced"  # 评估变体

    # OCR配置
    OCR_CONFIG = {
        "enable_pdf_ocr": True,
        "ocr_engine": "paddleocr",  # paddleocr, gemini, dashscope
        "ocr_languages": ["ch", "en"],
        "ocr_confidence_threshold": 0.6,
        "fallback_to_cloud": True,
        "enable_ocr_cache": True,
        "cache_ttl_hours": 24,
        "enable_ab_testing": False,
        "experiment_groups": {"ocr_enhanced": 1.0},
        "api_keys": {},
    }

    # Ground Truth配置
    GT_CONFIG = {
        "enable_pdf_ocr": False,  # 禁用OCR，使用control变体
        "enable_ab_testing": False,
        "experiment_groups": {"control": 1.0},
    }

    # 评估阈值
    THRESHOLDS = {
        "char_accuracy": 0.85,  # 字符准确率阈值
        "word_accuracy": 0.85,  # 词语准确率阈值
        "overall_score": 0.80,  # 综合得分阈值
    }

    # 评估优先级
    EVALUATION_PRIORITY = [
        "text",  # 文本准确率（最高优先级）
        "table",  # 表格识别
        "header",  # 标题识别
        "list",  # 列表识别
        "formula",  # 公式识别（最低优先级）
    ]

    # 报告配置
    REPORT_CONFIG = {
        "format": "html",  # html, json, csv
        "include_detailed_stats": True,
        "include_page_comparisons": True,
        "max_page_preview_length": 200,
    }

    # 日志配置
    LOG_CONFIG = {
        "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": str(OUTPUT_DIR / "logs" / "evaluation.log"),
    }

    @classmethod
    def get_config(cls) -> Dict:
        """获取完整配置"""
        return {
            "pdf_dir": str(cls.PDF_DIR),
            "output_dir": str(cls.OUTPUT_DIR),
            "sample_percent": cls.SAMPLE_PERCENT,
            "variant": cls.VARIANT,
            "ocr_config": cls.OCR_CONFIG,
            "gt_config": cls.GT_CONFIG,
            "thresholds": cls.THRESHOLDS,
            "evaluation_priority": cls.EVALUATION_PRIORITY,
            "report_config": cls.REPORT_CONFIG,
        }

    @classmethod
    def setup_logging(cls):
        """设置日志"""
        import logging

        log_dir = cls.OUTPUT_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, cls.LOG_CONFIG["level"]),
            format=cls.LOG_CONFIG["format"],
            handlers=[
                logging.FileHandler(cls.LOG_CONFIG["file"], encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

        return logging.getLogger(__name__)


if __name__ == "__main__":
    # 测试配置
    config = EvaluationConfig.get_config()
    print("评估配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
