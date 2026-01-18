"""
指标计算模块
提供各种评估指标的计算工具
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextMetrics:
    """文本评估指标"""

    char_accuracy: float
    word_accuracy: float
    levenshtein_distance: int
    normalized_distance: float
    char_error_rate: float
    word_error_rate: float


@dataclass
class StructureMetrics:
    """结构评估指标"""

    table_accuracy: float
    table_detection_rate: float
    header_accuracy: float
    header_detection_rate: float
    list_accuracy: float
    list_detection_rate: float
    formula_accuracy: float
    formula_detection_rate: float


@dataclass
class PerformanceMetrics:
    """性能指标"""

    processing_time_ms: float
    memory_usage_mb: float
    throughput_pages_per_sec: float


class MetricsCalculator:
    """
    指标计算器
    提供统一的指标计算接口
    """

    @staticmethod
    def calculate_text_accuracy_metrics(text_results: List[Any]) -> TextMetrics:
        """
        计算文本准确率指标

        Args:
            text_results: 文本评估结果列表（TextAccuracyResult对象或字典）

        Returns:
            TextMetrics对象
        """
        if not text_results:
            return TextMetrics(
                char_accuracy=0.0,
                word_accuracy=0.0,
                levenshtein_distance=0,
                normalized_distance=0.0,
                char_error_rate=0.0,
                word_error_rate=0.0,
            )

        # 聚合指标（支持TextAccuracyResult对象和字典）
        total_char_acc = 0
        total_word_acc = 0
        total_lev_dist = 0
        total_norm_dist = 0

        for r in text_results:
            if hasattr(r, "char_accuracy"):
                # TextAccuracyResult对象
                total_char_acc += r.char_accuracy
                total_word_acc += r.word_accuracy
                total_lev_dist += r.levenshtein_distance
                total_norm_dist += r.normalized_distance
            else:
                # 字典
                total_char_acc += r.get("char_accuracy", 0.0)
                total_word_acc += r.get("word_accuracy", 0.0)
                total_lev_dist += r.get("levenshtein_distance", 0)
                total_norm_dist += r.get("normalized_distance", 0.0)

        count = len(text_results)

        char_accuracy = total_char_acc / count
        word_accuracy = total_word_acc / count
        avg_lev_distance = total_lev_dist / count
        avg_norm_distance = total_norm_dist / count

        char_error_rate = 1.0 - char_accuracy
        word_error_rate = 1.0 - word_accuracy

        return TextMetrics(
            char_accuracy=char_accuracy,
            word_accuracy=word_accuracy,
            levenshtein_distance=int(avg_lev_distance),
            normalized_distance=avg_norm_distance,
            char_error_rate=char_error_rate,
            word_error_rate=word_error_rate,
        )

    @staticmethod
    def calculate_structure_metrics(
        structure_results: List[Dict[str, Any]],
    ) -> StructureMetrics:
        """
        计算结构识别指标

        Args:
            structure_results: 结构评估结果列表

        Returns:
            StructureMetrics对象
        """
        if not structure_results:
            return StructureMetrics(
                table_accuracy=0.0,
                table_detection_rate=0.0,
                header_accuracy=0.0,
                header_detection_rate=0.0,
                list_accuracy=0.0,
                list_detection_rate=0.0,
                formula_accuracy=0.0,
                formula_detection_rate=0.0,
            )

        # 聚合各类结构指标
        table_results = []
        header_results = []
        list_results = []
        formula_results = []

        for result in structure_results:
            if "table" in result:
                table_results.append(result["table"])
            if "header" in result:
                header_results.append(result["header"])
            if "list" in result:
                list_results.append(result["list"])
            if "formula" in result:
                formula_results.append(result["formula"])

        # 计算各类结构的平均指标
        table_acc = MetricsCalculator._avg_metric(table_results, "accuracy")
        table_det = MetricsCalculator._avg_metric(table_results, "detection_rate")

        header_acc = MetricsCalculator._avg_metric(header_results, "accuracy")
        header_det = MetricsCalculator._avg_metric(header_results, "detection_rate")

        list_acc = MetricsCalculator._avg_metric(list_results, "accuracy")
        list_det = MetricsCalculator._avg_metric(list_results, "detection_rate")

        formula_acc = MetricsCalculator._avg_metric(formula_results, "accuracy")
        formula_det = MetricsCalculator._avg_metric(formula_results, "detection_rate")

        return StructureMetrics(
            table_accuracy=table_acc,
            table_detection_rate=table_det,
            header_accuracy=header_acc,
            header_detection_rate=header_det,
            list_accuracy=list_acc,
            list_detection_rate=list_det,
            formula_accuracy=formula_acc,
            formula_detection_rate=formula_det,
        )

    @staticmethod
    def calculate_performance_metrics(
        processing_times: List[float], page_counts: List[int]
    ) -> PerformanceMetrics:
        """
        计算性能指标

        Args:
            processing_times: 处理时间列表（毫秒）
            page_counts: 页面数量列表

        Returns:
            PerformanceMetrics对象
        """
        if not processing_times:
            return PerformanceMetrics(
                processing_time_ms=0.0,
                memory_usage_mb=0.0,
                throughput_pages_per_sec=0.0,
            )

        # 平均处理时间
        avg_time = sum(processing_times) / len(processing_times)

        # 计算吞吐量（页面/秒）
        total_pages = sum(page_counts)
        total_time_sec = sum(processing_times) / 1000  # 转换为秒
        throughput = total_pages / total_time_sec if total_time_sec > 0 else 0.0

        return PerformanceMetrics(
            processing_time_ms=avg_time,
            memory_usage_mb=0.0,  # 需要实际测量
            throughput_pages_per_sec=throughput,
        )

    @staticmethod
    def _avg_metric(results: List[Dict[str, Any]], metric_name: str) -> float:
        """计算指定指标的平均值"""
        if not results:
            return 0.0

        values = [r.get(metric_name, 0.0) for r in results]
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def calculate_aggregate_metrics(all_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算聚合指标

        Args:
            all_results: 所有评估结果

        Returns:
            聚合指标字典
        """
        metrics = {}

        # 文本指标
        if "text" in all_results:
            text_metrics = MetricsCalculator.calculate_text_accuracy_metrics(
                all_results["text"]
            )
            metrics["text"] = {
                "char_accuracy": text_metrics.char_accuracy,
                "word_accuracy": text_metrics.word_accuracy,
                "char_error_rate": text_metrics.char_error_rate,
                "word_error_rate": text_metrics.word_error_rate,
                "levenshtein_distance": text_metrics.levenshtein_distance,
            }

        # 结构指标
        if "structure" in all_results:
            structure_metrics = MetricsCalculator.calculate_structure_metrics(
                all_results["structure"]
            )
            metrics["structure"] = {
                "table_accuracy": structure_metrics.table_accuracy,
                "table_detection_rate": structure_metrics.table_detection_rate,
                "header_accuracy": structure_metrics.header_accuracy,
                "header_detection_rate": structure_metrics.header_detection_rate,
                "list_accuracy": structure_metrics.list_accuracy,
                "list_detection_rate": structure_metrics.list_detection_rate,
                "formula_accuracy": structure_metrics.formula_accuracy,
                "formula_detection_rate": structure_metrics.formula_detection_rate,
            }

        # 性能指标
        if "performance" in all_results:
            perf_metrics = MetricsCalculator.calculate_performance_metrics(
                all_results["performance"]["processing_times"],
                all_results["performance"]["page_counts"],
            )
            metrics["performance"] = {
                "avg_processing_time_ms": perf_metrics.processing_time_ms,
                "throughput_pages_per_sec": perf_metrics.throughput_pages_per_sec,
            }

        # 总体指标
        if "text" in metrics and "structure" in metrics:
            # 从TextMetrics对象或字典中提取数据
            text_data = metrics["text"]
            if hasattr(text_data, "char_accuracy"):
                # TextMetrics对象
                char_acc = text_data.char_accuracy
                word_acc = text_data.word_accuracy
                norm_dist = text_data.normalized_distance
            else:
                # 字典
                char_acc = text_data.get("char_accuracy", 0.0)
                word_acc = text_data.get("word_accuracy", 0.0)
                norm_dist = text_data.get("normalized_distance", 0.0)

            # 从StructureMetrics对象或字典中提取数据
            structure_data = metrics["structure"]
            if hasattr(structure_data, "table_accuracy"):
                # StructureMetrics对象
                table_acc = structure_data.table_accuracy
                header_acc = structure_data.header_accuracy
                list_acc = structure_data.list_accuracy
                formula_acc = structure_data.formula_accuracy
            else:
                # 字典
                table_acc = structure_data.get("table_accuracy", 0.0)
                header_acc = structure_data.get("header_accuracy", 0.0)
                list_acc = structure_data.get("list_accuracy", 0.0)
                formula_acc = structure_data.get("formula_accuracy", 0.0)

            # 综合得分（加权平均）
            text_score = char_acc * 0.4 + word_acc * 0.4 + (1 - norm_dist) * 0.2

            structure_score = (
                table_acc * 0.3 + header_acc * 0.3 + list_acc * 0.3 + formula_acc * 0.1
            )

            overall_score = text_score * 0.7 + structure_score * 0.3

            metrics["overall"] = {
                "score": overall_score,
                "text_score": text_score,
                "structure_score": structure_score,
                "pass_threshold": 0.8,
                "passed": overall_score >= 0.8,
            }

        return metrics


