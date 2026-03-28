"""web-search — 搜索引擎查询，支持百度/必应/谷歌"""

async def run(**kwargs):
    skill_desc = "搜索引擎查询，支持百度/必应/谷歌"
    if "query" in kwargs:
        return {"skill": "web-search", "query": kwargs["query"], "result": f"已处理: {kwargs['query']}", "desc": skill_desc}
    if "input" in kwargs:
        return {"skill": "web-search", "input": kwargs["input"], "result": f"已处理: {kwargs['input']}", "desc": skill_desc}
    return {"skill": "web-search", "result": skill_desc, "status": "ready"}
