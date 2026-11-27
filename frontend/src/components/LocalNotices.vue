<script setup>
import {ref} from 'vue'
import {read} from '../api/library.js'
defineProps({editor:Boolean})
const key='fanqie_', announcement=ref(read(key+'announcement_v1',null)), dismissed=ref(read(key+'ann_dismissed_v1',false)),title=ref(announcement.value?.title||''),body=ref(announcement.value?.body||'')
function close(){dismissed.value=true;localStorage.setItem(key+'ann_dismissed_v1','true')}
function save(clear=false){announcement.value=clear?null:{title:title.value.trim(),body:body.value.trim()};localStorage.setItem(key+'announcement_v1',JSON.stringify(announcement.value));dismissed.value=false;localStorage.removeItem(key+'ann_dismissed_v1');if(clear){title.value='';body.value=''}}
</script><template><aside v-if="announcement&&!dismissed" class="notice"><b>{{announcement.title||'公告'}}</b><p>{{announcement.body}}</p><button @click="close">关闭公告</button></aside><section v-if="editor"><h2>本机公告</h2><form class="stack" @submit.prevent="save()"><label>标题<input v-model="title"></label><label>内容<textarea required v-model="body"></textarea></label><div class="row"><button>保存公告</button><button type="button" @click="save(true)">清除公告</button></div><small>沿用旧版存储方式，仅影响当前浏览器。</small></form></section></template>
