import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = 'SimpleReport',
    version = '1.0.0',
    author = 'Nguyễn Tôn Lễ. Mobile: 0944200173',
    author_email = 'ngtonle@gmail.com',
    description = ('Build report from xml template with database SQLite3'),
    long_description=read('README.md'),
    license = 'No License',
    keywords = 'SimpleReport build fpdf xml SQLite ',
    url = 'https://github.com/simplereport/xmltemplate',
    packages=["",'scr'],
    install_requires=[
        'fpdf','html.parser','HTMLParser'
    ],
    tests_require=[
        'einvoice.db', 'fpdfsample.xml'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Networking',
    ],
)
