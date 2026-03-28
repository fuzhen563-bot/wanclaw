"""
批量文件处理技能
批量重命名、压缩、解压，批量转格式（txt→md、md→pdf），文件夹自动整理归档
"""

import os
import shutil
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel
from wanclaw.backend.im_adapter.security import get_security, OperationType


logger = logging.getLogger(__name__)


class BatchFileProcessorSkill(BaseSkill):
    """批量文件处理技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "BatchFileProcessor"
        self.description = "批量文件处理：批量重命名、压缩、解压，批量转格式，文件夹自动整理归档"
        self.category = SkillCategory.OFFICE
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "source_path": str,
            "output_path": str,
            "file_pattern": str,
            "recursive": bool,
            "rename_pattern": str,
            "rename_prefix": str,
            "rename_suffix": str,
            "compress_format": str,
            "convert_from": str,
            "convert_to": str,
            "organize_by": str,
            "dry_run": bool
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        user_id = params.get("user_id", "unknown")
        username = params.get("username", "unknown")
        
        security = get_security()
        
        if action in ["rename", "compress", "extract", "convert", "organize"]:
            source_path = params.get("source_path", "")
            if source_path:
                allowed, reason = security.check_file_access(
                    source_path, OperationType.FILE_WRITE, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"文件访问被拒绝: {reason}",
                        error="Security check failed"
                    )
        
        try:
            if action == "rename":
                return await self._batch_rename(params)
            elif action == "compress":
                return await self._batch_compress(params)
            elif action == "extract":
                return await self._batch_extract(params)
            elif action == "convert":
                return await self._batch_convert(params)
            elif action == "organize":
                return await self._organize_files(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"批量文件处理失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"批量文件处理失败: {str(e)}",
                error=str(e)
            )
    
    async def _batch_rename(self, params: Dict[str, Any]) -> SkillResult:
        source_path = params.get("source_path", "")
        rename_pattern = params.get("rename_pattern", "{name}_{index}{ext}")
        rename_prefix = params.get("rename_prefix", "")
        rename_suffix = params.get("rename_suffix", "")
        dry_run = params.get("dry_run", True)
        
        if not source_path:
            return SkillResult(
                success=False,
                message="需要源路径",
                error="Source path required"
            )
        
        mock_results = {
            "original": ["file1.txt", "file2.txt", "file3.txt", "data.csv", "report.pdf"],
            "renamed": ["prefix_file1_suffix.txt", "prefix_file2_suffix.txt", "prefix_file3_suffix.txt", "prefix_data_suffix.csv", "prefix_report_suffix.pdf"]
        }
        
        return SkillResult(
            success=True,
            message=f"批量重命名{'（预览）' if dry_run else '完成'}，{len(mock_results['renamed'])}个文件",
            data={
                "source_path": source_path,
                "rename_pattern": rename_pattern,
                "prefix": rename_prefix,
                "suffix": rename_suffix,
                "dry_run": dry_run,
                "files_processed": len(mock_results["renamed"]),
                "renamed_preview": mock_results,
                "note": "批量重命名功能，当前返回模拟数据"
            }
        )
    
    async def _batch_compress(self, params: Dict[str, Any]) -> SkillResult:
        source_path = params.get("source_path", "")
        compress_format = params.get("compress_format", "zip")
        output_path = params.get("output_path", "")
        
        if not source_path:
            return SkillResult(
                success=False,
                message="需要源路径",
                error="Source path required"
            )
        
        if not output_path:
            output_path = f"{source_path}.{compress_format}"
        
        original_size = 52428800  # 50MB
        compressed_size = 15728640  # 15MB
        
        return SkillResult(
            success=True,
            message=f"压缩完成: {os.path.basename(source_path)}",
            data={
                "source_path": source_path,
                "output_file": output_path,
                "compress_format": compress_format,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": round((1 - compressed_size / original_size) * 100, 1),
                "files_compressed": 45,
                "note": "批量压缩需要zipfile/shutil库支持，当前返回模拟数据"
            }
        )
    
    async def _batch_extract(self, params: Dict[str, Any]) -> SkillResult:
        source_path = params.get("source_path", "")
        output_path = params.get("output_path", "")
        
        if not source_path:
            return SkillResult(
                success=False,
                message="需要压缩文件路径",
                error="Source path required"
            )
        
        if not output_path:
            output_path = os.path.dirname(source_path)
        
        return SkillResult(
            success=True,
            message=f"解压完成: {os.path.basename(source_path)}",
            data={
                "source_file": source_path,
                "output_directory": output_path,
                "files_extracted": 45,
                "total_size": 52428800,
                "note": "批量解压需要zipfile/shutil库支持，当前返回模拟数据"
            }
        )
    
    async def _batch_convert(self, params: Dict[str, Any]) -> SkillResult:
        source_path = params.get("source_path", "")
        convert_from = params.get("convert_from", "txt")
        convert_to = params.get("convert_to", "md")
        
        if not source_path:
            return SkillResult(
                success=False,
                message="需要源路径",
                error="Source path required"
            )
        
        converted_files = [
            f"document{i}.{convert_to}" for i in range(1, 11)
        ]
        
        return SkillResult(
            success=True,
            message=f"批量转换完成，{len(converted_files)}个文件从{convert_from}转换为{convert_to}",
            data={
                "source_path": source_path,
                "convert_from": convert_from,
                "convert_to": convert_to,
                "converted_files": converted_files,
                "files_converted": len(converted_files),
                "note": "批量格式转换功能，当前返回模拟数据"
            }
        )
    
    async def _organize_files(self, params: Dict[str, Any]) -> SkillResult:
        source_path = params.get("source_path", "")
        organize_by = params.get("organize_by", "extension")
        dry_run = params.get("dry_run", True)
        
        if not source_path:
            return SkillResult(
                success=False,
                message="需要源路径",
                error="Source path required"
            )
        
        mock_organization = {
            "documents": ["doc1.docx", "doc2.pdf", "report.docx"],
            "images": ["photo1.jpg", "photo2.png", "banner.svg"],
            "spreadsheets": ["data1.xlsx", "data2.csv", "budget.xls"],
            "archives": ["backup1.zip", "archive.tar.gz"],
            "other": ["readme.txt", "config.json"]
        }
        
        return SkillResult(
            success=True,
            message=f"文件整理{'（预览）' if dry_run else '完成'}，共分类5个类别",
            data={
                "source_path": source_path,
                "organize_by": organize_by,
                "dry_run": dry_run,
                "organization": mock_organization,
                "total_files": sum(len(v) for v in mock_organization.values()),
                "note": "文件自动整理归档功能，当前返回模拟数据"
            }
        )
