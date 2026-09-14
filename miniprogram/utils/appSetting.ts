/** 应用配置：内容编辑总开关查询。
 *
 * 前期内容安全防控：平台侧关闭开关后，用户可编辑文本的提交
 * （群组名/活动/评价/昵称签名）会被服务端统一拒绝（403）。
 * 前端在提交入口预检并给出友好提示。
 */
import { get } from './request'

let cached: { value: boolean; at: number } | null = null
const CACHE_MS = 30 * 1000

/** 查询内容编辑开关（30 秒缓存，失败时按开启处理，由服务端兜底拦截）。 */
export async function isContentEditEnabled(force = false): Promise<boolean> {
  if (!force && cached && Date.now() - cached.at < CACHE_MS) {
    return cached.value
  }
  try {
    const res = await get<{ key: string; value: boolean }>('/admin/status')
    cached = { value: res.value, at: Date.now() }
    return res.value
  } catch {
    // 查询失败不阻断用户操作，最终由服务端守卫拦截
    return true
  }
}

/** 开关提示文案。 */
export const CONTENT_EDIT_DISABLED_TIP = '平台内容编辑功能已暂停，暂不可提交'
