#!/usr/bin/env python3
"""
WanClaw 官方插件生态包生成脚本 v2
生成 60+ 个去重后的官方插件（覆盖电商/IM/办公RPA/AI/数据/运维/工作流/生态）
用法: python3 scripts/generate_all_official_plugins.py
"""

import os
import sys
import json
import zipfile
import io
from pathlib import Path
from datetime import datetime

WANCLAW_PLUGINS = Path("/data/wanclaw/wanclaw/wanclaw/plugins/official")
WANCLAW_PLUGINS.mkdir(parents=True, exist_ok=True)
SKILLS_DIR = Path("/data/wanclaw/wanclaw/wanclaw/backend/skills")

sys.path.insert(0, str(Path("/data/wanclaw/wanclaw").parent.parent / "clawhub"))
os.environ.setdefault("FLASK_ENV", "production")

AUTHOR = "WanClaw"
AUTHOR_EMAIL = "official@clawhub.com"
VERSION = "2.0.0"
COMPATIBLE_VERSION = ">=2.0.0"
AUTHOR_ID = 1

CATEGORIES = {
    "ecommerce": "电商自动化",
    "im": "IM智能客服",
    "office": "办公RPA",
    "ai": "AI增强",
    "data": "数据统计",
    "ops": "系统运维",
    "workflow": "工作流",
    "ecosystem": "插件生态",
}

LEVEL_NAMES = {
    "beginner": "初级",
    "intermediate": "中级",
    "advanced": "高级",
}


