# -*- coding: utf-8 -*-
"""Hình định tính before/after (VN+EN): box ĐỎ + zoom vùng u cho dễ nhìn. cwd=repo root."""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import numpy as np

plt.rcParams["font.family"]="DejaVu Sans"
NAVY="#1f3a5f"; RED="#ff3b30"; YELLOW="#ffd60a"; GREYT="#555"
IMG="seminar/code/data/data_liver_multi_v3/images/liver_014_pos_z355.png"
im=np.array(Image.open(IMG).convert("L")); H,W=im.shape
def sc(b): return [b[0]/1000*W, b[1]/1000*H, b[2]/1000*W, b[3]/1000*H]
GT=sc([632,449,667,492]); PRED=sc([631,451,669,491])
cx=(PRED[0]+PRED[2])/2; cy=(PRED[1]+PRED[3])/2; half=55
x0,y0=int(cx-half),int(cy-half); x1c,y1c=int(cx+half),int(cy+half)
crop=im[y0:y1c, x0:x1c]

TXT={
 "vn":dict(t0="Zero-shot (chưa fine-tune)",t1="Sau fine-tune",
           c0="Model trả lời: “No liver tumor is found”\n→ không khoanh gì",
           c1="Khoanh trúng khối u (IoU 0.86)",lp="Box dự đoán",lg="Box thật (GT)",zoom="phóng to"),
 "en":dict(t0="Zero-shot (untrained)",t1="After fine-tune",
           c0="Model says: “No liver tumor is found”\n→ draws nothing",
           c1="Correctly localizes the tumor (IoU 0.86)",lp="Predicted box",lg="Ground truth",zoom="zoom"),
}
def inset(ax,boxes):
    ia=ax.inset_axes([0.015,0.60,0.36,0.36]); ia.imshow(crop,cmap="gray"); ia.set_xticks([]); ia.set_yticks([])
    for c,ls,lw,bb in boxes:
        ia.add_patch(Rectangle((bb[0]-x0,bb[1]-y0),bb[2]-bb[0],bb[3]-bb[1],fill=False,edgecolor=c,lw=lw,ls=ls))
    for sp in ia.spines.values(): sp.set_edgecolor("white"); sp.set_linewidth(1.3)
    ia.set_title("",fontsize=6)
    return ia

for lang,L in TXT.items():
    fig,ax=plt.subplots(1,2,figsize=(8.2,4.5),dpi=150)
    for a in ax: a.imshow(im,cmap="gray"); a.set_xticks([]); a.set_yticks([])
    # Panel A — zero-shot: không box, chỉ zoom vùng u (không box) + nhãn vùng
    ax[0].set_title(L["t0"],fontsize=12,fontweight="bold",color=NAVY,pad=8)
    inset(ax[0],[])  # zoom, không box
    ax[0].text(0.19,0.585,"("+L["zoom"]+")",transform=ax[0].transAxes,ha="center",fontsize=7,color="white")
    ax[0].text(0.5,-0.11,L["c0"],transform=ax[0].transAxes,ha="center",va="top",fontsize=10,color=RED,style="italic")
    # Panel B — sau fine-tune: box đỏ (pred) + vàng đứt (GT)
    ax[1].set_title(L["t1"],fontsize=12,fontweight="bold",color=NAVY,pad=8)
    ax[1].add_patch(Rectangle((GT[0],GT[1]),GT[2]-GT[0],GT[3]-GT[1],fill=False,edgecolor=YELLOW,lw=1.4,ls="--"))
    ax[1].add_patch(Rectangle((PRED[0],PRED[1]),PRED[2]-PRED[0],PRED[3]-PRED[1],fill=False,edgecolor=RED,lw=2.2))
    inset(ax[1],[(YELLOW,"--",1.2,GT),(RED,"-",2.0,PRED)])
    ax[1].text(0.19,0.585,"("+L["zoom"]+")",transform=ax[1].transAxes,ha="center",fontsize=7,color="white")
    ax[1].text(0.5,-0.11,L["c1"],transform=ax[1].transAxes,ha="center",va="top",fontsize=10,color=NAVY,fontweight="bold")
    ax[1].plot([],[],color=RED,lw=2,label=L["lp"]); ax[1].plot([],[],color=YELLOW,lw=1.4,ls="--",label=L["lg"])
    ax[1].legend(loc="upper right",fontsize=7.5,framealpha=0.9)
    plt.tight_layout(rect=[0,0.05,1,1])
    out=f"seminar/code/before_after_qual_{lang}.png"
    plt.savefig(out,bbox_inches="tight",facecolor="white"); plt.close(); print("saved",out)
