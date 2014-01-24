from setuptools import setup, find_packages
from itc.core import __version__

setup(name = "itc.cli",
      version = __version__,
      author = 'Pavel Mazurin',
      author_email = 'me@kovpas.ru',
      description = 'iTunesConnect command line interface.',
      license='MIT',
      url = 'https://github.com/kovpas/itc.cli',
      packages = find_packages(),
      install_requires = ['requests==0.14.2', 'lxml', 'html5lib', 'docopt==0.6.1', 'beautifulsoup4==4.2.1', 'keyring==3.3'],
      scripts = ['itc/bin/itc'],
      include_package_data = True,
      zip_safe = False,
      classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
    ],
)

