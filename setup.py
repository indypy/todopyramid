import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid==1.4.3',
    'SQLAlchemy',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'waitress',
    'deform<=1.999',
    'deform_bootstrap==0.2.8',
    'deform_bootstrap_extra==0.2.8',
    'pyramid_persona',
    'WebHelpers',
    'pytz',
    'requests==1.1.0'
]

setup(
    name='todopyramid',
    version='1.0',
    description='todopyramid',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web wsgi pylons pyramid',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='todopyramid',
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = todopyramid:main
    [console_scripts]
    initialize_todopyramid_db = todopyramid.scripts.initializedb:main
    """,
)
