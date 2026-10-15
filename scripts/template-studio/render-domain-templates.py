"""Render exact final PPTX bytes in installed PowerPoint before publishing."""
import os,sys,json,hashlib
from pathlib import Path
import pypdfium2 as pdfium

root=Path(__file__).resolve().parents[2]
w=root/'.local/theme-studio-20261014'
sys.path.insert(0,str(root/'server'));os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
import django;django.setup()
from bids.services.proposal_preview import _convert_with_powerpoint
from bids.services.proposal_pptx_renderer import inspect_proposal_quality

configs=json.loads((w/'configs.json').read_text('utf-8'));reports=[]
for cfg in configs:
    if os.environ.get('ONLY_DOMAIN') and cfg['theme_id']!=os.environ['ONLY_DOMAIN']:continue
    folder=w/cfg.get('output_directory',os.environ.get('OUTPUT_DIR','output'))/('samples' if cfg['sample'] else 'templates')
    source=folder/(cfg['stem']+'.pptx');pdf=source.with_suffix('.pdf')
    if not pdf.exists():assert _convert_with_powerpoint(source.resolve(),pdf.resolve()),source
    render=folder/cfg['stem'];render.mkdir(exist_ok=True)
    with pdfium.PdfDocument(str(pdf)) as doc:
        assert len(doc)==14
        for index in range(len(doc)):
            page=doc[index];bitmap=page.render(scale=4/3 if cfg['sample'] else 1)
            im=bitmap.to_pil();im.save(render/f'slide_{index+1:03d}.png');im.close();bitmap.close();page.close()
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    (render/'manifest.json').write_text(json.dumps(dict(source_sha256=digest,slide_count=14)),encoding='utf-8')
    quality=inspect_proposal_quality(source.read_bytes())
    reports.append(dict(stem=cfg['stem'],slides=14,sha256=digest,overflow=quality['overflow_items'],placeholders=quality['unresolved_placeholders']))
    print(cfg['stem'], '14 rendered',len(quality['overflow_items']),'overflow flags',flush=True)
(w/'render-report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
