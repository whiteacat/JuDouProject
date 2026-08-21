// 评价页：六维评分（五颗星点选）+ 文字评价
import { get, post } from '../../../utils/request'

interface EventDetail {
  id: number
  status: string
  title: string
  restaurant: { id: number; name: string } | null
}

interface StarItem {
  value: number
  active: boolean
  dimIndex: number
}

interface Dim {
  key: string
  label: string
  score: number
  stars: StarItem[]
}

const DIM_DEFS = [
  { key: 'taste', label: '口味' },
  { key: 'value', label: '性价比' },
  { key: 'environment', label: '环境' },
  { key: 'service', label: '服务' },
  { key: 'traffic', label: '交通' }
]

// 总分权重（与后端 review_service.SCORE_WEIGHTS 保持一致）
const SCORE_WEIGHTS: Record<string, number> = {
  taste: 0.3,
  value: 0.2,
  environment: 0.2,
  service: 0.15,
  traffic: 0.15
}

/** 五维加权计算总分（与后端 compute_overall_score 同一算法）。 */
function computeTotal(dims: Dim[]): number {
  let total = 0
  for (const d of dims) {
    total += (SCORE_WEIGHTS[d.key] || 0) * d.score
  }
  return Math.round(total * 10) / 10
}

/** 构建六维数据：dimIndex/active 直接嵌入每颗星，避免嵌套循环作用域取值问题。 */
function buildDims(): Dim[] {
  return DIM_DEFS.map((d, dimIndex) => ({
    ...d,
    score: 5,
    stars: [1, 2, 3, 4, 5].map((value) => ({
      value,
      active: true,
      dimIndex
    }))
  }))
}

Page({
  data: {
    eventId: 0,
    event: null as EventDetail | null,
    dims: buildDims(),
    totalScore: 5,
    content: '',
    submitting: false
  },

  onLoad(options: Record<string, string>) {
    const eventId = Number(options.id || 0)
    if (!eventId) {
      wx.showToast({ title: '缺少组队参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ eventId })
    this.load()
  },

  async load() {
    const { eventId } = this.data
    try {
      const event = await get<EventDetail>(`/events/${eventId}`)
      if (event.status !== 'COMPLETED') {
        wx.showToast({ title: '组队完成后才能评价', icon: 'none' })
        setTimeout(() => wx.navigateBack(), 800)
        return
      }
      if (!event.restaurant) {
        wx.showToast({ title: '该组队未指定餐厅，无法评价', icon: 'none' })
        setTimeout(() => wx.navigateBack(), 800)
        return
      }
      this.setData({ event })
    } catch (err) {
      console.error('加载组队失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 401) {
        wx.showToast({ title: '请先登录', icon: 'none' })
        wx.navigateTo({ url: '/pages/login/index' })
        return
      }
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  // 点星打分：每颗星自带 dimIndex 与 value（1-5）
  onStarTap(e: WechatMiniprogram.TouchEvent) {
    const { dimIndex, score } = e.currentTarget.dataset
    const dims = this.data.dims
    const dim = dims[Number(dimIndex)]
    if (!dim) return
    dim.score = Number(score)
    dim.stars = dim.stars.map((s) => ({ ...s, active: s.value <= dim.score }))
    this.setData({ dims, totalScore: computeTotal(dims) })
  },

  onContentInput(e: WechatMiniprogram.TextareaInput) {
    this.setData({ content: e.detail.value })
  },

  async onSubmit() {
    const { eventId, dims, content } = this.data
    this.setData({ submitting: true })
    try {
      const payload: Record<string, unknown> = { content }
      for (const d of dims) {
        payload[`${d.key}_score`] = d.score
      }
      await post(`/events/${eventId}/reviews`, payload)
      wx.showToast({ title: '评价成功' })
      setTimeout(() => wx.navigateBack(), 800)
    } catch (err) {
      console.error('提交评价失败', err)
      const statusCode = (err as { statusCode?: number })?.statusCode
      if (statusCode === 409) {
        wx.showToast({ title: '该聚餐已评价过', icon: 'none' })
      } else if (statusCode === 403) {
        wx.showToast({ title: '仅参与聚餐的成员可评价', icon: 'none' })
      } else {
        wx.showToast({ title: '提交失败', icon: 'none' })
      }
    } finally {
      this.setData({ submitting: false })
    }
  }
})
