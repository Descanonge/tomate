
from setuptools import setup, find_packages
from os import path


here = path.abspath(path.dirname(__file__))


def get_long_description(rel_path):
    with open(path.join(here, rel_path)) as file:
        return file.read()


def get_version(rel_path):
    with open(path.join(here, rel_path)) as file:
        lines = file.read().splitlines()
    for line in lines:
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


required = ['numpy']

extras = {
    "time": ["cftime>=1.1.3"],
    "netcdf": ["netCDF4"],
    "plot": ["matplotlib"],
    "compute": ["scipy"],
}


setup(name='tomate-data',
      version=get_version('src/tomate/__init__.py'),
      description='Tool to manipulate and aggregate data',

      long_description=get_long_description('README.md'),
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

      package_dir={'': 'src'},
      packages=find_packages(where='src'),
      )
