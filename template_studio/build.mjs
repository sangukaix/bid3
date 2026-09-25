import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {catalog,pages} from './catalog.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime=process.env.BID3_ARTIFACT_RUNTIME;
const skill=process.env.BID3_PRESENTATION_SKILL;
if(!runtime||!skill) throw new Error('Set BID3_ARTIFACT_RUNTIME (node_modules) and BID3_PRESENTATION_SKILL.');
process.env.RUNTIME_NODE_MODULES=runtime;
const require=createRequire(path.join(runtime,'package.json'));
const {Presentation,PresentationFile}=require('@oai/artifact-tool');
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
const build=path.join(root,'.local','template-studio');
const output=path.join(build,process.env.BID3_TEMPLATE_REVISION||'final-v1');
await fs.mkdir(output,{recursive:true});
const font='Malgun Gothic';
const art={};
for(const name of ['navy-glass','sage-paper','plum-silk']) art[name]=new Uint8Array(await fs.readFile(path.join(root,'template_studio','assets',`${name}.png`)));
const coverArt={civic_navy:'navy-glass',digital_midnight:'navy-glass',public_cobalt:'navy-glass',research_indigo:'navy-glass',supply_steel:'navy-glass',learning_sage:'sage-paper',policy_paper:'sage-paper',forest_plan:'sage-paper',terra_field:'sage-paper',tourism_moss:'sage-paper',culture_plum:'plum-silk',cloud_violet:'plum-silk',executive_wine:'plum-silk',community_lavender:'plum-silk',studio_ruby:'plum-silk'};

