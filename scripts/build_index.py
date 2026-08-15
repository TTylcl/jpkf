# ============================================
# scripts/build_index.py
# 离线建索引脚本：读MD → 切分 → embedding → 写入PG
# 用法：python scripts/build_index.py
# ============================================

import os
import sys
from pathlib import Path
from datetime import datetime

# 项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from langchain_text_splitters import RecursiveCharacterTextSplitter
from infrastructure.embedding import create_embedding
from pgvector.psycopg2 import register_vector
import psycopg2

# ---------- 配置 ----------
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
BATCH_SIZE = 5

# 数据库连接
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5434"))
DB_NAME = os.getenv("DB_NAME", "test_database")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")


def get_db_connection():
    """获取同步数据库连接"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    register_vector(conn)
    return conn


def get_embedding_model():
    """创建 Embedding 模型实例（MaaS 兼容接口）"""
    return create_embedding()


def load_markdown_files(directory: Path) -> dict[str, str]:
    """读取目录下所有 .md 文件"""
    docs = {}
    for file_path in sorted(directory.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        docs[file_path.name] = content
        print(f"  读取: {file_path.name} ({len(content)} 字符)")
    return docs


def split_documents(docs: dict[str, str]) -> list[dict]:
    """切分文档，返回 [{chunk_text, source, chunk_index}]"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )

    all_chunks = []
    for filename, content in docs.items():
        chunks = splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "chunk_text": chunk,
                "source": filename,
                "chunk_index": i,
            })
        print(f"  切分: {filename} → {len(chunks)} 个chunk")
    return all_chunks


def embed_and_insert(chunks: list[dict], conn):
    """逐批 embedding + 写入数据库"""
    cursor = conn.cursor()
    embedding_model = get_embedding_model()
    inserted = 0

    batch_texts = []
    batch_meta = []

    for chunk in chunks:
        batch_texts.append(chunk["chunk_text"])
        batch_meta.append({
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
        })

        if len(batch_texts) >= BATCH_SIZE:
            _flush_batch(embedding_model, batch_texts, batch_meta, cursor)
            inserted += len(batch_texts)
            print(f"  已写入 {inserted}/{len(chunks)} 个chunk")
            batch_texts = []
            batch_meta = []

    if batch_texts:
        _flush_batch(embedding_model, batch_texts, batch_meta, cursor)
        inserted += len(batch_texts)
        print(f"  已写入 {inserted}/{len(chunks)} 个chunk")

    conn.commit()
    cursor.close()


def _flush_batch(embedding_model, texts: list[str], meta: list[dict], cursor):
    """批量embedding并写入"""
    vectors = embedding_model.embed_documents(texts)
    for text, vec, m in zip(texts, vectors, meta):
        cursor.execute(
            """INSERT INTO knowledge_chunks (chunk_text, embedding, source, chunk_index, created_at)
               VALUES (%s, %s::vector, %s, %s, %s)""",
            (text, vec, m["source"], m["chunk_index"], datetime.now()),
        )


def main():
    print("=" * 50)
    print("离线建索引脚本")
    print("=" * 50)

    # 1. 读取文件
    print(f"\n[1] 读取知识文档")
    if not KNOWLEDGE_DIR.exists():
        print(f"  ❌ 目录不存在: {KNOWLEDGE_DIR}")
        return
    docs = load_markdown_files(KNOWLEDGE_DIR)
    if not docs:
        print("  ❌ 没有找到 .md 文件")
        return
    print(f"  共 {len(docs)} 个文件")

    # 2. 切分
    print(f"\n[2] 切分文档 (chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    chunks = split_documents(docs)
    print(f"  共 {len(chunks)} 个chunk")

    # 3. 预览
    print(f"\n[3] 切分预览 (前3个):")
    for i, chunk in enumerate(chunks[:3]):
        preview = chunk["chunk_text"][:150].replace("\n", " ")
        print(f"  [{i}] {chunk['source']} #{chunk['chunk_index']}: {preview}...")

    # 4. 连接数据库
    print(f"\n[4] 连接数据库 ({DB_HOST}:{DB_PORT}/{DB_NAME})")
    try:
        conn = get_db_connection()
        print("  ✅ 连接成功")
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return

    # 5. 清空旧数据
    print(f"\n[5] 清空旧数据")
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE knowledge_chunks")
    conn.commit()
    cursor.close()
    print("  ✅ 已清空")

    # 6. Embedding + 写入
    print(f"\n[6] Embedding + 写入")
    try:
        embed_and_insert(chunks, conn)
        print("  ✅ 全部写入完成")
    except Exception as e:
        print(f"  ❌ 写入失败: {e}")
        conn.rollback()
        conn.close()
        return

    # 7. 验证
    print(f"\n[7] 验证")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT source) FROM knowledge_chunks")
    total, sources = cursor.fetchone()
    cursor.execute("SELECT source, COUNT(*) FROM knowledge_chunks GROUP BY source ORDER BY source")
    rows = cursor.fetchall()
    print(f"  总chunk数: {total}, 文件数: {sources}")
    for source, count in rows:
        print(f"    {source}: {count} 个chunk")
    cursor.close()
    conn.close()

    print(f"\n✅ 建索引完成！共 {total} 个chunk已写入 knowledge_chunks 表")


if __name__ == "__main__":
    main()