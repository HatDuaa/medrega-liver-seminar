# -*- coding: utf-8 -*-
"""Hình cho phần paper Mục 4-5 (VN): box-as-text (Fig4), train 2 giai đoạn, Regional CoT (Fig5), biểu đồ kết quả general. cwd=repo root."""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch, Ellipse
from PIL import Image
import numpy as np

plt.rcParams["font.family"]="DejaVu Sans"
NAVY="#1A3A5C"; RED="#e23b3b"; GREEN="#22a565"; ORANGE="#e08a2b"; ICE="#4a86c5"
GREY="#8a8f96"; LGREY="#d6dbe1"; INK="#1c2736"; CARD="#e8f0f8"; PAPER="#f4f7fb"

# ============ FIG A: box-as-text (Fig 4 redraw) — SƠ ĐỒ MINH HOẠ (không dùng data nhóm) ============
def fig_box_as_text():
    fig,ax=plt.subplots(figsize=(9.2,3.6),dpi=150); ax.axis("off")
    ax.set_xlim(0,100); ax.set_ylim(0,100)
    # --- left: SCHEMATIC medical scan (generic, not patient data) ---
    fx0,fy0,fw,fh=3,12,29,74
    ax.add_patch(FancyBboxPatch((fx0,fy0),fw,fh,boxstyle="round,pad=0.4,rounding_size=2",
                                lw=1.3,edgecolor=NAVY,facecolor="#eef1f4"))
    cx0=fx0+fw/2; cy0=fy0+fh/2
    ax.add_patch(Ellipse((cx0,cy0),fw*0.72,fh*0.80,facecolor="#d3dae1",edgecolor="none"))
    ax.add_patch(Ellipse((cx0+3,cy0-3),fw*0.42,fh*0.34,facecolor="#c2ccd6",edgecolor="none"))
    # region box (đỏ) + nhãn — rbw nhỏ hơn để bù tỉ lệ trục (x nén ~2.5x so với y)
    rbx,rby,rbw,rbh=cx0+3,cy0-1,3.2,8.0
    ax.add_patch(Rectangle((rbx,rby),rbw,rbh,fill=False,edgecolor=RED,lw=2.2))
    ax.text(rbx+rbw/2,rby-2.3,"vùng quan tâm",ha="center",va="top",fontsize=7.2,color=RED)
    # ticks 0..1000
    ax.text(fx0-0.5,fy0+fh+1.5,"0",fontsize=8,color=NAVY,ha="left")
    ax.text(fx0+fw,fy0+fh+1.5,"1000",fontsize=8,color=NAVY,ha="right")
    ax.text(fx0-0.5,fy0-2.0,"1000",fontsize=8,color=NAVY,ha="left",va="top")
    ax.annotate("",xy=(fx0+fw,fy0+fh+0.5),xytext=(fx0,fy0+fh+0.5),arrowprops=dict(arrowstyle="->",color=NAVY,lw=0.8))
    ax.annotate("",xy=(fx0-1.0,fy0),xytext=(fx0-1.0,fy0+fh),arrowprops=dict(arrowstyle="->",color=NAVY,lw=0.8))
    ax.text(cx0,fy0+fh+5.5,"Ảnh y tế (minh hoạ) — X-quang / CT / MRI …",ha="center",fontsize=10,color=NAVY,fontweight="bold")
    # --- arrow ---
    ax.add_patch(FancyArrowPatch((34,50),(41,50),arrowstyle="-|>",mutation_scale=22,lw=2.4,color=NAVY))
    ax.text(37.5,58,"mã hoá\nthành chữ",ha="center",va="bottom",fontsize=9,color=NAVY)
    # --- right: text bubble ---
    box=FancyBboxPatch((42,26),56,46,boxstyle="round,pad=1.2,rounding_size=3",
                       linewidth=1.4,edgecolor=NAVY,facecolor=PAPER); ax.add_patch(box)
    ax.text(45,64,"Chuỗi văn bản model sinh ra:",fontsize=9.5,color=GREY,style="italic")
    # tokenized lines — DejaVu Sans (đủ tiếng Việt), đo bề rộng thật để không đè
    X0=45; rend=fig.canvas.get_renderer()
    inv=ax.transData.inverted()
    def runline(y,segs):
        x=X0
        for t,c,b_ in segs:
            tx=ax.text(x,y,t,fontsize=10.5,color=c,fontweight=("bold" if b_ else "normal"),family="DejaVu Sans",va="center")
            bb=tx.get_window_extent(renderer=rend)
            (x0d,_),(x1d,_)=inv.transform((bb.x0,bb.y0)),inv.transform((bb.x1,bb.y0))
            x+=(x1d-x0d)
    runline(51,[("… phát hiện ",INK,False),("<ref>",ORANGE,True),("khối u",INK,True),("</ref>",ORANGE,True)])
    runline(41,[("<box>",GREEN,True),("[420,300,560,470]",RED,True),("</box>",GREEN,True)])
    ax.text(45,31,"<ref> = tên đối tượng    ·    <box> = toạ độ hộp (0–1000)",fontsize=8.6,color=GREY)
    plt.savefig("seminar/code/paper_box_as_text_vn.png",bbox_inches="tight",facecolor="white"); plt.close()
    print("saved paper_box_as_text_vn.png")

