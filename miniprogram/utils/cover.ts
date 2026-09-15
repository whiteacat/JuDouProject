/** 活动封面工具：预设封面白名单 + 主题归类 + 本地路径映射。
 *
 * 封面不允许用户上传，只能从预设列表选择。
 * 后端保存 preset://cover/NN 协议 URL，前端映射为
 * assets/activity_cover_assets/activity_cover_NN.png 本地图片。
 */

export interface PresetCover {
  key: string
  label: string
  image: string
  theme: 'dine' | 'play' | 'date' | 'team'
}

const img = (n: number) => `/assets/activity_cover_assets/activity_cover_${String(n).padStart(2, '0')}.png`

/** 各主题默认封面（从预设库中挑一张代表作） */
export const THEME_DEFAULTS: Record<string, number> = {
  dine: 1,
  play: 17,
  date: 3,
  team: 6,
}

/** 预设封面列表（30 张，与后端 cover.PRESET_COVERS 同步；theme 按主色调归类） */
export const PRESET_COVERS: PresetCover[] = Array.from({ length: 30 }, (_, i) => {
  const n = i + 1
  const theme: PresetCover['theme'] =
    n === 1 || n === 2 ? 'dine'
    : n === 17 ? 'play'
    : [6, 9, 10, 11, 12, 15, 16, 19, 21, 27, 28, 29].includes(n) ? 'team'
    : 'date'
  const label = theme === 'dine' ? '聚餐' : theme === 'play' ? '游玩' : theme === 'date' ? '约会' : '组队'
  return { key: `preset://cover/${String(n).padStart(2, '0')}`, label, image: img(n), theme }
})

/** 将封面 URL（preset://cover/NN 或空）解析为可展示的本地图片路径。 */
export function resolveCoverSrc(coverUrl: string | null | undefined): string {
  if (!coverUrl) return img(THEME_DEFAULTS.dine)
  const m = /^preset:\/\/cover\/(\d{2})$/.exec(coverUrl)
  if (m) {
    const found = PRESET_COVERS.find((c) => c.key === coverUrl)
    if (found) return found.image
  }
  return img(THEME_DEFAULTS.dine)
}

/** 按活动标题归类主题，返回默认封面 key（与列表页分类逻辑一致）。 */
export function defaultCoverOf(title: string): string {
  const t = title || ''
  const PLAY = ['电影', '展览', '密室', '桌游', '户外', 'KTV', '游乐', '剧本', '爬山', '徒步', '游泳', '运动', '游玩']
  const DATE = ['约会', '咖啡', '下午茶', '看展', '双人']
  const DINE = ['火锅', '聚餐', '吃饭', '烧烤', '海鲜', '日料', '川菜', '西餐', '甜品', '宵夜', '早茶', '烤肉', '自助餐']
  let theme = 'team'
  if (PLAY.some((kw) => t.includes(kw))) theme = 'play'
  else if (DATE.some((kw) => t.includes(kw))) theme = 'date'
  else if (DINE.some((kw) => t.includes(kw))) theme = 'dine'
  return `preset://cover/${String(THEME_DEFAULTS[theme]).padStart(2, '0')}`
}

/* ==================== 群组封面（详情页背景） ==================== */

export interface GroupCover {
  key: string
  image: string
}

const gimg = (n: number) => `/assets/group_cover_assets/group_cover_${String(n).padStart(2, '0')}.png`

/** 预设群组封面列表（20 张，与后端 cover.PRESET_GROUP_COVERS 同步） */
export const GROUP_COVERS: GroupCover[] = Array.from({ length: 20 }, (_, i) => {
  const n = i + 1
  return { key: `preset://group_cover/${String(n).padStart(2, '0')}`, image: gimg(n) }
})

/** 将群组封面 URL（preset://group_cover/NN 或空）解析为本地图片路径；空返回默认背景。 */
export function resolveGroupCoverSrc(coverUrl: string | null | undefined): string {
  if (!coverUrl) return gimg(1)
  const m = /^preset:\/\/group_cover\/(\d{2})$/.exec(coverUrl)
  if (m) {
    const found = GROUP_COVERS.find((c) => c.key === coverUrl)
    if (found) return found.image
  }
  return gimg(1)
}
