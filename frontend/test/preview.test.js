import test from 'node:test'
import assert from 'node:assert/strict'
import { createPreviewSession, searchBooks } from '../src/api/preview-api.js'

test('示例搜索涵盖有封面、无封面、作者和空结果', () => {
  const { items, total } = searchBooks(' 山海 ')
  assert.equal(total, 3)
  assert.ok(items.some(b => b.cover_url) && items.some(b => !b.cover_url))
  assert.equal(searchBooks('江屿').total, 1)
  assert.equal(searchBooks('不存在').total, 0)
})
test('任务接受后只扣一次，不能当作文件已就绪', () => {
  const s = createPreviewSession(), id = 'sample-01'
  assert.throws(() => s.submit(id, 'pdf'))
  assert.equal(s.quota, 3)
  assert.equal(s.submit(id, 'txt').status, 'queued')
  assert.throws(() => s.submit(id, 'epub'))
  assert.equal(s.quota, 2)
  for (let i = 0; i < 3; i++) assert.equal(s.advance(id).status, 'running')
  assert.equal(s.advance(id).status, 'done')
  assert.equal(createPreviewSession().quota, 3)
})
