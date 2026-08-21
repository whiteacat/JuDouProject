// 餐厅详情页：餐厅信息 + 群聚合评分（"我们群怎么看这家店"）+ 群成员评价
import { get } from '../../../utils/request'

interface GroupStats {
  visit_count: number
  score: number | null
  taste: number | null
  value: number | null
  environment: number | null
  service: number | null
  traffic: number | null
}

interface RestaurantInfo {
  id: number
  name: string
  category: string
  address: string
  phone: string | null
}

interface ReviewItem {
  id: number
  user_id: number
  nickname: string
  avatar_url: string
  overall_score: number
  content: string
}

interface ScoreBar {
  label: string
  score: number
  percent: number
}

Page({
  data: {
    groupId: 0,
    groupName: '',
    restaurantId: 0,
    restaurant: null as RestaurantInfo | null,
    stats: null as GroupStats | null,
    bars: [] as ScoreBar[],
    reviews: [] as ReviewItem[]
  },

  onLoad(options: Record<string, string>) {
    const groupId = Number(options.group_id || 0)
    const restaurantId = Number(options.restaurant_id || 0)
    if (!groupId || !restaurantId) {
      wx.showToast({ title: '缺少参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({
      groupId,
      groupName: options.group_name || '',
      restaurantId
    })
    this.load()
  },

  async load() {
    const { groupId, restaurantId } = this.data
    try {
      const [detail, reviews] = await Promise.all([
        get<{ restaurant: RestaurantInfo; group_stats: GroupStats }>(
          `/groups/${groupId}/restaurants/${restaurantId}`
        ),
        get<ReviewItem[]>(`/groups/${groupId}/restaurants/${restaurantId}/reviews`)
      ])
      const s = detail.group_stats
      const bars: ScoreBar[] = [
        { label: '口味', score: s.taste || 0, percent: ((s.taste || 0) / 5) * 100 },
        { label: '性价比', score: s.value || 0, percent: ((s.value || 0) / 5) * 100 },
        { label: '环境', score: s.environment || 0, percent: ((s.environment || 0) / 5) * 100 },
        { label: '服务', score: s.service || 0, percent: ((s.service || 0) / 5) * 100 },
        { label: '交通', score: s.traffic || 0, percent: ((s.traffic || 0) / 5) * 100 }
      ].filter((b) => b.score > 0)
      this.setData({
        restaurant: detail.restaurant,
        stats: detail.group_stats,
        bars,
        reviews
      })
      if (bars.length > 0) {
        wx.nextTick(() => {
          this.drawRadar(
            [s.taste || 0, s.value || 0, s.environment || 0, s.service || 0, s.traffic || 0],
            ['口味', '性价比', '环境', '服务', '交通']
          )
        })
      }
    } catch (err) {
      console.error('加载餐厅详情失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 401) {
        wx.showToast({ title: '请先登录', icon: 'none' })
        wx.navigateTo({ url: '/pages/login/index' })
        return
      }
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  goCreateEvent() {
    const { groupId, groupName, restaurant } = this.data
    if (!restaurant) return
    wx.navigateTo({
      url:
        `/pages/event/create/index?group_id=${groupId}` +
        `&group_name=${encodeURIComponent(groupName)}` +
        `&restaurant_id=${restaurant.id}` +
        `&restaurant_name=${encodeURIComponent(restaurant.name)}`
    })
  },

  // 六维评分雷达图（Canvas 2D 手绘，无第三方依赖）
  drawRadar(values: number[], labels: string[]) {
    this.createSelectorQuery()
      .select('#scoreRadar')
      .fields({ node: true, size: true })
      .exec((res) => {
        const info = res && (res[0] as { node?: WechatMiniprogram.Canvas; width: number; height: number })
        const canvas = info && info.node
        if (!canvas) return
        const dpr = (wx.getSystemInfoSync() as { pixelRatio?: number }).pixelRatio || 2
        const w = info.width
        const h = info.height
        canvas.width = w * dpr
        canvas.height = h * dpr
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const ctx = canvas.getContext('2d') as any
        ctx.scale(dpr, dpr)
        this.renderRadar(ctx, w, h, values, labels)
      })
  },

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  renderRadar(ctx: any, w: number, h: number, values: number[], labels: string[]) {
    const cx = w / 2
    const cy = h / 2
    const R = Math.min(w, h) / 2 - 36
    const n = values.length
    const angle = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n
    const point = (i: number, r: number) => ({
      x: cx + r * Math.cos(angle(i)),
      y: cy + r * Math.sin(angle(i))
    })

    // 网格（4 层多边形）
    ctx.lineWidth = 1
    ctx.strokeStyle = '#e8e8e8'
    ctx.fillStyle = '#fafafa'
    for (let ring = 4; ring >= 1; ring--) {
      const r = (R * ring) / 4
      ctx.beginPath()
      for (let i = 0; i < n; i++) {
        const p = point(i, r)
        if (i === 0) ctx.moveTo(p.x, p.y)
        else ctx.lineTo(p.x, p.y)
      }
      ctx.closePath()
      if (ring === 4) ctx.fill()
      ctx.stroke()
    }

    // 轴线
    for (let i = 0; i < n; i++) {
      const p = point(i, R)
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(p.x, p.y)
      ctx.stroke()
    }

    // 数据多边形
    const dataPoints = values.map((v, i) =>
      point(i, (Math.max(0, Math.min(5, v)) / 5) * R)
    )
    ctx.beginPath()
    dataPoints.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y)
      else ctx.lineTo(p.x, p.y)
    })
    ctx.closePath()
    ctx.fillStyle = 'rgba(255, 107, 53, 0.18)'
    ctx.fill()
    ctx.strokeStyle = '#ff6b35'
    ctx.lineWidth = 2
    ctx.stroke()

    // 数据点
    ctx.fillStyle = '#ff6b35'
    dataPoints.forEach((p) => {
      ctx.beginPath()
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2)
      ctx.fill()
    })

    // 维度标签
    ctx.fillStyle = '#666'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    labels.forEach((label, i) => {
      const p = point(i, R + 18)
      ctx.fillText(label, p.x, p.y)
    })
  }
})