if __name__ == "__main__":
    # 测试代码
    # 文本指标测试
    text_results = [
        {
            "char_accuracy": 0.95,
            "word_accuracy": 0.92,
            "levenshtein_distance": 10,
            "normalized_distance": 0.05,
        },
        {
            "char_accuracy": 0.98,
            "word_accuracy": 0.96,
            "levenshtein_distance": 5,
            "normalized_distance": 0.02,
        },
    ]

    text_metrics = MetricsCalculator.calculate_text_accuracy_metrics(text_results)
    print(f"字符准确率: {text_metrics.char_accuracy:.2%}")
    print(f"词语准确率: {text_metrics.word_accuracy:.2%}")

    # 结构指标测试
    structure_results = [
        {
            "table": {"accuracy": 0.85, "detection_rate": 0.90},
            "header": {"accuracy": 0.90, "detection_rate": 0.95},
        },
        {
            "table": {"accuracy": 0.88, "detection_rate": 0.92},
            "header": {"accuracy": 0.92, "detection_rate": 0.96},
        },
    ]

    structure_metrics = MetricsCalculator.calculate_structure_metrics(structure_results)
    print(f"表格准确率: {structure_metrics.table_accuracy:.2%}")
    print(f"标题准确率: {structure_metrics.header_accuracy:.2%}")
