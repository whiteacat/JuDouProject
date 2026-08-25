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

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function fullDateOf(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 由「HH:mm 基准 + 偏移小时」算出 HH:mm（默认时段：聚餐前 1 小时 ~ 聚餐后 2 小时）。 */
function shiftTime(base: string, offsetHours: number): string {
  if (!base) return '00:00'
  const [h, m] = base.split(':').map(Number)
  const total = ((h * 60 + (m || 0) + offsetHours * 60) + 24 * 60) % (24 * 60)
  return `${pad(Math.floor(total / 60))}:${pad(total % 60)}`
}

interface TimeWindowDraft {
  date: string
  start: string
  end: string
}

const EXPIRY_MODES = [
  { key: 'none', label: '长期有效', desc: '不自动失效，直到聚餐完成' },
  { key: 'at_complete', label: '完成才失效', desc: '聚餐完成后组队失效' },
  { key: 'at_time', label: '指定时间失效', desc: '超过设定时间自动失效' },
  { key: 'after_hours', label: '创建后限时', desc: '创建后 N 小时自动失效' }
]

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
    submitting: false,
    // 失效策略
    expiryModes: EXPIRY_MODES,
    expiryMode: 'none',
    expiryDate: '',
    expiryTime: '',
    expiresAfterHours: 48,
    // 创建者本人可参加时段：可跨多天、每天多段
    myWindows: [] as TimeWindowDraft[],
    windowEnabled: false
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
    const expiryDate = new Date(Date.now() + 48 * 3600 * 1000)
    // 默认给一段「聚餐日 前1小时 ~ 后2小时」的时段，可增删改
    this.setData({
      groupId,
      groupName,
      restaurantId,
      restaurantName,
      lat,
      lng,
      title: restaurantName,
      date,
      time,
      myWindows: [{ date, start: shiftTime(time, -1), end: shiftTime(time, 2) }],
      windowEnabled: true,
      expiryDate: `${expiryDate.getFullYear()}-${pad(expiryDate.getMonth() + 1)}-${pad(expiryDate.getDate())}`,
      expiryTime: time
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
    const date = String(e.detail.value)
    // 未改动的默认段（还在原聚餐日）跟随聚餐日期
    const old = this.data.date
    const myWindows = this.data.myWindows.map((w) =>
      w.date === old ? { ...w, date } : w
    )
    this.setData({ date, myWindows })
  },

  onTimeChange(e: WechatMiniprogram.PickerChange) {
    const time = String(e.detail.value)
    this.setData({ time })
  },

  onExpiryModeChange(e: WechatMiniprogram.TouchEvent) {
    const mode = e.currentTarget.dataset.mode as string
    this.setData({ expiryMode: mode })
  },

  onExpiryDateChange(e: WechatMiniprogram.PickerChange) {
    this.setData({ expiryDate: String(e.detail.value) })
  },

  onExpiryTimeChange(e: WechatMiniprogram.PickerChange) {
    this.setData({ expiryTime: String(e.detail.value) })
  },

  onExpiryHoursInput(e: WechatMiniprogram.Input) {
    this.setData({ expiresAfterHours: Number(e.detail.value) || 0 })
  },

  onWindowToggle(e: WechatMiniprogram.SwitchChange) {
    const enabled = e.detail.value
    // 首次开启且列表为空时给一段默认值（聚餐日 前1h~后2h）
    let myWindows = this.data.myWindows
    if (enabled && myWindows.length === 0) {
      myWindows = [{
        date: this.data.date,
        start: shiftTime(this.data.time, -1),
        end: shiftTime(this.data.time, 2)
      }]
    }
    this.setData({ windowEnabled: enabled, myWindows })
  },

  onAddWindow() {
    const { myWindows, date, time } = this.data
    if (myWindows.length >= 30) {
      wx.showToast({ title: '最多添加 30 个时段', icon: 'none' })
      return
    }
    const last = myWindows[myWindows.length - 1]
    const newWindow: TimeWindowDraft = {
      // 默认新段：沿用最近一日的日期、时段顺延 2 小时
      date: (last && last.date) || date,
      start: last ? shiftTime(last.start, 2) : shiftTime(time, -1),
      end: last ? shiftTime(last.end, 2) : shiftTime(time, 2)
    }
    this.setData({ myWindows: [...myWindows, newWindow] })
  },

  onRemoveWindow(e: WechatMiniprogram.TouchEvent) {
    const index = Number(e.currentTarget.dataset.index)
    const myWindows = this.data.myWindows.filter((_, i) => i !== index)
    this.setData({ myWindows })
  },

  onWindowDateChange(e: WechatMiniprogram.PickerChange) {
    const index = Number(e.currentTarget.dataset.index)
    const value = String(e.detail.value)
    this.setData({ [`myWindows[${index}].date`]: value })
  },

  onWindowStartChange(e: WechatMiniprogram.PickerChange) {
    const index = Number(e.currentTarget.dataset.index)
    const value = String(e.detail.value)
    this.setData({ [`myWindows[${index}].start`]: value })
  },

  onWindowEndChange(e: WechatMiniprogram.PickerChange) {
    const index = Number(e.currentTarget.dataset.index)
    const value = String(e.detail.value)
    this.setData({ [`myWindows[${index}].end`]: value })
  },

  /** 提交前校验：每段 end>start、同一天不重叠。通过返回规范化数组，否则 toast 并返回 null。 */
  validateWindows(): TimeWindowDraft[] | null {
    const { myWindows } = this.data
    for (const w of myWindows) {
      if (!w.date || !w.start || !w.end) {
        wx.showToast({ title: '时段未填完整', icon: 'none' })
        return null
      }
      if (w.start >= w.end) {
        wx.showToast({ title: `${w.date} 时段结束需晚于开始`, icon: 'none' })
        return null
      }
    }
    const byDate = new Map<string, [number, number][]>()
    for (const w of myWindows) {
      const s = Number(w.start.replace(':', ''))
      const e = Number(w.end.replace(':', ''))
      const segs = byDate.get(w.date) || []
      segs.push([s, e])
      byDate.set(w.date, segs)
    }
    for (const [date, segs] of byDate) {
      segs.sort((a, b) => a[0] - b[0])
      for (let i = 1; i < segs.length; i++) {
        if (segs[i][0] < segs[i - 1][1]) {
          wx.showToast({ title: `${date} 时段有重叠`, icon: 'none' })
          return null
        }
      }
    }
    return [...myWindows].sort((a, b) => (a.date + a.start).localeCompare(b.date + b.start))
  },

  async onSubmit() {
    const {
      groupId, title, date, time, minMembers, maxMembers,
      expiryMode, expiryDate, expiryTime, expiresAfterHours, windowEnabled
    } = this.data
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
    if (expiryMode === 'at_time' && (!expiryDate || !expiryTime)) {
      wx.showToast({ title: '请选择失效时间', icon: 'none' })
      return
    }
    if (expiryMode === 'after_hours' && (!expiresAfterHours || expiresAfterHours < 1)) {
      wx.showToast({ title: '请填写失效时长（小时）', icon: 'none' })
      return
    }
    const windows = windowEnabled ? this.validateWindows() : []
    if (windowEnabled && windows === null) {
      return
    }
    this.setData({ submitting: true })
    try {
      const payload: Record<string, unknown> = {
        title: title.trim(),
        event_time: `${date}T${time}:00+08:00`,
        min_members: minMembers,
        max_members: maxMembers,
        remark: this.data.remark || null,
        expiry_mode: expiryMode,
        time_windows: windows
      }
      if (expiryMode === 'at_time') {
        payload.expires_at = `${expiryDate}T${expiryTime}:00+08:00`
      } else if (expiryMode === 'after_hours') {
        payload.expires_after_hours = expiresAfterHours
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
