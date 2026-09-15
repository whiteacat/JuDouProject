// 活动海报生成页：canvas 绘制分享海报（封面 + 标题 + 时间 + 二维码），支持保存相册 / 转发
import { get } from '../../../utils/request'
import { BASE_URL } from '../../../utils/config'
import { resolveCoverSrc } from '../../../utils/cover'

interface EventInfo {
  id: number
  title: string
  event_time: string
  status: string
  current_members: number
  max_members: number
  cover_url: string | null
  group_id: number
  restaurant: { id: number; name: string; address?: string } | null
  budget: number | null
}

Page({
  data: {
    eventId: 0,
    event: null as EventInfo | null,
    canvasW: 750,
    canvasH: 1000,
    ready: false,
    generating: false
  },

  onLoad(options: Record<string, string>) {
    const eventId = Number(options.id || 0)
    if (!eventId) {
      wx.showToast({ title: '缺少活动参数', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ eventId })
    this.loadEvent()
  },

  async loadEvent() {
    try {
      const event = await get<EventInfo>(`/events/${this.data.eventId}`)
      // 活动加载完成后自动生成海报。
      // 不依赖「点击 canvas」触发：加载遮罩是绝对定位覆盖层，会拦截 tap，
      // 导致 onCanvasReady 永远不触发、海报卡在"生成中"。
      this.setData({ event, ready: true })
      this.generate()
    } catch (err) {
      console.error('加载活动失败', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
    }
  },

  onCanvasReady() {
    if (this.data.ready) return
    this.setData({ ready: true })
    this.generate()
  },

  /** 绘制海报 */
  async generate() {
    if (this.data.generating || !this.data.ready) return
    const event = this.data.event
    if (!event) return
    this.setData({ generating: true })

    const canvas = await this.waitForCanvas()
    if (!canvas) {
      this.setData({ generating: false })
      wx.showToast({ title: '海报尚未就绪，点击海报重试', icon: 'none' })
      return
    }
    const ctx = canvas.getContext('2d')
    const dpr = wx.getSystemInfoSync().pixelRatio || 2
    const W = this.data.canvasW
    const H = this.data.canvasH
    canvas.width = W * dpr
    canvas.height = H * dpr
    ctx.scale(dpr, dpr)

    // 1. 背景
    const bg = ctx.createLinearGradient(0, 0, 0, H)
    bg.addColorStop(0, '#fff7f2')
    bg.addColorStop(1, '#ffffff')
    ctx.fillStyle = bg
    ctx.fillRect(0, 0, W, H)

    // 2. 封面图
    const coverSrc = resolveCoverSrc(event.cover_url)
    await this.drawImage(ctx, canvas, coverSrc, 60, 60, W - 120, 360, 24)

    // 3. 品牌角标
    ctx.font = 'bold 28px sans-serif'
    ctx.fillStyle = '#ff6b35'
    ctx.fillText('聚豆 JUDOU', 60, 470)

    // 4. 标题（最多两行）
    ctx.font = 'bold 56px sans-serif'
    ctx.fillStyle = '#222'
    this.drawWrappedText(ctx, event.title, 60, 550, W - 120, 70, 2)

    // 5. 信息行
    const meta = ctx
    meta.font = '32px sans-serif'
    meta.fillStyle = '#888'
    const timeText = this.formatTime(event.event_time)
    meta.fillText(`📅 ${timeText}`, 60, 700)
    const locText = event.restaurant?.name || '地点待定'
    meta.fillText(`📍 ${locText}`, 60, 760)
    if (event.budget != null) {
      meta.fillText(`💰 人均 ¥${event.budget}`, 60, 820)
    }

    // 6. 人数胶囊
    ctx.font = '30px sans-serif'
    ctx.fillStyle = '#ff6b35'
    const peopleText = `已有 ${event.current_members}/${event.max_members} 人加入`
    ctx.fillText(peopleText, 60, 890)

    // 7. 二维码
    try {
      // canvas 的 createImage 无法携带 Authorization 请求头，
      // 需走后端 ?token= query 鉴权（二维码为公开内容，token 仅用于身份校验）
      const token = this.getToken()
      const qrUrl = token
        ? `${BASE_URL}/events/${event.id}/qrcode?token=${encodeURIComponent(token)}`
        : `${BASE_URL}/events/${event.id}/qrcode`
      await this.drawQrCode(ctx, canvas, qrUrl, W - 300, 940, 240, 240)
    } catch (e) {
      console.error('二维码加载失败', e)
      ctx.font = '26px sans-serif'
      ctx.fillStyle = '#bbb'
      ctx.fillText('二维码加载失败，请截图分享', W - 300, 1060)
    }

    // 8. 二维码下方引导文案
    ctx.font = '26px sans-serif'
    ctx.fillStyle = '#999'
    ctx.textAlign = 'center'
    ctx.fillText('微信扫码 · 一键加入组队', W - 180, 1215)
    ctx.textAlign = 'left'

    this.setData({ generating: false })
  },

  /** 等待 canvas 节点就绪（带重试）。
   * 用回调式 exec + 空值兜底：Promise 式 exec() 在部分基础库版本/
   * 节点未渲染完成时会 resolve 为 undefined，直接 [0] 会抛
   * "Cannot read properties of undefined (reading '0')"。
   * 生成时机可能在 setData 后立即执行，此时 canvas 尚未渲染，需短重试。 */
  waitForCanvas(tries = 10, delay = 150): Promise<WechatMiniprogram.Canvas | null> {
    return new Promise((resolve) => {
      const attempt = (n: number) => {
        const query = wx.createSelectorQuery()
        query
          .select('#posterCanvas')
          .fields({ node: true, size: true })
          .exec((res) => {
            const node = (res && res[0] && (res[0] as { node?: WechatMiniprogram.Canvas }).node) || null
            if (node) {
              resolve(node)
            } else if (n > 0) {
              setTimeout(() => attempt(n - 1), delay)
            } else {
              resolve(null)
            }
          })
      }
      attempt(tries)
    })
  },

  getToken(): string {
    return wx.getStorageSync('token') || ''
  },

  formatTime(iso: string): string {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  },

  /** 多行文本绘制（简单按宽度折行） */
  drawWrappedText(
    ctx: WechatMiniprogram.CanvasContext,
    text: string,
    x: number,
    y: number,
    maxWidth: number,
    lineHeight: number,
    maxLines: number
  ) {
    let line = ''
    let curY = y
    for (const ch of text) {
      const test = line + ch
      if (ctx.measureText(test).width > maxWidth && line) {
        ctx.fillText(line, x, curY)
        line = ch
        curY += lineHeight
        if (curY - y >= lineHeight * (maxLines - 1)) {
          // 超出行数：末尾加省略号
          const tail = this.ellipsis(line + '…', ctx, maxWidth)
          ctx.fillText(tail, x, curY)
          return
        }
      } else {
        line = test
      }
    }
    ctx.fillText(line, x, curY)
  },

  ellipsis(text: string, ctx: WechatMiniprogram.CanvasContext, maxWidth: number): string {
    while (ctx.measureText(text).width > maxWidth && text.length > 1) {
      text = text.slice(0, -2) + '…'
    }
    return text
  },

  /** 网络图片绘制（失败时画占位块） */
  drawImage(
    ctx: WechatMiniprogram.CanvasContext,
    canvas: WechatMiniprogram.Canvas,
    src: string,
    x: number,
    y: number,
    w: number,
    h: number,
    radius: number
  ): Promise<void> {
    return new Promise((resolve) => {
      const img = canvas.createImage()
      img.onload = () => {
        ctx.save()
        ctx.beginPath()
        this.roundRect(ctx, x, y, w, h, radius)
        ctx.clip()
        ctx.drawImage(img as unknown as string, x, y, w, h)
        ctx.restore()
        resolve()
      }
      img.onerror = (e) => {
        console.error('封面图加载失败', e)
        // 占位渐变块
        const g = ctx.createLinearGradient(x, y, x + w, y + h)
        g.addColorStop(0, '#ff6b35')
        g.addColorStop(1, '#ff9a5c')
        ctx.fillStyle = g
        this.roundRect(ctx, x, y, w, h, radius)
        ctx.fill()
        resolve()
      }
      img.src = src
    })
  },

  /** 二维码绘制（网络图片，带白底留扫描边距） */
  async drawQrCode(
    ctx: WechatMiniprogram.CanvasContext,
    canvas: WechatMiniprogram.Canvas,
    url: string,
    x: number,
    y: number,
    size: number,
    pad: number
  ): Promise<void> {
    const img = canvas.createImage()
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = (e) => {
        // 必须 reject（不能 throw）：throw 会让 Promise 永不 settle，
        // generate() 在 await 处永久挂起，海报卡死
        reject(new Error('qrcode load failed: ' + (e?.errMsg || String(e))))
      }
      img.src = url
    })
    // 白底
    ctx.fillStyle = '#fff'
    this.roundRect(ctx, x - 12, y - 12, size + 24, size + 24, 16)
    ctx.fill()
    ctx.strokeStyle = '#ffd9c7'
    ctx.lineWidth = 3
    this.roundRect(ctx, x - 12, y - 12, size + 24, size + 24, 16)
    ctx.stroke()
    ctx.drawImage(img as unknown as string, x, y, size, size)
  },

  roundRect(
    ctx: WechatMiniprogram.CanvasContext,
    x: number,
    y: number,
    w: number,
    h: number,
    r: number
  ) {
    ctx.beginPath()
    ctx.moveTo(x + r, y)
    ctx.arcTo(x + w, y, x + w, y + h, r)
    ctx.arcTo(x + w, y + h, x, y + h, r)
    ctx.arcTo(x, y + h, x, y, r)
    ctx.arcTo(x, y, x + w, y, r)
    ctx.closePath()
  },

  /** 保存海报到相册（type=2d canvas 需传 canvas 节点） */
  onSave() {
    if (!this.data.event) return
    const query = wx.createSelectorQuery()
    query
      .select('#posterCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        const canvas = res?.[0]?.node as WechatMiniprogram.Canvas | undefined
        if (!canvas) {
          wx.showToast({ title: '海报尚未就绪', icon: 'none' })
          return
        }
        wx.canvasToTempFilePath({
          canvas,
          fileType: 'png',
          success: async (r) => {
            try {
              await wx.saveImageToPhotosAlbum({ filePath: r.tempFilePath })
              wx.showToast({ title: '已保存到相册' })
            } catch (err) {
              const msg = (err as { errMsg?: string }).errMsg || ''
              if (msg.includes('auth deny') || msg.includes('authorize')) {
                wx.showModal({
                  title: '需要相册权限',
                  content: '保存海报需要访问相册，请在设置中开启权限',
                  confirmText: '去设置',
                  success: (m) => {
                    if (m.confirm) wx.openSetting()
                  }
                })
              } else {
                wx.showToast({ title: '保存失败', icon: 'none' })
              }
            }
          },
          fail: (e) => {
            console.error('海报导出失败', e)
            wx.showToast({ title: '海报生成失败', icon: 'none' })
          }
        })
      })
  },

  onShareAppMessage() {
    const event = this.data.event
    return {
      title: event ? `「${event.title}」组队中，快来加入` : '聚豆·组队聚餐',
      path: event ? `/pages/event/detail/index?id=${event.id}&invite=1` : '/pages/index/index'
    }
  },

  goDetail() {
    const event = this.data.event
    if (event) {
      wx.redirectTo({ url: `/pages/event/detail/index?id=${event.id}` })
    }
  }
})
