// 群组详情页：群信息、邀请码、成员列表、功能入口
import { get } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'

interface Member {
  user_id: number
  role: string
  joined_at: string
  nickname: string
  avatar_url: string
  short?: string
  avatar_src?: string
}

interface GroupDetail {
  id: number
  name: string
  avatar_url: string
  avatar_src?: string
  owner_id: number
  invite_code: string
  member_count: number
}

interface EventBrief {
  id: number
  title: string
  event_time: string
  status: string
  current_members: number
  max_members: number
  time_display?: string
  status_text?: string
}

const STATUS_TEXT: Record<string, string> = {
  RECRUITING: '招募中',
  CONFIRMED: '已确认',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  EXPIRED: '已失效'
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

Page({
  data: {
    groupId: 0,
    group: null as GroupDetail | null,
    members: [] as Member[],
    showMembers: [] as Member[],
    recentEvents: [] as EventBrief[],
    isMember: false,
    showAllMembers: false
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.id || 0)
    if (!groupId) {
      wx.showToast({ title: '缺少群组参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ groupId })
    this.fetchDetail()
  },

  onShareAppMessage() {
    const group = this.data.group
    return {
      title: group ? `「${group.name}」邀请你一起聚餐` : '聚豆·群组聚餐组队',
      path: group ? `/pages/group/detail/index?id=${group.id}` : '/pages/index/index'
    }
  },

  onShow() {
    if (this.data.groupId && !this.data.group) {
      this.fetchDetail()
    }
  },

  async fetchDetail() {
    const { groupId } = this.data
    if (!groupId) return
    try {
      const [group, members, events] = await Promise.all([
        get<GroupDetail>(`/groups/${groupId}`),
        get<Member[]>(`/groups/${groupId}/members`),
        get<EventBrief[]>(`/groups/${groupId}/events`).catch(() => [])
      ])
      const avatarSrc = resolveAvatarSrc(group.avatar_url || '')
      const mappedMembers = members.map((m) => ({
        ...m,
        short: m.nickname ? m.nickname[0] : '?',
        avatar_src: resolveAvatarSrc(m.avatar_url || ''),
      }))
      const mappedEvents = events.slice(0, 3).map((e) => ({
        ...e,
        time_display: formatTime(e.event_time),
        status_text: STATUS_TEXT[e.status] || e.status,
      }))
      this.setData({
        group: { ...group, avatar_src: avatarSrc },
        members: mappedMembers,
        showMembers: mappedMembers.slice(0, 8),
        recentEvents: mappedEvents,
        isMember: true
      })
    } catch (err) {
      console.error('加载群组失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 401) {
        wx.showToast({ title: '请先登录', icon: 'none' })
        wx.navigateTo({ url: '/pages/login/index' })
        return
      }
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  toggleMembers() {
    const showAll = !this.data.showAllMembers
    this.setData({
      showAllMembers: showAll,
      showMembers: showAll ? this.data.members : this.data.members.slice(0, 8)
    })
  },

  onAnnouncement() {
    wx.showToast({ title: '群公告功能开发中', icon: 'none' })
  },

  onMore() {
    wx.showActionSheet({
      itemList: ['分享群组', '退出群组'],
      success: (res) => {
        if (res.tapIndex === 0) {
          // 触发分享
        }
      }
    })
  },

  onCopyCode() {
    const code = this.data.group ? this.data.group.invite_code : ''
    if (!code) return
    wx.setClipboardData({ data: code })
  },

  goGroupEvents() {
    const group = this.data.group
    if (!group) return
    wx.navigateTo({
      url: `/pages/group/events/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
    })
  },

  goCreateEvent() {
    const group = this.data.group
    if (!group) return
    wx.navigateTo({
      url: `/pages/event/create/index?group_id=${group.id}&group_name=${encodeURIComponent(group.name)}`
    })
  },

  goEventDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/event/detail/index?id=${id}` })
  }
})
