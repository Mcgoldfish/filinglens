"""Build a dated, reproducible report index from published archive links.
No synthetic passages. Missing companies remain explicitly unindexed.
Run with the bundled Python runtime (pypdf required).
"""
import concurrent.futures, datetime, gzip, html, io, json, re, time, urllib.request, urllib.parse, threading, sys
from pathlib import Path
from html.parser import HTMLParser
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / '.report-cache'
CACHE.mkdir(exist_ok=True)
SNAPSHOT = '2026-10-13'
LIST_SOURCE = 'https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies'
NETWORK_LOCK = threading.Lock()
LAST_REQUEST = 0

def get(url):
    global LAST_REQUEST
    with NETWORK_LOCK:
        time.sleep(max(0, 2.1 - (time.monotonic() - LAST_REQUEST)))
        LAST_REQUEST = time.monotonic()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; FilingLens/1.0; public-report-index)'})
    with urllib.request.urlopen(req, timeout=35) as r:
        return r.read()

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row=[]
        if tag in ('td', 'th') and self.row is not None: self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row=None

def clean(text):
    text = re.sub(r'(\w)-\s*\n\s*(\w)',r'\1\2',text)
    return re.sub(r'\s+', ' ', text.replace('\x00','').replace('\u00ad','')).strip()

def collect(company):
    ticker = company['ticker']; cache = CACHE / (ticker + '.json')
    if cache.exists():
        cached=json.loads(cache.read_text(encoding='utf-8'))
        if re.search(r'/(NASDAQ|NYSE)_'+re.escape(ticker)+r'_\d{4}\.pdf$',cached.get('url',''),re.I):
            distinctive=next((w for w in re.findall(r'[a-z]+',company['name'].lower()) if w not in {'the','inc','corporation','company','holdings','plc'}),None)
            if not distinctive or distinctive in ' '.join(p['text'] for p in cached['pages'][:6]).lower():
                cached['searchablePages']=len(cached['pages'])
                return cached
    result={**company,'status':'unavailable'}
    if '--cached-only' in sys.argv:
        result['reason']='Not collected: archive access or report verification unavailable'
        return result
    try:
        search_url='https://www.annualreports.com/Companies?search='+urllib.parse.quote(ticker)
        search=get(search_url).decode('utf-8')
        links=list(dict.fromkeys(re.findall(r'href="(/Company/[^"#]+)"',search)))
        if not links:
            search=get('https://www.annualreports.com/Companies?search='+urllib.parse.quote(company['name'])).decode('utf-8')
            links=list(dict.fromkeys(re.findall(r'href="(/Company/[^"#]+)"',search)))
        if not links: raise ValueError('No archive company match')
        # Prefer ticker verification from a published report filename.
        report=None
        for link in links[:3]:
            page=get('https://www.annualreports.com'+link).decode('utf-8')
            pdfs=list(dict.fromkeys(re.findall(r'href="([^"\s]+\.pdf)"',page)))
            matches=[p for p in pdfs if re.search(r'/(NASDAQ|NYSE)_'+re.escape(ticker)+r'_\d{4}\.pdf$',p,re.I)]
            if matches:
                report=max(matches,key=lambda p:int(re.search(r'_(\d{4})\.pdf$',p).group(1)));break
        if not report: raise ValueError('No verified ticker report link')
        url=urllib.parse.urljoin('https://www.annualreports.com',report)
        pdf=get(url)
        if not pdf.startswith(b'%PDF'): raise ValueError('Download was not a PDF')
        reader=PdfReader(io.BytesIO(pdf))
        pages=[]
        for n,page in enumerate(reader.pages,1):
            text=clean(page.extract_text() or '')
            if len(text)>60: pages.append({'page':n,'text':text})
        if not pages: raise ValueError('No extractable text')
        # Check the company name against the front matter, in addition to exchange/ticker.
        namewords=re.findall(r'[a-z]+',company['name'].lower())
        distinctive=next((w for w in namewords if w not in {'the','inc','corporation','company','holdings','plc'}),None)
        front=' '.join(p['text'] for p in pages[:6]).lower()
        if distinctive and distinctive not in front: raise ValueError('Company name did not match report front matter')
        result.update(status='indexed',year=re.search(r'_(\d{4})\.pdf$',report).group(1),url=url,pages=pages,pageCount=len(reader.pages),searchablePages=len(pages),retrieved=SNAPSHOT)
        cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        print(ticker+': indexed '+str(len(pages))+' pages',flush=True)
    except Exception as e:
        result['reason']=str(e)[:160];print(ticker+': unavailable ('+str(e)[:70]+')',flush=True)
    return result

def main():
    roster_file=CACHE/'constituents.html'
    if not roster_file.exists(): roster_file.write_bytes(get(LIST_SOURCE))
    parser=Tables();parser.feed(roster_file.read_text(encoding='utf-8'))
    roster=[{'ticker':r[0],'name':re.sub(r'\s*\(Class [AC]\)','',r[1]),'industry':r[2]} for r in parser.rows if len(r)==4 and re.fullmatch(r'[A-Z]{1,5}',r[0])]
    if len(roster)<80: raise ValueError('Constituent parsing failed')
    # Alphabet share classes use one report; keep both searchable tickers.
    roster=[r for r in roster if r['ticker']!='GOOG']
    for r in roster:
        if r['ticker']=='GOOGL':r['aliases']=['GOOG']
    priority=['MSFT','NVDA','AAPL','AMZN','GOOGL','META','NFLX','TSLA','ADBE','COST']
    roster.sort(key=lambda r:priority.index(r['ticker']) if r['ticker'] in priority else 999)
    results=[]
    (ROOT/'.gitignore').write_text('.report-cache/\n',encoding='utf-8')
    def save():
        payload={'snapshot':SNAPSHOT,'constituentSource':LIST_SOURCE,'sourceNote':'Constituent reference snapshot; report availability is independently listed. Latest accessible archive report per company, not necessarily its latest filing.','companies':sorted(results,key=lambda r:r['name'])}
        encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        (ROOT/'dist'/'reports.json.gz').write_bytes(gzip.compress(encoded))
        meta={k:v for k,v in payload.items() if k!='companies'}
        meta['companies']=[{k:v for k,v in c.items() if k!='pages'} for c in payload['companies']]
        (ROOT/'dist'/'catalog.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(collect,roster):
            results.append(result)
            if len(results)%10==0:save()
    save();print('Complete: '+str(sum(c['status']=='indexed' for c in results))+'/'+str(len(results))+' companies indexed',flush=True)

if __name__=='__main__':main()
