"""Generate the publication diagram for Word: editable SVG and 600 dpi PNG."""
from pathlib import Path
import os
from PIL import Image, ImageDraw, ImageFont
OUT=Path(__file__).resolve().parent.parent/'Word/figures'
OUT.mkdir(parents=True,exist_ok=True)
font_path=os.environ.get('FIGURE_FONT','/System/Library/Fonts/Supplemental/Times New Roman.ttf')
scale=600/72
width,height=205.51,142
im=Image.new('RGB',(round(width*scale),round(height*scale)),'white')
draw=ImageDraw.Draw(im)
font=ImageFont.truetype(font_path,round(8*scale))
small=ImageFont.truetype(font_path,round(6*scale))
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="72.5mm" height="{height/72*25.4:.3f}mm" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="white"/>']
lines=[
['Retained event history, candidate attributes','Node memory and pair-history context'],
[('Temporal backbone F','θ'),'Candidate representation h'],
['Shared scored boundary','Connected h or detached sg(h)'],
[('Registered hierarchical readout G','ψ'),'Positive and negative link scores']]
for i,rows in enumerate(lines):
 y=4+i*36
 draw.rectangle(tuple(round(v*scale) for v in (2,y,width-2,y+26)),outline='black',width=round(.5*scale))
 svg.append(f'<rect x="2" y="{y}" width="{width-4}" height="26" fill="none" stroke="black" stroke-width=".5"/>')
 for j,row in enumerate(rows):
  baseline=y+10+j*10
  if isinstance(row,tuple):
   a,b=row;total=draw.textlength(a,font=font)+draw.textlength(b,font=small)
   x=(im.width-total)/2
   draw.text((x,baseline*scale),a,font=font,fill='black',anchor='ls')
   draw.text((x+draw.textlength(a,font=font),(baseline+2)*scale),b,font=small,fill='black',anchor='ls')
   text=a+f'<tspan baseline-shift="sub" font-size="6">{b}</tspan>'
  else:
   draw.text((im.width/2,baseline*scale),row,font=font,fill='black',anchor='ms');text=row
  svg.append(f'<text x="{width/2}" y="{baseline}" text-anchor="middle" font-family="Times New Roman,serif" font-size="8">{text}</text>')
 if i<3:
  x=width/2;top=y+26;bottom=y+36
  draw.line([(round(x*scale),round(top*scale)),(round(x*scale),round((bottom-2)*scale))],fill='black',width=round(.6*scale))
  draw.polygon([(round((x-2)*scale),round((bottom-4)*scale)),(round((x+2)*scale),round((bottom-4)*scale)),(round(x*scale),round(bottom*scale))],fill='black')
  svg.append(f'<path d="M{x} {top} V{bottom-2} M{x-2} {bottom-4} L{x} {bottom} L{x+2} {bottom-4}" fill="none" stroke="black" stroke-width=".6"/>')
svg.append('</svg>')
(OUT/'scored-feature-path.svg').write_text('\n'.join(svg))
im.save(OUT/'scored-feature-path.png',dpi=(600,600))
print(OUT)

