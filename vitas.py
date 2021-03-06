#!/usr/bin/env python

'''
 Initialize VITAS

 Raul Valenzuela
 July, 2015
 
 Use:
     $./vitas.py -c c03/leg01.cdf -s 010123I.nc -f DBZ -p 1 --wind 
     
     or when need returns using ipython:
     
     import vitas
     out = vitas.main('-c c03/leg01.cdf -s 010123I.nc -f DBZ -p 1 --wind')

'''

import Plotter
import sys
import matplotlib.pyplot as plt
import Filehandler as fh 
import ArgParser as parser
import VitasConfigParser as configp
import os

def main(args=None):

    config = configp.start()
    if args is None:
        args = parser.start()
    elif isinstance(args,basestring):
        args = parser.start(args)
    
    cedfile = args.ced
    stdfile = args.std
    plotFields = args.field 
    multi = args.multi
    print_shapes = args.print_shapes
    print_global_atts = args.print_global_atts
    print_axis = args.print_axis
    print_list_synth = args.print_list_synth
    terrain = args.terrain
    slope = args.slope
    meteo = args.meteo
    valid = args.valid
    prof = args.prof
    nearest = args.nearest
    noplot = args.no_plot

    """ print synhesis availables """
    if print_list_synth:
        synth_folder=fh.set_working_files(config=config)
        out=os.listdir(synth_folder)
        print "Synthesis directories available:"
        for f in out:
            print f
        usr_input = raw_input('\nIndicate directory: ')
        out=os.listdir(synth_folder+'/'+usr_input)
        print "\nSyntheses available:"
        out.sort()
        for f in out:
            if f[-3:]=='cdf': print f
        print '\n'
        sys.exit()


    """ retrieves synthesis and flight instances
        from AircraftAnalysis
    """
    SYNTH, FLIGHT, TERRAIN = fh.set_working_files(cedfile=cedfile,
                                                stdfile=stdfile,
                                                config=config)
    
    """ print shape of attribute arrays """
    if print_shapes:
        SYNTH.print_shapes()
        if not print_global_atts: 
            sys.exit()

    """ print global attirutes of cedric synthesis """
    if print_global_atts:
        SYNTH.print_global_atts()
        sys.exit()

    """ print axis values """
    if print_axis:
        for ax in print_axis:
            if ax.isupper():
                ax=ax.lower()
            SYNTH.print_axis(ax)
        sys.exit()

    """ print synthesis time """
#    print "Synthesis start time :%s" % SYNTH.start
#    print "Synthesis end time :%s\n" % SYNTH.end

    """ make synthesis plots """
    if plotFields:
        for f in plotFields:
            P=Plotter.plot_synth(SYNTH,FLIGHT,TERRAIN,
                                var=f,
                                wind=args.wind,
                                panel=args.panel,
                                slicem = args.slicem,
                                slicez = args.slicez,
                                slice = args.slice,
#                                azimuth = args.azimuth,
#                                distance = args.distance,
                                zoomIn=args.zoomin,
                                mask = args.mask,
                                config=config)

    """ make terrain plots """
    if terrain or slope:
        # P[0] might produce error if P is not a list, 
        # check in ploth_synth.cross_section
        Plotter.plot_terrain(P[0],
                             terrain=terrain,
                             slope=slope,
                             terrain_file=config['filepath_dtm'])

    """ make flight level meteo plot """
    if meteo:
        Plotter.plot_flight_meteo(SYNTH,FLIGHT)

    """ compare synth and flight level """
    if valid:
        out = Plotter.compare_synth_flight(SYNTH,FLIGHT,
                                     level=valid,
                                     zoomin=args.zoomin,
                                     noplot=noplot)
        
#        if 'wind_profiler' in config:
#            case=int(cedfile[1:3])
#            Plotter.compare_with_windprof(SYNTH,
#                                          location=config['wind_profiler'],
#                                          case=case)
        return out
        
    """ make profile from synthesis """
    if prof:
        if nearest is None:
            markers=['o','s','D','*']
            out = Plotter.make_synth_profile(SYNTH,coords=prof,
                                             markers=markers,
                                             noplot=noplot)
        else:
            ' (4.5km,n=12) or (7.0km,n=30) seem good choices '
            out = Plotter.make_synth_profile_withnearest(SYNTH,
                                                         target_latlon=prof,
                                                         max_dist=nearest[0][0], # [km]
                                                         n_neigh =nearest[0][1])        
        
        try:        
            ' if P exists '
            for i,p in enumerate(prof):
                lat,lon = p
                P.haxis.scatter(lon,lat,
                                s=config['sounding_size'],
                                c=config['sounding_color'],
                                marker=config['sounding_marker'],
                                lw=3)
        except UnboundLocalError:
            ' if P does not exist just pass '
            pass
        return out
        
        
    # if turbulence:
    # Plotter.print_covariance(SYNTH,FLIGHT)
    # Plotter.print_correlation(SYNTH,FLIGHT)
    # Plotter.plot_wind_comp_var(SYNTH,FLIGHT)
    # Plotter.plot_tke(SYNTH,FLIGHT)
    # Plotter.plot_vertical_heat_flux(SYNTH,FLIGHT)
    # Plotter.plot_vertical_momentum_flux(SYNTH,FLIGHT,config['filepath_dtm'])
    # Plotter.plot_turbulence_spectra(SYNTH,FLIGHT)

    if multi:
        plt.close('all')
        return P
    else:        
        ''' use this one with ipython '''
        plt.show(block=False)    
        ''' use this one with the shell '''
        # plt.show()




"""call main function """
if __name__ == "__main__":

    args = parser.start()
    p = main(args)


