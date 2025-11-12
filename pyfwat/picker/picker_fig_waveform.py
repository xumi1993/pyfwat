import numpy as np
import obspy
import matplotlib.pyplot as plt
from matplotlib.widgets import MultiCursor
from os.path import join, basename, normpath
from .mccc import mccc
from obspy.io.sac import SACTrace
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees
import glob
import os

"""
Figure for visually check teleseismic waveform in R and Z components based on Matplotlib
"""

class Para():
    def __init__(self):
        self.freqmin = None
        self.freqmax = None
        self.xlim = [-50, 100]
        self.path = ''
        self.comp = 'Z'
        self.sort_key = 'dist'
        self.enf = 1
        self.resample_dt = 0.025
        self.cut_win = [None, None]
        self.num_per_page = 30


class PickFig(object):
    def __init__(self, path, resample_dt=None) -> None:
        self.para = Para()
        self.para.path = path
        self.current_page = 0
        self.read_sac(resample_dt)

    def _get_y_limit(self):
        self.low_lim = np.arange(1, self.stnum+1, self.para.num_per_page)
        self.up_lim = np.append(self.low_lim[1:]-1, self.low_lim[-1]+self.para.num_per_page-1)
        self.npage = self.low_lim.size

    def init_figure(self, figsize=(18,10)):
        self.fig, self.axes = plt.subplots(1, 1, figsize=figsize, tight_layout=True)
        if hasattr(self.stz[0].stats.sac, 'evdp'):
            evdp = self.stz[0].stats.sac.evdp
        else:
            evdp = 0.
        self.fig.suptitle('Event: {}, Latitude: {:.3f}$^\\circ$, Longitude: {:.3f}$^\\circ$, Depth: {:.1f}\n'.format(
                          basename(normpath(self.para.path)), self.stz[0].stats.sac.evla, self.stz[0].stats.sac.evlo,
                          evdp), fontweight="bold")
        self._get_y_limit()
    
    def setup_figure(self):
        ax = self.axes
        ax.set_title('{} Component'.format(self.stz_cp[0].stats.channel[-1]))
        if self.para.xlim is None:
            self.get_xlim_from_data()
        ax.set_xlim(*self.para.xlim)
        ax.set_xlabel('Time (s)')
        # ax.set_ylim(0, self.stnum+1)
        y_range = np.arange(self.stnum) + 1
        ax.set_yticks(y_range)
        ax.set_yticklabels([tr.stats.network+'.'+tr.stats.station for tr in self.stz_cp])
        ax.set_ylim([self.low_lim[self.current_page]-1, self.up_lim[self.current_page]+1])
        for idx in np.where(self.good_seis == 0)[0]:
            ax.get_yticklabels()[idx].set_color('gray')

    def get_xlim_from_data(self):
        min_t = np.inf
        max_t = -np.inf
        for tr in self.stz_cp:
            t_start = tr.stats.sac.b
            t_end = tr.stats.sac.b + tr.stats.npts * tr.stats.delta
            if t_start < min_t:
                min_t = t_start
            if t_end > max_t:
                max_t = t_end
        self.para.xlim = [min_t, max_t]

    def read_sac(self, resample_dt=0.025):
        self.stz = obspy.read(join(self.para.path, f'*{self.para.comp}.sac'))
        if not self.stz:
            raise ValueError(f'No files found in {self.para.comp} component')
        else:
            self.stnum = len(self.stz)

        if resample_dt is not None:
            self.dt = resample_dt
            sample_rate = 1/resample_dt
            for i, stz in enumerate(self.stz):
                stz.resample(sample_rate)
        else:
            self.dt = self.stz[0].stats.delta    
        self._calc_distaz()
        self.sort()
        self.get_avg_amp()
        self.stz_cp = self.stz.copy()
        self.good_seis = np.ones(self.stnum)
        self.wvfillpos = [[] for i in range(self.stnum)]
        self.wvfillnag = [[] for i in range(self.stnum)]
    
    def _calc_distaz(self):
        self.dist = np.zeros(self.stnum)
        self.baz = np.zeros(self.stnum)
        for i, tr in enumerate(self.stz):
            if all(hasattr(tr.stats.sac, attr) for attr in ['dist', 'baz']):
                self.dist[i] = tr.stats.sac.dist
                self.baz[i] = tr.stats.sac.baz
            elif all(hasattr(tr.stats.sac, attr) for attr in ['stla', 'stlo', 'evla', 'evlo']):
                distaz = gps2dist_azimuth(tr.stats.sac.evla, tr.stats.sac.evlo,
                                          tr.stats.sac.stla, tr.stats.sac.stlo)
                self.dist[i] = kilometer2degrees(distaz[0]/1000)
                self.baz[i] = distaz[2]
            else:
                raise ValueError('Not enough info to calculate epicentral distance and back-azimuth. '
                                 'Please make sure sac headers contain dist, baz or stla, stlo, evla, evlo')

    def filter(self, renew=True, zerosphase=True):
        if self.para.freqmin is None or self.para.freqmax is None:
            return
        if renew:
            self.stz_cp = self.stz.copy()
        self.stz.taper(max_percentage=0.1, type='hann')
        self.stz_cp.filter(type='bandpass', freqmin=self.para.freqmin,
                           freqmax=self.para.freqmax, corners=4, zerophase=zerosphase)

    def get_avg_amp(self):
        # nb = max(int((tb-self.para.xlim[0]) / self.dt + 1), 0)
        # ne = min(int((self.para.xlim[1] - self.para.xlim[0]) / self.dt + 1), self.stz[0].data.size)
        # avg_data = np.zeros(ne-nb)
        self.avg_amp = 0.0
        for _, tr in enumerate(self.stz):
            # avg_data += tr.data[nb:ne]
            self.avg_amp += np.abs(tr.data).max()
        self.avg_amp /= self.stnum

    def plot_seis(self):
        ax = self.axes
        for i, tr in enumerate(self.stz_cp):
            bound = np.zeros(tr.data.size)
            times = tr.times() + tr.stats.sac.b
            data = tr.data / self.avg_amp * self.para.enf + (i + 1)
            ax.plot(times, data, color='gray', lw=0.3)
            self.wvfillpos[i] = ax.fill_between(times, data, bound + i+1, where=data > i+1, facecolor='red',
                            alpha=0.5)
            self.wvfillnag[i] = ax.fill_between(times, data, bound + i+1, where=data < i+1, facecolor='blue',
                            alpha=0.5)
    
    def page_up(self):
        if self.current_page < self.npage-1:
            self.current_page += 1
    
    def page_down(self):
        if self.current_page > 0:
            self.current_page -= 1

    def sort(self):
        if self.para.sort_key == 'gcarc' or self.para.sort_key == 'dist':
            idx = np.argsort(self.dist)
        elif self.para.sort_key == 'baz':
            idx = np.argsort(self.baz)
        self.dist = self.dist[idx]
        self.baz = self.baz[idx]
        self.stz = obspy.Stream([self.stz[i] for i in idx])

    def onclick(self, event):
        if event.inaxes != self.axes:
            return
        click_idx = int(np.round(event.ydata))
        ticklabel = self.axes.get_yticklabels()
        if click_idx > self.stnum:
            return
        if self.good_seis[click_idx-1] == 1:
            # self.log.RFlog.info("Selected "+self.filenames[click_idx-1])
            self.good_seis[click_idx-1] = 0
            self.wvfillpos[click_idx-1].set_facecolor('gray')
            self.wvfillnag[click_idx-1].set_facecolor('gray')
            ticklabel[click_idx-1].set_color('gray')
        else:
            # self.log.RFlog.info("Canceled "+self.filenames[click_idx-1])
            self.good_seis[click_idx-1] = 1
            self.wvfillpos[click_idx-1].set_facecolor('red')
            self.wvfillnag[click_idx-1].set_facecolor('blue')
            ticklabel[click_idx-1].set_color('black')

    def _set_gray(self):
        for i in np.where(self.good_seis == 0)[0]:
            self.wvfillpos[i].set_facecolor('gray')
            self.wvfillnag[i].set_facecolor('gray')

    def trim(self):
        for i in np.where(self.good_seis == 0)[0]:
            tref = -self.stz_trim[i].stats.sac.b
            self.stz_trim[i].trim(self.stz_trim[i].stats.starttime+tref+self.para.cut_win[0],
                                  self.stz_trim[i].stats.starttime+tref+self.para.cut_win[1])
    
    def restore(self):
        self.stz_cp = self.stz.copy()

    def save(self):
        self.stz_trim = self.stz.copy()
        if not (None in self.para.cut_win):
            self.trim()
        self.stz_cp = [ self.stz_cp[i] for i in range(self.stnum) if self.good_seis[i] == 1]
        self.stz = [ self.stz[i] for i in range(self.stnum) if self.good_seis[i] == 1]
        for i in range(self.stnum):
            if self.good_seis[i] == 0:
                files = glob.glob(join(self.para.path,'{}.{}.*'.format(
                                  self.stz_trim[i].stats.sac.knetwk,
                                  self.stz_trim[i].stats.sac.kstnm)))
                for fil in files:
                    os.remove(fil)
            else:
                sac = SACTrace.from_obspy_trace(self.stz_trim[i])
                sac.write(join(self.para.path, '{}.{}.{}.sac'.format(
                            sac.knetwk, sac.kstnm, sac.kcmpnm)))
        # delete_idx = np.where(self.good_seis == 0)[0]
        self.stnum = len(self.stz_cp)
        self.good_seis = np.ones(self.stnum)
        self._get_y_limit()
        self.get_avg_amp()
        self.current_page = 0
        
    def reset(self):
        self.axes.cla()
        self._get_y_limit()


if __name__ == '__main__':
    pf = PickFig('/Users/xumijian/Researches/Myanmar_FWI/TELE/data/2017.316.18.18.17')
    pf.read_sac()
    pf.filter()
    pf.tdelta_mccc()
    # pf.stz.plot()
    pf.plot_seis(align_with_mccc=True)
