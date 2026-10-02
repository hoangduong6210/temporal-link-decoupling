from pathlib import Path
import re,sys,subprocess,copy,hashlib,json,os,shutil
from docx import Document
from docx.shared import Cm,Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK,WD_TAB_ALIGNMENT,WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
P=Path(__file__).resolve().parent.parent
W=P/'Latex_full/build/word';W.mkdir(parents=True,exist_ok=True)
pandoc=os.environ.get('PANDOC') or shutil.which('pandoc')
if not pandoc:raise SystemExit('Set PANDOC to a Pandoc executable or put pandoc on PATH')
source=(P/'Latex_full/main.tex').read_text()
text=source.split(r'\begin{document}\normalsize',1)[1].split(r'\end{document}')[0]
keys=re.findall(r'\\bibitem\{([^}]+)\}',text);numbers={k:i+1 for i,k in enumerate(keys)}
text=re.sub(r'\\cite\{([^}]+)\}',lambda m:'['+', '.join(str(numbers[k]) for k in m[1].split(','))+']',text)
labels={k:i+1 for i,k in enumerate(re.findall(r'\\label\{(eq:[^}]+)\}',text))}
text=re.sub(r'\\eqref\{([^}]+)\}',lambda m:'('+str(labels[m[1]])+')',text)
text=re.sub(r'\{\\rm ([^}]+)\}',r'{\\mathrm{\1}}',text)
text=text.replace(r'\bar a',r'\overline{a}')
text=text.replace(r'\sigma',r'\sigma').replace(r'\sg',r'\operatorname{sg}').replace(r'\AP',r'\operatorname{AP}')
text=re.sub(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', '\n\nFIGUREPLACEHOLDER\n\n',text,flags=re.S)
text=text.replace(r'\begin{minipage}{\linewidth}\centering','').replace(r'\end{minipage}','')
table_sources=re.findall(r'\\begin\{center\}\s*\\captionof\{table\}.*?\\end\{center\}',text,re.S)
table_numbers={key:i+1 for i,block in enumerate(table_sources) for key in re.findall(r'\\label\{([^}]+)\}',block)}
text=re.sub(r'\\ref\{([^}]+)\}',lambda m:str(table_numbers[m[1]]),text)
for i,block in enumerate(table_sources):text=text.replace(block,'\n\nTABLEPLACEHOLDER'+str(i)+'\n\n')
text=text.replace(r'\captionof{figure}{Scored feature path in the primary comparison.}',r'\textbf{Figure 1. Scored feature path in the primary comparison.}')
text=text.replace(r'\captionof{table}{Registered experimental settings.}',r'\textbf{Table 1. Registered experimental settings.}').replace(r'\captionof{table}{Inductive AP: mean and sample SD.}',r'\textbf{Table 2. Inductive AP: mean and sample SD.}')
# Display equations are preserved as native Office Math; labels are appended after conversion.
def eq(m):
 content=m[2];ids=re.findall(r'\\label\{([^}]+)\}',content)
 if len(ids)>1:
  chunks=content.split(r'\\')
  return '\n\n'.join(eq(type('M',(),{'__getitem__':lambda self,k: 'equation' if k==1 else c})()) for c in chunks if c.strip())
 content=re.sub(r'\\label\{[^}]+\}|\\nonumber','',content)
 content=content.replace(r'\!', '')
 content=content.replace('&','')
 if m[1]=='align':content=r'\begin{aligned}'+content+r'\end{aligned}'
 return '\n\n$$'+content+'$$\n\nEQUATIONNUMBER'+'AND'.join(str(labels[k]) for k in ids)+'\n\n'
text=re.sub(r'\\begin\{(align|equation)\}(.*?)\\end\{\1\}',eq,text,flags=re.S)
text=re.sub(r'\\bibitem\{([^}]+)\}',lambda m:'\n\nREFNUMBER'+str(numbers[m[1]])+' ',text)
text=re.sub(r'\\begin\{thebibliography\}\{99\}|\\end\{thebibliography\}|\\begingroup|\\endgroup|\\renewcommand\{\\section\}\[2\]\{\}','',text)
text=text.replace(r'\begin{multicols}{2}','').replace(r'\end{multicols}','')
text=re.sub(r'\\fontsize\{[^}]+\}\{[^}]+\}\\selectfont','',text)
text=re.sub(r'\\vspace\{[^}]+\}','',text)
text=re.sub(r'\\begin\{list\}\{\}\{.*?\}\\item\[\]', '',text) if False else text
# Remove the known abstract-list wrapper while preserving its content.
text=text.replace(r'\begin{list}{}{\setlength{\leftmargin}{2cm}\setlength{\rightmargin}{2cm}}\item[]','').replace(r'\end{list}','')
text=text.replace(r'\clearpage','\n\nSECTIONBREAK\n\n')
text=re.sub(r'%[^\n]*','',text)
(W/'word-input.tex').write_text(text)
subprocess.run([str(pandoc),'-f','latex','-t','docx',str(W/'word-input.tex'),'--reference-doc',str(P/'Word/template.docx'),'-o',str(W/'word-raw.docx')],check=True)
d=Document(W/'word-raw.docx');d.core_properties.title='Gradient Decoupling for Inductive Temporal Link Prediction: A Controlled Study of Stateful Representations';d.core_properties.author='Duong Viet Hoang; Duong Viet Huy; Lun-Min Shih';d.core_properties.comments=''
# Source-template geometry and style package are retained; demonstration content is replaced.
for sec in d.sections:
 sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.top_margin=Cm(3.5);sec.bottom_margin=sec.left_margin=sec.right_margin=Cm(2)
 sec.header_distance=Cm(1);sec.footer_distance=Cm(1.2);sec.different_first_page_header_footer=False
 for h in (sec.header,sec.first_page_header,sec.even_page_header):
  for x in list(h._element):h._element.remove(x)
 for foot in (sec.footer,sec.first_page_footer,sec.even_page_footer):
  for x in list(foot._element):foot._element.remove(x)
  pp=foot.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;rr=pp.add_run();rr.font.name='Times New Roman';rr.font.size=Pt(8);fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');rr._r.addnext(fld)
base=d.styles['Normal'];base.font.name='Times New Roman';base.font.size=Pt(9)
base.paragraph_format.line_spacing=Pt(13.5);base.paragraph_format.space_after=Pt(0);base.paragraph_format.space_before=Pt(0)
for st in d.styles:
 if st.type==1 or st.type==2:
  st.font.name='Times New Roman';st.font.color.rgb=__import__('docx').shared.RGBColor(0,0,0)
  st._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Songti TC')
for name,size in [('Title',18),('Heading 1',11),('Heading 2',9)]:
 if name not in d.styles:d.styles.add_style(name,1)
 st=d.styles[name];st.font.size=Pt(size);st.font.bold=True;st.paragraph_format.keep_with_next=True
 st.paragraph_format.space_before=Pt(10 if name=='Heading 1' else 6);st.paragraph_format.space_after=Pt(4)
 st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER if name!='Heading 2' else WD_ALIGN_PARAGRAPH.LEFT
# Sectionbreak paragraphs carry previous-section properties. Final section is Chinese abstract.
sect_template=copy.deepcopy(d.sections[-1]._sectPr)
def section_props(cols):
 q=copy.deepcopy(sect_template)
 for v in list(q):
  if v.tag in [qn('w:cols'),qn('w:type'),qn('w:pgNumType'),qn('w:titlePg')]:q.remove(v)
 typ=OxmlElement('w:type');typ.set(qn('w:val'),'nextPage');q.append(typ)
 c=OxmlElement('w:cols');c.set(qn('w:num'),str(cols));c.set(qn('w:space'),'424');q.append(c)
 return q
part=0;section_count=0;sub=0;in_refs=False;abstract=False;prev=None
roman=['I','II','III','IV','V','VI','VII']
for pp in list(d.paragraphs):
 t=pp.text.strip();pf=pp.paragraph_format
 if pp.style is None:pp.style=d.styles['Normal']
 pf.space_before=Pt(0);pf.space_after=Pt(0);pf.line_spacing=Pt(13.5);pf.line_spacing_rule=WD_LINE_SPACING.AT_LEAST;pf.widow_control=True
 # Remove template direct line/character grid overrides.
 for node in list(pp._p.xpath('./w:pPr/w:pageBreakBefore')):node.getparent().remove(node)
 for run in pp.runs:
  run.font.name='Times New Roman';run.font.size=Pt(9);run.font.color.rgb=__import__('docx').shared.RGBColor(0,0,0)
  run._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Songti TC')
 if t=='SECTIONBREAK':
  pp.clear();pp._p.get_or_add_pPr().append(section_props(1 if part==0 else 2));part+=1;abstract=False;prev=pp;continue
 if t.startswith('EQUATIONNUMBER'):
  num=t[len('EQUATIONNUMBER'):].replace('AND',', ')
  if prev is not None:
   prev.add_run('  ('+num+')');prev.alignment=WD_ALIGN_PARAGRAPH.CENTER;prev.paragraph_format.space_before=Pt(5);prev.paragraph_format.space_after=Pt(5);prev.paragraph_format.line_spacing=1.0;prev.paragraph_format.keep_together=True
  pp._p.getparent().remove(pp._p);continue
 if t.startswith('TABLEPLACEHOLDER'):
  idx=int(t[len('TABLEPLACEHOLDER'):]);block=table_sources[idx]
  caption=re.search(r'\\captionof\{table\}\{([^}]+)\}',block)[1]
  pp.text='Table '+str(idx+1)+'. '+caption;pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.keep_with_next=True;pf.first_line_indent=Pt(0);pf.space_before=Pt(6);pf.space_after=Pt(5)
  for rr in pp.runs:rr.bold=True
  raw=re.search(r'\\begin\{tabular\}[^\n]+\n(.*?)\\end\{tabular\}',block,re.S)[1]
  raw=re.sub(r'\\(?:toprule|midrule|bottomrule)','',raw)
  rows=[]
  for line in raw.split(r'\\'):
   if not line.strip():continue
   line=line.replace(r'\pm','±').replace(r'\mathbf','').replace('$','').replace('{','').replace('}','')
   rows.append([c.strip() for c in line.split('&')])
  tab=d.add_table(rows=len(rows),cols=len(rows[0]));tab.autofit=False
  for rr,vals in zip(tab.rows,rows):
   for cell,value in zip(rr.cells,vals):cell.text=value
  pp._p.addnext(tab._tbl);prev=pp;continue
 if t=='FIGUREPLACEHOLDER':
  pp.clear();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
  # An editable table makes the four stages readable in Word as well as legacy DOC.
  tab=d.add_table(rows=4,cols=1);tab.autofit=False;tab.columns[0].width=Cm(6.7)
  vals=['Retained event history and candidate attributes\nNode memory and pair-history context ↓','Temporal backbone Fθ\nCandidate representation h ↓','Shared scored boundary\nConnected h or detached sg(h) ↓','Registered hierarchical readout Gψ\nPositive and negative link scores']
  for cell,val in zip(tab.column_cells(0),vals):
   cell.text=val;cp=cell.paragraphs[0];cp.alignment=WD_ALIGN_PARAGRAPH.CENTER;cp.paragraph_format.space_before=Pt(5);cp.paragraph_format.space_after=Pt(5)
   for rr in cp.runs:rr.font.name='Times New Roman';rr.font.size=Pt(8)
   tcpr=cell._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
   for side in ['top','left','bottom','right']:
    e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'444444');b.append(e)
   tcpr.append(b)
  pp._p.addnext(tab._tbl);prev=pp;continue
 if part in [0,2]:
  pf.first_line_indent=Pt(0);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
  if t.startswith('Gradient Decoupling') or t.startswith('歸納式時序連結預測中的梯度解耦'):
   pp.style=d.styles['Title'];pf.line_spacing=1.25;pf.space_after=Pt(12)
   for rr in pp.runs:rr.font.size=Pt(18);rr.bold=True
  elif t in ['ABSTRACT','摘要']:
   abstract=True;pf.space_before=Pt(16);pf.space_after=Pt(8)
   for rr in pp.runs:rr.font.size=Pt(11);rr.bold=True
  elif abstract:
   pp.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY;pf.left_indent=pf.right_indent=Cm(2)
   if t.startswith(('Key words','關鍵詞')):pf.space_before=Pt(10)
  elif t.startswith('Duong Viet Hoang'):
   for rr in pp.runs:rr.font.size=Pt(10)
   pf.space_after=Pt(6)
 else:
  pp.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY;pf.first_line_indent=Pt(13.5)
  if pp.style.name.startswith('Heading 1'):
   pf.first_line_indent=Pt(0);pf.space_before=Pt(12);pf.space_after=Pt(6);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
   if t=='References Cited':in_refs=True
   else:section_count+=1;sub=0;pp.text=roman[section_count-1]+'. '+t
   for rr in pp.runs:rr.font.size=Pt(11);rr.bold=True
  elif pp.style.name.startswith('Heading 2'):
   sub+=1;pp.text=str(sub)+'. '+t;pp.alignment=WD_ALIGN_PARAGRAPH.LEFT;pf.first_line_indent=Pt(0);pf.space_before=Pt(8);pf.space_after=Pt(3)
   for rr in pp.runs:rr.font.size=Pt(9);rr.bold=True
  elif t.startswith('REFNUMBER'):
   pp.text=re.sub(r'^REFNUMBER(\d+) ',r'\1. ',t);pp.style=d.styles['Normal'];pp.alignment=WD_ALIGN_PARAGRAPH.LEFT;pf.left_indent=Cm(.5);pf.first_line_indent=Cm(-.5);pf.space_after=Pt(3);pf.line_spacing=Pt(13.5)
   for rr in pp.runs:rr.font.size=Pt(9)
  elif t.startswith(('Figure 1.','Table 1.','Table 2.')):
   pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.first_line_indent=Pt(0);pf.keep_with_next=t.startswith('Table');pf.space_before=Pt(5);pf.space_after=Pt(5)
  elif pp._p.xpath('.//m:oMathPara'):
   pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.first_line_indent=Pt(0)
 prev=pp
