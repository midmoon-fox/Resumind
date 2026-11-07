import { ElMessage } from 'element-plus';
import 'element-plus/es/components/message/style/css';

export function useToast() {
  function notify(text: string) {
    ElMessage({ message: text, type: 'info', grouping: true, showClose: true });
  }
  function success(text: string) {
    ElMessage({ message: text, type: 'success', grouping: true, showClose: true });
  }
  function error(text: string) {
    ElMessage({ message: text, type: 'error', grouping: true, showClose: true, duration: 6000 });
  }
  function warning(text: string) {
    ElMessage({ message: text, type: 'warning', grouping: true, showClose: true, duration: 5000 });
  }
  return { notify, success, warning, error };
}
