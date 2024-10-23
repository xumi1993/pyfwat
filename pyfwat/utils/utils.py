from posixpath import dirname
import numpy as np
import subprocess
from os.path import join, basename, abspath
import re
import sys

def parse_cpt_name(cpt_name):
    cpt_path = join(dirname(abspath(__file__)), 'cpt', cpt_name+'.cpt')
    return cpt_path

