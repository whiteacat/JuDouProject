// 登录态管理：wx.login -> POST /auth/wechat/login -> 存 token 与用户信息
import { post } from './request'

export interface UserProfile {
  id: number
  nickname: string
  avatar_url: string
}

export interface LoginResponse {
  access_token: string
  user: UserProfile
}

export async function login(): Promise<LoginResponse> {
  return new Promise((resolve, reject) => {
    wx.login({
      success: async (res) => {
        if (!res.code) {
          reject(new Error('wx.login 未返回 code'))
          return
        }
        try {
          const data = await post<LoginResponse>('/auth/wechat/login', { code: res.code })
          wx.setStorageSync('token', data.access_token)
          wx.setStorageSync('userInfo', data.user)
          resolve(data)
        } catch (err) {
          reject(err)
        }
      },
      fail: (err) => reject(err)
    })
  })
}

export function isLoggedIn(): boolean {
  return Boolean(wx.getStorageSync('token'))
}

export function getUserProfile(): UserProfile | null {
  const info = wx.getStorageSync('userInfo') as UserProfile
  return info || null
}
