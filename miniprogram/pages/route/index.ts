// 路线规划页：起点=当前位置（GCJ-02），终点=活动/餐厅地点；经后端代理高德。
import { formatDistance, formatDuration, planRoute, RouteMode } from '../../utils/route'

interface RouteMarker {
  id: number
  longitude: number
  latitude: number
  title?: string
  callout?: {
    content: string
    display: 'BYCLICK' | 'ALWAYS'
  }
}

interface RouteLine {
  points: Array<{ longitude: number; latitude: number }>
  color: string
  width: number
}

function scaleOf(distanceM: number): number {
  if (distanceM < 2000) return 14
  if (distanceM < 5000) return 13
  if (distanceM < 15000) return 12
  return 11
}

Page({
  data: {
    destLng: 0,
    destLat: 0,
    destName: '',
    mode: 'driving' as RouteMode,
    originLng: 0,
    originLat: 0,
    centerLng: 0,
    centerLat: 0,
    scale: 12,
    markers: [] as RouteMarker[],
    polyline: [] as RouteLine[],
    info: '',
    mocked: false,
    loading: true,
    error: ''
  },

  onLoad(options: Record<string, string>) {
    const destLng = Number(options.dest_lng || 0)
    const destLat = Number(options.dest_lat || 0)
    if (!destLng || !destLat) {
      this.setData({ loading: false, error: '缺少目的地，无法规划路线' })
      return
    }
    let destName = options.dest_name || ''
    try {
      destName = decodeURIComponent(destName)
    } catch {
      // 解码失败则用原值展示
    }
    this.setData({
      destLng,
      destLat,
      destName,
      mode: options.mode === 'walking' ? 'walking' : 'driving'
    })
    this.locate()
  },

  locate() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({ originLng: res.longitude, originLat: res.latitude })
        void this.load()
      },
      fail: () => {
        this.setData({ loading: false, error: '定位失败，请检查定位权限后重试' })
      }
    })
  },

  async load() {
    const { originLng, originLat, destLng, destLat, mode, destName } = this.data
    this.setData({ loading: true, error: '' })
    try {
      const plan = await planRoute(
        { longitude: originLng, latitude: originLat },
        { longitude: destLng, latitude: destLat },
        mode
      )
      const points = plan.polyline.map(([lng, lat]) => ({ longitude: lng, latitude: lat }))
      this.setData({
        loading: false,
        mocked: plan.mocked,
        centerLng: (originLng + destLng) / 2,
        centerLat: (originLat + destLat) / 2,
        scale: scaleOf(plan.distance_m),
        markers: [
          { id: 0, longitude: originLng, latitude: originLat, title: '我的位置' },
          {
            id: 1,
            longitude: destLng,
            latitude: destLat,
            title: destName || '目的地',
            callout: { content: destName || '目的地', display: 'BYCLICK' }
          }
        ],
        polyline: [{ points, color: '#ff6b35', width: 6 }],
        info: `${mode === 'driving' ? '驾车' : '步行'} · ${formatDistance(plan.distance_m)} · ${formatDuration(plan.duration_s)}${plan.mocked ? '（直线示意）' : ''}`
      })
    } catch {
      this.setData({ loading: false, error: '路线规划失败，请稍后重试' })
    }
  },

  switchMode(e: WechatMiniprogram.TouchEvent) {
    const mode = (e.currentTarget.dataset as { mode: RouteMode }).mode
    if (mode === this.data.mode) return
    this.setData({ mode })
    void this.load()
  },

  retry() {
    if (!this.data.originLng) {
      this.locate()
      return
    }
    void this.load()
  },

  openNav() {
    const { destLat, destLng, destName } = this.data
    wx.openLocation({
      latitude: destLat,
      longitude: destLng,
      name: destName || '目的地',
      scale: 15
    })
  }
})