function text(slide,value,x,y,w,h,size,color,bold=false,align='left',name='body') {
  const shape=slide.shapes.add({name:name==='title'?'bid3-title':name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={typeface:font,fontSize:size,bold,color,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:true};
  return shape;
}

function footer(slide,t,n) {
  text(slide,'제안서',64,669,750,22,14,t.palette.accent,false,'left','bid3-fixed-footer');
  text(slide,String(n).padStart(2,'0'),1150,661,65,32,20,t.palette.accent,false,'right','bid3-fixed-page');
}

function narrowHeading(value) {
  const lines = [];
  for (const word of value.split(' ')) {
    const last = lines.at(-1);
    const candidate = last ? `${last} ${word}` : word;
    const units = [...candidate].reduce((sum, character) => sum + (character === ' ' ? 0.5 : 1), 0);
    if (last && units <= 6) lines[lines.length - 1] = candidate;
    else lines.push(word);
  }
  return lines.join('\n');
}

function contentFrame(slide,t,p,n) {
  const {bg,ink,accent}=t.palette; slide.background.fill=bg;
  const sidebar=t.composition==='sidebar';
  const numbered=t.composition==='numbered';
  const editorial=t.composition==='editorial';
  const x=sidebar?326:64, width=sidebar?890:1152;
  if(sidebar) {
    text(slide,String(n).padStart(2,'0'),64,60,220,100,70,accent,true,'left','bid3-fixed-section');
    text(slide,narrowHeading(p.title),64,210,215,220,35,ink,true,'left','title');
  } else if(numbered) {
    text(slide,String(n).padStart(2,'0'),64,56,105,90,61,accent,true,'left','bid3-fixed-section');
    text(slide,p.title,201,63,1005,90,43,ink,true,'left','title');
  } else {
    text(slide,p.title,64,65,1152,90,editorial?46:43,ink,true,t.composition==='centered'?'center':'left','title');
  }
  footer(slide,t,n);
  return {x,y:sidebar?88:204,w:width,h:sidebar?525:408};
}

function cover(slide,t,p,closing=false) {
  const {bg,ink,accent}=t.palette, c=t.composition;
  const dark=c==='dark'||c==='statement';
  slide.background.fill=dark?ink:bg;
  const primary=dark?'#FFFFFF':ink, secondary=dark?'#D8E2EE':accent;
  const names=closing?p.labels:['사업명 확인 필요','사업 제안서','제안사 확인 필요 · 제출일 확인 필요'];
  const v=t.variant%3;
  if(coverArt[t.id]) {
    const which=coverArt[t.id],right=which==='plum-silk';
    slide.images.add({blob:art[which],contentType:'image/png',alt:'BID3 original generated background',fit:'cover',position:{left:0,top:0,width:1280,height:720}});
    const color=which==='navy-glass'?'#FFFFFF':ink, muted=which==='navy-glass'?'#D9E7FE':accent;
    const x=right?566:72,w=right?636:785,y=214+v*42;
    text(slide,closing?'제안의 핵심':'사업 제안서',x,104,w,56,27,muted,false,'left','bid3-fixed-eyebrow');
    text(slide,closing?(right?'수행 범위\n확인 필요':names[0]):'[사업명]',x,y,w,210,70,color,true,'left','title');
    text(slide,closing?names[1]:'발주기관 확인 필요',x,y+229,w,62,25,muted);
    text(slide,names[2],x,590,w,69,20,muted);
    return;
  }
  if(c==='centered') {
    text(slide,closing?'제안의 핵심':'사업 제안서',100,145,1080,65,27,secondary,false,'center');
    text(slide,names[0],112,280,1056,140,68,primary,true,'center','title');
    text(slide,names[2],180,537,920,60,22,secondary,false,'center');
  } else if(c==='split'||c==='sidebar') {
    text(slide,closing?'핵심 제안':'사업 제안서',70,96,350,100,36,secondary,true);
    text(slide,names[0],(c==='split'?510:450),233,(c==='split'?690:750),196,68,primary,true,'left','title');
    text(slide,names[2],(c==='split'?510:450),546,700,75,22,secondary);
    text(slide,closing?'협의 사항 확인 필요':'발주기관 확인 필요',70,546,320,75,23,secondary);
  } else if(c==='numbered') {
    text(slide,closing?'20':'01',70,85,345,230,150,secondary,true,'left','bid3-fixed-section');
    text(slide,names[0],447,245,750,180,65,primary,true,'left','title');
    text(slide,closing?'제안의 핵심':'사업 제안서',451,174,740,50,26,secondary);
    text(slide,names[2],450,552,745,60,22,secondary);
  } else if(c==='editorial'||c==='ledger') {
    text(slide,closing?'제안의 핵심':'사업 제안서',70,78,700,50,26,secondary);
    text(slide,names[0],70,220+v*22,1110,145,78,primary,true,'left','title');
    text(slide,closing?'실행 원칙 확인 필요':'발주기관 확인 필요',73,440+v*15,900,65,29,secondary);
    text(slide,names[2],73,603,1000,55,22,secondary);
  } else if(c==='offset') {
    text(slide,closing?'제안의 핵심':'사업 제안서',72,74,1000,60,26,secondary);
    text(slide,names[0],330,274,850,160,70,primary,true,'right','title');
    text(slide,names[2],330,549,850,70,23,secondary,false,'right');
    text(slide,closing?'협의 사항 확인 필요':'발주기관 확인 필요',72,554,235,80,20,secondary);
  } else {
    text(slide,closing?'제안의 핵심':'사업 제안서',74,90,1110,62,27,secondary);
    text(slide,names[0],74,250+v*15,1110,175,74,primary,true,'left','title');
    text(slide,names[2],78,561,1030,60,23,secondary);
  }
}

function body(slide,t,p,n) {
  const f=contentFrame(slide,t,p,n), {ink,accent,soft}=t.palette;
  if(p.kind==='table') {
    const values=[p.headers,...Array.from({length:p.rows},(_,i)=>p.headers.map((_,j)=>j===0?`항목 ${i+1} 확인 필요`:'확인 필요'))];
    const table=slide.tables.add({rows:values.length,columns:p.headers.length,left:f.x,top:f.y,width:f.w,height:f.h,values});
    table.borders.assign({fill:t.palette.bg,width:2});
    table.cells.block({row:0,column:0,rowCount:values.length,columnCount:p.headers.length}).assign({textStyle:{typeface:font,fontSize:24,color:ink},margins:{left:18,right:18,top:16,bottom:12},anchor:'center'});
    for(let r=0;r<values.length;r++) for(let c=0;c<p.headers.length;c++) {
      const cell=table.getCell(r,c); cell.fill=r===0?accent:(r%2?soft:t.palette.bg);
      cell.text.style={typeface:font,fontSize:r===0?23:24,color:r===0?'#FFFFFF':ink,bold:r===0};
    }
    return;
  }
  if(p.kind==='contents') {
    const columns=t.variant%2===0?2:1, gap=70;
    p.labels.forEach((label,i)=>{
      const col=columns===1?0:i%2, row=columns===1?i:Math.floor(i/2);
      const w=columns===1?f.w:(f.w-gap)/2, x=f.x+col*(w+gap), y=f.y+row*(columns===1?100:205);
      text(slide,String(i+1).padStart(2,'0'),x,y,65,55,29,accent,true,'left','bid3-fixed-number');
      text(slide,label,x+80,y,w-80,95,columns===1?30:28,ink,true);
    }); return;
  }
  if(p.kind==='summary') {
    const side=t.variant%2===0;
    if(side) {
      text(slide,'핵심 제안\n내용 확인 필요',f.x,f.y,f.w*0.43,f.h,41,accent,true);
      p.labels.forEach((label,i)=>{
        const x=f.x+f.w*0.5,y=f.y+i*140;
        text(slide,label,x,y,f.w*0.5,44,24,ink,true);
        text(slide,'공고와 회사 자료에 따른 내용 확인 필요',x,y+51,f.w*0.5,79,23,ink);
      });
    } else {
      text(slide,'핵심 제안 내용 확인 필요',f.x,f.y,f.w,95,41,accent,true);
      const w=(f.w-64)/3;
      p.labels.forEach((label,i)=>{
        text(slide,label,f.x+i*(w+32),f.y+151,w,68,27,ink,true);
        text(slide,'공고와 회사 자료에 따른 내용 확인 필요',f.x+i*(w+32),f.y+244,w,145,24,ink);
      });
    } return;
  }
  if(p.kind==='process') {
    const vertical=t.composition==='sidebar'||t.variant%3===0;
    p.labels.forEach((label,i)=>{
      if(vertical) {
        const y=f.y+i*104;
        text(slide,String(i+1).padStart(2,'0'),f.x,y,65,64,36,accent,true,'left','bid3-fixed-number');
        text(slide,label,f.x+92,y,f.w*0.34,85,27,ink,true);
        text(slide,'활동·담당·산출물 확인 필요',f.x+f.w*0.5,y+5,f.w*0.5,83,24,ink);
      } else {
        const w=(f.w-90)/4,x=f.x+i*(w+30);
        text(slide,String(i+1).padStart(2,'0'),x,f.y,w,76,47,accent,true,'left','bid3-fixed-number');
        text(slide,label,x,f.y+108,w,103,28,ink,true);
        text(slide,'활동과 산출물\n확인 필요',x,f.y+252,w,138,24,ink);
      }
    });return;
  }
  const stacked=(t.composition==='ledger'||t.variant%5===4)&&p.kind==='comparison';
  const count=p.labels.length, gap=48, width=stacked?f.w:(f.w-gap*(count-1))/count;
  p.labels.forEach((label,i)=>{
    const x=stacked?f.x:f.x+i*(width+gap),y=stacked?f.y+i*203:f.y;
    text(slide,label,x,y,stacked?f.w*0.35:width,stacked?130:110,29,accent,true);
    text(slide,'공고·회사 자료에 근거한\n세부 내용 확인 필요',stacked?x+f.w*0.41:x,stacked?y:y+146,stacked?f.w*0.59:width,stacked?159:210,25,ink);
  });
}

const picked=process.argv[2]?catalog.filter(t=>t.id===process.argv[2]):catalog;
for(const t of picked) {
  if(await fs.stat(path.join(output,t.file)).then(()=>true,()=>false)) {console.log(JSON.stringify({id:t.id,status:'already-finalized'}));continue;}
  const presentation=Presentation.create({slideSize:{width:1280,height:720}});
  for(const [index,p] of pages.entries()) {
    const s=presentation.slides.add();
    if(p.kind==='cover'||p.kind==='closing') cover(s,t,p,p.kind==='closing'); else body(s,t,p,index+1);
    s.speakerNotes.textFrame.setText(`BID3 original template: ${t.name}. Role: ${p.role}. Example fields are not verified project facts. Replace only with evidence from the selected notice and company documents. No external template assets included.`);
  }
  const candidate=path.join(build,`${path.basename(output)}-${t.id}.draft.pptx`),final=path.join(output,`${t.id}.pptx`);
  await (await PresentationFile.exportPptx(presentation)).save(candidate);
  await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,pythonExecutable:process.env.BID3_ARTIFACT_PYTHON,
    integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
    explicitTotalSlideCount:20,layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...[6,7,11,12,15,17,19].flatMap(n=>['--require-native-table-slide',String(n)])],
    requiredNativeTableOwnerSlides:[6,7,11,12,15,17,19],fontPolicy:{basis:'design',families:[font]},
    verifyArtifactToolImport:true,receiptPath:path.join(build,`${path.basename(output)}-${t.id}.validation.json`)});
  console.log(JSON.stringify({id:t.id,status:'finalized',slides:20}));
}
await fs.writeFile(path.join(build,'catalog.json'),JSON.stringify(catalog,null,2)+'\n');
const layouts=Object.fromEntries(catalog.map(t=>[t.file,Object.fromEntries(pages.map((p,i)=>[String(i+1),{role:p.role,use_when:p.title,content_budget:p.kind==='table'?'4개 이하 항목, 셀별 핵심 문구':p.labels?.join(', ')||p.title}]))]));
await fs.writeFile(path.join(build,'layouts.json'),JSON.stringify(layouts,null,2)+'\n');
