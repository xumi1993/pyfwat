#!/usr/bin/env python
import re
import sys


def bool2str(condition):
    if not isinstance(condition, bool):
        raise ValueError('condition must be bool type')
    if condition:
        return '.true.'
    else:
        return '.false.'


def chpar(parstr, key, value):
    if not re.search('{}'.format(key), parstr):
        raise ValueError('No paremeter called {}'.format(key))
    if isinstance(value, bool):
        value = bool2str(value)
    parstr, repl_num = re.subn(r'({}\s+=\s*)(\S+)'.format(key), '\g<1>{}'.format(str(value)), parstr)
    if repl_num != 1:
        raise ValueError('More than one parameter will be changed. Please check.')
    else:
        return parstr


def setpar(par_file, key, value, out_par_file=None):
    with open(par_file) as f:
        content = f.read()
    content = chpar(content, key, value)
    if out_par_file is None:
        out_par_file = par_file
    with open(out_par_file, 'w') as f:
        f.write(content)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 3:
        print('Usage: pario.py filename key value')
    # v = readpar('flat_right_deg59_deep/Par_file', 'NPROC')
    setpar(args[0], args[1], args[2])
