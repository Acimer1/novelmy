import { searchBooks } from './preview-api.js'

const mode = new URLSearchParams(location.search).get('mode')
export const live = mode === 'live' || (mode !== 'demo' && !import.meta.env.DEV)
export const label = { fanqie: '番茄', qimao: '七猫' }
export const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
export function read(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback } }
export async function api(path, body, method) {
  if (!live) throw new Error('演示模式不访问账户服务。')
  const prefix = location.pathname.startsWith('/novel/') && path.startsWith('/admin/users') ? '/novel' : ''
  const res = await fetch(`${prefix}/api${path}`, {credentials:'same-origin', method:method || (body ? 'POST' : 'GET'), ...(body ? {headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {})})
  const data = await res.json().catch(() => { throw new Error('服务未返回 JSON，请检查后端地址和登录状态。') })
  if (!res.ok || data.error) {
    if (res.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('session-expired'))
    throw Object.assign(new Error(data.error || '服务未返回有效结果，请稍后再试。'), {data})
  }
  return data
}
const cats = [
  {id:'cat-01', title:'夜航电台',author:'周野',category:'都市',intro:'每晚十点，一座沿江小城在电波里交换未寄出的信。'},
  {id:'cat-02', title:'夜航日志',author:'汀白',category:'冒险',intro:'领航员在旧地图背面，发现一条不在航线上的河。'},
  {id:'cat-03', title:'夜航以北',author:'沈时',category:'故事',intro:'从北方抵达的小船，带来一张二十年前的合照。'},
]
export function normal(b) { return {...b,id:String(b.book_id ?? b.id),book_name:b.book_name || b.title,cover_url:b.cover_url || b.image_link,description:(b.description || b.abstract || b.intro || '').replace(/<[^>]+>/g,'')} }
export async function search(source,q,page) {
  const data = live ? await api(`${source === 'qimao' ? '/qimao' : ''}/search?${new URLSearchParams({q,page,per_page:12})}`) : source === 'fanqie' ? searchBooks(q) : {items:cats.filter(b=>(b.title+b.author).includes(q)),page:1}
  return {...data,items:data.items.map(normal),total:data.total ?? data.items.length}
}
export const sampleFiles = []
export async function download(source, body, report, quota, active = () => true) {
  if (!live) {
    const name = body.book_name || body.url
    if (sampleFiles.some(f=>f.book_name===name && f.source===source)) throw new Error('这本书已在我的文件中。')
    for (const pct of [20,65,100]) { await delay(240); if (!active()) return; report(`正在模拟${source==='fanqie'?'下载任务':'生成文件'}　${pct}%`) }
    sampleFiles.unshift({book_name:name,author:body.author || '',file_name:`${name}.${body.format}`,source,size:0,demo:true})
    quota(null); return '演示完成，可在「文件」查看记录。'
  }
  const d = await api(source==='qimao'?'/qimao/download':'/download',body)
  if (!active()) return
  quota(d.quota)
  if (source==='qimao') return `文件已生成：${d.file_name}`
  let done = d.status==='done'
  for(let i=0; !done && i<150; i++) {
    report('任务已接受，正在等待文件…'); await delay(2000); if (!active()) return
    const {items=[]} = await api('/jobs'); if (!active()) return
    const job=items.find(j=>d.job_id && j.id===d.job_id) || items.find(j=>String(j.book_id)===String(d.book_id))
    if (!job) continue
    if (['error','failed'].includes(job.status)) return '任务失败，后台将校验文件。请稍后查看「文件」。'
    done=job.status==='done'; if (!done) { report(`下载进度　${Math.floor(job.progress||0)}%`); await delay(400) }
  }
  if (!done) return '任务已提交，后台仍在校验，请稍后查看「文件」。'
  const rec=await api('/finish_download',{book_id:d.book_id,book_name:d.book_name,author:d.author||'',file_name:`${d.book_name} - ${d.author||''}.${body.format}`})
  return rec.file_found ? '文件已生成，可前往「文件」下载。' : '任务已结束，文件仍在校验。'
}
