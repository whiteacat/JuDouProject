"""活动/群组封面图预设白名单。

封面不允许用户上传，只能从预设列表中选择。
后端保存 `preset://cover/X` 形式的协议 URL，
小程序端将其映射为本地图片路径展示。
"""

from typing import Optional

# 预设活动封面白名单：preset://cover/NN 对应
# 小程序 assets/activity_cover_assets/activity_cover_NN.png
PRESET_COVERS: list[str] = [f"preset://cover/{i:02d}" for i in range(1, 31)]

# 预设群组封面（详情页背景）白名单：preset://group_cover/NN 对应
# 小程序 assets/group_cover_assets/group_cover_NN.png
PRESET_GROUP_COVERS: list[str] = [
    f"preset://group_cover/{i:02d}" for i in range(1, 21)
]


def validate_cover_url(cover_url: Optional[str]) -> Optional[str]:
    """校验封面 URL 是否在白名单内。

    Returns:
        校验通过的 cover_url；传入 None/空串时返回 None；
        不在白名单时抛出 HTTPException。
    """
    from fastapi import HTTPException
    from fastapi import status as http_status

    if cover_url is None or cover_url == "":
        return None
    if cover_url not in PRESET_COVERS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="封面图只能从预设中选择",
        )
    return cover_url


def validate_group_cover_url(cover_url: Optional[str]) -> Optional[str]:
    """校验群组封面背景 URL 是否在白名单内（None 合法：用默认背景）。"""
    from fastapi import HTTPException
    from fastapi import status as http_status

    if cover_url is None or cover_url == "":
        return None
    if cover_url not in PRESET_GROUP_COVERS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="群组封面只能从预设中选择",
        )
    return cover_url
