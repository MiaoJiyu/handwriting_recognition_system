"""
Common validators for API endpoints
"""
from fastapi import UploadFile, HTTPException, status


async def validate_upload_file(file: UploadFile, max_size: int) -> None:
    """
    验证上传的文件类型和大小

    Args:
        file: FastAPI UploadFile对象
        max_size: 最大文件大小（字节）

    Raises:
        HTTPException: 如果文件类型或大小不符合要求
    """
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能上传图片文件"
        )

    # 验证文件大小
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小不能超过 {max_size // (1024 * 1024)}MB"
            )

    # 重置文件指针到开头，以便后续读取
    await file.seek(0)
