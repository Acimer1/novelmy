document.querySelector('iframe').onload = async function () {
  const d=this.contentDocument, win=this.contentWindow, pause=ms=>new Promise(r=>setTimeout(r,ms))
  let step='启动'; const issues=[];win.addEventListener('error',e=>issues.push(e.message))
  async function wait(fn, name){step=name; for(let i=0;i<220;i++){const v=fn();if(v)return v;await pause(50)}throw Error('超时：'+name)}
  const visible=el=>el && el.getClientRects().length>0
  const buttons=()=>[...d.querySelectorAll('button')].filter(visible)
  async function click(text){const b=await wait(()=>buttons().find(x=>x.textContent.trim()===text&&!x.disabled),text);b.click();await pause(30)}
  async function input(sel,text){const el=await wait(()=>[...d.querySelectorAll(sel)].find(visible),sel);el.value=text;el.dispatchEvent(new win.Event('input',{bubbles:true}))}
  async function account(){(await wait(()=>d.querySelector('[aria-label="我的账户"]'),'账户入口')).click();await pause(40)}
  try{
    const admin=document.body.dataset.role==='admin';if(!admin)await click('创建新账号');await input('[autocomplete=username]',admin?'admin':'browser-reader');await input('input[type=password]',admin?'local-test-admin':'local-test-reader');await click(admin?'登录':'注册并登录');await wait(()=>d.querySelector('.account-anchor .welcome-tip'),'账户引导气泡');await click('查看指南 →');await wait(()=>d.querySelector('.guide')&&!d.querySelector('.welcome-tip'),'进入指南并关闭提示');await account()
    if(admin){
      const reader=()=>[...d.querySelectorAll('article')].find(el=>el.querySelector('h3')?.textContent==='browser-reader')
      await click('管理');await wait(reader,'管理员用户列表');await click('统计');await wait(()=>d.body.innerText.includes('普通用户下载排行'),'排行已加载')
      if(!buttons().find(b=>b.disabled&&b.textContent==='导出数据库'))throw Error('缺少禁用导出入口')
      await click('公告');await wait(()=>d.body.innerText.includes('本机公告'),'公告编辑器');await click('用户');await wait(reader,'返回用户列表')
      win.confirm=()=>true
      const action=async text=>{(await wait(()=>[...reader().querySelectorAll('button')].find(b=>b.textContent===text&&!b.disabled),text)).click()}
      await action('管理用户');await input('input[aria-label="调整次数"]','3');await action('保存次数');await wait(()=>reader().innerText.includes('剩余 4 次'),'管理员加次数')
      await action('管理用户');await action('停用');await wait(()=>reader().innerText.includes('已停用'),'已停用');await action('管理用户');await action('启用');await wait(()=>reader().innerText.includes('正常'),'已启用')
    }
    else{await click('指南');await wait(()=>d.querySelectorAll('.chapter').length===5,'五章指南');
      const frame=win.frameElement, oldWidth=frame.style.width
      for(const width of [320,360,390,430]){
        frame.style.width=width+'px';await pause(50)
        const root=d.documentElement, nav=d.querySelector('nav[aria-label="主导航"]')
        if(root.scrollWidth>root.clientWidth+1)throw Error(`指南超出视口：${root.scrollWidth} / ${root.clientWidth}px`)
        const picker=d.querySelector('.mobile-position select');if(!visible(picker)||picker.options.length!==5||visible(d.querySelector('.rail')))throw Error('窄屏章节目录未正确切换')
        if([...nav.children].some(b=>b.getBoundingClientRect().height<44||b.getBoundingClientRect().right>root.clientWidth+1))throw Error('底栏触控区域或屏幕边界异常')
      }
      const picker=d.querySelector('.mobile-position select');picker.value='2';picker.dispatchEvent(new win.Event('change',{bubbles:true}));await wait(()=>d.activeElement===d.querySelectorAll('.chapter')[2] && d.querySelector('.mobile-position strong').textContent==='批量导入','章节跳转与阅读位置');
      frame.style.width=oldWidth;await click('导入七猫链接');await wait(()=>[...d.querySelectorAll('.qimao textarea')].some(visible),'指南跳转七猫链接输入');await click('找书');await account();const contact=d.querySelector('.contact');contact.querySelector('summary').click();await wait(()=>contact.open&&[...contact.querySelectorAll('.contact-row')].every(row=>visible(row.querySelector('button')))&&contact.querySelectorAll('.contact-row').length===2,'两行联系方式与复制按钮');await input('[aria-label="卡密"]','LOCAL-TEST');await click('兑换');await wait(()=>d.body.innerText.includes('已增加 4 次'),'兑换到账');
      for(const source of ['七猫','番茄']){await click(source);await input('input[type=search]','联调');await click('搜索');const card=await wait(()=>[...d.querySelectorAll('.book')].find(visible),'搜索结果');card.click();await click('开始下载');await click('确认下载');await wait(()=>d.body.innerText.includes('文件已生成'),'实体文件生成');await click('文件');await wait(()=>d.body.innerText.includes(source+'联调样书'),'文件记录')}
      await click('番茄');await click('← 返回搜索结果');const recent=d.querySelector('.recent-toggle');recent.click();await wait(()=>recent.getAttribute('aria-expanded')==='true','展开最近搜索');await click('联调');await wait(()=>recent.getAttribute('aria-expanded')==='false'&&!d.querySelector('.fanqie .searchbox button').disabled,'点选历史词并收起');recent.click();await click('清空记录');await wait(()=>!d.querySelector('.recent'),'清空历史');await click('文件')
      const fanFile=await wait(()=>[...d.querySelectorAll('.file')].find(el=>el.querySelector('h3')?.textContent==='番茄联调样书'),'番茄文件')
      const original=await (await win.fetch(fanFile.querySelector('a[download]').href)).text()
      if(!original.startsWith('联调样章'))throw Error('原文件内容不符')
      fanFile.querySelector('button').click();await pause(50);const size=fanFile.querySelector('select');size.value='0.5';size.dispatchEvent(new win.Event('change',{bubbles:true}));win.confirm=()=>true;await click('开始分割')
      const pieces=await wait(()=>{const a=[...fanFile.querySelectorAll('a[href*="/novels/download/"]')];return a.length>1&&a},'分卷链接')
      const chunks=await Promise.all(pieces.map(async a=>{const r=await win.fetch(a.href);if(!r.ok)throw Error('分卷取回失败');return r.text()}));if(chunks.join('')!==original)throw Error('分卷重组与原文不同')
      await click('七猫');await click('链接下载');await input('textarea','20001\n20002');await click('开始下载');await click('确认下载');await wait(()=>d.body.innerText.includes('2/2　文件已生成'),'批量下载完成');await click('文件');await wait(()=>d.body.innerText.includes('七猫第二册'),'批量文件记录')
      await account();await wait(()=>d.body.innerText.includes('剩余 1 次下载额度'),'重复书籍未扣次');await click('退出登录');await wait(()=>buttons().some(b=>b.textContent==='登录'),'退出登录')}
    if(issues.length)throw Error(issues.join(';')); document.body.dataset.result='passed'
  }catch(e){document.body.dataset.failure=step+' / '+e.message+' / '+d.body.innerText.slice(-250)}
}
