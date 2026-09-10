"""Build the BIB V-groove schematic as editable PPTX and SVG objects."""

from pathlib import Path
from html import escape
import argparse, math, json, zipfile
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.xmlchemy import OxmlElement

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    '--output-dir',
    type=Path,
    default=Path(__file__).resolve().parents[2] / 'assets/cases/bib-v-groove/generated',
    help='directory for the editable PPTX, SVG, and validation report',
)
args = parser.parse_args()
OUT = args.output_dir
OUT.mkdir(parents=True, exist_ok=True)
prs=Presentation(); prs.slide_width=Inches(12); prs.slide_height=Inches(7.3)
slide=prs.slides.add_slide(prs.slide_layouts[6]); slide.background.fill.solid(); slide.background.fill.fore_color.rgb=RGBColor(255,255,255)
# Shared vector scene in reference-derived coordinates, with generous white margin.
S=12/720; OX=45; OY=40
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="876" viewBox="0 0 720 438"><rect width="720" height="438" fill="#FFFFFF"/>']
counts={'polygons':0,'segments':0,'textboxes':0}
def xy(p): return (p[0]+OX,p[1]+OY)
def group(name):
    g=slide.shapes.add_group_shape(); g.name=name; return g.shapes
def poly(name, pts, fill, parent=None, stroke=None, width=.65, opacity=1.0):
    parent=parent if parent is not None else slide.shapes
    ps=[xy(p) for p in pts]
    precise=[(round(x*1000),round(y*1000)) for x,y in ps]
    b=parent.build_freeform(precise[0][0],precise[0][1],scale=Inches(S)/1000); b.add_line_segments(precise[1:],close=True); sh=b.convert_to_shape(); sh.name=name
    sh.fill.solid(); sh.fill.fore_color.rgb=RGBColor.from_string(fill)
    if opacity < 1.0:
        alpha=OxmlElement('a:alpha'); alpha.set('val',str(round(opacity*100000)))
        sh._element.spPr.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr').append(alpha)
    if stroke: sh.line.color.rgb=RGBColor.from_string(stroke); sh.line.width=Pt(width)
    else: sh.line.fill.background()
    sh._element.spPr.append(OxmlElement('a:effectLst'))
    if hasattr(parent,'_recalculate_extents'): parent._recalculate_extents()
    svg.append(f'<polygon id="{name}" points="'+ ' '.join(f'{x},{y}' for x,y in ps)+f'" fill="#{fill}" fill-opacity="{opacity}"'+(f' stroke="#{stroke}" stroke-width="{width}"' if stroke else '')+'/>')
    counts['polygons']+=1
    return sh
