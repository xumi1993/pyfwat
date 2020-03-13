import numpy as np
import subprocess
from os.path import join, basename, abspath
import re
import sys


def readpar(par_file, key):
    s = subprocess.Popen("grep ^{} {} | cut -d = -f 2 | cut -d \\# -f 1 | tr -d ' '".format(key, par_file), 
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outstr = s.stdout.read().decode().strip()
    if outstr == '':
        raise ValueError('ERROR: No paremeter called {} in the {}'.format(key, par_file))
    else:
        try:
            value = float(outstr)
        except ValueError:
            if outstr == '.false.':
                value = False
            elif outstr == '.true.':
                value = True
            else:
                value = outstr
    return value


def readfkpar(par_file, key):
    with open(par_file) as f:
        par = f.read()
    outstr = re.findall(r'{}\s+(.+?)\n'.format(key), par)[0]
    # outstr = s.stdout.read().decode().strip()
    if key != 'INCIDENT_WAVE':
        val_lst = [float(value) for value in outstr.split()]
    if len(val_lst) == 1:
        return val_lst[0]
    else:
        return np.array(val_lst)
    

def bool2str(condition):
    if not isinstance(condition, bool):
        raise ValueError('condition must be bool type')
    if condition:
        return '.true.'
    else:
        return '.false.'
