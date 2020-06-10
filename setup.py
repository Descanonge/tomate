
from setuptools import setup, find_packages

import tomate


with open('README.md') as file:
    long_description = file.read()


required = ['numpy']

extras = {
    "Time": ["cftime>=1.1.3"],
    "NetCDF": ["netCDF4"],
    "Plot": ["matplotlib"],
    "Compute": ["scipy"],
}


setup(name='tomate-data',
      version=tomate.__version__,
      description='Tool to manipulate and aggregate data',

      long_description=long_description,
      long_description_content_type='text/markdown',
      keywords='data manipulate coordinate file netcdf load',

      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
      ],

      url='http://github.com/Descanonge/tomate',
      project_urls={
          'Documentation': 'https://tomate.readthedocs.org',
          'Source': 'https://github.com/Descanonge/tomate'
      },

      author='Clément HAËCK',
      author_email='clement.haeck@posteo.net',

      python_requires='>=3.7',
      install_requires=required,
      extras_require=extras,
      packages=find_packages(),
      )
