import pandas as pd
from ..para import FWATPara
from . import SRC_REC_DIR
from .logger import logger
import os
import sys


class DataInfo():
    def __init__(self) -> None:
        self.station_path = ''
        self.fkmodel_path = ''
        self.solution_path = ''
        self.receivers = pd.DataFrame()


class SrcRec():
    def __init__(self):
        self.sources = pd.DataFrame()
        self.receivers_all = pd.DataFrame()
        self.data_map = {}
        self.para = FWATPara()

    @classmethod
    def read(cls, para:FWATPara, simu_type):
        sr = cls()
        sr.para = para
        simu_type = 'tele' if 'tele' in simu_type or simu_type == 'rf' else simu_type
        source_file = os.path.join(sr.para.abs_workdir, SRC_REC_DIR, f'sources_{getattr(sr.para, simu_type)['set_name']}.dat')
        if not os.path.isfile(source_file):
            logger.srcrec.error(f"Source file {source_file} does not exist")
            sys.exit(1)
        try:
            sr.sources = pd.read_csv(source_file, header=None, sep=r'\s+')
        except pd.errors.ParserError as e:
            logger.srcrec.error(f"Error reading source file {source_file}: {e}")
            sys.exit(1)
        if sr.sources.shape[1] == 5:
            sr.sources.columns = ['evtid', 'lat', 'lon', 'dep', 'buried']
            sr.sources['weight'] = 1.0
        elif sr.sources.shape[1] == 6:
            sr.sources.columns = ['evtid', 'lat', 'lon', 'dep', 'buried', 'weight']
        else:
            logger.srcrec.error(f"Source file {source_file} has wrong format")
            sys.exit(1)
        sr.sources = sr.sources.astype({'evtid': str, 'lat': float, 'lon': float, 'dep': float, 'buried': float, 'weight': float})

        # append columns to sources
        fkmodel_path = []
        station_path = []
        solution_path = []
        recs = []
        # read STATIONS
        for _, src in sr.sources.iterrows():
            rec_file = os.path.join(
                sr.para.abs_workdir, SRC_REC_DIR, f'STATIONS_{src.evtid}.dat'
            )
            if not os.path.exists(rec_file):
                logger.srcrec.error(f"Station file {rec_file} does not exist")
                sys.exit(1)
            try:
                rec = pd.read_csv(rec_file, header=None, sep=r'\s+')
            except Exception as e:
                logger.srcrec.error(f"Error in reading station file {rec_file}: {e}")
                sys.exit(1)
            rec.columns = ['station', 'network', 'lon', 'lat', 'elev', 'buried']
            rec = rec.astype({
                'station': str, 'network': str,
                'lon': float, 'lat': float,
                'elev': float, 'buried': float
            })
            recs.append(rec)
            # di = DataInfo()
            # di.station_path = rec_file
            station_path.append(rec_file)
            if 'tele' in simu_type or simu_type == 'rf':
                fkmodel_path.append(os.path.join(sr.para.abs_workdir, SRC_REC_DIR, f'FKmodel_{src.evtid}'))
                solution_path.append(os.path.join(sr.para.abs_workdir, 'DATA', f'CMTSOLUTION'))
            elif simu_type == 'noise':
                solution_path.append(os.path.join(sr.para.abs_workdir, SRC_REC_DIR, f'FORCESOLUTION_{src.evtid}.dat'))
                fkmodel_path.append('')
            else:
                solution_path.append(os.path.join(sr.para.abs_workdir, SRC_REC_DIR, f'CMTSOLUTION_{src.evtid}.dat'))
                fkmodel_path.append('')
            # sr.data_map[src.evtid] = di
        sr.sources['station_path'] = station_path
        sr.sources['fkmodel_path'] = fkmodel_path
        sr.sources['solution_path'] = solution_path
        sr.sources['receivers'] = recs
        sr.receivers_all = pd.DataFrame(recs)
        sr.receivers_all.drop_duplicates(inplace=True, ignore_index=True)
        return sr