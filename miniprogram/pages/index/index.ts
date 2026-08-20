// 地图页：群组切换 -> 组队 Marker + 餐厅搜索 Marker -> 详情/加入
import { isLoggedIn } from '../../utils/auth'
import { get, post } from '../../utils/request'

interface Restaurant {
  id: number
  name: string
  category: string
  address: string
  longitude: number
  latitude: number
  phone: string | null
  distance_text?: string
}

interface GroupItem {
  id: number
  name: string
  member_count: number
}

interface EventBrief {
  id: number
  group_id: number
  creator_id: number
  title: string
  event_time: string
  event_time_display?: string
  status: string
  min_members: number
  max_members: number
  current_members: number
  remark: string | null
  latitude: number | null
  longitude: number | null
  restaurant: { id: number; name: string; longitude: number; latitude: number } | null
}

interface Marker {
  id: number
  latitude: number
  longitude: number
  title: string
  width: number
  height: number
}

const DEFAULT_LNG = 116.4
const DEFAULT_LAT = 39.9
const EVENT_OFFSET = 1000000 // 事件 Marker id 偏移，避免与餐厅 Marker 冲突

function formatTime(iso: string): string {
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

/** 平面距离近似（米）：小范围内足够精确。 */
function distanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dlat = (lat2 - lat1) * 111320
  const dlon = (lon2 - lon1) * 111320 * Math.cos(((lat1 + lat2) / 2) * (Math.PI / 180))
  return Math.sqrt(dlat * dlat + dlon * dlon)
}

function formatDistance(m: number): string {
  if (m < 1000) return `${Math.round(m)}m`
  return `${(m / 1000).toFixed(1)}km`
}

