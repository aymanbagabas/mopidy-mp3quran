#!/usr/bin/env python2

from __future__ import absolute_import, unicode_literals

import re
from setuptools import setup, find_packages

def get_version(filename):
    content = open(filename).read()
    metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", content))
    return metadata['version']


setup(
    name='Mopidy-Mp3Quran',
    version=get_version('mopidy_mp3quran/__init__.py'),
    url='https://github.com/aymanbagabas/mopidy-mp3quran',
    license='Apache License, Version 2.0',
    author='Ayman Bagabas',
    author_email='ayman.bagabas@gmail.com',
    description='Very short description',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*', 'test.py']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 0.14',
        'Pykka >= 1.1',
        'requests'
    ],
    entry_points={
        'mopidy.ext': [
            'mp3quran = mopidy_mp3quran:Extension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
