import { defineStore } from 'pinia'
import navImg from '@/assets/logo/emergingai_w.png'
import loginImg from '@/assets/logo/emergingai_b.png'

export const useAppStore = defineStore('app', {
  state: () => ({
    navLogo: {
      src: navImg,
      width: 'auto',
      height: '56px',
      alt: 'Emergingai'
    },
    loginLogo: {
      src: loginImg,
      width: '220px',
      height: 'auto',
      alt: 'Emergingai'
    },
    sidebarStatus: true
  }),
  actions: {
    toggleSideBar(): void {
      this.sidebarStatus = !this.sidebarStatus
    }
  }
})
