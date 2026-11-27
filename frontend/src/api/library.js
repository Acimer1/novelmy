export const label = { fanqie: '番茄', qimao: '七猫' }
export const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
export function read(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback } }
export async function api(path, body, method) {
  const prefix = location.pathname.startsWith('/novel/') && path.startsWith('/admin/users') ? '/novel' : ''
  const res = await fetch(`${prefix}/api${path}`, {credentials:'same-origin', method:method || (body ? 'POST' : 'GET'), ...(body ? {headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {})})
  const data = await res.json().catch(() => { throw new Error('服务未返回 JSON，请检查后端地址和登录状态。') })
  if (!res.ok || data.error) {
    if (res.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('session-expired'))
    throw Object.assign(new Error(data.error || '服务未返回有效结果，请稍后再试。'), {data})
  }
  return data
}
export function normal(b) { return {...b,id:String(b.book_id ?? b.id),book_name:b.book_name || b.title,cover_url:b.cover_url || b.image_link,description:(b.description || b.abstract || b.intro || '').replace(/<[^>]+>/g,'')} }
export async function search(source,q,page) {
  const data = await api(`${source === 'qimao' ? '/qimao' : ''}/search?${new URLSearchParams({q,page,per_page:12})}`)
  return {...data,items:data.items.map(normal),total:data.total ?? data.items.length}
}
export async function download(source, body, report, quota, active = () => true) {
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
