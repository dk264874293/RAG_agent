"""
Ground Truth生成器
使用EnhancedPdfExtractor的control变体生成参考文本
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio

from ..extractor.pdf_extractor import EnhancedPdfExtractor
from ..pipeline.document_processor import DocumentProcessingPipeline

logger = logging.getLogger(__name__)


class GroundTruthGenerator:
    """
    Ground Truth生成器
    使用control变体的EnhancedPdfExtractor生成高质量的参考文本
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化生成器

        Args:
            config: 配置字典，用于初始化提取器
        """
        self.config = config or {}
        # 确保使用control变体
        self.config.update(
            {
                "enable_pdf_ocr": False,  # 禁用OCR，使用纯文本提取
                "enable_ab_testing": False,  # 禁用A/B测试
                "experiment_groups": {"control": 1.0},  # 100%使用control变体
            }
        )

    def generate_for_pdf(self, pdf_path: str, output_dir: str) -> Dict[str, Any]:
        """
        为单个PDF生成Ground Truth

        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录

        Returns:
            包含Ground Truth信息的字典
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        pdf_stem = pdf_path.stem
        json_file = output_path / f"{pdf_stem}_ground_truth.json"

        # 检查是否已存在
        if json_file.exists():
            logger.info(f"Ground Truth已存在: {json_file}")
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)

        logger.info(f"开始生成Ground Truth: {pdf_path.name}")

        # 使用EnhancedPdfExtractor的control变体
        extractor = EnhancedPdfExtractor(
            file_path=str(pdf_path),
            tenant_id="ground_truth",
            user_id="evaluation",
            config=self.config,
        )

        # 提取文档
        try:
            documents = extractor.extract()

            # 构建Ground Truth结构
            ground_truth = {
                "pdf_file": pdf_path.name,
                "pdf_path": str(pdf_path),
                "total_pages": len(documents),
                "pages": [],
                "metadata": {
                    "generator": "GroundTruthGenerator",
                    "extractor": "EnhancedPdfExtractor (control variant)",
                    "config": self.config,
                },
                "extraction_stats": extractor.get_ocr_stats()
                if hasattr(extractor, "get_ocr_stats")
                else {},
            }

            # 处理每一页
            for i, doc in enumerate(documents):
                page_content = doc.page_content
                metadata = doc.metadata if hasattr(doc, "metadata") else {}

                # 分析页面结构（简化版本）
                structures = self._analyze_page_structure(page_content, i)

                page_data = {
                    "page_num": i,
                    "content": page_content,
                    "metadata": metadata,
                    "structures": structures,
                    "content_length": len(page_content),
                }

                ground_truth["pages"].append(page_data)

            # 保存到JSON文件
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(ground_truth, f, ensure_ascii=False, indent=2)

            logger.info(f"Ground Truth生成完成: {json_file}")
            return ground_truth

        except Exception as e:
            logger.error(f"生成Ground Truth失败: {pdf_path.name}, 错误: {e}")
            raise

    def _analyze_page_structure(self, content: str, page_num: int) -> Dict[str, Any]:
        """
        分析页面结构（简化版本）

        Args:
            content: 页面文本内容
            page_num: 页面编号

        Returns:
            结构信息字典
        """
        structures = {
            "tables": [],
            "headers": [],
            "lists": [],
            "formulas": [],
        }

        # 简单识别标题（基于行首空格和字体大小推断）
        lines = content.split("\n")
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检测可能的标题（以数字开头、短文本等）
            if len(line) < 100 and line.isupper():
                structures["headers"].append(
                    {"level": 1, "text": line, "line_num": line_num, "confidence": 0.7}
                )
            elif line.startswith(
                ("第", "一、", "二、", "三、", "1.", "2.", "3.", "•", "-", "*", "·")
            ):
                structures["headers"].append(
                    {"level": 2, "text": line, "line_num": line_num, "confidence": 0.6}
                )

            # 检测列表项
            if (
                line.startswith(("•", "-", "*", "·", "○", "□", "■"))
                or line[0].isdigit()
                and "." in line[:3]
            ):
                structures["lists"].append(
                    {
                        "type": "unordered"
                        if line.startswith(("•", "-", "*"))
                        else "ordered",
                        "text": line,
                        "line_num": line_num,
                    }
                )

            # 检测简单表格（基于对齐和分隔符）
            if "|" in line or ("  " in line and line.count("  ") > 3):
                # 简单表格检测
                structures["tables"].append(
                    {
                        "id": len(structures["tables"]) + 1,
                        "line_num": line_num,
                        "content": line,
                        "confidence": 0.5,
                    }
                )

            # 检测数学公式（简单模式）
            if any(
                pattern in line
                for pattern in ["=", "≈", "≤", "≥", "±", "×", "÷", "∑", "∫", "∂"]
            ):
                structures["formulas"].append(
                    {
                        "id": len(structures["formulas"]) + 1,
                        "line_num": line_num,
                        "content": line,
                        "type": "simple",
                    }
                )

        return structures

    async def generate_for_directory(
        self, pdf_dir: str, output_dir: str, sample_percent: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        为目录中的PDF文件生成Ground Truth

        Args:
            pdf_dir: PDF目录路径
            output_dir: 输出目录
            sample_percent: 抽样百分比（0.1表示10%）

        Returns:
            Ground Truth列表
        """
        pdf_dir = Path(pdf_dir)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"PDF目录不存在: {pdf_dir}")

        # 获取所有PDF文件
        pdf_files = list(pdf_dir.glob("*.pdf"))
        total_files = len(pdf_files)

        if total_files == 0:
            logger.warning(f"目录中没有PDF文件: {pdf_dir}")
            return []

        # 计算抽样数量（最少1个，最多10个）
        sample_count = max(1, min(10, int(total_files * sample_percent)))
        logger.info(f"找到 {total_files} 个PDF文件，抽样 {sample_count} 个进行测试")

        # 随机选择文件
        import random

        selected_files = random.sample(pdf_files, sample_count)

        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成Ground Truth
        results = []
        for pdf_file in selected_files:
            try:
                result = self.generate_for_pdf(str(pdf_file), str(output_path))
                results.append(result)
            except Exception as e:
                logger.error(f"生成 {pdf_file.name} 的Ground Truth失败: {e}")

        logger.info(f"完成 {len(results)}/{sample_count} 个PDF的Ground Truth生成")
        return results

    def batch_generate(
        self, pdf_paths: List[str], output_dir: str
    ) -> List[Dict[str, Any]]:
        """
        批量生成Ground Truth

        Args:
            pdf_paths: PDF文件路径列表
            output_dir: 输出目录

        Returns:
            Ground Truth列表
        """
        results = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for pdf_path in pdf_paths:
            try:
                result = self.generate_for_pdf(pdf_path, str(output_path))
                results.append(result)
                logger.info(f"完成: {Path(pdf_path).name}")
            except Exception as e:
                logger.error(f"处理 {pdf_path} 失败: {e}")

        return results


if __name__ == "__main__":
    # 测试代码
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    generator = GroundTruthGenerator()

    # 测试单个文件
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        output_dir = "./data/evaluation/ground_truth"
        result = generator.generate_for_pdf(pdf_path, output_dir)
        print(f"生成完成: {result['pdf_file']}, 共 {result['total_pages']} 页")
    else:
        print("用法: python ground_truth_generator.py <pdf文件路径>")
