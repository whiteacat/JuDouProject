// 群组入口页：创建新群组 / 邀请码加入已有群组
import { post } from '../../../utils/request'

interface JoinResult {
  id: number
  name: string
}

Page({
  data: {
    // tab: create | join
    tab: 'create',
    name: '',
    inviteCode: '',
    submitting: false
  },

  onLoad(options: Record<string, string>) {
    // 支持从入口携带 ?tab=join 直接进入邀请码加入
    if (options.tab === 'join') {
      this.setData({ tab: 'join' })
    }
  },

  onTabChange(e: WechatMiniprogram.TouchEvent) {
    this.setData({ tab: e.currentTarget.dataset.tab as string })
  },

  onNameInput(e: WechatMiniprogram.Input) {
    this.setData({ name: e.detail.value })
  },

  onCodeInput(e: WechatMiniprogram.Input) {
    this.setData({ inviteCode: e.detail.value.trim() })
  },

  /** 创建群组 */
  async onCreate() {
    const name = (this.data.name || '').trim()
    if (!name) {
      wx.showToast({ title: '请输入群组名称', icon: 'none' })
      return
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })
    wx.showLoading({ title: '创建中' })
    try {
      const group = await post<JoinResult>('/groups', { name })
      wx.hideLoading()
      wx.showToast({ title: '创建成功' })
      setTimeout(() => {
        wx.redirectTo({ url: `/pages/group/detail/index?id=${group.id}` })
      }, 600)
    } catch (err) {
      wx.hideLoading()
      console.error('创建群组失败', err)
      wx.showToast({ title: '创建失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /** 邀请码加入群组 */
  async onJoin() {
    const inviteCode = this.data.inviteCode
    if (!inviteCode) {
      wx.showToast({ title: '请输入邀请码', icon: 'none' })
      return
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })
    wx.showLoading({ title: '加入中' })
    try {
      const group = await post<JoinResult>('/groups/join-by-code', { invite_code: inviteCode })
      wx.hideLoading()
      wx.showToast({ title: `已加入「${group.name}」` })
      setTimeout(() => {
        wx.redirectTo({ url: `/pages/group/detail/index?id=${group.id}` })
      }, 800)
    } catch (err) {
      wx.hideLoading()
      console.error('加入群组失败', err)
      const detail = (err as { data?: { detail?: string } })?.data?.detail
      wx.showToast({ title: detail || '加入失败，请检查邀请码', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
