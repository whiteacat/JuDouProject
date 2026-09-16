// 群完整成员页：展示某群组全部成员（头像 + 昵称 + 群主/成员标签 + 加入时间）
import { get } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'

interface MemberItem {
  user_id: number
  role: string
  joined_at: string
  nickname: string
  avatar_url: string
  // 前端加工
  avatar_src?: string
  time_display?: string
  is_owner?: boolean
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

Page({
  data: {
    groupId: 0,
    members: [] as MemberItem[],
    loading: false,
    loaded: false
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.id || 0)
    if (!groupId) {
      wx.showToast({ title: '缺少群组参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ groupId })
    this.loadMembers()
  },

  async loadMembers() {
    if (this.data.loading) return
    this.setData({ loading: true })
    try {
      const items = await get<MemberItem[]>(`/groups/${this.data.groupId}/members`)
      this.setData({
        members: items.map((m) => ({
          ...m,
          avatar_src: m.avatar_url ? resolveAvatarSrc(m.avatar_url) : '',
          time_display: formatTime(m.joined_at),
          is_owner: m.role === 'OWNER'
        })),
        loaded: true
      })
    } catch (err) {
      console.error('加载群成员失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  }
})
