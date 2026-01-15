# 工业级RAG系统架构文档

## 系统概述

本系统是一个工业级的检索增强生成（RAG）系统，采用微服务架构设计，支持多种文档格式、混合检索策略、多LLM提供者，并具备完整的监控、安全和版本管理能力。

## 架构层次

### 1. 用户接口层
- Web UI（FastAPI）
- API网关
- RESTful API接口

### 2. 核心服务层
- **文档处理流水线** (`src/pipeline/document_processor.py`)
  - 支持PDF、Word、Excel、PPT、HTML、Markdown等格式
  - 异步处理能力
  - 元数据增强

- **智能分块器** (`src/pipeline/adaptive_chunker.py`)
  - 语义分块
  - 递归分块
  - 固定大小分块
  - 表格分块
  - 代码分块

- **混合检索系统** (`src/retrieval/hybrid_retriever.py`)
  - 向量检索（语义相似度）
  - 关键词检索（BM25/Elasticsearch）
  - 结果融合（RRF、加权融合、轮询融合）
  - 重排序

- **LLM编排器** (`src/llm/orchestrator.py`)
  - 多LLM提供者支持（OpenAI、DashScope等）
  - 成本感知路由
  - 质量优先路由
  - 多种提示模板

### 3. 支撑服务层
- **知识库版本管理** (`src/knowledge_base/version_manager.py`)
  - 版本控制
  - 增量更新
  - 变更检测
  - 回滚机制

- **安全过滤器** (`src/security/filter.py`)
  - 输入验证
  - PII检测
  - 提示注入防护
  - 输出过滤
  - 审计日志

- **质量优化器** (`src/quality/optimizer.py`)
  - 查询扩展
  - 答案验证
  - 反馈收集
  - 难例检测

- **监控系统** (`src/monitoring/metrics.py`)
  - Prometheus指标
  - 请求追踪
  - 性能监控

## 核心功能

### 文档上传与处理
```python
POST /api/v1/upload
```
- 支持多种文档格式
- 自动分块处理
- 知识库版本管理

### 查询接口
```python
POST /api/v1/query
```
- 混合检索
- LLM生成
- 安全过滤
- 质量优化

### 监控接口
```python
GET /api/v1/metrics
```
- Prometheus格式指标
- 性能统计
- 错误追踪

## 部署架构

### Kubernetes部署
- 部署配置：`k8s/deployment.yaml`
- 配置管理：`k8s/configmap.yaml`
- 告警规则：`k8s/alert-rules.yaml`

### 特性
- 水平自动伸缩（HPA）
- 健康检查（Liveness/Readiness）
- 多副本部署
- 反亲和性调度

## 配置说明

### 环境变量
- `OPENAI_API_KEY`: OpenAI API密钥
- `DASHSCOPE_API_KEY`: 阿里云DashScope API密钥
- `CHROMA_PERSIST_DIR`: ChromaDB持久化目录
- `UPLOAD_DIR`: 文档上传目录

### 配置文件
- `config.py`: 主配置文件
- `.env`: 环境变量文件

## 技术栈

- **Web框架**: FastAPI
- **向量数据库**: ChromaDB
- **全文检索**: Elasticsearch（可选）
- **LLM**: OpenAI, DashScope
- **监控**: Prometheus
- **容器编排**: Kubernetes

## 性能优化

1. **检索优化**
   - 混合检索策略
   - 结果融合（RRF）
   - 重排序

2. **缓存策略**
   - 多级缓存
   - Redis缓存（可选）

3. **异步处理**
   - 全链路异步
   - 并行检索

4. **批处理**
   - 批量向量化
   - 批量索引更新

## 安全特性

1. **输入安全**
   - 长度限制
   - 注入攻击防护
   - PII检测

2. **输出安全**
   - 有害内容过滤
   - 事实核查（可选）

3. **审计日志**
   - 完整操作记录
   - 可追溯性

## 监控指标

- 请求计数和延迟
- 检索延迟和精度
- 生成延迟和token使用
- 缓存命中率
- 错误统计

## 扩展性

系统采用模块化设计，易于扩展：
- 新增文档格式支持
- 新增检索策略
- 新增LLM提供者
- 新增质量评估指标

## 使用示例

### 上传文档
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@document.pdf"
```

### 查询
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是RAG系统？", "top_k": 5}'
```

### 查看指标
```bash
curl "http://localhost:8000/api/v1/metrics"
```

## 开发指南

### 本地开发
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入API密钥

# 运行服务
python main.py
```

### Docker部署
```bash
docker build -t rag-system:2.0.0 .
docker run -p 8000:8000 rag-system:2.0.0
```

### Kubernetes部署
```bash
kubectl apply -f k8s/
```

## 后续优化方向

1. 实现真正的语义分块（使用嵌入模型）
2. 集成Elasticsearch进行关键词检索
3. 实现图数据库检索（Neo4j）
4. 添加更多LLM提供者支持
5. 实现分布式缓存
6. 添加更多质量评估指标
7. 实现A/B测试框架