def line(name, pts, color='222222', width=1.4, parent=None, dash=False):
    parent=parent if parent is not None else slide.shapes
    for i,(a,b) in enumerate(zip(pts,pts[1:])):
        if dash:
            dx,dy=b[0]-a[0],b[1]-a[1]; d=math.hypot(dx,dy)
            intervals=max(1,round(d/13)); step=d/intervals; dash_length=step*0.54
            for j in range(intervals+1):
                st=max(0,j*step-dash_length/2); e=min(d,j*step+dash_length/2)
                line(name+f'-dash{i}-{j}',[(a[0]+dx*st/d,a[1]+dy*st/d),(a[0]+dx*e/d,a[1]+dy*e/d)],color,width,parent)
            continue
        p,q=xy(a),xy(b)
        from pptx.enum.shapes import MSO_CONNECTOR
        sh=parent.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(p[0]*S), Inches(p[1]*S), Inches(q[0]*S), Inches(q[1]*S)); sh.name=name+f'-{i}'
        sh.line.color.rgb=RGBColor.from_string(color); sh.line.width=Pt(width)
        sh._element.spPr.append(OxmlElement('a:effectLst'))
        svg.append(f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="#{color}" stroke-width="{width/1.2}"/>'); counts['segments']+=1
def arrow(name,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; n=math.hypot(dx,dy); ux,uy=dx/n,dy/n
    g=group(name)
    line(name,[a,(b[0]-ux*9,b[1]-uy*9)],width=2.2,parent=g)
    poly(name+'-head',[b,(b[0]-ux*10-uy*4,b[1]-uy*10+ux*4),(b[0]-ux*10+uy*4,b[1]-uy*10-ux*4)],'222222',g)
def txt(name,text,x,y,w,h,size=18,align='left',rotation=0):
    xx,yy=xy((x,y)); sh=slide.shapes.add_textbox(Inches(xx*S),Inches(yy*S),Inches(w*S),Inches(h*S)); sh.name=name
    sh.rotation=rotation
    tf=sh.text_frame; tf.clear(); tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0; tf.word_wrap=False; tf.vertical_anchor=MSO_ANCHOR.MIDDLE
    p=tf.paragraphs[0]; p.alignment=PP_ALIGN.CENTER if align=='center' else PP_ALIGN.LEFT
    r=p.add_run(); r.text=text; r.font.name='Arial'; r.font.size=Pt(size*1.2); r.font.color.rgb=RGBColor(0,0,0)
    anchor='middle' if align=='center' else 'start'; sx=xx+w/2 if align=='center' else xx
    transform=f' transform="rotate({rotation} {xx+w/2} {yy+h/2})"' if rotation else ''
    svg.append(f'<text id="{name}" x="{sx}" y="{yy+h/2}" dominant-baseline="central" text-anchor="{anchor}" font-family="Arial, sans-serif" font-size="{size}" fill="#000000"{transform}>{escape(text)}</text>'); counts['textboxes']+=1

# Front and right faces. No additional layer is introduced.
def layer(name,leftTop,rightTop,backTop,leftBottom,rightBottom,backBottom,front,side):
    g=group(name)
    poly(name+'-front',[(31,leftTop),(382,rightTop),(382,rightBottom),(31,leftBottom)],front,g)
    poly(name+'-right',[(382,rightTop),(552,backTop),(552,backBottom),(382,rightBottom)],side,g)
layer('High purity substrate',243,296,184,304,357,245,'BDBDBD','D5D5D5')
layer('Bottom contact',221,274,162,243,296,184,'B9C9B0','CFDCC2')
layer('AL',171,223,111,221,274,162,'EAD59B','F1E2B8')
layer('BL',132,186,74,171,223,111,'A9CDDA','C1DDE6')
g=group('Passivation layer')
poly('Passivation-continuous-surface',[(31,132),(201,20),(242,28),(552,74),(552,82),(382,194),(31,140)],'639BB5',g)
poly('Groove-rear-opening',[(242,0),(314,0),(314,33),(242,81)],'FFFFFF',g)

# Reference groove: two long lips and converging inclined metallized walls.
g=group('V groove and grounded Al contact')
# One native outline eliminates seams between identically colored metal faces.
poly('Groove-continuous-metal',[(31,132),(201,20),(242,28),(242,81),(314,33),(354,39),(354,42),(182,154),(145.761,148),(137,258),(86,249),(75.292,142),(31,135)],'DFA95F',g)
# Three top-contact pads, in the same positions as the source.
g=group('Top contact pads')
for name,pts in [('front',[(311,174),(327,163),(365,169),(353,181)]),('middle',[(368,133),(401,108),(447,115),(416,141)]),('rear',[(465,78),(487,59),(528,65),(507,83)])]:
    if name in ('front', 'middle', 'rear'):
        # A true parallelogram aligned with both axes of the device top plane.
        # Equal vertical extrusion on both visible edges forms a thin cuboid.
        a,depth,pad_width={'front':((311,174),16,38),'middle':((369,131),32,46),'rear':((465,78),22,41)}[name]
        b=(a[0]+depth,a[1]-depth*112/170)
        d=(a[0]+pad_width,a[1]+pad_width*54/351)
        c=(b[0]+pad_width,b[1]+pad_width*54/351)
        pts=[a,b,c,d]
        if name == 'front':
            # Preserve the source pad footprint at the front edge.
            a,b,c,d=(311,174),(327,163),(365,169),(353,181)
            pts=[a,b,c,d]
        thickness=3 if name == 'front' else 2.5
        if name == 'front':
            # Local pale region visible beneath the front contact in the source.
            # This is a local face detail, not an added full device layer.
            poly('Top-contact-front-pale-underface',[(a[0],a[1]+3),(d[0],d[1]+3),(d[0],d[1]+9),(a[0],a[1]+9)],'E9BEC2',g,opacity=0.42)
            # Retract only the metal pad along the top-plane depth axis.
            # Keep its lower front edge at the device rim, not over the BL face.
            retreat=(0,0)
            a,b,c,d=[(p[0]+retreat[0],p[1]+retreat[1]) for p in (a,b,c,d)]
            pts=[a,b,c,d]
        poly('Top-contact-'+name,[a,b,c,(c[0],c[1]+thickness),(d[0],d[1]+thickness),(a[0],a[1]+thickness)],'DFA95F',g)
        continue
    poly('Top-contact-'+name,pts,'DFA95F',g)
    a,b=pts[-2],pts[-1]
    poly('Top-contact-'+name+'-edge',[a,b,(b[0],b[1]+3),(a[0],a[1]+3)],'DFA95F',g)

g=group('Yellow dashed contours')
line('front-contour',[(227,157),(243,146.458824),(327,159.381901),(311,169.923077)],'EAD59B',1.5,g,True)
line('middle-contour',[(349,131.461538),(281,121),(336,84.764706),(404,95.226244),(349,131.461538)],'EAD59B',1.5,g,True)
line('rear-contour',[(373,65),(389,54.458824)],'EAD59B',1.5,g,True)
line('rear-contour-long',[(373,65),(450,76.846154),(466,66.304978)],'EAD59B',1.5,g,True)

g=group('Ground connection')
line('Ground-wire',[(128,92),(128,37),(30,19),(30,61)],parent=g)
for i,(x1,x2,y) in enumerate([(16,44,61),(21,39,70),(26,34,78)]): line('Ground-bar'+str(i),[(x1,y),(x2,y)],parent=g)
g=group('Positive bias connection')
line('Positive-wire',[(414,119),(414,76),(571,100),(571,186)],parent=g)
sh=g.add_shape(MSO_SHAPE.OVAL,Inches((567+OX)*S),Inches((186+OY)*S),Inches(8*S),Inches(8*S)); sh.name='Bias terminal'; sh.fill.solid(); sh.fill.fore_color.rgb=RGBColor(255,255,255); sh.line.color.rgb=RGBColor(34,34,34); sh.line.width=Pt(1.4)
sh._element.spPr.append(OxmlElement('a:effectLst'))
svg.append(f'<circle cx="{571+OX}" cy="{190+OY}" r="4" fill="white" stroke="#222222" stroke-width="1.2"/>')

# Text stays separate from groups so every label is directly editable.
txt('Label-passivation','Passivation layer',322,-20,205,26,18)
arrow('Passivation pointer',(363,17),(363,69))
txt('Label-negative-contact','Al:V−',137,79,78,24,18)
txt('Label-positive-contact','Al:V+',396,144,82,23,18)
txt('Label-groove-1','V',85,162,34,23,18,'center')
txt('Label-groove-2','groove',71,186,65,23,16,'center')
txt('Label-BL','BL',233,180,44,25,20,'center',8.7)
txt('Label-AL','AL',224,221,45,26,20,'center',8.7)
txt('Label-bottom-contact','Bottom contact',177,255,167,24,18,'center',8.7)
txt('Label-substrate','High purity substrate',99,289,253,28,19,'center',8.7)
txt('Label-bias','+V',551,199,46,26,20,'center')
# Source callout points upward to the contact crossing the front edge.
txt('Label-top-contact','Top contact',277,226,137,24,16)
g=group('Top contact pointer')
poly('Top contact solid black arrow',[(329,225),(337,225),(337,195),(341,195),(333,188),(325,195),(329,195)],'000000',g)

# Disable inherited theme outlines and effects as well as explicit shadows.
# Preserve explicit connector and terminal lines used by the electrical diagram.
for element in slide._element.iter():
    if element.tag.endswith('}style'):
        for ref in element:
            if ref.tag.endswith('}effectRef') or ref.tag.endswith('}lnRef'):
                ref.set('idx','0')
    if element.tag.endswith('}spPr'):
        for effect in list(element):
            if effect.tag.endswith('}effectLst') or effect.tag.endswith('}effectDag'):
                element.remove(effect)
        element.append(OxmlElement('a:effectLst'))
prs.save(OUT/'BIB_structure_editable.pptx')
svg.append('</svg>'); (OUT/'BIB_structure.svg').write_text('\n'.join(svg),encoding='utf-8')
with zipfile.ZipFile(OUT/'BIB_structure_editable.pptx') as z:
    media=[n for n in z.namelist() if n.startswith('ppt/media/')]
    assert not media,media
assert len(prs.slides)==1
(OUT/'validation.json').write_text(json.dumps({'slide_count':1,'raster_media':0,**counts},indent=2))
print(counts)
