/** Warm the browser cache for both theme covers so theme switches stay instant. */
export function preloadCovers() {
  const urls =
    typeof window !== 'undefined' && window.matchMedia('(min-width: 769px)').matches
      ? [
          '/wishlist-cover-light.jpg',
          '/wishlist-cover-dark.jpg',
          '/wishlist-cover-mobile-light.jpg',
          '/wishlist-cover-mobile-dark.jpg',
        ]
      : ['/wishlist-cover-mobile-light.jpg', '/wishlist-cover-mobile-dark.jpg']

  for (const href of urls) {
    if (document.head.querySelector(`link[rel="preload"][href="${href}"]`)) continue
    const link = document.createElement('link')
    link.rel = 'preload'
    link.as = 'image'
    link.href = href
    document.head.appendChild(link)
  }
}
