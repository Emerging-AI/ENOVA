import { createI18n } from 'vue-i18n'
import zhLoacles from './lang/zh'
import enLocales from './lang/en'
const getLocale = (): string => {
  let locale = localStorage.getItem('lang')
  if (!locale) {
    locale = navigator.language.split('-')[0]
  }
  if (!locale || locale === 'zh') {
    locale = 'zh_CN'
  }
  return locale
}

const i18n = createI18n({
  locale: getLocale(),
  legacy: false,
  globalInjection: true,
  fallbackLocale: 'zh_CN',
  messages: {
    zh_CN: { ...zhLoacles },
    en: { ...enLocales }
  }
})

export default i18n
