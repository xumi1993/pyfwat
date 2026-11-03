"""Data loading, plotting and saving behind the teleseismic picker."""

import numpy as np
import obspy
import matplotlib.pyplot as plt
from matplotlib.widgets import MultiCursor
from os.path import join, basename
from .mccc import mccc
from obspy.io.sac import SACTrace
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees
import glob
import os

"""
Figure for visually check teleseismic waveform in R and Z components based on Matplotlib
"""

class Para():
    """Display and processing settings of the teleseismic picker.

    Attributes: ``freqmin``/``freqmax`` (Hz) of the band-pass filter,
    ``xlim`` time range in s around the arrival, ``marker`` SAC header of the
    reference arrival, ``align`` (``'a'`` for the marker, ``'mccc'`` for the
    MCCC arrival), ``path`` data directory, ``enf`` amplitude scale,
    ``resample_dt``, ``cut_win`` time window in s around the arrival kept when
    saving, and ``num_per_page`` traces per page.
    """
    def __init__(self):
        """Set the default values."""
        self.freqmin = None
        self.freqmax = None
        self.xlim = [-50, 100]
        self.marker = 'a'
        self.align = 'a'
        self.path = ''
        self.enf = 1
        self.resample_dt = 0.025
        self.cut_win = [None, None]
        self.num_per_page = 30


