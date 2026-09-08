/** 头像 URL 解析工具：将预设头像协议映射为本地图片路径。 */

const PRESET_AVATAR_MAP: Record<string, string> = {
  'preset://avatar/1': '/assets/icons/preset-avatars/1.png',
  'preset://avatar/2': '/assets/icons/preset-avatars/2.png',
  'preset://avatar/3': '/assets/icons/preset-avatars/3.png',
  'preset://avatar/4': '/assets/icons/preset-avatars/4.png',
  'preset://avatar/5': '/assets/icons/preset-avatars/5.png',
  'preset://avatar/6': '/assets/icons/preset-avatars/6.png',
  'preset://avatar/7': '/assets/icons/preset-avatars/7.png',
  'preset://avatar/8': '/assets/icons/preset-avatars/8.png',
}

/** 将 avatar_url 转换为可用于 <image src> 的本地/网络地址。 */
export function resolveAvatarSrc(url: string): string {
  return PRESET_AVATAR_MAP[url] || url
}
