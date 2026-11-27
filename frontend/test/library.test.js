import assert from 'node:assert/strict'
import test from 'node:test'
import { normal, search } from '../src/api/library.js'

test('两个书源的详情映射为同一套书架字段', () => {
  const cat=normal({id:23,title:'七猫样书',image_link:'cover',intro:'<b>简介</b>'})
  assert.equal(cat.id,'23');assert.equal(cat.book_name,'七猫样书');assert.equal(cat.cover_url,'cover');assert.equal(cat.description,'简介')
  const fan=normal({book_id:'17',book_name:'番茄样书'});assert.equal(fan.id,'17');assert.equal(fan.book_name,'番茄样书')
})
test('搜索始终访问当前书源的 API', async t => {
  t.mock.method(globalThis,'fetch',async url=>({ok:true,json:async()=>({items:[],total:0,page:2})}))
  globalThis.location=new URL('http://localhost/?mode=demo')
  try { await search('qimao','书名',2);assert.match(fetch.mock.calls[0].arguments[0],/^\/api\/qimao\/search\?/);await search('fanqie','书名',2);assert.match(fetch.mock.calls[1].arguments[0],/^\/api\/search\?/) } finally {delete globalThis.location}
})
