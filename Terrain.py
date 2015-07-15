#
# Functions for digital terrain model
#
# Raul Valenzuela
# July 2015


from os.path import isfile
from mpl_toolkits.axes_grid1 import ImageGrid
import tempfile
import os
import gdal
import numpy as np
import matplotlib.pyplot as plt

class Terrain(object):
	def __init__(self,filepath):
		if filepath:
			self.file=filepath
		else:
			self.file=None

		self.array=None

# def plot_level():

# def plot_profile():

def add_contour(axis,Plot):

	if not Plot.terrain.array:
		dtm=make_array(Plot.terrain.file,Plot)
		Plot.terrain.array=dtm
	else:
		dtm=Plot.terrain.array

	cont=axis.contour(dtm['xg'],dtm['yg'],dtm['data'],
					levels=[200,600,1000],
					colors=( (0,0,0) , (0.3,0.3,0.3), (0.6,0.6,0.6) ),
					linewidths=2)
	
	axis.clabel(cont,[200,600,1000],fmt='%.0f',fontsize=12,inline_spacing=2)	

def plot_altitude_mask(axis,S,dtm):

	extent=S.get_extent()

	axis.figure()
	axis.plot(S.coast['lon'], S.coast['lat'], color='r')
	axis.plot(S.flight_lon, S.flight_lat,color='r')		
	axis.imshow(dtm['data'],
					interpolation='none',
					cmap='terrain_r',
					vmin=500,
					vmax=501,
					extent=dtm['extent'])
	axis.colorbar()
	axis.xlim(extent[0], extent[1])
	axis.ylim(extent[2], extent[3])				
	axis.draw()

def plot_slope_map(SynthPlot):

	extent=SynthPlot.get_extent()

	dem_file=tempfile.gettempdir()+'/terrain_resampled.tmp'
	out_file=tempfile.gettempdir()+'/terrain_slope.tmp'

	if isfile(out_file):
		data=get_data(out_file)
	else:
		input_param = (dem_file, out_file)
		run_gdal = 'gdaldem slope %s %s -p -s 111120 -q' % input_param
		os.system(run_gdal)
		data=get_data(out_file)

	data['cmap']='jet'
	data['vmin']=0
	data['vmax']=20
	data['title']='Terrain slope [%]'
	plot_map(SynthPlot,data)


def plot_altitude_map(SynthPlot):

	dem_file=tempfile.gettempdir()+'/terrain_resampled.tmp'
	data=get_data(dem_file)
	data['cmap']='terrain'
	data['vmin']=0
	data['vmax']=1000
	data['title']='Terrain altitude [m]'
	plot_map(SynthPlot,data)


def plot_map(SynthPlot,data):


	""" zoom (if any) same as the plotted field"""
	extent=SynthPlot.get_extent()

	fig = plt.figure(figsize=(8,8))

	pg=ImageGrid( fig,111,
							nrows_ncols = (1,1),
							axes_pad = 0.0,
							add_all = True,
							share_all=False,
							label_mode = "L",
							cbar_location = "top",
							cbar_mode="single")
	
	pg[0].plot(SynthPlot.coast['lon'], SynthPlot.coast['lat'], color='r')
	pg[0].plot(SynthPlot.flight['lon'], SynthPlot.flight['lat'],color='r')		
	im=pg[0].imshow(data['array'],
					interpolation='none',
					vmin=data['vmin'],
					vmax=data['vmax'],
					cmap=data['cmap'],
					extent=data['extent'])
	pg[0].set_xlim(extent[0], extent[1])
	pg[0].set_ylim(extent[2], extent[3])	
	pg[0].grid(True, which = 'major',linewidth=1)
	pg[0].grid(True, which = 'minor',alpha=0.5)
	pg[0].minorticks_on()

	pg.cbar_axes[0].colorbar(im)

	fig.suptitle(data['title'])	
	plt.tight_layout()
	plt.draw()



