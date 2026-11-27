<script setup>
import {nextTick,ref,onMounted,onUnmounted} from 'vue'
import GuidePage from './pages/GuidePage.vue'
import Icon from './components/LineIcon.vue'
import SourceShelf from './pages/SourceShelf.vue'
import LocalNotices from './components/LocalNotices.vue'
import FilesPage from './pages/FilesPage.vue'
import AuthPage from './pages/AuthPage.vue'
import AccountPage from './pages/AccountPage.vue'
import AdminPanel from './components/AdminPanel.vue'
import {api,read} from './api/library.js'
const tabs={fanqie:'番茄',qimao:'七猫',files:'文件',guide:'指南'}, tab=ref('fanqie'), user=ref(null), ready=ref(false), error=ref('')
const key='fanqie_theme_v1', theme=ref(read(key,'light'))
const welcomeKey='fanqie_welcome_seen_v1', welcome=ref(!read(welcomeKey,false)&&!read('fanqie_guide_read_v1',false)&&!read('fanqie_guide_strip_dismissed_v1',false))
const visited=ref(new Set(['fanqie'])), shelves={}
function dismissWelcome(){welcome.value=false;localStorage.setItem(welcomeKey,'true')}
function go(id){if(id==='fanqie'||id==='qimao')visited.value.add(id);tab.value=id;if(id==='guide'){localStorage.setItem('fanqie_guide_read_v1','true');dismissWelcome()}else if(id==='account'&&welcome.value)dismissWelcome();window.scrollTo(0,0)}
function toggle(){theme.value=theme.value==='light'?'dark':'light';localStorage.setItem(key,JSON.stringify(theme.value))}
function quota(n){if(user.value && typeof n==='number')user.value.download_quota=n}
const keyboardOpen=ref(false)
onMounted(()=>{
  const viewport=window.visualViewport
  if(!viewport)return
  let fullHeight=viewport.height, width=window.innerWidth
  function update(){
    const editing=document.activeElement?.matches('textarea,input:not([type=checkbox]):not([type=radio]):not([type=button])')
    if(width!==window.innerWidth){width=window.innerWidth;fullHeight=viewport.height}
    if(!editing || viewport.height>fullHeight)fullHeight=viewport.height
    keyboardOpen.value=!!editing && width<720 && viewport.scale===1 && fullHeight-viewport.height>120
  }
  viewport.addEventListener('resize',update);document.addEventListener('focusin',update);document.addEventListener('focusout',update)
  onUnmounted(()=>{viewport.removeEventListener('resize',update);document.removeEventListener('focusin',update);document.removeEventListener('focusout',update)})
})
const allowAutoLogin=ref(true)
function expire(){allowAutoLogin.value=false;user.value=null;visited.value=new Set(['fanqie']);go('fanqie')}
async function init(){ready.value=false;error.value='';try{const d=await api('/auth/me');user.value=d.logged_in?d.user:null}catch(e){error.value=e.message}finally{ready.value=true}}
let timer;onMounted(()=>{window.addEventListener('session-expired',expire);init();timer=setInterval(async()=>{if(!user.value)return;const uid=user.value.id;try{const d=await api('/auth/me');if(user.value?.id!==uid)return;if(!d.logged_in)expire();else quota(d.user.download_quota)}catch{}},20000)});onUnmounted(()=>{window.removeEventListener('session-expired',expire);clearInterval(timer)})
async function fromGuide(id, mode='search'){go(id);await nextTick();shelves[id]?.switchMode(mode)}
</script>
<template><div class="app" :class="{'keyboard-open':keyboardOpen}" :data-theme="theme"><header><div class="bar"><button class="brand" @click="go('fanqie')"><i aria-hidden="true"></i> 小说书架</button><div class="tools"><button :aria-label="theme==='dark'?'切换浅色':'切换深色'" @click="toggle"><Icon name="theme"/></button><button v-if="user" @click="go(user.is_admin?'admin':'account')" :title="user.is_admin?'管理工作台':'增加下载次数'">{{user.is_admin?'管理':user.download_quota+' 次'}}</button>
<div v-if="user" class="account-anchor"><button aria-label="我的账户" @click="go('account')"><Icon name="person"/></button><aside v-if="welcome" class="welcome-tip" aria-label="新手提示" @keydown.esc="dismissWelcome"><span>第一次使用书架？</span><button class="guide-action" @click="go('guide')">查看指南 →</button><button aria-label="关闭新手提示" @click="dismissWelcome">×</button></aside></div>
</div></div></header>
<nav v-if="user" aria-label="主导航"><button v-for="(text,id) in tabs" :key="id" :aria-current="tab===id?'page':undefined" @click="go(id)"><Icon :name="id"/>{{text}}</button></nav>
<main><p v-if="!ready">正在读取账户…</p><div v-else-if="error" class="panel"><p>{{error}}</p><button @click="init">重试连接</button></div><AuthPage v-else-if="!user" :allow-auto-login="allowAutoLogin" @login="u=>user=u"/><template v-else>
<LocalNotices v-if="tab!=='admin'"/>
<AdminPanel v-if="tab==='admin' && user.is_admin"/>
<template v-for="src in ['fanqie','qimao']" :key="src"><SourceShelf :ref="el=>shelves[src]=el" v-if="src===tab || visited.has(src)" v-show="tab===src" :source="src" :user="user" @quota="quota" @files="go('files')"/></template>
<FilesPage v-if="tab==='files'" class="appear"/><AccountPage v-if="tab==='account'" :user="user" class="appear" @quota="quota" @logout="expire"/><GuidePage v-if="tab==='guide'" @go="fromGuide"/></template></main></div></template>
<style scoped>
.account-anchor{position:relative}.welcome-tip{position:absolute;z-index:8;right:0;top:calc(100% + 5px);padding:0 2px 0 14px;display:flex;align-items:center;white-space:nowrap;border:1px solid var(--line);border-radius:13px;background:var(--surface);box-shadow:0 5px 18px #0002;font-size:13px}.welcome-tip::before{content:'';position:absolute;right:17px;top:-5px;width:8px;height:8px;transform:rotate(45deg);background:var(--surface);border-left:1px solid var(--line);border-top:1px solid var(--line)}.tools .guide-action{width:auto;padding:0 6px;color:var(--accent);font-size:13px}.welcome-tip span{color:var(--muted)}
</style>
