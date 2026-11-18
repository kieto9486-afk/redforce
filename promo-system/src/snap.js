// 이벤트 목록 페이지를 열어 화면 글자를 줄 단위로 모읍니다. 사용법: node src/snap.js <url>
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({userAgent:'Mozilla/5.0 (compatible; promo-monitor/1.0)'});
 try{const r=await p.goto(process.argv[2],{waitUntil:'domcontentloaded',timeout:30000});await p.waitForTimeout(3500);
 const t=await p.evaluate(()=>document.body.innerText);
 const lines=[...new Set(t.split('\n').map(s=>s.replace(/\s+/g,' ').trim()).filter(s=>s.length>=4&&s.length<=90))];
 console.log(JSON.stringify({ok:true,status:r?r.status():0,url:p.url(),lines}));}catch(e){console.log(JSON.stringify({ok:false,error:String(e).slice(0,200)}));}
 await b.close();})();
