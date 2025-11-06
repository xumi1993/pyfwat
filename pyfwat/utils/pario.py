import numpy as np
import subprocess
import re
import sys
from os.path import basename
import argparse
from ruamel.yaml import YAML


def readpar(par_file, key):
    """ Read parameter from sem parameter file.

    :param par_file: Path to sem parameter file
    :type par_file: str
    :param key: Parameter key to read
    :type key: str
    :return: Parameter value
    :rtype: float, int, bool, str
    """
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
    """ Read parameter from fk parameter file. 
    
    :param par_file: Path to fk parameter file
    :type par_file: str
    :param key: Parameter key to read
    :type key: str
    :return: Parameter value
    :rtype: float, int, bool, np.ndarray
    """
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

def readfwatpar(par_file='DATA/fwat_params.yml'):
    yaml = YAML()
    yaml.default_flow_style = True
    with open(par_file, encoding='utf-8') as f:
        file_data = f.read()
    return yaml.load(file_data)

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
    """
    Change parameter in the parameter string.

    :param parstr: Parameter content as a string
    :type parstr: str
    :param key: Parameter key to change
    :type key: str
    :param value: New value for the parameter
    :type value: str, float, int, bool, list, np.ndarray
    :param type: Type of parameter file, can be 'sem', 'fk', 'fwat', or 'solution'
    :type type: str

    :raises ValueError: If the type is not recognized or the key is not found
    :raises ValueError: If more than one parameter is matched for the key
    
    :return: Modified parameter string
    :rtype: str
    """
    if type.lower() not in ['sem', 'fk', 'solution']:
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
    elif type.lower() == 'solution':
        patten = r'^({}:\s+\s*)(.*?)$'.format(key)
        # value = str(value)+'\n'
    else:
        patten = r'^({}\s+=\s+)(.*?)$'.format(key)
        # value = str(value)
    # print(re.findall(patten,parstr, flags=re.MULTILINE))
    parstr, repl_num = re.subn(patten, r'\g<1>{}'.format(str(value)), parstr, flags=re.MULTILINE)
    if repl_num > 1:
        raise ValueError('More than one parameter will be changed. Please check.')
    else:
        return parstr

def str2val(str_val):
    """ Convert string value to appropriate type: int, float, list of int, list of float, or str.
    
    :param str_val: Input string value
    :type str_val: str
    :return: Converted value
    :rtype: int, float, list of int, list of float, or str
    """
    # single value handling
    # return integer
    try:
        return int(str_val)
    except ValueError:
        pass

    # return float
    try:
        return float(str_val)
    except ValueError:
        pass

    # list values handling
    # return list of integer
    try:
        return [int(v) for v in str_val.strip('[]').split(',')]
    except ValueError:
        pass

    # return list of float
    try:
        return [float(v) for v in str_val.strip('[]').split(',')]
    except ValueError:
        pass

    return str_val

def setpar():
    parser = argparse.ArgumentParser(description="Set parameters to configure file")
    parser.add_argument('par_file', type=str, help='Path to configure file')
    parser.add_argument('key', type=str, help='key name', metavar='key.name')
    parser.add_argument('value', type=str, help='value')
    args = parser.parse_args()
    if basename(args.par_file) == 'Par_file' or basename(args.par_file) == 'Mesh_Par_file':
        type = 'sem'
    elif 'fwat' in basename(args.par_file).lower():
        type = 'fwat'
    elif 'fk' in basename(args.par_file).lower():
        type = 'fk'
    else:
        raise ValueError('Cannot recognize the parameter file type.')
    
    # update parameter in the data structure for fwat parameter file
    if type == 'fwat':
        para = readfwatpar(args.par_file)
        keys = args.key.split('.')
        
        # Navigate to the correct nested location
        current = para
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        
        # Set the value at the final key
        current[keys[-1]] = str2val(args.value)
        
        # Write the complete parameter dictionary back to file
        with open(args.par_file, 'w', encoding='utf-8') as f:
            yaml = YAML()
            yaml.default_flow_style = False
            yaml.dump(para, f)

    # update parameter in the text file for sem and fk parameter file
    else:
        with open(args.par_file) as f:
            content = f.read()
        content = chpar(content, args.key, args.value, type=type)
        with open(args.par_file, 'w') as f:
            f.write(content)

