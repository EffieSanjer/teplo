import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import WishlistPage from './features/WishlistPage.vue'
import FriendsPage from './features/FriendsPage.vue'
import './style.css'
import { initTheme } from './shared/theme'

const cleanupTheme = initTheme()
if (import.meta.hot) import.meta.hot.dispose(cleanupTheme)

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/me' },
    { path: '/me', component: WishlistPage },
    { path: '/friends', component: FriendsPage },
    { path: '/users/:id/wishlist', component: WishlistPage },
    { path: '/users/:id/surprises', component: WishlistPage },
    { path: '/:pathMatch(.*)*', redirect: '/me' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

createApp(App).use(router).mount('#app')
