import numpy as np
import subprocess
import re
import sys
from os.path import basename
import argparse


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


def readfwatpar(par_file, key):
    int_str = ['NSCOMP', 'NRCOMP', 'NUM_FILTER', 'NUM_STEP', 'NGAUSS', 'ITMAX']
    array_str = ['SHORT_P', 'LONG_P', 'GROUPVEL_MIN', 'GROUPVEL_MAX', 'STEP_LENS', 'F0']
    with open(par_file) as f:
        par = f.read()
    outstr = re.findall(r'{}:\s+(.+?)\n'.format(key), par)[0]
    if key.upper() in array_str:
        return np.array([float(v) for v in outstr.split()])
    elif key.upper() in ['SCOMPS', 'RCOMPS']:
        return [v for v in outstr.split()]
    elif outstr.lower() == '.true.':
        return True
    elif outstr.lower() == '.false.':
        return False
    elif key.upper() in int_str:
        return int(outstr)
    else:
        try:
            return float(outstr)
        except Exception:
            raise ValueError('Error format in {}'.format(key))


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


def chpar(parstr, key, value, type='sem'):
    if type.lower() not in ['sem', 'fk', 'fwat']:
        raise ValueError('type should be in \'sem\' and \'fk\'')
    if not re.search('{}'.format(key), parstr):
        raise ValueError('No paremeter called {}'.format(key))
    if isinstance(value, bool):
        value = bool2str(value)
    if isinstance(value, (list, np.ndarray)):
        value = ' '.join('{:5.3f}'.format(v) for v in value)
    if type.lower() == 'fk':
        patten = r'^({}\s+)(.+?)(\S+)'.format(key)
        if key == 'ORIGIN_WAVEFRONT':
            patten = r'^({}\s+)(.+?)$'.format('ORIGIN_WAVEFRONT')
    elif type.lower() == 'fwat':
        patten = r'^({}:\s+\s*)(.*?)$'.format(key)
        # value = str(value)+'\n'
    else:
        patten = r'^({}\s+=\s+)(.*?)$'.format(key)
        # value = str(value)
    # print(re.findall(patten,parstr, flags=re.MULTILINE))
    parstr, repl_num = re.subn(patten, '\g<1>{}'.format(str(value)), parstr, flags=re.MULTILINE)
    if repl_num > 1:
        raise ValueError('More than one parameter will be changed. Please check.')
    else:
        return parstr


def setpar():
    parser = argparse.ArgumentParser(description="Set parameters to configure file")
    parser.add_argument('par_file', type=str, help='Path to configure file')
    parser.add_argument('key', type=str, help='key name')
    parser.add_argument('value', type=str, help='value')
    args = parser.parse_args()
    if basename(args.par_file) == 'Par_file' or basename(args.par_file) == 'Mesh_Par_file':
        type = 'sem'
    elif 'fwat' in basename(args.par_file).lower():
        type = 'fwat'
    else:
        type = 'fk'
    with open(args.par_file) as f:
        content = f.read()
    content = chpar(content, args.key, args.value, type=type)
    with open(args.par_file, 'w') as f:
        f.write(content)

