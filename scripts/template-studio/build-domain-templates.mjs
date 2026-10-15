// Rebuild the six domain frameworks from content profiles. No LLM/API calls.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {domains} from './domain-profiles.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const work=path.join(root,'.local/theme-studio-20261014');
const modules=process.env.RUNTIME_NODE_MODULES;
if(!modules||!process.env.PRESENTATIONS_SKILL_DIR||!process.env.RUNTIME_PYTHON)throw new Error('Set the bundled runtime and presentation skill paths.');
const {Presentation,PresentationFile}=createRequire(path.join(modules,'package.json'))('@oai/artifact-tool');
const skill=process.env.PRESENTATIONS_SKILL_DIR;
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const refs=JSON.parse(await fs.readFile(path.join(root,'server/proposal_templates/domain_sources.json'),'utf8'));
const assets=path.join(root,'server/proposal_templates/domain_assets');
const output=path.join(work,process.env.OUTPUT_DIR||'output');
const imageSources=JSON.parse(await fs.readFile(path.join(assets,'sources.json'),'utf8'));
await fs.mkdir(path.join(output,'templates'),{recursive:true});
await fs.mkdir(path.join(output,'samples'),{recursive:true});
await fs.mkdir(path.join(work,'build'),{recursive:true});
const FONT='Malgun Gothic',W=1280,H=720;

