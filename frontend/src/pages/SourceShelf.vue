<script setup>
import {computed,nextTick,ref,onUnmounted} from 'vue'
import BookCover from '../components/BookCover.vue'
import Icon from '../components/LineIcon.vue'
import {api,label,read,search,normal,download} from '../api/library.js'
const p=defineProps({source:String,user:Object}), emit=defineEmits(['quota','files'])
const query=ref(''), result=ref(null), book=ref(null), mode=ref('search'), links=ref(''), fmt=ref('txt'), busy=ref(false), loading=ref(false), status=ref(''), page=ref(1), last=ref('')
const searchField=ref(null), resultsTitle=ref(null)
const pageCount=computed(()=>result.value ? Math.ceil(result.value.total / result.value.per_page) : 0)
async function turnPage(target){
  if(loading.value || target<1 || target>pageCount.value)return
  const previous=result.value
  await find(target,last.value)
  await nextTick()
  if(result.value!==previous && resultsTitle.value?.getClientRects().length){
    resultsTitle.value.focus({preventScroll:true})
    resultsTitle.value.scrollIntoView({block:'start'})
  }
}
let composing=false
function submitSearch(){
  if(composing || loading.value || !query.value.trim())return
  if(matchMedia('(max-width:719px)').matches)searchField.value?.blur()
  find()
}
const historyKey='fanqie_search_history_v1', history=ref(read(historyKey,[])), confirmed=ref(false)
let alive=true
onUnmounted(()=>alive=false)
async function find(n=1,q=query.value.trim()){if(!q||loading.value)return;loading.value=true;status.value='';try{const r=await search(p.source,q,n);result.value=r;page.value=r.page;last.value=query.value=q;if(p.source==='fanqie'){history.value=[q,...history.value.filter(v=>v!==q)].slice(0,12);localStorage.setItem(historyKey,JSON.stringify(history.value))}}catch(e){status.value=e.message}finally{loading.value=false}}
async function open(b){if(loading.value)return;loading.value=true;status.value='';try{book.value=p.source==='fanqie'?normal({...b,...await api('/book_detail?book_id='+encodeURIComponent(b.id))}):b;fmt.value='txt'}catch(e){status.value=e.message}finally{loading.value=false}}
const historyOpen=ref(false), historyToggle=ref(null)
function pickHistory(q){
  if(loading.value)return
  query.value=q
  historyToggle.value?.focus({preventScroll:true})
  historyOpen.value=false
  find(1,q)
}
function clearHistory(){historyOpen.value=false;history.value=[];localStorage.removeItem(historyKey);resultsTitle.value?.focus({preventScroll:true})}
function change(m){mode.value=m;book.value=null;status.value='';confirmed.value=false}
function entries(){return book.value?[{book_id:book.value.id,book_name:book.value.book_name,author:book.value.author}]:links.value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).map(url=>({url}))}
function stage(){const n=entries().length;if(!n){status.value='请先粘贴链接或书籍 ID。';return}if(!p.user.is_admin && n>p.user.download_quota){status.value='剩余次数不足，请在账户页兑换卡密。';return}confirmed.value=true;status.value=''}
async function run(){if(!confirmed.value||busy.value)return;confirmed.value=false;busy.value=true;const rows=entries(), receipts=[];try{for(const [i,row] of rows.entries()){if(!alive)break;const prefix=rows.length>1?`${i+1}/${rows.length}　`:'';status.value=prefix+'正在提交…';try{const text=await download(p.source,{...row,format:fmt.value},m=>status.value=prefix+m,n=>emit('quota',n),()=>alive);if(text)receipts.push(prefix+text)}catch(e){receipts.push(prefix+e.message)}}status.value=receipts.join('\n')}finally{busy.value=false}}
defineExpose({switchMode(m){if(!busy.value&&!loading.value)change(m)}})
</script>
<template><section class="source" :class="source">
<div class="shelf-toolbar"><h1>{{label[source]}}<em>书架</em></h1>
<div class="switcher"><button v-for="m in ['search','link']" :aria-pressed="mode===m" :disabled="busy||loading" @click="change(m)"><Icon :name="m==='search'?'search':'link'"/>{{m==='search'?'找书':'链接下载'}}</button></div></div>
<div v-if="book" class="panel appear"><button class="quiet" :disabled="busy" @click="change('search')">← 返回搜索结果</button><div class="detail"><BookCover :book="book"/><div><small>{{book.category||label[source]}}</small><h2>{{book.book_name}}</h2><p>{{book.author}}</p><small>{{book.status || (book.is_over==='1'?'已完结':'')}} {{book.chapter_count ? book.chapter_count+' 章' : ''}} {{(book.words_num||book.word_count)?Number(book.words_num||book.word_count).toLocaleString()+' 字':''}} {{book.score?book.score+' 分':''}}</small><p v-if="book.ptags">{{(Array.isArray(book.ptags)?book.ptags:String(book.ptags).split(',')).join(' / ')}}</p></div></div><p>{{book.description||'暂无简介'}}</p></div>
<template v-else-if="mode==='search'"><form class="searchbox" @submit.prevent="submitSearch"><Icon name="search"/><input ref="searchField" enterkeyhint="search" @compositionstart="composing=true" @compositionend="composing=false" aria-label="书名或作者" v-model="query" type="search" placeholder="输入书名或作者"><button class="primary" :disabled="loading">{{loading?'查找中':'搜索'}}</button></form>
<section v-if="source==='fanqie' && history.length" class="recent" @keydown.esc.stop="historyOpen=false;historyToggle?.focus()">
  <div class="recent-head"><button type="button" ref="historyToggle" class="recent-toggle" :aria-expanded="historyOpen" aria-controls="recent-terms" @click="historyOpen=!historyOpen"><i aria-hidden="true"></i>最近搜索 <small>{{history.length}}</small></button><button v-if="historyOpen" type="button" class="recent-clear" :disabled="loading" @click="clearHistory">清空记录</button></div>
  <div id="recent-terms" class="recent-fold" :class="{expanded:historyOpen}" :inert="!historyOpen"><div class="recent-clip"><div class="recent-tags"><button v-for="q in history" :key="q" type="button" :disabled="loading" @click="pickHistory(q)">{{q}}</button></div></div></div>
