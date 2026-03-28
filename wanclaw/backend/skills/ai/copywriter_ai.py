"""
AI文案生成技能
广告语、朋友圈文案、产品介绍、邮件模板、报价单模板生成
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class CopywriterAISkill(BaseSkill):
    """AI文案生成技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "CopywriterAI"
        self.description = "AI文案生成：广告语、朋友圈文案、产品介绍、邮件模板、报价单模板生成"
        self.category = SkillCategory.AI
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "content_type": str,
            "product_name": str,
            "keywords": list,
            "tone": str,
            "length": str,
            "audience": str,
            "language": str,
            "template": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "generate":
                return await self._generate_copy(params)
            elif action == "ad_slogan":
                return await self._generate_ad_slogan(params)
            elif action == "朋友圈":
                return await self._generate_moments_copy(params)
            elif action == "product_intro":
                return await self._generate_product_intro(params)
            elif action == "email_template":
                return await self._generate_email_template(params)
            elif action == "quote_template":
                return await self._generate_quote_template(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"AI文案生成失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"AI文案生成失败: {str(e)}",
                error=str(e)
            )
    
    async def _generate_copy(self, params: Dict[str, Any]) -> SkillResult:
        content_type = params.get("content_type", "product_intro")
        product_name = params.get("product_name", "智能产品")
        tone = params.get("tone", "professional")
        language = params.get("language", "zh-CN")
        
        mock_copies = {
            "广告语": "✨{name}，让生活更智能！✨ 立即体验，开启未来科技新生活！".format(name=product_name),
            "朋友圈文案": "🔥【{name}新品上市】🔥\n\n用了{{一段时间}}真的绝了！💕\n强烈推荐给各位小伙伴~\n\n⭐推荐指数：{{5}}星\n\n#好物推荐 #科技生活 #种草".format(name=product_name),
            "产品介绍": "【{name}】产品介绍\n\n{{产品核心卖点}}\n\n产品规格：\n• {{规格1}}\n• {{规格2}}\n• {{规格3}}\n\n适用场景：{{场景描述}}\n\n立即购买：{{购买链接}}".format(name=product_name),
            "邮件模板": "尊敬的客户：\n\n您好！感谢您对{name}的关注。\n\n{{邮件内容}}\n\n如有任何疑问，欢迎随时联系我们。\n\n祝好！\n{{公司名称}}\n{{联系方式}}".format(name=product_name),
            "报价单模板": "{name} 报价单\n\n日期：{{报价日期}}\n报价单号：{{编号}}\n\n产品清单：\n| 产品 | 规格 | 数量 | 单价 | 金额 |\n|------|------|------|------|------|\n{{产品列表}} \n\n合计：{{总金额}}\n\n有效期：{{有效期限}}\n\n{{公司信息}}".format(name=product_name)
        }
        
        return SkillResult(
            success=True,
            message="文案生成完成",
            data={
                "content_type": content_type,
                "product_name": product_name,
                "tone": tone,
                "language": language,
                "copies": mock_copies,
                "generated_count": len(mock_copies),
                "note": "AI文案生成，当前返回模拟数据"
            }
        )
    
    async def _generate_ad_slogan(self, params: Dict[str, Any]) -> SkillResult:
        product_name = params.get("product_name", "产品")
        keywords = params.get("keywords", ["智能", "高效", "品质"])
        
        slogans = [
            "智能{name}，改变从现在开始！".format(name=product_name),
            "高效{name}，让效率飞起来！".format(name=product_name),
            "品质{name}，信赖之选！".format(name=product_name),
            "探索{name}的无限可能！".format(name=product_name),
            "选择{name}，选择美好生活！".format(name=product_name)
        ]
        
        return SkillResult(
            success=True,
            message=f"生成{len(slogans)}条广告语",
            data={
                "product_name": product_name,
                "keywords": keywords,
                "slogans": slogans,
                "count": len(slogans),
                "note": "广告语生成，当前返回模拟数据"
            }
        )
    
    async def _generate_moments_copy(self, params: Dict[str, Any]) -> SkillResult:
        content_type = params.get("content_type", "product")
        tone = params.get("tone", "casual")
        
        copies = [
            "🔥【新品推荐】{name}来了！✨\n\n用了{{一段时间}}真的爱上了💕\n强烈推荐给大家~🌟\n\n#好物分享 #种草 #{{标签}}".format(name=params.get("product_name", "这款产品")),
            "今天收到了{name}，开箱体验超棒！📦\n\n{{优点1}}\n{{优点2}}\n\n推荐指数：⭐⭐⭐⭐⭐\n\n#开箱 #{{标签}}".format(name=params.get("product_name", "产品")),
            "✨{name}使用心得✨\n\n用了{{多久}}，感觉{{效果}}\n真的太满意了！👍\n\n有需要的朋友可以私信我~".format(name=params.get("product_name", "这款好物"))
        ]
        
        return SkillResult(
            success=True,
            message=f"生成{len(copies)}条朋友圈文案",
            data={
                "content_type": content_type,
                "tone": tone,
                "copies": copies,
                "count": len(copies),
                "note": "朋友圈文案生成，当前返回模拟数据"
            }
        )
    
    async def _generate_product_intro(self, params: Dict[str, Any]) -> SkillResult:
        product_name = params.get("product_name", "产品")
        audience = params.get("audience", "企业客户")
        
        intro = f"""【{product_name}】产品介绍

一、产品概述
{product_name}是一款专为{audience}设计的{{产品类型}}，具有{{核心特点}}。

二、核心优势
• {{优势1}}
• {{优势2}}
• {{优势3}}

三、适用场景
{{场景1}}、{{场景2}}、{{场景3}}

四、规格参数
• {{参数1}}
• {{参数2}}
• {{参数3}}

五、客户案例
{{案例描述}}

六、购买方式
{{购买链接或联系方式}}

如有疑问，欢迎咨询！
"""
        
        return SkillResult(
            success=True,
            message="产品介绍生成完成",
            data={
                "product_name": product_name,
                "audience": audience,
                "intro": intro,
                "sections": ["概述", "优势", "场景", "规格", "案例", "购买"],
                "note": "产品介绍生成，当前返回模拟数据"
            }
        )
    
    async def _generate_email_template(self, params: Dict[str, Any]) -> SkillResult:
        template_type = params.get("template", "follow_up")
        product_name = params.get("product_name", "")
        
        templates = {
            "follow_up": f"""尊敬的[客户姓名]：

您好！我是{product_name or 'XX公司'}的小李。

此前与您沟通了关于{product_name or '我们的产品'}的合作事宜，不知您考虑得如何了？

如果您有任何疑问，欢迎随时联系我。

期待您的回复！

祝好！
[您的姓名]
[职位]
[公司名称]
[联系方式]""",
            "cold_outreach": f"""尊敬的[客户姓名]：

您好！

我是{product_name or 'XX公司'}的[您的姓名]。

了解到贵公司在{{行业}}领域发展迅速，我们{product_name or '的产品'}可能对您有所帮助。

{{产品/服务核心价值}}

如感兴趣，欢迎进一步沟通，我可以为您安排产品演示。

期待您的回复！

祝商祺！
[您的姓名]
[职位]
[公司名称]""",
            "thank_you": """尊敬的客户：

您好！

感谢您选择{product_name or '我们的产品'}！

为确保您获得最佳使用体验，我们将为您提供：
• 免费培训服务
• 专属客服支持
• 定期产品更新

如有任何问题，请随时联系您的专属客服。

祝使用愉快！

{product_name or 'XX公司'}团队"""
        }
        
        return SkillResult(
            success=True,
            message=f"生成邮件模板: {template_type}",
            data={
                "template_type": template_type,
                "templates": templates,
                "count": len(templates),
                "note": "邮件模板生成，当前返回模拟数据"
            }
        )
    
    async def _generate_quote_template(self, params: Dict[str, Any]) -> SkillResult:
        product_name = params.get("product_name", "")
        
        template = f"""报价单 QUOTATION

报价单位：{{公司名称}}
报价日期：{{日期}}
报价单号：{{编号}}
有效期限：{{有效期天数}}天

客户信息：
公司名称：{{客户公司}}
联系人：{{联系人}}
联系电话：{{电话}}

产品/服务报价：
--------------------------------------------------
序号 | 产品/服务 | 规格 | 数量 | 单价 | 金额
--------------------------------------------------
1    | {{产品1}} | {{规格}} | {{数量}} | {{单价}} | {{金额}}
2    | {{产品2}} | {{规格}} | {{数量}} | {{单价}} | {{金额}}
3    | {{产品3}} | {{规格}} | {{数量}} | {{单价}} | {{金额}}
--------------------------------------------------
                                    合计：{{总金额}}
                                   税率：{{税率}}%
                                  税额：{{税额}}
                              含税合计：{{含税金额}}
--------------------------------------------------

备注：
{{备注信息}}

支付方式：{{支付方式}}
交货期限：{{交货期限}}

如有任何疑问，请联系我：
电话：{{联系电话}}
邮箱：{{邮箱}}
地址：{{地址}}

{product_name or 'XX公司'}（盖章）
日期："""
        
        return SkillResult(
            success=True,
            message="报价单模板生成完成",
            data={
                "product_name": product_name,
                "template": template,
                "sections": ["头部信息", "客户信息", "产品清单", "合计", "备注", "签署"],
                "note": "报价单模板生成，当前返回模拟数据"
            }
        )
