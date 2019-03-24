"""A setuptools based setup module."""

from setuptools import setup, find_packages

print(find_packages())
setup(
    name='PY_Sinope',
    version='0.1.0',
    description='python API for Sinopé devices',
    long_description='python API for Sinopé devices: thermostats, ligth, dimmer and power switch'
                     '(https://sinopetech.com). Requires Python 3.4+',
    url='https://github.com/claudegel/sinope-1',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='Sinope, Neviweb',
    install_requires=['aiohttp'],
    zip_safe=True,
    author='Claude Gelinas',
    author_email='claudegel@users.noreply.github.com',
    packages=find_packages()
)