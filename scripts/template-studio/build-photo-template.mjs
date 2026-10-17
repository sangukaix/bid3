// Adapt the approved photo design; the shared template must contain no company uploads.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const args=Object.fromEntries(process.argv.slice(2).map((v,i,a)=>v.startsWith('--')?[v.slice(2),a[i+1]]:null).filter(Boolean));
const require=createRequire(path.join(process.env.RUNTIME_NODE_MODULES,'package.json'));
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const source=path.resolve(args.source),work=path.resolve(args.work),generic=args.mode==='template';
await fs.mkdir(path.join(work,'build'),{recursive:true});
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const C={bg:'#F5F6EE',ink:'#283D35',accent:'#427354',muted:'#617266',soft:'#E8EDDF'};
function text(s,value,x,y,w,h,size=27,color=C.ink,bold=false,name='visual-body'){
 const sh=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=value;sh.text.insets=0;sh.text.style={typeface:'Malgun Gothic',fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',wrap:true};return sh;
}
function setText(slide,old,value){const sh=slide.shapes.items.find(s=>s.text.toString()===old);if(!sh)throw new Error('Missing source text: '+old);sh.text=value;}
// Preserve the original cover art and hero headline; name the official project in full.
setText(p.slides.items[0],'2027–2028 교육과정 운영 제안','2027-2028년 KOTRA 전화외국어 교육과정 운영 위탁');
const coverLead=p.slides.items[0].shapes.items.find(s=>s.text.toString().startsWith('2027-2028년 KOTRA'));
coverLead.position={left:64,top:99,width:1152,height:70};coverLead.text.style={typeface:'Malgun Gothic',fontSize:25,color:C.accent};
setText(p.slides.items[10],'강사의 수업 역량을 확인하고 학습 피드백으로 개선합니다.','시차를 고려한 국내·현지 강사와 제2외국어 고급 강사 Pool 편성');
setText(p.slides.items[10],'언어·티칭 역량 확인','전문 원어민·티칭 역량 확인');
setText(p.slides.items[12],'예산은 예정 물량 기준이며 지급 보장 금액이 아닙니다.','예산은 최근 3개년 이행예정량 기준이며 지급 보장 금액이 아닙니다.');
setText(p.slides.items[14],'발주기관과 PM을 중심으로 교육·학습지원·정산 업무를 연결합니다.','상근직원 기준의 현장 투입 가능 인력으로 역할을 구성합니다.');
setText(p.slides.items[14],'역할 구성안 · 실명·투입 인력·재직 및 자격 증빙은 확인 후 반영','연령·근무경력: 제출일 현재 기준 / 실명·재직·현장 투입·자격 증빙 확인 필요');
// The security photograph remains in place. Use four short, native process labels.
const security=p.slides.items[16];
let snapshot=await p.inspect({kind:'textbox,shape,image,table,chart',maxChars:0});
p.delete(snapshot.records.filter(r=>r.slideIndex===16&&['textbox','shape'].includes(r.kind)
 && !['bid3-title','bid3-fixed-footer','bid3-fixed-page','source-caption'].includes(r.name)).map(r=>r.id));
text(security,'참여 인력의 보안교육부터 정보 인계까지 관리합니다.',64,177,1152,56,27,C.muted);
[['전원 교육','전담·비전담 참여 인력 모두 교육'],['제3자 동의·서약','이름·소속·이력 제공 동의'],['접근·보관','권한·보관 기준과 운영 기록 관리'],['인계·삭제','종료 시 인계·삭제 결과 확인']].forEach(([head,body],i)=>{
 const y=248+i*89;text(security,String(i+1).padStart(2,'0'),64,y+3,48,38,23,C.accent,true);
 text(security,head,120,y,405,43,30,C.accent,true);text(security,body,120,y+45,405,43,23,C.muted);
});
setText(p.slides.items[17],'제출 전 대조할 자료','운영에 연결할 지원 체계');
setText(p.slides.items[17],'현행 서비스 범위 · 투입 인력 · 유사 실적 증빙','학습 콘텐츠 · 학습자 지원 · 운영 기록');
setText(p.slides.items[18],'운영 산출물과 제출 전 확인','운영 기록과 결과 인계');
setText(p.slides.items[18],'최종 확인: 제안사명·인력·실적 증빙 / 원문의 경쟁 방식 및 협력사 조항 / 제출 서류','운영 계획 → 월별 교육·정산 기록 → 최종 결과·정보 인계');
const tableRecord=snapshot.records.find(r=>r.kind==='table'&&r.slideIndex===18);
p.resolve(tableRecord.id).cells.set(0,2,'운영 주기');
// One editable contract diagram supplies required content without an audit appendix.
const contract=p.slides.add({background:{fill:C.bg}});
contract.moveTo(19);
text(contract,'직접 수행과 계약 관리',64,65,1152,90,46,C.ink,true,'bid3-title');
text(contract,'운영 책임과 산출물의 권리를 계약 기준에 맞춰 관리합니다.',64,177,1152,56,27,C.muted);
[['직접 수행','하도급 없이\n단일 플랫폼으로 운영'],['지적재산권','자료 사용 범위와\n산출물의 권리 관리'],['비밀 유지','참여 인력의 서약과\n정보 취급 기준 적용'],['지연 대응','차질 공유·복구 협의\n지연배상 조건 준수'],['최저임금 이상','고용노동부 고시 기준을\n근로자 고용계약에 반영'],['대금 지급 연계','상생결제(우리은행)\n또는 하도급지킴이 연계']].forEach(([head,body],i)=>{
 const x=64+(i%3)*395,y=263+Math.floor(i/3)*177;
 text(contract,String(i+1).padStart(2,'0'),x,y,62,48,37,C.accent,true);
 text(contract,head,x+72,y+3,285,48,29,C.ink,true);text(contract,body,x+72,y+61,285,90,22,C.muted);
});
text(contract,'협력사 지급은 해당 시 상생결제 활용에 협력 / 지급 경로·계약 조건은 공고 원문에 따라 확정',64,630,1152,30,16,C.muted,false,'source-caption');
text(contract,'2027–2028 KOTRA 전화외국어 교육',64,677,1090,28,16,C.accent,false,'bid3-fixed-footer');
text(contract,'20',1160,675,56,32,18,C.accent,false,'bid3-fixed-page');
for(const [i,s] of p.slides.items.entries()){
 for(const sh of s.shapes.items)if(sh.name==='bid3-fixed-page')sh.text=String(i+1).padStart(2,'0');
 if([16,18,19].includes(i))s.speakerNotes.text+='\n공고 R26BK01759488-000 제안요청서의 참여 인력 보안교육·직접수행·계약 관련 내용. 미래 수행안이며 현행 자격·실적 증빙이 아님. 내부 검수표는 별도 PDF로 보관.';
}
if(generic){
 snapshot=await p.inspect({kind:'textbox,shape,image,table,chart',maxChars:0});
 const privatePages=new Set([3,5,7,11,17]);
 p.delete(snapshot.records.filter(r=>r.kind==='image'&&privatePages.has(r.slideIndex)||r.kind==='chart').map(r=>r.id));
 const slots={4:[.05,.24,.50,.61],6:[.05,.32,.90,.38],8:[.65,.40,.30,.29],12:[.65,.32,.30,.52],18:[.65,.23,.30,.60]};
 for(const [number,slot] of Object.entries(slots)){
  const [x,y,w,h]=slot;const s=p.slides.items[Number(number)-1];
  s.shapes.add({name:'bid3-material-placeholder-image',geometry:'rect',position:{left:x*1280,top:y*720,width:w*1280,height:h*720},fill:C.soft,line:{fill:'none',width:0}});
 }
 // A literal budget chart cannot be reused for a different tender's figures.
 const budget=p.slides.items[12];
 text(budget,'1차 운영',64,285,450,50,32,C.accent,true);text(budget,'[연차별 예산]',64,355,450,55,32);
 text(budget,'2차 운영',64,465,450,50,32,C.accent,true);text(budget,'[연차별 예산]',64,535,450,55,32);
 snapshot=await p.inspect({kind:'textbox,shape',maxChars:0});
 for(const record of snapshot.records){
  if(!record.text)continue;const sh=p.resolve(record.id);
  let value=record.text;
  if(record.name==='bid3-fixed-footer')value='교육·연수 운영 제안';
  else if(record.name==='bid3-fixed-page')continue;
  else if(record.name==='source-caption'){
   value=privatePages.has(record.slideIndex)?'회사 원문 시각 자료를 배치하는 영역':'설명용 생성 이미지·구성 예시 · 실제 회사 수행 증빙 아님';
   sh.name='bid3-fixed-visual-caption';
  }else{
   value=value.replaceAll('당근영어','회사').replaceAll('KOTRA','발주기관')
    .replace(/2027-2028년 발주기관 전화외국어 교육과정 운영 위탁/g,'[공고명]')
    .replace(/2027[–~-]2028/g,'[사업기간]').replace(/202[78]\.\d{2}\.\d{2}\./g,'[운영일정]')
    .replace(/2027년|2028년|2027|2028/g,'[운영연차]')
    .replace(/287,910,000원/g,'[총사업예산]').replace(/143,955,000원/g,'[연차별예산]')
    .replaceAll('24개월','[사업기간]').replaceAll('30 · 50분','[주당수업시간]').replaceAll('30분','[수업시간]').replaceAll('50분','[수업시간]')
    .replaceAll('80%','[수료기준]').replaceAll('50%','[공고기준]')
    .replaceAll('상생결제(우리은행)','[대금지급시스템]').replaceAll('하도급지킴이','[지급경로]');
  }
  sh.text=value;
  if(value.includes('[')&&record.style?.fontSize>42)sh.text.style={...record.style,fontSize:34};
 }
 for(const s of p.slides.items)s.speakerNotes.text='BID3 사진형 교육 양식. 기존 승인 디자인의 배치·서체·사진 구성을 재사용. 회사 업로드 이미지·화면·본문·수치·검수 기록은 포함하지 않음. 생성 사진은 가상의 설명용 장면이며 실제 수행 증빙이 아님.';
 await fs.writeFile(path.join(work,'build/photo-slots.json'),JSON.stringify(slots));
}
const stem=generic?'education_photo':'KOTRA_사진형_재구성_20261017';
await (await PresentationFile.exportPptx(p)).save(path.join(work,'build/'+stem+'-candidate.pptx'));
console.log(JSON.stringify({mode:args.mode,slides:p.slides.items.length,stem}));
