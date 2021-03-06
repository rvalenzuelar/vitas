
'''
***************************************
    Class for plotting flight level
    data

    Raul Valenzuela
    August, 2015
*************************************** 
'''

import Terrain

import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.pyplot as plt
import Common as cm 
import pandas as pd
import numpy as np
import seaborn as sns 

from itertools import product
from scipy.spatial import cKDTree
import statsmodels.api as sm
from scipy.interpolate import UnivariateSpline

''' set color codes in seaborn '''
sns.set_color_codes()

class FlightPlot(object):

    def __init__(self,**kwargs):

        self.met=None
        self.flightPath=None
        self.name=None
        self.time=None

        for key,value in kwargs.iteritems():
            if key == 'meteo':
                self.met=value
            elif key == 'flightPath':
                self.flightPath=value
            elif key == 'name':
                self.name=value
            elif key == 'time':
                self.time=value

    def plot_meteo(self,xaxis,dots):

        topo=Terrain.get_topo(lats=self.met['lats'], lons=self.met['lons'])

        varname={    0:{'var':'atemp','name': 'air temperature',
                            'loc':3,'ylim':None,'fmt':False},
                    1:{'var':'dewp','name': 'dew point temp',
                            'loc':3,'ylim':None,'fmt':False},
                    2:{'var':'wdir','name':'wind direction',
                            'loc':(0.05,0.9),'ylim':None,'fmt':True},                            
                    3:{'var':'apres','name': 'air pressure',
                            'loc':(0.05,0.9),'ylim':None,'fmt':False},                        
                    4:{'var':'relh','name':'relative humidity',
                            'loc':(0.05,0.05),'ylim':[80,101],'fmt':True},                            
                    5:{'var':'wspd','name': 'wind speed',
                            'loc':(0.05,0.9),'ylim':None,'fmt':True},
                    6:{'var':'galt','name': 'geopotential alt',
                            'loc':(0.05,0.9),'ylim':None,'fmt':True},
                    7:{'var':'jwlwc','name':'liquid water content',
                            'loc':(0.05,0.9),'ylim':None,'fmt':False},
                    8:{'var':'wvert','name':'vertical velocity',
                            'loc':(0.05,0.9),'ylim':[-2,4],'fmt':True},
                    9:{'var':'palt','name': 'pressure alt',
                            'loc':(0.05,0.9),'ylim':None,'fmt':True}}


        fig, ax = plt.subplots(3,3, sharex=True,figsize=(15,10))
        axs=ax.ravel()
        for i in varname.items():
            item = i[0]            
            var = i[1]['var']
            name = i[1]['name']
            loc = i[1]['loc']
            ylim = i[1]['ylim']
            ax = axs[item-1]
            if item < 2: # air temp and dew point in the same plot
                axs[0].plot(xaxis,self.met[var],label=name)
                if ylim: axs[0].set_ylim(ylim)
                if item == 1:
                    axs[0].grid(True)
                    axs[0].legend(loc=loc,frameon=False)
            else:
                ax.plot(xaxis,self.met[var],label=name)
                if item == 6: 
                    ax2 = ax.twinx()
                    ax2.plot(xaxis,topo,'r')
                    ax2.set_ylabel('topography [m]', color='r')
                    for tl in ax2.get_yticklabels():
                        tl.set_color('r')
                    ax2.grid(False)
                if ylim: ax.set_ylim(ylim)
                ax.grid(True)
                ax.annotate(name, fontsize=16,
                                    xy=loc, 
                                    xycoords='axes fraction')
                if item == 8:
                    ax.set_xlabel('Distance from beginning of flight [km]')

        new_xticks=[xaxis[i] for i in dots]
        adjust_xaxis(axs,new_xticks)
        adjust_yaxis(axs) # --> it's affecting formatter
        l1='Flight level meteorology for '+self.name
        l2='\nStart time: '+self.time[0].strftime('%Y-%m-%d %H:%M')+' UTC'
        l3='\nEnd time: '+self.time[1].strftime('%Y-%m-%d %H:%M')+' UTC'
        fig.suptitle(l1+l2+l3,y=0.98)
        fig.subplots_adjust(bottom=0.08,top=0.9,
                            hspace=0,wspace=0.2)
        plt.draw


    def compare_with_synth(self,**kwargs):

        """ Method description
            ----------------------------
            Comparison between the synthesis field and flight level
            data is achieved by:

            1) Find all the indexes of the synth grid where the flight trajectory intersects
            2) Filter out repeated indexes of the trajectory (LINE)
            3) Save geographic coordinates of the LINE
            4) In the synth grid, search the 9 nearest neighbors along each point of LINE
            5) Fill missing synth values by averaging the neighbors
            6) In the flight data, search 15 values nearest to each point of LINE 
            7) Average each set of 15 values of the flight array
        """

        synth=kwargs['array']
        synth_lons=kwargs['x']
        synth_lats=kwargs['y']
        synth_z=kwargs['z']
        zlevel=kwargs['level']
        flightmet = kwargs['met'] # flight level meteo field used for comparison
        noplot = kwargs['noplot']
        
        idx = np.where(synth_z==zlevel)
        data = np.squeeze(synth[:,:,idx])

        flgt_lats,flgt_lons=zip(*self.flightPath)
        flight_altitude=self.met['palt']
        
        if flightmet in ['u','v']:
            wspd=self.met['wspd']
            wdir=self.met['wdir']
            u = -wspd*np.sin(wdir*np.pi/180.)
            v = -wspd*np.cos(wdir*np.pi/180.)
            if flightmet == 'u':
                flight_wspd = u
            else:
                flight_wspd = v
        else:
            flight_wspd=self.met[flightmet]
            

        flgt_lats = np.asarray(cm.around(flgt_lats,4))
        flgt_lons = np.asarray(cm.around(flgt_lons,4))
        synth_lats = np.asarray(cm.around(synth_lats,4))
        synth_lons = np.asarray(cm.around(synth_lons,4))

        idx_lat=[]
        idx_lon=[]
        for lat,lon in zip(flgt_lats,flgt_lons):
            idx_lat.append(cm.find_index_recursively(array=synth_lats,value=lat,decimals=4))
            idx_lon.append(cm.find_index_recursively(array=synth_lons,value=lon,decimals=4))

        """ filter out repeated indexes """
        indexes_filtered=[]
        first=True
        for val in zip(idx_lon,idx_lat):
            if first:
                val_foo=val
                indexes_filtered.append(val)
                first=False
            elif val!=val_foo:
                indexes_filtered.append(val)
                val_foo=val

        """ save geographic coordinates of the line """
        line_lat=[]
        line_lon=[]        
        for lon,lat in indexes_filtered:
            line_lon.append(synth_lons[lon])
            line_lat.append(synth_lats[lat])            
        linesynth=zip(line_lon,line_lat)

        """ search nearest neighbors """
        synth_coord=list(product(synth_lons,synth_lats))
        tree = cKDTree(synth_coord)
        neigh = 9
        dist, idx = tree.query(linesynth, k=neigh, eps=0, p=2, distance_upper_bound=0.1)

        """ convert to one-column array """
        grid_shape=data.shape
        data = data.reshape(grid_shape[0]*grid_shape[1],1)

        """ gets the center point """
        idx_split=zip(*idx)
        idx0 = list(idx_split[0])

        """ extract center point value """
        data_extract=data[idx0]

        """ average neighbors """
        data_extract2=[]
        for i in idx:
            data_extract2.append(np.nanmean(data[i]))

        """ save center points of line """
        line_center=[]
        line_neighbors=[]
        for i in idx:
            value=np.unravel_index(i[0], grid_shape)
            line_center.append(value)
            for j in i[1:]:
                value=np.unravel_index(j, grid_shape)
                line_neighbors.append(value)

        """ convert back to 2D array """
        data=data.reshape(121,131)
    

        """ swap coordinates to (lon,lat)"""
        flight_coord = [(t[1], t[0]) for t in self.flightPath]
        tree = cKDTree(flight_coord)
        neigh = 15
        dist, idx = tree.query(linesynth, k=neigh, eps=0, p=2, distance_upper_bound=0.1)

        """ average flight data """
        flgt_mean=[]
        flgt_altitude=[]
        for i in idx:
            flgt_mean.append(np.nanmean(flight_wspd[i]))
            flgt_altitude.append(np.nanmean(flight_altitude[i]))


        """ make plots """

        jet = plt.get_cmap('jet')
        cNorm = colors.Normalize(vmin=np.amin(data), vmax=np.amax(data))
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=jet)
        synth_alt=str(int(zlevel[0]*1000))
        flgt_alt=str(int(np.average(flgt_altitude)))

        if flightmet == 'wspd':
            windtype = 'Horizontal'
        elif flightmet == 'u':
            windtype = 'U-component'
        elif flightmet == 'v':
            windtype = 'V-component'            
        elif flightmet == 'wvert':
            windtype = 'Vertical'

        antext1='Synthesis alt: '+synth_alt+' m MSL'
        antext2='Flight level alt: '+flgt_alt+' m MSL'
        title1=windtype +' wind speed\n'+self.name
        title2='Flight level and P3 synthesis comparison - '+windtype+' wind speed\n'+self.name

        if noplot is True:
            pass
        else:
            ''' grid '''
            plt.figure(figsize=(8,7))
            im=plt.imshow(data.T, interpolation='none',origin='lower',cmap='jet')
            for p,val in zip(line_center,data_extract2):
                colorVal=scalarMap.to_rgba(val)
                plt.plot(p[0],p[1],color=colorVal,marker='s',markersize=6,linestyle='none')
            plt.xlabel('X')
            plt.ylabel('Y')
            plt.colorbar(im)
            plt.annotate(antext1, xy=(0.1, 0.95), xycoords="axes fraction",fontsize=14)
            plt.suptitle(title1)
            plt.grid(which='major')
            plt.draw()
    
            ''' timeseries '''
            fig, ax1 = plt.subplots(figsize=(8,7))
            ln1=ax1.plot(data_extract,'bo',label='raw synthesis wind')
            ln2=ax1.plot(data_extract2,'rs',label='synthesis wind interpolated')
            ln3=ax1.plot(flgt_mean,'g',label='flight wind')
            ax1.set_ylabel('wind speed [m/s]')
            ax1.set_xlabel('Points along line')
            ax2=ax1.twinx()
            vmin=min(flgt_altitude)-50
            vmax=max(flgt_altitude)+50
            ln4=ax2.plot(flgt_altitude,'black',label='flight altitude')
            ax2.set_ylim([vmin,vmax])
            ax2.set_ylabel('Meters MSL')
            lns=ln1+ln2+ln3+ln4
            labs=[l.get_label() for l in lns]
            ax2.legend(lns,labs,numpoints=1,loc=4,prop={'size':10})
            ax2.annotate(antext1, xy=(0.5, 0.9), xycoords="axes fraction",fontsize=14)
            plt.grid(which='major')
            plt.suptitle(title2)
            plt.draw()
    
    
            ''' scatter '''
            # with sns.axes_style("darkgrid"):
            fig,ax=plt.subplots(figsize=(8,7))
            # fig,ax=plt.subplots()
            x=np.asarray(flgt_mean)
            y=np.asarray(data_extract2)
            ax.scatter(x,y)
            #----------
            # 1:1 line
            #==========
            maxx=np.nanmax(x)
            minx=np.nanmin(x)
            maxy=np.nanmax(y)
            miny=np.nanmin(y)
            mmax=np.max([maxx,maxy])
            mmin=np.min([minx,miny])
            x1to1=np.linspace(-30,30,3)
            y1to1=x1to1
            ax.plot(x1to1, y1to1, color='k', linestyle='-', linewidth=2)
            #-------------
            # regression
            #=============
            xs = x[~np.isnan(y)]
            ys = y[~np.isnan(y)]
            model=sm.OLS(ys,xs)
            result=model.fit()
            c=0
            m=result.params[0]
            xr=np.linspace(-30,30,3)
            yr=c+m*xr
            ax.plot(xr, yr, color='r', linestyle=':', linewidth=2)
            #--------------
            r2=np.round(result.rsquared,decimals=2)
            m=np.round(m,decimals=2)
            antext3="R-sqr: "+str(r2)
            antext4="Y = "+str(m)+" * X"
            textstr = antext2+'\n'+antext1+'\n'+antext3+'\n'+antext4
            ax.text(0.5, 0.05, textstr, transform=ax.transAxes, fontsize=14,
                    verticalalignment='bottom')
            ax.set_aspect(1)
            ax.set_xlim([mmin*0.95, mmax*1.05])
            ax.set_ylim([mmin*0.95, mmax*1.05])
    
            plt.suptitle(title2)
            plt.xlabel('Flight wind speed [m s-1]')
            plt.ylabel('Synthesis wind speed [m s-1]')
            plt.grid(which='major')

        return flgt_mean, data_extract2

    def print_covariance_matrix(self,data):

        met=data[['atemp','dewp','jwlwc','wdir','wspd','wvert','theta','thetav','thetaeq']]
        print "Covariance matrix"
        print "------------------------\n"
        print met.cov()
        print "------------------------\n"

    def print_correlation_matrix(self,data):

        met=data[['atemp','dewp','jwlwc','wdir','wspd','wvert','theta','thetav','thetaeq']]
        print "Correlation matrix"
        print "------------------------\n"
        print met.corr()
        print "------------------------\n"

    def plot_wind_comp_var(self,data,xaxis):

        met=data[['wdir','wspd','wvert']]

        ''' wind components and their variance'''
        u_comp,v_comp = get_wind_components(met.wspd,met.wdir)
        w_comp=met.wvert
        u_var = pd.rolling_var(u_comp,60,center=True)
        v_var = pd.rolling_var(v_comp,60,center=True)
        w_var = pd.rolling_var(w_comp,60,center=True)
        fig,(ax1,ax2,ax3) = plt.subplots(3,sharex=True)
        fs=14
        xpos=0.02
        ypos=0.9

        ''' u '''
        ax1.plot(xaxis, u_comp)
        add_text_to(ax1,xpos,ypos,'u-comp',fontsize=fs,color='b')
        add_text_to(ax1,0.95-xpos,ypos,'u-var',fontsize=fs,color='r')
        add_second_y_in(ax1,u_var,xaxis=xaxis)
        ''' v '''
        ax2.plot(xaxis, v_comp)
        add_text_to(ax2,xpos,ypos,'v-comp',fontsize=fs,color='b')
        add_text_to(ax2,0.95-xpos,ypos,'v-var',fontsize=fs,color='r')
        add_second_y_in(ax2,v_var,xaxis=xaxis)
        ''' w '''
        ax3.plot(xaxis, w_comp)
        add_text_to(ax3,xpos,ypos,'w-comp',fontsize=fs,color='b')
        add_text_to(ax3,0.95-xpos,ypos,'w-var',fontsize=fs,color='r')
        add_second_y_in(ax3,w_var,xaxis=xaxis)
        
        fig.subplots_adjust(hspace=0.1)
        plt.draw()

    def plot_tke(self,data,xaxis):

        met=data[['wdir','wspd','wvert','lats','lons']]
        topo=np.asarray(Terrain.get_topo(lats=met['lats'], lons=met['lons']))

        u_comp,v_comp = get_wind_components(met.wspd,met.wdir)
        w_comp=met.wvert
        u_var = pd.rolling_var(u_comp,60,center=True)
        v_var = pd.rolling_var(v_comp,60,center=True)
        w_var = pd.rolling_var(w_comp,60,center=True)

        tke = 0.5*(u_var+v_var+w_var)
        plt.figure()
        plt.plot(xaxis,tke)
        ax=plt.gca()
        ax.set_ylim([0,10])
        plt.xlabel('distance')
        plt.ylabel('TKE [m2 s-2]')
        add_second_y_in(ax,topo,xaxis=xaxis,color='g',label='Topography [m]')
        plt.draw()

    def plot_vertical_heat_flux(self,data,xdata):

        met=data[['theta','wvert','lats','lons']]
        topo=np.asarray(Terrain.get_topo(lats=met['lats'], lons=met['lons']))
        
        v_heatflux = pd.rolling_cov(met.wvert, met.theta, 60, center=True)

        plt.figure()
        plt.plot(xdata,v_heatflux)
        ax=plt.gca()
        ax.set_ylim([-0.5,0.5])
        ax.set_ylabel('Vertical heat flux [K m s-1]',color='b',fontsize=15)
        ax.set_xlabel('Distance from flight start [km]',fontsize=15)
        add_second_y_in(ax,topo,xaxis=xdata, color='r',label='Topography [m]')
        plt.draw()

    def plot_vertical_momentum_flux(self,data,xdata,terrain):

        met=data[['wdir','wspd','wvert','lats','lons']]
        # topo=np.asarray(Terrain.get_topo(lats=met['lats'], lons=met['lons']))
        topo2=np.asarray(Terrain.get_topo2(lats=met['lats'], lons=met['lons'],terrain=terrain))

        u_comp,v_comp = get_wind_components(met.wspd,met.wdir)
        w_comp=met.wvert

        u_moflux = pd.rolling_cov(u_comp, w_comp, 60, center=True)
        v_moflux = pd.rolling_cov(v_comp, w_comp, 60, center=True)

        fig, ax = plt.subplots(2,1, sharex=True)
        l1=ax[0].plot(xdata,u_moflux,label='U-moment')
        l2=ax[0].plot(xdata,v_moflux,label='V-moment')
        ax[0].set_ylim([-1.0,1.0])
        ax[0].set_ylabel('Vertical momentum flux [ m2 s-2]',color='b',fontsize=15)
        # plt.legend(handles=[l1,l2])
        ax[0].legend()

        spl=UnivariateSpline(xdata[::5],topo2[::5],k=5)
        xsmooth=np.linspace(0.,xdata[-1],int(len(xdata)))
        ysmooth=spl(xsmooth)
        ysmooth[ysmooth<0]=0
        ax[1].plot(xsmooth, ysmooth,color='black')
        ax[1].set_xlabel('Distance from flight start [km]',fontsize=15)

        plt.draw()

    def plot_turbulence_spectra(self,data):
        
        from scipy import fftpack

        array=np.squeeze(data[['wvert']].values)
        galt=np.squeeze(data[['galt']].values)
        acft_alt=np.mean(galt)
        variance=np.var(array)

        print array.size
        F = fftpack.fft(array)
        cut_half = int(len(array)/2)
        ps = 2*np.abs( F[:cut_half] )**2
        freq=np.linspace(1,len(ps),len(ps))/len(F)
        
        ' power density '
        fig,ax=plt.subplots(2,1,figsize=(8,10))
        ax[0].plot(array)
        ax[1].loglog(freq, ps)

        ' intertial subrange '
        x=np.linspace(0.005, 0.5, 1000)
        inertial = x**(-5/3.)
        ln=ax[1].loglog(x,inertial,linestyle='--',color='k',linewidth=3,label='-5/3')

        ' set spectrum label to seconds '
        xSeconds=[]
        for x in ax[1].get_xticks():
            xSeconds.append(int(1/x))
        ax[1].set_xticklabels(xSeconds)

        ax[0].text(0.1,0.15,'Variance:' + '{:2.1f}'.format(variance),transform=ax[0].transAxes,weight='bold')
        ax[0].text(0.1,0.1,'Acft altitude: '+ '{:2.1f}'.format(acft_alt)+' m MSL',transform=ax[0].transAxes,weight='bold')
        ax[0].set_ylabel('vvel [m s^-1]')
        ax[0].set_xlabel('seconds from beg of leg')
        ax[0].set_ylim([-3,3])
        ax[1].set_ylim([1e-2,1e7])
        ax[1].set_xlabel('seconds')
        ax[1].set_ylabel('2|F|^2')
        ax[1].legend(handles=ln)

        ax[1].xaxis.grid(b=True, which='minor')

        plt.subplots_adjust(top=0.95,bottom=0.08,hspace=0.15)

        time_title=self.time[0].strftime('%dT%H:%M:%S')+' - '+self.time[1].strftime('%dT%H:%M:%S')+' UTC'
        plt.suptitle('P3 Flight level '+self.time[0].strftime('%Y-%b')+'\n'+time_title)
        plt.draw()        

