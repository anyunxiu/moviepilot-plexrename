from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.models import FileType, RenameRequest, RenameResponse, RecommendedName
from app.services.namer import Namer
from app.services.recognizer import NameRecognizer

transfer_router = APIRouter()
storage_router = APIRouter()


@transfer_router.get("/name", response_model=RecommendedName, summary="查询整理后的名称")
def query_name(path: str = Query(..., description="文件或目录完整路径"),
               filetype: FileType = Query(..., description="file 或 dir")) -> Any:
    target = Path(path).expanduser()
    if not target.exists():
        return RecommendedName(success=False, message="路径不存在")

    recognizer = NameRecognizer()
    media = recognizer.recognize(target)
    if not media:
        return RecommendedName(success=False, message="未识别到媒体信息")

    namer = Namer()
    new_path = namer.render(media, target)
    if not new_path:
        return RecommendedName(success=False, message="未生成重命名路径")

    new_name = new_path.name if filetype == FileType.file else new_path.name
    return RecommendedName(success=True, name=new_name)


@storage_router.post("/rename", response_model=RenameResponse, summary="重命名文件或目录")
def rename(req: RenameRequest) -> Any:
    target = Path(req.path).expanduser()
    if not target.exists():
        return RenameResponse(success=False, message="路径不存在")

    try:
        target.rename(target.with_name(req.new_name))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"重命名失败: {exc}") from exc

    # 递归处理子文件（仅媒体文件）时，使用识别+命名
    if req.recursive and target.is_dir():
        recognizer = NameRecognizer()
        namer = Namer()
        for child in target.with_name(req.new_name).rglob("*"):
            if child.is_dir():
                continue
            media = recognizer.recognize(child)
            if not media:
                continue
            new_path = namer.render(media, child)
            if new_path and new_path.name != child.name:
                try:
                    child.rename(child.with_name(new_path.name))
                except Exception:
                    # 忽略单个文件错误
                    continue

    return RenameResponse(success=True, message="重命名完成")
