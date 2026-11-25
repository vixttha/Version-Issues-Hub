// Actual anonymous GitHub blob-page checks; no credentials or repository writes.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const repo='vixttha/Version-Issues-Hub';
const old='a9cdd97c4ad111ed4bb3eb1efa4c9bafc306a9b4';
const head=process.env.GITHUB_SHA;
const output=process.env.RUNNER_TEMP+'/vib-readme-visual';
const layouts=[{name:'desktop',width:1440,height:1000},{name:'mobile',width:390,height:844},{name:'small-mobile',width:320,height:800}];
fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 const rows=[];
 try {
  for(const revision of [{label:'before',sha:old},{label:'after',sha:head}]){
   for(const layout of layouts){
    for(const theme of ['light','dark']){
     const context=await browser.newContext({viewport:{width:layout.width,height:layout.height},colorScheme:theme,deviceScaleFactor:1,isMobile:layout.name!=='desktop',hasTouch:layout.name!=='desktop'});
     const page=await context.newPage();
     const key=revision.label+'-'+layout.name+'-'+theme;
     const file=revision.label==='before'?'workspace/v0.0.1/accepted/README.md':'README.md';
     const url=revision.label==='before'?'https://github.com/'+repo+'/blob/'+revision.sha+'/'+file:'https://github.com/'+repo+'/tree/'+revision.sha;
     let result={revision:revision.sha,label:revision.label,viewport:layout,theme,url,assetResponses:[]};
     page.on('response',r=>{if(/vib-logo/i.test(r.url()))result.assetResponses.push({url:r.url(),status:r.status(),contentType:r.headers()['content-type']||null});});
     try {
      const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
      assert.equal(response.status(),200,'GitHub response');
      const article=page.locator('.markdown-body').filter({has:page.getByRole('heading',{level:1,name:'Version-Issues-Hub-Branch (VIB)',exact:true})}).first();
      await article.waitFor({timeout:20000});
      const img=article.locator('picture img').first();
      await img.waitFor({timeout:10000});
      await page.evaluate(()=>document.fonts.ready);
      // Wait for a real successful image decode; preserve failure if retries exhaust.
      await img.evaluate(async e=>{let last;for(let i=0;i<3;i++){try{await e.decode();return;}catch(err){last=err;await new Promise(r=>setTimeout(r,500));}}throw last;});
      await article.scrollIntoViewIfNeeded();
      result={...result,...await article.evaluate(a=>{
       const img=a.querySelector('picture img'),r=a.getBoundingClientRect();
       const rect=e=>({x:Math.round(e.getBoundingClientRect().x),y:Math.round(e.getBoundingClientRect().y),width:Math.round(e.getBoundingClientRect().width),height:Math.round(e.getBoundingClientRect().height)});
       const overflow=[...a.querySelectorAll('h1,h2,p,ul,ol,table,picture,img')].filter(e=>e.getBoundingClientRect().right>r.right+2||e.getBoundingClientRect().left<r.left-2||e.scrollWidth>e.clientWidth+2&&e.clientWidth>0).map(e=>({tag:e.tagName,text:e.textContent.slice(0,65),scroll:e.scrollWidth,client:e.clientWidth}));
       return {article:rect(a),articleScroll:a.scrollWidth,articleClient:a.clientWidth,viewportWidth:innerWidth,heading:a.querySelector('h1').textContent,headingCount:a.querySelectorAll('h1').length,logo:{...rect(img),src:img.currentSrc,alt:img.alt,naturalWidth:img.naturalWidth},tables:a.querySelectorAll('table').length,overflow,codeBlocks:[...a.querySelectorAll('pre')].map(e=>({scroll:e.scrollWidth,client:e.clientWidth,overflowX:getComputedStyle(e).overflowX})),startHere:[...a.querySelectorAll('h2')].find(e=>e.textContent.trim()==='Start here')?.getBoundingClientRect().top-r.top,quickstart:[...a.querySelectorAll('h2')].find(e=>['Quickstart','First useful action'].includes(e.textContent.trim()))?.getBoundingClientRect().top-r.top,bodyBackground:getComputedStyle(document.body).backgroundColor};
      })};
      await page.screenshot({path:path.join(output,key+'-viewport.png'),animations:'disabled'});
      await article.screenshot({path:path.join(output,key+'-article.png'),animations:'disabled'});
      if(revision.label==='after'){
       assert.equal(result.headingCount,1);
       assert.equal(result.tables,0);
       assert.ok(result.logo.naturalWidth>0&&result.logo.alt.length>0);
       assert.ok(result.logo.src.includes(theme==='dark'?'vib-logo.svg':'vib-logo-light.svg'),'wrong theme asset: '+result.logo.src);
       assert.ok(result.logo.width<=result.article.width+2,'logo too wide');
       assert.ok(result.articleScroll<=result.articleClient+2,'article horizontal overflow');
       assert.deepEqual(result.overflow,[],'content overflow');
       assert.ok(result.viewportWidth<=layout.width+2,'viewport not responsive');
       assert.ok(result.quickstart>0&&result.startHere>0);
      }
      result.status='pass';
     }catch(error){result.status='fail';result.error=String(error);await page.screenshot({path:path.join(output,key+'-failure.png')}).catch(()=>{});}
     rows.push(result);console.log(JSON.stringify(result));await context.close();
    }
   }
  }
 }finally{await browser.close();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(rows,null,2));}
 assert.equal(rows.length,12);
 assert.equal(rows.filter(x=>x.label==='after'&&x.status==='pass').length,6,'candidate live GitHub visual checks');
 assert.equal(rows.filter(x=>x.label==='before'&&x.status==='pass').length,6,'baseline GitHub pages must load for comparison');
})().catch(e=>{console.error(e);process.exitCode=1;});
