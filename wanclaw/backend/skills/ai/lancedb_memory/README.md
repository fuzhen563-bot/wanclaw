# LanceDB 向量记忆技能

基于 LanceDB 的向量语义记忆系统，为 WanClaw Agent 提供持久化语义记忆存储与检索能力。

## 功能特性

| 功能 | 说明 |
|------|------|
| **添加记忆** | 自动向量嵌入，支持分类标签和重要性评分 |
| **语义搜索** | 自然语言描述查找相关记忆，支持阈值过滤 |
| **会话管理** | 按 session_id 分组管理记忆链 |
| **版本追踪** | 更新自动生成新版本，保留父版本 ID |
| **相似推荐** | 查找与当前记忆相似的其他记忆 |
| **分类存储** | 支持 conversation/fact/preference/workflow/context/document 六种类型 |
| **过期清理** | 自动清理 N 天前的记忆 |

## 记忆类型

| 类型 | 说明 |
|------|------|
| `conversation` | 对话记录（默认） |
| `fact` | 事实知识 |
| `preference` | 用户偏好 |
| `workflow` | 工作流记忆 |
| `context` | 上下文片段 |
| `document` | 文档摘要 |

## API 使用

### 添加记忆

```bash
POST /api/admin/skills/execute
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "add",
    "content": "用户偏好喝美式咖啡，不加糖",
    "session_id": "user_123",
    "memory_type": "preference",
    "tags": ["咖啡", "口味偏好"],
    "importance": 0.8
  }
}
```

### 语义搜索

```bash
POST /api/admin/skills/execute
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "search",
    "query": "用户喜欢什么口味的咖啡",
    "session_id": "user_123",
    "limit": 5,
    "threshold": 0.6
  }
}
```

### 搜索结果示例

```json
{
  "success": true,
  "message": "找到 3 条相关记忆",
  "data": {
    "query": "用户喜欢什么口味的咖啡",
    "results": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "content": "用户偏好喝美式咖啡，不加糖",
        "session_id": "user_123",
        "memory_type": "preference",
        "tags": ["咖啡", "口味偏好"],
        "score": 0.9234,
        "created_at": "2026-03-26T10:30:00"
      }
    ],
    "total": 3
  }
}
```

### 获取记忆详情

```json
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "get",
    "memory_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 更新记忆

```json
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "update",
    "memory_id": "550e8400-e29b-41d4-a716-446655440000",
    "content": "用户偏好喝拿铁咖啡，加一点点糖",
    "importance": 0.9
  }
}
```

### 列出记忆

```json
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "list",
    "session_id": "user_123",
    "limit": 20
  }
}
```

### 会话历史链

```json
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "session_history",
    "session_id": "user_123"
  }
}
```

### 查找相似记忆

```json
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "similar",
    "memory_id": "550e8400-e29b-41d4-a716-446655440000",
    "limit": 5
  }
}
```

### 清理过期记忆

```json
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "cleanup",
    "days": 30,
    "session_id": "user_123"
  }
}
```

### 记忆统计

```json
{
  "skill_name": "LanceDBMemory",
  "params": {
    "action": "stats"
  }
}
```

## 通过自然语言使用

在桌面助手中发送：

```
帮我记住用户喜欢喝美式咖啡不加糖
搜索一下之前关于咖啡偏好的记忆
把刚才的记忆更新为用户现在喜欢拿铁
```

## 嵌入模型配置

优先使用 Ollama 嵌入模型，可通过环境变量配置：

```bash
export OLLAMA_BASE_URL=http://localhost:11434

# 可选模型
ollama pull nomic-embed-text   # 推荐，中英文支持好
ollama pull mxbai-embed-large
ollama pull all-minilm
```

未配置 Ollama 时，自动回退到：
1. HuggingFace Transformers (`all-MiniLM-L6-v2`)
2. 纯 SHA256 哈希向量（无语义）

## 存储结构

```
data/lancedb_memory/
├── .lancedb/
│   └── ...  (LanceDB 元数据)
└── memory.lance/
    └── ...  (记忆数据)
```

## 权限说明

```json
{
  "permissions": ["network", "filesystem:read", "filesystem:write"]
}
```

- `network`: 调用 Ollama 嵌入 API
- `filesystem:read/write`: 读写 LanceDB 数据目录

## 与 Agent 集成

在 Agent 决策循环中集成记忆检索：

```python
from wanclaw.backend.skills.ai.lancedb_memory import LanceDBMemorySkill

memory_skill = LanceDBMemorySkill()

# 检索相关记忆
result = await memory_skill.execute({
    "action": "search",
    "query": user_message,
    "session_id": session_id,
    "limit": 5
})

# 将记忆注入上下文
relevant_memories = result.data["results"]
context = "\n".join([m["content"] for m in relevant_memories])
```

## 注意事项

1. 首次运行会自动创建 `./data/lancedb_memory` 目录
2. 向量维度默认为 384，可通过嵌入模型自动适配
3. 建议配合定时清理任务，防止记忆库膨胀
4. 高并发场景建议使用 LanceDB Cloud 企业版
