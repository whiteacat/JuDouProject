// 头像裁剪页：圆形裁剪框 + 双指缩放/拖动，输出 200x200 JPEG
import { BASE_URL } from '../../../utils/config'

const SIZE = 200 // 输出边长

Page({
  data: {
    tempPath: '',
    canvasSize: 300, // 展示区边长（px）
    imgW: 0,
    imgH: 0,
    scale: 1,
    offset: { x: 0, y: 0 },
    // 手势状态
    startDistance: 0,
    startScale: 1,
    startX: 0,
    startY: 0,
    startOffset: { x: 0, y: 0 },
    touching: false,
    submitting: false
  },

  onLoad(options: Record<string, string>) {
    const tempPath = decodeURIComponent(options.path || '')
    if (!tempPath) {
      wx.showToast({ title: '缺少图片', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 600)
      return
    }
    this.setData({ tempPath })
    // 读取图片原始尺寸
    wx.getImageInfo({
      src: tempPath,
      success: (res) => {
        const { width, height } = res
        const canvas = this.data.canvasSize
        const baseScale = Math.min(canvas / width, canvas / height)
        this.setData({
          imgW: width,
          imgH: height,
          scale: baseScale,
          startScale: baseScale
        })
      },
      fail: () => {
        wx.showToast({ title: '图片加载失败', icon: 'none' })
        setTimeout(() => wx.navigateBack(), 800)
      }
    })
  },

  /* ---------- 手势：拖动 ---------- */

  onTouchStart(e: WechatMiniprogram.TouchEvent) {
    const t = e.touches
    if (t.length === 2) {
      // 双指缩放
      this.setData({
        startDistance: this.distance(t[0], t[1]),
        startScale: this.data.scale
      })
    } else {
      this.setData({
        touching: true,
        startX: t[0].clientX,
        startY: t[0].clientY,
        startOffset: { ...this.data.offset }
      })
    }
  },

  onTouchMove(e: WechatMiniprogram.TouchEvent) {
    const t = e.touches
    if (t.length === 2) {
      // 双指缩放：以 canvas 中心为锚点
      const ratio = this.distance(t[0], t[1]) / (this.data.startDistance || 1)
      const newScale = Math.max(
        this.data.startScale,
        Math.min(this.data.startScale * ratio, this.data.startScale * 4)
      )
      this.setData({ scale: newScale })
    } else if (this.data.touching) {
      const dx = t[0].clientX - this.data.startX
      const dy = t[0].clientY - this.data.startY
      const canvas = this.data.canvasSize
      const drawnW = this.data.imgW * this.data.scale
      const drawnH = this.data.imgH * this.data.scale
      // 限位：图片不能拖出裁剪框
      const maxX = Math.max(0, (drawnW - canvas) / 2)
      const maxY = Math.max(0, (drawnH - canvas) / 2)
      this.setData({
        offset: {
          x: Math.max(-maxX, Math.min(maxX, this.data.startOffset.x + dx)),
          y: Math.max(-maxY, Math.min(maxY, this.data.startOffset.y + dy))
        }
      })
    }
  },

  onTouchEnd() {
    this.setData({ touching: false })
  },

  distance(a: { clientX: number; clientY: number }, b: { clientX: number; clientY: number }) {
    const dx = a.clientX - b.clientX
    const dy = a.clientY - b.clientY
    return Math.sqrt(dx * dx + dy * dy)
  },

  /* ---------- 确认裁剪 ---------- */

  async onConfirm() {
    if (this.data.submitting) return
    this.setData({ submitting: true })
    wx.showLoading({ title: '处理中' })
    try {
      const filePath = await this.cropToTempFile()
      const token = wx.getStorageSync('token')
      // 上传到后端，成功后返回 avatar_url
      const res: { data?: { avatar_url?: string }; errMsg?: string } = await new Promise((resolve, reject) => {
        wx.uploadFile({
          url: `${BASE_URL}/users/me/avatar`,
          filePath,
          name: 'file',
          header: { Authorization: `Bearer ${token}` },
          success: (r) => {
            try {
              resolve({ data: JSON.parse(r.data) } as never)
            } catch {
              reject(new Error('bad response'))
            }
          },
          fail: reject
        })
      })
      wx.hideLoading()
      const avatarUrl = res.data?.avatar_url
      if (!avatarUrl) throw new Error('no avatar_url')
      wx.setStorageSync('avatarPicked', avatarUrl)
      wx.navigateBack()
    } catch (err) {
      wx.hideLoading()
      console.error('头像上传失败', err)
      wx.showToast({ title: '上传失败，请重试', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /** 离屏 canvas 绘制圆形裁剪，输出 200x200 JPEG 临时文件 */
  cropToTempFile(): Promise<string> {
    return new Promise((resolve, reject) => {
      const query = wx.createSelectorQuery()
      query
        .select('#cropCanvas')
        .fields({ node: true })
        .exec((res) => {
          const canvas = res?.[0]?.node as WechatMiniprogram.Canvas | undefined
          if (!canvas) {
            reject(new Error('canvas not found'))
            return
          }
          const ctx = canvas.getContext('2d')
          const dpr = wx.getSystemInfoSync().pixelRatio || 2
          canvas.width = SIZE * dpr
          canvas.height = SIZE * dpr
          ctx.scale(dpr, dpr)

          const img = canvas.createImage()
          img.onload = () => {
            const { imgW, imgH, scale, offset } = this.data
            const view = this.data.canvasSize
            // 裁剪框在展示区正中心，换算到输出坐标系
            const k = SIZE / view
            const cx = view / 2 - offset.x
            const cy = view / 2 - offset.y
            // 圆形裁剪
            ctx.beginPath()
            ctx.arc(SIZE / 2, SIZE / 2, SIZE / 2, 0, Math.PI * 2)
            ctx.clip()
            // 圆形外填充白色（JPEG 不支持透明）
            ctx.fillStyle = '#fff'
            ctx.fillRect(0, 0, SIZE, SIZE)
            // 绘制图片：展示区坐标 → 输出坐标
            const dw = imgW * scale
            const dh = imgH * scale
            // 运行时 Canvas.drawImage 接受 Image 对象；类型包不完整，此处断言
            ;(ctx as unknown as {
              drawImage: (
                img: unknown,
                x: number,
                y: number,
                w: number,
                h: number
              ) => void
            }).drawImage(img, (offset.x - view / 2) * k + dw / 2, (offset.y - view / 2) * k + dh / 2, dw * k, dh * k)

            wx.canvasToTempFilePath({
              canvas,
              fileType: 'jpg',
              quality: 0.9,
              success: (r) => resolve(r.tempFilePath),
              fail: (e) => reject(e)
            })
          }
          img.onerror = (e) => reject(e)
          img.src = this.data.tempPath
        })
    })
  },

  onCancel() {
    wx.navigateBack()
  },

  onShareAppMessage() {
    return { title: '聚豆·组队聚餐', path: '/pages/index/index' }
  }
})
