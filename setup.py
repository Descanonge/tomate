
from setuptools import setup, find_packages

import tomate


with open('README.rst') as file:
    long_description = file.read()


required = ['numpy']

extras = {
    "Mask": ["scipy"],
    "NetCDF": ["netCDF4"],
    "Time": ["cftime>=1.3.3"],
    "Plot": ["matplotlib"]
}


setup(name='tomate-data',
      version=tomate.__version__,
      description='Tool to manipulate and aggregate data',

      long_description=long_description,
      long_description_content_type='text/x-rst',
      keywords='data manipulate coordinate file netcdf load',

      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Science/Research,'
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
      ],

      url='http://github.com/Descanonge/tomate',
      project_urls={
          'Documentation': 'http'
      },

      author='Clément HAËCK',
      author_email='clement.haeck@posteo.net',

      python_requires='>=3.7',
      install_requires=required,
      extras_require=extras,
      packages=find_packages(),
      )
