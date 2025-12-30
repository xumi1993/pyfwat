import pygmt
import numpy as np
import subprocess
import obspy
from os import remove
import argparse
import glob
from os.path import basename
from ..io.misfit import PeriodBandMisfit
from ..utils.pario import readfwatpar
import os
from .. import SOLVER_PATH

class PlotWaveformFit:
    def __init__(self, modelname, evtid, comp, fltstr=None, simutype='LEQ'):
        """ Plot waveform fitting for a given event and model.
        :param modelname: Model name, e.g., M00, M01...
        :type modelname: str
        :param evtid: Event id
        :type evtid: str
        :param comp: Component name, e.g., Z, R, T
        :type comp: str
        :param fltstr: Period band name, e.g., T005_T020, defaults to the first band in parameter file
        :type fltstr: str, optional
        :param simutype: Simulation type, LEQ or NOISE, defaults to '
        :type simutype: str, optional
        """
        self.para = readfwatpar()
        self.modelname = modelname
        self.iter = int(modelname[1:])
        self.evtid = evtid
        self.comp = comp
        self.chan = f'{self.para[simutype.upper()]['CH_CODE']}{comp}'
        if fltstr is None:
            short_p = self.para[simutype.upper()]['SHORT_P'][0]
            long_p = self.para[simutype.upper()]['LONG_P'][0]
            self.fltstr = f'T{short_p:03d}_T{long_p:03d}'
        elif isinstance(fltstr, str):
            self.fltstr = fltstr 
        else:
            raise ValueError('ERROR: fltstr should be a string representing the band name.')
        self.pbm = PeriodBandMisfit(self.iter, self.fltstr, evtid=self.evtid)

    def read_waveform(self, sort='dist'):
        """ Read observed and synthetic waveforms, normalize them, and sort by distance.
        :param sort: Sorting key, defaults to 'dist'
        :type sort: str, optional
        """
        st_obs = obspy.read(f'{SOLVER_PATH}/{self.modelname}.*/{self.evtid}/OUTPUT_FILES/*.*{self.comp}.obs.sac.{self.fltstr}')
        st_syn = obspy.read(f'{SOLVER_PATH}/{self.modelname}.*/{self.evtid}/OUTPUT_FILES/*.*{self.comp}.syn.sac.{self.fltstr}')
        max_amp = np.max([np.max(np.abs(tr.data)) for tr in st_obs])
        # normalize the waveforms
        for i, tr in enumerate(st_obs):
            tr.data = tr.data / max_amp
            st_syn[i].data = st_syn[i].data / max_amp
        self.dist = np.array([tr.stats.sac.__dict__[sort] for tr in st_syn])
        idx_sort = np.argsort(self.dist)
        self.dist = self.dist[idx_sort] 
        self.st_obs = obspy.Stream([st_obs[i] for i in idx_sort])
        self.st_syn = obspy.Stream([st_syn[i] for i in idx_sort])
        self.times = self.st_syn[0].times() + self.st_syn[0].stats.sac.b

    def read_windows(self):
        """ Read time windows from misfit dataframe.
        """
        self.win_dict = {}
        for tr in self.st_syn:
            net = tr.stats.network
            sta = tr.stats.station
            twin = self.pbm.misfits[(self.pbm.misfits['netwk']==net) & (self.pbm.misfits['stnm']==sta) & (self.pbm.misfits['chan'] == self.chan)]
            if not twin.empty:
                self.win_dict[f'{net}.{sta}'] = twin[['tstart', 'tend']].values.tolist()
            else:
                self.win_dict[f'{net}.{sta}'] = []
    
    def plot(self, xlim=None, outpath='./figures', enf=0.4, yunit=0.3):
        """ Plot waveform fitting.
        :param xlim: x-axis limits, defaults to None
        :type xlim: list, optional
        :param outpath: Output path for figures, defaults to './figures'
        :type outpath: str, optional
        :param enf: Enlargement coefficient for waveform amplitude, defaults to 0.4
        :type enf: float, optional
        :param yunit: y-axis unit per station, defaults to 0.3
        :type yunit: float, optional
        """
        num_sta = len(self.st_obs)
        fig = pygmt.Figure()
        pygmt.config(FONT_TITLE='12p',
                    MAP_GRID_PEN='0.3p,gray')
        if xlim is None:
            xlim = [self.times[0], self.times[-1]]
        ysize = (num_sta+3) * yunit
        fig.basemap(
            region=[*xlim, 0, num_sta+3], projection=f'X8c/{ysize}c',
            frame=[f'xafg+lTime (s)', 'ya1' , f'wSet+t{self.modelname}, Event: {self.evtid}, Band: {self.fltstr}']
        )
        for i, trdat in enumerate(self.st_obs):
            # plot observed data
            fig.plot(
                x=self.times, y=trdat.data * enf + i + 1,
                pen='0.5p,black'
            )
            # plot synthetic data
            trsyn = self.st_syn[i]
            fig.plot(
                x=self.times, y=trsyn.data * enf + i + 1,
                pen='0.5p,255/25/25'
            )
            # plot windows
            staname = f'{trdat.stats.sac.knetwk}.{trdat.stats.station}'
            for twin in self.win_dict[staname]:
                # draw an area to indicate the window
                fig.plot(
                    x=[twin[0], twin[1], twin[1], twin[0], twin[0]],
                    y=[i+0.5, i+0.5, i+1.5, i+1.5, i+0.5],
                    fill='lightblue', transparency=50
                )
            # plot station name
            fig.text(
                x=xlim[0], y=i+1, text=staname, fill='255',
                font='7p,Helvetica,black', justify='RM', offset='-0.1c/0c', no_clip=True
            )
        os.makedirs(outpath, exist_ok=True)
        fig.savefig(f'{outpath}/{self.modelname}_{self.evtid}_waveform_fit_{self.comp}_{self.fltstr}.png')

def main():
    parser = argparse.ArgumentParser('Plot noise/leq fitting.')
    parser.add_argument('-m', help='Model name e.g., M00, M01...', metavar='model')
    parser.add_argument('-s', help='Event id', metavar='evtid')
    parser.add_argument('-f', help='Band name ', default=None, metavar='bandname')
    parser.add_argument('-c', help='Component name, defaults to Z', default='Z', metavar='comp')
    parser.add_argument('-x', help='x-axis limits, defaults to -5/30, NOTE: DO NOT insert space after -x', default=None, metavar='xmin/xmax')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 5', type=float, default=3, metavar='coef')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    parser.add_argument('-t', help='Simulation type, LEQ or NOISE, default to LEQ', default='LEQ', metavar='simutype')
    args = parser.parse_args()

    if args.x is not None:
        xlim = [float(v) for v in args.x.split('/')]
    else:
        xlim = None
    pwf = PlotWaveformFit(args.m, args.s, args.c, args.f, simutype=args.t)
    pwf.read_waveform()
    pwf.read_windows()
    pwf.plot(xlim=xlim, outpath=args.o, enf=args.e)