# ============ FIG B: 2-stage training ============
def _modbox(ax,x,y,w,h,label,state,tags=("❄ đóng băng","● huấn luyện"),fs=8.6):
    # state: 'freeze' or 'train'
    fc=CARD if state=="freeze" else "#fbe6cb"
    ec=ICE if state=="freeze" else ORANGE
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.3,rounding_size=2",lw=1.5,edgecolor=ec,facecolor=fc))
    ax.text(x+w/2,y+h*0.62,label,ha="center",va="center",fontsize=fs,color=INK,fontweight="bold")
    tag=tags[0] if state=="freeze" else tags[1]
    ax.text(x+w/2,y+h*0.26,tag,ha="center",va="center",fontsize=fs-1.2,color=ec,fontweight="bold")

def _arrow(ax,x0,y0,x1,y1):
    ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle="-|>",mutation_scale=13,lw=1.6,color=NAVY))

def fig_train_stages(lang="vn"):
    EN=(lang=="en")
    tags=("❄ frozen","● trained") if EN else ("❄ đóng băng","● huấn luyện")
    box_labels=["Vision","Connector","LLM"] if EN else ["Vision","Cầu nối","LLM"]
    t1="Stage 1 — Alignment training" if EN else "Giai đoạn 1 — Alignment"
    t2="Stage 2 — Instruction tuning" if EN else "Giai đoạn 2 — Instruction tuning"
    fig,ax=plt.subplots(figsize=(9.6,1.95),dpi=150); ax.axis("off")
    ax.set_xlim(0,100); ax.set_ylim(0,100)
    bw,bh=13,44; ah=bh/2
    def panel(x0,title,states):
        ax.text(x0+22,90,title,ha="center",fontsize=10.5,color=NAVY,fontweight="bold")
        xs=[x0,x0+15.5,x0+31]; y=20
        for xi,lb,st in zip(xs,box_labels,states): _modbox(ax,xi,y,bw,bh,lb,st,tags=tags,fs=9.0)
        _arrow(ax,xs[0]+bw,y+ah,xs[1],y+ah); _arrow(ax,xs[1]+bw,y+ah,xs[2],y+ah)
    panel(3,t1,["freeze","train","freeze"])
    ax.plot([50,10],[0,0],color="white",lw=0.1)  # giữ lề dưới
    ax.plot([50,50],[8,84],color=LGREY,lw=1.0)
    panel(53,t2,["freeze","freeze","train"])
    out=f"seminar/code/paper_train_stages_{'en' if EN else 'vn'}.png"
    plt.savefig(out,bbox_inches="tight",facecolor="white"); plt.close(); print("saved",out)

# ============ FIG C: Regional CoT (Fig 5 redraw) ============
def _flowbox(ax,x,y,w,h,label,fc,ec,tc=INK,fs=8.6):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.3,rounding_size=2",lw=1.5,edgecolor=ec,facecolor=fc))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=fs,color=tc,fontweight="bold")

