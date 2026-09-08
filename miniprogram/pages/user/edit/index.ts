// 编辑用户资料页：修改昵称 + 选择头像（微信头像 / 预设头像）
import { getUserProfile, UserProfile } from '../../../utils/auth'
import { patch } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'

/** 预设头像列表（与后端 PRESET_AVATARS 同步） */
const PRESET_AVATARS = [
  'preset://avatar/1',
  'preset://avatar/2',
  'preset://avatar/3',
  'preset://avatar/4',
  'preset://avatar/5',
  'preset://avatar/6',
  'preset://avatar/7',
  'preset://avatar/8',
]

const PRESET_AVATAR_SRCS = PRESET_AVATARS.map(resolveAvatarSrc)

Page({
  data: {
    nickname: '',
    avatarUrl: '',
    /** 用于展示的头像图片地址 */
    avatarSrc: '',
    presetAvatars: PRESET_AVATARS,
    presetAvatarSrcs: PRESET_AVATAR_SRCS,
    /** 当前选中的预设头像 key（空串表示未选预设） */
    selectedPreset: '',
    submitting: false,
  },

  onLoad() {
    const profile: UserProfile | null = getUserProfile()
    if (profile) {
      const isPreset = profile.avatar_url.startsWith('preset://')
      this.setData({
        nickname: profile.nickname || '',
        avatarUrl: profile.avatar_url || '',
        avatarSrc: resolveAvatarSrc(profile.avatar_url || ''),
        selectedPreset: isPreset ? profile.avatar_url : '',
      })
    }
  },

  /** 选择微信头像（open-type="chooseAvatar" 回调） */
  onChooseAvatar(e: WechatMiniprogram.ButtonChooseAvatar) {
    this.setData({
      avatarUrl: e.detail.avatarUrl,
      avatarSrc: e.detail.avatarUrl,
      selectedPreset: '',
    })
  },

  /** 选择预设头像 */
  onSelectPreset(e: WechatMiniprogram.TouchEvent) {
    const key = e.currentTarget.dataset.key as string
    this.setData({
      avatarUrl: key,
      avatarSrc: resolveAvatarSrc(key),
      selectedPreset: key,
    })
  },

  onNicknameInput(e: WechatMiniprogram.Input) {
    this.setData({ nickname: e.detail.value })
  },

  async onSave() {
    const { nickname, avatarUrl } = this.data
    if (!nickname.trim()) {
      wx.showToast({ title: '请输入昵称', icon: 'none' })
      return
    }
    if (!avatarUrl) {
      wx.showToast({ title: '请选择头像', icon: 'none' })
      return
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })
    wx.showLoading({ title: '保存中' })
    try {
      const user = await patch<UserProfile>('/users/me', {
        nickname: nickname.trim(),
        avatar_url: avatarUrl,
      })
      wx.setStorageSync('userInfo', user)
      wx.showToast({ title: '保存成功' })
      setTimeout(() => wx.navigateBack(), 800)
    } catch (err: unknown) {
      console.error('保存失败', err)
      const msg = (err as { data?: { detail?: string } })?.data?.detail || '保存失败'
      wx.showToast({ title: msg, icon: 'none' })
    } finally {
      this.setData({ submitting: false })
      wx.hideLoading()
    }
  },
})
