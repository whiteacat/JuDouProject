// 编辑用户资料页：修改昵称 + 选择头像（微信头像 / 预设头像）+ 个性签名 + 偏好设置
import { getUserProfile, UserProfile } from '../../../utils/auth'
import { patch } from '../../../utils/request'
import { resolveAvatarSrc } from '../../../utils/avatar'
import { isContentEditEnabled, CONTENT_EDIT_DISABLED_TIP } from '../../../utils/appSetting'

const PRESET_AVATARS = [
  'preset://avatar/1', 'preset://avatar/2', 'preset://avatar/3', 'preset://avatar/4',
  'preset://avatar/5', 'preset://avatar/6', 'preset://avatar/7', 'preset://avatar/8',
]

const PRESET_AVATAR_SRCS = PRESET_AVATARS.map(resolveAvatarSrc)

const FOOD_PREFS = ['火锅', '日料', '烧烤', '甜品', '川菜', '粤菜', '西餐', '东南亚']
const PLAY_PREFS = ['电影', '桌游', '户外', '展览', '密室', 'KTV', '运动', '旅行']

const BUDGET_OPTIONS = ['50以内', '50-100元', '100-200元', '200-500元', '500元以上']
const DISTANCE_OPTIONS = ['3km以内', '5km以内', '10km以内', '20km以内', '不限']
const TIME_PREFS = ['工作日晚上', '周末优先', '节假日', '随时']

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
    budgetOptions: BUDGET_OPTIONS,
    distanceOptions: DISTANCE_OPTIONS,
    timePrefOptions: TIME_PREFS,
    budget: '',
    distance: '',
    timePref: '',
  },

  onLoad() {
    const profile: UserProfile | null = getUserProfile()
    if (profile) {
      const isPreset = profile.avatar_url.startsWith('preset://')
      const prefs = profile.preferences || {}
      this.setData({
        nickname: profile.nickname || '',
        avatarUrl: profile.avatar_url || '',
        avatarSrc: resolveAvatarSrc(profile.avatar_url || ''),
        selectedPreset: isPreset ? profile.avatar_url : '',
        signature: profile.signature || '',
        selectedFoodPrefs: prefs.food || [],
        selectedPlayPrefs: prefs.play || [],
        budget: prefs.budget || '',
        distance: prefs.distance || '',
        timePref: prefs.time_pref || '',
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

  onBudgetChange(e: WechatMiniprogram.PickerChange) {
    this.setData({ budget: this.data.budgetOptions[Number(e.detail.value)] })
  },

  onDistanceChange(e: WechatMiniprogram.PickerChange) {
    this.setData({ distance: this.data.distanceOptions[Number(e.detail.value)] })
  },

  onTimePrefChange(e: WechatMiniprogram.PickerChange) {
    this.setData({ timePref: this.data.timePrefOptions[Number(e.detail.value)] })
  },

  async onSave() {
    const { nickname, avatarUrl, signature, selectedFoodPrefs, selectedPlayPrefs, budget, distance, timePref } = this.data
    // 内容编辑开关预检（提交包含文本字段，与后端守卫一致）
    if (!(await isContentEditEnabled())) {
      wx.showToast({ title: CONTENT_EDIT_DISABLED_TIP, icon: 'none' })
      return
    }
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
        preferences: {
          food: selectedFoodPrefs,
          play: selectedPlayPrefs,
          budget: budget || '',
          distance: distance || '',
          time_pref: timePref || ''
        },
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
