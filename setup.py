# -*- coding: utf8 -*-
from setuptools import setup

setup(name='tmscoring', version='0.1',
      description='Python implementation of the TMscore program',
      url='https://github.com/Dapid/tmscoring',
      author='David Menéndez Hurtado',
      author_email='davidmenhur@gmail.com',
      license='BSD 3-clause',
      packages=['tmscoring'],
      requires=['numpy', 'iminuit', 'biopython'],
      test_suite='nose.collector',
      tests_require=['nose'],
      classifiers=['Programming Language :: Python',
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Cython',
                   'Programming Language :: Python :: Implementation :: CPython',
                   'Topic :: Scientific/Engineering :: Bio-Informatics',
                   'Intended Audience :: Science/Research',
                   'Development Status :: 3 - Alpha',
                   'License :: OSI Approved :: BSD License']
)