last=d._element.body.sectPr
new=section_props(1);last.getparent().replace(last,new)
for tab in d.tables:
 tab.autofit=False
 borders=OxmlElement('w:tblBorders')
 for side in ['top','bottom','left','right','insideH','insideV']:
  edge=OxmlElement('w:'+side);edge.set(qn('w:val'),'single');edge.set(qn('w:sz'),'4');edge.set(qn('w:color'),'AAAAAA');borders.append(edge)
 tab._tbl.tblPr.append(borders)
 if len(tab.columns)==2:widths=[3.45,3.8]
 elif len(tab.columns)==3:widths=[2.1,2.6,2.6] if tab.cell(0,0).text=='Configuration' else [1.7,2.5,3.1]
 elif len(tab.columns)==4:widths=[1.65,1.65,2.3,2.3]
 else:widths=[6.7]
 for col,width in zip(tab.columns,widths):col.width=Cm(width)
 for ri,row in enumerate(tab.rows):
  for cell,width in zip(row.cells,widths):
   cell.width=Cm(width)
   for pp in cell.paragraphs:
    pp.paragraph_format.keep_with_next=ri<len(tab.rows)-1;pp.paragraph_format.line_spacing=1.2;pp.paragraph_format.space_after=Pt(2);pp.paragraph_format.space_before=Pt(2)
    for rr in pp.runs:rr.font.name='Times New Roman';rr.font.size=Pt(8)
  trpr=row._tr.get_or_add_trPr();n=OxmlElement('w:cantSplit');trpr.append(n)
for mr in d._element.xpath('.//m:r'):
 wr=mr.find(qn('w:rPr'))
 if wr is None:wr=OxmlElement('w:rPr');mr.insert(1 if mr.find(qn('m:rPr')) is not None else 0,wr)
 sz=OxmlElement('w:sz');sz.set(qn('w:val'),'18');wr.append(sz)
settings=d.settings.element;hy=OxmlElement('w:autoHyphenation');hy.set(qn('w:val'),'true');settings.append(hy)
n=OxmlElement('w:updateFields');n.set(qn('w:val'),'true');settings.append(n)
(P/'Word').mkdir(exist_ok=True)
d.save(P/'Word/DYU_Journal_Manuscript.docx')
print('Word saved; equations',len(d._element.xpath('.//m:oMathPara')),'references',len(keys))
