"""
知识库版本管理与更新
"""
import hashlib
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from ..models.document import Document


class KnowledgeBaseManager:
    """知识库版本管理与更新"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.metadata_db = None  # 元数据数据库连接
        self.vector_store = None  # 向量存储连接
        
        # 初始化数据库连接
        self._init_metadata_db()
    
    def _init_metadata_db(self):
        """初始化元数据数据库"""
        # 简化版：使用SQLite作为元数据存储
        # 生产环境应该使用PostgreSQL
        try:
            import sqlite3
            db_path = self.config.get('metadata_db_path', './data/kb_metadata.db')
            self.metadata_db = sqlite3.connect(db_path, check_same_thread=False)
            self._init_schema()
        except ImportError:
            print("警告: 无法初始化SQLite，版本管理功能可能受限")
    
    def _init_schema(self):
        """初始化数据库表"""
        if not self.metadata_db:
            return
        
        cursor = self.metadata_db.cursor()
        
        # 版本表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_versions (
                version_id TEXT PRIMARY KEY,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                document_count INTEGER,
                chunk_count INTEGER,
                vector_index_name TEXT,
                status TEXT DEFAULT 'pending',
                checksum TEXT
            )
        """)
        
        # 文档变更表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_changes (
                change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id TEXT,
                document_id TEXT,
                operation TEXT,
                previous_hash TEXT,
                new_hash TEXT,
                change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES kb_versions(version_id)
            )
        """)
        
        # 文档表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                file_path TEXT,
                file_hash TEXT,
                file_size INTEGER,
                file_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version_id TEXT
            )
        """)
        
        self.metadata_db.commit()
    
    def _generate_version_id(self) -> str:
        """生成版本ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"v{timestamp}"
    
    def _calculate_hash(self, content: str) -> str:
        """计算内容哈希值"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def update_knowledge_base(self, documents: List[Document]) -> str:
        """增量更新知识库"""
        try:
            # 1. 文档去重
            deduped_docs = await self.deduplicate(documents)
            
            # 2. 变更检测
            changes = await self.detect_changes(deduped_docs)
            
            if not changes['has_changes']:
                return "无变更，跳过更新"
            
            # 3. 创建新版本记录
            version_id = self._generate_version_id()
            await self._create_version_record(version_id, changes)
            
            # 4. 增量索引更新
            if changes['new'] or changes['updated']:
                await self.update_index_incrementally(changes, version_id)
            
            # 5. 删除处理
            if changes['deleted']:
                await self.remove_documents(changes['deleted'])
            
            # 6. 创建版本快照
            snapshot_path = await self.create_version_snapshot(version_id)
            
            # 7. 质量检查
            quality_passed = await self.run_quality_checks(version_id)
            
            if quality_passed:
                # 8. 更新版本状态为活跃
                await self._activate_version(version_id)
                
                # 9. 更新路由配置
                await self.update_routing_config(version_id)
                
                return f"知识库更新成功，版本: {version_id}"
            else:
                # 回滚到上一版本
                await self.rollback_version(version_id)
                return "质量检查未通过，已回滚"
                
        except Exception as e:
            print(f"知识库更新失败: {e}")
            raise
    
    async def deduplicate(self, documents: List[Document]) -> List[Document]:
        """文档去重"""
        seen_hashes = set()
        deduped = []
        
        for doc in documents:
            content_hash = self._calculate_hash(doc.page_content)
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduped.append(doc)
        
        return deduped
    
    async def detect_changes(self, documents: List[Document]) -> Dict:
        """检测文档变更"""
        changes = {
            'new': [],
            'updated': [],
            'deleted': [],
            'unchanged': [],
            'has_changes': False
        }
        
        if not self.metadata_db:
            # 如果没有数据库，所有文档都视为新文档
            changes['new'] = documents
            changes['has_changes'] = len(documents) > 0
            return changes
        
        # 获取现有文档的哈希值
        existing_hashes = await self._get_existing_document_hashes()
        new_hashes = {doc.id_: self._calculate_hash(doc.page_content) for doc in documents}
        
        # 检测变更
        for doc in documents:
            doc_hash = new_hashes[doc.id_]
            
            if doc.id_ not in existing_hashes:
                changes['new'].append(doc)
                changes['has_changes'] = True
            elif existing_hashes[doc.id_] != doc_hash:
                changes['updated'].append(doc)
                changes['has_changes'] = True
            else:
                changes['unchanged'].append(doc)
        
        # 检测删除
        existing_ids = set(existing_hashes.keys())
        new_ids = set(new_hashes.keys())
        deleted_ids = existing_ids - new_ids
        
        changes['deleted'] = list(deleted_ids)
        if deleted_ids:
            changes['has_changes'] = True
        
        return changes
    
    async def _get_existing_document_hashes(self) -> Dict[str, str]:
        """获取现有文档的哈希值"""
        if not self.metadata_db:
            return {}
        
        cursor = self.metadata_db.cursor()
        cursor.execute("SELECT document_id, file_hash FROM documents")
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}
    
    async def _create_version_record(self, version_id: str, changes: Dict):
        """创建版本记录"""
        if not self.metadata_db:
            return
        
        cursor = self.metadata_db.cursor()
        cursor.execute("""
            INSERT INTO kb_versions 
            (version_id, document_count, chunk_count, status)
            VALUES (?, ?, ?, ?)
        """, (
            version_id,
            len(changes['new']) + len(changes['updated']) + len(changes['unchanged']),
            0,  # chunk_count将在后续更新
            'pending'
        ))
        self.metadata_db.commit()
    
    async def update_index_incrementally(self, changes: Dict, version_id: str):
        """增量更新索引"""
        # 这里应该调用向量存储的更新接口
        # 简化版：占位符
        pass
    
    async def remove_documents(self, document_ids: List[str]):
        """删除文档"""
        if not self.metadata_db:
            return
        
        cursor = self.metadata_db.cursor()
        placeholders = ','.join(['?'] * len(document_ids))
        cursor.execute(f"DELETE FROM documents WHERE document_id IN ({placeholders})", document_ids)
        self.metadata_db.commit()
    
    async def create_version_snapshot(self, version_id: str) -> str:
        """创建版本快照"""
        # 简化版：返回路径
        return f"./data/snapshots/{version_id}"
    
    async def run_quality_checks(self, version_id: str) -> bool:
        """运行质量检查"""
        # 简化版：总是通过
        # 实际应该检查：文档完整性、向量质量等
        return True
    
    async def _activate_version(self, version_id: str):
        """激活版本"""
        if not self.metadata_db:
            return
        
        # 将其他版本设为非活跃
        cursor = self.metadata_db.cursor()
        cursor.execute("UPDATE kb_versions SET status = 'inactive' WHERE status = 'active'")
        # 激活当前版本
        cursor.execute("UPDATE kb_versions SET status = 'active' WHERE version_id = ?", (version_id,))
        self.metadata_db.commit()
    
    async def update_routing_config(self, version_id: str):
        """更新路由配置"""
        # 简化版：占位符
        pass
    
    async def rollback_version(self, version_id: str):
        """回滚版本"""
        if not self.metadata_db:
            return
        
        cursor = self.metadata_db.cursor()
        cursor.execute("DELETE FROM kb_versions WHERE version_id = ?", (version_id,))
        cursor.execute("DELETE FROM document_changes WHERE version_id = ?", (version_id,))
        self.metadata_db.commit()
