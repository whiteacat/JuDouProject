// 活动完整成员页：展示某活动全部已加入成员（头像 + 昵称）
import { get } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'

interface MemberItem {
  id: number
  nickname: string
  avatar_url: string
  joined_at: string
  is_creator: boolean
  // 前端加工
  avatar_src?: string
  time_display?: string
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
    eventId: 0,
    members: [] as MemberItem[],
    loading: false,
    loaded: false
  },

  onLoad(options: Record<string, string>) {
    const eventId = Number(options.id || 0)
    if (!eventId) {
      wx.showToast({ title: '缺少活动参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ eventId })
    this.loadMembers()
  },

  async loadMembers() {
    if (this.data.loading) return
    this.setData({ loading: true })
    try {
      const items = await get<MemberItem[]>(`/events/${this.data.eventId}/members`)
      this.setData({
        members: items.map((m) => ({
          ...m,
          avatar_src: m.avatar_url ? resolveAvatarSrc(m.avatar_url) : '',
          time_display: formatTime(m.joined_at)
        })),
        loaded: true
      })
    } catch (err) {
      console.error('加载成员失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  }
})
