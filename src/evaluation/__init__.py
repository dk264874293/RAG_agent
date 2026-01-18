"""
OCR准确性评估模块
提供PDF OCR准确性评估的多维度指标
"""

__version__ = "1.0.0"
__author__ = "RAG Agent System"

from .ground_truth_generator import GroundTruthGenerator
from .test_runner import EvaluationTestRunner
from .report_generator import HTMLReportGenerator
from .metrics import TextMetrics, StructureMetrics

__all__ = [
    "GroundTruthGenerator",
    "EvaluationTestRunner",
    "HTMLReportGenerator",
    "TextMetrics",
    "StructureMetrics",
]
