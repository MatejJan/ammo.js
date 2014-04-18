#!/usr/bin/python

import os, sys, re, json, shutil
from subprocess import Popen, PIPE, STDOUT

# Startup

exec(open(os.path.expanduser('~/.emscripten'), 'r').read())

try:
  EMSCRIPTEN_ROOT
except:
  print "ERROR: Missing EMSCRIPTEN_ROOT (which should be equal to emscripten's root dir) in ~/.emscripten"
  sys.exit(1)

sys.path.append(EMSCRIPTEN_ROOT)
import tools.shared as emscripten

# Settings

'''
          Settings.INLINING_LIMIT = 0
          Settings.DOUBLE_MODE = 0
          Settings.PRECISE_I64_MATH = 0
          Settings.CORRECT_SIGNS = 0
          Settings.CORRECT_OVERFLOWS = 0
          Settings.CORRECT_ROUNDINGS = 0
'''
#emcc_args = sys.argv[1:] or '-O3 --closure 0 -s DOUBLE_MODE=1 -s CORRECT_SIGNS=1 -s INLINING_LIMIT=0'.split(' ')
emcc_args = sys.argv[1:] or '-O2 --llvm-lto 1 -s DOUBLE_MODE=0 -s PRECISE_I64_MATH=0 -s ASM_JS=1'.split(' ')

emcc_args += ['-s', 'TOTAL_MEMORY=%d' % (64*1024*1024)] # default 64MB. Compile with ALLOW_MEMORY_GROWTH if you want a growable heap (slower though).

print
print '--------------------------------------------------'
print 'Building ammo.js, build type:', emcc_args
print '--------------------------------------------------'
print

'''
import os, sys, re

infile = open(sys.argv[1], 'r').read()
outfile = open(sys.argv[2], 'w')

t1 = infile
while True:
  t2 = re.sub(r'\(\n?!\n?1\n?\+\n?\(\n?!\n?1\n?\+\n?(\w)\n?\)\n?\)', lambda m: '(!1+' + m.group(1) + ')', t1)
  print len(infile), len(t2)
  if t1 == t2: break
  t1 = t2

outfile.write(t2)
'''

# Utilities

stage_counter = 0
def stage(text):
  global stage_counter
  stage_counter += 1
  text = 'Stage %d: %s' % (stage_counter, text)
  print
  print '=' * len(text)
  print text
  print '=' * len(text)
  print

# Main

try:
  this_dir = os.getcwd()
  os.chdir('bullet')
  if not os.path.exists('build'):
    os.makedirs('build')
  os.chdir('build')

  stage('Generate bindings')

  Popen([emscripten.PYTHON, os.path.join(EMSCRIPTEN_ROOT, 'tools', 'webidl_binder.py'), os.path.join(this_dir, 'ammo.idl'), 'glue']).communicate()
  assert os.path.exists('glue.js')
  assert os.path.exists('glue.cpp')

  stage('Build bindings')

  emscripten.Building.make([emscripten.EMCC, '-I../src', '-include', 'btBulletDynamicsCommon.h', 'glue.cpp', '-c', '-o', 'glue.bc'])
  assert(os.path.exists('glue.bc'))

  if not os.path.exists('config.h'):
    stage('Configure (if this fails, run autogen.sh in bullet/ first)')

    emscripten.Building.configure(['../configure', '--disable-demos','--disable-dependency-tracking'])

  stage('Make')

  emscripten.Building.make(['make', '-j'])

  stage('Link')

  emscripten.Building.link([
                            'glue.bc',
                            os.path.join('src', '.libs', 'libBulletDynamics.a'),
                            os.path.join('src', '.libs', 'libBulletCollision.a'),
                            os.path.join('src', '.libs', 'libLinearMath.a')
                           ],
                           'libbullet.bc')
  assert os.path.exists('libbullet.bc'), 'Failed to create client'

  1/0

  stage('emcc: ' + ' '.join(emcc_args))

  emscripten.Building.emcc('libbullet.bc', emcc_args + ['--js-transform', 'python %s' % os.path.join('..', '..', 'bundle.py')],
                           os.path.join('..', '..', 'builds', 'ammo.js'))

  assert os.path.exists(os.path.join('..', '..', 'builds', 'ammo.js')), 'Failed to create script code'

finally:
  os.chdir(this_dir);

