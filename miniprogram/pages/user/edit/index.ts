// 编辑用户资料页：修改昵称 + 选择头像（微信头像 / 预设头像）+ 个性签名 + 偏好设置
import { getUserProfile, UserProfile } from '../../../utils/auth'
import { patch } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'

const PRESET_AVATARS = [
  'preset://avatar/1', 'preset://avatar/2', 'preset://avatar/3', 'preset://avatar/4',
  'preset://avatar/5', 'preset://avatar/6', 'preset://avatar/7', 'preset://avatar/8',
]

const PRESET_AVATAR_SRCS = PRESET_AVATARS.map(resolveAvatarSrc)

const FOOD_PREFS = ['火锅', '日料', '烧烤', '甜品', '川菜', '粤菜', '西餐', '东南亚']
const PLAY_PREFS = ['电影', '桌游', '户外', '展览', '密室', 'KTV', '运动', '旅行']

Page({
  data: {
    nickname: '',
    avatarUrl: '',
    avatarSrc: '',
    signature: '',
    presetAvatars: PRESET_AVATARS,
    presetAvatarSrcs: PRESET_AVATAR_SRCS,
    selectedPreset: '',
    submitting: false,
    // 偏好
    foodPrefs: FOOD_PREFS,
    playPrefs: PLAY_PREFS,
    selectedFoodPrefs: [] as string[],
    selectedPlayPrefs: [] as string[],
    // 其他设置
    budget: '',
    distance: '',
    timePref: '',
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
        signature: profile.signature || '',
      })
    }
  },

  onChooseAvatar(e: { detail: { avatarUrl: string } }) {
    this.setData({
      avatarUrl: e.detail.avatarUrl,
      avatarSrc: e.detail.avatarUrl,
      selectedPreset: '',
    })
  },

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

  onSignatureInput(e: WechatMiniprogram.Input) {
    this.setData({ signature: e.detail.value })
  },

  onTogglePref(e: WechatMiniprogram.TouchEvent) {
    const tag = e.currentTarget.dataset.tag as string
    const group = e.currentTarget.dataset.group as string
    if (group === 'food') {
      const list = this.data.selectedFoodPrefs
      this.setData({
        selectedFoodPrefs: list.includes(tag) ? list.filter((t) => t !== tag) : [...list, tag]
      })
    } else {
      const list = this.data.selectedPlayPrefs
      this.setData({
        selectedPlayPrefs: list.includes(tag) ? list.filter((t) => t !== tag) : [...list, tag]
      })
    }
  },

  async onSave() {
    const { nickname, avatarUrl, signature } = this.data
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
        signature: (signature || '').trim(),
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
