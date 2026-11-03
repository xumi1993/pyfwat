"""Multi-channel cross-correlation of waveforms for relative time delays."""

import numpy as np


def mccc(data, dt, twin=0):
    """Relative time delays of waveforms by multi-channel cross-correlation.

    The delay of every pair is taken at the peak of their cross-correlation,
    and the delay of each trace is the least-squares solution relative to the
    mean of all traces (VanDecar and Crosson, 1990).

    :param data: Waveforms of shape ``(ntrace, npts)`` with a common sampling
    :type data: numpy.ndarray
    :param dt: Sampling interval in s
    :type dt: float
    :param twin: Maximum lag window in s, 0 for no limit, defaults to 0
    :type twin: float, optional
    :return: Time delay of each trace in s
    :rtype: numpy.ndarray
    """
    nt = data.shape[1] * 2
    ns = data.shape[0]
    mask = np.ones(nt)
    tcc = np.zeros([ns, ns])
    tdel = np.zeros(ns)
    fft_all = np.fft.fft(data, nt, 1)
    fft_conj = fft_all.conj()

    if twin != 0:
        itw = np.fix(twin/(2*dt))
        mask = np.zeros(nt)
        mask[0:itw] = 1.0
        mask[nt-itw-1:nt] = 1.0
    for i in range(ns-1):
        ffis = fft_conj[i]
#        ffis = np.conj(np.fft.fft(seis[i].data, nt))
        for j in np.arange(i+1, ns):
            ffjs = fft_all[j]
#            ffjs = np.fft.fft(seis[j].data, nt)
            ccf = np.fft.ifft(ffis*ffjs, nt).real*mask
            tcc[i, j] = np.argmax(ccf)

    (row, col) = np.where(tcc > nt/2)
    for i in range(row.shape[0]):
        tcc[row[i], col[i]] -= (nt+1)

    tcc *= dt

    for i in np.arange(0, ns):
        tdel[i] = (-np.sum(tcc[0:i, i]) + np.sum(tcc[i, i+1:ns]))/ns

    return tdel
