export type CardOrigin = {
  left: number
  top: number
  width: number
  height: number
  photoRatio?: number
  background?: string
  backgroundImage?: string
  photo?: { left: number; top: number; width: number; height: number; src: string }
}
