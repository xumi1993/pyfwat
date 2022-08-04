import pygmt
from pygmt.clib import Session
import numpy as np
import subprocess
import obspy
from os import remove
import argparse
import glob
from os.path import basename
import os

def read_waveforms(evtid, periodmin, periodmax):
    pass