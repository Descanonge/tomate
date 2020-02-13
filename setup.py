
from setuptools import setup, find_packages

import data_loader


with open('README.rst') as file:
    long_description = file.read()


required = ['numpy']

extras = {
    "Mask": ["scipy"],
    "NetCDF": ["netCDF4"],
}


setup(name='data_loader',
      version=data_loader.__version__,
      description='Load data from a multitude of files.',
      long_description=long_description,
      keywords='data file netcdf load',
      url='http://github.com/Descanonges/data-loader',
      author='Clément HAËCK',
      author_email='clement.haeck@posteo.net',
      license='MIT License',
      install_requires=required,
      extras_require=extras,
      packages=find_packages())
