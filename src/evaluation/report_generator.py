"""
HTML报告生成器
生成可视化的HTML评估报告
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    HTML报告生成器
    生成美观、交互式的HTML评估报告
    """

    def __init__(self):
        self.template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR准确性评估报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        header .meta {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.2em;
        }
        
        .metric {
            font-size: 2em;
            font-weight: bold;
            color: #764ba2;
            margin-bottom: 5px;
        }
        
        .metric-label {
            color: #666;
            font-size: 0.9em;
        }
        
        .section {
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background: #667eea;
            color: white;
            font-weight: bold;
        }
        
        tr:hover {
            background: #f5f7fa;
        }
        
        .accuracy-bar {
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 5px;
        }
        
        .accuracy-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
        }
        
        .status-pass {
            color: #4caf50;
            font-weight: bold;
        }
        
        .status-fail {
            color: #f44336;
            font-weight: bold;
        }
        
        .status-warning {
            color: #ff9800;
            font-weight: bold;
        }
        
        .details-container {
            display: none;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 5px;
            margin-top: 10px;
            border-left: 3px solid #667eea;
        }
        
        .details-container.show {
            display: block;
        }
        
        .toggle-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
        }
        
        .toggle-btn:hover {
            background: #764ba2;
        }
        
        .comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .comparison-box {
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        
        .comparison-box.ground-truth {
            background: #e8f5e9;
            border-color: #4caf50;
        }
        
        .comparison-box.predicted {
            background: #e3f2fd;
            border-color: #2196f3;
        }
        
        .comparison-box h4 {
            margin-bottom: 10px;
            color: #333;
        }
        
        .comparison-box h4.ground-truth {
            color: #4caf50;
        }
        
        .comparison-box h4.predicted {
            color: #2196f3;
        }
        
        .difference {
            color: #f44336;
            text-decoration: line-through;
        }
        
        .addition {
            color: #4caf50;
            font-weight: bold;
        }
        
        pre {
            background: #f5f7fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
        }
        
        .filter-controls {
            margin-bottom: 20px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 5px;
        }
        
        .filter-controls select, .filter-controls input {
            padding: 8px;
            margin-right: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        
        @media print {
        body {{
                background: white;
            }
            .container {
                max-width: 100%;
            }
            .toggle-btn {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 OCR准确性评估报告</h1>
            <div class="meta">
                <p>生成时间: {timestamp}</p>
                <p>评估变体: {variant}</p>
                <p>测试文件数: {total_files}</p>
            </div>
        </header>
        
        <!-- 总体摘要 -->
        <div class="section">
            <h2>📈 总体摘要</h2>
            <div class="summary">
                <div class="card">
                    <h3>综合得分</h3>
                    <div class="metric">{overall_score:.1%}</div>
                    <div class="metric-label">Overall Score</div>
                </div>
                <div class="card">
                    <h3>字符准确率</h3>
                    <div class="metric">{char_accuracy:.1%}</div>
                    <div class="metric-label">Character Accuracy</div>
                </div>
                <div class="card">
                    <h3>词语准确率</h3>
                    <div class="metric">{word_accuracy:.1%}</div>
                    <div class="metric-label">Word Accuracy</div>
                </div>
                <div class="card">
                    <h3>平均处理时间</h3>
                    <div class="metric">{avg_time:.1f}ms</div>
                    <div class="metric-label">Processing Time</div>
                </div>
            </div>
        </div>
        
        <!-- 文本准确率详情 -->
        <div class="section">
            <h2>📝 文本准确率详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>PDF文件</th>
                        <th>字符准确率</th>
                        <th>词语准确率</th>
                        <th>编辑距离</th>
                        <th>状态</th>
                        <th>详情</th>
                    </tr>
                </thead>
                <tbody>
                    {text_rows}
                </tbody>
            </table>
        </div>
        
        <!-- 结构识别详情 -->
        <div class="section">
            <h2>🔧 结构识别详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>PDF文件</th>
                        <th>表格准确率</th>
                        <th>标题准确率</th>
                        <th>列表准确率</th>
                        <th>公式准确率</th>
                    </tr>
                </thead>
                <tbody>
                    {structure_rows}
                </tbody>
            </table>
        </div>
        
        <!-- 逐页对比 -->
        <div class="section">
            <h2>📄 逐页对比</h2>
            <div class="filter-controls">
                <select id="pdf-filter" onchange="filterPages()">
                    <option value="all">所有PDF文件</option>
                    {pdf_options}
                </select>
                <select id="status-filter" onchange="filterPages()">
                    <option value="all">所有状态</option>
                    <option value="pass">通过</option>
                    <option value="fail">失败</option>
                    <option value="warning">警告</option>
                </select>
            </div>
            <div id="page-comparisons">
                {page_comparisons}
            </div>
        </div>
        
        <!-- 详细统计 -->
        <div class="section">
            <h2>📊 详细统计</h2>
            <pre>{detailed_stats}</pre>
        </div>
        
        <footer>
            <p style="text-align: center; color: #666; margin-top: 30px;">
                OCR准确性评估报告 - 自动生成
            </p>
        </footer>
    </div>
    
    <script>
        function toggleDetails(id) {{
            const element = document.getElementById(id);
            element.classList.toggle('show');
        }}
        
        function filterPages() {{
            const pdfFilter = document.getElementById('pdf-filter').value;
            const statusFilter = document.getElementById('status-filter').value;
            const pages = document.querySelectorAll('.page-comparison');
            
            pages.forEach(page => {{
                const pagePdf = page.getAttribute('data-pdf');
                const pageStatus = page.getAttribute('data-status');
                
                const pdfMatch = pdfFilter === 'all' || pagePdf === pdfFilter;
                const statusMatch = statusFilter === 'all' || pageStatus === statusFilter;
                
                page.style.display = (pdfMatch && statusMatch) ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""
        import re

        # 转义<style>标签内的所有花括号（除了已经转义的）
        def escape_css_braces(match):
            css = match.group(1)
            # 将单花括号替换为双花括号，但避免重复转义
            css = re.sub(r"(?<!\{)\{(?!\{)", "{{", css)
            css = re.sub(r"(?<!\})\}(?!\})", "}}", css)
            return "<style>" + css + "</style>"

        self.template = re.sub(
            r"<style>(.*?)</style>", escape_css_braces, self.template, flags=re.DOTALL
        )

    def generate(self, evaluation_results: Dict[str, Any], output_path: str):
        """
        生成HTML报告

        Args:
            evaluation_results: 评估结果
            output_path: 输出文件路径
        """
        # 准备数据
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        variant = evaluation_results.get("variant", "ocr_enhanced")
        total_files = len(evaluation_results.get("file_results", []))

        # 计算总体指标
        metrics = evaluation_results.get("metrics", {})
        overall_score = metrics.get("overall", {}).get("score", 0.0)
        text_metrics = metrics.get("text", {})
        perf_metrics = metrics.get("performance", {})

        # 生成表格行
        text_rows = self._generate_text_rows(evaluation_results.get("file_results", []))
        structure_rows = self._generate_structure_rows(
            evaluation_results.get("file_results", [])
        )
        page_comparisons = self._generate_page_comparisons(
            evaluation_results.get("file_results", [])
        )
        pdf_options = self._generate_pdf_options(
            evaluation_results.get("file_results", [])
        )
        detailed_stats = json.dumps(metrics, indent=2, ensure_ascii=False)

        # 填充模板
        html_content = self.template.format(
            timestamp=timestamp,
            variant=variant,
            total_files=total_files,
            overall_score=overall_score,
            char_accuracy=text_metrics.get("char_accuracy", 0.0),
            word_accuracy=text_metrics.get("word_accuracy", 0.0),
            avg_time=perf_metrics.get("avg_processing_time_ms", 0.0),
            text_rows=text_rows,
            structure_rows=structure_rows,
            page_comparisons=page_comparisons,
            pdf_options=pdf_options,
            detailed_stats=detailed_stats,
        )

        # 保存文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML报告生成完成: {output_path}")

    def _generate_text_rows(self, file_results: List[Dict]) -> str:
        """生成文本准确率表格行"""
        rows = []

        for file_result in file_results:
            pdf_name = file_result.get("pdf_file", "Unknown")
            text_result = file_result.get("text_accuracy", {})

            # 支持TextMetrics对象和字典
            if hasattr(text_result, "char_accuracy"):
                char_acc = text_result.char_accuracy
                word_acc = text_result.word_accuracy
                lev_dist = text_result.levenshtein_distance
                detailed_stats = getattr(text_result, "detailed_stats", {})
            else:
                char_acc = text_result.get("char_accuracy", 0.0)
                word_acc = text_result.get("word_accuracy", 0.0)
                lev_dist = text_result.get("levenshtein_distance", 0)
                detailed_stats = text_result.get("detailed_stats", {})

            # 判断状态
            if char_acc >= 0.95:
                status = '<span class="status-pass">通过</span>'
                status_class = "pass"
            elif char_acc >= 0.85:
                status = '<span class="status-warning">警告</span>'
                status_class = "warning"
            else:
                status = '<span class="status-fail">失败</span>'
                status_class = "fail"

            # 准确率条
            char_bar = f"""
                <div class="accuracy-bar">
                    <div class="accuracy-fill" style="width: {char_acc * 100}%"></div>
                </div>
            """

            row = f"""
                <tr>
                    <td>{pdf_name}</td>
                    <td>
                        {char_acc:.2%}
                        {char_bar}
                    </td>
                    <td>{word_acc:.2%}</td>
                    <td>{lev_dist}</td>
                    <td>{status}</td>
                    <td>
                        <button class="toggle-btn" onclick="toggleDetails('details-{len(rows)}')">查看详情</button>
                    </td>
                </tr>
                <tr id="details-{len(rows)}" class="details-container">
                    <td colspan="6">
                        <h4>详细统计</h4>
                        <pre>{json.dumps(detailed_stats, indent=2, ensure_ascii=False)}</pre>
                    </td>
                </tr>
            """

            rows.append(row)

        return "\n".join(rows)

    def _generate_structure_rows(self, file_results: List[Dict]) -> str:
        """生成结构识别表格行"""
        rows = []

        for file_result in file_results:
            pdf_name = file_result.get("pdf_file", "Unknown")
            structure_results = file_result.get("structure_evaluation", {})

            # 支持StructureMetrics对象和字典
            if hasattr(structure_results, "table_accuracy"):
                table_acc = structure_results.table_accuracy
                header_acc = structure_results.header_accuracy
                list_acc = structure_results.list_accuracy
                formula_acc = structure_results.formula_accuracy
            else:
                table_acc = structure_results.get("table", {}).get("accuracy", 0.0)
                header_acc = structure_results.get("header", {}).get("accuracy", 0.0)
                list_acc = structure_results.get("list", {}).get("accuracy", 0.0)
                formula_acc = structure_results.get("formula", {}).get("accuracy", 0.0)

            row = f"""
                <tr>
                    <td>{pdf_name}</td>
                    <td>{table_acc:.2%}</td>
                    <td>{header_acc:.2%}</td>
                    <td>{list_acc:.2%}</td>
                    <td>{formula_acc:.2%}</td>
                </tr>
            """

            rows.append(row)

        return "\n".join(rows)

    def _generate_page_comparisons(self, file_results: List[Dict]) -> str:
        """生成逐页对比HTML"""
        comparisons = []

        for file_result in file_results:
            pdf_name = file_result.get("pdf_file", "Unknown")
            pages = file_result.get("pages", [])

            for page_data in pages:
                page_num = page_data.get("page_num", 0)
                predicted = page_data.get("predicted", "")
                ground_truth = page_data.get("ground_truth", "")
                text_accuracy = page_data.get("text_accuracy", {})
                if hasattr(text_accuracy, "char_accuracy"):
                    accuracy = text_accuracy.char_accuracy
                else:
                    accuracy = text_accuracy.get("char_accuracy", 0.0)

                # 判断状态
                if accuracy >= 0.95:
                    status = "pass"
                elif accuracy >= 0.85:
                    status = "warning"
                else:
                    status = "fail"

                comparison = f'''
                    <div class="page-comparison" data-pdf="{pdf_name}" data-status="{status}">
                        <h3>📄 {pdf_name} - 第 {page_num + 1} 页</h3>
                        <p><strong>准确率:</strong> {accuracy:.2%}</p>
                        
                        <div class="comparison">
                            <div class="comparison-box ground-truth">
                                <h4>标准答案 (Ground Truth)</h4>
                                <p>{self._truncate_text(ground_truth, 200)}</p>
                            </div>
                            <div class="comparison-box predicted">
                                <h4>OCR结果 (Predicted)</h4>
                                <p>{self._truncate_text(predicted, 200)}</p>
                            </div>
                        </div>
                    </div>
                '''

                comparisons.append(comparison)

        return "\n".join(comparisons)

    def _generate_pdf_options(self, file_results: List[Dict]) -> str:
        """生成PDF筛选选项"""
        options = []
        for file_result in file_results:
            pdf_name = file_result.get("pdf_file", "Unknown")
            option = f'<option value="{pdf_name}">{pdf_name}</option>'
            options.append(option)
        return "\n".join(options)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
