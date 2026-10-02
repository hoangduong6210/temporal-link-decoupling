"""Build an author-review manuscript by patching the journal template package.

Usage: python build_docx.py --template converted-template.docx --output manuscript.docx
Only manuscript text, template instruction slots, header/footer placeholders,
title style and update-fields setting are edited. Other package parts are preserved.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
def el(name, **attrs):
    e = ET.Element("{%s}%s" % (W, name))
    for k, v in attrs.items():
        e.set("{%s}%s" % (W, k), str(v))
    return e
def child(parent, name, **attrs):
    e = parent.find("w:"+name, NS)
    if e is None:
        e = el(name)
        parent.append(e)
    for k, v in attrs.items(): e.set("{%s}%s" % (W,k), str(v))
    return e
def xml(root):
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--template",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    rootdir=Path(__file__).resolve().parent
    source=rootdir/"manuscript.txt"
    with ZipFile(a.template) as z: parts={n:z.read(n) for n in z.namelist()}
    doc=ET.fromstring(parts["word/document.xml"])
    body=doc.find("w:body",NS)
    oldp=body.findall("w:p",NS)
    sects=doc.findall(".//w:sectPr",NS)
    assert len(sects)==3
    patterns={k:deepcopy(oldp[i]) for k,i in {
      "TITLE_EN":11,"TITLE_ZH":0,"AUTHORS":13,"AFFIL_EN":14,
      "AFFIL_ZH":3,"EMAIL":16,"ABSTRACT_EN":19,"ABSTRACT_ZH":8,
      "KEYWORDS_EN":20,"KEYWORDS_ZH":9,"H1":25,"H2":33,
      "P":26,"EQ":44,"TABLE_CAP":46,"REF":95}.items()}
    geometry=[deepcopy(s) for s in sects]
    for e in list(body): body.remove(e)
    def para(kind,text,size=None):
        p=deepcopy(patterns[kind])
        pp=p.find("w:pPr",NS)
        if pp is None: pp=el("pPr");p.insert(0,pp)
        for e in list(p):
            if e is not pp: p.remove(e)
        for name in ["rPr","numPr","sectPr","tabs","pageBreakBefore"]:
            for e in pp.findall("w:"+name,NS): pp.remove(e)
        child(pp,"spacing",line=360,lineRule="auto",before=0,after=0)
        child(pp,"widowControl")
        child(pp,"keepNext",val="1" if kind in ["TITLE_EN","TITLE_ZH","AUTHORS","AFFIL_EN","AFFIL_ZH","EMAIL","H1","H2","TABLE_CAP"] else "0")
        child(pp,"keepLines",val="1" if kind!="P" else "0")
        base_size={"TITLE_EN":18,"TITLE_ZH":18,"AUTHORS":10,"H1":11}.get(kind,9)
        size=size or base_size
        if kind.startswith("TITLE"):
            child(pp,"pStyle",val="Title")
            child(pp,"spacing",line=360,lineRule="auto",before=0,after=180)
        elif kind=="H1":
            child(pp,"spacing",line=360,lineRule="auto",before=180,after=90)
        elif kind=="H2":
            child(pp,"spacing",line=360,lineRule="auto",before=120,after=30)
        elif kind=="TABLE_CAP":
            child(pp,"spacing",line=360,lineRule="auto",before=100,after=60)
        if kind=="P": child(pp,"ind",left=0,right=0,firstLine=240)
        if kind=="REF":
            child(pp,"ind",left=240,hanging=240)
            child(pp,"spacing",line=360,lineRule="auto",before=0,after=40)
        if kind in ["ABSTRACT_EN","ABSTRACT_ZH","KEYWORDS_EN","KEYWORDS_ZH"]:
            child(pp,"ind",left=1134,right=1134,firstLine=0)
        if kind in ["H1","H2","TABLE_CAP","EQ","TITLE_EN","TITLE_ZH","AUTHORS","AFFIL_EN","AFFIL_ZH","EMAIL"]:
            child(pp,"ind",left=0,right=0,firstLine=0)
        if kind=="EQ":
            child(pp,"jc",val="left")
            child(pp,"spacing",line=360,lineRule="auto",before=180,after=180)
            tabs=child(pp,"tabs")
            tabs.append(el("tab",val="right",pos=4550))
            text=re.sub(r"\s+(\(\d+\))$",r"\t\1",text)
        rp=el("rPr")
        rp.append(el("rFonts",ascii="Times New Roman",hAnsi="Times New Roman",eastAsia="MingLiU",cs="Times New Roman"))
        rp.append(el("color",val="000000"));rp.append(el("sz",val=int(size*2)));rp.append(el("szCs",val=int(size*2)))
        if kind in ["TITLE_EN","TITLE_ZH","H1","H2","TABLE_CAP"]: rp.append(el("b"))
        if kind in ["AFFIL_EN","EMAIL"]: rp.append(el("i"))
        for i,seg in enumerate(text.split("\t")):
            if i:
                tabrun=el("r");tabrun.append(el("tab"));p.append(tabrun)
            r=el("r");r.append(deepcopy(rp))
            t=el("t");t.set("{http://www.w3.org/XML/1998/namespace}space","preserve");t.text=seg;r.append(t);p.append(r)
        # Word-native subscripts keep mathematical notation editable.
        for run in list(p.findall('w:r',NS)):
            ts=run.findall('w:t',NS)
            if len(ts)!=1 or run.find('w:tab',NS) is not None:
                continue
            value=ts[0].text or ''
            if not re.search(r'(?:F|G|φ|H|p)_(?:θ|ψ|uv|t|dec)',value):
                continue
            position=list(p).index(run)
            p.remove(run)
            pieces=re.split(r'((?:F|G|φ|H|p)_(?:θ|ψ|uv|t|dec))',value)
            for piece in pieces:
                sub=re.fullmatch(r'(F|G|φ|H|p)_(θ|ψ|uv|t|dec)',piece)
                segments=[(sub[1],False),(sub[2],True)] if sub else [(piece,False)]
                for value,is_sub in segments:
                    if not value: continue
                    nr=el('r');nrp=deepcopy(rp)
                    if is_sub:nrp.append(el('vertAlign',val='subscript'))
                    nr.append(nrp);nt=el('t');nt.text=value;nt.set('{http://www.w3.org/XML/1998/namespace}space','preserve');nr.append(nt)
                    p.insert(position,nr);position+=1
        return p
    def append(kind,text):
        p=para(kind,text);body.append(p);return p
    def section_break(s,ncols):
        s=deepcopy(s)
        child(s,"type",val="nextPage")
        for n in ["pgNumType","titlePg"]:
            for e in s.findall("w:"+n,NS):s.remove(e)
        child(s,"cols",num=ncols,space=424,equalWidth="true",sep="false")
        p=el("p");pp=el("pPr")
        pp.append(el("spacing",before=0,after=0,line=20,lineRule="exact"))
        pp.append(s);p.append(pp);body.append(p)
    def table(rows):
        nc=len(rows[0]);widths=[1980,2620] if nc==2 else [1150,1680,1770]
        tbl=el("tbl");pr=el("tblPr")
        pr.append(el("tblW",w=sum(widths),type="dxa"))
        pr.append(el("jc",val="center"));pr.append(el("tblLayout",type="fixed"))
        borders=el("tblBorders")
        for edge in ["top","left","bottom","right","insideH","insideV"]:
            borders.append(el(edge,val="single",sz=4,color="000000"))
        pr.append(borders)
        mar=el("tblCellMar")
        for edge in ["top","bottom"]:mar.append(el(edge,w=55,type="dxa"))
        for edge in ["left","right"]:mar.append(el(edge,w=55,type="dxa"))
        pr.append(mar);tbl.append(pr)
        grid=el("tblGrid")
        for w in widths:grid.append(el("gridCol",w=w))
        tbl.append(grid)
        for ri,row in enumerate(rows):
            tr=el("tr");trp=el("trPr");trp.append(el("cantSplit"))
            if ri==0:trp.append(el("tblHeader"))
            tr.append(trp)
            for ci,txt in enumerate(row):
                tc=el("tc");tcp=el("tcPr");tcp.append(el("tcW",w=widths[ci],type="dxa"));tcp.append(el("vAlign",val="center"));tc.append(tcp)
                p=para("P",txt,8);pp=p.find("w:pPr",NS)
                child(pp,"ind",left=0,right=0,firstLine=0)
                child(pp,"jc",val="left" if ci<nc-1 else "center")
                child(pp,"spacing",before=0,after=0,line=270,lineRule="auto")
                child(pp,"keepNext",val="1" if ri<len(rows)-1 else "0")
                if ri==0:
                    for rp in p.findall("w:r/w:rPr",NS): rp.append(el("b"))
                tc.append(p);tr.append(tc)
            tbl.append(tr)
        body.append(tbl)
        p=para("P","");child(p.find("w:pPr",NS),"spacing",line=60,lineRule="exact",after=0);body.append(p)
    lines=[x.split("\t",1) for x in source.read_text().splitlines() if x.strip()]
    enstart=next(i for i,x in enumerate(lines) if x[0]=="TITLE_EN")
    mainstart=next(i for i,x in enumerate(lines) if x[0]=="H1")
    zh,en,content=lines[:enstart],lines[enstart:mainstart],lines[mainstart:]
    def front(items,lang):
        for kind,text in items:
            if kind=="ABSTRACT_"+lang:
                p=para("H1","Abstract" if lang=="EN" else "摘　要")
                child(p.find("w:pPr",NS),"spacing",before=180,after=100,line=360,lineRule="auto")
                body.append(p)
            append(kind,text)
    front(en,"EN");section_break(geometry[0],1)
    i=0
    while i<len(content):
        kind,text=content[i]
        if kind.endswith("_ROW"):
            rows=[]
            while i<len(content) and content[i][0]==kind:
                rows.append(content[i][1].split("|"));i+=1
            table(rows);continue
        append(kind,text);i+=1
    section_break(geometry[1],2)
    front(zh,"ZH")
    last=deepcopy(geometry[2]);child(last,"cols",num=1,space=424,equalWidth="true",sep="false");child(last,"type",val="nextPage")
    for n in ["pgNumType","titlePg"]:
        for e in last.findall("w:"+n,NS):last.remove(e)
    body.append(last);parts["word/document.xml"]=xml(doc)
    styles=ET.fromstring(parts["word/styles.xml"])
    title=styles.find("w:style[@w:styleId='Title']",NS)
    if title is None:
        title=el("style",type="paragraph",styleId="Title")
        title.append(el("name",val="Title"));title.append(el("basedOn",val="Normal"));styles.append(title)
    parts["word/styles.xml"]=xml(styles)
    settings=ET.fromstring(parts["word/settings.xml"]);child(settings,"updateFields",val="true");parts["word/settings.xml"]=xml(settings)
    for name in list(parts):
        if re.fullmatch(r"word/header\d+\.xml",name):
            h=ET.fromstring(parts[name])
            for c in list(h):h.remove(c)
            p=para("P","Gradient Decoupling for Inductive Temporal Link Prediction",8)
            pp=p.find("w:pPr",NS);child(pp,"jc",val="left");child(pp,"ind",left=0,right=0,firstLine=0)
            child(pp,"tabs").append(el("tab",val="right",pos=9638))
            r=el("r");r.append(el("tab"));p.append(r)
            f=el("fldSimple",instr=" PAGE ");r=el("r");t=el("t");t.text="1";r.append(t);f.append(r);p.append(f);h.append(p)
            parts[name]=xml(h)
        if re.fullmatch(r"word/footer\d+\.xml",name):
            h=ET.fromstring(parts[name])
            for c in list(h):h.remove(c)
            h.append(el("p"));parts[name]=xml(h)
    core=ET.fromstring(parts["docProps/core.xml"])
    for c in list(core):core.remove(c)
    dc="http://purl.org/dc/elements/1.1/"
    t=ET.SubElement(core,"{%s}title"%dc);t.text=en[0][1]
    t=ET.SubElement(core,"{%s}creator"%dc);t.text="Duong Viet Hoang; Duong Viet Huy; Lun-Min Shih"
    parts["docProps/core.xml"]=xml(core)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(a.output,"w",ZIP_DEFLATED) as z:
        for n,b in parts.items():z.writestr(n,b)
    with ZipFile(a.template) as z:
        changed=[n for n in z.namelist() if z.read(n)!=parts[n]]
    print(json.dumps({"output":str(a.output),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"template_sha256":hashlib.sha256(a.template.read_bytes()).hexdigest(),"changed_package_parts":changed},indent=2))
if __name__=="__main__":main()
