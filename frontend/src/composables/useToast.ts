import { ElMessage } from 'element-plus';
import 'element-plus/es/components/message/style/css';

export function useToast() {
  function notify(text: string) {
    ElMessage({ message: text, type: 'info', grouping: true });
  }
  function success(text: string) {
    ElMessage({ message: text, type: 'success', grouping: true });
  }
  function error(text: string) {
    ElMessage({ message: text, type: 'error', grouping: true });
  }
  return { notify, success, error };
}
