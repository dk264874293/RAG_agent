"""
结构评估器
评估表格、标题、列表等结构的准确性
"""

import logging
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StructureType(Enum):
    """结构类型枚举"""

    TABLE = "table"
    HEADER = "header"
    LIST = "list"
    FORMULA = "formula"


@dataclass
class StructureEvaluationResult:
    """结构评估结果"""

    detection_rate: float
    accuracy: float
    total_count: int
    detected_count: int
    correct_count: int
    detailed_stats: Dict[str, Any]


class StructureEvaluator:
    """
    结构评估器
    评估表格、标题、列表等结构的识别准确率
    """

    def __init__(self):
        # 标题模式
        self.header_patterns = [
            r"^第[一二三四五六七八九十百]+[章节条款]",  # 第一章、第二节等
            r"^\d+[\.\s]",  # 1. 2. 等数字开头
            r"^[一二三四五六七八九十]+、",  # 一、二、等中文数字
            r"^[A-Z][A-Z\s]+$",  # 全大写单词
            r"^[一二三四五六七八九十]+[\.、]\s*",  # 一. 二、等
        ]

        # 列表模式
        self.list_patterns = [
            r"^[•\-\*·]\s+",  # 无序列表符号
            r"^[○□■]\s+",  # 其他无序符号
            r"^\d+[\.、\)]\s+",  # 有序数字
            r"^[a-z][\.\)]\s+",  # 小写字母
        ]

        # 表格模式（简化）
        self.table_patterns = [
            r"\|.*\|",  # 包含管道符
            r"(\s{2,}){3,}",  # 多列（多个空格）
            r"^\s*\S+(\s{2,}\S+){2,}",  # 多行多列
        ]

    def evaluate(
        self, predicted_content: str, ground_truth: Dict[str, Any]
    ) -> Dict[StructureType, StructureEvaluationResult]:
        """
        评估所有结构类型的准确率

        Args:
            predicted_content: 预测的文本内容
            ground_truth: 标准答案（包含structures字段）

        Returns:
            每种结构类型的评估结果
        """
        results = {}

        # 评估表格
        if "tables" in ground_truth:
            results[StructureType.TABLE] = self._evaluate_tables(
                predicted_content, ground_truth["tables"]
            )

        # 评估标题
        if "headers" in ground_truth:
            results[StructureType.HEADER] = self._evaluate_headers(
                predicted_content, ground_truth["headers"]
            )

        # 评估列表
        if "lists" in ground_truth:
            results[StructureType.LIST] = self._evaluate_lists(
                predicted_content, ground_truth["lists"]
            )

        # 评估公式
        if "formulas" in ground_truth:
            results[StructureType.FORMULA] = self._evaluate_formulas(
                predicted_content, ground_truth["formulas"]
            )

        return results

    def _evaluate_tables(
        self, predicted: str, gt_tables: List[Dict]
    ) -> StructureEvaluationResult:
        """
        评估表格识别准确率
        """
        if not gt_tables:
            return StructureEvaluationResult(
                detection_rate=1.0,
                accuracy=1.0,
                total_count=0,
                detected_count=0,
                correct_count=0,
                detailed_stats={},
            )

        total = len(gt_tables)
        detected = 0
        correct = 0
        details = []

        # 从预测内容中提取表格
        pred_tables = self._extract_tables(predicted)
        detected = len(pred_tables)

        # 匹配表格
        for gt_table in gt_tables:
            best_match = None
            best_similarity = 0

            for pred_table in pred_tables:
                similarity = self._calculate_similarity(
                    gt_table["content"], pred_table["content"]
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pred_table

            if best_similarity > 0.5:  # 相似度阈值
                correct += 1

            details.append(
                {
                    "ground_truth": gt_table,
                    "matched": best_similarity > 0.5,
                    "similarity": best_similarity,
                }
            )

        detection_rate = detected / total if total > 0 else 1.0
        accuracy = correct / total if total > 0 else 1.0

        return StructureEvaluationResult(
            detection_rate=detection_rate,
            accuracy=accuracy,
            total_count=total,
            detected_count=detected,
            correct_count=correct,
            detailed_stats={
                "tables": details,
                "precision": correct / detected if detected > 0 else 0,
                "recall": correct / total if total > 0 else 0,
            },
        )

    def _evaluate_headers(
        self, predicted: str, gt_headers: List[Dict]
    ) -> StructureEvaluationResult:
        """
        评估标题识别准确率
        """
        if not gt_headers:
            return StructureEvaluationResult(
                detection_rate=1.0,
                accuracy=1.0,
                total_count=0,
                detected_count=0,
                correct_count=0,
                detailed_stats={},
            )

        total = len(gt_headers)
        detected = 0
        correct = 0
        details = []

        # 从预测内容中提取标题
        pred_headers = self._extract_headers(predicted)
        detected = len(pred_headers)

        # 匹配标题
        for gt_header in gt_headers:
            best_match = None
            best_similarity = 0

            for pred_header in pred_headers:
                similarity = self._calculate_similarity(
                    gt_header["text"], pred_header["text"]
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pred_header

            # 检查层级是否一致
            level_match = best_match and best_match.get("level", 0) == gt_header.get(
                "level", 0
            )

            if best_similarity > 0.7 and level_match:
                correct += 1

            details.append(
                {
                    "ground_truth": gt_header,
                    "matched": best_similarity > 0.7,
                    "level_match": level_match,
                    "similarity": best_similarity,
                }
            )

        detection_rate = detected / total if total > 0 else 1.0
        accuracy = correct / total if total > 0 else 1.0

        return StructureEvaluationResult(
            detection_rate=detection_rate,
            accuracy=accuracy,
            total_count=total,
            detected_count=detected,
            correct_count=correct,
            detailed_stats={
                "headers": details,
                "precision": correct / detected if detected > 0 else 0,
                "recall": correct / total if total > 0 else 0,
            },
        )

    def _evaluate_lists(
        self, predicted: str, gt_lists: List[Dict]
    ) -> StructureEvaluationResult:
        """
        评估列表识别准确率
        """
        if not gt_lists:
            return StructureEvaluationResult(
                detection_rate=1.0,
                accuracy=1.0,
                total_count=0,
                detected_count=0,
                correct_count=0,
                detailed_stats={},
            )

        total = len(gt_lists)
        detected = 0
        correct = 0
        details = []

        # 从预测内容中提取列表项
        pred_lists = self._extract_lists(predicted)
        detected = len(pred_lists)

        # 匹配列表
        for gt_list in gt_lists:
            best_match = None
            best_similarity = 0

            for pred_list in pred_lists:
                similarity = self._calculate_similarity(
                    gt_list["text"], pred_list["text"]
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pred_list

            # 检查列表类型是否一致
            type_match = best_match and best_match.get("type", "") == gt_list.get(
                "type", ""
            )

            if best_similarity > 0.6 and type_match:
                correct += 1

            details.append(
                {
                    "ground_truth": gt_list,
                    "matched": best_similarity > 0.6,
                    "type_match": type_match,
                    "similarity": best_similarity,
                }
            )

        detection_rate = detected / total if total > 0 else 1.0
        accuracy = correct / total if total > 0 else 1.0

        return StructureEvaluationResult(
            detection_rate=detection_rate,
            accuracy=accuracy,
            total_count=total,
            detected_count=detected,
            correct_count=correct,
            detailed_stats={
                "lists": details,
                "precision": correct / detected if detected > 0 else 0,
                "recall": correct / total if total > 0 else 0,
            },
        )

    def _evaluate_formulas(
        self, predicted: str, gt_formulas: List[Dict]
    ) -> StructureEvaluationResult:
        """
        评估公式识别准确率
        """
        if not gt_formulas:
            return StructureEvaluationResult(
                detection_rate=1.0,
                accuracy=1.0,
                total_count=0,
                detected_count=0,
                correct_count=0,
                detailed_stats={},
            )

        total = len(gt_formulas)
        detected = 0
        correct = 0
        details = []

        # 从预测内容中提取公式
        pred_formulas = self._extract_formulas(predicted)
        detected = len(pred_formulas)

        # 匹配公式
        for gt_formula in gt_formulas:
            best_match = None
            best_similarity = 0

            for pred_formula in pred_formulas:
                similarity = self._calculate_similarity(
                    gt_formula["content"], pred_formula["content"]
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pred_formula

            if best_similarity > 0.5:
                correct += 1

            details.append(
                {
                    "ground_truth": gt_formula,
                    "matched": best_similarity > 0.5,
                    "similarity": best_similarity,
                }
            )

        detection_rate = detected / total if total > 0 else 1.0
        accuracy = correct / total if total > 0 else 1.0

        return StructureEvaluationResult(
            detection_rate=detection_rate,
            accuracy=accuracy,
            total_count=total,
            detected_count=detected,
            correct_count=correct,
            detailed_stats={
                "formulas": details,
                "precision": correct / detected if detected > 0 else 0,
                "recall": correct / total if total > 0 else 0,
            },
        )

    def _extract_tables(self, content: str) -> List[Dict]:
        """提取表格"""
        tables = []
        lines = content.split("\n")
        current_table = []
        in_table = False

        for line in lines:
            is_table_line = any(
                re.search(pattern, line) for pattern in self.table_patterns
            )

            if is_table_line:
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(line)
            elif in_table:
                # 表格结束
                if current_table:
                    table_content = "\n".join(current_table)
                    tables.append(
                        {
                            "id": len(tables) + 1,
                            "content": table_content,
                            "rows": len(current_table),
                        }
                    )
                in_table = False
                current_table = []

        return tables

    def _extract_headers(self, content: str) -> List[Dict]:
        """提取标题"""
        headers = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检查是否匹配标题模式
            for pattern in self.header_patterns:
                if re.match(pattern, line):
                    # 推断层级
                    level = 1
                    if re.match(r"^第[一二三四五六七八九十百]+[章节条款]", line):
                        level = 1
                    elif re.match(r"^\d+[\.、]", line):
                        level = 2
                    elif re.match(r"^[一二三四五六七八九十]+、", line):
                        level = 2

                    headers.append({"level": level, "text": line, "line_num": i})
                    break

        return headers

    def _extract_lists(self, content: str) -> List[Dict]:
        """提取列表"""
        lists = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否匹配列表模式
            for pattern in self.list_patterns:
                match = re.match(pattern, line)
                if match:
                    # 确定列表类型
                    list_type = (
                        "unordered"
                        if match.group(0)[0] in ["•", "-", "*", "·", "○", "□", "■"]
                        else "ordered"
                    )

                    lists.append(
                        {"type": list_type, "text": line, "marker": match.group(0)}
                    )
                    break

        return lists

    def _extract_formulas(self, content: str) -> List[Dict]:
        """提取公式"""
        formulas = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测公式特征
            formula_markers = [
                "=",
                "≈",
                "≤",
                "≥",
                "±",
                "×",
                "÷",
                "∑",
                "∫",
                "∂",
                "√",
                "∞",
            ]
            marker_count = sum(1 for marker in formula_markers if marker in line)

            # 如果包含多个公式标记，可能是公式
            if marker_count >= 1:
                formulas.append(
                    {"id": len(formulas) + 1, "content": line, "type": "simple"}
                )

        return formulas

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算文本相似度（Jaccard + 编辑距离混合）
        """
        # Jaccard相似度
        set1 = set(text1.split())
        set2 = set(text2.split())

        if not set1 or not set2:
            return 1.0 if text1 == text2 else 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union > 0 else 0

        # 简单的字符相似度
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 1.0

        char_matches = sum(1 for c1, c2 in zip(text1, text2) if c1 == c2)
        char_similarity = char_matches / max_len

        # 混合相似度
        return jaccard * 0.7 + char_similarity * 0.3


if __name__ == "__main__":
    # 测试代码
    evaluator = StructureEvaluator()

    # 测试用例
    predicted = """
    第一章 测试内容
    1. 第一项测试
    2. 第二项测试
    | 列1 | 列2 |
    |---|---|
    | 数据1 | 数据2 |
    公式: A = B + C
    """

    gt = {
        "headers": [{"level": 1, "text": "第一章 测试内容"}],
        "lists": [
            {"type": "ordered", "text": "1. 第一项测试"},
            {"type": "ordered", "text": "2. 第二项测试"},
        ],
        "tables": [{"id": 1, "content": "| 列1 | 列2 |\n|---|---|\n| 数据1 | 数据2 |"}],
        "formulas": [{"id": 1, "content": "公式: A = B + C"}],
    }

    results = evaluator.evaluate(predicted, gt)
    for struct_type, result in results.items():
        print(
            f"{struct_type.value}: 准确率={result.accuracy:.2%}, 检测率={result.detection_rate:.2%}"
        )
