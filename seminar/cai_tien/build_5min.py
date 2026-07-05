# -*- coding: utf-8 -*-
"""Condensed 5-minute standalone deck (our part only), VN + EN. cwd = repo root."""
import sys, re
sys.stdout.reconfigure(encoding="utf-8")
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

NAVY=RGBColor(0x1A,0x3A,0x5C); SUBTXT=RGBColor(0xB8,0xCF,0xE0); FOOTBG=RGBColor(0xEE,0xF4,0xFB)
FOOTTX=RGBColor(0x6B,0x7F,0x95); CARD2=RGBColor(0xE8,0xF0,0xF8); GREY=RGBColor(0x75,0x70,0x70)
INK=RGBColor(0x1C,0x27,0x36); INFO=RGBColor(0x1F,0x55,0x8C); CAV=RGBColor(0xA0,0x46,0x46)
CAVBG=RGBColor(0xFB,0xF1,0xF1); PAGECL=RGBColor(0x5A,0x5A,0x5A); WHITE=RGBColor(0xFF,0xFF,0xFF)
TFONT,BFONT="Cambria","Calibri"; SW,SH=10.0,5.625

def build(LANG):
    prs=Presentation(); prs.slide_width=Inches(SW); prs.slide_height=Inches(SH)
    BLANK=prs.slide_layouts[6]
    EN=(LANG=="en")
    def T(vn,en): return en if EN else vn
    def _set(run,size,color,bold=False,italic=False,font=BFONT):
        run.font.size=Pt(size); run.font.bold=bold; run.font.italic=italic; run.font.name=font; run.font.color.rgb=color
    def rect(slide,l,t,w,h,fill):
        sp=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(l),Inches(t),Inches(w),Inches(h))
        sp.fill.solid(); sp.fill.fore_color.rgb=fill; sp.line.fill.background(); sp.shadow.inherit=False; return sp
    def _runs(p,text):
        for seg in re.split(r"(\*\*.*?\*\*)",text):
            if not seg: continue
            r=p.add_run()
            if seg.startswith("**") and seg.endswith("**"): r.text=seg[2:-2]; yield (r,True)
            else: r.text=seg; yield (r,False)
    def tb_(slide,l,t,w,h,anchor=MSO_ANCHOR.TOP):
        tb=slide.shapes.add_textbox(Inches(l),Inches(t),Inches(w),Inches(h)); tf=tb.text_frame
        tf.word_wrap=True; tf.vertical_anchor=anchor
        tf.margin_left=Pt(2); tf.margin_right=Pt(2); tf.margin_top=Pt(1); tf.margin_bottom=Pt(1); return tf
    def header(slide,title,subtitle=None):
        h=1.30 if subtitle else 0.97; rect(slide,0,0,SW,h,NAVY)
        tf=tb_(slide,0.35,0.12 if subtitle else 0.20,9.3,0.60)
        for r,_ in _runs(tf.paragraphs[0],title): _set(r,22,WHITE,bold=True,font=TFONT)
        if subtitle:
            tf2=tb_(slide,0.37,0.76,9.2,0.45); r=tf2.paragraphs[0].add_run(); r.text=subtitle; _set(r,11.5,SUBTXT,italic=True)
        return h+0.15
    def footer(slide,page):
        rect(slide,0,5.34,SW,0.29,FOOTBG); tf=tb_(slide,0.35,5.40,7,0.18)
        r=tf.paragraphs[0].add_run(); r.text=T("Cải tiến MedRegA · Gemma 4 E4B (u gan LiTS)","MedRegA Improvements · Gemma 4 E4B (liver tumor, LiTS)"); _set(r,8.5,FOOTTX)
        tf2=tb_(slide,9.0,5.40,0.8,0.18); tf2.paragraphs[0].alignment=PP_ALIGN.RIGHT
        r2=tf2.paragraphs[0].add_run(); r2.text=str(page); _set(r2,9,PAGECL)
    def bullets(slide,items,l,t,w,h,base=14,gap=9):
        tf=tb_(slide,l,t,w,h); first=True
        for text,lvl in items:
            p=tf.paragraphs[0] if first else tf.add_paragraph(); first=False
            p.level=lvl; p.space_after=Pt(gap); p.space_before=Pt(0)
            pr=p.add_run(); pr.text=("▪  " if lvl==0 else "–  "); _set(pr,base,NAVY if lvl==0 else GREY,bold=(lvl==0))
            for r,isb in _runs(p,text): _set(r,base if lvl==0 else base-1,INK if lvl==0 else GREY,bold=isb)
    def notebox(slide,label,text,l,t,w,h,kind="info"):
        rect(slide,l,t,w,h,CARD2 if kind=="info" else CAVBG); tf=tb_(slide,l+0.12,t+0.07,w-0.24,h-0.14)
        r=tf.paragraphs[0].add_run(); r.text=label; _set(r,10.5,INFO if kind=="info" else CAV,bold=True)
        p2=tf.add_paragraph(); p2.space_before=Pt(1)
        for r,isb in _runs(p2,text): _set(r,10,INK,bold=isb)
    def image(slide,path,l,t,w=None,h=None,caption=None):
        kw={}
        if w: kw["width"]=Inches(w)
        if h: kw["height"]=Inches(h)
        pic=slide.shapes.add_picture(path,Inches(l),Inches(t),**kw)
        if caption:
            tf=tb_(slide,l,t+pic.height/914400+0.03,max(pic.width/914400,2.0),0.3)
            pp=tf.paragraphs[0]; pp.alignment=PP_ALIGN.CENTER; r=pp.add_run(); r.text=caption; _set(r,8,FOOTTX,italic=True)
        return pic
    def table(slide,headers,rows,l,t,w,colw=None,fs=11,hfs=11,rh=0.34,first_bold=True):
        g=slide.shapes.add_table(len(rows)+1,len(headers),Inches(l),Inches(t),Inches(w),Inches(rh*(len(rows)+1))).table
        g.first_row=False; g.horz_banding=False
        if colw:
            for i,cw in enumerate(colw): g.columns[i].width=Inches(cw)
        for j,htx in enumerate(headers):
            c=g.cell(0,j); c.fill.solid(); c.fill.fore_color.rgb=NAVY; c.vertical_anchor=MSO_ANCHOR.MIDDLE
            c.margin_left=Pt(5); c.margin_top=Pt(2); c.margin_bottom=Pt(2)
            for r,isb in _runs(c.text_frame.paragraphs[0],htx): _set(r,hfs,WHITE,bold=True)
        for i,row in enumerate(rows,1):
            for j,val in enumerate(row):
                c=g.cell(i,j); c.fill.solid(); c.fill.fore_color.rgb=WHITE if i%2 else CARD2; c.vertical_anchor=MSO_ANCHOR.MIDDLE
                c.margin_left=Pt(5); c.margin_top=Pt(1); c.margin_bottom=Pt(1)
                for r,isb in _runs(c.text_frame.paragraphs[0],val): _set(r,fs,INK,bold=(isb or (first_bold and j==0)))
    IOU=T("seminar/code/iou_frozen_vs_unfrozen.png","seminar/code/iou_frozen_vs_unfrozen_en.png")
    DET=T("seminar/code/detect_before_after.png","seminar/code/detect_before_after_en.png")

    # ---- S1 TITLE ----
    s=prs.slides.add_slide(BLANK)
    rect(s,0,0,SW,0.24,NAVY); rect(s,0,1.55,SW,2.30,NAVY)
    tf=tb_(s,0.5,1.72,9.0,1.0,MSO_ANCHOR.MIDDLE); p=tf.paragraphs[0]; p.alignment=PP_ALIGN.CENTER
    r=p.add_run(); r.text=T("Cải tiến của nhóm trên MedRegA","Our Improvements on MedRegA"); _set(r,36,WHITE,bold=True,font=TFONT)
    tf2=tb_(s,0.5,2.82,9.0,0.9);
    for i,line in enumerate([T("Fine-tune Gemma 4 E4B phát hiện u gan trên CT (LiTS)","Fine-tuning Gemma 4 E4B for liver-tumor detection on CT (LiTS)"),
                             T("Mô hình nhỏ — trung thực về đánh giá & độ tin cậy","A small model — honest about evaluation & reliability")]):
        pp=tf2.paragraphs[0] if i==0 else tf2.add_paragraph(); pp.alignment=PP_ALIGN.CENTER
        rr=pp.add_run(); rr.text=line; _set(rr,15,SUBTXT)
    rect(s,0,5.34,SW,0.29,FOOTBG); tf3=tb_(s,0.35,5.40,9,0.18)
    r3=tf3.paragraphs[0].add_run(); r3.text=T("Seminar Học sâu · 2026","Deep Learning Seminar · 2026"); _set(r3,9,FOOTTX)

    # ---- S2 ARCHITECTURE & METHOD (limitation ↔ our choice) ----
    s=prs.slides.add_slide(BLANK); bt=header(s,T("Kiến trúc & cách làm của nhóm","Our architecture & method"),
        T("Mỗi lựa chọn vá đúng MỘT hạn chế của MedRegA","Each choice fixes ONE MedRegA limitation"))
    table(s,[T("Hạn chế của MedRegA","MedRegA limitation"),T("Lựa chọn của nhóm (vì sao)","Our choice (why)")],
      [[T("Dồn lên **LLM 40B**; “mắt” & “cầu” bất động → định vị không sắc",
          "Load on the **40B LLM**; “eyes” & “bridge” frozen → localization not sharp"),
        T("**Gemma 4 E4B (~8B)** + **mở khoá vision** (pIoU 0.015→0.27)",
          "**Gemma 4 E4B (~8B)** + **unlock vision** (pIoU 0.015→0.27)")],
       [T("Chỉ **1 lát trung tâm**, **không ca âm**, box gộp thô",
          "Only **1 central slice**, **no negatives**, coarse box"),
        T("**Đa lát + ca âm + multi-box** (tách từng ổ); split theo bệnh nhân",
          "**Multi-slice + negatives + multi-box** (per-lesion); split by patient")],
       [T("Chi phí **16×H800** — ngoài tầm sinh viên",
          "Cost **16×H800** — out of reach for a student"),
        T("**LoRA + full-finetune vision**, chạy **1 GPU**",
          "**LoRA + full fine-tune vision**, runs on **1 GPU**")],
       [T("**Per-image** (pseudoreplication); không abstain / CI",
          "**Per-image** (pseudoreplication); no abstain / CI"),
        T("**Per-patient + CI**, tách detect/localize, **selective prediction**",
          "**Per-patient + CI**, detect/localize split, **selective prediction**")]],
      0.4,bt+0.1,9.2,colw=[4.4,4.8],fs=11.5,hfs=12,rh=0.62,first_bold=False)
    footer(s,2)

    # ---- S3 RESULTS VS BASELINE ----
    s=prs.slides.add_slide(BLANK); bt=header(s,T("Kết quả vs baseline (zero-shot → fine-tune)","Results vs baseline (zero-shot → fine-tuned)"))
    table(s,[T("Chỉ số","Metric"),T("Baseline","Baseline"),T("Của mình","Ours")],
      [[T("Detection F1 (bệnh nhân)","Detection F1 (patient)"),"0.33","0.89"],
       [T("Sensitivity (bắt u)","Sensitivity (catch tumor)"),"20%","80%"],
       [T("Localization pIoU","Localization pIoU"),"0.002","0.27"],
       ["recall@IoU 0.25","0%","54%"],
       [T("False-positive (lát âm)","False-positive (neg. slice)"),"2.2%","1.5%"]],
      0.4,bt+0.05,5.5,colw=[2.9,1.3,1.3],fs=11,hfs=11,rh=0.40)
    bullets(s,[(T("**Không quên:** vẫn hội thoại / JSON / thơ / toán (LoRA giữ trọng số gốc).",
                 "**No forgetting:** still chats / JSON / poem / math (LoRA keeps base weights)."),0)],0.4,bt+2.35,5.5,0.7,base=12)
    notebox(s,T("⚠ Lưu ý","⚠ Note"),T("n nhỏ (~25 bn dương, 2 âm) → CI rộng; đây là PoC, không tuyên bố lâm sàng.",
              "small n (~25 pos patients, 2 neg) → wide CI; this is a PoC, no clinical claim."),0.4,bt+3.0,5.5,0.7,kind="caveat")
    image(s,DET,6.1,bt+0.25,w=3.7,caption=T("Trước → sau fine-tune","Before → after fine-tune"))
    footer(s,3)

    # ---- S4 VS MEDREGA ----
    s=prs.slides.add_slide(BLANK); bt=header(s,T("Kết quả vs MedRegA","Results vs MedRegA"))
    table(s,[T("Khía cạnh","Aspect"),"MedRegA",T("Của mình","Ours")],
      [[T("Quy mô","Scale"),"~40B, 16×H800","~8B, 1 GPU"],
       [T("Vào 3D","Into 3D"),T("1 lát trung tâm","1 central slice"),T("đa lát + ca âm","multi-slice + negatives")],
       [T("Đơn vị đánh giá","Eval unit"),"per-image","per-patient + CI"],
       [T("Detect vs Localize","Detect vs Localize"),T("gộp","merged"),T("tách riêng","separated")],
       [T("Ca âm / Bất định","Negatives / Uncertainty"),T("không","none"),"FP + selective prediction"],
       ["Localization","IoU ~0.23","pIoU ~0.27"]],
      0.4,bt+0.05,6.0,colw=[2.0,2.0,2.0],fs=10,hfs=10.5,rh=0.36)
    notebox(s,T("Đọc đúng cách","Read it correctly"),
      T("KHÔNG so số trực tiếp (khác data/metric); pIoU có PHẠT nên khắt khe hơn. Đóng góp thật = khung đánh giá trung thực + độ tin cậy.",
        "NOT a direct number match (different data/metric); pIoU is PENALIZED, so stricter. Real contribution = honest evaluation + reliability layer."),
      6.55,bt+0.1,3.1,2.4,kind="info")
    footer(s,4)

    # ---- S5 CONCLUSION ----
    s=prs.slides.add_slide(BLANK); bt=header(s,T("Kết luận","Conclusion"))
    bullets(s,[
      (T("**Chứng minh cơ chế:** region-centric (khoanh-rồi-đọc) khả thi ở **~8B, 1 GPU**.",
         "**Proof of mechanism:** region-centric (localize-then-read) is feasible at **~8B, 1 GPU**."),0),
      (T("**Giá trị:** khung đánh giá trung thực + selective prediction — không phải điểm số.",
         "**Value:** honest evaluation + selective prediction — not the score."),0),
      (T("**Trung thực:** PoC trên 1 dataset / 1 task, n nhỏ, CI rộng.",
         "**Honest:** PoC on 1 dataset / 1 task, small n, wide CI."),0),
      (T("**Tương lai:** ảnh giàu hơn (multi-window, 2.5D) + external validation.",
         "**Future:** richer images (multi-window, 2.5D) + external validation."),0),
    ],0.4,bt+0.1,9.2,3.0,base=15,gap=13)
    notebox(s,T("Câu chốt","Closing"),
      T("Không hứa đã tới đích — chỉ ra con đường và nói rõ chỗ nào còn dốc.",
        "We don't claim to have arrived — we map the road and say where it's still steep."),0.4,bt+3.05,9.2,0.6,kind="info")
    footer(s,5)

    out=f"seminar/cai_tien/slides_5min_{'EN' if EN else 'VN'}.pptx"
    prs.save(out); print("SAVED",out,"| slides =",len(prs.slides._sldIdLst))

for lang in ("vn","en"): build(lang)
