import { computed, ref } from 'vue';
import { useAppStore } from './useAppStore';
const search = ref('');
const sortOrder = ref<'updated' | 'name'>('updated');
export function useDashboard() {
  const { state, createResume } = useAppStore();
  const resumes = computed(() => state.resumes);
  const filteredResumes = computed(() =>
    state.resumes
      .filter((item) =>
        (item.title + ' ' + item.role).toLowerCase().includes(search.value.trim().toLowerCase()),
      )
      .sort((a, b) =>
        sortOrder.value === 'name'
          ? a.title.localeCompare(b.title, 'zh-CN')
          : Date.parse(b.updatedAt) - Date.parse(a.updatedAt),
      ),
  );
  return { resumes, search, sortOrder, filteredResumes, createDraft: createResume };
}