</section>
<h2 v-if="result" ref="resultsTitle" tabindex="-1" class="result-heading">搜索结果 <small>{{result.total}} 本</small></h2><div class="shelf"><button class="book" v-for="b in result?.items" :key="b.id" @click="open(b)"><BookCover :book="b"/><span class="book-copy"><b>{{b.book_name}}</b><small v-if="b.author">{{b.author}}</small></span><span v-if="b.category" class="book-category">{{b.category}}</span></button></div><p v-if="result && !result.total" class="empty">没有找到这本书，试试作者名。</p><div v-if="pageCount>1" class="search-pager" role="group" aria-label="搜索结果分页"><button :disabled="loading||page<=1" @click="turnPage(page-1)">‹ 上一页</button><span aria-live="polite">第 <b>{{page}}</b> / {{pageCount}} 页</span><button :disabled="loading||page>=pageCount" @click="turnPage(page+1)">下一页 ›</button></div></template>
<div v-else class="panel appear"><label>分享链接或书籍 ID<textarea enterkeyhint="enter" autocapitalize="off" spellcheck="false" v-model="links" :disabled="busy||confirmed" rows="4" placeholder="每行一本，可一次粘贴多条"></textarea></label></div>
<div v-if="book||mode==='link'" class="options panel"><div class="row"><b>文件格式</b><label v-for="f in ['txt','epub']"><input type="radio" :value="f" v-model="fmt" :disabled="busy||confirmed"> {{f.toUpperCase()}}</label></div><button v-if="!confirmed" class="primary" :disabled="busy" @click="stage">{{busy?'处理中…':'开始下载'}}</button><div v-else class="appear"><p>{{entries().length}} 本，{{user.is_admin?'管理员不扣次数':`将使用 ${entries().length} 次下载额度`}}。</p><button class="primary" @click="run">确认下载</button> <button @click="confirmed=false">取消</button></div></div>
<p v-if="status" role="status" class="notice">{{status}}</p><button v-if="status && !busy && (book||mode==='link')" @click="emit('files')">查看我的文件 →</button></section></template>
<style scoped>
.recent{margin-top:6px;border-bottom:1px solid var(--line)}
.recent-head,.recent-toggle,.recent-tags{display:flex;align-items:center}.recent-head{justify-content:space-between}
.recent-head button,.recent-tags button{border:0;background:transparent;color:var(--muted);font-size:13px}
.recent-toggle{gap:8px;padding:0 8px}.recent-toggle small{font-size:12px;font-variant-numeric:tabular-nums}.recent-toggle i{width:7px;height:7px;border:solid currentColor;border-width:0 1.5px 1.5px 0;transform:rotate(-45deg);transition:transform .18s}.recent-toggle[aria-expanded=true] i{transform:rotate(45deg)}
.recent-fold{display:grid;grid-template-rows:0fr;opacity:0;transition:grid-template-rows .19s ease-out,opacity .16s}.recent-fold.expanded{grid-template-rows:1fr;opacity:1}.recent-clip{overflow:hidden;min-height:0}.recent-tags{flex-wrap:wrap;gap:0 6px;padding:0 4px 6px}.recent-tags button{max-width:100%;overflow-wrap:anywhere;position:relative;isolation:isolate;padding:4px 10px;color:var(--text)}.recent-tags button::before{content:'';position:absolute;z-index:-1;inset:5px 0;background:var(--raised);border-radius:5px;transition:background .12s,transform .12s}.recent-head button:active,.recent-tags button:active{color:var(--accent)}.recent-tags button:active::before{transform:scale(.96);background:var(--line)}
@media(hover:hover){.recent-head button:hover,.recent-tags button:hover{color:var(--accent)}}
.search-pager{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px;margin-top:8px;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
.search-pager button{border:0;background:none;color:var(--accent);font-size:14px;justify-self:start;padding-inline:8px}.search-pager button:last-child{justify-self:end}.search-pager button:disabled{color:var(--muted);opacity:.5}.search-pager b{color:var(--text);font-weight:600}.result-heading{scroll-margin-top:12px}.result-heading:focus:not(:focus-visible){outline:none}
</style>
