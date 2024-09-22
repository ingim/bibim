# setup.py

from setuptools import setup

setup(
    name='bibim',
    version='0.1.0',
    description='A simple command-line tool for managing computer science bibliography.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='In Gim',
    author_email='in.gim@yale.edu',
    url='https://github.com/ingim/bibim',
    py_modules=['bibim'],
    install_requires=[
        'requests',
        'scholarly',
        'openai',
        'feedparser'
    ],
    entry_points={
        'console_scripts': [
            'bibim = bibim.__main__:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    keywords='bibliography bibtex markdown command-line',
    python_requires='>=3.8',
)