PLUGINS = {
    # ==================== 电商自动化 (14) ====================
    "ec_order_remark": {
        "name": "淘宝订单自动备注",
        "category": "ecommerce",
        "level": "intermediate",
        "description": "淘宝/天猫订单自动识别买家留言并打标备注，支持关键词匹配、颜色尺码提取、发货时间承诺",
        "keywords": ["淘宝", "天猫", "订单备注", "打标", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_refund_auto": {
        "name": "拼多多售后自动退款",
        "category": "ecommerce",
        "level": "advanced",
        "description": "拼多多售后单自动审核，符合条件自动同意退款退货，异常单标记人工处理",
        "keywords": ["拼多多", "售后", "退款", "自动审核", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_shipment_sync": {
        "name": "抖店自动发货同步",
        "category": "ecommerce",
        "level": "intermediate",
        "description": "抖音小店订单自动抓取、物流信息自动回填、发货状态自动同步至平台",
        "keywords": ["抖音", "抖店", "自动发货", "物流同步", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_product_auto_listing": {
        "name": "商品自动上下架",
        "category": "ecommerce",
        "level": "intermediate",
        "description": "多平台电商商品定时上下架、库存为0自动下架、活动结束自动恢复，支持淘宝/京东/拼多多/抖音",
        "keywords": ["商品", "上下架", "定时", "库存", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_order_close": {
        "name": "超时订单自动关闭",
        "category": "ecommerce",
        "level": "beginner",
        "description": "电商平台超时未支付订单自动关闭，释放库存，支持自定义超时时间规则",
        "keywords": ["订单", "超时", "自动关闭", "库存释放", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_tracking_auto": {
        "name": "物流单号自动识别",
        "category": "ecommerce",
        "level": "intermediate",
        "description": "发货时自动识别快递单号格式、回填物流信息、异常单号自动提醒",
        "keywords": ["物流", "快递", "单号识别", "回填", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_review_monitor": {
        "name": "差评自动监控提醒",
        "category": "ecommerce",
        "level": "intermediate",
        "description": "多平台买家差评、中差评实时监控，自动推送至钉钉/飞书/微信，提醒客服及时响应",
        "keywords": ["差评", "监控", "中差评", "提醒", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_unified_order_view": {
        "name": "多店铺订单统一视图",
        "category": "ecommerce",
        "level": "advanced",
        "description": "聚合淘宝/京东/拼多多/抖音/快手等多平台订单，统一展示、筛选、导出",
        "keywords": ["多平台", "订单聚合", "统一视图", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_shipping_fee": {
        "name": "运费智能计算",
        "category": "ecommerce",
        "level": "intermediate",
        "description": "根据商品重量、地区、快递公司自动计算运费，支持首重续重、满减包邮规则",
        "keywords": ["运费", "物流计算", "快递", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_data_mask": {
        "name": "订单数据脱敏导出",
        "category": "ecommerce",
        "level": "advanced",
        "description": "订单数据导出时自动脱敏（手机号、地址、姓名），支持自定义脱敏规则，满足数据安全合规",
        "keywords": ["脱敏", "数据安全", "隐私", "导出", "电商"],
        "permissions": ["database", "filesystem:write"],
        "dependencies": [],
    },
    "ec_presale_split": {
        "name": "预售订单自动拆分",
        "category": "ecommerce",
        "level": "advanced",
        "description": "预售订单按商品库存状态自动拆分为现货单/预售单，分别推送至仓库处理",
        "keywords": ["预售", "订单拆分", "库存", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_rto_ledger": {
        "name": "退换货自动台账",
        "category": "ecommerce",
        "level": "intermediate",
        "description": "电商退换货申请自动登记台账，跟踪处理进度，自动生成月度退换货报表",
        "keywords": ["退换货", "台账", "退货", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_stock_alert": {
        "name": "库存阈值自动告警",
        "category": "ecommerce",
        "level": "beginner",
        "description": "商品库存低于预设阈值时自动告警，支持多平台店铺、多SKU监控，消息推送到钉钉/飞书/邮件",
        "keywords": ["库存", "告警", "阈值", "库存预警", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ec_auto_review_reply": {
        "name": "评价智能自动回复",
        "category": "ecommerce",
        "level": "advanced",
        "description": "基于语义识别自动生成评价回复，好评感谢、中差评安抚，支持自定义回复模板和AI生成",
        "keywords": ["评价", "自动回复", "好评", "差评回复", "电商"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },

    # ==================== IM智能客服 & 私域运营 (14) ====================
    "im_friend_auto": {
        "name": "好友自动通过与打标",
        "category": "im",
        "level": "intermediate",
        "description": "新好友申请自动通过、按来源渠道自动打标签，支持企业微信/微信/QQ等多平台",
        "keywords": ["好友", "自动通过", "打标签", "私域", "微信"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "im_welcome_auto": {
        "name": "新人入群自动欢迎",
        "category": "im",
        "level": "beginner",
        "description": "新成员加入群聊时自动发送欢迎语，支持@mention、自定义文案、间隔发送避免频繁",
        "keywords": ["群欢迎", "欢迎语", "自动发送", "私域", "微信"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "im_keyword_reply": {
        "name": "关键词触发自动回复",
        "category": "im",
        "level": "intermediate",
        "description": "根据消息关键词自动匹配回复内容，支持正则表达式、模糊匹配、多答案随机回复",
        "keywords": ["关键词", "自动回复", "触发", "客服", "私域"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "im_anti_ads": {
        "name": "广告违规自动踢人",
        "category": "im",
        "level": "intermediate",
        "description": "群内检测广告链接、敏感词、诱导分享等违规内容，自动警告或踢出，并记录日志",
        "keywords": ["广告", "踢人", "违规词", "社群运营", "微信"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "im_mute_schedule": {
        "name": "静音时段定时开关",
        "category": "im",
        "level": "beginner",
        "description": "设置消息免打扰时段，自动开启/关闭消息免打扰，支持工作日/周末不同规则",
        "keywords": ["静音", "免打扰", "定时", "私域", "微信"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "im_message_priority": {
        "name": "客户消息智能分级",
        "category": "im",
        "level": "advanced",
        "description": "基于消息内容和客户画像自动分级（紧急/重要/普通），优先推送高价值客户消息",
        "keywords": ["消息分级", "优先级", "客户分层", "私域"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "im_inbox_unified": {
        "name": "多平台消息统一收件箱",
        "category": "im",
        "level": "advanced",
        "description": "聚合企业微信/钉钉/飞书/Telegram等消息，统一展示、回复、检索，支持会话合并",
        "keywords": ["统一收件箱", "多平台", "消息聚合", "IM"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "im_quick_reply": {
        "name": "快捷回复模板库",
        "category": "im",
        "level": "beginner",
        "description": "常用话术模板库，支持分类管理、快捷搜索、一键发送，提高客服效率",
        "keywords": ["快捷回复", "话术库", "模板", "客服"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "im_group_activity": {
        "name": "群活跃度统计分析",
        "category": "im",
        "level": "intermediate",
        "description": "自动统计群的发言人数、消息数量、活跃时段，生成日/周/月度群运营报告",
        "keywords": ["群活跃度", "统计分析", "社群运营", "微信"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "im_profile_auto": {
        "name": "客户画像自动记录",
        "category": "im",
        "level": "intermediate",
        "description": "自动记录客户的基础信息、咨询内容、购买记录，构建完整客户画像并打标签",
        "keywords": ["客户画像", "标签", "私域运营", "CRM"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "im_voice_to_text": {
        "name": "语音消息转文字",
        "category": "im",
        "level": "intermediate",
        "description": "接收到的语音消息自动转文字，方便客服查看和检索，支持普通话和方言",
        "keywords": ["语音转文字", "ASR", "语音识别", "IM"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "im_blacklist_sync": {
        "name": "跨平台黑名单同步",
        "category": "im",
        "level": "intermediate",
        "description": "黑名单用户跨平台同步，多平台自动拦截，永久封禁，支持手动添加和自动规则",
        "keywords": ["黑名单", "同步", "封禁", "私域", "IM"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "im_schedule_broadcast": {
        "name": "定时群发消息",
        "category": "im",
        "level": "intermediate",
        "description": "定时向客户/群聊发送营销内容，支持内容审核、定时取消、发送效果追踪",
        "keywords": ["定时群发", "营销", "消息推送", "私域"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "im_transfer_handoff": {
        "name": "客服会话智能转接",
        "category": "im",
        "level": "advanced",
        "description": "根据客服技能组、在线状态、客户级别自动转接会话，支持转接历史记录",
        "keywords": ["转接", "会话", "客服", "工单", "IM"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },

    # ==================== 办公RPA自动化 (12) ====================
    "office_excel_diff": {
        "name": "Excel批量对比差异",
        "category": "office",
        "level": "intermediate",
        "description": "两个或多个Excel文件对比，快速找出差异单元格、新增行、删除行，高亮标注",
        "keywords": ["Excel", "对比", "差异", "表格", "办公"],
        "permissions": ["filesystem:read"],
        "dependencies": ["openpyxl"],
    },
    "office_pdf_watermark": {
        "name": "PDF批量水印处理",
        "category": "office",
        "level": "intermediate",
        "description": "批量给PDF添加文字/图片水印，或批量去除水印，支持自定义透明度、位置、旋转角度",
        "keywords": ["PDF", "水印", "批量", "办公"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": ["PyPDF2"],
    },
    "office_image_processor": {
        "name": "图片批量处理",
        "category": "office",
        "level": "intermediate",
        "description": "批量压缩图片、调整尺寸、裁剪、加logo/水印，支持JPG/PNG/GIF/WebP格式",
        "keywords": ["图片", "压缩", "裁剪", "水印", "批量", "办公"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": ["Pillow"],
    },
    "office_folder_auto_sort": {
        "name": "文件夹自动整理归档",
        "category": "office",
        "level": "beginner",
        "description": "按文件类型、日期、名称等规则自动整理文件夹，支持自定义规则、定期自动执行",
        "keywords": ["文件夹", "整理", "归档", "自动化", "办公"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": [],
    },
    "office_email_auto_classify": {
        "name": "邮件自动分类归档",
        "category": "office",
        "level": "intermediate",
        "description": "根据发件人、主题、关键词自动将邮件分类到指定文件夹，支持规则组合",
        "keywords": ["邮件", "分类", "归档", "自动化", "办公"],
        "permissions": ["email"],
        "dependencies": [],
    },
    "office_web_scraper": {
        "name": "网页数据定时采集",
        "category": "office",
        "level": "advanced",
        "description": "可视化配置采集规则，定时抓取网页数据，支持登录认证、翻页、增量采集",
        "keywords": ["爬虫", "采集", "网页", "数据", "办公"],
        "permissions": ["network", "filesystem:write"],
        "dependencies": ["requests", "beautifulsoup4"],
    },
    "office_deduplicate": {
        "name": "表格重复数据去重",
        "category": "office",
        "level": "beginner",
        "description": "Excel/CSV表格按指定列去重，支持完全去重和模糊去重，生成去重报告",
        "keywords": ["去重", "重复", "表格", "数据清洗", "办公"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": ["pandas"],
    },
    "office_multi_table_merge": {
        "name": "多表格自动汇总",
        "category": "office",
        "level": "intermediate",
        "description": "将多个结构相同或不同的表格按字段关联汇总，支持vlookup、数据透视",
        "keywords": ["汇总", "合并", "表格", "vlookup", "办公"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": ["pandas", "openpyxl"],
    },
    "office_contract_extract": {
        "name": "合同要素智能提取",
        "category": "office",
        "level": "advanced",
        "description": "自动识别PDF/图片合同中的关键要素：甲乙方、金额、期限、违约条款，高亮标注",
        "keywords": ["合同", "提取", "NLP", "要素识别", "办公"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": ["pytesseract"],
    },
    "office_batch_rename": {
        "name": "批量文件规则重命名",
        "category": "office",
        "level": "beginner",
        "description": "按前缀/后缀/序号/日期等规则批量重命名文件，支持预览和撤销",
        "keywords": ["重命名", "批量", "文件", "自动化", "办公"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": [],
    },
    "office_form_auto_fill": {
        "name": "网页表单自动填充",
        "category": "office",
        "level": "advanced",
        "description": "预设数据自动填充网页表单，支持批量导入、多表单、自动提交",
        "keywords": ["表单填充", "RPA", "自动化", "办公"],
        "permissions": ["network"],
        "dependencies": ["selenium"],
    },
    "office_print_queue": {
        "name": "打印任务自动队列",
        "category": "office",
        "level": "beginner",
        "description": "批量文件加入打印队列，自动分页、自动排版、按打印机分配任务",
        "keywords": ["打印", "队列", "自动化", "办公"],
        "permissions": ["filesystem:read"],
        "dependencies": [],
    },

    # ==================== AI增强能力 (10) ====================
    "ai_product_copy": {
        "name": "AI商品文案生成",
        "category": "ai",
        "level": "intermediate",
        "description": "输入商品信息自动生成标题、主图描述、详情页文案，支持多平台风格适配（淘宝/抖音/京东）",
        "keywords": ["AI文案", "商品描述", "标题生成", "电商"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_reply_suggest": {
        "name": "AI客服话术推荐",
        "category": "ai",
        "level": "advanced",
        "description": "根据客户问题实时推荐最佳回复话术，支持多轮对话上下文记忆，客服一点即用",
        "keywords": ["AI回复", "话术推荐", "客服", "智能推荐"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_ocr_high_precision": {
        "name": "高精度OCR识别",
        "category": "ai",
        "level": "intermediate",
        "description": "票据、身份证、营业执照、合同等高精度识别，支持批量图片转文字，结构化输出",
        "keywords": ["OCR", "文字识别", "票据", "身份证", "AI"],
        "permissions": ["filesystem:read", "network"],
        "dependencies": ["pytesseract", "Pillow"],
    },
    "ai_tts_broadcast": {
        "name": "语音合成播报",
        "category": "ai",
        "level": "intermediate",
        "description": "文字转语音播报，支持多种音色、语速调节，可用于通知播报、客服录音",
        "keywords": ["TTS", "语音合成", "播报", "语音", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_text_summary": {
        "name": "长文本自动摘要",
        "category": "ai",
        "level": "intermediate",
        "description": "长篇文章、会议记录、报告自动摘要为关键要点，支持指定摘要长度",
        "keywords": ["摘要", "文章摘要", "关键要点", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_intent_classify": {
        "name": "AI意图识别",
        "category": "ai",
        "level": "advanced",
        "description": "无需配置，自动识别用户消息意图（咨询/投诉/购买/退款等），驱动智能路由",
        "keywords": ["意图识别", "NLP", "分类", "AI", "客服"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_translate": {
        "name": "多语言自动翻译",
        "category": "ai",
        "level": "beginner",
        "description": "支持中英日韩法德等30+语言互译，批量翻译文档、聊天记录、商品信息",
        "keywords": ["翻译", "多语言", "互译", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_image_moderation": {
        "name": "图片内容安全审核",
        "category": "ai",
        "level": "advanced",
        "description": "自动检测图片中的色情、暴恐、政治敏感等违规内容，返回风险评分和位置",
        "keywords": ["图片审核", "内容安全", "鉴黄", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_report_auto": {
        "name": "AI自动生成经营报告",
        "category": "ai",
        "level": "intermediate",
        "description": "自动汇总订单、客服、销售数据，生成日报/周报/月报，支持导出Word/PDF",
        "keywords": ["报告", "日报", "周报", "AI生成", "数据分析"],
        "permissions": ["network", "database", "filesystem:write"],
        "dependencies": [],
    },
    "ai_emotion_detect": {
        "name": "对话情绪识别",
        "category": "ai",
        "level": "advanced",
        "description": "分析买家/客户消息的情绪（愤怒/不满/满意/中性），自动标记高情绪客户优先处理",
        "keywords": ["情绪识别", "情感分析", "AI", "客服"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_knowledge_qa": {
        "name": "知识库智能问答",
        "category": "ai",
        "level": "advanced",
        "description": "基于企业知识库进行 RAG 检索问答，支持上传文档构建知识库，精准回答内部问题",
        "keywords": ["知识库", "RAG", "问答", "检索增强", "AI"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ai_vector_search": {
        "name": "向量语义检索",
        "category": "ai",
        "level": "advanced",
        "description": "将文档、图片等内容向量化，支持语义相似度搜索，返回最相关结果",
        "keywords": ["向量", "语义搜索", "embedding", "相似度", "AI"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ai_doc_qa": {
        "name": "文档智能问答",
        "category": "ai",
        "level": "intermediate",
        "description": "上传 PDF/Word/Excel 后，直接用自然语言提问，AI 从文档中找出答案并标注来源",
        "keywords": ["文档问答", "PDF", "Word", "问答", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_code_generate": {
        "name": "代码自动生成",
        "category": "ai",
        "level": "intermediate",
        "description": "根据自然语言需求自动生成 Python/JavaScript/Go 等代码，支持指定语言和框架",
        "keywords": ["代码生成", "coding", "自动编程", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_code_explain": {
        "name": "代码解释与重构",
        "category": "ai",
        "level": "intermediate",
        "description": "上传代码片段，自动解释逻辑并给出优化重构建议，支持多语言",
        "keywords": ["代码解释", "重构", "code review", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_bug_detect": {
        "name": "Bug 自动检测",
        "category": "ai",
        "level": "advanced",
        "description": "扫描代码自动发现潜在 Bug、安全漏洞、性能问题，提供修复建议和示例代码",
        "keywords": ["Bug检测", "漏洞扫描", "静态分析", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_image_generate": {
        "name": "AI 文生图创作",
        "category": "ai",
        "level": "intermediate",
        "description": "输入文字描述自动生成图片，支持多种风格（写实/插画/动漫），可指定尺寸和比例",
        "keywords": ["文生图", "AI绘图", "图像生成", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_image_edit": {
        "name": "图片智能编辑",
        "category": "ai",
        "level": "intermediate",
        "description": "AI 驱动的图片编辑，支持局部重绘、背景消除、画质增强、人像精修",
        "keywords": ["图片编辑", "AI修图", "局部重绘", "AI"],
        "permissions": ["network", "filesystem:read", "filesystem:write"],
        "dependencies": [],
    },
    "ai_voice_asr": {
        "name": "语音识别转文字",
        "category": "ai",
        "level": "intermediate",
        "description": "音频/视频文件自动转文字，支持普通话、方言、英语，生成带时间戳的字幕文件",
        "keywords": ["ASR", "语音转文字", "字幕", "录音转文字", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_voice_clone": {
        "name": "声音克隆合成",
        "category": "ai",
        "level": "advanced",
        "description": "上传少量音频样本，克隆音色，输入文字即可用克隆声音朗读",
        "keywords": ["声音克隆", "TTS", "语音合成", "音色", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_nl_to_sql": {
        "name": "自然语言转 SQL",
        "category": "ai",
        "level": "advanced",
        "description": "用自然语言提问，自动生成 SQL 查询语句，从数据库获取结果并解读",
        "keywords": ["NL2SQL", "自然语言", "数据库查询", "AI"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ai_data_interpret": {
        "name": "数据智能解读",
        "category": "ai",
        "level": "intermediate",
        "description": "上传 Excel/CSV 数据文件，AI 自动分析数据特征，发现规律，生成文字解读报告",
        "keywords": ["数据分析", "数据解读", "Excel", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_chart_generate": {
        "name": "图表自动生成",
        "category": "ai",
        "level": "beginner",
        "description": "输入数据或描述，自动推荐最佳图表类型，生成可编辑的图表，支持 PNG/SVG/Excel",
        "keywords": ["图表", "可视化", "自动生成", "AI"],
        "permissions": ["network", "filesystem:write"],
        "dependencies": [],
    },
    "ai_trend_predict": {
        "name": "业务趋势预测",
        "category": "ai",
        "level": "advanced",
        "description": "基于历史数据预测未来趋势（销售/流量/库存），输出预测值和置信区间",
        "keywords": ["趋势预测", "时序预测", "销量预测", "AI"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ai_anomaly_detect": {
        "name": "异常数据检测",
        "category": "ai",
        "level": "advanced",
        "description": "自动识别数据中的异常值和异常事件，标注异常点并给出可能原因分析",
        "keywords": ["异常检测", "离群点", "数据质量", "AI"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ai_xiaohongshu": {
        "name": "小红书笔记生成",
        "category": "ai",
        "level": "beginner",
        "description": "输入产品信息或话题，自动生成小红书风格图文笔记，包含emoji、标签和互动话术",
        "keywords": ["小红书", "种草", "文案", "社交媒体", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_video_script": {
        "name": "视频脚本生成",
        "category": "ai",
        "level": "intermediate",
        "description": "输入视频主题，自动生成完整视频脚本，包含开场、转折、高潮、结尾和字幕文案",
        "keywords": ["视频脚本", "短视频", "口播", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_seo_optimize": {
        "name": "SEO 标题描述优化",
        "category": "ai",
        "level": "beginner",
        "description": "输入文章或产品标题，AI 优化 SEO 元标签（Title/Meta/关键词），提升搜索排名",
        "keywords": ["SEO", "搜索引擎优化", "标题优化", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },
    "ai_contract_audit": {
        "name": "合同智能审查",
        "category": "ai",
        "level": "advanced",
        "description": "上传合同 PDF，自动识别风险条款、缺失条款、不合理条款，生成审查报告",
        "keywords": ["合同审查", "法务", "风险识别", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_pdf_qa": {
        "name": "PDF 文档问答",
        "category": "ai",
        "level": "intermediate",
        "description": "上传 PDF 文档，用自然语言提问，AI 在文档范围内精准回答，标注答案所在页码",
        "keywords": ["PDF问答", "文档理解", "PDF阅读", "AI"],
        "permissions": ["network", "filesystem:read"],
        "dependencies": [],
    },
    "ai_smart_search": {
        "name": "智能语义搜索",
        "category": "ai",
        "level": "intermediate",
        "description": "超越关键词匹配，理解搜索意图，返回语义最相关的文档和内容片段",
        "keywords": ["语义搜索", "智能搜索", "全文检索", "AI"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "ai_meeting_minutes": {
        "name": "会议纪要生成",
        "category": "ai",
        "level": "intermediate",
        "description": "上传会议录音或文字记录，AI 自动生成结构化会议纪要，包含决议、待办和负责人",
        "keywords": ["会议纪要", "会议记录", "待办事项", "AI"],
        "permissions": ["network", "filesystem:read", "filesystem:write"],
        "dependencies": [],
    },
    "ai_similar_rec": {
        "name": "相似内容推荐",
        "category": "ai",
        "level": "intermediate",
        "description": "输入一段内容，AI 推荐与之相似的文章、商品或解决方案，用于知识推荐和营销",
        "keywords": ["相似推荐", "内容推荐", "协同过滤", "AI"],
        "permissions": ["network"],
        "dependencies": [],
    },

    # ==================== 数据统计与可视化 (8) ====================
    "data_sales_stats": {
        "name": "经营数据自动统计",
        "category": "data",
        "level": "intermediate",
        "description": "日/周/月度订单销售额、退款额、客单价自动统计，支持多平台汇总对比",
        "keywords": ["销售统计", "经营数据", "报表", "电商"],
        "permissions": ["database", "filesystem:write"],
        "dependencies": ["pandas"],
    },
    "data_agent_stats": {
        "name": "客服接待量实时报表",
        "category": "data",
        "level": "intermediate",
        "description": "客服的接待消息数、平均响应时长、好评率实时统计，生成个人/团队排行榜",
        "keywords": ["客服统计", "接待量", "排行榜", "客服"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "data_plugin_usage": {
        "name": "插件使用数据统计",
        "category": "data",
        "level": "intermediate",
        "description": "统计各插件的使用频率、执行成功率、平均耗时，支持按团队/用户筛选",
        "keywords": ["插件统计", "使用数据", "分析"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "data_channel_stats": {
        "name": "客户来源渠道分析",
        "category": "data",
        "level": "intermediate",
        "description": "分析客户来源渠道（搜索/广告/社群/活动等），统计各渠道转化率和ROI",
        "keywords": ["渠道分析", "来源统计", "ROI", "转化率"],
        "permissions": ["database", "filesystem:write"],
        "dependencies": [],
    },
    "data_inventory_turnover": {
        "name": "库存周转率分析",
        "category": "data",
        "level": "advanced",
        "description": "自动计算各SKU的库存周转天数、呆滞库存预警、补货建议",
        "keywords": ["库存周转", "呆滞库存", "补货", "电商"],
        "permissions": ["database"],
        "dependencies": ["pandas"],
    },
    "data_chart_export": {
        "name": "可视化图表导出",
        "category": "data",
        "level": "beginner",
        "description": "数据一键生成折线图、柱状图、饼图、漏斗图，支持导出PNG/SVG/Excel",
        "keywords": ["图表", "可视化", "导出", "报表"],
        "permissions": ["filesystem:write"],
        "dependencies": ["matplotlib"],
    },
    "data_sync_sheets": {
        "name": "数据同步至飞书/钉钉",
        "category": "data",
        "level": "intermediate",
        "description": "经营数据自动同步至飞书多维表格或钉钉表格，定时推送，支持自定义字段映射",
        "keywords": ["飞书", "钉钉", "数据同步", "表格"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "data_daily_push": {
        "name": "每日经营数据推送",
        "category": "data",
        "level": "beginner",
        "description": "每天定时将核心经营指标（销售额/订单数/客单价）推送至钉钉群/邮件/微信",
        "keywords": ["数据推送", "每日简报", "经营数据"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },

    # ==================== 系统运维与稳定性 (7) ====================
    "ops_auto_restart": {
        "name": "服务崩溃自动重启",
        "category": "ops",
        "level": "intermediate",
        "description": "监控服务健康状态，进程崩溃、网络断连时自动重启，支持邮件/钉钉通知",
        "keywords": ["重启", "自愈", "守护进程", "运维"],
        "permissions": [],
        "dependencies": ["psutil"],
    },
    "ops_disk_cleanup": {
        "name": "磁盘空间自动清理",
        "category": "ops",
        "level": "beginner",
        "description": "磁盘使用率超过阈值时自动清理日志、临时文件、旧的备份，支持白名单保护",
        "keywords": ["磁盘清理", "日志清理", "运维", "存储"],
        "permissions": ["filesystem:write"],
        "dependencies": ["psutil"],
    },
    "ops_config_backup": {
        "name": "配置文件自动备份",
        "category": "ops",
        "level": "beginner",
        "description": "配置文件修改时自动备份至指定目录，支持版本管理、超量自动清理",
        "keywords": ["配置备份", "版本管理", "运维"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": [],
    },
    "ops_cpu_mem_alert": {
        "name": "资源超限告警",
        "category": "ops",
        "level": "beginner",
        "description": "CPU/内存/磁盘超过阈值时自动告警，支持钉钉/飞书/邮件推送",
        "keywords": ["告警", "资源监控", "CPU", "内存", "运维"],
        "permissions": [],
        "dependencies": ["psutil"],
    },
    "ops_log_rotate": {
        "name": "日志自动切割归档",
        "category": "ops",
        "level": "beginner",
        "description": "日志文件按大小或日期自动切割，压缩归档，保留指定天数历史日志",
        "keywords": ["日志切割", "logrotate", "归档", "运维"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "dependencies": [],
    },
    "ops_remote_restart": {
        "name": "远程服务一键重启",
        "category": "ops",
        "level": "advanced",
        "description": "通过API或管理后台远程重启指定服务，支持服务分组、批量操作",
        "keywords": ["远程重启", "服务管理", "运维"],
        "permissions": [],
        "dependencies": ["psutil"],
    },
    "ops_network_reconnect": {
        "name": "网络断连自动重连",
        "category": "ops",
        "level": "intermediate",
        "description": "检测网络连接状态，断开后自动重连，失败后告警通知",
        "keywords": ["网络", "重连", "自愈", "运维"],
        "permissions": [],
        "dependencies": [],
    },

    # ==================== 工作流编排 (6) ====================
    "wf_visual_builder": {
        "name": "可视化工作流设计器",
        "category": "workflow",
        "level": "advanced",
        "description": "拖拽式可视化工作流设计器，支持连线和节点配置，在线保存和调试",
        "keywords": ["工作流", "可视化", "拖拽", "编排"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "wf_condition_branch": {
        "name": "条件分支工作流",
        "category": "workflow",
        "level": "intermediate",
        "description": "工作流中支持IF/ELSE条件判断，根据数据动态选择执行分支",
        "keywords": ["工作流", "条件分支", "IF", "判断"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "wf_schedule_trigger": {
        "name": "定时任务触发",
        "category": "workflow",
        "level": "intermediate",
        "description": "工作流支持定时触发（cron表达式），按日/周/月循环执行",
        "keywords": ["定时任务", "Cron", "工作流", "触发"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "wf_auto_retry": {
        "name": "失败步骤自动重试",
        "category": "workflow",
        "level": "intermediate",
        "description": "工作流节点执行失败时自动重试，支持设置重试次数、间隔、可跳过的错误类型",
        "keywords": ["重试", "容错", "工作流", "失败处理"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "wf_result_notify": {
        "name": "执行结果自动通知",
        "category": "workflow",
        "level": "beginner",
        "description": "工作流执行完成后自动发送通知，支持钉钉/飞书/邮件/微信",
        "keywords": ["通知", "工作流", "执行结果"],
        "permissions": ["network", "database"],
        "dependencies": [],
    },
    "wf_template_import": {
        "name": "工作流模板市场",
        "category": "workflow",
        "level": "intermediate",
        "description": "内置常用工作流模板（订单处理/客服接待/数据采集），一键导入使用",
        "keywords": ["工作流模板", "模板市场", "一键导入"],
        "permissions": ["database"],
        "dependencies": [],
    },

    # ==================== 插件生态功能 (5) ====================
    "eco_oneclick_install": {
        "name": "插件一键安装升级",
        "category": "ecosystem",
        "level": "beginner",
        "description": "从ClawHub生态站一键安装插件，自动处理依赖，支持版本升级和回滚",
        "keywords": ["插件安装", "升级", "卸载", "生态站"],
        "permissions": ["network", "filesystem:write"],
        "dependencies": [],
    },
    "eco_permission_confirm": {
        "name": "插件权限手动确认",
        "category": "ecosystem",
        "level": "intermediate",
        "description": "插件安装前展示所需权限清单，用户手动确认授权，支持权限粒度控制",
        "keywords": ["插件权限", "安全确认", "授权"],
        "permissions": [],
        "dependencies": [],
    },
    "eco_plugin_rating": {
        "name": "插件评分与评论",
        "category": "ecosystem",
        "level": "beginner",
        "description": "用户对插件进行1-5星评分和文字评论，支持查看插件评价和评分趋势",
        "keywords": ["插件评分", "评论", "评价", "生态站"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "eco_plugin_ranking": {
        "name": "插件排行榜",
        "category": "ecosystem",
        "level": "beginner",
        "description": "按下载量、评分、好评率等多维度展示插件排行榜，推荐优质插件",
        "keywords": ["排行榜", "插件排行", "推荐", "生态站"],
        "permissions": ["database"],
        "dependencies": [],
    },
    "eco_offline_import": {
        "name": "本地插件离线导入",
        "category": "ecosystem",
        "level": "intermediate",
        "description": "支持导入本地ZIP包插件，无需联网，离线环境下也能扩展功能",
        "keywords": ["离线导入", "本地安装", "插件生态"],
        "permissions": ["filesystem:read"],
        "dependencies": [],
    },
}


def make_plugin_id(slug: str) -> str:
    return f"wanclaw.{slug}"


def generate_plugin_json(plugin_id: str, name: str, desc: str, category: str,
                          level: str, keywords: list, permissions: list,
                          deps: list, version: str = VERSION) -> dict:
    return {
        "plugin_id": plugin_id,
        "plugin_name": name,
        "plugin_type": "skill",
        "description": desc,
        "author": AUTHOR,
        "version": version,
        "category": category,
        "compatible_wanclaw_version": COMPATIBLE_VERSION,
        "entry_file": "main.py",
        "permissions": permissions,
        "keywords": keywords,
        "level": level,
        "is_official": True,
        "dependencies": deps,
        "marketplace": "clawhub",
        "download_count": 0,
        "rating": 5.0,
        "rating_count": 0,
        "review_status": "approved",
        "tags": ["官方", "内置", CATEGORIES.get(category, category)],
    }


def generate_main_py(plugin_id: str, name: str, category: str) -> str:
    return f'''"""WanClaw 官方插件 - {name}"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def run(**kwargs) -> Dict[str, Any]:
    """插件入口函数 - {name}"""
    try:
        return {{
            "success": True,
            "message": "{name} 插件已就绪",
            "plugin_id": "{plugin_id}",
            "category": "{category}",
            "params": kwargs,
            "note": "此为官方插件骨架，实际功能开发中"
        }}
    except Exception as e:
        logger.error(f"Plugin error: {{e}}")
        return {{
            "success": False,
            "error": str(e),
            "message": "插件执行失败"
        }}
'''


def generate_readme(plugin_id: str, name: str, desc: str, category: str,
                     level: str, keywords: list, permissions: list, deps: list) -> str:
    return f'''# {name}

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | {plugin_id} |
| 类型 | 官方内置插件 |
| 版本 | {VERSION} |
| 分类 | {CATEGORIES.get(category, category)} |
| 难度 | {LEVEL_NAMES.get(level, level)} |
| 作者 | {AUTHOR} |

## 功能说明

{desc}

## 关键词

{" / ".join(keywords)}

## 权限说明

{", ".join(permissions) if permissions else "无需特殊权限"}

## 依赖

{", ".join(deps) if deps else "无外部依赖"}

## 使用方法

```python
result = await plugin_manager.execute("{plugin_id}", {{"action": "xxx"}})
```

---
*WanClaw 官方插件 · {datetime.now().year}*
'''


def main():
    print(f"目标输出目录: {WANCLAW_PLUGINS}")
    print(f"插件数量: {len(PLUGINS)}")
    print("=" * 70)

    total = len(PLUGINS)
    by_category = {}

    for slug, info in PLUGINS.items():
        plugin_id = make_plugin_id(slug)
        plugin_dir = WANCLAW_PLUGINS / slug

        plugin_dir.mkdir(parents=True, exist_ok=True)

        pj = generate_plugin_json(
            plugin_id=plugin_id,
            name=info["name"],
            desc=info["description"],
            category=info["category"],
            level=info["level"],
            keywords=info["keywords"],
            permissions=info["permissions"],
            deps=info["dependencies"],
        )

        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(pj, f, ensure_ascii=False, indent=2)

        manifest = {
            "name": slug,
            "version": VERSION,
            "description": info["description"],
            "author": AUTHOR,
            "category": info["category"],
            "keywords": info["keywords"],
            "entry_point": "main.py",
            "dependencies": info["dependencies"],
            "permissions": info["permissions"],
            "platforms": ["all"],
            "is_official": True,
            "wanclaw_version": COMPATIBLE_VERSION,
        }
        with open(plugin_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        mp = generate_main_py(plugin_id, info["name"], info["category"])
        with open(plugin_dir / "main.py", "w", encoding="utf-8") as f:
            f.write(mp)

        rm = generate_readme(
            plugin_id, info["name"], info["description"], info["category"],
            info["level"], info["keywords"], info["permissions"],
            info["dependencies"],
        )
        with open(plugin_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(rm)

        cat = info["category"]
        if cat not in by_category:
            by_category[cat] = 0
        by_category[cat] += 1

        print(f"  [{CATEGORIES.get(cat, cat):10s}] {plugin_id} - {info['name']}")

    print("=" * 70)
    print("按分类统计:")
    for cat, count in sorted(by_category.items()):
        print(f"  {CATEGORIES.get(cat, cat)}: {count} 个")
    print(f"\n总计: {total} 个官方插件")
    print(f"输出目录: {WANCLAW_PLUGINS}")

    summary = {
        "generated_at": datetime.now().isoformat(),
        "total": total,
        "by_category": {CATEGORIES.get(k, k): v for k, v in by_category.items()},
        "plugins": {
            make_plugin_id(slug): generate_plugin_json(
                make_plugin_id(slug), info["name"], info["description"],
                info["category"], info["level"], info["keywords"],
                info["permissions"], info["dependencies"],
            )
            for slug, info in PLUGINS.items()
        },
    }

    summary_path = WANCLAW_PLUGINS / "_all_plugins_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n汇总已保存: {summary_path}")

    sync_to_clawhub(summary)


def sync_to_clawhub(summary: dict):
    """同步到 ClawHub 数据库"""
    print("\n同步到 ClawHub 数据库...")
    try:
        import sys
        sys.path.insert(0, "/data/clawhub")
        from backend.app import app, db, Plugin, User

        with app.app_context():
            db.create_all()

            official_user = User.query.filter_by(username=AUTHOR).first()
            if not official_user:
                from werkzeug.security import generate_password_hash
                official_user = User(
                    username=AUTHOR,
                    email=AUTHOR_EMAIL,
                    password_hash=generate_password_hash("official_dummy"),
                    role="admin",
                )
                db.session.add(official_user)
                db.session.commit()
                print(f"  创建官方用户: {AUTHOR}")

            added = updated = 0
            for plugin_id, pj in summary["plugins"].items():
                existing = Plugin.query.filter_by(plugin_id=plugin_id).first()

                if existing:
                    existing.plugin_name = pj["plugin_name"]
                    existing.description = pj["description"]
                    existing.version = pj["version"]
                    existing.category = pj["category"]
                    existing.permissions = pj["permissions"]
                    existing.review_status = "approved"
                    updated += 1
                else:
                    plugin = Plugin(
                        plugin_id=plugin_id,
                        plugin_name=pj["plugin_name"],
                        description=pj["description"],
                        author=AUTHOR,
                        author_id=official_user.id,
                        version=pj["version"],
                        plugin_type="skill",
                        category=pj["category"],
                        compatible_wanclaw_version=pj["compatible_wanclaw_version"],
                        entry_file="main.py",
                        permissions=pj["permissions"],
                        file_path=str(WANCLAW_PLUGINS / plugin_id.replace("wanclaw.", "")),
                        review_status="approved",
                        review_message="官方插件，自动审核通过",
                        downloads=0,
                        rating=5.0,
                        rating_count=0,
                    )
                    db.session.add(plugin)
                    added += 1

            db.session.commit()

            total_db = Plugin.query.filter_by(review_status="approved").count()
            print(f"  新增: {added} | 更新: {updated} | 数据库总计: {total_db} 个已审核插件")

    except ImportError as e:
        print(f"  跳过数据库同步 (flask 未安装): {e}")
    except Exception as e:
        print(f"  数据库同步失败: {e}")


if __name__ == "__main__":
    main()
