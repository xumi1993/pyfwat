from ...utils.decon import RFTrace
from ...para import FWATPara

class RFAdj():
    def __init__(self, para: FWATPara):
        """
        Measure adjoint source for receiver function

        :param para: _description_
        :type para: FWATPara
        """ 
        self.para = para