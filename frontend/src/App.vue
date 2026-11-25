<script setup>
import {computed,nextTick,ref,onMounted,onUnmounted} from 'vue'
import GuidePage from './pages/GuidePage.vue'
import Icon from './components/LineIcon.vue'
import SourceShelf from './pages/SourceShelf.vue'
import LocalNotices from './components/LocalNotices.vue'
import FilesPage from './pages/FilesPage.vue'
import AuthPage from './pages/AuthPage.vue'
import AccountPage from './pages/AccountPage.vue'
import {api,live,read} from './api/library.js'
const tabs={fanqie:'番茄',qimao:'七猫',files:'文件',guide:'指南'},tab=ref('fanqie'),user=ref(live?null:{username:'演示读者',download_quota:3}),ready=ref(!live),error=ref('')
const key=(live?'':'demo_')+'fanqie_theme_v1',theme=ref(read(key,'dark')),seen=ref(read((live?'':'demo_')+'fanqie_guide_read_v1',false))
const activeSource=computed(()=>['fanqie','qimao'].includes(tab.value))
const visited=ref(new Set(['fanqie']))
function go(id){if(id==='fanqie'||id==='qimao')visited.value.add(id);tab.value=id;if(id==='guide'){seen.value=true;localStorage.setItem((live?'':'demo_')+'fanqie_guide_read_v1','true')}window.scrollTo(0,0)}
function toggle(){theme.value=theme.value==='light'?'dark':'light';localStorage.setItem(key,JSON.stringify(theme.value))}
function quota(n){if(user.value)user.value.download_quota=n??Math.max(0,user.value.download_quota-1)}
const allowAutoLogin=ref(true)
function expire(){allowAutoLogin.value=false;user.value=null;visited.value=new Set(['fanqie']);go('fanqie')}
async function init(){ready.value=false;error.value='';try{const d=await api('/auth/me');user.value=d.logged_in?d.user:null}catch(e){error.value=e.message}finally{ready.value=true}}
let timer;onMounted(()=>{window.addEventListener('session-expired',expire);if(live){init();timer=setInterval(async()=>{if(!user.value)return;const uid=user.value.id;try{const d=await api('/auth/me');if(user.value?.id!==uid)return;if(!d.logged_in)expire();else quota(d.user.download_quota)}catch{}},20000)}});onUnmounted(()=>{window.removeEventListener('session-expired',expire);clearInterval(timer)})
const shelves={}, stripKey=(live?'':'demo_')+'fanqie_guide_strip_dismissed_v1', dismissed=ref(read(stripKey,false))
function dismissStrip(){dismissed.value=true;localStorage.setItem(stripKey,'true')}
async function fromGuide(id, mode='search'){go(id);await nextTick();shelves[id]?.switchMode(mode)}
</script>
<template><div class="app" :data-theme="theme"><header><div class="bar"><button class="brand" @click="go('fanqie')"><i><Icon name="shelf"/></i> 小说书架</button><div class="tools"><span class="badge">{{live?'在线':'本地演示'}}</span><button :aria-label="theme==='dark'?'切换浅色':'切换深色'" @click="toggle"><Icon name="theme"/></button><button v-if="user" @click="go('account')" :title="user.is_admin?'管理账户':'增加下载次数'">{{user.is_admin?'管理':user.download_quota+' 次'}}</button><button v-if="user" aria-label="我的账户" @click="go('account')"><Icon name="person"/></button></div></div></header>
<nav v-if="user" aria-label="主导航"><button v-for="(text,id) in tabs" :key="id" :aria-current="tab===id?'page':undefined" @click="go(id)"><Icon :name="id"/>{{text}}</button></nav>
<main><p v-if="!ready">正在读取账户…</p><div v-else-if="error" class="panel"><p>{{error}}</p><button @click="init">重试连接</button></div><AuthPage v-else-if="!user" :allow-auto-login="allowAutoLogin" @login="u=>user=u"/><template v-else>
<LocalNotices :admin="!!user.is_admin" :account="tab==='account'" @guide="go('guide')"/>
<template v-for="src in ['fanqie','qimao']" :key="src"><SourceShelf :ref="el=>shelves[src]=el" v-if="src===tab || visited.has(src)" v-show="tab===src" :source="src" :user="user" @quota="quota" @files="go('files')"/></template>
<FilesPage v-if="tab==='files'" class="appear"/><AccountPage v-if="tab==='account'" :user="user" class="appear" @quota="quota" @logout="expire"/>
<GuidePage v-if="tab==='guide'" @go="fromGuide"/>
<p v-if="activeSource && !seen && !dismissed" class="guide-link"><button class="quiet" @click="go('guide')">第一次使用？查看下载指南 →</button><button class="quiet" @click="dismissStrip">不再提示</button></p></template></main></div></template>
<script>
// 保留切换书源前的查询和下载任务；退出账户时销毁两个页面。
</script>