function text(s,value,x,y,w,h,size,color,bold=false,name='domain-copy',align='left'){
 if(value===undefined||value===null)throw new Error('Missing slide text: '+name);
 const sh=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=String(value);sh.text.insets=0;
 sh.text.style={typeface:FONT,fontSize:size,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:true};
 return sh;
}
function rule(s,x,y,w,color){return s.shapes.add({geometry:'rect',name:'bid3-fixed-rule',position:{left:x,top:y,width:w,height:1.5},fill:color,line:{fill:'none',width:0}});}
function node(s,title,body,x,y,w,h,C){
 const sh=s.shapes.add({geometry:'rect',name:'domain-diagram-node',position:{left:x,top:y,width:w,height:h},fill:C.soft,line:{fill:C.accent,width:1}});
 text(s,title,x+18,y+18,w-36,44,28,C.ink,true);
 if(body)text(s,body,x+18,y+72,w-36,h-82,24,C.ink);
 return sh;
}
function connector(s,x,y,w,h,C){s.shapes.add({geometry:'connector',name:'domain-diagram-connection',position:{left:x,top:y,width:w,height:h},line:{fill:C.accent,width:2},fill:'none'});}
async function detailPhoto(s,d,x,y,w,h){
 const extension=d.id==='education'?'.png':'.jpg';
 s.images.add({blob:new Uint8Array(await fs.readFile(path.join(assets,d.id+'-detail'+extension))),contentType:extension==='.png'?'image/png':'image/jpeg',alt:`${d.name} 설명용 이미지. 실제 수행 사진 아님`,fit:'cover',position:{left:x,top:y,width:w,height:h}});
}
function footer(s,d,n,C,sample){
 text(s,`${d.name} 제안서`,64,669,500,28,16,C.accent,false,'bid3-fixed-footer');
 text(s,sample?d.sampleStatus:'분야별 작성 양식',680,669,465,28,15,C.accent,false,'bid3-fixed-status','right');
 text(s,String(n).padStart(2,'0'),1167,665,49,33,22,C.accent,true,'bid3-fixed-page','right');
}
function header(s,p,d,n,C,sample,variant){
 s.background.fill=C.bg;
 text(s,`${d.name} / ${p.role==='contents'?'제안 구성':p.role==='evidence'?'수행 근거':'수행 계획'}`,64,36,1100,31,18,C.accent,true,'bid3-fixed-section');
 text(s,p.title,64,92,1152,69,43,C.ink,true,'bid3-title');
 text(s,p.lead,64,174,1152,72,25,C.ink);
 if(variant===1)rule(s,64,254,1152,C.accent);
 footer(s,d,n,C,sample);
}
function nativeTable(s,rows,C,{y=279,h=337}={}){
 const cols=rows[0].length;
 const widths=cols===6?[252,180,180,180,180,180]:cols===4?[185,270,397,300]:[240,456,456];
 const t=s.tables.add({rows:rows.length,columns:cols,left:64,top:y,width:1152,height:h,columnWidths:widths,values:rows});
 t.borders.assign({fill:C.bg,width:2,style:'solid'});
 for(let r=0;r<rows.length;r++){
  t.rows[r].height=r===0?62:(h-62)/(rows.length-1);
  for(let c=0;c<cols;c++){
   const cell=t.getCell(r,c);cell.fill=r===0?C.ink:r%2===0?C.bg:C.soft;
   cell.text.style={typeface:FONT,fontSize:cols>=4?23:25,color:r===0?'#FFFFFF':C.ink,bold:r===0||c===0,alignment:'left',verticalAlignment:'middle',wrap:true};
   t.cells.block({row:r,column:c,rowCount:1,columnCount:1}).assign({margins:{left:15,right:15,top:12,bottom:10},anchor:'center'});
  }
 }
 return t;
}
function blankPage(p,d){
 const q=structuredClone(p);
 if(d.id==='education'){
  if(q.kind==='numbers'&&q.title.startsWith('주 '))q.title='수업 유형과 운영 시간';
  if(q.role==='evidence')q.lead='회사 자료와 현행 제공 범위를 대조해 수행 근거를 작성합니다.';
  if(q.role==='timeline')q.lead='계약 기간과 교육 일정에 맞춰 운영 단계와 보고 시점을 작성합니다.';
 }
 q.data=q.data.map((row,r)=>row.map((value,c)=>{
  if((q.kind==='table'||q.kind==='gantt')&&r===0)return value;
  if(c===0){
   if(d.id==='education'&&q.kind==='numbers')return ['운영 기준','선택 유형','지원 범위'][r];
   if(d.id==='education'&&q.role==='timeline')return ['운영 1단계','운영 2단계'][r];
   return value;
  }
  if(q.kind==='gantt')return '확인';
  if(['architecture','tree'].includes(q.kind))return value.replace(/\n/g,' · ');
  return c===1?'사업에 맞는 세부 내용 작성':'조건·기준·근거 확인 필요';
 }));
 return q;
}
async function cover(s,d,C,variant,sample){
 s.background.fill=C.bg;
 const photoFile=path.join(assets,d.id+(d.id==='education'?'.png':'.jpg'));
 const right=variant===0;
 s.images.add({blob:new Uint8Array(await fs.readFile(photoFile)),contentType:d.id==='education'?'image/png':'image/jpeg',alt:`${d.name} 분야 설명용 이미지. 실제 제안사 수행 사진 아님`,fit:'cover',position:{left:right?626:0,top:0,width:654,height:720}});
 const x=right?64:718;
 text(s,d.name+' 제안서',x,65,490,40,24,C.accent,true,'bid3-fixed-section');
 const title=sample?d.sample.replace(' ','\n'):d.name+'\n사업 제안서';
 text(s,title,x,197,490,210,56,C.ink,true,'bid3-title');
 text(s,sample?d.sampleStatus:'사업명 · 발주기관 · 제안사 작성',x,464,490,77,24,C.ink);
 text(s,d.variants[variant][1],x,613,490,33,18,C.accent,false,'bid3-fixed-design-name');
 text(s,'01',right?545:1190,669,40,30,20,C.accent,true,'bid3-fixed-page','right');
}
function compose(s,p,C,variant){
 const data=p.data;
 switch(p.kind){
 case 'contents':
  data.forEach(([head,body],i)=>{const y=275+i*83;text(s,String(i+1).padStart(2,'0'),64,y,92,50,36,C.accent,true);text(s,head,184,y+2,376,48,29,C.ink,true);text(s,body,583,y+5,633,56,25,C.ink);if(i<3)rule(s,184,y+67,1032,C.soft);});break;
 case 'table':case 'gantt':nativeTable(s,data,C);break;
 case 'compare':{
  const width=(1152-48*(data.length-1))/data.length;
  data.forEach(([head,body],i)=>{const x=64+i*(width+48);text(s,String(i+1).padStart(2,'0'),x,283,width,72,57,C.accent,true);rule(s,x,374,width,C.accent);text(s,head,x,407,width,86,31,C.ink,true);text(s,body,x,502,width,118,25,C.ink);});break;
 }
 case 'flow':{
  const gap=34,width=(1152-gap*(data.length-1))/data.length;
  data.forEach(([head,body],i)=>{const x=64+i*(width+gap);text(s,String(i+1).padStart(2,'0'),x,282,width,58,35,C.accent,true);node(s,head,body,x,359,width,230,C);if(i<data.length-1)connector(s,x+width,466,gap,0,C);});break;
 }
 case 'numbers':
  data.slice(0,2).forEach(([n,b],i)=>{const x=64+i*592;text(s,n,x,285,555,113,80,C.accent,true);rule(s,x,424,555,C.accent);text(s,b,x,453,550,96,28,C.ink);});
  if(data[2]){text(s,data[2][0],64,576,425,57,27,C.accent,true);text(s,data[2][1],510,579,706,65,24,C.ink);}break;
 case 'lanes':{
  const stride=data.length===2?154:112;
  data.forEach(([a,b,c],i)=>{const y=283+i*stride;text(s,a,64,y,260,55,30,C.accent,true);text(s,b,344,y+2,470,78,25,C.ink);text(s,c,849,y+2,367,78,24,C.ink);if(i<data.length-1)rule(s,64,y+stride-25,1152,C.soft);});break;
 }
 case 'tree':{
  const [root,...branches]=data;
  node(s,root[0],root[1],397,268,486,139,C);
  connector(s,640,407,0,42,C);connector(s,235,449,810,0,C);
  branches.forEach(([head,body],i)=>{const x=64+i*406;connector(s,x+170,449,0,24,C);node(s,head,body,x,473,340,165,C);});break;
 }
 case 'architecture':{
  data.forEach((row,i)=>{const y=279+i*115; text(s,row[0],64,y+20,230,55,29,C.accent,true);const cells=row.slice(1);const width=(894-20*(cells.length-1))/cells.length;cells.forEach((label,j)=>{node(s,label,'',322+j*(width+20),y,width,83,C);});if(i<data.length-1)connector(s,770,y+83,0,32,C);});break;
 }
 case 'before_after':
  data.forEach(([head,body,detail],i)=>{const x=64+i*592;text(s,head,x,283,540,55,34,C.accent,true);rule(s,x,365,560,C.accent);text(s,body,x,393,540,125,31,C.ink,true);if(detail)text(s,detail,x,535,540,105,25,C.ink);});break;
 case 'questions':
  data.forEach(([a,b,c],i)=>{const y=277+i*(350/data.length);text(s,`${String(i+1).padStart(2,'0')}`,64,y,80,50,33,C.accent,true);text(s,a,165,y,420,68,29,C.ink,true);text(s,b,620,y+2,596,65,25,C.ink);if(c)text(s,c,620,y+58,596,38,22,C.accent);if(i<data.length-1)rule(s,165,y+350/data.length-16,1051,C.soft);});break;
 case 'verification':
  data.forEach(([a,b,c],i)=>{const y=282+i*85;text(s,a,64,y,290,60,28,C.accent,true);text(s,b,380,y+2,c?400:836,60,24,C.ink);if(c)text(s,c,821,y+2,395,60,24,C.ink);if(i<data.length-1)rule(s,64,y+68,1152,C.soft);});break;
 case 'evidence':
  data.forEach(([head,body],i)=>{const y=282+i*109;text(s,head,64,y,528,48,29,C.accent,true);text(s,body,64,y+48,528,68,24,C.ink);});
  text(s,'원문 자료와 제출 증빙',704,300,472,53,29,C.accent,true,'bid3-material-placeholder-heading');
  text(s,'회사 소개서의 관련 이미지·도표를\n현재 사업의 수행 근거와 대조합니다.',704,385,472,123,25,C.ink,false,'bid3-material-placeholder-copy');
  text(s,'자료가 없으면 현행 증빙 확보 후 반영',704,547,472,65,23,C.accent,false,'bid3-material-placeholder-notice');break;
 default:throw new Error('Unknown composition '+p.kind);
 }
}

