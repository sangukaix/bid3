"""Install the sanitized photo template and previews; never publish the company example."""
import argparse,json,hashlib,shutil
from pathlib import Path
from pptx import Presentation

parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True)
parser.add_argument('--deck',type=Path);parser.add_argument('--receipt',type=Path);args=parser.parse_args()
root=Path(__file__).resolve().parents[2];library=root/'server/proposal_templates/library';work=args.work.resolve()
source=args.deck or work/'output/education_photo.pptx'
validation=json.loads((args.receipt or work/'build/education_photo-validation.json').read_text('utf-8'))
assert validation['finalSha256']==hashlib.sha256(source.read_bytes()).hexdigest()
assert validation['packageIntegrity']['status']=='pass' and validation['firstPartyImport']['passed']
roles=['cover','contents','summary','problem','domain','strategy','domain','strategy','domain','metrics','quality','quality','metrics','timeline','organization','quality','security','domain','deliverables','governance','closing']
names=['표지','제안의 구성','교육 운영의 핵심 제안','업무와 함께 이어지는 학습','언어와 목적별 교육','예습·수업·복습 흐름','교육과정과 교재','수업 시간과 이용 환경','AI·영상·일일 학습','출석·수료 기준','강사 선발·훈련·평가','학습 평가와 피드백','연차별 예산·실비 정산','연차별 운영 일정','직접 투입 인력과 조직','문의·차질 대응','전원 보안교육·정보 보호','회사 서비스·학습 콘텐츠','운영 보고와 인계','직접 수행·계약 준수','제안의 약속']
slots=json.loads((work/'build/photo-slots.json').read_text('utf-8'))
layouts={str(i+1):{'role':roles[i],'theme_id':'education','kind':'photo' if i+1 in [1,2,3,4,6,7,8,9,11,12,14,17,18,21] else 'diagram',
    'use_when':name,'content_budget':'사진·화면·도식을 유지하고 항목별 핵심 설명만 작성합니다. 상세 원문·검수표는 별도 파일에 보존합니다.',
    **({'material_slot':slots[str(i+1)]} if str(i+1) in slots else {})} for i,name in enumerate(names)}
catalog_path=library/'catalog.json';catalog=json.loads(catalog_path.read_text('utf-8'))
entry={'id':'education_photo','theme_id':'education','name':'교육·연수 · 러닝 세이지 포토','category':'교육·연수',
 'description':'큰 사진과 회사 서비스 화면, 학습 흐름·운영 도식 중심의 사진형 제안서',
 'structure_summary':'사진·서비스 화면·학습 흐름·보안·계약 수행을 시각적으로 구성. 검수표는 별도 PDF.',
 'outline':names[1:-1],'tags':['사진형','회사 원문 재사용','검수표 별도'],'collection':'분야별 제안서','file':'education_photo.pptx',
 'target_slides':21,'composition':'photo','palette':{'bg':'#F5F6EE','ink':'#283D35','accent':'#427354','soft':'#E8EDDF'},
 'license_note':'BID3 승인 사진형 디자인을 재사용. 생성 사진은 가상 설명 장면. 회사 업로드·특정 공고·회사 수치가 없는 공용 양식.'}
catalog=[e for e in catalog if e['id']!='education_photo'];position=next(i for i,e in enumerate(catalog) if e['id']=='education_learning');catalog.insert(position,entry)
target=library/'education_photo.pptx';shutil.copy2(source,target)
previews=library/'previews/education_photo';previews.mkdir(parents=True,exist_ok=True)
for number in range(1,22):shutil.copy2(work/f'render-template/{number:02d}.png',previews/f'slide_{number:03d}.png')
(previews/'manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'slide_count':21},indent=2)+'\n',encoding='utf-8')
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
layout_path=library/'layouts.json';all_layouts=json.loads(layout_path.read_text('utf-8'))
for number,meta in all_layouts.get('education_photo.pptx',{}).items():
    if number in layouts and meta.get('element_briefs'):
        layouts[number]['element_briefs']=meta['element_briefs']
all_layouts['education_photo.pptx']=layouts
layout_path.write_text(json.dumps(all_layouts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Installed shared photo template: 21 slides, 21 matching previews, no company example.')
