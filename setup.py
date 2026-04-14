from setuptools import setup, find_packages

with open("requirements.txt", "r") as in_file:
    requirements = in_file.readlines()

setup(
    name='thsr-ticket',
    version='2.0.0',
    description='A modular automatic booking program for Taiwan High Speed Railway (THSR) with CLI and Web interfaces.',
    long_description=open('README.md', 'r', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='BreezeWhite',
    author_email='miyashita2010@tuta.io',
    url='https://github.com/BreezeWhite/THSR-Ticket',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={'console_scripts': ['thsr-ticket = src.main:main']},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Browsers',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.8',
    keywords='taiwan high speed rail thsr booking automation cli web',
    project_urls={
        'Bug Reports': 'https://github.com/BreezeWhite/THSR-Ticket/issues',
        'Source': 'https://github.com/BreezeWhite/THSR-Ticket',
    },
)
