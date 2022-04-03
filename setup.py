#!/usr/bin/env python
from setuptools import find_packages, setup
packages = find_packages()

with open("README.md", "r") as fh:
    long_description = fh.read()


VERSION = "0.1.1"
setup(name='pyfwat',
      version=VERSION,
      author='Mijian Xu',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author_email='mijian.xu@ntu.edu.sg',
      license='GPLv3',
      packages=find_packages(),
      package_dir={'pyfwat': 'pyfwat'},
      package_data={'': ['cpt/*']},
      install_requires=[
                # 'netcdf4>=1.5.2',
                'obspy>=1.2.0',
                'pandas>=1.0.0',
                'numpy>=1.19.0,<1.22.0',
                'scipy>=1.1.0',
                'matplotlib>=3.2.0',
                'pygmt'],
      entry_points={'console_scripts': ['plot_vel_sec=pyfwat.plot.plot_vel_sec:main',
                                        'plot_stations=pyfwat.plot.plot_stations:main',
                                        'plot_rf_evts=pyfwat.plot.plot_rf_evts:main',
                                        'gen_virt_fkevts=pyfwat.preproc.gen_virt_fkevts:main',
                                        'plot_rf_fit=pyfwat.plot.plot_rf_fit:main']},
      #  include_package_data=True,
      zip_safe=False,
      classifiers=['Programming Language :: Python',
                   'Programming Language :: Python :: 3.7',
                   'Programming Language :: Python :: 3.8',
                   'Programming Language :: Python :: 3.9']
      )