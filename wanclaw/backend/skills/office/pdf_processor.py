"""
PDF处理技能 V2.0
基于 pypdf + pdfplumber 实现真实文件操作
"""

import os
import logging
from typing import Dict, List, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel

logger = logging.getLogger(__name__)


class PDFProcessorSkill(BaseSkill):
    
    def __init__(self):
        super().__init__()
        self.name = "PDFProcessor"
        self.description = "PDF处理：合并、拆分、加水印、加密、提取文字"
        self.category = SkillCategory.OFFICE
        self.level = SkillLevel.INTERMEDIATE
        self.required_params = ["action"]
        self.optional_params = {
            "file_path": str, "file_paths": list, "output_path": str,
            "output_dir": str, "convert_format": str, "page_range": str,
            "watermark_text": str, "watermark_image": str,
            "password": str, "encrypt": bool, "extract_images": bool,
            "ocr": bool, "quality": int
        }

    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        try:
            method = getattr(self, f"_action_{action}", None)
            if not method:
                return SkillResult(success=False, message=f"不支持的操作: {action}")
            return await method(params)
        except ImportError as e:
            return SkillResult(success=False, message=str(e), error=str(e))
        except Exception as e:
            logger.error(f"PDF处理失败: {action} - {e}")
            return SkillResult(success=False, message=f"PDF处理失败: {str(e)}", error=str(e))

    async def _load_pypdf(self):
        try:
            from pypdf import PdfReader, PdfWriter
            return {"reader": PdfReader, "writer": PdfWriter}
        except ImportError:
            try:
                from PyPDF2 import PdfReader, PdfWriter
                return {"reader": PdfReader, "writer": PdfWriter}
            except ImportError:
                raise ImportError("pypdf 未安装，请运行: pip install pypdf")

    async def _load_pdfplumber(self):
        try:
            import pdfplumber
            return pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed, using pypdf fallback")
            return None

    async def _action_merge(self, params: Dict) -> SkillResult:
        file_paths = params.get("file_paths", [])
        output_path = params.get("output_path", "merged_output.pdf")

        if len(file_paths) < 2:
            return SkillResult(success=False, message="合并需要至少2个PDF文件", error="need 2+ files")

        libs = await self._load_pypdf()
        PdfWriter = libs["writer"]
        writer = PdfWriter()
        total_pages = 0

        for fp in file_paths:
            if not os.path.exists(fp):
                continue
            reader = libs["reader"](fp)
            total_pages += len(reader.pages)
            for page in reader.pages:
                writer.add_page(page)

        writer.write(output_path)
        return SkillResult(
            success=True, message=f"合并完成，{len(file_paths)}个文件，共{total_pages}页",
            data={"source_files": file_paths, "output_file": output_path,
                  "total_pages": total_pages}
        )

    async def _action_split(self, params: Dict) -> SkillResult:
        file_path = params.get("file_path", "")
        page_range = params.get("page_range", "1-10")
        output_dir = params.get("output_dir", os.path.dirname(file_path) or ".")

        if not file_path or not os.path.exists(file_path):
            return SkillResult(success=False, message="文件不存在", error="file not found")

        libs = await self._load_pypdf()
        reader = libs["reader"](file_path)
        os.makedirs(output_dir, exist_ok=True)

        parts = page_range.split(",")
        output_files = []
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        for idx, part in enumerate(parts):
            part = part.strip()
            writer = libs["writer"]()
            if "-" in part:
                start, end = part.split("-")
                for p in range(int(start.strip()) - 1, min(int(end.strip()), len(reader.pages))):
                    writer.add_page(reader.pages[p])
            else:
                p = int(part.strip()) - 1
                if 0 <= p < len(reader.pages):
                    writer.add_page(reader.pages[p])
            out_file = os.path.join(output_dir, f"{base_name}_part{idx + 1}.pdf")
            writer.write(out_file)
            output_files.append(out_file)

        return SkillResult(
            success=True, message=f"拆分完成，生成{len(output_files)}个文件",
            data={"source_file": file_path, "page_range": page_range,
                  "output_files": output_files}
        )

    async def _action_watermark(self, params: Dict) -> SkillResult:
        file_path = params.get("file_path", "")
        watermark_text = params.get("watermark_text", "CONFIDENTIAL")
        output_path = params.get("output_path", file_path.replace(".pdf", "_watermarked.pdf"))

        if not file_path or not os.path.exists(file_path):
            return SkillResult(success=False, message="文件不存在", error="file not found")

        libs = await self._load_pypdf()
        reader = libs["reader"](file_path)
        writer = libs["writer"]()

        for page in reader.pages:
            writer.add_page(page)
            page.merge_page(page)
            writer.add_annotation(
                page,
                {
                    "type": "/FreeText",
                    "contents": watermark_text,
                    "rect": [100, 700, 500, 750],
                }
            )

        writer.write(output_path)
        return SkillResult(
            success=True, message=f"添加水印完成: {watermark_text}",
            data={"source_file": file_path, "output_file": output_path,
                  "watermark_text": watermark_text}
        )

    async def _action_encrypt(self, params: Dict) -> SkillResult:
        file_path = params.get("file_path", "")
        password = params.get("password", "")
        output_path = params.get("output_path", file_path.replace(".pdf", "_encrypted.pdf"))

        if not file_path or not os.path.exists(file_path):
            return SkillResult(success=False, message="文件不存在", error="file not found")
        if not password:
            return SkillResult(success=False, message="需要提供密码", error="password required")

        libs = await self._load_pypdf()
        reader = libs["reader"](file_path)
        writer = libs["writer"]()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(password)
        writer.write(output_path)

        return SkillResult(
            success=True, message="PDF加密完成",
            data={"source_file": file_path, "output_file": output_path,
                  "encrypted": True, "password_set": True}
        )

    async def _action_decrypt(self, params: Dict) -> SkillResult:
        file_path = params.get("file_path", "")
        password = params.get("password", "")
        output_path = params.get("output_path", file_path.replace(".pdf", "_decrypted.pdf"))

        if not file_path or not os.path.exists(file_path):
            return SkillResult(success=False, message="文件不存在", error="file not found")

        libs = await self._load_pypdf()
        reader = libs["reader"](file_path)

        if reader.is_encrypted:
            if not reader.decrypt(password):
                return SkillResult(success=False, message="密码错误", error="wrong password")

        writer = libs["writer"]()
        for page in reader.pages:
            writer.add_page(page)
        writer.write(output_path)

        return SkillResult(
            success=True, message="PDF解密完成",
            data={"source_file": file_path, "output_file": output_path, "decrypted": True}
        )

    async def _action_extract_text(self, params: Dict) -> SkillResult:
        file_path = params.get("file_path", "")
        ocr = params.get("ocr", False)

        if not file_path or not os.path.exists(file_path):
            return SkillResult(success=False, message="文件不存在", error="file not found")

        pdfplumber = await self._load_pdfplumber()

        if pdfplumber and not ocr:
            with pdfplumber.open(file_path) as pdf:
                all_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                full_text = "\n\n".join(all_text)
        else:
            libs = await self._load_pypdf()
            reader = libs["reader"](file_path)
            all_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)
            full_text = "\n\n".join(all_text)

        return SkillResult(
            success=True, message="文本提取完成",
            data={"source_file": file_path, "extracted_text": full_text,
                  "text_length": len(full_text), "ocr_used": ocr}
        )

    async def _action_info(self, params: Dict) -> SkillResult:
        file_path = params.get("file_path", "")

        if not file_path or not os.path.exists(file_path):
            return SkillResult(success=False, message="文件不存在", error="file not found")

        libs = await self._load_pypdf()
        reader = libs["reader"](file_path)

        info = {
            "source_file": file_path,
            "pages": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "metadata": {},
        }

        if reader.metadata:
            info["metadata"] = {
                k: str(v) for k, v in reader.metadata.items()
            }

        pdfplumber = await self._load_pdfplumber()
        if pdfplumber:
            with pdfplumber.open(file_path) as pdf:
                info["page_width"] = pdf.pages[0].width if pdf.pages else 0
                info["page_height"] = pdf.pages[0].height if pdf.pages else 0

        return SkillResult(success=True, message=f"PDF信息: {len(reader.pages)} 页", data=info)
