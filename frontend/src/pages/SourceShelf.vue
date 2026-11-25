<script setup>
import {ref,onUnmounted,onMounted} from 'vue'
import BookCover from '../components/BookCover.vue'
import Icon from '../components/LineIcon.vue'
import {api,live,label,read,search,normal,download} from '../api/library.js'
const p=defineProps({source:String,user:Object}), emit=defineEmits(['quota','files'])
const query=ref(live?'':p.source==='fanqie'?'山海':'夜航'), result=ref(null), book=ref(null), mode=ref('search'), links=ref(''), fmt=ref('txt'), busy=ref(false), loading=ref(false), status=ref(''), page=ref(1), last=ref('')
const historyKey=(live?'':'demo_')+'fanqie_search_history_v1', history=ref(read(historyKey,[])), confirmed=ref(false)
let alive=true
onUnmounted(()=>alive=false)
async function find(n=1,q=query.value.trim()){if(!q||loading.value)return;loading.value=true;status.value='';try{const r=await search(p.source,q,n);result.value=r;page.value=r.page;last.value=query.value=q;if(p.source==='fanqie'){history.value=[q,...history.value.filter(v=>v!==q)].slice(0,12);localStorage.setItem(historyKey,JSON.stringify(history.value))}}catch(e){status.value=e.message}finally{loading.value=false}}
onMounted(()=>{if(!live)find()})
async function open(b){if(loading.value)return;loading.value=true;status.value='';try{book.value=live&&p.source==='fanqie'?normal({...b,...await api('/book_detail?book_id='+encodeURIComponent(b.id))}):b;fmt.value='txt'}catch(e){status.value=e.message}finally{loading.value=false}}
function clearHistory(){history.value=[];localStorage.removeItem(historyKey)}
function change(m){mode.value=m;book.value=null;status.value='';confirmed.value=false}
function entries(){return book.value?[{book_id:book.value.id,book_name:book.value.book_name,author:book.value.author}]:links.value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).map(url=>({url}))}
function stage(){const n=entries().length;if(!n){status.value='请先粘贴链接或书籍 ID。';return}if(!p.user.is_admin && n>p.user.download_quota){status.value='剩余次数不足，请在账户页兑换卡密。';return}confirmed.value=true;status.value=''}
async function run(){if(!confirmed.value||busy.value)return;confirmed.value=false;busy.value=true;const rows=entries(), receipts=[];try{for(const [i,row] of rows.entries()){if(!alive)break;const prefix=rows.length>1?`${i+1}/${rows.length}　`:'';status.value=prefix+'正在提交…';try{const text=await download(p.source,{...row,format:fmt.value},m=>status.value=prefix+m,n=>emit('quota',n),()=>alive);if(text)receipts.push(prefix+text)}catch(e){receipts.push(prefix+e.message)}}status.value=receipts.join('\n')}finally{busy.value=false}}
</script>
<template><section class="source" :class="source">
<div class="eyebrow"><span class="dot"></span>{{ source==='fanqie'?'SOURCE 01':'SOURCE 02' }} / {{live?'在线书源':'演示书源'}}</div>
<h1>{{label[source]}}<em>书架</em></h1>
<div class="switcher"><button v-for="m in ['search','link']" :aria-pressed="mode===m" :disabled="busy||loading" @click="change(m)"><Icon :name="m==='search'?'search':'link'"/>{{m==='search'?'找书':'链接下载'}}</button></div>
<div v-if="book" class="panel appear"><button class="quiet" :disabled="busy" @click="change('search')">← 返回搜索结果</button><div class="detail"><BookCover :book="book"/><div><small>{{book.category||label[source]}}</small><h2>{{book.book_name}}</h2><p>{{book.author}}</p><small>{{book.status || (book.is_over==='1'?'已完结':'')}} {{book.chapter_count ? book.chapter_count+' 章' : ''}}</small></div></div><p>{{book.description||'暂无简介'}}</p></div>
<template v-else-if="mode==='search'"><form class="searchbox" @submit.prevent="find()"><Icon name="search"/><input aria-label="书名或作者" v-model="query" type="search" placeholder="输入书名或作者"><button class="primary" :disabled="loading">{{loading?'查找中':'搜索'}}</button></form>
<details v-if="source==='fanqie' && history.length"><summary>最近搜索</summary><button class="chip" v-for="q in history" @click="find(1,q)">{{q}}</button><button class="quiet" @click="clearHistory">清空</button></details>
<h2>搜索结果 <small v-if="result">{{result.total}} 本</small></h2><div class="shelf"><button class="book" v-for="(b,i) in result?.items" :key="b.id" :style="{'--i':Math.min(i,5)}" @click="open(b)"><BookCover :book="b"/><b>{{b.book_name}}</b><small>{{b.author}}</small></button></div><p v-if="!result?.total" class="empty">{{result?'没有找到这本书，试试作者名。':'输入书名，开始查找。'}}</p><div v-if="result?.total>12" class="row"><button :disabled="loading||page<=1" @click="find(page-1,last)">上一页</button>{{page}}<button :disabled="loading||page*12>=result.total" @click="find(page+1,last)">下一页</button></div></template>
<div v-else class="panel appear"><label>分享链接或书籍 ID<textarea v-model="links" :disabled="busy||confirmed" rows="4" placeholder="每行一本，可一次粘贴多条"></textarea></label></div>
<div v-if="book||mode==='link'" class="options panel"><div class="row"><b>文件格式</b><label v-for="f in ['txt','epub']"><input type="radio" :value="f" v-model="fmt" :disabled="busy||confirmed"> {{f.toUpperCase()}}</label></div><button v-if="!confirmed" class="primary" :disabled="busy" @click="stage">{{busy?'处理中…':live?'开始下载':'模拟下载'}}</button><div v-else class="appear"><p>{{entries().length}} 本，{{user.is_admin?'管理员不扣次数':`将使用 ${entries().length} 次${live?'下载':'演示'}额度`}}。</p><button class="primary" @click="run">确认下载</button> <button @click="confirmed=false">取消</button></div></div>
<p v-if="status" role="status" class="notice">{{status}}</p><button v-if="status && !busy && (book||mode==='link')" @click="emit('files')">查看我的文件 →</button></section></template>