Page({
  data: {
    latitude: DEFAULT_LAT,
    longitude: DEFAULT_LNG,
    markers: [] as Marker[],
    keyword: '',
    searching: false,
    results: [] as Restaurant[],
    showResults: false,
    selectedRestaurant: null as Restaurant | null,
    selectedEvent: null as EventBrief | null,
    groups: [] as GroupItem[],
    groupNames: [] as string[],
    groupIndex: -1,
    currentGroup: null as GroupItem | null,
    eventStatusText: ''
  },

  restaurantMarkers: [] as Marker[],
  eventMarkers: [] as Marker[],
  restaurants: [] as Restaurant[],
  events: [] as EventBrief[],

  onLoad() {
    this.locate()
  },

  onShow() {
    this.loadGroups()
  },

  locate() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({
          latitude: res.latitude,
          longitude: res.longitude
        })
        this.loadEvents()
      },
      fail: () => {
        wx.showToast({ title: '定位失败，使用默认位置', icon: 'none' })
        this.loadEvents()
      }
    })
  },

  async loadGroups() {
    try {
      const groups = await get<GroupItem[]>('/groups')
      const groupNames = groups.map((g) => g.name)
      const groupIndex = groups.length > 0 ? 0 : -1
      this.setData({ groups, groupNames, groupIndex, currentGroup: groupIndex >= 0 ? groups[0] : null })
      this.loadEvents()
    } catch (err) {
      console.error('加载群组失败', err)
    }
  },

  onGroupChange(e: WechatMiniprogram.PickerChange) {
    const index = Number(e.detail.value)
    const currentGroup = this.data.groups[index] || null
    this.setData({ groupIndex: index, currentGroup })
    this.loadEvents()
  },

  goGroupList() {
    wx.switchTab({ url: '/pages/group/list/index' })
  },

  async loadEvents() {
    const group = this.data.currentGroup
    if (!group) {
      this.eventMarkers = []
      this.events = []
      this._refreshMarkers()
      return
    }
    try {
      const events = await get<EventBrief[]>(`/groups/${group.id}/events/map`, {
        longitude: this.data.longitude,
        latitude: this.data.latitude,
        radius: 3000
      })
      this.events = events
      this.eventMarkers = events
        .filter((e) => e.latitude !== null && e.longitude !== null)
        .map((e) => ({
          id: EVENT_OFFSET + e.id,
          latitude: e.latitude as number,
          longitude: e.longitude as number,
          title: e.title,
          width: 24,
          height: 30
        }))
      this._refreshMarkers()
    } catch (err) {
      console.error('加载组队 Marker 失败', err)
    }
  },

  _refreshMarkers() {
    this.setData({ markers: [...this.eventMarkers, ...this.restaurantMarkers] })
  },

  onKeywordInput(e: WechatMiniprogram.Input) {
    this.setData({ keyword: e.detail.value })
  },

  async onSearch() {
    const keyword = (this.data.keyword || '').trim()
    if (!keyword) {
      wx.showToast({ title: '请输入关键字', icon: 'none' })
      return
    }
    if (!isLoggedIn()) {
      wx.showToast({ title: '请先在"我的"页登录', icon: 'none' })
      return
    }
    this.setData({ searching: true })
    try {
      const restaurants = await get<Restaurant[]>('/restaurants/search', {
        keyword,
        longitude: this.data.longitude,
        latitude: this.data.latitude,
        radius: 3000
      })
      this.restaurants = restaurants
      this.restaurantMarkers = restaurants.map((r) => ({
        id: r.id,
        latitude: r.latitude,
        longitude: r.longitude,
        title: r.name,
        width: 24,
        height: 30
      }))
      this._refreshMarkers()
      // 搜索结果显示为列表（店铺名 + 距离 + 分类/地址）
      const centerLat = this.data.latitude
      const centerLng = this.data.longitude
      const results = restaurants.map((r) => ({
        ...r,
        distance_text: formatDistance(distanceMeters(centerLat, centerLng, r.latitude, r.longitude))
      }))
      this.setData({ results, showResults: results.length > 0 })
      if (restaurants.length === 0) {
        wx.showToast({ title: '没有找到相关餐厅', icon: 'none' })
      }
    } catch (err) {
      console.error('搜索餐厅失败', err)
      wx.showModal({
        title: '搜索失败',
        content: '请求未成功。请在 详情→本地设置 勾选"不校验合法域名、web-view、TLS"，然后重试。',
        showCancel: false
      })
    } finally {
      this.setData({ searching: false })
    }
  },

  onMarkerTap(e: WechatMiniprogram.MarkerTap) {
    const markerId = e.detail.markerId
    if (markerId >= EVENT_OFFSET) {
      const target = this.events.find((ev) => EVENT_OFFSET + ev.id === markerId)
      if (target) {
        this.setData({
          selectedEvent: { ...target, event_time_display: formatTime(target.event_time) },
          eventStatusText: this._statusText(target.status)
        })
      }
      return
    }
    const target = this.restaurants.find((r) => r.id === markerId)
    if (target) {
      this.setData({ selectedRestaurant: target })
    }
  },

  _statusText(status: string): string {
    const map: Record<string, string> = {
      RECRUITING: '招募中',
      CONFIRMED: '已确认',
      COMPLETED: '已完成',
      CANCELLED: '已取消'
    }
    return map[status] || status
  },

  hideResults() {
    this.setData({ showResults: false })
  },

  onResultTap(e: WechatMiniprogram.TouchEvent) {
    const id = Number(e.currentTarget.dataset.id)
    const target = this.restaurants.find((r) => r.id === id)
    if (target) {
      this.setData({ selectedRestaurant: target })
    }
  },

  closeSheets() {
    this.setData({ selectedRestaurant: null, selectedEvent: null })
  },

  goEventDetail() {
    const ev = this.data.selectedEvent
    if (!ev) return
    wx.navigateTo({ url: `/pages/event/detail/index?id=${ev.id}` })
  },

  async joinEventFromMap() {
    const ev = this.data.selectedEvent
    if (!ev) return
    try {
      await post(`/events/${ev.id}/join`)
      wx.showToast({ title: '加入成功' })
      this.setData({ selectedEvent: null })
      this.loadEvents()
    } catch (err) {
      console.error('加入组队失败', err)
      wx.showToast({ title: '加入失败，可能已满员', icon: 'none' })
    }
  },

  goCreateEvent() {
    const r = this.data.selectedRestaurant
    const group = this.data.currentGroup
    if (!group) {
      wx.showToast({ title: '请先选择群组', icon: 'none' })
      return
    }
    const params = [`group_id=${group.id}`, `group_name=${encodeURIComponent(group.name)}`]
    if (r) {
      params.push(`restaurant_id=${r.id}`, `restaurant_name=${encodeURIComponent(r.name)}`)
    }
    wx.navigateTo({ url: `/pages/event/create/index?${params.join('&')}` })
  },

  goCreateEventForRestaurant() {
    this.goCreateEvent()
  },

  goRestaurantDetail() {
    const r = this.data.selectedRestaurant
    const group = this.data.currentGroup
    if (!r || !group) {
      wx.showToast({ title: '请先选择群组', icon: 'none' })
      return
    }
    wx.navigateTo({
      url:
        `/pages/restaurant/detail/index?group_id=${group.id}` +
        `&group_name=${encodeURIComponent(group.name)}` +
        `&restaurant_id=${r.id}`
    })
  }
})
