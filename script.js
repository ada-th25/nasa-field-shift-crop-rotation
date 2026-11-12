'use strict';
/* ===== HARVEST HEROES: data ===== */
const $=s=>document.querySelector(s),sleep=ms=>new Promise(r=>setTimeout(r,ms)),rnd=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
const esc=s=>String(s).replace(/[&<>"]/g,c=>'&#'+c.charCodeAt(0)+';');
const K=['drought','flood','frost','heat','pest'];
const BIO={
tropical:{n:'Tropical Rainforest',c:'bangladesh,brazil,indonesia,malaysia,congo,thailand,vietnam,philippines,india,colombia,nigeria,peru,sri lanka',fx:'rain',eg:'Bangladesh'},
desert:{n:'Desert',c:'egypt,saudi arabia,morocco,namibia,arizona,nevada,new mexico,utah,libya,algeria,iraq,oman,sahara,uae,dubai,jordan,sudan',fx:'dust',eg:'Egypt'},
tundra:{n:'Icy Tundra',c:'russia,siberia,iceland,greenland,nunavut,yukon,alaska,northern canada,lapland,norway,finland',fx:'snow',eg:'Russia'},
temperate:{n:'Temperate Countryside',c:'wales,england,ireland,france,germany,scotland,uk,united kingdom,britain,netherlands,poland,belgium,denmark',fx:'none',eg:'Wales'},
steppe:{n:'Central Asian Steppe',c:'kazakhstan,mongolia,uzbekistan,kyrgyzstan,turkmenistan,tajikistan,central asia',fx:'wind',eg:'Kazakhstan'},
plains:{n:'North American Plains',c:'usa,united states,america,canada,great plains,kansas,nebraska,iowa,dakota,oklahoma,texas,illinois,saskatchewan,alberta',fx:'wind',eg:'USA'}};
const detect=t=>{t=t.toLowerCase();for(const k of['tundra','desert','tropical','steppe','temperate','plains'])if(BIO[k].c.split(',').some(w=>new RegExp('\\b'+w+'\\b').test(t)))return k;return null};
const MV={irrigate:{n:'IRRIGATE',c:'#4aa8ff',d:[34,4,8,24,8]},drainage:{n:'DRAINAGE',c:'#3a6fe0',d:[8,34,16,6,14]},mulch:{n:'MULCH',c:'#c89a4a',d:[20,12,30,34,10]},rotation:{n:'CROP ROTATION',c:'#5ac84a',d:[10,10,12,8,34]}};
const SB={clay:'drainage',sandy:'mulch',loam:'rotation',silt:'irrigate',peat:'drainage'};
const W={drought:'irrigate',flood:'drainage',frost:'mulch',heat:'mulch',pest:'rotation'};
const MON={
drought:{name:'DROUGHTON',type:'DROUGHT',col:'#e07a20',atk:['Sandstorm','Water Drain','Heat Wave'],intro:'A cracked-earth giant rises from the dust!',
 pal:{b:'#4a2a12',o:'#c4561a',d:'#e2b25c',R:'#ff3418',y:'#ffd23a',k:'#1a0a05'},
 s:'..b...../..bb..bb/.bbbbbbb/.boooooo/.bokkyoo/.boooooo/.bbooRRR/bbbooRRy/bobooRRR/bobooooo/bbbooooo/.bbbbooo/.bbd.bbb/.bb..ddd/dddd.ddd/dd.d.d.d'},
flood:{name:'FLOODRA',type:'FLOOD',col:'#3a9aff',atk:['Flash Flood','Rising Tide','Mudslide'],intro:'Rain clouds swirl as a wave-beast surges in!',
 pal:{c:'#9aa8c0',C:'#6a7890',n:'#1b3f9a',m:'#2f7fe0',l:'#8fd0ff',e:'#b8f8ff',w:'#fff'},
 s:'..cccccc/.ccCcccc/.CcccCcc/...l..l./..nnnnnn/.nmmmmmm/.nmeewmm/.nmeeemm/nmmmmmmm/nmlmmmlm/nmmmmmmm/nnmlmmlm/.nmmmmmm/.nnllmmm/..nnnmlm/...nnnnn'},
frost:{name:'FROSTHORN',type:'FROST',col:'#9fe0ff',atk:['Blizzard','Ice Spike','Frozen Ground'],intro:'Snowflakes spiral around a crystal-horned beast!',
 pal:{w:'#fff',i:'#c4e8ff',c:'#74b8f4',n:'#1d3f8f',k:'#0a1a4a',y:'#ffe94a'},
 s:'.c....../.cc....c/.ici..ci/.icc.cii/.iiiiiii/..iiiwww/.iiwwwww/.iwkywww/.iwwwwww/iiwwiwww/iwwknnkw/iwwwwwww/.iwwiwww/.iiwwwww/..nn.nnn/.nnn.nnn'},
heat:{name:'PYRABLOOM',type:'HEAT',col:'#ff6a1e',atk:['Scorching Sun','Fire Burst','Burning Soil'],intro:'Embers drift as a flaming flower blooms!',
 pal:{r:'#c8281a',o:'#ff8a1e',y:'#ffd93a',g:'#2f3b1c',G:'#4a5a2a',k:'#14130e',e:'#ffe08a'},
 s:'..e..r.o/.ror.ror/.rooooyo/rooyyyoo/royykkyy/royyyyyy/rooyyyyy/.rooyyoo/..rooroo/...gGgg./..gGgggG/.ggkgGg./gg.gggg./g..GgG.e/...gGg../..gg.gg.'},
pest:{name:'ROOTROT',type:'PEST',col:'#8a46c4',atk:['Crop Infestation','Root Damage','Disease Spread'],intro:'Twisted roots writhe around a staring bug!',
 pal:{p:'#8a46c4',d:'#3b1d63',g:'#1f4a2a',G:'#4a9a3a',w:'#fff',k:'#0a0a14'},
 s:'.g....../g.g...../.gpddddd/..pppppd/.ppwwwpp/.pwwkwwp/.pwwkwwp/.ppwwwpp/..pppddd/gpppdddd/.gppddpp/g.pdddpp/.g.pdd../g..g.g../.G.g..g./g....G..'}};
const FARMER={pal:{h:'#e8c050',H:'#b8902c',s:'#f0b890',k:'#222',r:'#d04040',b:'#3a6bc8',B:'#2a4a98',n:'#5a3a1a'},
 s:'...hhhhh/..hhhhhh/.hhhhhhh/HHHHHHHH/.sssssss/..ssksss/..ssssss/...sssss/..rrrrrr/.rrbbbbb/srrbbbbb/ssrbbbbb/..bbbbbb/..bbbbbb/..bbB.BB/..nn.nnn'};
function spr(o){const c=document.createElement('canvas');c.width=c.height=16;const g=c.getContext('2d');
 o.s.split('/').forEach((r,y)=>[...r].forEach((ch,x)=>{if(ch!='.'){g.fillStyle=o.pal[ch];g.fillRect(x,y,1,1);g.fillRect(15-x,y,1,1)}}));return c}
const SP={farmer:spr(FARMER)};K.forEach(k=>SP[k]=spr(MON[k]));
/* Field-plan text. $c=crop $s=soil $l=location */
const REC={
drought:{water:'Use efficient irrigation such as drip lines for $c, watering deeply and less often, early morning or evening.',soil:'Add organic matter and a 5-8 cm mulch layer on $s soil to cut evaporation and keep moisture steady.',prot:'Shade or shelter young $c plants in extreme heat and watch for wilting, leaf curl and scorch.',plant:'Time planting around local rains and consider drought-tolerant $c varieties suited to $l.',sus:'Harvest rainwater, check irrigation water quality and monitor soil salinity, since irrigation in dry climates can build up salts.'},
flood:{water:'Improve field drainage with channels, raised beds or ridges so $c is not waterlogged for long, and monitor water levels all season.',soil:'Avoid working saturated $s soil to prevent compaction; add organic matter to improve structure and infiltration.',prot:'Inspect $c regularly after heavy rain for fungal disease, root rot and nutrient loss.',plant:'Consider $c varieties tolerant of wet or flooded conditions and keep recommended plant spacing for airflow.',sus:'Keep vegetated buffer strips along ditches and banks to slow runoff and reduce erosion.'},
frost:{water:'Moist soil holds heat better than dry soil, so water before a forecast frost, but avoid leaving ground waterlogged and freezing.',soil:'Mulch around $c to insulate roots and moderate temperature swings in $s soil.',prot:'Cover tender $c plants with fleece or cloches on frost nights and use windbreaks.',plant:'Sow or plant after the last expected frost, or choose cold-hardy $c varieties for $l.',sus:'Record first and last frost dates each year and use winter cover crops to protect the soil.'},
heat:{water:'Irrigate $c at cooler times of day and monitor soil moisture so heat stress does not compound dry spells.',soil:'Mulch $s soil to keep roots cool and add organic matter to hold moisture.',prot:'Use shade cloth or windbreaks at sensitive stages such as flowering, when heat can cut $c yields.',plant:'Adjust sowing dates to avoid peak heat at flowering and choose heat-tolerant $c varieties.',sus:'Plant trees or hedgerows for shade and diversify crops to spread risk.'},
pest:{water:'Avoid overwatering and wet foliage overnight, which favours fungal disease in $c.',soil:'Rotate $c with unrelated crops and feed $s soil with compost, as healthy soil helps suppress root disease.',prot:'Scout $c fields weekly, remove infected plants early and use integrated pest management.',plant:'Use certified clean seed or resistant $c varieties and keep recommended spacing for airflow.',sus:'Encourage beneficial insects with flower strips and avoid relying on broad-spectrum sprays.'}};
const SOIL={clay:'Clay holds water and compacts easily; ridges, raised beds and avoiding working it wet help.',sandy:'Sandy soil drains fast and loses nutrients; add compost and apply water and fertiliser little and often.',loam:'Loam is forgiving; protect it with cover crops and avoid overworking it.',silt:'Silt soils crust and erode; keep the ground covered with mulch or cover crops.',peat:'Peat is rich but can stay waterlogged or dry out; keep drainage balanced.'};
const CROP=[[/rice/,'Rice does best with managed water depth; where suited, alternate wetting and drying can cut water use.'],[/wheat|barley|oat/,'Cereals are sensitive to waterlogging and to late frost around heading; match variety to your season.'],[/potato/,'Potatoes need even moisture and are prone to blight in cool, wet weather; use certified seed.'],[/corn|maize/,'Maize is most sensitive to water stress at tasselling and silking.'],[/cotton/,'Cotton needs warmth and careful irrigation; check salinity in dry regions.'],[/date|palm/,'Date palms tolerate heat but need steady deep watering in the growing season and good drainage to avoid salt build-up.']];
const TIP={drought:'Mulch plus drip irrigation can stretch every drop of water further.',flood:'Raised beds and drainage channels keep roots from suffocating in saturated soil.',frost:'Moist soil and mulch hold heat; covers protect tender plants on frosty nights.',heat:'Heat stress at flowering is costly. Shade, mulch and sowing dates all help.',pest:'Rotation breaks the pest and disease cycles that build up when one crop repeats.'};
const CATS=[['Water management','water'],['Soil health','soil'],['Crop protection','prot'],['Planting and growing','plant'],['Long-term sustainability','sus']];

/* ===== pixel scenery ===== */
const SC={};
function paint(b){
 if(SC[b])return SC[b];
 const c=SC[b]=document.createElement('canvas');c.width=160;c.height=96;const g=c.getContext('2d');
 const R=(x,y,w,h,f)=>{g.fillStyle=f;g.fillRect(x|0,y|0,w|0,h|0)};
 let sd=11;const rr=()=>(sd=sd*16807%2147483647)/2147483647,pk=a=>a[Math.floor(rr()*a.length)];
 const hill=(base,amp,per,col,ph=0)=>{for(let x=0;x<160;x++){const y=base+Math.sin(x/per+ph)*amp;R(x,y,1,96-y,col)}};
 const mtn=(x,w,h,col,cap)=>{for(let i=0;i<h;i++){const ww=w*i/h;R(x-ww/2,40-h+i,ww,1,cap&&i<h/4?cap:col)}};
 const tree=(x,y,s,t,l)=>{R(x,y,2,6*s,t);R(x-3*s,y-5*s,8*s,6*s,l);R(x-2*s,y-7*s,6*s,3*s,l)};
 const pine=(x,y,s,l)=>{for(let i=0;i<4;i++)R(x-i-1,y-8*s+i*3*s,2*i+3,3*s,l);R(x,y,2,3,'#4a3020')};
 const cloud=(x,y,f)=>{R(x,y,18,4,f);R(x+3,y-2,10,3,f)};
 const sky=(a,b,gr)=>{R(0,0,160,40,a);R(0,24,160,16,b);R(0,40,160,56,gr)};
 const cactus=(x,y)=>{R(x,y,3,12,'#2e8a3a');R(x-3,y+4,3,2,'#2e8a3a');R(x-3,y+1,2,4,'#2e8a3a');R(x+3,y+6,3,2,'#2e8a3a');R(x+4,y+3,2,4,'#2e8a3a')};
 const dots=(n,y0,cols)=>{for(let i=0;i<n;i++)R(rr()*158,y0+rr()*(96-y0),2,2,pk(cols))};
 if(b=='tropical'){sky('#4db6e6','#9fe3c8','#2f9e3a');cloud(20,10,'#9aa8b0');cloud(90,6,'#8a98a0');hill(34,3,9,'#1e7a34');
  for(let i=0;i<14;i++)tree(rr()*158,34+rr()*8,2,'#6b4423',pk(['#1f8a2e','#17702a','#26a33a']));
  R(0,52,160,6,'#3a8ee0');for(let x=0;x<160;x+=9)R(x,54,4,1,'#9fd4ff');
  for(let i=0;i<8;i++){const x=rr()*150,y=60+rr()*30;R(x,y,8,2,'#1a6a2a');R(x+2,y-2,4,2,'#1a6a2a')}dots(30,60,['#ff6ab0','#ffd23a','#ff5a3a','#fff'])}
 else if(b=='desert'){sky('#3fa9f5','#9fdcff','#e6c26e');R(110,2,10,10,'#fff6a0');mtn(36,40,22,'#d8b070');R(80,24,6,16,'#c9a063');R(90,28,6,12,'#c9a063');R(76,22,14,2,'#b8904f');
  hill(42,4,14,'#f0d283');hill(54,3,11,'#e0bb66',2);cactus(20,46);cactus(130,70);cactus(60,76);
  R(140,40,2,16,'#7a5a30');[[-5,-2],[-3,-4],[2,-4],[4,-2]].forEach(([a,b2])=>R(141+a,38+b2,5,2,'#2e8a3a'));
  for(let i=0;i<6;i++)R(rr()*150,60+rr()*30,6,3,'#8a8a3a')}
 else if(b=='tundra'){sky('#9cc3ee','#e6f2ff','#f0f6ff');mtn(30,60,26,'#7fa0cc','#fff');mtn(100,70,30,'#6a8cc0','#fff');mtn(148,44,20,'#7fa0cc','#fff');
  R(60,60,66,16,'#a8dcff');R(66,64,12,1,'#fff');R(96,69,14,1,'#fff');
  for(let i=0;i<9;i++)pine(rr()*158,38+rr()*50,1,pk(['#1d4a58','#2a6068']));
  for(let i=0;i<7;i++){const x=rr()*150,y=50+rr()*40;R(x,y,2,7,'#bfe8ff');R(x+2,y+2,2,5,'#9ad0f8');R(x-2,y+3,2,4,'#fff')}}
 else if(b=='temperate'){sky('#9fb4c4','#d4dee6','#4aa63e');cloud(10,8,'#e8eef2');cloud(70,12,'#dde4ea');cloud(120,5,'#e8eef2');hill(36,4,12,'#5fb450');hill(44,3,9,'#4aa63e',2);
  for(let i=0;i<5;i++)R(0,56+i*8,160,3,'#5cb84a');R(0,86,160,4,'#5aa0d8');
  R(118,24,24,14,'#e8dcc0');R(116,19,28,6,'#a04030');R(126,30,5,8,'#6a4a2a');R(134,28,4,4,'#7ac0e8');
  R(0,50,160,3,'#9a9a98');for(let x=0;x<160;x+=7)R(x,50,1,3,'#6a6a68');
  tree(24,34,2,'#6b4423','#2e8a3a');tree(96,34,2,'#6b4423','#3a9a3a');dots(40,58,['#fff','#ffd23a','#ff8ab0','#b08aff'])}
 else if(b=='steppe'){sky('#7cc0ea','#cfe6f0','#d2b25a');mtn(30,70,22,'#8a7aa8','#fff');mtn(110,80,26,'#7a6a98','#fff');hill(44,2,20,'#c4a448');
  R(130,32,18,8,'#f0e8d8');R(133,28,12,4,'#e0d8c8');R(137,34,4,6,'#8a5a30');
  for(let i=0;i<12;i++)R(rr()*150,50+rr()*40,7,3,pk(['#7a8a3a','#9a9a4a']));for(let i=0;i<8;i++)R(rr()*150,50+rr()*40,5,3,'#8a8a88')}
 else{sky('#4fb0fa','#b4e4ff','#7cc24a');R(18,6,8,8,'#fff3a0');cloud(60,10,'#fff');cloud(110,6,'#fff');hill(36,3,20,'#6aa860');
  R(110,24,24,16,'#b03a2e');R(108,20,28,5,'#6a2018');R(116,30,8,10,'#f0e0d0');R(136,16,8,24,'#c8ccd0');R(135,13,10,4,'#8a8e92');
  for(let i=0;i<4;i++)R(0,56+i*10,160,5,i%2?'#d8b84a':'#5aa83a');
  for(let x=0;x<160;x+=14){R(x,46,2,8,'#8a5a30')}R(0,48,160,1,'#8a5a30');R(0,51,160,1,'#8a5a30');
  for(let i=0;i<40;i++)R(rr()*158,58+rr()*36,1,5,pk(['#4a9a2a','#d8c04a']))}
 R(98,46,56,3,'rgba(0,0,0,.2)');R(10,86,56,3,'rgba(0,0,0,.2)');
 return c}
const PT=Array.from({length:70},()=>({x:Math.random()*160,y:Math.random()*96,v:Math.random()}));
function weather(g,n){const f=BIO[P.biome].fx;g.save();
 PT.forEach(p=>{
  if(f=='rain'){p.y+=2+p.v*2;p.x-=.6;g.fillStyle='#cfe8ff';g.fillRect(p.x,p.y,1,3)}
  else if(f=='snow'){p.y+=.4+p.v*.6;p.x+=Math.sin(n/600+p.v*9)*.3;g.fillStyle='#fff';g.fillRect(p.x,p.y,p.v>.7?2:1,p.v>.7?2:1)}
  else if(f=='dust'){p.x+=1.2+p.v;p.y+=Math.sin(n/500+p.v*9)*.2;g.globalAlpha=.5;g.fillStyle='#e8c070';g.fillRect(p.x,p.y,2,1)}
  else if(f=='wind'){p.x+=2+p.v*2;g.globalAlpha=.4;g.fillStyle=P.biome=='plains'?'#fff':'#f0e0a0';g.fillRect(p.x,p.y,4+p.v*5,1)}
  if(p.y>96)p.y=0;if(p.x>160)p.x=0;if(p.x<0)p.x=160});
 if(P.biome=='desert'){g.globalAlpha=.25;g.fillStyle='#fff';for(let i=0;i<4;i++)g.fillRect(Math.sin(n/300+i)*4+i*40,36+i*2,40,1)}
 if(f=='rain'&&n%7000<120){g.globalAlpha=.5;g.fillStyle='#fff';g.fillRect(0,0,160,96)}
 g.restore()}

/* ===== state ===== */
let S=JSON.parse(localStorage.getItem('hh1')||'null')||{xp:0,w:0,def:{},st:{},log:[]},P={},B=null,TXT='';
const save=()=>localStorage.setItem('hh1',JSON.stringify(S)),lvl=()=>1+Math.floor(S.xp/100);
const stat=()=>$('#stat').textContent=`LV ${lvl()}  WINS ${S.w}  XP ${S.xp%100}/100`;
function show(id){['start','map','battle','plan','journal'].forEach(s=>$('#'+s).hidden=s!=id);if(id=='map')drawMap();if(id=='journal')drawJournal();stat()}
document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>show(b.dataset.go));

/* ===== start screen ===== */
$('#biome').innerHTML=Object.keys(BIO).map(k=>`<option value="${k}">${BIO[k].n}</option>`).join('');
function guess(){const t=$('#region').value+' , '+$('#country').value,b=detect(t);
 if(b){$('#biome').value=b;$('#hint').textContent='Detected biome: '+BIO[b].n+'. Change it above if your region differs.'}
 else $('#hint').textContent=t.trim().length>3?'Unknown place. Please choose a biome above.':''}
$('#country').oninput=$('#region').oninput=guess;
$('#go').onclick=()=>{
 const country=$('#country').value.trim(),crop=$('#crop').value.trim();
 if(!country||!crop){$('#hint').textContent='Enter a country and a crop to begin!';return}
 const rg=$('#region').value.trim();
 P={country,crop,loc:rg?rg+', '+country:country,biome:$('#biome').value,soil:$('#soil').value,season:$('#season').value,size:$('#size').value,water:$('#water').value};
 startBattle()};

/* ===== monster choice: climate + crop + season + soil + water ===== */
function pick(){
 const sc={},why={};K.forEach(k=>{sc[k]=0;why[k]=[]});
 const add=(tb,key,label)=>(tb[key]||[]).forEach(([k,p])=>{sc[k]+=p;why[k].push(label)});
 add({tropical:[['flood',2],['pest',2]],desert:[['drought',3],['heat',2]],tundra:[['frost',3]],temperate:[['flood',1],['pest',1]],steppe:[['drought',2],['frost',1]],plains:[['drought',1],['heat',1],['pest',1]]},P.biome,'the '+BIO[P.biome].n.toLowerCase()+' climate');
 add({monsoon:[['flood',3]],summer:[['heat',2],['drought',1]],winter:[['frost',3]],spring:[['flood',1],['pest',1],['frost',1]],autumn:[['pest',1],['frost',1]]},P.season,P.season+' season');
 add({clay:[['flood',2]],sandy:[['drought',2]],silt:[['flood',1]],loam:[['pest',1]],peat:[['flood',1],['frost',1]]},P.soil,P.soil+' soil');
 add({limited:[['drought',3]],rainfed:[['drought',1],['flood',1]],irrigated:[['pest',1],['heat',1]],waterlogged:[['flood',3]]},P.water,{limited:'limited water',rainfed:'rain-fed water',irrigated:'reliable irrigation',waterlogged:'limited drainage'}[P.water]);
 const c=P.crop.toLowerCase();
 [[/rice/,[['flood',2]]],[/date|cotton|olive|sorghum/,[['drought',1],['heat',1]]],[/wheat|barley|oat/,[['frost',1]]],[/potato|tomato/,[['pest',1],['flood',1]]],[/corn|maize/,[['heat',1],['drought',1]]]].forEach(([re,l])=>{if(re.test(c))add({x:l},'x',P.crop+' crops')});
 const k=K.reduce((a,b)=>sc[b]>sc[a]?b:a);return{k,why:[...new Set(why[k])]}}

/* ===== battle ===== */
async function say(t){const e=$('#txt');e.textContent='';for(const ch of t){e.textContent+=ch;await sleep(14)}await sleep(600)}
function bars(){[['eh',B.eh],['ph',B.ph]].forEach(([id,v])=>{const e=$('#'+id);e.style.width=Math.max(0,v)+'%';e.style.background=v>50?'#4ac84a':v>25?'#e8c030':'#e03a3a'})}
function moves(){$('#mv').innerHTML=Object.keys(MV).map(k=>`<button data-k="${k}" ${B.pp[k]&&!B.busy?'':'disabled'}>${MV[k].n}<small>PP ${B.pp[k]}</small></button>`).join('');
 document.querySelectorAll('#mv button').forEach(b=>b.onclick=()=>turn(b.dataset.k))}
function pop(d,enemy){const s=document.createElement('span');s.textContent='-'+d;s.style.left=(enemy?72:26)+'%';s.style.top=(enemy?18:55)+'%';$('#dmg').append(s);setTimeout(()=>s.remove(),900)}
async function fx(toEnemy,c){B.fx={t:performance.now(),e:toEnemy,c};await sleep(650);B.fx=null}
async function startBattle(){
 const r=pick(),M=MON[r.k];B={k:r.k,why:r.why,eh:100,ph:90,pp:{irrigate:5,drainage:5,mulch:5,rotation:5},good:0,turn:0,busy:1,sh:{e:0,p:0},dead:0,pdead:0,fx:null};
 $('#en').textContent=M.name;$('#et').textContent=M.type;bars();moves();show('battle');
 await say(`You arrive in ${P.loc} to grow ${P.crop}. A wild ${M.name} appeared!`);await say(M.intro);
 B.busy=0;moves();$('#txt').textContent='What will FARMER do? Pick the move that best counters '+M.type+'.'}
async function turn(k){
 if(B.busy)return;B.busy=1;B.pp[k]--;moves();const M=MON[B.k];
 await say(`FARMER used ${MV[k].n}!`);
 const d=Math.max(1,MV[k].d[K.indexOf(B.k)]+(SB[P.soil]==k?5:0)+rnd(-3,3));
 await fx(true,MV[k].c);B.eh-=d;B.sh.e=performance.now()+450;pop(d,1);bars();
 if(d>=30){B.good++;await say("It's super effective!")}else if(d<=12)await say('It barely helped...');
 if(B.eh<=0){B.dead=performance.now();await say(`${M.name} was defeated!`);return win()}
 const ai=B.turn++%3,e=ai==2?rnd(18,24):rnd(10,16);
 await say(`${M.name} used ${M.atk[ai]}!`);await fx(false,M.col);B.ph-=e;B.sh.p=performance.now()+450;pop(e,0);bars();
 if(B.ph<=0||!Object.values(B.pp).some(v=>v)){B.pdead=performance.now();await say(B.ph<=0?'FARMER is out of energy...':'FARMER has no moves left...');return lose()}
 B.busy=0;moves();$('#txt').textContent='What will FARMER do?'}
let raf=0;
function loop(){raf=requestAnimationFrame(loop);if(!B||$('#battle').hidden)return;
 const g=$('#cv').getContext('2d'),n=performance.now();g.imageSmoothingEnabled=false;g.drawImage(paint(P.biome),0,0);weather(g,n);
 let a=1,ox=n<B.sh.e?Math.sin(n/25)*3:0,oy=Math.sin(n/350)*2;
 if(B.dead){const u=Math.min(1,(n-B.dead)/900);a=1-u;oy+=u*14}
 g.globalAlpha=a;g.drawImage(SP[B.k],100+ox,2+oy,48,48);g.globalAlpha=1;
 a=B.pdead?Math.max(0,1-(n-B.pdead)/900):1;g.globalAlpha=a;g.drawImage(SP.farmer,14+(n<B.sh.p?Math.sin(n/25)*3:0),44+Math.sin(n/500),48,48);g.globalAlpha=1;
 if(B.fx){const u=Math.min(1,(n-B.fx.t)/650),[x0,y0,x1,y1]=B.fx.e?[50,58,122,26]:[122,26,40,64];g.fillStyle=B.fx.c;
  for(let i=0;i<10;i++){const v=Math.max(0,Math.min(1,u*1.3-i*.03));g.fillRect(x0+(x1-x0)*v+Math.sin(i*2+n/80)*3,y0+(y1-y0)*v+Math.cos(i*3)*3,3,3)}}}

/* ===== results ===== */
const sub=t=>t.replace(/\$c/g,P.crop).replace(/\$s/g,P.soil).replace(/\$l/g,P.loc);
function win(){
 const k=B.k,M=MON[k];S.w++;S.xp+=50;S.def[k]=(S.def[k]||0)+1;S.st[P.biome]=1;S.log.unshift({m:k,c:P.crop,l:P.loc,d:new Date().toLocaleDateString()});S.log=S.log.slice(0,10);save();stat();
 const list=CATS.map(([t,c])=>[t,[sub(REC[k][c])]]);
 list[1][1].push(sub(SOIL[P.soil]));
 const ct=CROP.find(([re])=>re.test(P.crop.toLowerCase()));if(ct)list[3][1].push(ct[1]);
 list[4][1][0]+=' '+{small:'On a small plot, hand-managed methods are practical.',medium:'On a medium farm, split fields into zones so you can monitor and act in stages.',large:'On a large farm, plan zones and routine monitoring so problems are caught early.'}[P.size];
 const why=`${M.name} appeared because ${B.why.join(', ')} make ${M.type.toLowerCase()} a real risk for ${P.crop} in ${P.loc}.`;
 const well=`You landed ${B.good} super-effective move(s) and matched ${MV[W[k]].n} to ${M.name}, finishing with ${Math.max(0,B.ph)} HP.`;
 const DIS='These are general educational guidance only. Consult local agricultural advisers before making important farming decisions.';
 TXT=`FIELD PLAN: ${P.crop} in ${P.loc}\nThreat defeated: ${M.name}\nSoil: ${P.soil} | Season: ${P.season} | Farm: ${P.size} | Water: ${P.water}\n\nWhy it appeared: ${why}\n\n`+list.map(([t,a])=>t.toUpperCase()+'\n'+a.map(x=>'- '+x).join('\n')).join('\n\n')+`\n\nTip: ${TIP[k]}\n\n${DIS}`;
 $('#plan').innerHTML=`<h2>FIELD PLAN UNLOCKED!</h2><p><b>+50 XP</b> | Level ${lvl()} | Wins ${S.w} | ${M.name} added to your journal</p>
 <p><b>Why it appeared:</b> ${esc(why)}</p><p><b>What you did well:</b> ${esc(well)}</p>
 ${list.map(([t,a])=>`<h3>${t}</h3><ul>${a.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`).join('')}
 <h3>Farming tip</h3><p>${esc(TIP[k])}</p><p><small>${DIS}</small></p>
 <div class="row"><button id="cp">COPY PLAN</button><button id="sv">SAVE AS TEXT</button><button data-go="map">WORLD MAP</button><button id="again">FARM AGAIN</button></div>`;
 wire();$('#cp').onclick=()=>(navigator.clipboard?navigator.clipboard.writeText(TXT):Promise.reject()).then(()=>$('#cp').textContent='COPIED!',()=>$('#sv').click());
 $('#sv').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([TXT],{type:'text/plain'}));a.download='field-plan.txt';a.click()};show('plan')}
