# -*- coding: utf-8 -*-
"""
Created on Thu Jul 21 14:49:30 2016

@author: raul
"""

import vitas
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import statsmodels.api as sm

from matplotlib import rcParams
rcParams['xtick.labelsize'] = 15
rcParams['ytick.labelsize'] = 15
rcParams['legend.fontsize'] = 15
rcParams['axes.labelsize'] = 15
rcParams['legend.handletextpad'] = 0.2
rcParams['mathtext.default'] = 'sf'

#sns.reset_defaults()
#sns.reset_orig()
sns.set_style("whitegrid")

targets = list()
targets.append(['c03/leg01.cdf','3','010123I.nc'])
targets.append(['c03/leg02.cdf','7','010123I.nc'])
targets.append(['c03/leg03.cdf','6','010123I.nc'])
targets.append(['c03/leg04.cdf','6','010123I.nc'])
targets.append(['c03/leg05.cdf','3','010123I.nc'])
targets.append(['c03/leg08.cdf','6','010123I.nc'])
targets.append(['c03/leg09.cdf','8','010123I.nc'])
targets.append(['c03/leg12.cdf','3','010123I.nc'])
targets.append(['c03/leg13.cdf','6','010123I.nc'])
targets.append(['c03/leg14.cdf','6','010123I.nc'])
#targets.append(['c03/leg15.cdf','3','010123I.nc']) # error, not sure why
targets.append(['c03/leg16.cdf','3','010123I.nc'])
targets.append(['c03/leg20.cdf','15','010123I.nc'])
#
targets.append(['c07/leg01.cdf','0','010217I.nc'])
targets.append(['c07/leg03.cdf','6','010217I.nc'])
targets.append(['c07/leg04.cdf','0','010217I.nc'])
targets.append(['c07/leg05.cdf','4','010217I.nc'])
targets.append(['c07/leg06.cdf','0','010217I.nc'])


fl_u = np.array([])
fl_v = np.array([])
sy_u = np.array([])
sy_v = np.array([])

template = '-c {0} -s {2} --valid {1} --no_plot'
for t in targets:
    out = vitas.main(template.format(t[0],t[1],t[2]))   
    fl_u = np.append(fl_u, out['fl']['u'])
    fl_v = np.append(fl_v, out['fl']['v'])
    sy_u = np.append(sy_u, out['sy']['u'])
    sy_v = np.append(sy_v, out['sy']['v'])

good_u=[np.where(~np.isnan(sy_u))]
good_v=[np.where(~np.isnan(sy_v))]

Xu,Yu = np.squeeze(fl_u[good_u]),np.squeeze(sy_u[good_u])
Xv,Yv = np.squeeze(fl_v[good_v]),np.squeeze(sy_v[good_v])
x0u,y0u = np.arange(-20,21), np.arange(-20,21)
x0v,y0v = np.arange(0,31), np.arange(0,31)
add_const=True
if add_const is True:
    Xu = sm.add_constant(Xu)
    model = sm.OLS(Yu,Xu)
    result_u = model.fit()  
    
    Xv = sm.add_constant(Xv)
    model = sm.OLS(Yv,Xv)
    result_v = model.fit()
    
    inter_u, slope_u = result_u.params
    inter_v, slope_v = result_v.params
    
    template = 'Slope: {:2.2f}\nIntercep: {:2.2f}\nR-sqr: {:2.2f}\
                \nN: {:2.0f}'
    stats_u=template.format(slope_u, inter_u,
                            result_u.rsquared,result_u.nobs)
    stats_v=template.format(slope_v, inter_v,
                            result_v.rsquared,result_v.nobs)
    y1u = inter_u + x0u*slope_u
    y1v = inter_v + x0v*slope_v
else:
    model = sm.OLS(Yu,Xu)
    result_u = model.fit()
    
    model = sm.OLS(Yv,Xv)
    result_v = model.fit()
    
    slope_u = result_u.params
    slope_v = result_v.params 
    
    template = 'Slope: {:2.2f}\nR-sqr: {:2.2f}\nN: {:2.0f}'
    stats_u=template.format(slope_u[0], result_u.rsquared,
                            result_u.nobs)
    stats_v=template.format(slope_v[0], result_v.rsquared,
                            result_v.nobs)
    y1u = x0u*slope_u
    y1v = x0v*slope_v

scale=0.9
fig, ax = plt.subplots(1,2,figsize=(9*scale,4*scale))

ax[0].scatter(fl_u,sy_u)
ax[0].plot(x0u,y0u,'--',color='k')
ax[0].plot(x0u,y1u,'-',color='r',lw=2)
ax[0].text(0.05,0.7,stats_u,transform=ax[0].transAxes)
ax[0].set_xlim([x0u.min(),x0u.max()])
ax[0].set_ylim([y0u.min(),y0u.max()])
ax[0].set_xlabel('Flight U-comp')
ax[0].set_ylabel('Synth U-comp')

ax[1].scatter(fl_v,sy_v)
ax[1].plot(x0v,y0v,'--',color='k')
ax[1].plot(x0v,y1v,'-',color='r',lw=2)
ax[1].text(0.05,0.7,stats_v,transform=ax[1].transAxes)
ax[1].set_xlim([x0v.min(),x0v.max()])
ax[1].set_ylim([y0v.min(),y0v.max()])
ax[1].set_xlabel('Flight V-comp')
ax[1].set_ylabel('synth V-comp')

plt.subplots_adjust(wspace=0.25)
plt.show()