def add_text_to(ax,x,y,text,**kwargs):

        fs=kwargs['fontsize']
        co=kwargs['color']
        axtxt=ax.twinx()
        axtxt.text(x,y,text,transform=axtxt.transAxes,size=fs,color=co)    
        axtxt.set_frame_on(False)
        axtxt.axes.get_yaxis().set_visible(False)    

def add_second_y_in(ax,data,**kwargs):
        
        axt = ax.twinx()
        if kwargs:
            for key, value in kwargs.iteritems():
                if key == 'xaxis':
                    x=value
                elif key == 'color':
                    co=value
                elif key == 'label':
                    lb=value
            axt.plot(x,data,co)
            axt.set_ylabel(lb,color=co,fontsize=15)
        else:
            axt.plot(data)

        axt.grid(False)

def adjust_yaxis(axes):

    for i in range(9):
        newlabels=[]
        yticks=axes[i].get_yticks()

        """ make list of new ticklabels """
        for y in yticks:
            if i in [2,6]:
                newlabels.append(str(y))
            else:
                newlabels.append("{:.0f}".format(y))

        """ delete overlapping ticklabels """
        if i in [0,1,2]:
            newlabels[0]=''
            axes[i].set_yticklabels(newlabels)
        elif i in [3,4,5]:
            newlabels[0]=''
            newlabels[-1]=''
            axes[i].set_yticklabels(newlabels)
        elif i == 6:
            newlabels[-2]=''
            axes[i].set_yticklabels(newlabels)
        elif i in [7,8]:
            newlabels[-1]=''
            axes[i].set_yticklabels(newlabels)

def adjust_xaxis(axes,new_xticks):

    for i in [6,7,8]:
        xticks=axes[i].get_xticks()
        new_xticks = cm.round_to_closest_int(new_xticks,10)
        axes[i].set_xticks(new_xticks)

def get_wind_components(wspd,wdir):
    deg2rad=np.pi/180
    u = -wspd*np.sin(wdir*deg2rad)
    v = -wspd*np.cos(wdir*deg2rad)
    return u,v
