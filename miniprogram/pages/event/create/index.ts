// 组队创建页：可从群组主页（无餐厅）或地图餐厅弹层（携带餐厅）进入
import { post } from '../../../utils/request'

/** 安全解码 URL 参数：onLoad 拿到的 query 参数是 encodeURIComponent 编码后的原样值。 */
function safeDecode(value: string): string {
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function defaultDateTime() {
  const now = new Date(Date.now() + 24 * 3600 * 1000) // 明天
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return { date: `${y}-${m}-${d}`, time: '19:00' }
}

Page({
  data: {
    groupId: 0,
    groupName: '',
    restaurantId: 0 as number | null,
    restaurantName: '',
    lat: 0 as number | null,
    lng: 0 as number | null,
    title: '',
    date: '',
    time: '',
    minMembers: 1,
    maxMembers: 6,
    remark: '',
    submitting: false
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.group_id || 0)
    if (!groupId) {
      wx.showToast({ title: '缺少群组参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    const restaurantId = Number(options.restaurant_id || 0) || null
    const lat = Number(options.lat || 0) || null
    const lng = Number(options.lng || 0) || null
    const groupName = safeDecode(options.group_name || '')
    const restaurantName = safeDecode(options.restaurant_name || '')
    const { date, time } = defaultDateTime()
    this.setData({
      groupId,
      groupName,
      restaurantId,
      restaurantName,
      lat,
      lng,
      title: restaurantName,
      date,
      time
    })
    // 未指定餐厅且未携带坐标时，尝试用当前位置作为组队地点（否则组队不会显示在地图上）
    if (!restaurantId && (!lat || !lng)) {
      this.locateForEvent()
    }
  },

  locateForEvent() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({ lat: res.latitude, lng: res.longitude })
      },
      fail: () => {
        wx.showToast({ title: '定位失败，组队将不显示在地图上', icon: 'none' })
      }
    })
  },

  onTitleInput(e: WechatMiniprogram.Input) {
    this.setData({ title: e.detail.value })
  },

  onRemarkInput(e: WechatMiniprogram.Input) {
    this.setData({ remark: e.detail.value })
  },

  onMinInput(e: WechatMiniprogram.Input) {
    this.setData({ minMembers: Number(e.detail.value) || 1 })
  },

  onMaxInput(e: WechatMiniprogram.Input) {
    this.setData({ maxMembers: Number(e.detail.value) || 1 })
  },

  onDateChange(e: WechatMiniprogram.PickerChange) {
    this.setData({ date: String(e.detail.value) })
  },

  onTimeChange(e: WechatMiniprogram.PickerChange) {
    this.setData({ time: String(e.detail.value) })
  },

  async onSubmit() {
    const { groupId, title, date, time, minMembers, maxMembers } = this.data
    if (!title.trim()) {
      wx.showToast({ title: '请输入组队标题', icon: 'none' })
      return
    }
    if (minMembers < 1 || maxMembers < 1 || minMembers > maxMembers) {
      wx.showToast({ title: '人数设置不合法', icon: 'none' })
      return
    }
    if (!date || !time) {
      wx.showToast({ title: '请选择时间', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    try {
      const payload: Record<string, unknown> = {
        title: title.trim(),
        event_time: `${date}T${time}:00+08:00`,
        min_members: minMembers,
        max_members: maxMembers,
        remark: this.data.remark || null
      }
      if (this.data.restaurantId) {
        payload.restaurant_id = this.data.restaurantId
      } else if (this.data.lat && this.data.lng) {
        payload.latitude = this.data.lat
        payload.longitude = this.data.lng
      }
      const event = await post<{ id: number }>(`/groups/${groupId}/events`, payload)
      wx.showToast({ title: '组队创建成功' })
      wx.redirectTo({ url: `/pages/event/detail/index?id=${event.id}` })
    } catch (err) {
      console.error('创建组队失败', err)
      wx.showToast({ title: '创建失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
