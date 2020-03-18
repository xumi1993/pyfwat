#!/usr/bin/env python

import numpy as np
import re


'''
2600  5800  3198  9999. 9999.  0  2
'''

def read_media(media_num, fname='DATA/meshfem3D_files/Mesh_Par_file'):
    with open(fname) as f:
        cont = f.read()
    media = re.findall(r'\n{}\s+(.+?)\s+(.+?)\s+(.+?)\s+9999.'.format(media_num), cont)
    return [float(value) for value in media[0]]
    

def create_buffer(media_3d_num, media_1d_num, elem_num=10):
    media_3d = read_media(media_3d_num)
    media_1d = read_media(media_1d_num)
    buffer = np.linspace(media_3d, media_1d, elem_num)[1:-1]
    for _, media in enumerate(buffer):
        print('{:.0f} {:.0f} {:.0f} 9999. 9999.  0  2'.format(media[0], media[1], media[2]))


if __name__ == "__main__":
    create_buffer(1, 2)
