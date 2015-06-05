from setuptools import setup

setup(name='tmscoring', version='0.1',
      description='Python implementation of the TMscore program',
      url='',
      author='David Men\'endez Hurtado',
      license='BSD 3-clause',
      packages=['tmscoring'],
      requires=['numpy', 'iminuit', 'biopython'],
      test_suite='nose.collector',
      tests_require=['nose']
)