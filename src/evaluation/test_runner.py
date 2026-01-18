"""
测试运行器
协调整个评估流程
"""

import json
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import asdict, is_dataclass

from .ground_truth_generator import GroundTruthGenerator
from .evaluators.text_accuracy import TextAccuracyEvaluator
from .evaluators.structure_evaluator import StructureEvaluator
from .evaluators.formula_evaluator import FormulaEvaluator
from .metrics import MetricsCalculator
from .report_generator import HTMLReportGenerator
from ..extractor.pdf_extractor import EnhancedPdfExtractor
from ..pipeline.document_processor import DocumentProcessingPipeline

logger = logging.getLogger(__name__)


class EvaluationTestRunner:
    """
    评估测试运行器
    协调整个评估流程：生成GT、执行OCR、评估、生成报告
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化测试运行器

        Args:
            config: 评估配置
        """
        self.config = config or {}

        # 初始化组件
        self.gt_generator = GroundTruthGenerator(config)
        self.text_evaluator = TextAccuracyEvaluator()
        self.structure_evaluator = StructureEvaluator()
        self.formula_evaluator = FormulaEvaluator()
        self.metrics_calculator = MetricsCalculator()
        self.report_generator = HTMLReportGenerator()

        # 配置
        self.pdf_dir = self.config.get("pdf_dir", "./data/evaluation/benchmarks/pdfs")
        self.output_dir = self.config.get("output_dir", "./data/evaluation")
        self.ground_truth_dir = f"{self.output_dir}/ground_truth"
        self.results_dir = f"{self.output_dir}/results"
        self.reports_dir = f"{self.output_dir}/reports/html"

        # 创建输出目录
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.ground_truth_dir).mkdir(parents=True, exist_ok=True)
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)
        Path(self.reports_dir).mkdir(parents=True, exist_ok=True)

    def _convert_structure_results(self, structure_results):
        """将StructureType枚举键转换为字符串键，dataclass值转换为字典"""
        if isinstance(structure_results, dict):
            converted = {}
            for key, value in structure_results.items():
                # 枚举键 -> 字符串（使用.value属性）
                if hasattr(key, "value"):
                    str_key = key.value  # 如：StructureType.TABLE.value → "table"
                else:
                    str_key = str(key)

                # dataclass值 -> 字典
                if is_dataclass(value):
                    converted[str_key] = asdict(value)
                else:
                    converted[str_key] = value
            return converted
        return structure_results

    async def run_evaluation(
        self, variant: str = "ocr_enhanced", sample_percent: float = 0.1
    ) -> Dict[str, Any]:
        """
        运行完整评估流程

        Args:
            variant: 评估变体（control/ocr_basic/ocr_enhanced）
            sample_percent: 抽样百分比

        Returns:
            完整的评估结果
        """
        logger.info("=" * 60)
        logger.info("开始OCR准确性评估")
        logger.info(f"变体: {variant}, 抽样: {sample_percent * 100}%")
        logger.info("=" * 60)

        # 阶段1: 生成Ground Truth
        logger.info("\n[1/4] 生成Ground Truth...")
        gt_results = await self.gt_generator.generate_for_directory(
            self.pdf_dir, self.ground_truth_dir, sample_percent
        )

        if not gt_results:
            logger.error("没有生成Ground Truth，评估终止")
            return {"error": "No ground truth generated"}

        # 阶段2: 执行OCR提取
        logger.info(f"\n[2/4] 执行OCR提取（变体: {variant}）...")
        ocr_results = await self._run_ocr_extraction(gt_results, variant)

        # 阶段3: 执行评估
        logger.info("\n[3/4] 执行多维度评估...")
        evaluation_results = await self._run_evaluation(gt_results, ocr_results)

        # 阶段4: 生成报告
        logger.info("\n[4/4] 生成评估报告...")
        final_results = await self._generate_report(evaluation_results, variant)

        logger.info("=" * 60)
        logger.info("评估完成！")
        logger.info(f"报告路径: {final_results['report_path']}")
        logger.info(f"综合得分: {final_results['metrics']['overall']['score']:.2%}")
        logger.info("=" * 60)

        # 合并evaluation_results中的file_results到返回值
        final_results["file_results"] = evaluation_results.get("file_results", [])
        return final_results

    async def _run_ocr_extraction(
        self, gt_results: List[Dict], variant: str
    ) -> List[Dict]:
        """
        执行OCR提取

        Args:
            gt_results: Ground Truth结果列表
            variant: OCR变体

        Returns:
            OCR提取结果列表
        """
        ocr_results = []

        # 配置OCR变体
        ocr_config = self.config.copy()
        ocr_config.update(
            {
                "enable_pdf_ocr": True,
                "enable_ab_testing": False,
                "experiment_groups": {variant: 1.0},  # 100%使用指定变体
            }
        )

        for gt_data in gt_results:
            pdf_path = gt_data["pdf_path"]
            pdf_name = gt_data["pdf_file"]

            logger.info(f"处理PDF: {pdf_name}")

            start_time = time.time()

            try:
                # 使用EnhancedPdfExtractor
                extractor = EnhancedPdfExtractor(
                    file_path=pdf_path,
                    tenant_id="evaluation",
                    user_id="test",
                    config=ocr_config,
                )

                documents = extractor.extract()
                processing_time = (time.time() - start_time) * 1000  # 毫秒

                # 构建OCR结果
                ocr_result = {
                    "pdf_file": pdf_name,
                    "pdf_path": pdf_path,
                    "total_pages": len(documents),
                    "processing_time_ms": processing_time,
                    "pages": [],
                    "ocr_stats": extractor.get_ocr_stats(),
                }

                # 处理每一页
                for i, doc in enumerate(documents):
                    page_data = {
                        "page_num": i,
                        "predicted": doc.page_content,
                        "metadata": doc.metadata,
                    }
                    ocr_result["pages"].append(page_data)

                ocr_results.append(ocr_result)
                logger.info(f"✓ 完成: {pdf_name}, 耗时: {processing_time:.1f}ms")

            except Exception as e:
                logger.error(f"✗ 失败: {pdf_name}, 错误: {e}")
                ocr_results.append(
                    {"pdf_file": pdf_name, "pdf_path": pdf_path, "error": str(e)}
                )

        return ocr_results

    async def _run_evaluation(
        self, gt_results: List[Dict], ocr_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        执行多维度评估

        Args:
            gt_results: Ground Truth结果
            ocr_results: OCR结果

        Returns:
            评估结果
        """
        file_results = []
        all_text_results = []
        all_structure_results = []
        all_performance_data = []

        # 匹配GT和OCR结果
        for gt_data in gt_results:
            pdf_name = gt_data["pdf_file"]
            ocr_data = next((r for r in ocr_results if r["pdf_file"] == pdf_name), None)

            if not ocr_data or "error" in ocr_data:
                logger.warning(f"跳过 {pdf_name}: OCR处理失败")
                continue

            # 评估每一页
            file_result = {
                "pdf_file": pdf_name,
                "pdf_path": gt_data["pdf_path"],
                "pages": [],
                "text_accuracy": {},
                "structure_evaluation": {},
            }

            # 按页评估
            for gt_page in gt_data["pages"]:
                page_num = gt_page["page_num"]
                ocr_page = next(
                    (p for p in ocr_data["pages"] if p["page_num"] == page_num), None
                )

                if not ocr_page:
                    continue

                # 文本准确率评估
                predicted_text = ocr_page["predicted"]
                gt_text = gt_page["content"]
                gt_structures = gt_page["structures"]

                text_result = self.text_evaluator.evaluate(predicted_text, gt_text)
                structure_results = self.structure_evaluator.evaluate(
                    predicted_text, gt_structures
                )

                # 转换为字典以便JSON序列化
                text_result_dict = (
                    asdict(text_result) if is_dataclass(text_result) else text_result
                )
                structure_results_dict = self._convert_structure_results(
                    structure_results
                )

                page_data = {
                    "page_num": page_num,
                    "predicted": predicted_text,
                    "ground_truth": gt_text,
                    "text_accuracy": text_result_dict,
                    "structure_evaluation": structure_results_dict,
                }
                file_result["pages"].append(page_data)

                # 收集用于聚合的数据
                all_text_results.append(text_result)
                all_structure_results.append(
                    self._convert_structure_results(structure_results)
                )

            # 聚合文件级指标
            if file_result["pages"]:
                # 文本指标（平均）
                text_metrics = self.metrics_calculator.calculate_text_accuracy_metrics(
                    [p["text_accuracy"] for p in file_result["pages"]]
                )
                file_result["text_accuracy"] = (
                    asdict(text_metrics) if is_dataclass(text_metrics) else text_metrics
                )

                # 结构指标（平均）
                structure_metrics = self.metrics_calculator.calculate_structure_metrics(
                    [p["structure_evaluation"] for p in file_result["pages"]]
                )
                file_result["structure_evaluation"] = (
                    asdict(structure_metrics)
                    if is_dataclass(structure_metrics)
                    else structure_metrics
                )

                # 性能数据
                all_performance_data.append(
                    {
                        "processing_time": ocr_data["processing_time_ms"],
                        "page_count": ocr_data["total_pages"],
                    }
                )

                file_results.append(file_result)

        # 计算整体指标
        overall_metrics = {
            "text": all_text_results,
            "structure": all_structure_results,
            "performance": {
                "processing_times": [
                    d["processing_time"] for d in all_performance_data
                ],
                "page_counts": [d["page_count"] for d in all_performance_data],
            },
        }

        metrics = self.metrics_calculator.calculate_aggregate_metrics(overall_metrics)

        return {
            "variant": self.config.get("variant", "ocr_enhanced"),
            "timestamp": datetime.now().isoformat(),
            "file_results": file_results,
            "metrics": metrics,
            "config": self.config,
        }

    async def _generate_report(
        self, evaluation_results: Dict[str, Any], variant: str
    ) -> Dict[str, Any]:
        """
        生成报告

        Args:
            evaluation_results: 评估结果
            variant: 变体名称

        Returns:
            包含报告路径的字典
        """
        # 添加变体信息
        evaluation_results["variant"] = variant

        # 生成HTML报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = (
            Path(self.reports_dir) / f"ocr_evaluation_{variant}_{timestamp}.html"
        )

        self.report_generator.generate(evaluation_results, str(report_path))

        # 保存JSON结果
        json_path = (
            Path(self.results_dir) / f"ocr_evaluation_{variant}_{timestamp}.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_results, f, indent=2, ensure_ascii=False)

        return {
            "report_path": str(report_path),
            "json_path": str(json_path),
            "metrics": evaluation_results["metrics"],
            "variant": variant,
        }

    def run_batch_evaluation(
        self, variants: List[str] = None, sample_percent: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        批量运行多个变体的评估

        Args:
            variants: 变体列表
            sample_percent: 抽样百分比

        Returns:
            所有变体的评估结果
        """
        if variants is None:
            variants = ["ocr_enhanced"]

        results = []

        for variant in variants:
            logger.info(f"\n开始评估变体: {variant}")
            try:
                result = asyncio.run(self.run_evaluation(variant, sample_percent))
                results.append(result)
            except Exception as e:
                logger.error(f"评估变体 {variant} 失败: {e}")

        # 生成对比报告
        if len(results) > 1:
            self._generate_comparison_report(results)

        return results

    def _generate_comparison_report(self, results: List[Dict[str, Any]]):
        """生成变体对比报告"""
        logger.info("生成变体对比报告...")

        comparison_data = {
            "timestamp": datetime.now().isoformat(),
            "variants": [],
            "comparison": {},
        }

        for result in results:
            variant = result["variant"]
            metrics = result["metrics"]

            comparison_data["variants"].append(
                {
                    "name": variant,
                    "overall_score": metrics.get("overall", {}).get("score", 0.0),
                    "char_accuracy": metrics.get("text", {}).get("char_accuracy", 0.0),
                    "word_accuracy": metrics.get("text", {}).get("word_accuracy", 0.0),
                    "processing_time": metrics.get("performance", {}).get(
                        "avg_processing_time_ms", 0.0
                    ),
                }
            )

        # 找出最佳变体
        best_variant = max(
            comparison_data["variants"], key=lambda x: x["overall_score"]
        )
        comparison_data["best_variant"] = best_variant

        # 保存对比报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_path = (
            Path(self.results_dir) / f"variant_comparison_{timestamp}.json"
        )
        with open(comparison_path, "w", encoding="utf-8") as f:
            json.dump(comparison_data, f, indent=2, ensure_ascii=False)

        logger.info(f"对比报告已保存: {comparison_path}")


if __name__ == "__main__":
    # 测试代码
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = {
        "pdf_dir": "./data/evaluation/benchmarks/pdfs",
        "output_dir": "./data/evaluation",
        "variant": "ocr_enhanced",
    }

    runner = EvaluationTestRunner(config)

    # 运行评估
    results = asyncio.run(
        runner.run_evaluation(variant="ocr_enhanced", sample_percent=0.1)
    )

    print(f"评估完成！综合得分: {results['metrics']['overall']['score']:.2%}")