function lose(){
 $('#plan').innerHTML=`<h2>CROPS WITHERED...</h2><p>${MON[B.k].name} (${MON[B.k].type}) was too strong. Think about the problem: what would a real farmer do about ${MON[B.k].type.toLowerCase()}? Try the move that best fits it.</p>
 <div class="row"><button id="retry">TRY AGAIN</button><button id="again">CHANGE FARM</button></div>`;wire();$('#retry').onclick=startBattle;show('plan')}
function wire(){document.querySelectorAll('#plan [data-go]').forEach(b=>b.onclick=()=>show(b.dataset.go));$('#again').onclick=()=>show('start')}

/* ===== world map and journal ===== */
function drawMap(){
 $('#map').innerHTML='<div class="box"><h2>World Map</h2><p>Win a battle in a region to earn its stamp. Tap a region to travel.</p></div><div class="grid">'+Object.keys(BIO).map(k=>`<div class="box"><img src="${paint(k).toDataURL()}" alt=""><h3>${BIO[k].n}</h3><p>${S.st[k]?'★ Stamp collected':'Not yet conquered'}</p><button data-b="${k}">TRAVEL</button></div>`).join('')+'</div>';
 document.querySelectorAll('[data-b]').forEach(b=>b.onclick=()=>{const k=b.dataset.b;$('#country').value=BIO[k].eg;$('#region').value='';$('#biome').value=k;guess();show('start')})}
function drawJournal(){
 $('#journal').innerHTML=`<div class="box"><h2>Farming Journal</h2><p>Level ${lvl()} | ${S.w} victories | ${Object.keys(S.st).length}/6 stamps</p></div><div class="grid">`+K.map(k=>{const M=MON[k],n=S.def[k]||0;
  return `<div class="box"><img class="${n?'':'sil'}" src="${SP[k].toDataURL()}" alt=""><h3>${n?M.name:'???'}</h3><p>${n?`Type: ${M.type} | Defeated: ${n}<br>Weak to: ${MV[W[k]].n}<br>${esc(TIP[k])}`:'Not yet discovered'}</p></div>`}).join('')+'</div>'+
  `<div class="box"><h3>Recent field plans</h3>${S.log.length?'<ul>'+S.log.map(l=>`<li>${esc(l.c)} in ${esc(l.l)}: beat ${MON[l.m].name} (${l.d})</li>`).join('')+'</ul>':'<p>None yet. Win a battle to unlock your first plan!</p>'}</div>`}
stat();show('start');loop();
