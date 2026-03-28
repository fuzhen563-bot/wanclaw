"""
邮件处理技能
提供邮件发送、接收和处理功能
"""

import smtplib
import imaplib
import email
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import decode_header
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class EmailProcessorSkill(BaseSkill):
    """邮件处理技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "EmailProcessor"
        self.description = "邮件处理：发送、接收、搜索邮件"
        self.category = SkillCategory.OFFICE
        self.level = SkillLevel.INTERMEDIATE
        
        # 必需参数
        self.required_params = ["action"]
        
        # 可选参数及其类型
        self.optional_params = {
            "smtp_server": str,
            "smtp_port": int,
            "imap_server": str,
            "imap_port": int,
            "username": str,
            "password": str,
            "use_ssl": bool,
            "use_tls": bool,
            "from_email": str,
            "to_email": str,
            "subject": str,
            "body": str,
            "body_html": str,
            "attachments": list,
            "mailbox": str,
            "search_criteria": str,
            "max_emails": int,
            "email_id": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """
        执行邮件处理操作
        
        Args:
            params: {
                "action": "send|receive|search|delete|mark_read",
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "imap_server": "imap.example.com",
                "imap_port": 993,
                "username": "user@example.com",
                "password": "password",
                "use_ssl": true,
                "use_tls": true,
                "from_email": "sender@example.com",
                "to_email": "recipient@example.com",
                "subject": "邮件主题",
                "body": "邮件正文",
                "body_html": "<p>HTML邮件正文</p>",
                "attachments": ["file1.pdf", "file2.docx"],
                "mailbox": "INBOX",
                "search_criteria": "UNSEEN",
                "max_emails": 10,
                "email_id": "邮件ID"
            }
            
        Returns:
            执行结果
        """
        action = params.get("action", "").lower()
        
        try:
            if action == "send":
                return await self._send_email(params)
            elif action == "receive":
                return await self._receive_emails(params)
            elif action == "search":
                return await self._search_emails(params)
            elif action == "delete":
                return await self._delete_email(params)
            elif action == "mark_read":
                return await self._mark_email_read(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"邮件操作失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"邮件操作失败: {str(e)}",
                error=str(e)
            )
    
    async def _send_email(self, params: Dict[str, Any]) -> SkillResult:
        """发送邮件"""
        # 获取参数
        smtp_server = params.get("smtp_server", "smtp.gmail.com")
        smtp_port = params.get("smtp_port", 587)
        username = params.get("username", "")
        password = params.get("password", "")
        use_ssl = params.get("use_ssl", False)
        use_tls = params.get("use_tls", True)
        from_email = params.get("from_email", username)
        to_email = params.get("to_email", "")
        subject = params.get("subject", "")
        body = params.get("body", "")
        body_html = params.get("body_html", "")
        attachments = params.get("attachments", [])
        
        # 验证必需参数
        if not username or not password:
            return SkillResult(
                success=False,
                message="需要用户名和密码",
                error="Username and password required"
            )
        
        if not to_email:
            return SkillResult(
                success=False,
                message="需要收件人邮箱",
                error="Recipient email required"
            )
        
        try:
            # 创建邮件
            if body_html:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body, 'plain'))
                msg.attach(MIMEText(body_html, 'html'))
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body, 'plain'))
            
            # 设置邮件头
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Date'] = email.utils.formatdate()
            
            # 添加附件
            for attachment_path in attachments:
                try:
                    with open(attachment_path, 'rb') as f:
                        attachment = MIMEApplication(f.read())
                    
                    filename = attachment_path.split('/')[-1]
                    attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                    msg.attach(attachment)
                except Exception as e:
                    logger.warning(f"附件添加失败 {attachment_path}: {e}")
            
            # 连接SMTP服务器并发送邮件
            if use_ssl:
                # SSL连接
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                    server.login(username, password)
                    server.send_message(msg)
            else:
                # 普通连接
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    if use_tls:
                        server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
            
            return SkillResult(
                success=True,
                message=f"邮件发送成功: {subject}",
                data={
                    "from": from_email,
                    "to": to_email,
                    "subject": subject,
                    "attachments_count": len(attachments),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"邮件发送失败: {str(e)}",
                error=str(e)
            )
    
    async def _receive_emails(self, params: Dict[str, Any]) -> SkillResult:
        """接收邮件"""
        # 获取参数
        imap_server = params.get("imap_server", "imap.gmail.com")
        imap_port = params.get("imap_port", 993)
        username = params.get("username", "")
        password = params.get("password", "")
        mailbox = params.get("mailbox", "INBOX")
        max_emails = params.get("max_emails", 10)
        
        # 验证必需参数
        if not username or not password:
            return SkillResult(
                success=False,
                message="需要用户名和密码",
                error="Username and password required"
            )
        
        try:
            # 连接IMAP服务器
            mail = imaplib.IMAP4_SSL(imap_server, imap_port) if imap_port == 993 else imaplib.IMAP4(imap_server, imap_port)
            mail.login(username, password)
            mail.select(mailbox)
            
            # 搜索未读邮件
            result, data = mail.search(None, 'UNSEEN')
            if result != 'OK':
                mail.logout()
                return SkillResult(
                    success=False,
                    message="邮件搜索失败",
                    error="Email search failed"
                )
            
            email_ids = data[0].split()
            if not email_ids:
                mail.logout()
                return SkillResult(
                    success=True,
                    message="没有新邮件",
                    data={"emails": [], "total": 0}
                )
            
            # 限制获取数量
            email_ids = email_ids[:max_emails]
            emails = []
            
            for email_id in email_ids:
                try:
                    # 获取邮件
                    result, msg_data = mail.fetch(email_id, '(RFC822)')
                    if result != 'OK':
                        continue
                    
                    # 解析邮件
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # 解析邮件信息
                    email_info = self._parse_email(msg, email_id.decode())
                    emails.append(email_info)
                    
                except Exception as e:
                    logger.warning(f"解析邮件失败 {email_id}: {e}")
                    continue
            
            mail.logout()
            
            return SkillResult(
                success=True,
                message=f"获取到 {len(emails)} 封新邮件",
                data={
                    "emails": emails,
                    "total": len(emails),
                    "mailbox": mailbox
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"接收邮件失败: {str(e)}",
                error=str(e)
            )
    
    async def _search_emails(self, params: Dict[str, Any]) -> SkillResult:
        """搜索邮件"""
        # 获取参数
        imap_server = params.get("imap_server", "imap.gmail.com")
        imap_port = params.get("imap_port", 993)
        username = params.get("username", "")
        password = params.get("password", "")
        mailbox = params.get("mailbox", "INBOX")
        search_criteria = params.get("search_criteria", "ALL")
        max_emails = params.get("max_emails", 20)
        
        # 验证必需参数
        if not username or not password:
            return SkillResult(
                success=False,
                message="需要用户名和密码",
                error="Username and password required"
            )
        
        try:
            # 连接IMAP服务器
            mail = imaplib.IMAP4_SSL(imap_server, imap_port) if imap_port == 993 else imaplib.IMAP4(imap_server, imap_port)
            mail.login(username, password)
            mail.select(mailbox)
            
            # 搜索邮件
            result, data = mail.search(None, search_criteria)
            if result != 'OK':
                mail.logout()
                return SkillResult(
                    success=False,
                    message="邮件搜索失败",
                    error="Email search failed"
                )
            
            email_ids = data[0].split()
            if not email_ids:
                mail.logout()
                return SkillResult(
                    success=True,
                    message="没有找到邮件",
                    data={"emails": [], "total": 0}
                )
            
            # 限制获取数量
            email_ids = email_ids[:max_emails]
            emails = []
            
            for email_id in email_ids:
                try:
                    # 获取邮件
                    result, msg_data = mail.fetch(email_id, '(RFC822)')
                    if result != 'OK':
                        continue
                    
                    # 解析邮件
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # 解析邮件信息
                    email_info = self._parse_email(msg, email_id.decode())
                    emails.append(email_info)
                    
                except Exception as e:
                    logger.warning(f"解析邮件失败 {email_id}: {e}")
                    continue
            
            mail.logout()
            
            return SkillResult(
                success=True,
                message=f"搜索到 {len(emails)} 封邮件",
                data={
                    "emails": emails,
                    "total": len(emails),
                    "mailbox": mailbox,
                    "search_criteria": search_criteria
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"搜索邮件失败: {str(e)}",
                error=str(e)
            )
    
    async def _delete_email(self, params: Dict[str, Any]) -> SkillResult:
        """删除邮件"""
        # 获取参数
        imap_server = params.get("imap_server", "imap.gmail.com")
        imap_port = params.get("imap_port", 993)
        username = params.get("username", "")
        password = params.get("password", "")
        mailbox = params.get("mailbox", "INBOX")
        email_id = params.get("email_id", "")
        
        # 验证必需参数
        if not username or not password:
            return SkillResult(
                success=False,
                message="需要用户名和密码",
                error="Username and password required"
            )
        
        if not email_id:
            return SkillResult(
                success=False,
                message="需要邮件ID",
                error="Email ID required"
            )
        
        try:
            # 连接IMAP服务器
            mail = imaplib.IMAP4_SSL(imap_server, imap_port) if imap_port == 993 else imaplib.IMAP4(imap_server, imap_port)
            mail.login(username, password)
            mail.select(mailbox)
            
            # 标记邮件为删除
            mail.store(email_id, '+FLAGS', '\\Deleted')
            mail.expunge()
            mail.logout()
            
            return SkillResult(
                success=True,
                message="邮件删除成功",
                data={
                    "email_id": email_id,
                    "mailbox": mailbox
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"删除邮件失败: {str(e)}",
                error=str(e)
            )
    
    async def _mark_email_read(self, params: Dict[str, Any]) -> SkillResult:
        """标记邮件为已读"""
        # 获取参数
        imap_server = params.get("imap_server", "imap.gmail.com")
        imap_port = params.get("imap_port", 993)
        username = params.get("username", "")
        password = params.get("password", "")
        mailbox = params.get("mailbox", "INBOX")
        email_id = params.get("email_id", "")
        
        # 验证必需参数
        if not username or not password:
            return SkillResult(
                success=False,
                message="需要用户名和密码",
                error="Username and password required"
            )
        
        if not email_id:
            return SkillResult(
                success=False,
                message="需要邮件ID",
                error="Email ID required"
            )
        
        try:
            # 连接IMAP服务器
            mail = imaplib.IMAP4_SSL(imap_server, imap_port) if imap_port == 993 else imaplib.IMAP4(imap_server, imap_port)
            mail.login(username, password)
            mail.select(mailbox)
            
            # 标记邮件为已读
            mail.store(email_id, '+FLAGS', '\\Seen')
            mail.logout()
            
            return SkillResult(
                success=True,
                message="邮件标记为已读",
                data={
                    "email_id": email_id,
                    "mailbox": mailbox
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"标记邮件失败: {str(e)}",
                error=str(e)
            )
    
    def _parse_email(self, msg: email.message.Message, email_id: str) -> Dict[str, Any]:
        """解析邮件信息"""
        email_info = {
            "id": email_id,
            "subject": self._decode_header(msg.get('Subject', '')),
            "from": self._decode_header(msg.get('From', '')),
            "to": self._decode_header(msg.get('To', '')),
            "date": msg.get('Date', ''),
            "has_attachments": False,
            "attachments": [],
            "body_text": "",
            "body_html": "",
            "is_read": False
        }
        
        # 检查是否已读
        flags = msg.get('Flags', '')
        email_info["is_read"] = '\\Seen' in flags
        
        # 解析邮件内容
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # 附件
                if "attachment" in content_disposition:
                    email_info["has_attachments"] = True
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header(filename)
                        email_info["attachments"].append({
                            "filename": filename,
                            "content_type": content_type,
                            "size": len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0
                        })
                
                # 文本内容
                elif content_type == "text/plain" and not email_info["body_text"]:
                    body = part.get_payload(decode=True)
                    if body:
                        email_info["body_text"] = body.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                
                # HTML内容
                elif content_type == "text/html" and not email_info["body_html"]:
                    body = part.get_payload(decode=True)
                    if body:
                        email_info["body_html"] = body.decode(part.get_content_charset() or 'utf-8', errors='ignore')
        else:
            # 非多部分邮件
            content_type = msg.get_content_type()
            body = msg.get_payload(decode=True)
            
            if body:
                charset = msg.get_content_charset() or 'utf-8'
                body_text = body.decode(charset, errors='ignore')
                
                if content_type == "text/html":
                    email_info["body_html"] = body_text
                else:
                    email_info["body_text"] = body_text
        
        # 如果没有文本内容但有关HTML内容，从HTML中提取文本
        if not email_info["body_text"] and email_info["body_html"]:
            import re
            # 简单的HTML标签去除
            clean_text = re.sub(r'<[^>]+>', ' ', email_info["body_html"])
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            email_info["body_text"] = clean_text[:500] + "..." if len(clean_text) > 500 else clean_text
        
        # 截断长文本
        if len(email_info["body_text"]) > 500:
            email_info["body_text"] = email_info["body_text"][:500] + "..."
        
        if len(email_info["body_html"]) > 1000:
            email_info["body_html"] = email_info["body_html"][:1000] + "..."
        
        return email_info
    
    def _decode_header(self, header: str) -> str:
        """解码邮件头"""
        if not header:
            return ""
        
        try:
            decoded_parts = decode_header(header)
            decoded_str = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_str += part.decode(encoding, errors='ignore')
                    else:
                        decoded_str += part.decode('utf-8', errors='ignore')
                else:
                    decoded_str += part
            
            return decoded_str
        except:
            return str(header)