def fig_regional_cot():
    fig,ax=plt.subplots(figsize=(5.0,4.2),dpi=150); ax.axis("off")
    ax.set_xlim(0,100); ax.set_ylim(0,100)
    # top flow (usual, grey)
    ax.text(3,93,"Cách thường",fontsize=9.5,color=GREY,fontweight="bold")
    yt=76; h=13
    _flowbox(ax,3,yt,26,h,"Ảnh +\nCâu hỏi","#eef0f2",GREY,GREY)
    _flowbox(ax,42,yt,20,h,"LLM","#eef0f2",GREY,GREY)
    _flowbox(ax,74,yt,23,h,"Trả lời","#eef0f2",GREY,GREY)
    _arrow(ax,29,yt+h/2,42,yt+h/2); _arrow(ax,62,yt+h/2,74,yt+h/2)
    ax.text(50,71,"trả lời ngay — dễ bỏ sót chi tiết bên trong ảnh",ha="center",fontsize=7.8,color=GREY,style="italic")
    ax.plot([2,98],[64,64],color=LGREY,lw=1.0)
    # bottom flow (Regional CoT, navy)
    ax.text(3,58,"Regional CoT",fontsize=9.8,color=NAVY,fontweight="bold")
    yb=30; h2=13
    _flowbox(ax,2,yb,20,h2,"Ảnh +\nCâu hỏi",CARD,NAVY,INK,8.0)
    _flowbox(ax,27,yb,22,h2,"① Detect\nvùng",CARD,NAVY,NAVY,8.0)
    _flowbox(ax,54,yb,22,h2,"② Prompt\nkèm  box","#fbe6cb",ORANGE,INK,8.0)
    _flowbox(ax,80,yb,18,h2,"LLM →\nTrả lời",CARD,NAVY,INK,8.0)
    _arrow(ax,22,yb+h2/2,27,yb+h2/2); _arrow(ax,49,yb+h2/2,54,yb+h2/2); _arrow(ax,76,yb+h2/2,80,yb+h2/2)
    # loop arrow from detect back into prompt (feedback)
    ax.text(50,20,"tự khoanh vùng quan trọng TRƯỚC, rồi mới trả lời",ha="center",fontsize=8,color=NAVY,style="italic")
    ax.text(50,11,"→ ép model chú ý cấu trúc bên trong · tái dùng kỹ năng detect đã học",ha="center",fontsize=7.6,color=GREY,style="italic")
    plt.savefig("seminar/code/paper_regional_cot_vn.png",bbox_inches="tight",facecolor="white"); plt.close()
    print("saved paper_regional_cot_vn.png")

# ============ FIG D: general results bar chart ============
def fig_general_bar(lang="vn"):
    EN=(lang=="en")
    tasks=(["VQA\nEN","VQA\nZH","Report\nEN","Report\nZH"] if EN
           else ["VQA\nAnh","VQA\nTrung","Report\nAnh","Report\nTrung"])
    lgd=(["MedRegA","MedDr (strong baseline)","InternVL (base)"] if EN
         else ["MedRegA","MedDr (baseline mạnh)","InternVL (nền)"])
    title=("General tasks — BLEU-1 (higher = better)" if EN
           else "Tác vụ tổng quát — BLEU-1 (cao = tốt)")
    medrega=[67.65,60.89,40.46,40.76]
    meddr  =[65.72,37.76,34.49,11.99]
    internvl=[63.51,39.73,13.12,10.71]
    x=np.arange(len(tasks)); w=0.26
    fig,ax=plt.subplots(figsize=(6.6,3.5),dpi=150)
    b1=ax.bar(x-w,medrega,w,label=lgd[0],color=NAVY)
    ax.bar(x,meddr,w,label=lgd[1],color="#7aa3c7")
    ax.bar(x+w,internvl,w,label=lgd[2],color=LGREY)
    ax.set_xticks(x); ax.set_xticklabels(tasks,fontsize=9.5,color=INK)
    ax.set_ylabel("BLEU-1",fontsize=10,color=INK); ax.set_ylim(0,80)
    for b in b1:
        ax.text(b.get_x()+b.get_width()/2,b.get_height()+1.2,f"{b.get_height():.0f}",ha="center",fontsize=8,color=NAVY,fontweight="bold")
    ax.legend(fontsize=8.5,loc="upper right",framealpha=0.95)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.tick_params(axis="y",labelsize=8,colors=GREY)
    ax.set_title(title,fontsize=10.5,color=NAVY,fontweight="bold",pad=8)
    plt.tight_layout()
    out=f"seminar/code/paper_general_bar_{'en' if EN else 'vn'}.png"
    plt.savefig(out,bbox_inches="tight",facecolor="white"); plt.close(); print("saved",out)

for _lg in ("vn","en"):
    fig_train_stages(_lg); fig_general_bar(_lg)
print("ALL FIGS DONE")
