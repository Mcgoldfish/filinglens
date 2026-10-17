const fs=require('fs'),vm=require('vm'),zlib=require('zlib'),assert=require('assert');
const db=JSON.parse(zlib.gunzipSync(fs.readFileSync('dist/reports.json.gz')));
const catalog=JSON.parse(fs.readFileSync('dist/catalog.json'));
assert.equal(catalog.companies.length,100);
for(const c of db.companies.filter(c=>c.status==='indexed')){
 assert(new RegExp('/(NASDAQ|NYSE)_'+c.ticker+'_\\d{4}\\.pdf$','i').test(c.url),'Exchange/ticker mismatch: '+c.ticker);
 assert.equal(c.searchablePages,c.pages.length);
 assert(c.pages.every(p=>p.page>=1&&p.page<=c.pageCount&&p.text.length>60));
}
let message;const ctx={performance,postMessage:m=>message=m};vm.createContext(ctx);
vm.runInContext(fs.readFileSync('dist/search-worker.js','utf8'),ctx);ctx.payload=db;vm.runInContext('db=payload',ctx);
const run=opts=>{ctx.onmessage({data:{type:'search',id:1,query:'supply chain',sort:'relevance',...opts}});return message};
let r=run({company:'AAPL'});assert(r.total>0);assert(r.results.every(r=>r.ticker==='AAPL'));assert.equal(r.companies,1);
r=run({query:'"supply chain"',company:'AAPL'});assert(r.results.every(r=>db.companies.find(c=>c.ticker==='AAPL').pages.find(p=>p.page===r.page).text.toLowerCase().includes('supply chain')));
r=run({query:'not-a-real-term-918231'});assert.equal(r.total,0);
r=run({industry:'Health Care'});assert(r.results.every(r=>r.industry==='Health Care'));
r=run({year:'1900'});assert.equal(r.total,0);
r=run({sort:'company'});assert(r.results.every((v,i,a)=>i===0||a[i-1].name.localeCompare(v.name)<=0));
r=run({query:'revenue'});assert(r.total>r.results.length);assert.equal(r.results.length,500);
ctx.onmessage({data:{type:'page',ticker:'AAPL',page:9}});assert(message.page.text.includes('supply chain'));assert(message.company.url.includes('NASDAQ_AAPL'));
console.log('Passed: 100-company coverage manifest, report identity, page bounds, keyword search, exact phrases, company/industry/year filters, sorting, pagination limit, and source page lookup.');