def get_data(dtmfile):

	''' store dtm in data '''
	datafile = gdal.Open(dtmfile)
	geotransform=datafile.GetGeoTransform()
	cols=datafile.RasterXSize
	rows=datafile.RasterYSize
	band=datafile.GetRasterBand(1)		
	array=band.ReadAsArray(0,0,cols,rows)
	datafile=None

	''' geographic axes '''
	originX=geotransform[0]
	originY=geotransform[3]
	pixelW=geotransform[1]
	pixelH=geotransform[5]
	
	endingX=originX+cols*pixelW
	endingY=originY+rows*pixelH

	xg=np.linspace(originX,endingX,cols)
	yg=np.linspace(originY,endingY,rows)

	''' data extent '''
	ulx=min(xg)
	lrx=max(xg)
	lry=min(yg)
	uly=max(yg)

	''' return dictionary '''
	data={}
	data['array']=array
	data['extent']=[ulx,lrx,lry,uly]
	data['xg']=xg
	data['yg']=yg

	return data

def make_3d_mask(data,levels,res):

	rows=data['rows']
	cols=data['cols']
	array=data['array']

	''' creates 3D terrain mask array '''
	mask=np.zeros((rows,cols,levels))

	'''Loop through each pixel of DTM and 
	corresponding vertical column of mask'''
	for ij in np.ndindex(mask.shape[:2]):

		'''indices'''
		i,j=ij

		'''index of maximum vertical gate to
		filled with ones (e.g. presence of terrain);
		works like floor function; altitude of mask 
		is zlevel[n-1] for n>0'''
		n = int(np.ceil(array[i,j]/float(res)))

		''' fills verical levels '''
		mask[i,j,0:n] = 1

	return mask

def make_array(dem_file, Plot):

	temp_file=tempfile.gettempdir()+'/terrain_clipped.tmp'
	out_file=tempfile.gettempdir()+'/terrain_resampled.tmp'

	''' same boundaries as synthesis'''
	ulx = min(Plot.lons)
	uly = max(Plot.lats)		
	lrx = max(Plot.lons)
	lry = min(Plot.lats)

	''' number of verical gates '''
	zvalues=Plot.axesval['z']		
	levels=len(zvalues)

	''' vertical gate resolution'''
	res=(zvalues[1]-zvalues[0])*1000 # [m] 

	''' downsample DTM using synthesis axes '''
	xvalues=Plot.axesval['x']
	yvalues=Plot.axesval['y']

	''' output terrian data has same 
	horizontal resolution as synthesis'''
	resampx_to=len(xvalues)*1
	resampy_to=len(yvalues)*1

	if isfile(out_file):
		data=get_data(out_file)
	else:
		''' clip original dtm '''
		input_param = (ulx, uly, lrx, lry, dem_file, temp_file)
		run_gdal = 'gdal_translate -q -projwin %s %s %s %s %s %s' % input_param
		os.system(run_gdal)

		''' resample clipped dtm '''
		input_param = (resampy_to,resampx_to,temp_file, out_file)
		run_gdal = 'gdalwarp -q -ts %s %s -r near -co "TFW=YES" %s %s' % input_param
		os.system(run_gdal)

		data=get_data(out_file)

	# mask=make_3d_mask(data,levels,res)
	mask=[]

	
	''' return dictionary '''
	dtm={}
	dtm['data']=data['array']
	dtm['mask']=mask
	dtm['extent']=data['extent']
	dtm['xg']=data['xg']
	dtm['yg']=data['yg']

	return dtm

def get_altitude_profile(Plot):

	dem_file=tempfile.gettempdir()+'/terrain_resampled.tmp'
	dtm=get_data(dem_file)

	data=dtm['array']

	altitude=[]
	if Plot.sliceo=='zonal':		
		geoax=dtm['yg']
		plotax=dtm['xg']
		for coord in Plot.slicez:
			idx=find_nearest(geoax,coord)
			altitude.append(data[idx,:])
	elif Plot.sliceo=='meridional':
		geoax=dtm['xg']
		plotax=dtm['yg']
		for coord in Plot.slicem:
			idx=find_nearest(geoax,-coord)
			altitude.append(data[:,idx])


	axis=[]
	for a in altitude:
		axis.append(plotax)

	# print profiles
	# exit()
	prof={}
	prof['altitude']=altitude
	prof['axis']=axis

	return prof

def find_nearest(array,value):

	idx = (np.abs(array-value)).argmin()
	return idx