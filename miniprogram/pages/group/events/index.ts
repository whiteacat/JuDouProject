// 群组组队列表页：当前群的组队（含全部状态，点击进详情）
import { get } from '../../../utils/request'

interface GroupEventItem {
  id: number
  title: string
  event_time: string
  status: string
  current_members: number
  max_members: number
  restaurant: { id: number; name: string } | null
  time_display?: string
  status_text?: string
}

const STATUS_TEXT: Record<string, string> = {
  RECRUITING: '招募中',
  CONFIRMED: '已确认',
  COMPLETED: '已完成',
  CANCELLED: '已取消'
}

/** 招募中的组队若已过聚餐时间，标记为已过期。 */
function statusTextOf(status: string, eventTime: string): string {
  if (
    (status === 'RECRUITING' || status === 'CONFIRMED') &&
    new Date(eventTime).getTime() < Date.now()
  ) {
    return '已过期'
  }
  return STATUS_TEXT[status] || status
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
    groupName: '',
    events: [] as GroupEventItem[],
    loading: false
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.group_id || 0)
    if (!groupId) {
      wx.showToast({ title: '缺少群组参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ groupId, groupName: options.group_name || '' })
    this.fetchEvents()
  },

  async fetchEvents() {
    const { groupId } = this.data
    this.setData({ loading: true })
    try {
      const events = await get<GroupEventItem[]>(`/groups/${groupId}/events`)
      this.setData({
        events: events.map((e) => ({
          ...e,
          time_display: formatTime(e.event_time),
          status_text: statusTextOf(e.status, e.event_time)
        }))
      })
    } catch (err) {
      console.error('加载群组队失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goDetail(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/event/detail/index?id=${id}` })
  }
})
