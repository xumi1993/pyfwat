from posixpath import dirname
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
    if key == 'LAYER':
        outstr = re.findall(r'{}\s+(\d+\s+\d+.+?)\n'.format(key), par)
        model = np.empty([0, 5])
        for line in outstr:
            model = np.vstack((model, np.array([float(value) for value in line.split()])))
        return model
    else:
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


def read_interface(fname='DATA/meshfem3D_files/interfaces.dat', inter_num=1):
    with open(fname) as f:
        cont = f.read()
    interfs = re.findall(r'(\d+)\s+(\d+)\s+(.+?)\s+(.+?)\s+(.+?)\s+(.+?)\s+\n', cont)
    return [float(value) for value in interfs[inter_num-1]]


def parse_cpt_name(cpt_name):
    cpt_path = join(dirname(abspath(__file__)), 'cpt', cpt_name+'.cpt')
    return cpt_path

if __name__ == "__main__":
    interf = read_interface('/share/home/goxu/xu_mijian/workspace/semfk/slop_1/DATA/meshfem3D_files/interfaces.dat')
    print(interf)
