#!/usr/bin/env python
import re
import sys


def chpar(parstr, key, value):
    if not re.search('{}'.format(key), parstr):
        raise ValueError('No paremeter called {}'.format(key))
    parstr, repl_num = re.subn(r'({}\s+)(.+?)\n'.format(key), '\g<1>{}\n'.format(str(value)), parstr)
    if repl_num != 1:
        raise ValueError('More than one parameter will be changed. Please check.')
    else:
        return parstr


def setpar(par_file, key, value):
    with open(par_file) as f:
        content = f.read()
    content = chpar(content, key, value)
    with open(par_file, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 3:
        print('Usage: setfk.py filename key value')
    # v = readpar('flat_right_deg59_deep/Par_file', 'NPROC')
    setpar(args[0], args[1], args[2])