class PickFig(object):
    """Matplotlib figure of the R and Z teleseismic waveforms of an event.

    Traces are sorted by distance and shown page by page; clicking a trace
    toggles whether it is kept, and :meth:`save` writes the result back to the
    data directory.
    """
    def __init__(self, path, marker='t0', resample_dt=None) -> None:
        """:param path: Directory with the ``*R.sac`` and ``*Z.sac`` files of an event
        :type path: str
        :param marker: SAC header of the reference arrival, defaults to ``'t0'``
        :type marker: str, optional
        :param resample_dt: Resampling interval in s, None to keep the original
            sampling, defaults to None
        :type resample_dt: float, optional
        """
        self.para = Para()
        self.para.path = path
        self.para.marker = marker
        self.current_page = 0
        self.read_sac(resample_dt)

    def _get_y_limit(self):
        """Compute the first and last trace index of each page and the number of pages."""
        self.low_lim = np.arange(1, self.stnum+1, self.para.num_per_page)
        self.up_lim = np.append(self.low_lim[1:]-1, self.low_lim[-1]+self.para.num_per_page-1)
        self.npage = self.low_lim.size

    def init_figure(self, figsize=(18,10)):
        """Create the figure with the R and Z axes and the event information.

        :param figsize: Figure size in inches, defaults to ``(18, 10)``
        :type figsize: tuple, optional
        """
        self.fig, self.axes = plt.subplots(1, 2, figsize=figsize, tight_layout=True)
        self.fig.suptitle('Event: {}, Latitude: {:.3f}$^\\circ$, Longitude: {:.3f}$^\\circ$, Depth: {:.1f}, Mag: {:.1f}\n'
                          'Averaged distance: {:.2f}$^\\circ$, Averaged back-azimuth: {:.2f}$^\\circ$'.format(
                          basename(self.para.path), self.stz[0].stats.sac.evla, self.stz[0].stats.sac.evlo,
                          self.stz[0].stats.sac.evdp, self.stz[0].stats.sac.mag, np.mean(self.dist), np.mean(self.baz)), fontweight="bold")
        self._get_y_limit()
    
    def setup_figure(self):
        """Set titles, axis limits and station labels of the current page.

        Labels of the traces marked as bad are gray.
        """
        for st, icomp in zip([self.str_cp, self.stz_cp], [0, 1]):
            ax = self.axes[icomp]
            ax.set_title('{} Component'.format(st[0].stats.channel[-1]))
            ax.set_xlim(*self.para.xlim)
            ax.set_xlabel('Time (s)')
            # ax.set_ylim(0, self.stnum+1)
            y_range = np.arange(self.stnum) + 1
            ax.set_yticks(y_range)
            if icomp == 0:
                ax.set_yticklabels([tr.stats.network+'.'+tr.stats.station for tr in st])
            else:
                ax.set_yticklabels(y_range)
            ax.set_ylim([self.low_lim[self.current_page]-1, self.up_lim[self.current_page]+1])
            for idx in np.where(self.good_seis == 0)[0]:
                ax.get_yticklabels()[idx].set_color('gray')

    def read_sac(self, resample_dt=0.025):
        """Read, resample and sort the R and Z traces.

        :param resample_dt: Resampling interval in s, None to keep the original
            sampling, defaults to 0.025
        :type resample_dt: float, optional
        :raises ValueError: If the R and Z components have different numbers of
            files
        """
        self.str = obspy.read(join(self.para.path,'*R.sac'))
        self.stz = obspy.read(join(self.para.path,'*Z.sac'))
        if len(self.str) != len(self.stz):
            raise ValueError('Different num of files in R and Z components')
        else:
            self.stnum = len(self.stz)

        if resample_dt is not None:
            self.dt = resample_dt
            sample_rate = 1/resample_dt
            for i, str in enumerate(self.str):
                str.resample(sample_rate)
                self.stz[i].resample(sample_rate)
        else:
            self.dt = self.str[0].stats.delta    
        self._calc_distaz()
        self.sort()
        self.str_cp = self.str.copy()
        self.stz_cp = self.stz.copy()
        self.good_seis = np.ones(self.stnum)
        self.wvfillpos = [[[], []] for i in range(self.stnum)]
        self.wvfillnag = [[[], []] for i in range(self.stnum)]
    
    def _calc_distaz(self):
        """Epicentral distance (deg) and back-azimuth of each trace from the SAC headers.

        :raises ValueError: If the headers have neither the station and event
            coordinates nor ``dist`` and ``baz``
        """
        self.dist = np.zeros(self.stnum)
        self.baz = np.zeros(self.stnum)
        for i, tr in enumerate(self.stz):
            if all(hasattr(tr.stats.sac, attr) for attr in ['stla', 'stlo', 'evla', 'evlo']):
                distaz = gps2dist_azimuth(tr.stats.sac.evla, tr.stats.sac.evlo,
                                          tr.stats.sac.stla, tr.stats.sac.stlo)
                self.dist[i] = kilometer2degrees(distaz[0]/1000)
                self.baz[i] = distaz[2]
            elif all(hasattr(tr.stats.sac, attr) for attr in ['dist', 'baz']):
                self.dist[i] = tr.stats.sac.gcarc
                self.baz[i] = tr.stats.sac.baz
            else:
                raise ValueError('Not enough info to calculate epicentral distance and back-azimuth. '
                                 'Please make sure sac headers contain dist, baz or stla, stlo, evla, evlo')

    def filter(self, renew=True, zerosphase=True):
        """Band-pass filter the displayed traces with ``freqmin`` and ``freqmax``.

        Does nothing if either frequency is None.

        :param renew: Filter a fresh copy of the raw traces instead of the current
            ones, defaults to True
        :type renew: bool, optional
        :param zerosphase: Use a zero-phase filter, defaults to True
        :type zerosphase: bool, optional
        """
        if self.para.freqmin is None or self.para.freqmax is None:
            return
        if renew:
            self.str_cp = self.str.copy()
            self.stz_cp = self.stz.copy()
        self.str_cp.taper(max_percentage=0.1, type='hann')
        self.str_cp.filter(type='bandpass', freqmin=self.para.freqmin, 
                           freqmax=self.para.freqmax, corners=4, zerophase=zerosphase)
        self.stz_cp.taper(max_percentage=0.1, type='hann')
        self.stz_cp.filter(type='bandpass', freqmin=self.para.freqmin,
                           freqmax=self.para.freqmax, corners=4, zerophase=zerosphase)

    def tdelta_mccc(self, tb=5, te=20):
        """Relative arrival times of the Z traces by multi-channel cross-correlation.

        :param tb: Window start in s before the marker, defaults to 5
        :type tb: float, optional
        :param te: Window end in s after the marker, defaults to 20
        :type te: float, optional
        """
        dataz = np.zeros((len(self.stz_cp), int((tb+te)/self.dt)))
        for i, trz in enumerate(self.stz_cp):
            tshift = trz.stats.sac[self.para.marker] - trz.stats.sac.b
            nb = int((tshift - tb)/self.dt)
            ne = int((tshift + te)/self.dt)
            dataz[i, :] = trz.data[nb:ne]
        self.tdelta = mccc(dataz, self.dt)
        self.set_times()
        self.get_avg_amp()

    def set_times(self):
        """Set the marker arrival ``t0`` and the MCCC arrival ``tmccc`` of each trace, in s after the trace start."""
        self.t0 = np.zeros(self.stnum)
        self.tmccc = np.zeros(self.stnum)
        for i, tr in enumerate(self.stz):
            self.t0[i] = tr.stats.sac[self.para.marker] - tr.stats.sac.b
            self.tmccc[i] = self.t0[i] - self.tdelta[i]

    def get_avg_amp(self):
        """Set ``avg_amp``, the peak of the mean Z trace aligned on the marker, used to normalize the traces."""
        nb = int(-self.para.xlim[0]/self.dt)
        ne = int(self.para.xlim[1]/self.dt+1)
        avg_data = np.zeros(nb+ne)
        for i, tr in enumerate(self.stz):
            t0 = self.t0[i]
            nref = int(t0/self.dt)
            if nref-nb < 0:
                nref = nb
            avg_data += tr.data[nref-nb:nref+ne]
        avg_data /= self.stnum
        self.avg_amp = np.max(avg_data)

    def plot_seis(self):
        """Plot the R and Z traces aligned on the marker or the MCCC arrival.

        Blue ticks mark the marker arrival and red ticks the MCCC arrival.
        """
        for st, icomp in zip([self.str_cp, self.stz_cp], [0, 1]):
            ax = self.axes[icomp]
            for i, tr in enumerate(st):
                bound = np.zeros(tr.data.size)
                if self.para.align == 'mccc':
                    self.tarr = self.tmccc[i]
                    tt0 = self.tdelta[i]
                    ttal = 0
                else:
                    self.tarr = self.t0[i]
                    tt0 = 0
                    ttal = self.tdelta[i]
                times = tr.times() - self.tarr
                data = tr.data / self.avg_amp * self.para.enf + (i + 1)
                ax.plot(times, data, color='gray', lw=0.3)
                self.wvfillpos[i][icomp] = ax.fill_between(times, data, bound + i+1, where=data > i+1, facecolor='red',
                                alpha=0.5)
                self.wvfillnag[i][icomp] = ax.fill_between(times, data, bound + i+1, where=data < i+1, facecolor='blue',
                                alpha=0.5)
                ax.plot([tt0, tt0], [i+1-0.3, i+1+0.3], color='blue')
                ax.plot([ttal, ttal], [i+1-0.3, i+1+0.3], color='red')
    
    def page_up(self):
        """Go to the next page if there is one."""
        if self.current_page < self.npage-1:
            self.current_page += 1
            # for ax in self.axes:
                # ax.set_ylim([self.low_lim[self.current_page]-1, self.up_lim[self.current_page]+1])
    
    def page_down(self):
        """Go to the previous page if there is one."""
        if self.current_page > 0:
            self.current_page -= 1
            # for ax in self.axes:
                # ax.set_ylim([self.low_lim[self.current_page]-1, self.up_lim[self.current_page]+1])

    def sort(self, key='dist'):
        """Sort the traces by distance or back-azimuth.

        :param key: ``'dist'`` (or ``'gcarc'``) or ``'baz'``, defaults to ``'dist'``
        :type key: str, optional
        """
        if key == 'gcarc' or key == 'dist':
            idx = np.argsort(self.dist)
        elif key == 'baz':
            idx = np.argsort(self.baz)
        self.dist = self.dist[idx]
        self.baz = self.baz[idx]
        self.stz = obspy.Stream([self.stz[i] for i in idx])
        self.str = obspy.Stream([self.str[i] for i in idx])

    def onclick(self, event):
        """Toggle whether the clicked trace is kept.

        :param event: Mouse click event
        :type event: matplotlib.backend_bases.MouseEvent
        """
        if event.inaxes != self.axes[0] and event.inaxes != self.axes[1]:
            return
        click_idx = int(np.round(event.ydata))
        ticklabels = [ax.get_yticklabels() for ax in self.axes]
        if click_idx > self.stnum:
            return
        if self.good_seis[click_idx-1] == 1:
            # self.log.RFlog.info("Selected "+self.filenames[click_idx-1])
            self.good_seis[click_idx-1] = 0
            self.wvfillpos[click_idx-1][0].set_facecolor('gray')
            self.wvfillpos[click_idx-1][1].set_facecolor('gray')
            self.wvfillnag[click_idx-1][0].set_facecolor('gray')
            self.wvfillnag[click_idx-1][1].set_facecolor('gray')
            for ticklabel in ticklabels:
                ticklabel[click_idx-1].set_color('gray')
        else:
            # self.log.RFlog.info("Canceled "+self.filenames[click_idx-1])
            self.good_seis[click_idx-1] = 1
            self.wvfillpos[click_idx-1][0].set_facecolor('red')
            self.wvfillpos[click_idx-1][1].set_facecolor('red')
            self.wvfillnag[click_idx-1][0].set_facecolor('blue')
            self.wvfillnag[click_idx-1][1].set_facecolor('blue')
            for ticklabel in ticklabels:
                ticklabel[click_idx-1].set_color('black')
    
    def onclick_arr(self, event):
        """Shift the arrival times of all traces by the clicked time.

        The marker arrivals or the MCCC arrivals are shifted, depending on
        ``align``.

        :param event: Mouse click event
        :type event: matplotlib.backend_bases.MouseEvent
        """
        if event.inaxes != self.axes[0] and event.inaxes != self.axes[1]:
            return
        tcorr = event.xdata
        if self.para.align == 'mccc':
            self.tmccc += tcorr
        else:
            self.t0 += tcorr

    def _set_gray(self):
        """Gray out the traces marked as bad."""
        for i in np.where(self.good_seis == 0)[0]:
            self.wvfillpos[i][0].set_facecolor('gray')
            self.wvfillpos[i][1].set_facecolor('gray')
            self.wvfillnag[i][0].set_facecolor('gray')
            self.wvfillnag[i][1].set_facecolor('gray')
    
    def get_tref(self, idx):
        """Reference arrival of a trace, following ``align``.

        :param idx: Trace index
        :type idx: int
        :return: Arrival time in s after the trace start
        :rtype: float
        """
        if self.para.align == 'mccc':
            tref = self.tmccc[idx]
        else:
            tref = self.t0[idx]
        return tref

    def trim(self):
        """Cut the traces marked as bad in ``str_trim`` and ``stz_trim`` to ``cut_win`` around their arrival."""
        for i in np.where(self.good_seis == 0)[0]:
            tref = self.get_tref(i)
            self.str_trim[i].trim(self.str_trim[i].stats.starttime+tref+self.para.cut_win[0],
                                  self.str_trim[i].stats.starttime+tref+self.para.cut_win[1])
            self.stz_trim[i].trim(self.stz_trim[i].stats.starttime+tref+self.para.cut_win[0],
                                  self.stz_trim[i].stats.starttime+tref+self.para.cut_win[1])
    
    def restore(self):
        """Discard filtering by copying the raw traces to the displayed ones."""
        self.str_cp = self.str.copy()
        self.stz_cp = self.stz.copy()

    def save(self):
        """Delete the files of the bad traces and rewrite the kept ones.

        Kept traces are written as ``<net>.<sta>.<comp>.sac`` with the reference
        arrival in the ``t0`` header; the selection and pages are then reset.
        """
        self.str_trim = self.str.copy()
        self.stz_trim = self.stz.copy()
        if not (None in self.para.cut_win):
            self.trim()
        self.str_cp = [ self.str_cp[i] for i in range(self.stnum) if self.good_seis[i] == 1]
        self.stz_cp = [ self.stz_cp[i] for i in range(self.stnum) if self.good_seis[i] == 1]
        self.str = [ self.str[i] for i in range(self.stnum) if self.good_seis[i] == 1]
        self.stz = [ self.stz[i] for i in range(self.stnum) if self.good_seis[i] == 1]
        for i in range(self.stnum):
            if self.good_seis[i] == 0:
                files = glob.glob(join(self.para.path,'{}.{}.*'.format(
                                  self.stz_trim[i].stats.sac.knetwk,
                                  self.stz_trim[i].stats.sac.kstnm)))
                for fil in files:
                    os.remove(fil)
            else:
                tref = self.get_tref(i)
                for tr in [self.str_trim[i], self.stz_trim[i]]:
                    sac = SACTrace.from_obspy_trace(tr)
                    # sac.b = tref+self.para.cut_win[0]
                    sac.t0 = tref + sac.b
                    sac.write(join(self.para.path, '{}.{}.{}.sac'.format(
                                sac.knetwk, sac.kstnm, sac.kcmpnm)))
        delete_idx = np.where(self.good_seis == 0)[0]
        self.t0 = np.delete(self.t0, delete_idx)
        self.tmccc = np.delete(self.tmccc, delete_idx)
        self.tdelta = np.delete(self.tdelta, delete_idx)
        self.stnum = len(self.stz_cp)
        self.good_seis = np.ones(self.stnum)
        self._get_y_limit()
        self.get_avg_amp()
        self.current_page = 0
        
    def reset(self):
        """Clear the axes and recompute the pages."""
        for ax in self.axes:
            ax.cla()
        self._get_y_limit()


if __name__ == '__main__':
    pf = PickFig('/Users/xumijian/Researches/Myanmar_FWI/TELE/data/2017.316.18.18.17')
    pf.read_sac()
    pf.filter()
    pf.tdelta_mccc()
    # print(pf.tdelta)
    # pf.stz.plot()
    pf.plot_seis(align_with_mccc=True)
