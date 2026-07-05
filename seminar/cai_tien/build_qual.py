# -*- coding: utf-8 -*-
"""Hình định tính before/after fine-tune (VN + EN). cwd=repo root."""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import numpy as np

plt.rcParams["font.family"]="DejaVu Sans"
NAVY="#1f3a5f"; GREEN="#2ecc71"; YELLOW="#f1c40f"; RED="#e74c3c"
IMG="seminar/code/data/data_liver_multi_v3/images/liver_014_pos_z355.png"
im=np.array(Image.open(IMG).convert("L")); H,W=im.shape
def sc(b): return [b[0]/1000*W, b[1]/1000*H, b[2]/1000*W, b[3]/1000*H]
GT=sc([632,449,667,492]); PRED=sc([631,451,669,491])

TXT={
 "vn":dict(t0="Zero-shot (chưa fine-tune)",t1="Sau fine-tune",
           c0="Model trả lời: “No liver tumor is found”\n→ không khoanh gì",
           c1="Khoanh trúng khối u (IoU 0.86)",lp="Box dự đoán",lg="Box thật (GT)"),
 "en":dict(t0="Zero-shot (untrained)",t1="After fine-tune",
           c0="Model says: “No liver tumor is found”\n→ draws nothing",
           c1="Correctly localizes the tumor (IoU 0.86)",lp="Predicted box",lg="Ground truth"),
}
for lang,L in TXT.items():
    fig,ax=plt.subplots(1,2,figsize=(8.2,4.4),dpi=150)
    for a in ax: a.imshow(im,cmap="gray"); a.set_xticks([]); a.set_yticks([])
    ax[0].set_title(L["t0"],fontsize=12,fontweight="bold",color=NAVY,pad=8)
    ax[0].text(0.5,-0.10,L["c0"],transform=ax[0].transAxes,ha="center",va="top",fontsize=10,color=RED,style="italic")
    ax[1].set_title(L["t1"],fontsize=12,fontweight="bold",color=NAVY,pad=8)
    gx,gy,gx2,gy2=GT; px,py,px2,py2=PRED
    ax[1].add_patch(Rectangle((gx,gy),gx2-gx,gy2-gy,fill=False,edgecolor=YELLOW,lw=1.6,ls="--"))
    ax[1].add_patch(Rectangle((px,py),px2-px,py2-py,fill=False,edgecolor=GREEN,lw=2.0))
    ax[1].text(0.5,-0.10,L["c1"],transform=ax[1].transAxes,ha="center",va="top",fontsize=10,color=NAVY,fontweight="bold")
    ax[1].plot([],[],color=GREEN,lw=2,label=L["lp"]); ax[1].plot([],[],color=YELLOW,lw=1.6,ls="--",label=L["lg"])
    ax[1].legend(loc="upper right",fontsize=7.5,framealpha=0.85)
    plt.tight_layout(rect=[0,0.04,1,1])
    out=f"seminar/code/before_after_qual_{lang}.png"
    plt.savefig(out,bbox_inches="tight",facecolor="white"); plt.close(); print("saved",out)
