import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import WishlistPage from './pages/WishlistPage.vue'
import FriendsPage from './pages/FriendsPage.vue'
import UiKitPage from './pages/UiKitPage.vue'
import './styles/index.css'
import { preloadCovers } from './shared/covers'
import { initTheme } from './shared/theme'

const cleanupTheme = initTheme()
preloadCovers()
if (import.meta.hot) import.meta.hot.dispose(cleanupTheme)

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: (to) => ({ path: '/me', query: to.query, hash: to.hash }) },
    { path: '/me', component: WishlistPage },
    { path: '/friends', component: FriendsPage },
    { path: '/ui', component: UiKitPage },
    { path: '/users/:id/wishlist', component: WishlistPage },
    { path: '/users/:id/surprises', component: WishlistPage },
    { path: '/:pathMatch(.*)*', redirect: '/me' },
  ],
  scrollBehavior: (to, from) => {
    if (
      to.path.startsWith('/users/') &&
      from.path.startsWith('/users/') &&
      to.params.id === from.params.id
    )
      return false
    return { top: 0 }
  },
})

createApp(App).use(router).mount('#app')
