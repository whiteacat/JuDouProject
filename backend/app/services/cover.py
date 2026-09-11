"""活动封面图预设白名单。

封面不允许用户上传，只能从预设列表中选择。
后端保存 `preset://cover/X` 形式的协议 URL，
小程序端将其映射为本地图片路径展示。
"""

from typing import Optional

# 预设封面白名单：preset://cover/NN 对应
# 小程序 assets/activity_cover_assets/activity_cover_NN.png
PRESET_COVERS: list[str] = [f"preset://cover/{i:02d}" for i in range(1, 31)]


def validate_cover_url(cover_url: Optional[str]) -> Optional[str]:
    """校验封面 URL 是否在白名单内。

    Returns:
        校验通过的 cover_url；传入 None/空串时返回 None；
        不在白名单时抛出 HTTPException。
    """
    from fastapi import HTTPException, status as http_status

    if cover_url is None or cover_url == "":
        return None
    if cover_url not in PRESET_COVERS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="封面图只能从预设中选择",
        )
    return cover_url
