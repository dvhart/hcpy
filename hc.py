#!/usr/bin/env python
# :exec set tabstop=4 softtab expandtab encoding=utf8 :

'''
Provide the basic calculational engine for the calculator.

$Id: hc.py 1.87 2009/03/17 18:54:09 donp Exp $

---------------------------------------------------------------------------
Copyright (c) 2009, Don Peterson
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above
copyright notice, this list of conditions and the following
disclaimer in the documentation and/or other materials provided
with the distribution.
* Neither the name of the <ORGANIZATION> nor the names of its
contributors may be used to endorse or promote products derived
from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

#----------------------------------
# Python library stuff
import sys, getopt
import readline
from string import strip
from os import remove, system, urandom, environ
import os.path
from textwrap import wrap
from traceback import extract_stack
from tempfile import mkstemp

try: from pdb import xx  # pdb.set_trace is xx; easy to find for debugging
except: pass

#----------------------------------
# Modules we are dependent on
try:
    import mpmath as m
except ImportError:
    print '''This package is dependent on the mpmath module for its arithmetic
facilities.  You can download it from:
    http://code.google.com/p/mpmath/
This package was developed and tested with mpmath version 0.10.'''
    exit(1)

#----------------------------------
# Modules needed in our package
from rational import Rational
from convert import *
from cmddecod import CommandDecode
from stack import Stack
from number import Number
from helpinfo import helpinfo
from mpformat import mpFormat
from integer import Zn
from julian import Julian
from debug import fln, toggle_debug, get_debug
# You may create your own display (GUI, curses, etc.) by derivation.  The
# default Display object just prints to stdout and should work with any
# console.
from display import Display

#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
# Global variables
display = Display()     # Used to display messages to user
stack = Stack()         # Keeps all number objects
fp = mpFormat()         # For formatting floating point numbers
ap = mpFormat()         # For formatting arguments of complex numbers
registers = {}          # Keeps all stored registers
out = sys.stdout.write
err = sys.stderr.write
nl = "\n"
stdin_finished = False  # Flags when stdin has reached EOF
comment_line = "\xec\xeb"
eof = "\xed\xee"
argument_types = "%sThe two arguments must be the same type"
factorial_cache = {0:1, 1:1, 2:2}
process_stdin = False   # -s If true, our input comes from stdin
run_checks = False      # -c Run checks
quiet = False           # -q If true, don't print initial message
testing = False         # -t If true, exit with nonzero status if x!=y
tee_is_on = False       # True when logging to a file
use_default_config_only = False

# Status numbers that can be returned
status_ok               = 0
status_quit             = 1
status_error            = 2
status_unknown_command  = 3
status_ok_no_display    = 4
status_interrupted      = 5

# Used for binary conversions
hexdigits = {
    "0" : "0000", "1" : "0001", "2" : "0010", "3" : "0011", "4" : "0100",
    "5" : "0101", "6" : "0110", "7" : "0111", "8" : "1000", "9" : "1001",
    "a" : "1010", "b" : "1011", "c" : "1100", "d" : "1101", "e" : "1110",
    "f" : "1111"}

#---------------------------------------------------------------------------
# Configuration information.

cfg = {
    # If any of these environment variables exist, execute the
    # commands in them.
    "environment" : ["HCPYINIT", "hcpyinit"],

    # Angle mode:  must be either 'deg' or 'rad'
    "angle_mode" : "deg",

    # Integer mode: must be 'dec', 'hex', 'oct', or 'bin'.
    "integer_mode" : "dec",

    # Prompt to be displayed for each input (may be empty)
    "prompt" : "> ",

    # If true, coerce means to change arguments' types as needed to
    # calculate a function.  Otherwise, a ValueError exception will be
    # thrown.
    "coerce" : True,

    # If true, we'll allow x/0 to be infinity as long as x != 0
    "allow_divide_by_zero" : True,

    # The calculator is capable of handling rational numbers.  If
    # you'd rather a division of two integers result in a real number,
    # set no_rationals to True.  The rat command toggles this setting.
    "no_rationals" : True,

    # For display of complex numbers.  Mode is either rect or polar.
    "imaginary_mode" : "rect",
    "imaginary_unit" : "i",
    "imaginary_unit_first" : False,  # If true, 1+i3
    "imaginary_space" : True,        # If true, 1 + 3i or (1, 3)
    "ordered_pair" : False,          # If true, (1,3)
    "polar_separator" : " <| ",      # Used in polar display
    "degree_symbol" : "deg",         # chr(248) might be OK for cygwin bash
    "infinity_symbol" : "inf",       # chr(236) might be OK for cygwin bash
    "arg_digits" : 2,                # Separate formatting num digits for args
    "arg_format" : "fix",            # Separate formatting type for arguments

    # Factorials of integers <= this number are calculated exactly.
    # Otherwise, the mpmath factorial function is used which returns either
    # an mpf or mpc.  Set to zero if you want all factorials to be
    # calculated exactly (warning:  this can result in long calculation
    # times and lots of digits being printed).
    "factorial_limit" : 20001,

    # The following string is used to separate commands on the command
    # input.  If this string is not in the command line, the command is
    # parsed into separate commands based on whitespace.
    "command_separator" : ";",

    # Editor to use for viewing/changing files.  The temporary file is
    # used with the editor.  If you wish to have the program use the
    # tempfile standard library feature, leave tempfile as the empty
    # string.
    "editor" : "d:/bin/vim/vim71/vim.exe",
    "tempfile" : "",
    # How many items of the stack to show.  Use 0 for all.
    "stack_display" : 0,

    # If the following variable is True, we will persist our settings from
    # run to run.  Otherwise, our configuration comes from this dictionary
    # and the stack and registers are empty when starting.
    "persist" : False,

    # Name of files to persist our configuration, stack, and registers to.
    # If None, there will be no persistence of the objects.  If set to a
    # file name which contains no '/' characters, then the indicated object
    # will be persisted to that file in the same directory where the
    # executable is.  Otherwise, make sure it is a full path name.
    "config_file" :           "",
    "config_save_registers" : "",
    "config_save_stack" :     "",

    # The following variables determines how floating point numbers are
    # formatted. Legitimate values are:  fix for fixed, sig for significant
    # figures, sci for scientific, eng for engineering, engsi for
    # engineering with SI prefixes after the number, and "none".  If
    # "none", then the default mpmath string representation is used.
    # Change the mpformat.py file if you wish to change things such as
    # decimal point type, comma decoration, etc.
    #
    # NOTE:  there are mpFormat class variables in mpformat.py that you
    # might want to examine and set to your tastes.  They are not included
    # here because they will probably be set only once by a user.
    "fp_format" : "sig",
    "fp_digits" : 3,
    "fp_show_plus_sign" : False,  # If true, "+3.4" instead of " 3.4"
    "fp_comma_decorate" : True,   # If true, 1,234 instead of 1234
    "fp_cuddle_si" : False,       # If true, "12.3k" instead of "12.3 k"

    # Set how many digits of precision the mpmath library should use.
    "prec" : 30,

    # Settings for interval number display.  iva mode is a+-b; ivb mode is
    # a(b%); ivc mode is <a, b>.
    "iv_space" : True,              # a +- b vs. a+-b, a (b%) vs a(b%)
    "iv_mode" : "b",
    "iv_brackets" : ("<", ">"),     # <a, b>

    # If brief is set to true, truncate numbers to fit on one line.
    "brief" : True,

    # Set the line width for the display.  Set it to a negative integer to
    # instruct the program to try to first read the value from the COLUMNS
    # environment variable; if not present, it will use the absolute value.
    "line_width" : 75,

    # String to use when an ellipsis is needed (used by brief command)
    "ellipsis" : "."*3,

    # If true, display fractions as mixed fractions.
    "mixed_fractions" : True,

    # If this number is not 1, then it is used for modular arithmetic.
    "modulus" : 1,

    # If this is true, then results are downcast to simpler types.
    # Warning:  this may cause suprises.  For example, if prec is set to 15
    # and you execute 'pi 1e100 *', you'll see an integer result.  This
    # isn't a bug, but is a consequence of the finite number of digits of
    # precision -- the downcast happens because int(1e100*pi) == 1e100*pi.
    "downcasting" : False,

    # The integers used by this program exhibit python-style division.
    # This behavior can be surprising to a C programmer, because in
    # python, (-3) // 8 is equal to -1 (this is called floor division);
    # most C programmers would expect this to be zero.  Set the
    # following variable to True if you want (-3) // 8 to be zero.
    "C_division" : True,

    # Scripts that can be called using the ! command are in the following
    # directory.  Any python script in this directory will have its main()
    # function called and the value that is returned will be pushed on the
    # stack.  This lets you write auxiliary scripts that prompt you to help
    # you get a number you need without cluttering up the commands or
    # registers of this program.  Example:  an astronomy.py script could
    # prompt you for which astronomical constant you wanted to use.  Set
    # this entry to the empty string or None if you don't want this
    # behavior.  You can also give the name of the function you want to
    # be called.  This function will be called with the display object,
    # which you can use to send messages to the user.
    "helper_scripts" : "d:/p/math/hcpy/helpers",
    "helper_script_function_name" : "main",
}

cfg_default = {}
cfg_default.update(cfg)

#---------------------------------------------------------------------------
# Utility functions

def isint(x):
    return isinstance(x, int) or isinstance(x, long) or isinstance(x, Zn)

def use_modular_arithmetic(x, y):
    return (isint(x) and isint(y) and abs(cfg["modulus"]) > 1)

def TypeCheck(x, y):
    if (not cfg["coerce"]) and (type(x) != type(y)):
        raise ValueError(argument_types % fln())

def DownCast(x):
    '''If x can be converted to an integer with no loss of information,
    do so.  If its a complex that can be converted to a real, do so.
    '''
    if cfg["downcasting"] == False:
        return x
    if x == inf or x == -inf:
        return x
    elif isinstance(x, Rational):
        if x.d == 1:
            return x.n
    elif isinstance(x, m.mpf):
        if int(x) == x:
            return int(x)
    elif isinstance(x, m.mpc):
        if x.imag == 0:
            x = x.real
            if int(x) == x:
                return int(x)
    return x

def Conv2Deg():
    '''Routine to convert the top of the stack element to degrees.  This
    is typically done after calling inverse trig functions.
    '''
    try:
        if cfg["angle_mode"] == "deg":
            x = stack.pop()
            if isinstance(x, Zn):
                x = int(x)
            elif isinstance(x, m.mpc):  # Don't change complex numbers
                stack.push(x)
                return
            stack.push(x*180/pi)
    except:
        raise ValueError("%sx can't be converted from radians to degrees" % fln())

def Conv2Rad():
    '''Routine to convert the top of the stack element to radians.  This
    is typically done before calling trig functions.
    '''
    try:
        if cfg["angle_mode"] == "deg":
            x = stack.pop()
            if isinstance(x, Zn):
                x = int(x)
            elif isinstance(x, m.mpc):  # Don't change complex numbers
                stack.push(x)
                return
            stack.push(x*pi/180)
    except:
        raise ValueError("%sx can't be converted from degrees to radians" % fln())

#---------------------------------------------------------------------------
# Binary functions

def add(x, y):
    if use_modular_arithmetic(x, y):
        return (x + y) % cfg["modulus"]
    TypeCheck(x, y)
    try:
        return x + y
    except:
        return y + x

def subtract(x, y):
    if use_modular_arithmetic(x, y):
        return (x - y) % cfg["modulus"]
    TypeCheck(x, y)
    try:
        return x - y
    except:
        return -y + x

def multiply(x, y):
    if use_modular_arithmetic(x, y):
        return (x*y) % cfg["modulus"]
    TypeCheck(x, y)
    try:
        return x*y
    except:
        return y*x

def divide(x, y):
    if use_modular_arithmetic(x, y):
        return (x//y) % cfg["modulus"]
    TypeCheck(x, y)
    if y == 0:
        if cfg["allow_divide_by_zero"]:
            if x > 0:
                return m.inf
            elif x < 0:
                return -m.inf
            else:
                raise ValueError("%s0/0 is ambiguous" % fln())
        else:
            raise ValueError("%sCan't divide by zero" % fln())
    if isint(x) and isint(y):
        if cfg["no_rationals"]:
            return mpf(x)/mpf(y)
        else:
            q = Rational(int(x), int(y))
            if q.d == 1:
                return q.n
            else:
                return q
    try:
        return x/y
    except:
        return (1/y)*x

def Mod(n, d):
    TypeCheck(n, d)
    if isint(n) and isint(d):
        return Zn(n) % Zn(d)
    if isinstance(n, Zn): n = n.value
    if isinstance(d, Zn): d = d.value
    n = Convert(n, MPF)
    d = Convert(d, MPF)
    result = m.modf(n, d)
    if int(result) == result:
        result = Zn(int(result))
    return result

def integer_divide(n, d):
    if use_modular_arithmetic(n, d):
        return (Zn(n)//Zn(d)) % cfg["modulus"]
    TypeCheck(n, d)
    if isint(n) and isint(d):
        return Zn(n) // Zn(d)
    n   = Convert(n, MPF)
    d = Convert(d, MPF)
    return int(m.floor(n/d))

def bit_and(x, y):
    TypeCheck(x, y)
    if isint(x) and isint(y):
        return Zn(x) & Zn(y)
    x = Convert(x, INT)
    y = Convert(y, INT)
    return x & y

def bit_or(x, y):
    TypeCheck(x, y)
    if isint(x) and isint(y):
        return Zn(x) | Zn(y)
    x = Convert(x, INT)
    y = Convert(y, INT)
    return x | y

def bit_xor(x, y):
    TypeCheck(x, y)
    if isint(x) and isint(y):
        return Zn(x) ^ Zn(y)
    x = Convert(x, INT)
    y = Convert(y, INT)
    return x ^ y

def bit_leftshift(x, y):
    TypeCheck(x, y)
    if isint(x) and isint(y):
        return Zn(x) << Zn(y)
    x = Convert(x, INT)
    y = Convert(y, INT)
    return x << y

def bit_rightshift(x, y):
    TypeCheck(x, y)
    if isint(x) and isint(y):
        return Zn(x) >> Zn(y)
    x = Convert(x, INT)
    y = Convert(y, INT)
    return x >> y

def percent_change(x, y):
    x = Convert(x, MPF)
    y = Convert(y, MPF)
    if x == 0:
        raise ValueError("%sBase is zero for %ch" % fln())
    return 100*(y - x)/x

def combination(x, y):
    if (not cfg["coerce"]) and \
       (not isint(x)) and (not isint(y)):
        raise ValueError(argument_types % fln())
    x = Convert(x, INT)
    y = Convert(y, INT)
    return int(permutation(x, y)//Factorial(y))

def permutation(x, y):
    if (not cfg["coerce"]) and \
       (not isint(x)) and (not isint(y)):
        raise ValueError(argument_types % fln())
    x = Convert(x, INT)
    y = Convert(y, INT)
    return int(Factorial(x)//Factorial(x - y))

def power(x, y):
    return pow(x, y)

#---------------------------------------------------------------------------
# Unary functions

def ip(x):
    if isint(x):
        return x
    return Convert(x, INT)

def Fp(x):
    if isint(x):
        return m.mpf(0)
    return Convert(x, MPF) - ip(x).value

def reciprocal(x):
    if x == 0:
        if cfg["allow_divide_by_zero"]:
            return inf
        else:
            raise ValueError("%sDivision by zero" % fln())
    if isint(x):
        return Rational(1, x)
    elif isinstance(x, Rational):
        return Rational(x.d, x.n)
    return m.mpf(1)/x

def chs(x):
    return -x

def bit_negate(x):
    return ~Convert(x, INT)

def numerator(x):
    return Convert(x, RAT).n

def denominator(x):
    return Convert(x, RAT).d

def apart(x):
    if isinstance(x, mpc):
        return x.real, x.imag
    elif isinstance(x, Rational):
        return x.n, x.d
    elif isinstance(x, mpi):
        return x.a, x.b
    elif isinstance(x, Julian):
        return x.value.a, x.value.b
    else:
        msg = "%sapart requires rational, complex, or interval number"
        raise ValueError(msg % fln())

def ToV(y, x):
    'Convert to interval number [y,x]'
    if y > x:
        msg = "%sy register must be <= x register"
        raise ValueError(msg % fln())
    y = Convert(y, MPF)
    x = Convert(x, MPF)
    return mpi(y, x)

def Chop(x):
    n = Number()
    return n(Format(x).replace(" ", ""))

def RealPart(x):
    if isinstance(x, m.mpc):
        return x.real
    else:
        return x

def ImagPart(x):
    if isinstance(x, m.mpc):
        return x.imag
    else:
        return x

def conj(x):
    if isinstance(x, m.mpc):
        n = Convert(x, MPC)
        return m.mpc(n.real, -n.imag)
    else:
        return x

def square(x): return x*x

def mid(x):
    if isinstance(x, m.mpi):
        return x.mid
    else:
        raise ValueError("%sNeed an interval number for mid" % fln())

def Factorial(x):
    def ExactIntegerFactorial(x):
        if x in factorial_cache:
            return factorial_cache[x]
        else:
            if x > 2:
                y = 1
                for i in xrange(2, x+1):
                    y *= i
                factorial_cache[x] = y
                return y
    limit = cfg["factorial_limit"]
    if limit < 0 or not isint(limit):
        raise SyntaxError("%sFactorial limit needs to be an integer >= 0" % fln())
    if isint(x) and x >= 0:
        if limit == 0 or (limit > 0 and x < limit):
            return ExactIntegerFactorial(x)
    return m.factorial(x)

def Ln2(x):
    return m.ln(x)/m.ln(2)

def ToDegrees(x):
    if x == 0: return x
    if isinstance(x, m.mpc):
        raise ValueError("%sNot an appropriate operation for a complex number" % fln())
    return degrees(x)

def ToRadians(x):
    if x == 0: return x
    if isinstance(x, m.mpc):
        raise ValueError("%sNot an appropriate operation for a complex number" % fln())
    return radians(x)

def Ncdf(x):
    'Normal probability CDF'
    return ncdf(x, 0, 1)

def Incdf(x):
    'Inverse of normal probability CDF'
    if not (0 < x < 1):
        raise ValueError("%sInverse normal CDF requires 0 < argument < 1" % \
            fln())

    if   x < 0.01:  start = mpf("-2.3")
    elif x < 0.05:  start = mpf("-1.64")
    elif x < 0.10:  start = mpf("-1.28")
    elif x < 0.25:  start = mpf("-0.67")
    elif x < 0.50:  start = mpf("0")
    elif x < 0.75:  start = mpf("0.67")
    elif x < 0.90:  start = mpf("1.28")
    elif x < 0.95:  start = mpf("1.64")
    elif x < 0.99:  start = mpf("2.3")
    else:           start = mpf("3")
    y = m.findroot(lambda z: ncdf(z) - x, 0)
    return y

def hr(x):
    'Convert hms to decimal hours'
    x = Convert(x, MPF)
    hours = int(x)
    x -= hours
    x *= 100
    minutes = int(x)
    x -= minutes
    x *= 100
    return hours + minutes/mpf(60) + x/3600

def hms(x):
    'Convert decimal hours to hours.MMSSss'
    x = Convert(x, MPF)
    hours = int(x)
    x -= hours
    x *= 60
    minutes = int(x)
    if minutes == 60:
        hours += 1
        minutes = 0
    x -= minutes
    seconds = 60*x
    if seconds == 60:
        minutes += 1
        seconds = 0
    if minutes == 60:
        hours += 1
        minutes = 0
    return hours + minutes/mpf(100) + seconds/mpf(10000)

def rand():
    '''Return a uniformly-distributed random number in [0, 1).  We use
    the os.urandom function to return a group of random bytes, then convert
    the bytes to a binary fraction expressed in decimal.
    '''
    numbytes = ceil(mp.prec/mpf(8)) + 1
    bytes = urandom(numbytes)
    number = sum([ord(b)*mpf(256)**(-(i+1)) for i, b in enumerate(list(bytes))])
    stack.push(number)

#---------------------------------------------------------------------------
# Other functions

def Modulus(x):
    '''Set up modulus arithmetic with X as the modulus (1 or 0 to cancel)
    '''
    if isinstance(x, m.mpc) or isinstance(x, m.mpi):
        raise ValueError("%sModulus cannot be a complex or interval number" % fln())
    if x == 0:
        cfg["modulus"] = 1
    else:
        cfg["modulus"] = x
    return None

def Rationals(x):
    if x != 0:
        cfg["no_rationals"] = True
    else:
        cfg["no_rationals"] = False

def ToggleDowncasting(x):
    if x != 0:
        cfg["downcasting"] = True
    else:
        cfg["downcasting"] = False

def ClearRegisters():
    global registers
    registers = {}

def Phi():
    stack.push(m.phi)

def ShowConfig():
    d = {True:"on", False:"off"}
    per = d[cfg["persist"]]
    st = str(cfg["stack_display"])
    lw = cfg["line_width"]
    mf = str(cfg["mixed_fractions"])
    dc = d[cfg["downcasting"]]
    sps = d[cfg["fp_show_plus_sign"]]
    am = cfg["angle_mode"]
    im = cfg["integer_mode"]
    imm = cfg["imaginary_mode"]
    sd = str(cfg["stack_display"])
    fmt = cfg["fp_format"]
    dig = str(cfg["fp_digits"])
    ad = str(cfg["arg_digits"])
    af = cfg["arg_format"]
    pr = str(mp.dps)
    br = d[cfg["brief"]]
    nr = d[cfg["no_rationals"]]
    cd = d[cfg["fp_comma_decorate"]]
    adz = d[cfg["allow_divide_by_zero"]]
    iv = cfg["iv_mode"]
    cdiv = d[cfg["C_division"]]
    dbg = d[get_debug()]
    if 1:
        s = '''Configuration:
  Stack:%(st)s    Commas:%(cd)s   +sign:%(sps)s   Allow divide by zero:%(adz)s
  iv%(iv)s    brief:%(br)s  C-type integer division:%(cdiv)s   Rationals:%(nr)s
  Line width:%(lw)s    Mixed fractions:%(mf)s     Downcasting:%(dc)s
  Complex numbers:  %(imm)s    arguments:%(af)s %(ad)s digits Debug:%(dbg)s
  Display: %(fmt)s %(dig)s digits   prec:%(pr)s  Integers:%(im)s  Angles:%(am)s''' \
    % locals()

    display.msg(s)

def quit():
    pass

def Pi():
    print m.mpf(m.mp.pi)
    stack.push(m.mpf(m.mp.pi))

def E():
    stack.push(m.mp.e)

def Enter():
    if stack.size():
        stack.push(stack[0])

def lastx():
    assert stack.lastx != None, "Bug:  stack.lastx is None"
    stack.push(stack.lastx)

def mixed(x):
    if x != 0:
        cfg["mixed_fractions"] = True
        Rational.mixed = True
    else:
        cfg["mixed_fractions"] = False
        Rational.mixed = False

def xch():
    try:
        stack.swap()
    except:
        display.msg("%sStack is not large enough" % fln())

def roll():
    try:
        stack.roll()
    except:
        display.msg("%sStack is not large enough" % fln())

def Del():
    try:
        stack.pop()
    except:
        display.msg("%sStack is empty" % fln())

def Cast(x, newtype, use_prec=False):
    '''If use_prec == True, use mp.dps.
    '''
    try:
        try:
            if use_prec == True:
                digits = 0
            else:
                digits = max(1, fp.num_digits)
        except:
            pass
        return Convert(x, newtype, digits)
    except:
        display.msg("%sCouldn't perform conversion" % fln())
        return None

def Cast_i(x):
    return Cast(x, INT)

def Cast_qq(x):
    return Cast(x, RAT, use_prec=True)

def Cast_q(x):
    return Cast(x, RAT, use_prec=False)

def Cast_r(x):
    return Cast(x, MPF)

def Cast_c(x):
    return Cast(x, MPC)

def Cast_t(x):
    return Cast(x, JUL)

def Cast_v(x):
    return Cast(x, MPI)

def prec(x):
    if isint(x) and x > 0:
        mp.dps = int(x)
        cfg["prec"] = int(x)
        if cfg["fp_digits"] > mp.dps:
            cfg["fp_digits"] = mp.dps
        if fp.num_digits > mp.dps:
            fp.digits(mp.dps)
        return None
    else:
        display.msg("You must supply an integer > 0")
        return x

def digits(x):
    if int(x) == x:
        if x >= 0:
            d = min(int(x), mp.dps)
            cfg["fp_digits"] = d
            fp.digits(min(int(x), mp.dps))
            return None
        else:
            display.msg("Use an integer >= 0")
            return x
    else:
        display.msg("You must supply an integer >= 0")
        return x

def SetStackDisplay(x):
    msg = "Stack display size be an integer >= 0"
    if int(x) == x:
        if x >= 0:
            cfg["stack_display"] = int(x)
            return None
        else:
            display.msg(msg)
            return x
    else:
        display.msg(msg)
        return x

def Round(y, x):
    '''Round y to the nearest x.  Algorithm from PC Magazine, 31Oct1988,
    pg 435.
    '''
    y = Convert(y, MPF)
    x = Convert(x, MPF)
    sgn = 1
    if y < 0: sgn = -1
    return sgn*int(mpf("0.5") + abs(y)/x)*x

def In(y, x):
    '''Both x and y are expected to be interval numbers or x a number and
    y and interval number.  Returns the boolean 'x in y'.
    '''
    msg = "%sy needs to be an interval number or Julian interval"
    if isinstance(y, m.mpi):
        if testing:
            if x not in y:
                s = "x was not in y:" + nl
                s += "  x = " + repr(x) + nl
                s += "  y = " + repr(y)
                display.msg(s)
                exit(1)
        return x in y
    elif isinstance(y, Julian):
        if not isinstance(y.value, m.mpi):
            raise ValueError(msg % fln())
        if testing:
            if x not in y.value:
                s = "x was not in y:" + nl
                s += "  x = " + repr(x) + nl
                s += "  y = " + repr(y.value)
                display.msg(s)
                exit(1)
        if isinstance(x, Julian):
            return x.value in y.value
        else:
            return x in y.value
    else:
        raise ValueError(msg % fln())

#---------------------------------------------------------------------------

def Dummy():
    raise Exception("%sDummy():  shouldn't have executed this function" % fln())

def NotImpl():
    print "Not implemented yet"

def NotImplx(x):
    print "Not implemented yet"
    return x

def Debug(x):
    if x != 0:
        toggle_debug(True)
    else:
        toggle_debug(False)

def Reset():
    ClearRegisters()
    ClearStack()
    cfg.clear()
    cfg.update(cfg_default)
    ConfigChanged()

def Show():
    '''Show the full precision of x.
    '''
    def showx(x, prefix=""):
        if mp.dps < 2:
            return
        sign, mant, exponent = to_digits_exp(x._mpf_, mp.dps)
        s = mant[0] + "." + mant[1:] + "e" + str(exponent)
        if sign ==  -1:
            s = "-" + s
        display.msg(" " + prefix + s)
    from mpmath.libmp.libmpf import to_digits_exp
    x = stack[0]
    if isinstance(x, m.mpf):
        showx(x)
    elif isinstance(x, m.mpc):
        display.msg(" x is complex")
        showx(x.real, "  x.real:  ")
        showx(x.imag, "  x.imag:  ")
    elif isinstance(x, m.mpi):
        display.msg(" x is an interval number")
        showx(x.a, "  x.a:  ")
        showx(x.b, "  x.b:  ")
    # Return False to avoid displaying the stack
    return False

def ClearStack():
    stack.clear_stack()

def comma(x):
    if x != 0:
        cfg["fp_comma_decorate"] = True
    else:
        cfg["fp_comma_decorate"] = False
    mpFormat.comma_decorate = cfg["fp_comma_decorate"]

def width(x):
    if isint(x) and x > 20:
        cfg["line_width"] = int(x)
    else:
        display.msg("width command requires an integer > 20")

def Rectangular():
    cfg["imaginary_mode"] = "rect"

def Polar():
    cfg["imaginary_mode"] = "polar"

def brief(x):
    if x != 0:
        cfg["brief"] = True
    else:
        cfg["brief"] = False

def Flatten(n=0):
    '''The top of the stack contains a sequence of values.  Remove them
    and put them onto the stack.  If n is 0, it means do this with all the
    elements; otherwise, just do it with the left-most n elements and
    discard the rest.
    '''
    assert n >= 0
    if not stack.size():
        return
    items = list(stack.pop())
    if not n:
        n = len(items)
    stack.stack += items[:n]

def ConfigChanged():
    try:
        fp.digits(cfg["fp_digits"])
    except:
        raise ValueError("%s'fp_digits' value in configuration is bad" % fln())
    try:
        ap.digits(cfg["arg_digits"])
    except:
        raise ValueError("%s'arg_digits' value in configuration is bad" % fln())
    mpFormat.comma_decorate = cfg["fp_comma_decorate"]
    mpFormat.cuddle_si = cfg["fp_cuddle_si"]
    mpFormat.explicit_plus_sign = cfg["fp_show_plus_sign"]
    Rational.mixed = cfg["mixed_fractions"]
    Zn().C_division = cfg["C_division"]
    if isint(cfg["prec"]) and int(cfg["prec"]) > 0:
        mp.dps = cfg["prec"]
    else:
        raise ValueError("%s'prec' value in configuration is bad" % fln())

def GetFullPath(s):
    '''If s doesn't have a slash in it, prepend it with the directory where
    our executable is.  If it does have a slash, verify it's usable.
    '''
    if "/" not in s:
        path, file = os.path.split(sys.argv[0])
        return os.path.join(path, s)
    else:
        return os.normalize(s)

def SaveConfiguration():
    if cfg["persist"]:
        c, r, s = cfg["config_file"], cfg["config_save_registers"], \
                  cfg["config_save_stack"]
        msg = "%sCould not write %s to:\n  %s"
        if c:
            try:
                p = GetFullPath(c)
                WriteDictionary(p, "cfg", cfg)
            except:
                display.msg(msg % (fln(), "config", p))
        if r:
            try:
                p = GetFullPath(r)
                WriteDictionary(p, "registers", registers)
            except:
                display.msg(msg % (fln(), "registers", p))
        if s:
            try:
                p = GetFullPath(s)
                WriteList(p, "mystack", stack.stack)
            except:
                display.msg(msg % (fln(), "stack", p))

def GetLineWidth():
    '''Try to get the current console's linewidth by reading the
    COLUMNS environment variable.  If it's present, use it to set
    cfg["line_width"].
    '''
    try:
        cfg["line_width"] = int(environ["COLUMNS"]) - 1
    except:
        pass

def GetConfiguration():
    global cfg
    cf = cfg["config_file"]
    GetLineWidth()
    ConfigChanged()
    us = "Using default configuration"
    if cfg["persist"]:
        c, r, s = cfg["config_file"], cfg["config_save_registers"], \
                  cfg["config_save_stack"]
        if c and not use_default_config_only:
            try:
                d = {}
                p = GetFullPath(c)
                execfile(p, d, d)
                cfg = d["cfg"]
                ConfigChanged()
            except:
                msg = "%sCould not read and execute configuration file:" % fln() + \
                      nl + "  " + c
                display.msg(msg)
                display.msg(us)
        if r:
            try:
                d = {}
                p = GetFullPath(r)
                execfile(p, d, d)
                global registers
                registers = d["registers"]
            except:
                msg = "%sCould not read and execute register file:"  % fln() + \
                      nl + "  " + r
                display.msg(msg)
        if s:
            try:
                d = {}
                p = GetFullPath(s)
                execfile(p, d, d)
                global stack
                stack.stack = d["mystack"]
            except:
                msg = "%sCould not read and execute stack file:" % fln() + \
                      nl + "  " + s
                display.msg(msg)

def Help(cmd, commands_dict):
    assert cmd[0] == "?"
    if len(cmd) > 1:
        # Asked for help on a certain topic
        try:
            topic = cmd[1:]
            c = CommandDecode(commands_dict)
            x = c.identify_cmd(cmd[1:])
            if type(x) == type(""):
                display.msg(nl.join(wrap(helpinfo[x])))
            else:
                raise Exception()
        except:
            display.msg("%sNo help on '%s'" % (fln(), topic))
    else:
        keys = commands_dict.keys()
        keys.sort()
        indent = "  "
        t = indent

        s = "List of commands (use ?cmd for details):\n"
        width = cfg["line_width"]
        for key in keys:
            if len(t) + len(key) + 1 >= width:
                s += t + nl
                t = indent + key + " "
            else:
                t += key + " "
        if t: s += t
        display.msg(s)

def DisplayStack(display, stack):
    size = cfg["stack_display"]
    assert size >= 0 and isint(size)
    display.msg(stack._string(Format, size))
    if cfg["modulus"] != 1:
        display.msg(" (mod " + Format(cfg["modulus"])+ ")")

def EllipsizeString(s, desired_length, ellipsis):
    '''Remove characters out of the middle of s until the length of s
    with the ellipsis inserted is <= the desired length.  Note:  the
    string returned will be of length desired_length or one less.
    '''
    had_exponent = "e" in s or "E" in s
    had_dp = "." in s
    if len(s) <= desired_length:
        return s
    if len(s) < desired_length - len(ellipsis) + 3:
        raise Exception("%sProgram bug:  string too short" % fln())
    left, right = s[:len(s)//2], s[len(s)//2:]
    while len(left) + len(right) + len(ellipsis) > desired_length:
        try:
            left = left[:-1]
            right = right[1:]
        except:
            raise Exception("%sProgram bug:  string too short" % fln())
    new_s = left + ellipsis + right
    chopped_exponent = had_exponent and ("E" not in new_s and "e" not in new_s)
    chopped_dp = had_dp and "." not in new_s
    if chopped_exponent or chopped_dp:
        display.msg("Warning:  floating point number was 'damaged' by inserting ellipsis")
    return new_s

def Format(x):
    '''Format the four different types of numbers.  Return a string in
    the proper format.
    '''
    width = abs(cfg["line_width"])
    brief = cfg["brief"]
    e = cfg["ellipsis"]
    im = cfg["integer_mode"]
    stack_header_allowance = 5
    if isint(x):
        if isinstance(x, int) or isinstance(x, long):
            x = Zn(x)
        if im == "dec":
            s = str(x)
        elif im == "hex":
            s = hex(x)
        elif im == "oct":
            s = oct(x)
        elif im == "bin":
            s = x.bin()
        else:
            raise Exception("%s'%s' integer mode is unrecognized" % (im, fln()))
        # Prepend a space or + if this is being done in the mpFormat
        # object.  This is a hack; eventually, there will be a single
        # number object where the formatting is handled.
        if x >= Zn(0):
            if mpFormat.implicit_plus_sign == True:  sign = " "
            if mpFormat.explicit_plus_sign == True:  sign = "+"
            s = sign + s
        if s[-1] == "L": s = s[:-1]  # Handle old python longs
        if brief:
            s = EllipsizeString(s, width - stack_header_allowance, e)
        return s
    elif isinstance(x, Rational):
        s = str(x)
        if x >= Rational(0):
            if mpFormat.implicit_plus_sign == True:  sign = " "
            if mpFormat.explicit_plus_sign == True:  sign = "+"
            s = sign + s
        if len(s) > width//2:
            s = s.replace("/", " / ") # Makes / easier to see
        if brief:
            size = (width - stack_header_allowance)//2 - 1
            s = EllipsizeString(s, size, e)
        return s
    elif isinstance(x, mpf):
        s = str(x)
        if cfg["fp_format"] != "none":
            s = fp.format(x, cfg["fp_format"])
        if brief:
            s = EllipsizeString(s, width - stack_header_allowance, e)
        return s
    elif isinstance(x, mpc):
        space = cfg["imaginary_space"]
        s = ""
        if space:
            s = " "
        sre = str(x.real)
        sim = str(abs(x.imag))
        if cfg["fp_format"] != "none":
            sre = fp.format(x.real, cfg["fp_format"])
            sim = fp.format(abs(x.imag), cfg["fp_format"]).strip()
        if cfg["ordered_pair"]:
            if brief:
                size = (width - stack_header_allowance)//2 - 4
                sre = EllipsizeString(sre, size, e).strip()
                sim = EllipsizeString(sim, size, e)
            s = "(" + sre + "," + s + sim + ")"
        else:
            mode = cfg["imaginary_mode"]
            first = cfg["imaginary_unit_first"]
            unit = cfg["imaginary_unit"]
            if mode == "polar":
                # Polar mode
                sep = cfg["polar_separator"]
                angle_mode = cfg["angle_mode"]
                mag = abs(x)
                ang = arg(x)
                if angle_mode == "deg":
                    ang_sym = cfg["degree_symbol"]
                    ang *= 180/pi
                else:
                    ang_sym = "rad"
                if angle_mode != "deg" and angle_mode != "rad":
                    display.msg("Warning:  bad angle_mode('%s') in configuration" \
                        % angle_mode)
                m = str(mag)
                a = str(ang)
                if cfg["fp_format"] != "none":
                    m = fp.format(mag, cfg["fp_format"])
                    a = ap.format(ang, cfg["arg_format"])
                if brief:
                    size = (width - stack_header_allowance)//2 - \
                           len(sep) - 4
                    mag = EllipsizeString(m, size, e)
                    ang = EllipsizeString(a, size, e)
                s = m + cfg["polar_separator"] + a + " " + ang_sym
            else:
                # Rectangular mode
                if brief:
                    size = (width - stack_header_allowance)//2 - 1
                    sre = EllipsizeString(sre, size, e)
                    sim = EllipsizeString(sim, size, e)
                if x.real == 0:
                    # Pure imaginary
                    sign = ""
                    if mpFormat.implicit_plus_sign == True:  sign = " "
                    if mpFormat.explicit_plus_sign == True:  sign = "+"
                    if x.imag < 0:
                        if x.imag == -1:
                            s = "-" + unit
                        else:
                            if first:
                                s = "-" + unit + sim
                            else:
                                s = "-" + sim + unit
                    elif x.imag == 0:
                        s = sign + sre
                    else:
                        if x.imag == 1:
                            s = sign + unit
                        else:
                            if first:
                                s = sign + unit + sim
                            else:
                                s = sign + sim + unit
                else:
                    if x.imag < 0:
                        if space:
                            if first:
                                s = sre + s + "-" + s + unit + sim
                            else:
                                s = sre + s + "-" + s + sim + unit
                        else:
                            if first:
                                s = sre + "-" + unit + sim
                            else:
                                s = sre + "-" + sim + unit
                    elif x.imag == 0:
                        s = sre
                    else:
                        if space:
                            if first:
                                s = sre + s + "+" + s + unit + sim
                            else:
                                s = sre + s + "+" + s + sim + unit
                        else:
                            if first:
                                s = sre + "+" + unit + sim
                            else:
                                s = sre + "+" + sim + unit
            if mode != "rect" and mode != "polar":
                display.msg("Warning:  bad imaginary_mode('%s') in configuration" \
                    % mode)
        return s
    elif isinstance(x, mpi):
        a = str(x.a)
        b = str(x.b)
        mid = x.mid
        delta = x.delta/2
        f = cfg["fp_format"]
        mode = cfg["iv_mode"]
        sp = ""
        if cfg["iv_space"]:
            sp = " "
        if cfg["fp_format"] != "none":
            a = fp.format(x.a, f)
            b = fp.format(x.b, f).strip()
            mid = fp.format(mid, f)
            delta = fp.format(delta, f).strip()
        if mode == "a":
            s = mid + sp + "+-" + sp + delta
        elif mode == "b":
            a = x.mid
            if x.mid != 0:
                b = 100*x.delta/(2*x.mid)
            else:
                b = mpf(0)
            m = str(a)
            p = str(b)
            if cfg["fp_format"] != "none":
                m = fp.format(a, f)
                p = fp.format(b, f).strip()
            s = m + sp + "(" + p + "%)"
        elif mode == "c":
            br1, br2 = cfg["iv_brackets"]
            s = br1 + a.strip() + "," + sp + b + br2
        else:
            raise ValueError("%s'%s' is unknown iv_mode in configuration" % \
                (fln(), mode))
    elif isinstance(x, Julian):
        return str(x)
    else:
        raise Exception("%sError in Format():  Unknown number format" % fln())
    return s

def WriteList(filename, name, list):
    try:
        f = open(filename, "wb")
        p = f.write
        p("from mpmath import *" + nl)
        p("from rational import Rational" + nl)
        p("from integer import Zn" + nl)
        p("from julian import Julian" + nl)
        p("mp.dps = " + str(mp.dps) + nl + nl)
        p(name + " = [" + nl)
        indent = "  "
        for item in list:
            s = repr(item)
            if s == "<pi: 3.14159~>": s = "pi"
            p(indent + s + "," + nl)
        p("]" + nl)
        f.close()
    except Exception, e:
        msg = ("%sError trying to write list '%s':" % (fln(), name)) + nl + str(e)
        display.msg(msg)
        raise

def WriteDictionary(filename, name, dictionary):
    try:
        f = open(filename, "wb")
        p = f.write
        p("from mpmath import *" + nl)
        p("from rational import Rational" + nl)
        p("from integer import Zn" + nl)
        p("from julian import Julian" + nl)
        p("mp.dps = " + str(mp.dps) + nl + nl)
        p(name + " = {" + nl)
        keys = dictionary.keys()
        keys.sort()
        indent = "  "
        for key in keys:
            s = repr(dictionary[key])
            if s == "<pi: 3.14159~>": s = "pi"
            p(indent + '"' + key + '"' + " : " + s + "," + nl)
        p("}" + nl)
        f.close()
    except Exception, e:
        msg = ("%sError trying to write dictionary '%s':" % (fln(), name)) + nl + str(e)
        display.msg(msg)
        raise

def EditDictionary(name, dictionary):
    if not cfg["editor"]:
        raise RuntimeError("%sEditor is not defined in configuration" % fln())
    if not cfg["tempfile"]:
        filename = mkstemp(prefix="hctemp")
    else:
        filename = cfg["tempfile"]
    try:
        WriteDictionary(cfg["tempfile"], name, dictionary)
    except:
        display.msg("%sUnable to edit dictionary '%s'" % (fln(), name))
        return False
    # Open the file in the editor
    cmd = cfg["editor"] + " " + filename
    system(cmd)  # We use the os.system command because it blocks
    # Execute the new file
    newdict = {}
    try:
        execfile(filename, newdict)
    except Exception, e:
        msg = "%sError trying to read in the modified dictionary:" % fln() \
              + nl + str(e)
        display.msg(msg)
        return False
    dictionary.clear()
    dictionary.update(newdict[name])
    # Remove the temporary file if it's not set in cfg
    if not cfg["tempfile"]:
        os.remove(filename)
    return True

def EditConfiguration():
    if EditDictionary("cfg", cfg):
        ConfigChanged()

def EditStack():
    if not cfg["editor"]:
        raise RuntimeError("%sEditor is not defined in configuration" % fln())
    if not cfg["tempfile"]:
        filename = mkstemp(prefix="hctemp")
    else:
        filename = cfg["tempfile"]
    name = "mystack"
    fp = open(filename, "wb")
    p = fp.write
    p("from mpmath import *" + nl + nl)
    p("mp.dps = " + str(mp.dps) + nl + nl)
    p(name + " = [" + nl)
    indent = "  "
    for item in stack.stack:
        p(indent + repr(item) + "," + nl)
    p("]" + nl)
    fp.close()
    # Open the file in the editor
    cmd = cfg["editor"] + " " + filename
    system(cmd)  # We use the os.system command because it blocks
    # Execute the new file
    newdict = {}
    try:
        execfile(filename, newdict)
    except Exception, e:
        msg = "%sError trying to read in the modified stack:" % fln() + nl + str(e)
        display.msg(msg)
        return
    stack.stack = newdict[name]
    # Remove the temporary file if it's not set in cfg
    if not cfg["tempfile"]:
        os.remove(filename)

def EditRegisters():
    EditDictionary("registers", registers)

def PrintRegisters():
    if not registers:
        raise ValueError("%sThere are no registers defined" % fln())
    names = registers.keys()
    names.sort()
    lengths = [len(name) for name in names]
    fmt = "%%-%ds  %%s\n" % max(lengths)
    s = ""
    for name in names:
        s += fmt % (name, Format(registers[name]))
    display.msg(s)

def CheckEnvironment(commands_dict):
    '''Look at the environment variables defined in
    cfg["environment"] and execute any commands in them.  Note we only
    do this if we're not using the default configuation (-d option).
    '''
    if use_default_config_only: return
    for var in cfg["environment"]:
        if var in os.environ:
            try:
                finished = False
                status = None
                cmd_line = os.environ[var]
                cmds = ParseCommandInput(cmd_line)
                n = len(cmds) - 1
                for i, cmd in enumerate(cmds):
                    status = ProcessCommand(cmd, commands_dict, i==n)
                    if status == status_quit:
                        finished = True
                if finished:
                    raise Exception("%sGot a quit command" % fln())
            except Exception, e:
                msg = "%sFor environment variable '%s', got exception:" + nl
                display.msg(msg % (fln(), var) + str(e))


def RunChecks(commands_dict):
    '''Run checks on various things to flag things that might need to be
    fixed.
    '''
    if not run_checks:  return
    # Look for commands that don't have associated help strings
    s = ""
    for cmd in commands_dict:
        if cmd[0] == " ":  cmd = cmd[1:]
        if cmd in helpinfo:
            if len(helpinfo[cmd]) == 0:
                s += ("'%s' command missing help string" % cmd) + nl
        else:
            s += ("'%s' command has no helpinfo dictionary entry" % cmd) + nl
    if s: display.msg(s)

def ExecutedCommandOK(cmd, args, commands_dict):
    '''command is the string containing the command to execute.  args
    contains any alternative arguments for this command.  commands_dict is a
    dictionary defining the dispatch function with other needed info.
    Return True unless an exception occurred and a message already was
    printed.
    '''
    if cmd[0] == " ":  cmd = cmd[1:]
    if cmd not in commands_dict:
        raise Exception("%sProgram bug:  bad command" % fln())
    extra_dict = None
    if len(commands_dict[cmd]) == 3:
        func, num_stack_args, extra_dict = commands_dict[cmd]
    else:
        func, num_stack_args = commands_dict[cmd]
    if len(commands_dict[cmd]) == 3:
        extra_dict = commands_dict[cmd][2]
    # Handle any pre-processing
    if extra_dict and "pre" in extra_dict:
            if len(extra_dict) == 2:
                prefunc, args = extra_dict["pre"]
                prefunc(args)
            else:
                prefunc = extra_dict["pre"]
                prefunc()
    if num_stack_args == 0:
        try:
            status = func()
            # If you don't want the stack displayed after the function
            # is called, have it return False.
            if status == False:
                return False
        except Exception, e:
            display.msg("%s" % fln() + str(e))
            return False
    elif num_stack_args == 1:
        # Unary function
        try:
            x = stack[0]
            stack.lastx = x
            if isinstance(x, Zn):
                if cmd == "abs":
                    y = x.__abs__()
                else:
                    x = int(x)
                    y = func(x)
            else:
                y = func(x)
            stack.pop()
            if y != None:
                if isint(y):
                    y = Zn(y)
                stack.push(y)
                if isinstance(y, tuple) or isinstance(y, list):
                    Flatten()
        except KeyboardInterrupt:
            display.msg("%sInterrupted" % fln())
            return False
        except Exception, e:
            display.msg("%s" % fln() + str(e))
            return False
    elif num_stack_args == 2:
        # Binary function
        size = stack.size()
        try:
            x, y = stack[0], stack[1]
            x1 = x
            if isinstance(x, Zn): x = int(x)
            if isinstance(y, Zn): y = int(y)
        except Exception, e:
            display.msg("%s" % fln() + str(e))
            return False
        try:
            stack.pop()
            stack.pop()
        except Exception, e:
            display.msg("%s" % fln() + str(e))
            # Fix stack if corrupted
            if stack.size() == size - 1:
                stack.append(x)
            elif stack.size() == size - 2:
                stack.append(y)
                stack.append(x)
            return False
        try:
            stack.lastx = x1
            result = func(y, x)
            if result != None:
                if isint(result):
                    result = Zn(result)
                stack.push(result)
        except KeyboardInterrupt:
            display.msg("%sInterrupted" % fln())
            return False
        except Exception, e: 
            display.msg("%s" % fln() + str(e))
            return False
    else:
        raise Exception("%sProgram bug:  too many stack args" % fln())
    # Handle any post-processing
    if extra_dict and "post" in extra_dict:
        if len(extra_dict) == 2:
            postfunc, args = extra_dict["post"]
            postfunc(args)
        else:
            postfunc = extra_dict["post"]
            postfunc()
    return True

def ParseCommandLine():
    global run_checks
    global use_default_config_only
    global process_stdin
    global testing
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    descr = "Command line RPN calculator"
    parser = OptionParser(usage, description=descr)
    c,d,s,t,v = ("Check that commands have help info",
                 "Use default configuration in hc.py file only",
                 "Take input from stdin",
                 "Exit with status 1 if = or == are False",
                 "Display program version")
    parser.add_option("-c", "--run_checks", action="store_true", help=c)
    parser.add_option("-d", "--default_config", action="store_true", help=d)
    parser.add_option("-s", "--read_stdin", action="store_true", help=s)
    parser.add_option("-t", "--testing_mode", action="store_true", help=t)
    parser.add_option("-v", "--version", action="store_true", help=v)
    (options, args) = parser.parse_args(args=None, values=None)
    if options.run_checks:
        run_checks = True
    if options.default_config:
        use_default_config_only = True
        display.msg("Using default configuration only")
    if options.read_stdin:
        process_stdin = True
    if options.testing_mode:
        testing = True
    if options.version:
        display.msg("hcpy version 6 (17 Mar 2009)")

def GetRegisterName(cmd):
    cmd = strip(cmd)
    if len(cmd) < 2:
        raise ValueError("%sYou must give a register name" % fln())
    return cmd[1:]

def RecallRegister(cmd):
    name = GetRegisterName(cmd)
    if name not in registers:
        raise ValueError("%sRegister name '%s' is not defined" % (fln(), name))
    stack.push(registers[name])
    return status_ok

def StoreRegister(cmd):
    name = GetRegisterName(cmd)
    if stack.size() == 0:
        raise Exception("%sStack is empty" % fln())
    registers[name] = stack[0]
    return status_ok

def EditXRegister():
    try:
        d = {"x":stack[0]}
        EditDictionary("x_register", d)
        stack[0] = d["x"]
    except Exception, e:
        raise Exception("%sCouldn't edit x" % fln())

def Int(cmd):
    if len(cmd) > 3:
        s = cmd[3:]
        n = int(s)
        if not isint(n):
            msg = "%%s'%s' is not a valid integer for int command" % s
            raise ValueError(msg % fln())
        if n < 1:
            msg = "%sInteger for int command must be > 0"
            raise ValueError(msg % fln())
        Number.bits = n
        Zn().bits = n
    else:
        Number.bits = 0
        Zn().bits = 0
    # TODO This is ugly and needs refactoring...
    Number.signed = True
    Zn().signed = True

def Bang(cmd):
    '''If the command is !, give a list of the python scripts that
    are in cfg["helper_scripts"].  If there's an argument, execute
    that script and push the returned number on the stack.
    '''
    import os.path, glob
    try:
        dir = os.path.normpath(cfg["helper_scripts"])
        func = cfg["helper_script_function_name"]
    except Exception, e:
        raise Exception("%sBad cfg key(s) in Bang:\n%s" % (fln(), str(e)))
    if dir:
        try:
            glob_spec = os.path.join(dir, "*.py")
            files = glob.glob(glob_spec)
            if cmd == "!":
                files = [os.path.split(i)[1].replace(".py", "") for i in files]
                files = " ".join(files)
                s = "Scripts to execute:" + nl + nl.join(wrap(files))
                display.msg(s)
            else:
                name = cmd[1:]
                sys.path.insert(0, dir)
                s = "from %s import %s\nresult = %s(display)\n" % \
                    (name, func, func)
                co = compile(s, "", "exec")
                d = {"display":display}
                eval(co, d, d)
                result = d["result"]
                if result != None:
                    # TODO: Need to validate that result is a valid stack
                    # object.
                    stack.push(result)
        except Exception, e:
            raise Exception("%s'%s' failed:\n%s" % (fln(), cmd, str(e)))

def Uint(cmd):
    if not (len(cmd) > 4):
        raise ValueError("%suint command must be followed by an integer" % fln())
    s = cmd[4:]
    n = int(s)
    if not isint(n):
        msg = "%%s'%s' is not a valid integer for uint command" % s
        raise ValueError(msg % fln())
    if n < 1:
        msg = "%%sInteger for uint command must be > 0"
        raise ValueError(msg % fln())
    # TODO This is ugly and needs refactoring...
    Number.bits = n
    Zn().bits = n
    Number.signed = False
    Zn().signed = False

def Tee(cmd):
    write_mode = "wb"  # new file
    chop_off_leader = 2
    if cmd[:3] == ">>>":
        write_mode = "ab"  # append to possibly existing file
        if len(cmd) < 4:
            raise Exception("%s>>> command requires a file name" % fln())
        chop_off_leader = 3
    file = cmd[chop_off_leader:]
    try:
        f = open(file, write_mode)
        display.logon(f)
        global tee_is_on
        tee_is_on = True
    except:
        raise Exception("%sCouldn't open '%s' for tee" % (fln(), file))

def TeeOff():
    try:
        display.logoff()
        global tee_is_on
        tee_is_on = False
    except:
        pass

def ExpandCommand(cmd):
    '''If cmd is of the form n*x, expand it into a list of n of the
    commands x and return it.  Otherwise, just return x.
    '''
    if len(cmd) > 2 and "*" in cmd:
        try:
            loc = cmd.find("*")
            if loc == 0 or loc == len(cmd) - 1:
                return cmd
            n = cmd[:loc]
            x = cmd[loc+1:]
            n = int(n)
            return n*[x]
        except:
            pass
    return cmd

def ParseCommandInput(cmd):
    '''cmd is a nonempty string and needs to be parsed.  If it contains the
    cfg["command_separator"] string, then the user wanted those to separate
    commands, as some of the individual commands contain whitespace.
    Otherwise, parse on whitespace.  Return a list of one or more command
    strings.
    '''
    assert cmd, "Error in program:  cmd is empty string"
    sep = cfg["command_separator"]
    if sep in cmd:
        commands = [strip(s) for s in cmd.split(sep)]
    else:
        commands = cmd.split()
    assert commands, "Error in program:  empty list"
    # Check each command for multiple form:  n*x where n is an integer
    # and x is a command.  If present, expand them into separate
    # commands.
    commands = [ExpandCommand(i) for i in commands]
    new_commands = []
    for i in commands:
        if isinstance(i, list):
            new_commands += i
        else:
            new_commands.append(i)
    return new_commands

def GreaterThanEqual(x, y):
    'If x >= y, return True; otherwise, return False.'
    result = (x >= y)
    if not result and testing: exit(1)
    return result

def GreaterThan(x, y):
    'If x > y, return True; otherwise, return False.'
    result = (x > y)
    if not result and testing: exit(1)
    return result

def LessThanEqual(x, y):
    'If x <= y, return True; otherwise, return False.'
    result = (x <= y)
    if not result and testing: exit(1)
    return result

def LessThan(x, y):
    'If x < y, return True; otherwise, return False.'
    result = (x < y)
    if not result and testing: exit(1)
    return result

def Equal(x, y):
    'If x and y are equal, return True; otherwise, return False.'
    result = (x == y)
    if not result and testing:
        exit(1)
    return result

def NotEqual(x, y):
    'If x and y are not equal, return True; otherwise, return False.'
    result = (x != y)
    if not result and testing:
        exit(1)
    return result

def DisplayEqual(x, y):
    '''If x and y are equal, return True; otherwise, return False.
    IMPORTANT:  the test of equality is whether the string
    representations in the current display mode match.  If they do,
    the numbers are equal.  If testing is True, then if the two
    numbers compare false, we exit with a status of 1.
    '''
    sx, sy = Format(x), Format(y)
    result = (sx == sy)
    if not result and testing:
        exit(1)
    return result

def ReadInputFromFile(command, commands_dict):
    stream = open(command[2:])
    while stream:
        cmd_line = GetLineOfInput(stream)
        if cmd_line == eof: break
        if cmd_line == comment_line or cmd_line == "": continue
        cmds = ParseCommandInput(cmd_line)
        if not cmds: continue
        n = len(cmds) - 1
        for i, cmd in enumerate(cmds):
            status = ProcessCommand(cmd, commands_dict, i==n)
            if status == status_quit or \
               status == status_error or \
               status == status_unknown_command:
                return status
            cmd = ""
    if status == status_ok:
        return status_ok_no_display
    return status

def ProcessSpecialCommand(cmd, commands_dict):
    '''This function is for commands that don't fit the general pattern or
    are just easiest to implement here.  We return either status_ok,
    status_ok_no_display, status_error, or status_unknown_command
    or status_quit.
    '''
    if cmd[0] == "?":
        Help(cmd, commands_dict)
        return status_ok_no_display
    elif len(cmd) >= 3 and cmd[:3] == "int":
        Int(cmd)
    elif len(cmd) >= 4 and cmd[:4] == "uint":
        Uint(cmd)
    elif (len(cmd) == 1 and cmd == "!") or \
         (len(cmd) > 1 and cmd[0] == "!" and cmd[1] != "="):
        Bang(cmd)
    elif len(cmd) > 1 and cmd[0] == "<" and cmd[1] != "<" and cmd[1] != "=":
        return RecallRegister(cmd)
    elif len(cmd) > 1 and cmd[0] == ">" and cmd[1] != ">" and cmd[1] != "=":
        return StoreRegister(cmd)
    elif len(cmd) > 2 and cmd[0] == ">" and cmd[1] == ">":
        Tee(cmd)
    elif len(cmd) > 2 and cmd[0] == "<" and cmd[1] == "<":
        return ReadInputFromFile(cmd, commands_dict)
    elif cmd == ">>.":
        TeeOff()
    elif cmd == "fix":
        cfg["fp_format"] = "fix"
    elif cmd == "sig":
        cfg["fp_format"] = "sig"
    elif cmd == "sci":
        cfg["fp_format"] = "sci"
    elif cmd == "eng":
        cfg["fp_format"] = "eng"
    elif cmd == "engsi":
        cfg["fp_format"] = "engsi"
    elif cmd == "none":
        cfg["fp_format"] = "none"
    elif cmd == "dec":
        cfg["integer_mode"] = "dec"
    elif cmd == "hex":
        cfg["integer_mode"] = "hex"
    elif cmd == "oct":
        cfg["integer_mode"] = "oct"
    elif cmd == "bin":
        cfg["integer_mode"] = "bin"
    elif cmd == "iva":
        cfg["iv_mode"] = "a"
        Julian.interval_representation = "a"
    elif cmd == "ivb":
        cfg["iv_mode"] = "b"
        Julian.interval_representation = "b"
    elif cmd == "ivc":
        cfg["iv_mode"] = "c"
        Julian.interval_representation = "c"
    elif cmd == "on":
        display.on()
        return status_ok_no_display
    elif cmd == "off":
        display.off()
        return status_ok_no_display
    elif cmd == "eps":
        stack.push(eps)
    elif cmd == "deg":
        cfg["angle_mode"] = "deg"
    elif cmd == "rad":
        cfg["angle_mode"] = "rad"
    elif cmd == "prst" or cmd == ".":
        if stack.size() > 0:
            display.msg(stack._string(Format))
            if cfg["modulus"] != 1:
                display.msg(" (mod " + Format(cfg["modulus"])+ ")")
            return status_ok_no_display
    else:
        return status_unknown_command
    return status_ok

def ProcessCommand(cmd, commands_dict, last_command):
    '''Decode cmd and execute it as appropriate.  commands_dict maps
    commands to actions.  If last_command is true, then the stack should
    be printed when finished.  Our return values are coded as follows:
        status_ok       Everything fine
        status_quit     Received a quit command
        status_error    A command resulted in an error
        status_interrupted  The processing was interrupted
    otherwise return false.
    '''
    c, n, x = CommandDecode(commands_dict), Number(), ""
    if tee_is_on:
        display.log(cmd)
    try:
        # We need to fully expand special commands like 'bi' here,
        # which will become 'bin', yet need to be processed by
        # ProcessSpecialCommand().
        x = c.identify_cmd(cmd)
        if isinstance(x, type("")):
            status = ProcessSpecialCommand(x, commands_dict)
        else:
            status = ProcessSpecialCommand(cmd, commands_dict)
    except Exception, e:
        display.msg("%s" % fln() + str(e))
        return status_error
    ok = False
    if status == status_ok:
        ok = True
    elif status == status_ok_no_display:
        return status_ok
    if status == status_unknown_command:
        # First check to see if we have a number.  However, 'I' will be
        # ignored, as it's a command to cast to complex.
        ok = False
        if cmd != "I" and \
           cmd != "T" and \
           cmd != "im" and \
           cmd != "ip" and \
           cmd != "in":
            try:
                num = n(cmd)
                if num != None:
                    stack.push(num)
                    ok = True
            except Exception, e:
                display.msg("%s" % fln() + str(e))
                return status_error
        # Handle the help command with an argument specially
        if not ok and len(cmd) > 1 and cmd[0] == "?":
            Help(commands_dict, cmd[1:])
            ok = True
        # The apostrophe is another special command
        if not ok and len(cmd) == 2 and cmd[0] == "'":
            stack.push(ord(cmd[1]))
            ok = True
        # Now see if we can identify this command
        if not ok:
            x = c.identify_cmd(cmd)
            if isinstance(x, type("")):
                try:
                    ok = ExecutedCommandOK(x, arg, commands_dict)
                    if cfg["modulus"] != 1:
                        if stack.size():
                            y = Mod(stack[0], cfg["modulus"])
                            stack.pop()
                            stack.push(y)
                except KeyboardInterrupt:
                    display.msg("%sProcessing interrupted" % fln())
                    return status_interrupted
                except Exception, e:
                    display.msg("%sUnexpected exception:\n" % fln() + str(e))
                    return status_error
            elif isinstance(x, type([])):  # It was an ambiguous command
                x.sort()
                display.msg("Ambiguous: " + ' '.join(x))
                return status_error
            else:  # Dunno
                display.msg("Command '%s' not recognized" % cmd)
                return status_error
        if x == "quit":
            return status_quit
    if ok and last_command:
        if stack.size():
            try:
                y = DownCast(stack.pop())
                stack.push(y)
            except Exception, e:
                display.msg("%sDowncast failed:  " % fln() + str(e))
            DisplayStack(display, stack)
        else:
            #display.msg("Stack is empty")
            pass
        return status_ok

def GetLineOfInput(stream=None):
    #
    global stdin_finished
    if stream:
        s = stream.readline()
    elif process_stdin:
        s = sys.stdin.readline()
    else:
        s = raw_input(cfg["prompt"])
    # Log the line received
    if s and s[-1] == nl:
        display.log('--> "%s"' % s, suppress_nl=True)
    else:
        display.log('--> "%s"' % s)
    if s == "":
        s = eof
        stdin_finished = True
    else:
        s = strip(s)
    pos = s.find("#")  # Delete comments
    if pos != -1:
        s = s[:pos]
        if pos == 0:
            # This line was nothing but a comment
            return comment_line
    return s

def main():
    args = ParseCommandLine()
    GetConfiguration()
    commands_dict = {
        # Values are
        # [
        #   implementation function to call,
        #   number of stack arguments consumed,
        #   Optional dictionary of other needed things, such as:
        #       "pre" : [func, (args,)]  Function to execute before calling
        #                                the implementation function.
        #       "post": [func, (args,)]  Function to execute after calling
        #                                the implementation function.
        # ]

        # Binary functions
        "+"        : [add, 2],
        "-"        : [subtract, 2],
        "*"        : [multiply, 2],
        "/"        : [divide, 2],
        "//"       : [integer_divide, 2],
        "%"        : [Mod, 2],
        "and"      : [bit_and, 2],
        "or"       : [bit_or, 2],
        "xor"      : [bit_xor, 2],
        "<<"       : [bit_leftshift, 2],
        ">>"       : [bit_rightshift, 2],
        "%ch"      : [percent_change, 2],
        "comb"     : [combination, 2],  # Combinations of y taken x at a time
        "perm"     : [permutation, 2],  # Permutations of y taken x at a time
        "pow"      : [m.power, 2],  # Raise y to the power of x
        "atan2"    : [m.atan2, 2, {"post" : Conv2Deg}], #
        "hypot"    : [m.hypot, 2],  # sqrt(x*x + y*y)
        "round"    : [Round, 2],  # Round y to nearest x
        "in"       : [In, 2],     # True if x is in interval y
        "=="       : [Equal, 2],     # True if x == y
        "!="       : [NotEqual, 2],  # True if x != y
        "<"        : [LessThan, 2],  # True if x < y
        "<="       : [LessThanEqual, 2], # True if x <= y
        ">"        : [GreaterThan, 2],      # True if x > y
        ">="       : [GreaterThanEqual, 2], # True if x >= y
        "="        : [DisplayEqual, 2],  # True if displayed strings of x & y are equal
        "2V"       : [ToV, 2],   # Convert to [y,x] interval number

        # Unary functions
        "I"        : [Cast_i, 1],  # Convert to integer
        "Q"        : [Cast_q, 1],  # Convert to rational at display resolution
        "QQ"       : [Cast_qq, 1], # Convert to rational at full precision
        "R"        : [Cast_r, 1],  # Convert to real number
        "C"        : [Cast_c, 1],  # Convert to complex number
        "T"        : [Cast_t, 1],  # Convert to time/date
        "V"        : [Cast_v, 1],  # Convert to interval number
        "ip"       : [ip, 1],    # Integer part of x
        "fp"       : [Fp, 1],    # Fractional part of x
        "1/x"      : [reciprocal, 1], # Calculate the reciprocal of x
        "chs"      : [chs, 1],   # Change the sign of x
        "~"        : [bit_negate, 1],   # Flip all the bits of x
        "numer"    : [numerator, 1],    # Numerator of rational
        "denom"    : [denominator, 1],  # Denominator of rational
        "apart"    : [apart, 1], # Take rational, complex, or interval apart
        "chop"     : [Chop, 1],  # Convert x to its displayed value
        "re"       : [RealPart, 1],     # Real part of x
        "im"       : [ImagPart, 1],     # Imaginary part of x
        "conj"     : [conj, 1],  # Complex conjugate of x
        "sqrt"     : [sqrt, 1],  # Square root of x
        "square"   : [square, 1],# Square x
        "mid"      : [mid, 1],   # Take midpoint of interval number
        "fact"     : [Factorial, 1], # Factorial of x
        "floor"    : [floor, 1], # Largest integer <= x
        "ceil"     : [ceil, 1],  # Smallest integer >= x
        "eps"      : [None, 0],
        "sin"      : [m.sin, 1,  {"pre"  : Conv2Rad}],
        "cos"      : [m.cos, 1,  {"pre"  : Conv2Rad}],
        "tan"      : [m.tan, 1,  {"pre"  : Conv2Rad}],
        "asin"     : [m.asin, 1, {"post" : Conv2Deg}],
        "acos"     : [m.acos, 1, {"post" : Conv2Deg}],
        "atan"     : [m.atan, 1, {"post" : Conv2Deg}],
       #"sec"      : [m.sec, 1,  {"pre"  : Conv2Rad}],
       #"csc"      : [m.csc, 1,  {"pre"  : Conv2Rad}],
       #"cot"      : [m.cot, 1,  {"pre"  : Conv2Rad}],
       #"asec"     : [m.asec, 1, {"post" : Conv2Deg}],
       #"acsc"     : [m.acsc, 1, {"post" : Conv2Deg}],
       #"acot"     : [m.acot, 1, {"post" : Conv2Deg}],
       #"sinh"     : [m.sinh, 1],
       #"cosh"     : [m.cosh, 1],
       #"tanh"     : [m.tanh, 1],
       #"asinh"    : [m.asinh, 1],
       #"acosh"    : [m.acosh, 1],
       #"atanh"    : [m.atanh, 1],
       #"sech"     : [m.sech, 1],
       #"csch"     : [m.csch, 1],
       #"coth"     : [m.coth, 1],
       #"asech"    : [m.asech, 1],
       #"acsch"    : [m.acsch, 1],
       #"acoth"    : [m.acoth, 1],
        "2deg"     : [ToDegrees, 1],  # Convert x to radians
        "2rad"     : [ToRadians, 1],  # Convert x to degrees
        "ln"       : [m.ln, 1],    # Natural logarithm
        "ln2"      : [Ln2, 1],     # Base 2 logarithm
        "log"      : [m.log10, 1], # Base 10 logarithm
        "exp"      : [m.exp, 1], # Exponential function
        "abs"      : [abs, 1],   # Absolute value of x
        "arg"      : [arg, 1, {"post" : Conv2Deg}],  # Argument of complex

        # Other functions
        "quit"     : [quit, 0],  # Exit the program
        "enter"    : [Enter, 0], # Push a copy of x onto the stack
        "lastx"    : [lastx, 0], # Recall last x used
        "mixed"    : [mixed, 1], # Toggle mixed fraction display
        "xch"      : [xch, 0],   # Exchange x and y
        "roll"     : [roll, 0],  # Roll stack
        "del"      : [Del, 0],   # Pop x off the stack
        "?"        : [None, 0],  # Help command
        "pi"       : [Pi, 0],
        "prst"     : [None, 0],  # Print stack
        "."        : [None, 0],  # Print stack
        "clst"     : [ClearStack, 0],
        "stack"    : [SetStackDisplay, 1],
        "e"        : [E, 0],
        "deg"      : [None, 0],  # Set degrees for angle mode
        "rad"      : [None, 0],  # Set radians for angle mode
        "ec"       : [EditConfiguration, 0],
        "es"       : [EditStack, 0],
        "er"       : [EditRegisters, 0],
        "prr"      : [PrintRegisters, 0],
        "2hr"      : [hr, 1],    # Convert to decimal hour format
        "2hms"     : [hms, 1],   # Convert to hour/minute/second format
        "rand"     : [rand, 0],  # Uniform random number
        "cfg"      : [ShowConfig, 0], # Show configuration
        "mod"      : [Modulus, 1], # All answers displayed with this modulus
        "rat"      : [Rationals, 1], # Toggle whether to use rationals
        "down"     : [ToggleDowncasting, 1],
        "clrg"     : [ClearRegisters, 0],
       #"phi"      : [Phi, 0],   # Golden ratio
        ">>."      : [None, 0],  # Turn off logging
        "int"      : [None, 0],  # Signed n-bit integer mode
        "uint"     : [None, 0],  # Unsigned n-bit integer mode
        "!"        : [None, 0],  # Execute helper scripts

        # Display functions
        "on"       : [None, 0],  # Turn display of answers on
        "off"      : [None, 0],  # Turn display of answers off
        "prec"     : [prec, 1],  # Set calculation precision
        "digits"   : [digits, 1],# Set significant figures for display
        "width"    : [width, 1], # Set line width
        "comma"    : [comma, 1], # Toggle comma decorating
        "fix"      : [None, 0],  # Fixed number of places after decimal point
        "sig"      : [None, 0],  # Display signification figures
        "sci"      : [None, 0],  # Scientific notation display
        "eng"      : [None, 0],  # Engineering display
        "engsi"    : [None, 0],  # Engineering display with SI prefix
        "brief"    : [brief, 1],  # Fit number on one line
        "polar"    : [Polar, 0],  # Complex number display
        "rect"     : [Rectangular, 0],  # Complex number display
        "dec"      : [None, 0],  # Decimal display for integers
        "hex"      : [None, 0],  # Hex display for integers
        "oct"      : [None, 0],  # Octal for integers
        "bin"      : [None, 0],  # Binary display for integers
        "iva"      : [None, 0],  # Interval display
        "ivb"      : [None, 0],  # Interval display
        "ivc"      : [None, 0],  # Interval display
        "show"     : [Show, 0],  # Show full precision of x register
        "debug"    : [Debug, 1], # Toggle the debug variable
        # The none display mode is primarily intended for debugging.  It
        # displays makes the mpmath numbers display in their native formats.
        "none"     : [None, 0],
        "clear"    : [Reset, 0], # Reset the calculator state

        # Some other math functions
        "gamma"    : [gamma, 1],
        "zeta"     : [zeta, 1],
        "ncdf"     : [Ncdf, 1],
        "invn"     : [Incdf, 1],

    }
    RunChecks(commands_dict)
    CheckEnvironment(commands_dict)
    finished = False
    status = None
    if stack.size():
        DisplayStack(display, stack)
    try:
        while not finished:
            cmd_line = GetLineOfInput()
            if cmd_line == comment_line:
                continue
            elif cmd_line == "" or (cmd_line == eof and process_stdin):
                finished = True
            elif cmd_line == eof:
                continue
            else:
                cmds = ParseCommandInput(cmd_line)
                n = len(cmds) - 1
                for i, cmd in enumerate(cmds):
                    status = ProcessCommand(cmd, commands_dict, i==n)
                    if status == status_quit:
                        finished = True
    except KeyboardInterrupt, e:
        pass
    except EOFError, e:
        pass
    print
    SaveConfiguration()
    if status == status_error:
        exit(1)
    else:
        exit(0)
main()
