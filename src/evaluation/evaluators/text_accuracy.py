"""
文本准确率评估器
计算字符级、词语级准确率和编辑距离
"""

import logging
from typing import Dict, List, Any, Tuple
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextAccuracyResult:
    """文本准确率评估结果"""

    char_accuracy: float
    word_accuracy: float
    levenshtein_distance: int
    normalized_distance: float
    line_match_accuracy: float
    char_error_rate: float
    word_error_rate: float
    detailed_stats: Dict[str, Any]


class TextAccuracyEvaluator:
    """
    文本准确率评估器
    支持中英文混合文本评估
    """

    def __init__(self):
        self.chinese_pattern = re.compile(r"[\u4e00-\u9fff]")
        self.english_pattern = re.compile(r"[a-zA-Z]+")
        self.digit_pattern = re.compile(r"\d+")

    def evaluate(self, predicted: str, ground_truth: str) -> TextAccuracyResult:
        """
        评估预测文本与标准文本的准确率

        Args:
            predicted: 预测文本
            ground_truth: 标准文本

        Returns:
            TextAccuracyResult对象
        """
        # 预处理：去除多余空格
        pred_clean = self._preprocess_text(predicted)
        gt_clean = self._preprocess_text(ground_truth)

        # 1. 字符级准确率
        char_acc, char_stats = self._character_accuracy(pred_clean, gt_clean)

        # 2. 词语级准确率（中文分词）
        word_acc, word_stats = self._word_accuracy(pred_clean, gt_clean)

        # 3. 编辑距离
        lev_dist, norm_dist = self._levenshtein_distance(pred_clean, gt_clean)

        # 4. 行匹配准确率
        line_acc, line_stats = self._line_match_accuracy(pred_clean, gt_clean)

        # 5. 错误率
        char_error_rate = 1.0 - char_acc
        word_error_rate = 1.0 - word_acc

        # 汇总详细统计
        detailed_stats = {
            "character": char_stats,
            "word": word_stats,
            "line": line_stats,
            "length_comparison": {
                "predicted_length": len(pred_clean),
                "ground_truth_length": len(gt_clean),
                "length_difference": len(pred_clean) - len(gt_clean),
                "length_ratio": len(pred_clean) / len(gt_clean)
                if len(gt_clean) > 0
                else 0,
            },
        }

        return TextAccuracyResult(
            char_accuracy=char_acc,
            word_accuracy=word_acc,
            levenshtein_distance=lev_dist,
            normalized_distance=norm_dist,
            line_match_accuracy=line_acc,
            char_error_rate=char_error_rate,
            word_error_rate=word_error_rate,
            detailed_stats=detailed_stats,
        )

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 去除多余的空白字符
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    def _character_accuracy(
        self, predicted: str, ground_truth: str
    ) -> Tuple[float, Dict]:
        """
        计算字符级准确率

        对于中文字符：逐个字符匹配
        对于英文字符：按单词匹配
        """
        if not ground_truth:
            return 1.0, {"total": 0, "correct": 0}

        total_chars = len(ground_truth)
        correct_chars = 0
        chinese_stats = [0, 0]  # [total, correct]
        english_stats = [0, 0]  # [total, correct]
        digit_stats = [0, 0]  # [total, correct]

        # 对齐文本（简单的逐字符对齐）
        max_len = max(len(predicted), len(ground_truth))
        for i in range(max_len):
            if i >= len(ground_truth):
                # 预测文本比标准文本长
                continue
            elif i >= len(predicted):
                # 预测文本比标准文本短
                char = ground_truth[i]
                self._classify_and_count(
                    char,
                    0,
                    chinese_stats,
                    english_stats,
                    digit_stats,
                )
            else:
                pred_char = predicted[i]
                gt_char = ground_truth[i]

                is_match = pred_char == gt_char
                if is_match:
                    correct_chars += 1

                self._classify_and_count(
                    gt_char,
                    1 if is_match else 0,
                    chinese_stats,
                    english_stats,
                    digit_stats,
                )

        accuracy = correct_chars / total_chars if total_chars > 0 else 1.0

        stats = {
            "total": total_chars,
            "correct": correct_chars,
            "chinese": {
                "total": chinese_stats[0],
                "correct": chinese_stats[1],
                "accuracy": chinese_stats[1] / chinese_stats[0]
                if chinese_stats[0] > 0
                else 0,
            },
            "english": {
                "total": english_stats[0],
                "correct": english_stats[1],
                "accuracy": english_stats[1] / english_stats[0]
                if english_stats[0] > 0
                else 0,
            },
            "digits": {
                "total": digit_stats[0],
                "correct": digit_stats[1],
                "accuracy": digit_stats[1] / digit_stats[0]
                if digit_stats[0] > 0
                else 0,
            },
        }

        return accuracy, stats

    def _classify_and_count(
        self,
        char: str,
        is_correct: int,
        chinese: list,
        english: list,
        digits: list,
    ):
        """分类并统计字符"""
        if self.chinese_pattern.search(char):
            chinese[0] += 1  # total
            chinese[1] += is_correct  # correct
        elif self.english_pattern.search(char):
            english[0] += 1
            english[1] += is_correct
        elif char.isdigit():
            digits[0] += 1
            digits[1] += is_correct

    def _word_accuracy(self, predicted: str, ground_truth: str) -> Tuple[float, Dict]:
        """
        计算词语级准确率
        中文：按字符（因为中文没有显式的词边界）
        英文：按单词
        """
        if not ground_truth:
            return 1.0, {"total": 0, "correct": 0}

        # 中文分词（简化：按字符）
        chinese_gt = list(self.chinese_pattern.findall(ground_truth))
        chinese_pred = list(self.chinese_pattern.findall(predicted))

        # 英文分词
        english_gt = self.english_pattern.findall(ground_truth)
        english_pred = self.english_pattern.findall(predicted)

        # 统计中文
        chinese_total = len(chinese_gt)
        chinese_correct = 0
        for i, char in enumerate(chinese_pred):
            if i < chinese_total and char == chinese_gt[i]:
                chinese_correct += 1

        # 统计英文
        english_total = len(english_gt)
        english_correct = 0
        for i, word in enumerate(english_pred):
            if i < english_total and word.lower() == english_gt[i].lower():
                english_correct += 1

        total_words = chinese_total + english_total
        correct_words = chinese_correct + english_correct
        accuracy = correct_words / total_words if total_words > 0 else 1.0

        stats = {
            "total": total_words,
            "correct": correct_words,
            "chinese": {"total": chinese_total, "correct": chinese_correct},
            "english": {"total": english_total, "correct": english_correct},
        }

        return accuracy, stats

    def _levenshtein_distance(self, s1: str, s2: str) -> Tuple[int, float]:
        """
        计算Levenshtein编辑距离
        """
        m, n = len(s1), len(s2)

        # 创建距离矩阵
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # 初始化边界
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        # 动态规划计算
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    cost = 0
                else:
                    cost = 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # 删除
                    dp[i][j - 1] + 1,  # 插入
                    dp[i - 1][j - 1] + cost,  # 替换
                )

        distance = dp[m][n]
        max_len = max(m, n)
        normalized = distance / max_len if max_len > 0 else 0

        return distance, normalized

    def _line_match_accuracy(
        self, predicted: str, ground_truth: str
    ) -> Tuple[float, Dict]:
        """
        计算行匹配准确率
        """
        pred_lines = [line.strip() for line in predicted.split("\n") if line.strip()]
        gt_lines = [line.strip() for line in ground_truth.split("\n") if line.strip()]

        if not gt_lines:
            return 1.0, {"total": 0, "matched": 0}

        matched = 0
        total = len(gt_lines)
        exact_matches = 0

        # 简单的逐行匹配
        for i, gt_line in enumerate(gt_lines):
            if i < len(pred_lines):
                pred_line = pred_lines[i]
                if pred_line == gt_line:
                    exact_matches += 1
                    matched += 1
                elif self._fuzzy_match(pred_line, gt_line):
                    matched += 1

        accuracy = matched / total if total > 0 else 1.0

        stats = {
            "total": total,
            "matched": matched,
            "exact_matches": exact_matches,
            "partial_matches": matched - exact_matches,
            "accuracy": accuracy,
        }

        return accuracy, stats

    def _fuzzy_match(self, s1: str, s2: str, threshold: float = 0.8) -> bool:
        """模糊匹配（基于相似度）"""
        if not s1 or not s2:
            return False

        # 计算Jaccard相似度
        set1 = set(s1.split())
        set2 = set(s2.split())

        if not set1 or not set2:
            return s1 == s2

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        similarity = intersection / union if union > 0 else 0

        return similarity >= threshold


if __name__ == "__main__":
    # 测试代码
    evaluator = TextAccuracyEvaluator()

    # 测试用例1：中文
    pred1 = "这是一个测试文本"
    gt1 = "这是一个测试文本"
    result1 = evaluator.evaluate(pred1, gt1)
    print(f"测试1: 字符准确率={result1.char_accuracy:.2%}")

    # 测试用例2：英文
    pred2 = "This is a test text"
    gt2 = "This is a test text"
    result2 = evaluator.evaluate(pred2, gt2)
    print(f"测试2: 字符准确率={result2.char_accuracy:.2%}")

    # 测试用例3：有错误
    pred3 = "这是一个测试文本，有错误"
    gt3 = "这是一个测试文本，正确"
    result3 = evaluator.evaluate(pred3, gt3)
    print(
        f"测试3: 字符准确率={result3.char_accuracy:.2%}, 编辑距离={result3.levenshtein_distance}"
    )
