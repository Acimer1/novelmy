<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import Icon from '../components/LineIcon.vue'
const emit = defineEmits(['go'])
const chapters = [
  {id:'fanqie', nav:'番茄下载', title:'从番茄下载第一本书', icon:'fanqie', steps:['打开「番茄」，在「找书」中输入书名关键词，点封面查看简介。','有分享链接时，选择「链接下载」，粘贴原链接或短链接。也可以直接填纯数字书籍 ID。','选择 TXT 或 EPUB，确认下载。番茄先创建任务；看到「文件已生成」后，再去「文件」取回。'], action:'去番茄找书'},
  {id:'qimao', nav:'七猫下载', title:'用七猫链接或书籍 ID 下载', icon:'qimao', steps:['在「七猫」按书名或作者查找，打开详情后选择 TXT 或 EPUB。','从七猫 App 复制的分享链接可直接粘贴。支持 app-share.wtzw.com、qimao.com、wtzw.com 的书籍链接，也支持纯数字书籍 ID。','确认后等待文件生成。长篇小说可能需要更长时间，不必再提交一次。'], action:'去七猫找书'},
  {id:'batch', nav:'批量导入', title:'多本书，一行一本', icon:'link', steps:['先按书源分开链接。进入相应书架的「链接下载」，每行粘贴一个链接或书籍 ID。','核对本数、格式和剩余次数，再点「确认下载」。系统按顺序逐本处理，进度中的 2/5 表示正在处理第 2 本。','普通用户每新增一本扣 1 次，已下载的书不会重复扣次。某行失败时，先看该行提示，不必重提整批。']},
  {id:'files', nav:'文件分卷', title:'取回文件，或把 TXT 分成几卷', icon:'files', steps:['打开「文件」，点「下载文件」保存整本小说。若番茄仍在校验，稍后点「刷新列表」。','文件太大时，展开「TXT 分卷」，选每卷大小，再点「开始分割」。一次最多生成 10 个文件，超过上限请调大每卷大小。','分卷不消耗次数。完成后按顺序保存各分卷；EPUB 直接下载原文件。'], action:'查看我的文件'},
  {id:'faq', nav:'常见问题', title:'遇到问题时', icon:'guide'}
]
const active=ref(0), sections=[]
function position(){const edge=matchMedia('(max-width:719px)').matches?56:innerHeight*.34;let index=0;for(let i=0;i<sections.length;i++){if(sections[i]?.getBoundingClientRect().top<=edge)index=i}if(innerHeight+scrollY>=document.documentElement.scrollHeight-2)index=chapters.length-1;active.value=index}
function jump(i){const target=sections[i];if(!target)return;active.value=i;target.focus({preventScroll:true});target.scrollIntoView({behavior:matchMedia('(max-width:719px), (prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'})}
onMounted(()=>{position();window.addEventListener('scroll',position,{passive:true});window.addEventListener('resize',position)})
onUnmounted(()=>{window.removeEventListener('scroll',position);window.removeEventListener('resize',position)})
</script>
<template><section class="guide appear"><h1>3 分钟<em>快速上手</em></h1><p class="intro">从找到一本书，到把它存进手机。选一章开始，也可以直接前往书架。</p><div class="row"><button class="primary" @click="emit('go','fanqie')">开始找书 →</button><button @click="emit('go','files')">查看已下载</button></div>
<div class="reading"><aside aria-label="章节目录"><label class="mobile-position"><span>阅读位置</span><b>{{active+1}} / {{chapters.length}}</b><strong>{{chapters[active].nav}}</strong><span class="choose">目录 ﹀</span><select aria-label="选择指南章节" :value="active" @change="jump(Number($event.target.value))"><option v-for="(c,i) in chapters" :key="c.id" :value="i">第 {{i+1}} 章　{{c.nav}}</option></select></label><small class="desktop-position">阅读位置　{{active+1}} / {{chapters.length}}</small><div class="rail"><button v-for="(c,i) in chapters" :key="c.id" :aria-current="active===i?'location':undefined" @click="jump(i)"><span>0{{i+1}}</span>{{c.nav}}</button></div></aside>
<div><section v-for="(c,i) in chapters" :key="c.id" :ref="el=>sections[i]=el" tabindex="-1" class="chapter"><div class="eyebrow"><Icon :name="c.icon"/> 0{{i+1}} / {{c.nav}}</div><h2>{{c.title}}</h2><ol v-if="c.steps"><li v-for="s in c.steps" :key="s">{{s}}</li></ol><template v-else><details open><summary>下载次数用完了？</summary><p>新注册的账户从 0 次开始。在「我的账户」兑换卡密，成功后可看到新的剩余次数。已付款但找不到卡密，请点「查询订单」。</p><button @click="emit('go','account')">去账户兑换</button></details><details><summary>链接解析失败？</summary><p>检查书源是否选对，重新从原书详情页复制分享链接。如果知道书籍 ID，可只填数字；也可以返回「找书」按书名搜索。</p></details><details><summary>找不到刚下载的书？</summary><p>进入「文件」刷新列表。任务已接受不等于文件已生成；看到校验提示时，不要重复提交。在微信内无法保存文件时，请复制页面链接，改用手机浏览器打开。</p></details></template><button v-if="c.action" class="quiet" @click="emit('go',c.id)">{{c.action}} →</button><div class="row" v-if="c.id==='batch'"><button @click="emit('go','fanqie','link')">导入番茄链接</button><button @click="emit('go','qimao','link')">导入七猫链接</button></div></section></div></div></section></template>
<style scoped>
.intro{color:var(--muted);max-width:36em}.reading{margin-top:32px;display:grid;gap:20px}.reading aside{align-self:start;position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;border-block:1px solid var(--line)}.rail{display:flex;overflow-x:auto;gap:4px}.rail button{white-space:nowrap;border:0;background:none;color:var(--muted);padding:6px 10px}.rail span{margin-right:5px;font-variant-numeric:tabular-nums}.rail [aria-current]{background:var(--raised);color:var(--accent)}.chapter{scroll-margin:100px;padding:22px 0 26px;border-bottom:1px solid var(--line)}.chapter h2{margin:8px 0 14px;text-wrap:balance}.chapter .eyebrow{display:flex;align-items:center;gap:9px;color:var(--accent)}.chapter ol{padding-left:1.5em}.chapter li{padding:3px 0 6px 4px}.chapter li::marker{color:var(--muted)}.chapter .quiet{color:var(--accent)}@media(min-width:720px){.reading{grid-template-columns:155px 1fr;gap:42px}.reading aside{top:22px}.rail{flex-direction:column;align-items:stretch}.rail button{text-align:left}.chapter{scroll-margin:20px}.chapter:first-child{padding-top:6px}}
.mobile-position{display:none}
@media(max-width:719px){
  .reading{grid-template-columns:minmax(0,1fr);margin-top:20px;gap:6px}
  .reading>*{min-width:0}
  .reading aside{padding:0}
  .desktop-position,.rail{display:none}
  .mobile-position{display:flex;align-items:center;gap:8px;position:relative;min-height:44px;color:var(--muted);font-size:12px}
  .mobile-position b{font-variant-numeric:tabular-nums;color:var(--accent)}.mobile-position strong{font-size:14px;color:var(--text)}.mobile-position .choose{margin-left:auto;color:var(--accent)}
  .mobile-position select{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}.mobile-position:focus-within{outline:2px solid var(--accent);outline-offset:-2px}
  .chapter{padding:16px 0;scroll-margin-top:55px;overflow-wrap:anywhere}
  .chapter h2{margin:6px 0 8px;font-size:18px}
  .chapter ol{margin:8px 0;padding-left:1.4em}
  .chapter li{padding:2px 0 4px 2px}
  .intro{margin:8px 0 12px}
}
</style>
