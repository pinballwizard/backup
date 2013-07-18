#!/usr/bin/env python
""" Setup file for Backup package """
 
from distutils.core import setup
setup(name=u'Backup',
      version=u'0.1',
      description=u'Backup package',
      long_description = u"Backup makes a backup for server",
      author=u'Karbovnichiy Vasiliy',
      author_email=u'menstenebris@gmail.com',
      url='http://example.com/',
      packages=['modules'],
      package_dir={'modules':'/home/backup/modules/'},
      scripts=['script/main.py'],
      script_dir={'script/main.py':'/home/backup/script/'},
 
      classifiers=(
          'Development Status :: Pre-Beta',
          'Environment :: Console',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: POSIX',
          'Operating System :: Unix',
          'Programming Language :: Python 2.7',
        ),
      license="GPL-2"
     )