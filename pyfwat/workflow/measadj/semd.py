import obspy
from obspy.io.sac import SACTrace
from ...para import FWATPara
from ..src_rec import SrcRec
from .. import SOLVER_DIR, FWAT_DATA_DIR, OUTPUT_DIR
import os
import numpy as np

chans = ['E', 'N', 'Z']

class Semd():
    def __init__(self, para:FWATPara, simu_type, model, ch_code='BX') -> None:
        self.para = para
        self.simu_type = simu_type
        self.model = model
        self.ch_code = ch_code
        self.sr = SrcRec.read(para, simu_type)
        self.model_path = os.path.join(
            self.para.abs_workdir,
            SOLVER_DIR,
            self.model
        )
        self.obs_data = {}
        self.syn_data = {}
    
    def _read_obs(self):
        for _, src in self.sr.sources.iterrows():
            data_path = os.path.join(
                self.para.abs_workdir,
                FWAT_DATA_DIR,
                src.evtid
            )
            self.obs_data[src.evtid] = obspy.read(os.path.join(data_path, '*.sac'))
    
    def _read_syn(self):
        for _, src in self.sr.sources.iterrows():
            data_path = os.path.join(
                self.model_path,
                src.evtid,
                OUTPUT_DIR
            )
            self.syn_data[src.evtid] = obspy.Stream()
            for _, rec in src['receivers'].iterrows():
                # syn = obspy.read(os.path.join(data_path, f'{rec.sta}.sac'))
                for ch in chans:
                    times, dat = np.loadtxt(
                        os.path.join(data_path, f'{rec.network}.{rec.station}.{self.ch_code}{ch}.semd'),
                        unpack=True
                    )
                    sac = SACTrace(
                        data=dat,
                        delta = times[1] - times[0],
                        b = times[0],
                        knetwk = rec.network,
                        kstnm = rec.station,
                        kcmpnm = f'{self.ch_code}{ch}'
                    )
                    self.syn_data[src.evtid].append(sac.to_obspy_trace())

