// 路径规划：后端代理高德驾车/步行接口（坐标系 GCJ-02，与微信 gcj02 定位一致）。
import { get } from './request'

export type RouteMode = 'driving' | 'walking'

export interface RoutePlan {
  mode: RouteMode
  distance_m: number
  duration_s: number
  polyline: Array<[number, number]>
  mocked: boolean
}

export interface LngLat {
  longitude: number
  latitude: number
}

export function planRoute(origin: LngLat, dest: LngLat, mode: RouteMode): Promise<RoutePlan> {
  return get<RoutePlan>('/route/plan', {
    origin_lng: origin.longitude,
    origin_lat: origin.latitude,
    dest_lng: dest.longitude,
    dest_lat: dest.latitude,
    mode
  })
}

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)}米`
  return `${(meters / 1000).toFixed(1)}公里`
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return '1分钟内'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `约${minutes}分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? `约${hours}小时` : `约${hours}小时${rest}分钟`
}
