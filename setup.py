from distutils.core import setup
import glob

setup(name='mash',
      version='0.1.1',
      description='Build system -> repository tool',
      author='Bill Nottingham',
      author_email='notting@redhat.com',
      url='http://move/along/nothing/to/see/here/',
      license='GPL',
      packages=['mash'],
      scripts = ['mash.py'],
      data_files=[('/etc/mash', glob.glob('configs/*'))]
      )

