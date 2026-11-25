// 预览不访问 Flask。字段名与番茄的搜索、详情和任务接口保持一致。
const books = [
  { book_id: 'sample-01', book_name: '山海手记', author: '林川', cover_url: '/web_static/sample-cover.svg', category: '旅行', description: '旅人沿海岸向北，把渡口、山路和沿途的人写成一本手记。' },
  { book_id: 'sample-02', book_name: '山海之间的最后一班渡船', author: '江屿', category: '故事', description: '航线即将停运。最后一周，一位新船员开始记录每个过客的目的地。' },
  { book_id: 'sample-03', book_name: '山海来信', author: '许南', category: '书信', description: '两座小城之间，一段由书信串起的漫长旅途。' },
]

export function searchBooks(query) {
  const key = query.trim()
  const items = key ? books.filter(b => `${b.book_name} ${b.author}`.includes(key)) : []
  return { items, page: 1, total: items.length }
}

export function getDetail(id) {
  return books.find(b => b.book_id === id)
}

export function createPreviewSession() {
  let quota = 3
  const jobs = new Map()
  return {
    get quota() { return quota },
    submit(id, format) {
      if (!getDetail(id) || !['txt', 'epub'].includes(format)) throw new Error('请选择书籍和下载格式。')
      if (jobs.has(id)) throw new Error('这本书已有演示任务，不会重复扣次。')
      if (!quota) throw new Error('演示次数已用完。刷新页面可重新体验。')
      const job = { id: `job-${id}`, book_id: id, format, status: 'queued', progress: 0 }
      jobs.set(id, job)
      return { job_id: job.id, quota: --quota, status: job.status }
    },
    advance(id) {
      const job = jobs.get(id)
      if (!job) return null
      job.progress = Math.min(100, job.progress + 25)
      job.status = job.progress === 100 ? 'done' : 'running'
      return { ...job }
    },
  }
}
