from setuptools import setup

with open('README.md', 'r') as f:
  long_description = f.read()

requirements = list(map(lambda line: line.rstrip("\n"), open('requirements.txt', 'r')))

setup(
  name='ncaa_hoops_pbp',
  version='1.0.0',
  description="Small Package to Extract NCAA Men's and Women's Basketball Play-by-Play Data, and Optionally Extract On-Off Splits",
  license="MIT",
  author="Nick Kalinowski (@kalidrafts on X and Bluesky)
  long_description=long_description,
  packages=[
    'ncaa_hoops_pbp',
    'ncaa_hoops_pbp.scripts'
  ]
  install_requires=requirements,
)
