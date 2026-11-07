import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { useToast } from './composables/useToast';
import './styles/main.css';
import 'element-plus/es/components/message-box/style/css';

document.documentElement.classList.add('js');

const app = createApp(App);
app.config.errorHandler = (cause) => {
  console.error('页面操作异常', cause);
  useToast().error('页面操作失败，请重试；若仍失败，请刷新页面后再操作。');
};
window.addEventListener('unhandledrejection', (event) => {
  console.error('异步操作异常', event.reason);
  useToast().error('操作未能完成，请检查网络后重试。');
});
app.use(router).mount('#app');

import './styles/resume.css';
import './styles/workspace.css';

import './styles/refinement.css';
import './styles/signature-motion.css';

import './styles/element-theme.css';

import './styles/product-polish.css';
import './styles/liquid-glass.css';
