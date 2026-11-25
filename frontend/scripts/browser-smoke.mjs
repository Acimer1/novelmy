// 在本地内存页面内驱动同源静态预览，不访问 Flask 或真实账户。
import { createServer } from 'node:http'
import { spawn } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
const tmpdir = () => fileURLToPath(new URL('../node_modules/', import.meta.url))
import assert from 'node:assert/strict'
const preview='http://127.0.0.1:4173'
const smoke=async function(){
  const frame=document.querySelector('iframe'),d=frame.contentDocument
  let errors=[];frame.contentWindow.addEventListener('error',e=>errors.push(e.message))
  const wait=ms=>new Promise(r=>setTimeout(r,ms))
  const button=(text)=>Array.from(d.querySelectorAll('button')).find(b=>b.offsetWidth&&b.textContent.trim()===text)
  async function click(b){if(!b)throw Error('找不到控件');b.click();await wait(60)}
  try{
    for(let i=0;!d.querySelector('.book')&&i<50;i++)await wait(50)
    if(d.documentElement.scrollWidth>frame.clientWidth)throw Error('页面发生水平溢出')
    await click(button('七猫'));await click([...d.querySelectorAll('.qimao .book')][0]);await click(button('模拟下载'));await click(button('确认下载'));await wait(1000);await click(button('文件'))
    if(!d.querySelector('.file')?.textContent.includes('夜航电台'))throw Error('文件记录缺失')
    await click(button('指南'));if(!d.querySelector('main').textContent.includes('3 分钟快速上手'))throw Error('指南未加载')
    await click(d.querySelector('[aria-label="我的账户"]'));if(!d.querySelector('main').innerText.includes('剩余 2 次'))throw Error('额度未更新')
    await click(d.querySelector('[aria-label="切换浅色"]'));if(!d.querySelector('[data-theme="light"]'))throw Error('浅色切换失败')
    if(errors.length)throw Error(errors.join(';'));document.body.dataset.smoke='passed'
  }catch(e){document.body.dataset.error=e.message}
}
const server=createServer(async(req,res)=>{try{const u=new URL(req.url,'http://localhost');if(u.pathname==='/smoke'){res.setHeader('content-type','text/html; charset=utf-8');res.end(`<iframe style="border:0;width:${Number(u.searchParams.get('width'))}px;height:820px" src="/?mode=demo"></iframe><script>document.querySelector('iframe').onload=()=>(${smoke.toString()})();</script>`);return}const upstream=await fetch(preview+u.pathname);res.writeHead(upstream.status,{'content-type':upstream.headers.get('content-type')||'text/plain'});res.end(Buffer.from(await upstream.arrayBuffer()))}catch{res.writeHead(502).end()}})
await new Promise(r=>server.listen(0,'127.0.0.1',r))
try{for(const width of [390,1000]){const profile=await mkdtemp(join(tmpdir(),'shelf-smoke-'));try{const output=await new Promise((resolve,reject)=>{const p=spawn(process.env.CHROME_BIN,['--headless','--disable-gpu','--no-first-run','--disable-background-networking',`--user-data-dir=${profile}`,'--virtual-time-budget=8000','--dump-dom',`http://127.0.0.1:${server.address().port}/smoke?width=${width}`],{stdio:['ignore','pipe','ignore']});let result='';p.stdout.on('data',c=>result+=c);p.on('error',reject);p.on('close',()=>resolve(result))});assert.match(output,/<body data-smoke="passed"/,output.match(/<body[^>]*>/)?.[0]);console.log(`${width}px：七猫模拟下载、文件、指南、账户和主题通过`)}finally{await rm(profile,{recursive:true,force:true,maxRetries:3,retryDelay:250})}}}finally{server.close()}
