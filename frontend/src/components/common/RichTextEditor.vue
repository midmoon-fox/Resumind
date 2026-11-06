<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue';
import { EditorContent, useEditor, Mark, mergeAttributes } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextStyle from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Underline as UnderlineIcon,
  Undo2,
  Redo2,
} from '@lucide/vue';
import { safeHtml } from '../../utils/content';
const props = defineProps<{ modelValue: string; label?: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const BackendLink = Mark.create({
  name: 'link',
  addAttributes: () => ({ href: { default: null } }),
  parseHTML: () => [
    {
      tag: 'a[href]',
      getAttrs: (element) =>
        /^https?:\/\//.test((element as HTMLElement).getAttribute('href') ?? '') ? null : false,
    },
  ],
  renderHTML: ({ HTMLAttributes }) => [
    'a',
    mergeAttributes(HTMLAttributes, { rel: 'noopener noreferrer' }),
    0,
  ],
});
const editor = useEditor({
  extensions: [
    StarterKit.configure({
      heading: false,
      strike: false,
      codeBlock: false,
      code: false,
      blockquote: false,
      horizontalRule: false,
    }),
    Underline,
    BackendLink,
    TextStyle,
    Color,
  ],
  content: safeHtml(props.modelValue),
  editorProps: {
    attributes: {
      role: 'textbox',
      'aria-label': props.label || '经历描述',
      'aria-multiline': 'true',
    },
  },
  onUpdate: ({ editor }) => emit('update:modelValue', safeHtml(editor.getHTML())),
});
watch(
  () => props.modelValue,
  (value) => {
    if (editor.value && safeHtml(value) !== editor.value.getHTML())
      editor.value.commands.setContent(safeHtml(value), false);
  },
);
onBeforeUnmount(() => editor.value?.destroy());
</script>
<template>
  <div v-if="editor" class="rich-editor">
    <div class="rich-toolbar" role="toolbar" aria-label="文字格式">
      <button
        type="button"
        aria-label="加粗"
        :aria-pressed="editor.isActive('bold')"
        @click="editor.chain().focus().toggleBold().run()"
      >
        <Bold :size="15" />
      </button>
      <button
        type="button"
        aria-label="斜体"
        :aria-pressed="editor.isActive('italic')"
        @click="editor.chain().focus().toggleItalic().run()"
      >
        <Italic :size="15" />
      </button>
      <button
        type="button"
        aria-label="下划线"
        :aria-pressed="editor.isActive('underline')"
        @click="editor.chain().focus().toggleUnderline().run()"
      >
        <UnderlineIcon :size="15" />
      </button>
      <button
        type="button"
        aria-label="项目符号列表"
        :aria-pressed="editor.isActive('bulletList')"
        @click="editor.chain().focus().toggleBulletList().run()"
      >
        <List :size="15" />
      </button>
      <button
        type="button"
        aria-label="编号列表"
        :aria-pressed="editor.isActive('orderedList')"
        @click="editor.chain().focus().toggleOrderedList().run()"
      >
        <ListOrdered :size="15" />
      </button>
      <label class="rich-color"
        >文字颜色<ElSelect
          aria-label="文字颜色"
          :model-value="editor.getAttributes('textStyle').color || '#333333'"
          @change="editor.chain().focus().setColor(String($event)).run()"
          ><ElOption value="#333333" :label="'深灰'" />
          <ElOption value="#1F2937" :label="'黑灰'" />
          <ElOption value="#2563EB" :label="'蓝色'" /></ElSelect
      ></label>
      <button
        type="button"
        aria-label="撤销文字编辑"
        :disabled="!editor.can().undo()"
        @click="editor.chain().focus().undo().run()"
      >
        <Undo2 :size="15" />
      </button>
      <button
        type="button"
        aria-label="重做文字编辑"
        :disabled="!editor.can().redo()"
        @click="editor.chain().focus().redo().run()"
      >
        <Redo2 :size="15" />
      </button>
    </div>
    <EditorContent :editor="editor" />
  </div>
</template>
