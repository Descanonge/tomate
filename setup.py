
from setuptools import setup


with open('README.rst') as file:
    long_description = file.read()


setup(name='data_loader',
      version='0.2',
      description='Load data from a multitude of files.',
      long_description=long_description,
      keywords='data file netcdf load',
      url='http://github.com/Descanonges/data-loader',
      author='Clément HAËCK',
      author_email='clement.haeck@posteo.net',
      license='',
      install_requires=['mypack-descanonges @ git+git://github.com/Descanonges/myPack.git'],
      packages=['data_loader'])