const configs=[];
for(const d of domains){
 for(let variant=0;variant<2;variant++){
  for(const sample of variant===0?[false,true]:[false]){
   const [suffix,name,bg,ink,accent,soft]=d.variants[variant],id=d.id+'_'+suffix;
   const stem=sample?`sample_${id}`:id;
   if(process.env.ONLY_DOMAIN&&process.env.ONLY_DOMAIN!==d.id)continue;
   const build=path.join(work,'build',stem);await fs.mkdir(build,{recursive:true});
   const deck=Presentation.create({slideSize:{width:W,height:H}}),C={bg,ink,accent,soft};
   const first=deck.slides.add();await cover(first,d,C,variant,sample);
   const metadata={'1':{role:'cover',theme_id:d.id,kind:'cover',use_when:d.name+' 사업명',content_budget:'사업명·발주기관·제안사·제출일'}};
   for(const [index,raw]of d.pages.entries()){
    const p=sample?raw:blankPage(raw,d),n=index+2,s=deck.slides.add();header(s,p,d,n,C,sample,variant);
    if(index===1&&p.kind==='compare'){
     await detailPhoto(s,d,666,280,550,335);
     p.data.forEach(([head,body],i)=>{const y=281+i*112;text(s,head,64,y,542,45,29,C.accent,true);text(s,body,64,y+47,542,69,24,C.ink);});
     text(s,d.id==='education'?'AI 생성 교육 장면 · 실제 소속 강사 사진 아님':'분야 설명용 사진 · 실제 제안사 수행 사진 아님',666,626,550,30,15,C.accent,false,'bid3-fixed-image-caption');
    }else compose(s,p,C,variant);
    metadata[n]={role:p.role,theme_id:d.id,kind:p.kind,use_when:p.title,content_budget:p.lead+' / '+p.data.map(r=>r[0]).join(', ')};
    if(p.kind==='evidence')metadata[n].material_slot=[.54,.39,.41,.44];
   }
   const last=deck.slides.add();last.background.fill=ink;
   const closingPhoto=!['education','construction','event'].includes(d.id);
   if(closingPhoto)await detailPhoto(last,d,800,0,480,720);
   text(last,d.closing,64,167,closingPhoto?696:1120,210,64,'#FFFFFF',true,'bid3-title');
   text(last,sample?'수행 범위와 증빙을 확인한 뒤 제출안을 확정합니다.':'제안사 · 담당자 · 연락처 작성',69,468,closingPhoto?665:1100,112,28,'#FFFFFF');
   text(last,d.name+' 제안서',64,669,800,28,18,'#FFFFFF',false,'bid3-fixed-footer');text(last,'14',1167,665,49,33,22,'#FFFFFF',true,'bid3-fixed-page','right');
   metadata['14']={role:'closing',theme_id:d.id,kind:'closing',use_when:'제안 마무리',content_budget:'제안 요약·연락처'};
   const notes=refs.filter(r=>d.sourceIds.includes(r.id)).map(r=>`${r.kind}: ${r.title}\n${r.url}`).join('\n\n');
   deck.slides.items.forEach((s,i)=>{const imageId=i===0?d.id:(i===2&&!closingPhoto)||(i===13&&closingPhoto)?d.id+'-detail':'';const credit=imageSources.find(a=>a.id===imageId);s.speakerNotes.text=`${sample?d.sampleStatus:'재사용 분야별 작성 양식'}\n${sample&&d.id!=='education'?'가상 사업의 수행 방법 예시. 실제 발주조건·제안사 실적·가격·인력·인증을 의미하지 않음.':''}\n${credit?credit.use+'\n이미지 출처: '+credit.url:''}\n구조 참고 원문. 과거 사례의 수치와 과업조건은 현재 사업으로 전용하지 않음.\n${notes}${sample&&d.id==='education'?'\n교육 조건은 기존 R26BK01759488 KOTRA 공고 기반 검토용. 제출 전 원문·정정 공고와 대조 필요.':''}`;});
   const candidate=path.join(build,'candidate.pptx'),final=path.join(output,sample?'samples':'templates',stem+'.pptx');
   await (await PresentationFile.exportPptx(deck)).save(candidate);
   const tableOwners=d.pages.flatMap((p,i)=>['table','gantt'].includes(p.kind)?[i+2]:[]);
   await finalizePresentation({workspaceDir:work,candidatePath:candidate,finalPath:final,pythonExecutable:process.env.RUNTIME_PYTHON,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--validate-bullet-geometry',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:14,requiredNativeTableOwnerSlides:tableOwners,fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation-'+Date.now()+'.json')});
   const cfg={id,stem,sample,theme_id:d.id,name:d.name+' · '+name,category:d.name,description:d.summary,structure_summary:d.summary,outline:d.pages.map(p=>p.title),tags:[d.short,'분야별 구조','편집 가능한 도표'],collection:'분야별 제안서',file:id+'.pptx',target_slides:14,palette:{bg,ink,accent,soft},license_note:'BID3 자체 제작. 공개 원문은 구조 연구에 참고. 사진은 분야 설명용이며 회사 실적 증빙이 아닙니다.',metadata};
   cfg.output_directory=path.basename(output);
   configs.push(cfg);await fs.writeFile(path.join(build,'config.json'),JSON.stringify(cfg,null,2));
   console.log(JSON.stringify({output:stem,slides:14,tables:tableOwners}));
  }
 }
}
let all=configs;
if(process.env.ONLY_DOMAIN){
 const previous=JSON.parse(await fs.readFile(path.join(work,'configs.json'),'utf8'));
 all=previous.map(c=>configs.find(n=>n.stem===c.stem)||c);
}
await fs.writeFile(path.join(work,'configs.json'),JSON.stringify(all,null,2));
