from distutils.core import setup
import glob

setup(name='mash',
      version='0.6.19',
      description='Build system -> repository tool',
      author='Dennis Gilmore',
      author_email='dennis@ausil.us',
      url='https://pagure.io/mash',
      license='GPLv2',
      packages=['mash'],
      scripts=['mash.py'],
      data_files=[('/etc/mash', glob.glob('configs/*')),
                  ('/usr/share/mash', glob.glob('utils/*'))]
      )
