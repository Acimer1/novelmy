<script setup>
import {ref} from 'vue'
import {api,live} from '../api/library.js'
import CopyButton from '../components/CopyButton.vue'
import AdminPanel from '../components/AdminPanel.vue'
const p=defineProps({user:Object}),emit=defineEmits(['quota','logout']);const code=ref(''),busy=ref(false),msg=ref('')
async function redeem(){if(!live||busy.value||!code.value.trim())return;busy.value=true;try{const d=await api('/card/redeem',{code:code.value.trim()});emit('quota',d.quota);code.value='';msg.value=`已增加 ${d.added} 次下载次数。`}catch(e){msg.value=e.message}finally{busy.value=false}}
async function logout(){if(busy.value)return;busy.value=true;try{await api('/auth/logout',{});emit('logout')}catch(e){msg.value=e.message}finally{busy.value=false}}
</script><template><section><div class="eyebrow">ACCOUNT / {{live?'在线':'演示'}}</div><h1>我的<em>账户</em></h1><div class="panel"><h2>{{p.user.username}}</h2><p>{{p.user.is_admin?'管理员不消耗下载次数':`剩余 ${p.user.download_quota} 次${live?'下载':'演示'}额度`}}</p><form v-if="!p.user.is_admin" class="searchbox" @submit.prevent="redeem"><input v-model="code" aria-label="卡密" placeholder="输入卡密" :disabled="!live"><button :disabled="!live||busy" class="primary">兑换</button></form><p v-if="!live"><small>演示模式不接受真实卡密或账号。</small></p><div class="row" v-if="live"><a href="https://wzyp.cn/shop/N0CQ5T2I" target="_blank" rel="noopener">购买卡密 ↗</a><a href="https://www.ldxp.cn/order" target="_blank" rel="noopener">查询订单 ↗</a></div></div><details><summary>联系管理员</summary><p>QQ：3637438435 <CopyButton text="3637438435" label="复制 QQ"/><br>微信：acimer <CopyButton text="acimer" label="复制微信"/><br>添加时请备注「小说下载」。</p></details><AdminPanel v-if="live&&p.user.is_admin"/><button v-if="live" :disabled="busy" @click="logout">退出登录</button><p role="status">{{msg}}</p></section></template>
