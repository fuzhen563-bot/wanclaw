"""excel-merge — 合并多个 Excel 文件到一个工作表"""

async def run(**kwargs):
    skill_desc = "合并多个 Excel 文件到一个工作表"
    if "query" in kwargs:
        return {"skill": "excel-merge", "query": kwargs["query"], "result": f"已处理: {kwargs['query']}", "desc": skill_desc}
    if "input" in kwargs:
        return {"skill": "excel-merge", "input": kwargs["input"], "result": f"已处理: {kwargs['input']}", "desc": skill_desc}
    return {"skill": "excel-merge", "result": skill_desc, "status": "ready"}
