import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layout/index.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Layout,
      redirect: '/instance',
      children: [
        {
          path: '/instance',
          name: 'instance',
          component: () => import('../views/Instance.vue'),
          meta: {
            title: 'service',
            icon: 'docker'
          }
        },
        {
          path: '/record',
          name: 'testRecord',
          component: () => import('../views/TestRecord.vue'),
          meta: {
            title: 'record',
            icon: 'log'
          }
        }
      ]
    }
  ]
})

export default router
