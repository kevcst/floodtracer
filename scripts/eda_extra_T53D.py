"""Análisis exploratorio extra (hecho en Cowork 2026-11-14) sobre data_nisar/T53D_F105.
Partes: (a) percentiles y Otsu por fecha, (b) mapas de agua y frecuencia, (c) dispersores persistentes / doble rebote.
Uso: python scripts/eda_extra_T53D.py  (requiere rasterio, scikit-image, scipy, matplotlib). Guarda en /tmp/eda.
"""
import os; os.makedirs('/tmp/eda', exist_ok=True)

# ---- (a)
import rasterio,numpy as np,glob,os
from skimage.filters import threshold_otsu
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data_nisar','T53D_F105')
dates=sorted({os.path.basename(p)[:10] for p in glob.glob(D+'/*_HH.tif')})
def rd(d,p):
    a=rasterio.open(f'{D}/{d}_{p}.tif').read(1).astype('float32'); a[(a<=0)|~np.isfinite(a)]=np.nan; return 10*np.log10(a)
HH=np.stack([rd(d,'HH') for d in dates]); HV=np.stack([rd(d,'HV') for d in dates])
np.save('/tmp/eda/HH.npy',HH); np.save('/tmp/eda/HV.npy',HV)
valid=np.all(np.isfinite(HH),0)
print('valid frac',valid.mean())
perm=np.all(HH<-18,0)&valid
print('always dark % ',100*perm.sum()/valid.sum())
for i,d in enumerate(dates):
    h=HH[i][valid]; v=HV[i][valid]
    t=threshold_otsu(h[(h>-35)&(h<5)])
    print(d,'pct HH p5/50/95 %.1f %.1f %.1f'%tuple(np.percentile(h,[5,50,95])),'| otsu %.1f'%t,'| water(otsu) %.1f%%'%(100*np.mean(h<t)),
          '| permwater HH med %.1f'%np.median(HH[i][perm]) if perm.any() else '', '| HV p50 %.1f'%np.median(v))

# ---- (b)
import numpy as np,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from scipy import ndimage as ndi
HH=np.load('/tmp/eda/HH.npy');HV=np.load('/tmp/eda/HV.npy')
dates=['06-17','06-29','07-11','07-23','08-16','08-28','09-09','09-21','10-03','10-15','10-27']
valid=np.all(np.isfinite(HH),0)
# speckle: 3x3 mean in linear
def sm(a): 
    l=10**(a/10); l=np.where(np.isfinite(l),l,np.nan); m=ndi.uniform_filter(np.nan_to_num(l),5); return 10*np.log10(np.maximum(m,1e-6))
HHs=np.stack([sm(h) for h in HH])
T=-18
W=(HHs<T)&valid
freq=W.mean(0)
base=W[:4].mean(0)  # jun-jul
aug=W[4:6].any(0)&(base==0)
late=W[10]&(W[:9].sum(0)==0)
print('perm (all dates)%%: %.2f'%(100*(W.all(0)).sum()/valid.sum()))
print('aug-only new water %%: %.2f'%(100*aug.sum()/valid.sum()))
print('aug water that returned by 09-21 %%: %.2f'%(100*(aug&~W[7]).sum()/max(aug.sum(),1)))
print('new water 10-27 only %%: %.2f'%(100*late.sum()/valid.sum()))
print('new water 10-15 or 10-27 not before %%: %.2f'%(100*((W[9]|W[10])&(W[:9].sum(0)==0)).sum()/valid.sum()))
# connected components of late
lab,n=ndi.label(late); sizes=ndi.sum(late,lab,range(1,n+1)); print('late comps',n,'>=50px(2ha):',(sizes>=50).sum(),'largest',np.sort(sizes)[-5:]*0.04,'ha')
lab,n=ndi.label(aug); sizes=ndi.sum(aug,lab,range(1,n+1)); print('aug comps >=50px',(sizes>=50).sum(),'largest ha',np.sort(sizes)[-5:]*0.04)
np.save('/tmp/eda/HHs.npy',HHs)
f,ax=plt.subplots(2,3,figsize=(15,14))
for a,(i,t) in zip(ax[0],[(0,'HH 2026-06-17'),(5,'HH 2026-08-28'),(10,'HH 2026-10-27 (VALIDATED)')]):
    a.imshow(HHs[i],vmin=-22,vmax=-2,cmap='gray');a.set_title(t)
ax[1,0].imshow(freq,cmap='Blues',vmin=0,vmax=1);ax[1,0].set_title('Frecuencia de agua (HH<-18dB)')
rgb=np.dstack([np.clip((HHs[0]+22)/20,0,1),np.clip((HHs[5]+22)/20,0,1),np.clip((HHs[10]+22)/20,0,1)])
ax[1,1].imshow(rgb);ax[1,1].set_title('RGB = HH jun-17 / ago-28 / oct-27')
c=np.zeros(valid.shape+(3,));c[valid]=0.85;c[W.all(0)]=[0,0,.6];c[aug]=[0,.7,1];c[late]=[1,.3,0]
ax[1,2].imshow(c);ax[1,2].set_title('azul osc=agua perm, celeste=agua ago, naranja=agua nueva oct-27')
for a in ax.flat:a.axis('off')
plt.tight_layout();plt.savefig('/tmp/eda/maps.png',dpi=70)

# ---- (c)
import numpy as np
HHs=np.load('/tmp/eda/HHs.npy');HV=np.load('/tmp/eda/HV.npy');HH=np.load('/tmp/eda/HH.npy')
from scipy import ndimage as ndi
valid=np.all(np.isfinite(HH),0)
d=['06-17','06-29','07-11','07-23','08-16','08-28','09-09','09-21','10-03','10-15','10-27']
# persistent bright scatterers: top 0.2% in every date up to 10-15
thr=[np.nanpercentile(HH[i][valid],99.8) for i in range(10)]
ps=valid.copy()
for i in range(10): ps&=HH[i]>thr[i]-3
print('PS pixels',ps.sum())
print('PS median HH per date',[round(float(np.median(HH[i][ps])),1) for i in range(11)])
# double bounce: HH-HV large & HH high
HVs=np.stack([10*np.log10(np.maximum(ndi.uniform_filter(np.nan_to_num(10**(h/10)),5),1e-6)) for h in HV])
db=(HHs.mean(0)>-6)&((HHs-HVs).mean(0)>9)&valid&~ps
print('double-bounce candidate %%: %.2f'%(100*db.sum()/valid.sum()))
print('DB median HH',[round(float(np.median(HHs[i][db])),1) for i in range(11)])
print('DB median HH-HV',[round(float(np.median((HHs-HVs)[i][db])),1) for i in range(11)])
# general land (not water ever, not db)
land=valid&~db&~ps&((HHs<-18).sum(0)==0)
print('land median HH',[round(float(np.median(HHs[i][land])),1) for i in range(11)])
print('land median HV',[round(float(np.median(HVs[i][land])),1) for i in range(11)])
