from setuptools import setup, find_packages

setup(name = "itc.cli",
      version = "0.4.3",
      author = 'Pavel Mazurin',
      author_email = 'me@kovpas.ru',
      description = 'iTunesConnect command line interface.',
      url = 'https://github.com/kovpas/itc.cli',
      packages = find_packages(),
      package_data = {'itc.util': ['languages.json']},
      install_requires = ['requests==0.14.2', 'lxml', 'html5lib', 'docopt==0.6.1', 'beautifulsoup4==4.2.1'],
      scripts = ['itc/bin/itc'],
      include_package_data = True,
      zip_safe = False,
)

