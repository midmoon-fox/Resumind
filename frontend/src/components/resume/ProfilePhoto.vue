<script setup lang="ts">
import { ref } from 'vue';
import FileUpload from '../common/FileUpload.vue';
const props = defineProps<{ modelValue?: string | null }>();
const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>();
const error = ref('');
async function select(files: File[]) {
 error.value = '';
 const file = files[0]; if (!file) return;
 if (!['image/jpeg','image/png'].includes(file.type) || file.size > 20*1024*1024) { error.value='请选择 20MB 以内的 JPG 或 PNG 照片'; return; }
 const url=URL.createObjectURL(file);
 try {
 const image=new Image(); image.src=url; await image.decode();
 const canvas=document.createElement('canvas'); const ratio=Math.min(1,400/Math.max(image.width,image.height));
 canvas.width=Math.max(1,Math.round(image.width*ratio));canvas.height=Math.max(1,Math.round(image.height*ratio));
 const ctx=canvas.getContext('2d')!;ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);
 emit('update:modelValue',canvas.toDataURL('image/jpeg',0.82));
 } catch { error.value='无法读取照片，请换一张 JPG 或 PNG 图片'; } finally { URL.revokeObjectURL(url); }
}
</script>
<template><div class="profile-photo"><span>简历照片（选填）</span><img v-if="props.modelValue" :src="props.modelValue" alt="简历照片" /><FileUpload accept="image/jpeg,image/png" @select="select" /><button v-if="modelValue" type="button" class="text-link" @click="emit('update:modelValue',null)">移除照片</button><p v-if="error" role="alert" class="form-error">{{ error }}</p></div></template>
<style scoped>.profile-photo{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0}.profile-photo img{width:60px;height:80px;object-fit:cover;border-radius:6px}</style>
