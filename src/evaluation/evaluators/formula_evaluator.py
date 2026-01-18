"""
公式评估器
评估数学公式识别的准确性
"""

import logging
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormulaEvaluationResult:
    """公式评估结果"""

    detection_rate: float
    latex_accuracy: float
    semantic_accuracy: float
    total_count: int
    detected_count: int
    correct_count: int
    detailed_stats: Dict[str, Any]


class FormulaEvaluator:
    """
    公式评估器
    评估数学公式的检测和识别准确率
    """

    def __init__(self):
        # 公式模式（简化）
        self.formula_patterns = [
            # 数学符号
            r"[≈≤≥±×÷∑∫∂√∞]",
            # 希腊字母
            r"[αβγδεζηθικλμνξπρστυφχψω]",
            r"[ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ]",
            # 数学运算符
            r"[a-z]+\s*[=<>≠≤≥]+\s*[a-z0-9]+",
            # 分数
            r"[a-z0-9]+\s*/\s*[a-z0-9]+",
            # 幂次
            r"[a-z]\^[0-9]+",
            # 下标
            r"[a-z]_[a-z0-9]+",
            # 根号
            r"√[a-z0-9]+",
        ]

    def evaluate(
        self, predicted_content: str, ground_truth: Dict[str, Any]
    ) -> FormulaEvaluationResult:
        """
        评估公式识别准确率

        Args:
            predicted_content: 预测的文本内容
            ground_truth: 标准答案（包含formulas字段）

        Returns:
            FormulaEvaluationResult对象
        """
        if "formulas" not in ground_truth:
            return FormulaEvaluationResult(
                detection_rate=1.0,
                latex_accuracy=1.0,
                semantic_accuracy=1.0,
                total_count=0,
                detected_count=0,
                correct_count=0,
                detailed_stats={},
            )

        gt_formulas = ground_truth["formulas"]
        total = len(gt_formulas)

        # 从预测内容中提取公式
        pred_formulas = self._extract_formulas(predicted_content)
        detected = len(pred_formulas)

        # 匹配公式
        correct = 0
        details = []
        for gt_formula in gt_formulas:
            best_match = None
            best_similarity = 0

            for pred_formula in pred_formulas:
                similarity = self._calculate_formula_similarity(
                    gt_formula["content"], pred_formula["content"]
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pred_formula

            if best_similarity > 0.7:
                correct += 1

            details.append(
                {
                    "ground_truth": gt_formula,
                    "matched": best_similarity > 0.7,
                    "similarity": best_similarity,
                    "prediction": best_match,
                }
            )

        detection_rate = detected / total if total > 0 else 1.0
        accuracy = correct / total if total > 0 else 1.0

        # LaTeX准确性（简化：基于特殊字符识别）
        latex_accuracy = self._evaluate_latex_accuracy(pred_formulas, gt_formulas)

        # 语义准确性（简化：基于公式结构）
        semantic_accuracy = self._evaluate_semantic_accuracy(pred_formulas, gt_formulas)

        return FormulaEvaluationResult(
            detection_rate=detection_rate,
            latex_accuracy=latex_accuracy,
            semantic_accuracy=semantic_accuracy,
            total_count=total,
            detected_count=detected,
            correct_count=correct,
            detailed_stats={
                "formulas": details,
                "precision": correct / detected if detected > 0 else 0,
                "recall": correct / total if total > 0 else 0,
                "latex_accuracy": latex_accuracy,
                "semantic_accuracy": semantic_accuracy,
            },
        )

    def _extract_formulas(self, content: str) -> List[Dict]:
        """提取公式"""
        formulas = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检测公式特征
            formula_score = 0
            formula_markers = {
                "math_symbols": ["=", "≈", "≤", "≥", "±", "×", "÷", "∑", "∫", "∂", "√"],
                "greek_letters": [
                    "α",
                    "β",
                    "γ",
                    "δ",
                    "ε",
                    "ζ",
                    "η",
                    "θ",
                    "λ",
                    "μ",
                    "π",
                    "σ",
                    "φ",
                ],
                "operators": ["+", "-", "*", "/", "÷"],
            }

            # 计算公式特征得分
            for marker_list in formula_markers.values():
                formula_score += sum(1 for marker in marker_list if marker in line)

            # 检测LaTeX格式
            latex_patterns = [r"\\[a-z]+", r"\$[^$]+\$", r"\\begin\{equation\}"]
            for pattern in latex_patterns:
                if re.search(pattern, line):
                    formula_score += 2

            # 如果得分超过阈值，认为是公式
            if formula_score >= 1:
                formulas.append(
                    {
                        "id": len(formulas) + 1,
                        "content": line,
                        "type": "latex"
                        if any(re.search(p, line) for p in latex_patterns)
                        else "simple",
                        "score": formula_score,
                        "line_num": i,
                    }
                )

        return formulas

    def _calculate_formula_similarity(self, formula1: str, formula2: str) -> float:
        """
        计算公式相似度
        基于符号、运算符和结构
        """
        # 提取公式元素
        elements1 = self._extract_formula_elements(formula1)
        elements2 = self._extract_formula_elements(formula2)

        # Jaccard相似度
        set1 = set(elements1)
        set2 = set(elements2)

        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union > 0 else 0

        # 字符相似度
        max_len = max(len(formula1), len(formula2))
        if max_len == 0:
            return 1.0

        char_matches = sum(1 for c1, c2 in zip(formula1, formula2) if c1 == c2)
        char_similarity = char_matches / max_len

        # 混合相似度
        return jaccard * 0.6 + char_similarity * 0.4

    def _extract_formula_elements(self, formula: str) -> List[str]:
        """提取公式元素（变量、运算符、数字）"""
        elements = []

        # 提取变量
        variables = re.findall(r"[a-zA-Zα-ωΑ-Ω]", formula)
        elements.extend(variables)

        # 提取数字
        numbers = re.findall(r"\d+", formula)
        elements.extend(numbers)

        # 提取运算符
        operators = re.findall(r"[=≈≤≥±×÷+\-*/\^_\[\]]", formula)
        elements.extend(operators)

        # 提取函数
        functions = re.findall(r"\\[a-z]+", formula)
        elements.extend(functions)

        return elements

    def _evaluate_latex_accuracy(
        self, pred_formulas: List[Dict], gt_formulas: List[Dict]
    ) -> float:
        """
        评估LaTeX语法准确性（简化版本）
        """
        if not gt_formulas:
            return 1.0

        # 检查预测公式中的LaTeX语法
        correct_count = 0
        total_checked = 0

        for pred_formula in pred_formulas:
            if pred_formula.get("type") == "latex":
                total_checked += 1

                # 简单的LaTeX语法检查
                content = pred_formula["content"]

                # 检查括号匹配
                brackets_correct = self._check_brackets(content)

                # 检查基本语法
                syntax_correct = self._check_latex_syntax(content)

                if brackets_correct and syntax_correct:
                    correct_count += 1

        # 如果没有LaTeX公式，返回1.0
        if total_checked == 0:
            return 1.0

        return correct_count / total_checked

    def _check_brackets(self, text: str) -> bool:
        """检查括号是否匹配"""
        stack = []
        brackets = {"{": "}", "[": "]", "(": ")"}

        for char in text:
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack:
                    return False
                if brackets[stack.pop()] != char:
                    return False

        return len(stack) == 0

    def _check_latex_syntax(self, text: str) -> bool:
        """简单的LaTeX语法检查"""
        # 检查反斜杠后跟字母
        if re.search(r"\\[^a-zA-Z]", text):
            return False

        # 检查未闭合的命令
        if re.search(r"\\[a-z]+\s+[a-z]", text):
            return False

        return True

    def _evaluate_semantic_accuracy(
        self, pred_formulas: List[Dict], gt_formulas: List[Dict]
    ) -> float:
        """
        评估公式语义准确性（简化版本）
        检查公式的基本结构和变量是否一致
        """
        if not gt_formulas:
            return 1.0

        # 为每个标准公式找到最佳匹配
        total_similarity = 0
        matched_count = 0

        for gt_formula in gt_formulas:
            best_similarity = 0
            for pred_formula in pred_formulas:
                similarity = self._calculate_formula_similarity(
                    gt_formula["content"], pred_formula["content"]
                )
                if similarity > best_similarity:
                    best_similarity = similarity

            if best_similarity > 0:
                total_similarity += best_similarity
                matched_count += 1

        if matched_count == 0:
            return 0.0

        return total_similarity / matched_count


if __name__ == "__main__":
    # 测试代码
    evaluator = FormulaEvaluator()

    # 测试用例
    predicted = """
    根据公式: E = mc²
    以及: α + β = π
    """

    gt = {
        "formulas": [
            {"id": 1, "content": "根据公式: E = mc²", "type": "simple"},
            {"id": 2, "content": "α + β = π", "type": "simple"},
        ]
    }

    result = evaluator.evaluate(predicted, gt)
    print(f"公式检测率: {result.detection_rate:.2%}")
    print(f"公式准确率: {result.semantic_accuracy:.2%}")
