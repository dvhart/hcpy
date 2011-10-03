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
import traceback
import re as regex
from tempfile import mkstemp

try: from pdb import xx  # pdb.set_trace is xx; easy to find for debugging
except: pass

#----------------------------------
# Modules we are dependent on
try:
    import mpmath as m
    from simpleparse.stt import TextTools
    from simpleparse import generator
except ImportError:
    print """
This is a complex program that requires several external python
libraries.  Please install mpmath, simpleparse

apt-get install python-mpmath python-simpleparse

"""
    sys.exit(1)

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

out = sys.stdout.write
err = sys.stderr.write
nl = "\n"
# Status numbers that can be returned
status_ok               = 0
status_quit             = 1
status_error            = 2
status_unknown_command  = 3
status_ok_no_display    = 4
status_interrupted      = 5


class ParseError(Exception):
    pass

class InsufficientStackSize(Exception):
    pass

def _functionId(nFramesUp=0):
    """ Create a string naming the function n frames up on the stack.
    """
    co = sys._getframe(nFramesUp+1)
    return "%s: %d" % (co.f_code.co_name, co.f_lineno)

def isint(x):
    return isinstance(x, int) or isinstance(x, long) or isinstance(x, Zn)

class Calculator(object):
    ANGLE_RADIANS = 0
    ANGLE_DEGREES = 1
    VECTOR_CARTESIAN = 0
    VECTOR_POLAR = 1
    
    def __init__(self):
        self.stack = Stack()
        self.stack_index = True
        self.constants = {}
        self.angle_mode = Calculator.ANGLE_RADIANS
        self.vector_mode = Calculator.VECTOR_CARTESIAN
        self.display = Display()     # Used to display messages to user
        self.fp = mpFormat()         # For formatting floating point numbers
        self.ap = mpFormat()         # For formatting arguments of complex numbers
        self.registers = {}          # Keeps all stored registers
        self.commands_dict = {
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
            "+"        : [self.add, 2],
            "-"        : [self.subtract, 2],
            "*"        : [self.multiply, 2],
            "/"        : [self.divide, 2],
            "div"      : [self.integer_divide, 2],
            "%"        : [self.Mod, 2],
            "and"      : [self.bit_and, 2],
            "or"       : [self.bit_or, 2],
            "xor"      : [self.bit_xor, 2],
            "<<"       : [self.bit_leftshift, 2],
            ">>"       : [self.bit_rightshift, 2],
            "%ch"      : [self.percent_change, 2],
            "comb"     : [self.combination, 2],  # Combinations of y taken x at a time
            "perm"     : [self.permutation, 2],  # Permutations of y taken x at a time
            "pow"      : [self.power, 2],  # Raise y to the power of x
            "^"        : [self.power, 2],  # Raise y to the power of x
            "atan2"    : [self.atan2, 2, {"post" : self.Conv2Deg}], #
            "hypot"    : [self.hypot, 2],  # sqrt(x*x + y*y)
            "round"    : [self.Round, 2],  # Round y to nearest x
            "in"       : [self.In, 2],     # True if x is in interval y
            "=="       : [self.Equal, 2],     # True if x == y
            "!="       : [self.NotEqual, 2],  # True if x != y
            "<"        : [self.LessThan, 2],  # True if x < y
            "<="       : [self.LessThanEqual, 2], # True if x <= y
            ">"        : [self.GreaterThan, 2],      # True if x > y
            ">="       : [self.GreaterThanEqual, 2], # True if x >= y
            "="        : [self.DisplayEqual, 2],  # True if displayed strings of x & y are equal
            "2V"       : [self.ToV, 2],   # Convert to [y,x] interval number

            # Unary functions
            "I"        : [self.Cast_i, 1],  # Convert to integer
            "Q"        : [self.Cast_q, 1],  # Convert to rational at display resolution
            "QQ"       : [self.Cast_qq, 1], # Convert to rational at full precision
            "R"        : [self.Cast_r, 1],  # Convert to real number
            "C"        : [self.Cast_c, 1],  # Convert to complex number
            "T"        : [self.Cast_t, 1],  # Convert to time/date
            "V"        : [self.Cast_v, 1],  # Convert to interval number
            "ip"       : [self.ip, 1],    # Integer part of x
            "fp"       : [self.Fp, 1],    # Fractional part of x
            "inv"      : [self.reciprocal, 1], # reciprocal of x
            "~"        : [self.bit_negate, 1],   # Flip all the bits of x
            "numer"    : [self.numerator, 1],    # Numerator of rational
            "denom"    : [self.denominator, 1],  # Denominator of rational
            "apart"    : [self.apart, 1], # Take rational, complex, or interval apart
            "chop"     : [self.Chop, 1],  # Convert x to its displayed value
            "re"       : [self.RealPart, 1],     # Real part of x
            "im"       : [self.ImagPart, 1],     # Imaginary part of x
            "conj"     : [self.conj, 1],  # Complex conjugate of x
            "sqrt"     : [self.sqrt, 1],  # Square root of x
            "sqr"      : [self.square, 1],# Square x
            "neg"      : [self.negate, 1], # negative of x
            "mid"      : [self.mid, 1],   # Take midpoint of interval number
            "sum"      : [self.Sum, 'x'],  # sum of top x values (depth sum for all)
            "!"        : [self.Factorial, 1],  # factorial
            "floor"    : [self.floor, 1], # Largest integer <= x
            "ceil"     : [self.ceil, 1],  # Smallest integer >= x

            # trig functions
            "sin"      : [self.sin, 1],#  {"pre"  : self.Conf2Rad}],
            "cos"      : [self.cos, 1],#  {"pre"  : self.Conf2Rad}],
            "tan"      : [self.tan, 1],#  {"pre"  : self.Conf2Rad}],
            "asin"     : [self.asin, 1],# {"post" : self.Conf2Deg}],
            "acos"     : [self.acos, 1],# {"post" : self.Conf2Deg}],
            "atan"     : [self.atan, 1],# {"post" : self.Conf2Deg}],
            "sec"      : [self.sec, 1],#  {"pre"  : self.Conf2Rad}],
            "csc"      : [self.csc, 1],#  {"pre"  : self.Conf2Rad}],
            "cot"      : [self.cot, 1],#  {"pre"  : self.Conf2Rad}],
            "asec"     : [self.asec, 1],# {"post" : self.Conf2Deg}],
            "acsc"     : [self.acsc, 1],# {"post" : self.Conf2Deg}],
            "acot"     : [self.acot, 1],# {"post" : self.Conf2Deg}],
            "sinh"     : [self.sinh, 1],
            "cosh"     : [self.cosh, 1],
            "tanh"     : [self.tanh, 1],
            "asinh"    : [self.asinh, 1],
            "acosh"    : [self.acosh, 1],
            "atanh"    : [self.atanh, 1],
            "sech"     : [self.sech, 1],
            "csch"     : [self.csch, 1],
            "coth"     : [self.coth, 1],
            "asech"    : [self.asech, 1],
            "acsch"    : [self.acsch, 1],
            "acoth"    : [self.acoth, 1],
            "2deg"     : [self.ToDegrees, 1],  # Convert x to radians
            "2rad"     : [self.ToRadians, 1],  # Convert x to degrees

            "ln"       : [self.ln, 1],    # Natural logarithm
            "ln2"      : [self.Ln2, 1],     # Base 2 logarithm
            "log"      : [self.log10, 1], # Base 10 logarithm
            "exp"      : [self.exp, 1], # Exponential function
            "abs"      : [self.abs, 1],   # Absolute value of x
            "arg"      : [self.arg, 1],# {"post" : Conv2Deg}],  # Argument of complex

            # Stack functions
            "clr"      : [self.ClearStack, 0],
            "stack"    : [self.SetStackDisplay, 1],
            "lastx"    : [self.lastx, 0], # Recall last x used
            "mixed"    : [self.mixed, 1], # Toggle mixed fraction display
            "swap"     : [self.swap, 0],   # swap x and y
            "roll"     : [self.roll, 0],  # Roll stack
            "rolld"    : [self.rolld, 0],  # Roll stack down
            "drop"     : [self.drop, 1],   # Pop x off the stack
            "drop2"    : [self.drop2, 2],   # Pop x and y off the stack
            "dropn"    : [self.dropn, 'x'],   # Pop x items off the stack
            "dup"      : [self.dup, 1],   # Push a copy of x onto the stack
            "dup2"     : [self.dup2, 2],   # Push a copy of x and y onto the stack
            "dupn"     : [self.dupn, 'x'],  # duplicate top x values on stack
            "depth"    : [self.depth, 0],  # Push stack depth onto stack

            # constants
            "pi"       : [self.Pi, 0],
            "e"        : [self.E, 0],

            # Other stuff
            "?"        : [self.help, 0],  # Help command
            "help"     : [self.help, 0],  # Help command
            "quit"     : [self.quit, 0],  # Exit the program
            "deg"      : [self.deg, 0],  # Set degrees for angle mode
            "rad"      : [self.rad, 0],  # Set radians for angle mode
            "ec"       : [self.EditConfiguration, 0],
            "es"       : [self.EditStack, 0],
            "er"       : [self.EditRegisters, 0],
            "prr"      : [self.PrintRegisters, 0],
            "2hr"      : [self.hr, 1],    # Convert to decimal hour format
            "2hms"     : [self.hms, 1],   # Convert to hour/minute/second format
            "rand"     : [self.rand, 0],  # Uniform random number
            "cfg"      : [self.ShowConfig, 0], # Show configuration
            "mod"      : [self.Modulus, 1], # All answers displayed with this modulus
            "rat"      : [self.Rationals, 1], # Toggle whether to use rationals
            "down"     : [self.ToggleDowncasting, 1],
            "clrg"     : [self.ClearRegisters, 0],
           #"phi"      : [self.Phi, 0],   # Golden ratio
            ">>."      : [self.display.logoff, 0],  # Turn off logging
            "sx"       : [self.C_sX, 1],  # Unsigned n-bit integer mode
            "ux"       : [self.C_uX, 1],  # Signed n-bit integer mode

            # Display functions
            "on"       : [self.display.on, 0],  # Turn display of answers on
            "off"      : [self.display.off, 0],  # Turn display of answers off
            "prec"     : [self.Prec, 1],  # Set calculation precision
            "digits"   : [self.digits, 1],# Set significant figures for display
            "width"    : [self.width, 1], # Set line width
            "comma"    : [self.comma, 1], # Toggle comma decorating
            "fix"      : [self.fix, 0],  # Fixed number of places after decimal point
            "sig"      : [self.sig, 0],  # Display signification figures
            "sci"      : [self.sci, 0],  # Scientific notation display
            "eng"      : [self.eng, 0],  # Engineering display
            "engsi"    : [self.engsi, 0],  # Engineering display with SI prefix
            "brief"    : [self.brief, 1],  # Fit number on one line
            "polar"    : [self.Polar, 0],  # Complex number display
            "rect"     : [self.Rectangular, 0],  # Complex number display
            "dec"      : [self.dec, 0],  # Decimal display for integers
            "hex"      : [self.hex, 0],  # Hex display for integers
            "oct"      : [self.oct, 0],  # Octal for integers
            "bin"      : [self.bin, 0],  # Binary display for integers
            "ip"       : [self.ip, 0],  # ip address display
            "iva"      : [self.iva, 0],  # Interval display
            "ivb"      : [self.ivb, 0],  # Interval display
            "ivc"      : [self.ivc, 0],  # Interval display
            "show"     : [self.Show, 0],  # Show full precision of x register
            "debug"    : [self.Debug, 1], # Toggle the debug variable
            # The none display mode is primarily intended for debugging.  It
            # displays makes the mpmath numbers display in their native formats.
            "clear"    : [self.Reset, 0], # Reset the calculator state

            # Some other math functions
            "gamma"    : [self.gamma, 1],
            "zeta"     : [self.zeta, 1],
            "ncdf"     : [self.Ncdf, 1],
            "invn"     : [self.Incdf, 1],

        }
        #t = datetime.now()
        #M.rand('init', 64)
        #M.rand('seed', (t.year+t.month+t.day)/(t.microsecond+1)+
        #    (((t.hour*60)+t.minute)*60+t.second*1000000)+t.microsecond)
        # set up readline stuff
        # check for dir and file
        # consider adding tab completion
        try:
            os.makedirs(os.path.expanduser('~')+'/.pycalc')
        except OSError:
            pass
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(os.path.expanduser('~')+'/.pycalc/history')
            except IOError:
                pass
            #atexit.register(self.cleanup)

        grammar = """
        calculator_grammar := statement / ws
        statement := simple_statement / (simple_statement, ws, statement) / help_statement
        help_statement := 'help',(ws,(delimited_func / operator))?
        simple_statement := cint / number / delimited_func / constant / operator / ((constant/number), ows, operator)
        cint := [us],[0-9]+
        operator := '+' / '*' / '/' / '-' / '%' / '^' / '&' / '!'
        number := scaler_number / compound_number / [ij]
        compound_number := vector / array
        scaler_number := complex_number / imag_number / real_number
        complex_number := (real_number_ns,('+'/'-'),imag_number) / ('(',real_number,',',real_number,')') / ('(', real_number, (',', ows)?, '<', real_number, ')')
        imag_number := real_number_ns,[ij]
        array := '[', vector_list, ']'
        vector_list := (vector, ',', vector_list) / vector 
        vector := '[', real_number_list, ']'
        real_number_list := real_number, (','?, real_number)*
        real_number := ows, real_number_ns, ows
        real_number_ns := bin_number / oct_number / hex_number / dec_number
        hex_number := hex_float / hex_whole
        dec_number := dec_float / dec_whole
        oct_number := oct_float / oct_whole
        bin_number := bin_float / bin_whole
        hex_whole := '-'?,'0x',hex_chars,('@','-'?,hex_chars)?
        hex_float := '-'?,'0x',hex_chars?,'.',hex_chars,('@','-'?,hex_chars)?
        dec_whole := '-'?,dec_chars,('e','-'?,dec_chars)?
        dec_float := '-'?,dec_chars?,'.',dec_chars,('e','-'?,dec_chars)?
        oct_whole := '-'?,'0o',oct_chars,('@','-'?,oct_chars)?
        oct_float := '-'?,'0o',oct_chars?,'.',oct_chars,('@','-'?,oct_chars)?
        bin_whole := '-'?,'0b',bin_chars,('@','-'?,bin_chars)?
        bin_float := '-'?,'0b',bin_chars?,'.',bin_chars,('@','-'?,bin_chars)?
        hex_chars := [0-9A-Fa-f]+
        dec_chars := [0-9]+
        oct_chars := [0-7]+
        bin_chars := [01]+
        ows := [ \n\t]*
        ws := [ \n\t],ows
        delimited_func := (ws,func,ws) / (ws,func) / (func,ws) / func
        """
        defined_constants = "constant := 'null'"
        try:
            for c in self.constants.iterkeys():
                defined_constants += " / '%s'" %c
            grammar += defined_constants + "\n        "
            defined_functions = "func := 'nop'"
            funcs = self.commands_dict.keys()
            funcs.sort(reverse=True)
            for f in funcs:
                if f in ['+', '-', '*', '/', '%', '^', '&', '!']:
                    continue
                defined_functions += " / '%s'" %f
            grammar += defined_functions
            print grammar
            self.parser = generator.buildParser(grammar).parserbyname('calculator_grammar')
        except:
            print "Something bad happened in init().  This may not work at all..."
            type,value,tb = sys.exc_info()
            traceback.print_exception(type, value, tb, None, sys.stdout)
        self.chomppre = regex.compile(r"^\s*")
        self.chomppost = regex.compile(r"\s*$")
    
    #---------------------------------------------------------------------------
    #---------------------------------------------------------------------------
    # Global variables
        self.stdin_finished = False  # Flags when stdin has reached EOF
        self.comment_line = "\xec\xeb"
        self.eof = "\xed\xee"
        self.argument_types = "%sThe two arguments must be the same type"
        self.factorial_cache = {0:1, 1:1, 2:2}
        self.process_stdin = False   # -s If true, our input comes from stdin
        self.run_checks = False      # -c Run checks
        self.quiet = False           # -q If true, don't print initial message
        self.testing = False         # -t If true, exit with nonzero status if x!=y
        self.tee_is_on = False       # True when logging to a file
        self.use_default_config_only = False

        # Used for binary conversions
        self.hexdigits = {
            "0" : "0000", "1" : "0001", "2" : "0010", "3" : "0011", "4" : "0100",
            "5" : "0101", "6" : "0110", "7" : "0111", "8" : "1000", "9" : "1001",
            "a" : "1010", "b" : "1011", "c" : "1100", "d" : "1101", "e" : "1110",
            "f" : "1111"}

        #---------------------------------------------------------------------------
        # Configuration information.

        self.cfg = {
            # If any of these environment variables exist, execute the
            # commands in them.
            "environment" : ["HCPYINIT", "hcpyinit"],

            # Angle mode:  must be either 'deg' or 'rad'
            "angle_mode" : "deg",

            # Integer mode: must be 'dec', 'hex', 'oct', 'bin', or 'ip'.
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

        self.cfg_default = {}
        self.cfg_default.update(self.cfg)
        self.RunChecks()
        self.CheckEnvironment()
        self.GetConfiguration()

    #---------------------------------------------------------------------------
    # Utility functions

    def use_modular_arithmetic(self, x, y):
        return (isint(x) and isint(y) and abs(self.cfg["modulus"]) > 1)

    def TypeCheck(self, x, y):
        if (not self.cfg["coerce"]) and (type(x) != type(y)):
            raise ValueError(self.argument_types % fln())

    def DownCast(self, x):
        '''If x can be converted to an integer with no loss of information,
        do so.  If its a complex that can be converted to a real, do so.
        '''
        if self.cfg["downcasting"] == False:
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

    def Conv2Deg(self, x):
        '''Routine to convert the top of the stack element to degrees.  This
        is typically done after calling inverse trig functions.
        '''
        try:
            if self.cfg["angle_mode"] == "deg":
                if isinstance(x, m.mpc):  # Don't change complex numbers
                    return x
                return x*180/pi
        except:
            raise ValueError("%sx can't be converted from radians to degrees" % fln())

    def Conv2Rad(self, x):
        '''Routine to convert the top of the stack element to radians.  This
        is typically done before calling trig functions.
        '''
        try:
            if self.cfg["angle_mode"] == "deg":
                if isinstance(x, m.mpc):  # Don't change complex numbers
                    return x
                return x*pi/180
        except:
            raise ValueError("%sx can't be converted from degrees to radians" % fln())

    #---------------------------------------------------------------------------
    # Binary functions

    def add(self, x, y):
        if self.use_modular_arithmetic(x, y):
            return (x + y) % self.cfg["modulus"]
        self.TypeCheck(x, y)
        try:
            return x + y
        except:
            return y + x

    def subtract(self, x, y):
        if self.use_modular_arithmetic(x, y):
            return (x - y) % self.cfg["modulus"]
        self.TypeCheck(x, y)
        try:
            return x - y
        except:
            return -y + x

    def multiply(self, x, y):
        if self.use_modular_arithmetic(x, y):
            return (x*y) % self.cfg["modulus"]
        self.TypeCheck(x, y)
        try:
            return x*y
        except:
            return y*x

    def divide(self, x, y):
        if self.use_modular_arithmetic(x, y):
            return (x//y) % self.cfg["modulus"]
        self.TypeCheck(x, y)
        if y == 0:
            if self.cfg["allow_divide_by_zero"]:
                if x > 0:
                    return m.inf
                elif x < 0:
                    return -m.inf
                else:
                    raise ValueError("%s0/0 is ambiguous" % fln())
            else:
                raise ValueError("%sCan't divide by zero" % fln())
        if isint(x) and isint(y):
            if self.cfg["no_rationals"]:
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

    def Mod(self, n, d):
        self.TypeCheck(n, d)
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

    def integer_divide(self, n, d):
        if self.use_modular_arithmetic(n, d):
            return (Zn(n)//Zn(d)) % self.cfg["modulus"]
        self.TypeCheck(n, d)
        if isint(n) and isint(d):
            return Zn(n) // Zn(d)
        n   = Convert(n, MPF)
        d = Convert(d, MPF)
        return int(m.floor(n/d))

    def bit_and(self, x, y):
        self.TypeCheck(x, y)
        if isint(x) and isint(y):
            return Zn(x) & Zn(y)
        x = Convert(x, INT)
        y = Convert(y, INT)
        return x & y

    def bit_or(self, x, y):
        self.TypeCheck(x, y)
        if isint(x) and isint(y):
            return Zn(x) | Zn(y)
        x = Convert(x, INT)
        y = Convert(y, INT)
        return x | y

    def bit_xor(self, x, y):
        self.TypeCheck(x, y)
        if isint(x) and isint(y):
            return Zn(x) ^ Zn(y)
        x = Convert(x, INT)
        y = Convert(y, INT)
        return x ^ y

    def bit_leftshift(self, x, y):
        self.TypeCheck(x, y)
        if isint(x) and isint(y):
            return Zn(x) << Zn(y)
        x = Convert(x, INT)
        y = Convert(y, INT)
        return x << y

    def bit_rightshift(self, x, y):
        self.TypeCheck(x, y)
        if isint(x) and isint(y):
            return Zn(x) >> Zn(y)
        x = Convert(x, INT)
        y = Convert(y, INT)
        return x >> y

    def percent_change(self, x, y):
        x = Convert(x, MPF)
        y = Convert(y, MPF)
        if x == 0:
            raise ValueError("%sBase is zero for %ch" % fln())
        return 100*(y - x)/x

    def combination(self, x, y):
        if (not self.cfg["coerce"]) and \
           (not isint(x)) and (not isint(y)):
            raise ValueError(self.argument_types % fln())
        x = Convert(x, INT)
        y = Convert(y, INT)
        return int(self.permutation(x, y)//self.Factorial(y))

    def permutation(self, x, y):
        if (not self.cfg["coerce"]) and \
           (not isint(x)) and (not isint(y)):
            raise ValueError(self.argument_types % fln())
        x = Convert(x, INT)
        y = Convert(y, INT)
        return int(self.Factorial(x)//self.Factorial(x - y))

    def power(self, x, y):
        return pow(x, y)

    def atan2(self, x, y):
        return m.atan2(x, y)

    def hypot(self, x, y):
        return m.hypot(x, y)
    #---------------------------------------------------------------------------
    # Unary functions

    def ip(self, x):
        if isint(x):
            return x
        return Convert(x, INT)

    def Fp(self, x):
        if isint(x):
            return m.mpf(0)
        return Convert(x, MPF) - self.ip(x).value

    def reciprocal(self, x):
        if x == 0:
            if self.cfg["allow_divide_by_zero"]:
                return inf
            else:
                raise ValueError("%sDivision by zero" % fln())
        if isint(x):
            return Rational(1, x)
        elif isinstance(x, Rational):
            return Rational(x.d, x.n)
        return m.mpf(1)/x

    def bit_negate(self, x):
        return ~Convert(x, INT)

    def negate(self, x):
        return -x

    def numerator(self, x):
        return Convert(x, RAT).n

    def denominator(self, x):
        return Convert(x, RAT).d

    def apart(self, x):
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

    def ToV(self, y, x):
        'Convert to interval number [y,x]'
        if y > x:
            msg = "%sy register must be <= x register"
            raise ValueError(msg % fln())
        y = Convert(y, MPF)
        x = Convert(x, MPF)
        return mpi(y, x)

    def Chop(self, x):
        n = Number()
        return n(self.Format(x).replace(" ", ""))

    def RealPart(self, x):
        if isinstance(x, m.mpc):
            return x.real
        else:
            return x

    def ImagPart(self, x):
        if isinstance(x, m.mpc):
            return x.imag
        else:
            return x

    def conj(self, x):
        if isinstance(x, m.mpc):
            n = Convert(x, MPC)
            return m.mpc(n.real, -n.imag)
        else:
            return x

    def sqrt(self, x):
        return m.sqrt(x)

    def square(self, x):
        return x*x

    def mid(self, x):
        if isinstance(x, m.mpi):
            return x.mid
        else:
            raise ValueError("%sNeed an interval number for mid" % fln())

    def Factorial(self, x):
        def ExactIntegerFactorial(x):
            if x in self.factorial_cache:
                return self.factorial_cache[x]
            else:
                if x > 2:
                    y = 1
                    for i in xrange(2, x+1):
                        y *= i
                    self.factorial_cache[x] = y
                    return y
        limit = self.cfg["factorial_limit"]
        if limit < 0 or not isint(limit):
            raise SyntaxError("%sFactorial limit needs to be an integer >= 0" % fln())
        if isint(x) and x >= 0:
            if limit == 0 or (limit > 0 and x < limit):
                return ExactIntegerFactorial(x)
        return m.factorial(x)

    def Sum(self, *args):
        s = 0
        try:
            for x in args:
                s = self.add(s, x)
        except Exception, e:
            self.display.msg("%sStack is not large enough, %s" % (fln(), e))
            return None
        return s

    def floor(self, x):
        return m.floor(x)

    def ceil(self, x):
        return m.ceil(x)

    def sin(self, x):
        """
    Usage: x sin

    Returns the sine of the top item on the stack
        """
        return m.sin(x)

    def cos(self, x):
        """
    Usage: x cos

    Returns the cosine of the top item on the stack
        """
        return m.cos(x)

    def tan(self, x):
        """
    Usage: x tan

    Returns the tangent of the top item on the stack
        """
        return m.tan(x)

    def asin(self, x):
        """
    Usage: x asin

    Returns the arc-sine of the top item on the stack
        """
        return m.asin(x)

    def acos(self, x):
        """
    Usage: x acos

    Returns the arc-cosine of the top item on the stack
        """
        return m.acos(x)

    def atan(self, x):
        """
    Usage: x atan

    Returns the arctangent of the top item on the stack
        """
        return m.atan(x)

    def sec(self, x):
        """
    Usage: x sec

    Returns the secant of the top item on the stack
        """
        return m.sec(x)

    def csc(self, x):
        """
    Usage: x csc

    Returns the cosecant of the top item on the stack
        """
        return m.csc(x)

    def cot(self, x):
        """
    Usage: x cot

    Returns the cotangent of the top item on the stack
        """
        return m.cot(x)

    def asec(self, x):
        """
    Usage: x asec

    Returns the arc-secant of the top item on the stack
        """
        return m.asec(x)

    def acsc(self, x):
        """
    Usage: x acsc

    Returns the arc-cosecant of the top item on the stack
        """
        return m.acsc(x)

    def acot(self, x):
        """
    Usage: x acot

    Returns the arc-cotangent of the top item on the stack
        """
        return m.acot(x)

    def sinh(self, x):
        """
    Usage: x sinh

    Returns the hypebolic sine of the top item on the stack
        """
        return m.sinh(x)

    def cosh(self, x):
        """
    Usage: x cosh

    Returns the hypebolic cosine of the top item on the stack
        """
        return m.cosh(x)

    def tanh(self, x):
        """
    Usage: x tanh

    Returns the hypebolic tangent of the top item on the stack
        """
        return m.tanh(x)

    def asinh(self, x):
        """
    Usage: x asinh

    Returns the hypebolic arc-sine of the top item on the stack
        """
        return m.asinh(x)

    def acosh(self, x):
        """
    Usage: x acosh

    Returns the hypebolic arc-cosine of the top item on the stack
        """
        return m.acosh(x)

    def atanh(self, x):
        """
    Usage: x atanh

    Returns the hypebolic arctangent of the top item on the stack
        """
        return m.atanh(x)

    def sech(self, x):
        """
    Usage: x sech

    Returns the hyperbolic secant of the top item on the stack
        """
        return m.sech(x)

    def csch(self, x):
        """
    Usage: x csch

    Returns the hyperbolic cosecant of the top item on the stack
        """
        return m.csch(x)

    def coth(self, x):
        """
    Usage: x coth

    Returns the hyperbolic cotangent of the top item on the stack
        """
        return m.coth(x)

    def asech(self, x):
        """
    Usage: x asech

    Returns the hyperbolic arc-secant of the top item on the stack
        """
        return m.asech(x)

    def acsch(self, x):
        """
    Usage: x acsch

    Returns the hyperbolic arc-cosecant of the top item on the stack
        """
        return m.acsch(x)

    def acoth(self, x):
        """
    Usage: x acoth

    Returns the hyperbolic arc-cotangent of the top item on the stack
        """
        return m.acoth(x)

    def ln(self, x):
        """
    Usage: x ln

    Returns the natural log of the top item on the stack
        """
        return m.ln(x)

    def Ln2(self, x):
        """
    Usage: x log2

    Returns the log2 of the top item on the stack
        """
        return m.ln(x)/m.ln(2)

    def log10(self, x):
        """
    Usage: x log

    Returns the log10 of the top item on the stack
        """
        return m.log10(x)

    def exp(self, x, y):
        """
    Usage: x ^ | x exp

    Returns e raised to the power of top item on the stack (e^x)
        """
        return m.exp(x, y)

    def abs(self, x):
        """
    Usage: x abs

    Returns the absolute value of the top item on the stack
        """
        return m.abs(x)

    def arg(self, x):
        """
    Usage: x arg

    Returns the complex argument of the top item on the stack
        """
        return m.arg(x)

    def ToDegrees(self, x):
        if x == 0: return x
        if isinstance(x, m.mpc):
            raise ValueError("%sNot an appropriate operation for a complex number" % fln())
        return degrees(x)

    def ToRadians(self, x):
        if x == 0: return x
        if isinstance(x, m.mpc):
            raise ValueError("%sNot an appropriate operation for a complex number" % fln())
        return radians(x)

    def gamma(self, x):
        return m.gamma(x)

    def zeta(self, x):
        return m.zeta(x)

    def Ncdf(self, x):
        'Normal probability CDF'
        return ncdf(x, 0, 1)

    def Incdf(self, x):
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

    def hr(self, x):
        'Convert hms to decimal hours'
        x = Convert(x, MPF)
        hours = int(x)
        x -= hours
        x *= 100
        minutes = int(x)
        x -= minutes
        x *= 100
        return hours + minutes/mpf(60) + x/3600

    def hms(self, x):
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

    def rand(self):
        '''Return a uniformly-distributed random number in [0, 1).  We use
        the os.urandom function to return a group of random bytes, then convert
        the bytes to a binary fraction expressed in decimal.
        '''
        numbytes = ceil(mp.prec/mpf(8)) + 1
        bytes = urandom(numbytes)
        number = self.sum([ord(b)*mpf(256)**(-(i+1)) for i, b in enumerate(list(bytes))])
        return number

    #---------------------------------------------------------------------------
    # Other functions

    def Modulus(self, x):
        '''Set up modulus arithmetic with X as the modulus (1 or 0 to cancel)
        '''
        if isinstance(x, m.mpc) or isinstance(x, m.mpi):
            raise ValueError("%sModulus cannot be a complex or interval number" % fln())
        if x == 0:
            self.cfg["modulus"] = 1
        else:
            self.cfg["modulus"] = x
        return None

    def Rationals(self, x):
        '''Show rationals as rationals instead of decimals
        '''
        if x != 0:
            self.cfg["no_rationals"] = True
        else:
            self.cfg["no_rationals"] = False

    def ToggleDowncasting(self, x):
        '''Toggle downcasting: if X, downcast floats to ints if precision permits
        '''
        if x != 0:
            self.cfg["downcasting"] = True
        else:
            self.cfg["downcasting"] = False

    def ClearRegisters(self):
        self.registers = {}

    def Phi(self):
        return m.phi

    def ShowConfig(self):
        d = {True:"on", False:"off"}
        per = d[self.cfg["persist"]]
        st = str(self.cfg["stack_display"])
        lw = self.cfg["line_width"]
        mf = str(self.cfg["mixed_fractions"])
        dc = d[self.cfg["downcasting"]]
        sps = d[self.cfg["fp_show_plus_sign"]]
        am = self.cfg["angle_mode"]
        im = self.cfg["integer_mode"]
        imm = self.cfg["imaginary_mode"]
        sd = str(self.cfg["stack_display"])
        fmt = self.cfg["fp_format"]
        dig = str(self.cfg["fp_digits"])
        ad = str(self.cfg["arg_digits"])
        af = self.cfg["arg_format"]
        pr = str(mp.dps)
        br = d[self.cfg["brief"]]
        nr = d[self.cfg["no_rationals"]]
        cd = d[self.cfg["fp_comma_decorate"]]
        adz = d[self.cfg["allow_divide_by_zero"]]
        iv = self.cfg["iv_mode"]
        cdiv = d[self.cfg["C_division"]]
        dbg = d[get_debug()]
        if 1:
            s = '''Configuration:
      Stack:%(st)s    Commas:%(cd)s   +sign:%(sps)s   Allow divide by zero:%(adz)s
      iv%(iv)s    brief:%(br)s  C-type integer division:%(cdiv)s   Rationals:%(nr)s
      Line width:%(lw)s    Mixed fractions:%(mf)s     Downcasting:%(dc)s
      Complex numbers:  %(imm)s    arguments:%(af)s %(ad)s digits Debug:%(dbg)s
      Display: %(fmt)s %(dig)s digits   prec:%(pr)s  Integers:%(im)s  Angles:%(am)s''' \
        % locals()

        self.display.msg(s)

    def Pi(self):
        return m.mpf(m.mp.pi)

    def E(self):
        return m.mpf(m.mp.e)

    def lastx(self):
        assert self.stack.lastx != None, "Bug:  stack.lastx is None"
        return self.stack.lastx

    def mixed(self, x):
        if x != 0:
            self.cfg["mixed_fractions"] = True
            Rational.mixed = True
        else:
            self.cfg["mixed_fractions"] = False
            Rational.mixed = False

    def swap(self):
        try:
            self.stack.swap()
        except:
            self.display.msg("%sStack is not large enough" % fln())

    def roll(self):
        print "roll"
        self.stack.roll(0)

    def rolld(self):
        print "rolld"
        self.stack.roll(-1)

    def drop(self, x):
        return None

    def drop2(self, y, x):
        return None

    def dropn(self, *args):
        return None

    def dup(self, x):
        self.stack.push(x)
        return x

    def dup2(self, y, x):
        self.stack.push(y)
        self.stack.push(x)
        self.stack.push(y)
        return x

    def dupn(self, *args):
        n = len(args)
        for a in range(1, n+1):
            self.stack.push(args[-a])
        for a in range(1, n+1):
            self.stack.push(args[-a])
        return None

    def depth(self):
        return len(self.stack)

    def Cast(self, x, newtype, use_prec=False):
        '''If use_prec == True, use mp.dps.
        '''
        try:
            try:
                if use_prec == True:
                    digits = 0
                else:
                    digits = max(1, self.fp.num_digits)
            except:
                pass
            return Convert(x, newtype, digits)
        except:
            self.display.msg("%sCouldn't perform conversion" % fln())
            return None

    def Cast_i(self, x):
        return self.Cast(x, INT)

    def Cast_qq(self, x):
        return self.Cast(x, RAT, use_prec=True)

    def Cast_q(self, x):
        return self.Cast(x, RAT, use_prec=False)

    def Cast_r(self, x):
        return self.Cast(x, MPF)

    def Cast_c(self, x):
        return self.Cast(x, MPC)

    def Cast_t(self, x):
        return self.Cast(x, JUL)

    def Cast_v(self, x):
        return self.Cast(x, MPI)

    def Prec(self, x):
        if isint(x) and x > 0:
            mp.dps = int(x)
            self.cfg["prec"] = int(x)
            if self.cfg["fp_digits"] > mp.dps:
                self.cfg["fp_digits"] = mp.dps
            if self.fp.num_digits > mp.dps:
                self.fp.digits(mp.dps)
            return None
        else:
            self.display.msg("You must supply an integer > 0")
            return x

    def digits(self, x):
        if int(x) == x:
            if x >= 0:
                d = min(int(x), mp.dps)
                self.cfg["fp_digits"] = d
                self.fp.digits(min(int(x), mp.dps))
                return None
            else:
                self.display.msg("Use an integer >= 0")
                return x
        else:
            self.display.msg("You must supply an integer >= 0")
            return x

    def SetStackDisplay(self, x):
        msg = "Stack display size be an integer >= 0"
        if int(x) == x:
            if x >= 0:
                self.cfg["stack_display"] = int(x)
                return None
            else:
                self.display.msg(msg)
                return x
        else:
            self.display.msg(msg)
            return x

    def Round(self, y, x):
        '''Round y to the nearest x.  Algorithm from PC Magazine, 31Oct1988,
        pg 435.
        '''
        y = Convert(y, MPF)
        x = Convert(x, MPF)
        sgn = 1
        if y < 0: sgn = -1
        return sgn*int(mpf("0.5") + abs(y)/x)*x

    def In(self, y, x):
        '''Both x and y are expected to be interval numbers or x a number and
        y and interval number.  Returns the boolean 'x in y'.
        '''
        msg = "%sy needs to be an interval number or Julian interval"
        if isinstance(y, m.mpi):
            if self.testing:
                if x not in y:
                    s = "x was not in y:" + nl
                    s += "  x = " + repr(x) + nl
                    s += "  y = " + repr(y)
                    self.display.msg(s)
                    exit(1)
            return x in y
        elif isinstance(y, Julian):
            if not isinstance(y.value, m.mpi):
                raise ValueError(msg % fln())
            if self.testing:
                if x not in y.value:
                    s = "x was not in y:" + nl
                    s += "  x = " + repr(x) + nl
                    s += "  y = " + repr(y.value)
                    self.display.msg(s)
                    exit(1)
            if isinstance(x, Julian):
                return x.value in y.value
            else:
                return x in y.value
        else:
            raise ValueError(msg % fln())

    #---------------------------------------------------------------------------

    def Dummy(self):
        raise Exception("%sDummy():  shouldn't have executed this function" % fln())

    def NotImpl(self):
        print "Not implemented yet"

    def NotImplx(self, x):
        print "Not implemented yet"
        return x

    def Debug(self, x):
        if x != 0:
            toggle_debug(True)
        else:
            toggle_debug(False)

    def Reset(self):
        self.ClearRegisters()
        self.ClearStack()
        self.cfg.clear()
        self.cfg.update(self.cfg_default)
        self.ConfigChanged()

    def Show(self):
        '''Show the full precision of x.
        '''
        def showx(self, x, prefix=""):
            if mp.dps < 2:
                return
            sign, mant, exponent = to_digits_exp(x._mpf_, mp.dps)
            s = mant[0] + "." + mant[1:] + "e" + str(exponent)
            if sign ==  -1:
                s = "-" + s
            self.display.msg(" " + prefix + s)
        from mpmath.libmp.libmpf import to_digits_exp
        x = stack[0]
        if isinstance(x, m.mpf):
            showx(x)
        elif isinstance(x, m.mpc):
            self.display.msg(" x is complex")
            showx(x.real, "  x.real:  ")
            showx(x.imag, "  x.imag:  ")
        elif isinstance(x, m.mpi):
            self.display.msg(" x is an interval number")
            showx(x.a, "  x.a:  ")
            showx(x.b, "  x.b:  ")
        # Return False to avoid displaying the stack
        return False

    def ClearStack(self):
        self.stack.clear_stack()

    def comma(self, x):
        if x != 0:
            self.cfg["fp_comma_decorate"] = True
        else:
            self.cfg["fp_comma_decorate"] = False
        mpFormat.comma_decorate = self.cfg["fp_comma_decorate"]

    def width(self, x):
        if isint(x) and x > 20:
            self.cfg["line_width"] = int(x)
        else:
            self.display.msg("width command requires an integer > 20")

    def Rectangular(self):
        self.cfg["imaginary_mode"] = "rect"

    def Polar(self):
        self.cfg["imaginary_mode"] = "polar"

    def fix(self):
            self.cfg["fp_format"] = "fix"

    def sig(self):
            self.cfg["fp_format"] = "sig"

    def sci(self):
            self.cfg["fp_format"] = "sci"

    def eng(self):
            self.cfg["fp_format"] = "eng"

    def engsi(self):
            self.cfg["fp_format"] = "engsi"

    def none(self):
            self.cfg["fp_format"] = "none"

    def dec(self):
            self.cfg["integer_mode"] = "dec"

    def hex(self):
            self.cfg["integer_mode"] = "hex"

    def oct(self):
            self.cfg["integer_mode"] = "oct"

    def bin(self):
            self.cfg["integer_mode"] = "bin"

    def ip(self):
            self.cfg["integer_mode"] = "ip"

    def iva(self):
            self.cfg["iv_mode"] = "a"
            Julian.interval_representation = "a"

    def ivb(self):
            self.cfg["iv_mode"] = "b"
            Julian.interval_representation = "b"

    def ivc(self):
            self.cfg["iv_mode"] = "c"
            Julian.interval_representation = "c"

    def on(self):
            self.display.on()
            return status_ok_no_display

    def off(self):
            self.display.off()
            return status_ok_no_display

    def deg(self):
            self.cfg["angle_mode"] = "deg"

    def rad(self):
            self.cfg["angle_mode"] = "rad"

    def brief(self, x):
        if x != 0:
            self.cfg["brief"] = True
        else:
            self.cfg["brief"] = False

    def Flatten(self, n=0):
        '''The top of the stack contains a sequence of values.  Remove them
        and put them onto the stack.  If n is 0, it means do this with all the
        elements; otherwise, just do it with the left-most n elements and
        discard the rest.
        '''
        assert n >= 0
        if not len(self.stack):
            return
        items = list(self.stack.pop())
        if not n:
            n = len(items)
        self.stack.stack += items[:n]

    def ConfigChanged(self):
        try:
            self.fp.digits(self.cfg["fp_digits"])
        except:
            raise ValueError("%s'fp_digits' value in configuration is bad" % fln())
        try:
            self.ap.digits(self.cfg["arg_digits"])
        except:
            raise ValueError("%s'arg_digits' value in configuration is bad" % fln())
        mpFormat.comma_decorate = self.cfg["fp_comma_decorate"]
        mpFormat.cuddle_si = self.cfg["fp_cuddle_si"]
        mpFormat.explicit_plus_sign = self.cfg["fp_show_plus_sign"]
        Rational.mixed = self.cfg["mixed_fractions"]
        Zn().C_division = self.cfg["C_division"]
        if isint(self.cfg["prec"]) and int(self.cfg["prec"]) > 0:
            mp.dps = self.cfg["prec"]
        else:
            raise ValueError("%s'prec' value in configuration is bad" % fln())

    def GetFullPath(self, s):
        '''If s doesn't have a slash in it, prepend it with the directory where
        our executable is.  If it does have a slash, verify it's usable.
        '''
        if "/" not in s:
            path, file = os.path.split(sys.argv[0])
            return os.path.join(path, s)
        else:
            return os.normalize(s)

    def SaveConfiguration(self):
        if self.cfg["persist"]:
            c, r, s = self.cfg["config_file"], self.cfg["config_save_registers"], \
                      self.cfg["config_save_stack"]
            msg = "%sCould not write %s to:\n  %s"
            if c:
                try:
                    p = GetFullPath(c)
                    WriteDictionary(p, "self.cfg", self.cfg)
                except:
                    self.display.msg(msg % (fln(), "config", p))
            if r:
                try:
                    p = GetFullPath(r)
                    WriteDictionary(p, "registers", self.registers)
                except:
                    self.display.msg(msg % (fln(), "registers", p))
            if s:
                try:
                    p = GetFullPath(s)
                    WriteList(p, "mystack", self.stack.stack)
                except:
                    self.display.msg(msg % (fln(), "stack", p))

    def GetLineWidth(self):
        '''Try to get the current console's linewidth by reading the
        COLUMNS environment variable.  If it's present, use it to set
        cfg["line_width"].
        '''
        try:
            self.cfg["line_width"] = int(environ["COLUMNS"]) - 1
        except:
            pass

    def GetConfiguration(self):
        cf = self.cfg["config_file"]
        self.GetLineWidth()
        self.ConfigChanged()
        us = "Using default configuration"
        if self.cfg["persist"]:
            c, r, s = self.cfg["config_file"], self.cfg["config_save_registers"], \
                      self.cfg["config_save_stack"]
            if c and not self.use_default_config_only:
                try:
                    d = {}
                    p = GetFullPath(c)
                    execfile(p, d, d)
                    self.cfg = d["cfg"]
                    self.ConfigChanged()
                except:
                    msg = "%sCould not read and execute configuration file:" % fln() + \
                          nl + "  " + c
                    self.display.msg(msg)
                    self.display.msg(us)
            if r:
                try:
                    d = {}
                    p = GetFullPath(r)
                    execfile(p, d, d)
                    self.registers = d["registers"]
                except:
                    msg = "%sCould not read and execute register file:"  % fln() + \
                          nl + "  " + r
                    self.display.msg(msg)
            if s:
                try:
                    d = {}
                    p = GetFullPath(s)
                    execfile(p, d, d)
                    global stack
                    self.stack.stack = d["mystack"]
                except:
                    msg = "%sCould not read and execute stack file:" % fln() + \
                          nl + "  " + s
                    self.display.msg(msg)

    def DisplayStack(self):
        size = self.cfg["stack_display"]
        assert size >= 0 and isint(size)
        self.display.msg(self.stack._string(self.Format, size))
        if self.cfg["modulus"] != 1:
            self.display.msg(" (mod " + self.Format(self.cfg["modulus"])+ ")")

    def EllipsizeString(self, s, desired_length, ellipsis):
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
            self.display.msg("Warning:  floating point number was 'damaged' by inserting ellipsis")
        return new_s

    def Format(self, x):
        '''Format the four different types of numbers.  Return a string in
        the proper format.
        '''
        width = abs(self.cfg["line_width"])
        brief = self.cfg["brief"]
        e = self.cfg["ellipsis"]
        im = self.cfg["integer_mode"]
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
            elif im == "ip":
                s = x.ip()
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
                s = self.EllipsizeString(s, width - stack_header_allowance, e)
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
                s = self.EllipsizeString(s, size, e)
            return s
        elif isinstance(x, mpf):
            s = str(x)
            if self.cfg["fp_format"] != "none":
                s = self.fp.format(x, self.cfg["fp_format"])
            if brief:
                s = self.EllipsizeString(s, width - stack_header_allowance, e)
            return s
        elif isinstance(x, mpc):
            space = self.cfg["imaginary_space"]
            s = ""
            if space:
                s = " "
            sre = str(x.real)
            sim = str(abs(x.imag))
            if self.cfg["fp_format"] != "none":
                sre = self.fp.format(x.real, self.cfg["fp_format"])
                sim = self.fp.format(abs(x.imag), self.cfg["fp_format"]).strip()
            if self.cfg["ordered_pair"]:
                if brief:
                    size = (width - stack_header_allowance)//2 - 4
                    sre = self.EllipsizeString(sre, size, e).strip()
                    sim = self.EllipsizeString(sim, size, e)
                s = "(" + sre + "," + s + sim + ")"
            else:
                mode = self.cfg["imaginary_mode"]
                first = self.cfg["imaginary_unit_first"]
                unit = self.cfg["imaginary_unit"]
                if mode == "polar":
                    # Polar mode
                    sep = self.cfg["polar_separator"]
                    angle_mode = self.cfg["angle_mode"]
                    mag = abs(x)
                    ang = arg(x)
                    if angle_mode == "deg":
                        ang_sym = self.cfg["degree_symbol"]
                        ang *= 180/pi
                    else:
                        ang_sym = "rad"
                    if angle_mode != "deg" and angle_mode != "rad":
                        self.display.msg("Warning:  bad angle_mode('%s') in configuration" \
                            % angle_mode)
                    m = str(mag)
                    a = str(ang)
                    if self.cfg["fp_format"] != "none":
                        m = self.fp.format(mag, self.cfg["fp_format"])
                        a = self.ap.format(ang, self.cfg["arg_format"])
                    if brief:
                        size = (width - stack_header_allowance)//2 - \
                               len(sep) - 4
                        mag = self.EllipsizeString(m, size, e)
                        ang = self.EllipsizeString(a, size, e)
                    s = m + self.cfg["polar_separator"] + a + " " + ang_sym
                else:
                    # Rectangular mode
                    if brief:
                        size = (width - stack_header_allowance)//2 - 1
                        sre = self.EllipsizeString(sre, size, e)
                        sim = self.EllipsizeString(sim, size, e)
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
                    self.display.msg("Warning:  bad imaginary_mode('%s') in configuration" \
                        % mode)
            return s
        elif isinstance(x, mpi):
            a = str(x.a)
            b = str(x.b)
            mid = x.mid
            delta = x.delta/2
            f = self.cfg["fp_format"]
            mode = self.cfg["iv_mode"]
            sp = ""
            if self.cfg["iv_space"]:
                sp = " "
            if self.cfg["fp_format"] != "none":
                a = self.fp.format(x.a, f)
                b = self.fp.format(x.b, f).strip()
                mid = self.fp.format(mid, f)
                delta = self.fp.format(delta, f).strip()
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
                if self.cfg["fp_format"] != "none":
                    m = self.fp.format(a, f)
                    p = self.fp.format(b, f).strip()
                s = m + sp + "(" + p + "%)"
            elif mode == "c":
                br1, br2 = self.cfg["iv_brackets"]
                s = br1 + a.strip() + "," + sp + b + br2
            else:
                raise ValueError("%s'%s' is unknown iv_mode in configuration" % \
                    (fln(), mode))
        elif isinstance(x, Julian):
            return str(x)
        else:
            raise Exception("%sError in Format():  Unknown number format" % fln())
        return s

    def WriteList(self, filename, name, list):
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
            self.display.msg(msg)
            raise

    def WriteDictionary(self, filename, name, dictionary):
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
            self.display.msg(msg)
            raise

    def EditDictionary(self, name, dictionary):
        if not self.cfg["editor"]:
            raise RuntimeError("%sEditor is not defined in configuration" % fln())
        if not self.cfg["tempfile"]:
            filename = mkstemp(prefix="hctemp")
        else:
            filename = self.cfg["tempfile"]
        try:
            WriteDictionary(self.cfg["tempfile"], name, dictionary)
        except:
            self.display.msg("%sUnable to edit dictionary '%s'" % (fln(), name))
            return False
        # Open the file in the editor
        cmd = self.cfg["editor"] + " " + filename
        system(cmd)  # We use the os.system command because it blocks
        # Execute the new file
        newdict = {}
        try:
            execfile(filename, newdict)
        except Exception, e:
            msg = "%sError trying to read in the modified dictionary:" % fln() \
                  + nl + str(e)
            self.display.msg(msg)
            return False
        dictionary.clear()
        dictionary.update(newdict[name])
        # Remove the temporary file if it's not set in cfg
        if not self.cfg["tempfile"]:
            os.remove(filename)
        return True

    def EditConfiguration(self):
        if EditDictionary("cfg", self.cfg):
            self.ConfigChanged()

    def EditStack(self):
        if not self.cfg["editor"]:
            raise RuntimeError("%sEditor is not defined in configuration" % fln())
        if not self.cfg["tempfile"]:
            filename = mkstemp(prefix="hctemp")
        else:
            filename = self.cfg["tempfile"]
        name = "mystack"
        self.fp = open(filename, "wb")
        p = self.fp.write
        p("from mpmath import *" + nl + nl)
        p("mp.dps = " + str(mp.dps) + nl + nl)
        p(name + " = [" + nl)
        indent = "  "
        for item in self.stack.stack:
            p(indent + repr(item) + "," + nl)
        p("]" + nl)
        self.fp.close()
        # Open the file in the editor
        cmd = self.cfg["editor"] + " " + filename
        system(cmd)  # We use the os.system command because it blocks
        # Execute the new file
        newdict = {}
        try:
            execfile(filename, newdict)
        except Exception, e:
            msg = "%sError trying to read in the modified stack:" % fln() + nl + str(e)
            self.display.msg(msg)
            return
        self.stack.stack = newdict[name]
        # Remove the temporary file if it's not set in cfg
        if not self.cfg["tempfile"]:
            os.remove(filename)

    def EditRegisters(self):
        EditDictionary("registers", self.registers)

    def PrintRegisters(self):
        if not self.registers:
            raise ValueError("%sThere are no registers defined" % fln())
        names = self.registers.keys()
        names.sort()
        lengths = [len(name) for name in names]
        fmt = "%%-%ds  %%s\n" % max(lengths)
        s = ""
        for name in names:
            s += fmt % (name, self.Format(self.registers[name]))
        self.display.msg(s)

    def CheckEnvironment(self):
        '''Look at the environment variables defined in
        cfg["environment"] and execute any commands in them.  Note we only
        do this if we're not using the default configuation (-d option).
        '''
        if self.use_default_config_only: return
        for var in self.cfg["environment"]:
            if var in os.environ:
                try:
                    finished = False
                    status = None
                    cmd_line = os.environ[var]
                    cmds = ParseCommandInput(cmd_line)
                    n = len(cmds) - 1
                    for i, cmd in enumerate(cmds):
                        status = ProcessCommand(cmd, self.commands_dict, i==n)
                        if status == status_quit:
                            finished = True
                    if finished:
                        raise Exception("%sGot a quit command" % fln())
                except Exception, e:
                    msg = "%sFor environment variable '%s', got exception:" + nl
                    self.display.msg(msg % (fln(), var) + str(e))


    def RunChecks(self):
        '''Run checks on various things to flag things that might need to be
        fixed.
        '''
        if not self.run_checks:  return
        # Look for commands that don't have associated help strings
        s = ""
        for cmd in self.commands_dict:
            if cmd[0] == " ":  cmd = cmd[1:]
            if cmd in helpinfo:
                if len(helpinfo[cmd]) == 0:
                    s += ("'%s' command missing help string" % cmd) + nl
            else:
                s += ("'%s' command has no helpinfo dictionary entry" % cmd) + nl
        if s: self.display.msg(s)

    def ExecutedCommandOK(self, cmd, args, commands_dict):
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
                self.display.msg("%s" % fln() + str(e))
                return False
        elif num_stack_args == 1:
            # Unary function
            try:
                x = stack[0]
                self.stack.lastx = x
                if isinstance(x, Zn):
                    if cmd == "abs":
                        y = x.__abs__()
                    else:
                        x = int(x)
                        y = func(x)
                else:
                    y = func(x)
                self.stack.pop()
                if y != None:
                    if isint(y):
                        y = Zn(y)
                    self.stack.push(y)
                    if isinstance(y, tuple) or isinstance(y, list):
                        Flatten()
            except KeyboardInterrupt:
                self.display.msg("%sInterrupted" % fln())
                return False
            except Exception, e:
                self.display.msg("%s" % fln() + str(e))
                return False
        elif num_stack_args == 2:
            # Binary function
            size = len(self.stack)
            try:
                x, y = stack[0], stack[1]
                x1 = x
                if isinstance(x, Zn): x = int(x)
                if isinstance(y, Zn): y = int(y)
            except Exception, e:
                self.display.msg("%s" % fln() + str(e))
                return False
            try:
                self.stack.pop()
                self.stack.pop()
            except Exception, e:
                self.display.msg("%s" % fln() + str(e))
                # Fix stack if corrupted
                if len(self.stack) == size - 1:
                    self.stack.append(x)
                elif len(self.stack) == size - 2:
                    self.stack.append(y)
                    self.stack.append(x)
                return False
            try:
                self.stack.lastx = x1
                result = func(y, x)
                if result != None:
                    if isint(result):
                        result = Zn(result)
                    self.stack.push(result)
            except KeyboardInterrupt:
                self.display.msg("%sInterrupted" % fln())
                return False
            except Exception, e:
                self.display.msg("%s" % fln() + str(e))
                return False
        elif num_stack_args == 'x':
            # Binary function
            size = len(self.stack)
            n = 0
            try:
                n = stack[0]
                n = int(n)
                last = stack[n]
            except:
                self.display.msg("Not enonugh arguments")
                return False
            args = []
            x1 = self.stack.pop()
            try:
                for i in range(n):
                    x = self.stack.pop()
                    if isinstance(x, Zn): x = int(x)
                    args.append(x)
            except Exception, e:
                self.display.msg("%s" % fln() + str(e))
                return False
            try:
                self.stack.lastx = x1
                result = func(*args)
                if result != None:
                    if isint(result):
                        result = Zn(result)
                    self.stack.push(result)
            except KeyboardInterrupt:
                self.display.msg("%sInterrupted" % fln())
                return False
            except Exception, e:
                self.display.msg("%s" % fln() + str(e))
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

    def GetRegisterName(self, cmd):
        cmd = strip(cmd)
        if len(cmd) < 2:
            raise ValueError("%sYou must give a register name" % fln())
        return cmd[1:]

    def RecallRegister(self, cmd):
        name = GetRegisterName(cmd)
        if name not in self.registers:
            raise ValueError("%sRegister name '%s' is not defined" % (fln(), name))
        self.stack.push(self.registers[name])
        return status_ok

    def StoreRegister(self, cmd):
        name = GetRegisterName(cmd)
        if len(self.stack) == 0:
            raise Exception("%sStack is empty" % fln())
        self.registers[name] = stack[0]
        return status_ok

    def EditXRegister(self):
        try:
            d = {"x":stack[0]}
            EditDictionary("x_register", d)
            stack[0] = d["x"]
        except Exception, e:
            raise Exception("%sCouldn't edit x" % fln())

    def C_int(self, cmd, val):
        print '%s, %s' %(cmd, val)
        try:
            n = int(val)
        except:
            msg = "%%s'%s' is not a valid integer for int command" % val
            raise ValueError(msg)

        if n > 0:
            if n < 1:
                msg = "%sInteger for int command must be > 0"
                raise ValueError(msg % fln())
            Number.bits = n
            Zn().bits = n
        else:
            Number.bits = 0
            Zn().bits = 0
        # TODO This is ugly and needs refactoring...
        if cmd == 's':
            Number.signed = True
            Zn().signed = True
        else:
            Number.signed = False
            Zn().signed = False

    def C_sX(self, val):
        """
    Usage: sX where X is 'X' or X is an integer
           sX -> set C signed integer mode with bits defined by the
                top value on the stack
           s5 -> set C signed integer mode with 5 bits
        """
        self.C_int('s', val)

    def C_uX(self, val):
        """
    Usage: uX where X is 'X' or X is an integer
           uX -> set C unsigned integer mode with bits defined by the
                top value on the stack
           u5 -> set C unsigned integer mode with 5 bits
        """
        self.C_int('u', val)

    def Bang(self, cmd):
        '''If the command is !, give a list of the python scripts that
        are in cfg["helper_scripts"].  If there's an argument, execute
        that script and push the returned number on the stack.
        '''
        import os.path, glob
        try:
            dir = os.path.normpath(self.cfg["helper_scripts"])
            func = self.cfg["helper_script_function_name"]
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
                    self.display.msg(s)
                else:
                    name = cmd[1:]
                    sys.path.insert(0, dir)
                    s = "from %s import %s\nresult = %s(display)\n" % \
                        (name, func, func)
                    co = compile(s, "", "exec")
                    d = {"display":self.display}
                    eval(co, d, d)
                    result = d["result"]
                    if result != None:
                        # TODO: Need to validate that result is a valid stack
                        # object.
                        self.stack.push(result)
            except Exception, e:
                raise Exception("%s'%s' failed:\n%s" % (fln(), cmd, str(e)))

    def Tee(self, cmd):
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
            self.display.logon(f)
            self.tee_is_on = True
        except:
            raise Exception("%sCouldn't open '%s' for tee" % (fln(), file))

    def TeeOff(self):
        try:
            self.display.logoff()
            self.tee_is_on = False
        except:
            pass

    def ExpandCommand(self, cmd):
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

    def ParseCommandInput(self, cmd):
        '''cmd is a nonempty string and needs to be parsed.  If it contains the
        cfg["command_separator"] string, then the user wanted those to separate
        commands, as some of the individual commands contain whitespace.
        Otherwise, parse on whitespace.  Return a list of one or more command
        strings.
        '''
        assert cmd, "Error in program:  cmd is empty string"
        sep = self.cfg["command_separator"]
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

    def GreaterThanEqual(self, x, y):
        'If x >= y, return True; otherwise, return False.'
        result = (x >= y)
        if not result and self.testing: exit(1)
        return result

    def GreaterThan(self, x, y):
        'If x > y, return True; otherwise, return False.'
        result = (x > y)
        if not result and self.testing: exit(1)
        return result

    def LessThanEqual(self, x, y):
        'If x <= y, return True; otherwise, return False.'
        result = (x <= y)
        if not result and self.testing: exit(1)
        return result

    def LessThan(self, x, y):
        'If x < y, return True; otherwise, return False.'
        result = (x < y)
        if not result and self.testing: exit(1)
        return result

    def Equal(self, x, y):
        'If x and y are equal, return True; otherwise, return False.'
        result = (x == y)
        if not result and self.testing:
            exit(1)
        return result

    def NotEqual(self, x, y):
        'If x and y are not equal, return True; otherwise, return False.'
        result = (x != y)
        if not result and self.testing:
            exit(1)
        return result

    def DisplayEqual(self, x, y):
        '''If x and y are equal, return True; otherwise, return False.
        IMPORTANT:  the test of equality is whether the string
        representations in the current display mode match.  If they do,
        the numbers are equal.  If testing is True, then if the two
        numbers compare false, we exit with a status of 1.
        '''
        sx, sy = self.Format(x), self.Format(y)
        result = (sx == sy)
        if not result and self.testing:
            exit(1)
        return result

    def ReadInputFromFile(self, command, commands_dict):
        stream = open(command[2:])
        while stream:
            cmd_line = GetLineOfInput(stream)
            if cmd_line == self.eof: break
            if cmd_line == self.comment_line or cmd_line == "": continue
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

    def ProcessSpecialCommand(self, cmd, commands_dict):
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
            self.cfg["fp_format"] = "fix"
        elif cmd == "sig":
            self.cfg["fp_format"] = "sig"
        elif cmd == "sci":
            self.cfg["fp_format"] = "sci"
        elif cmd == "eng":
            self.cfg["fp_format"] = "eng"
        elif cmd == "engsi":
            self.cfg["fp_format"] = "engsi"
        elif cmd == "none":
            self.cfg["fp_format"] = "none"
        elif cmd == "dec":
            self.cfg["integer_mode"] = "dec"
        elif cmd == "hex":
            self.cfg["integer_mode"] = "hex"
        elif cmd == "oct":
            self.cfg["integer_mode"] = "oct"
        elif cmd == "bin":
            self.cfg["integer_mode"] = "bin"
        elif cmd == "ip":
            self.cfg["integer_mode"] = "ip"
        elif cmd == "iva":
            self.cfg["iv_mode"] = "a"
            Julian.interval_representation = "a"
        elif cmd == "ivb":
            self.cfg["iv_mode"] = "b"
            Julian.interval_representation = "b"
        elif cmd == "ivc":
            self.cfg["iv_mode"] = "c"
            Julian.interval_representation = "c"
        elif cmd == "on":
            self.display.on()
            return status_ok_no_display
        elif cmd == "off":
            self.display.off()
            return status_ok_no_display
        elif cmd == "eps":
            self.stack.push(eps)
        elif cmd == "deg":
            self.cfg["angle_mode"] = "deg"
        elif cmd == "rad":
            self.cfg["angle_mode"] = "rad"
        elif cmd == "prst" or cmd == ".":
            if len(self.stack) > 0:
                self.display.msg(self.stack._string(self.Format))
                if self.cfg["modulus"] != 1:
                    self.display.msg(" (mod " + self.Format(self.cfg["modulus"])+ ")")
                return status_ok_no_display
        else:
            return status_unknown_command
        return status_ok

    def ProcessCommand(self, cmd, commands_dict, last_command):
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
        if self.tee_is_on:
            self.display.log(cmd)
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
            self.display.msg("%s" % fln() + str(e))
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
                        self.stack.push(num)
                        ok = True
                except Exception, e:
                    self.display.msg("%s" % fln() + str(e))
                    return status_error
            # Handle the help command with an argument specially
            if not ok and len(cmd) > 1 and cmd[0] == "?":
                Help(commands_dict, cmd[1:])
                ok = True
            # The apostrophe is another special command
            if not ok and len(cmd) == 2 and cmd[0] == "'":
                self.stack.push(ord(cmd[1]))
                ok = True
            # Now see if we can identify this command
            if not ok:
                x = c.identify_cmd(cmd)
                if isinstance(x, type("")):
                    try:
                        ok = ExecutedCommandOK(x, arg, commands_dict)
                        if self.cfg["modulus"] != 1:
                            if len(self.stack):
                                y = self.Mod(stack[0], self.cfg["modulus"])
                                self.stack.pop()
                                self.stack.push(y)
                    except KeyboardInterrupt:
                        self.display.msg("%sProcessing interrupted" % fln())
                        return status_interrupted
                    except Exception, e:
                        self.display.msg("%sUnexpected exception:\n" % fln() + str(e))
                        return status_error
                elif isinstance(x, type([])):  # It was an ambiguous command
                    x.sort()
                    self.display.msg("Ambiguous: " + ' '.join(x))
                    return status_error
                else:  # Dunno
                    self.display.msg("Command '%s' not recognized" % cmd)
                    return status_error
            if x == "quit":
                return status_quit
        if ok and last_command:
            if len(self.stack):
                try:
                    y = self.DownCast(self.stack.pop())
                    self.stack.push(y)
                except Exception, e:
                    self.display.msg("%sDowncast failed:  " % fln() + str(e))
                self.DisplayStack()
            else:
                #self.display.msg("Stack is empty")
                pass
            return status_ok

    def GetLineOfInput(self, stream=None):
        #
        if stream:
            s = stream.readline()
        elif self.process_stdin:
            s = sys.stdin.readline()
        else:
            s = raw_input(self.cfg["prompt"])
        # Log the line received
        if s and s[-1] == nl:
            self.display.log('--> "%s"' % s, suppress_nl=True)
        else:
            self.display.log('--> "%s"' % s)
        if s == "":
            s = self.eof
            self.stdin_finished = True
        else:
            s = strip(s)
        pos = s.find("#")  # Delete comments
        if pos != -1:
            s = s[:pos]
            if pos == 0:
                # This line was nothing but a comment
                return self.comment_line
        return s

    def cleanup(self):
        readline.write_history_file(os.path.expanduser('~')+'/.pycalc/history')
    
    def show_stack(self):
        depth = len(self.stack)
        if self.stack_index:
            template = "%%(index) %dd: %%(value)s" % (2+int(m.log10(max(depth,1))))
        else:
            template = "%(value)s"
        for v in self.stack:
            print template % {'index': depth, 'value':
                v.show(self.cfg["integer_mode"], self.cfg["prec"], self.vector_mode, self.angle_mode)
            }
            depth -= 1
    
    def push(self, val):
        if val is None:
            raise Exception('BAD! val is None at %s'%_functionId())
        try:
            self.stack.push(val)
        except:
            print type(val)
            raise Exception('BAD! at %s'%_functionId())
    
    def pop(self):
        return self.stack.pop()
    
    def peek(self):
        return self.stack[len(self.stack)-1]
    
    def read_line(self):
        mode = ''
        angle = ''
        if self.vector_mode == Calculator.VECTOR_CARTESIAN:
            mode = 'cart'
        elif self.vector_mode == Calculator.VECTOR_POLAR:
            mode = 'polar'
        if self.angle_mode == Calculator.ANGLE_DEGREES:
            angle = 'deg'
        elif self.angle_mode == Calculator.ANGLE_RADIANS:
            angle = 'rad'
        prompt = "%s|%s|pycalc> " % (mode, angle)
        try:
            line = raw_input(prompt)
        except KeyboardInterrupt:
            print
            sys.exit()
        # it looks like readline automatically adds stuff to history
        #readline.add_history(line)
        return line
        return self.chomp(line)
    
    def chomp(self, line):
        return self.chomppost.sub("", self.chomppre.sub("", line))
    
    def token(self):
        # snag the next token from the line
        line = self.read_line()
        #print "got new line: '%s'" % line
        success, taglist, next = TextTools.tag(line, self.parser)
        while self.chomp(line) != '':
            if not success:
                raise ParseError('Invalid token: %s'%line)
            #print "'%s' yielding '%s', '%s'" % (line, self.chomp(line[:next]),taglist)
            yield self.chomp(line[:next]), taglist, line[next:]
            line = self.chomp(line[next:])
            #line = line[next:]
            success, taglist, next = TextTools.tag(line, self.parser)

    def prepare_args(self, n):
        args = []
        if n == 'x':
            n = int(self.pop())
        #print "stack size is %d"%len(self.stack)
        if n > len(self.stack):
            raise InsufficientStackSize("Looking for %d args" % n)
        for i in range(n):
            val = self.pop()
            if isinstance(val, Zn): val = int(val)
            args.insert(0, val)
        return args
    
    def run(self):
        NGen = Number()
        cints = regex.compile(r"[su][0-9]+")
        while True:
            arg = ''
            try:
                for arg,tag,line in self.token():
                    #print arg,tag,line
                    if arg in ['help', '?']:
                        self.commands_dict['help'][0](line)
                        break
                    elif cints.match(arg):
                        self.C_int(arg[0], arg[1:])
                    elif arg in self.commands_dict:
                        args = self.prepare_args(self.commands_dict[arg][1])
                        retval = self.commands_dict[arg][0](*args)
                        if retval is not None:
                            if isint(retval):
                                retval = Zn(retval)
                            self.push(retval)
                    elif arg in self.constants:
                        self.push(self.constants[arg])
                    # these are the base tokens for functions and constants
                    elif arg in ['null', 'nop']:
                        pass
                    else:
                        # this should be a number....
                        num = self.chomp(arg)
                        #print "num = '%s', arg = '%s'"%(num,arg)
                        if len(num) > 0:
                            try:
                                num = NGen(self.chomp(arg))
                                if num is not None:
                                    self.push(num)
                            except ValueError:
                                print "Invalid input: ", arg
                if arg not in ['help', '?']:
                    self.DisplayStack()
            except EOFError:
                break
            except ParseError:
                type,value,tb = sys.exc_info()
                print value
            except IndexError:
                if len(self.stack) == 0:
                    print "Empty stack"
                else:
                    print "Insufficient arguments"
            except SystemExit:
                raise
            except:
                print "Something bad happened.  Don't do that again!"
                type,value,tb = sys.exc_info()
                traceback.print_exception(type, value, tb, None, sys.stdout)
        readline.write_history_file()
    
    def help(self, args=None):
        """
    Usage: help [function]

    Lists the functions implemented or displays help for the
    requested function
        """
        if args is not None:
            args = args.split()
            if args:
                arg = args[0]
                if arg in self.commands_dict:
                    if self.commands_dict[arg][0].__doc__ is None:
                        print "No help for %s" % arg
                    else:
                        print self.commands_dict[arg][0].__doc__
                else:
                    print "unknown function:", arg
                return
        maxlen = 0
        functions = []
        for k in self.commands_dict.iterkeys():
            maxlen = max(maxlen, len(k))
            functions.append(k)
        functions.sort();
        maxlen += 1
        printed = 0
        for k in functions:
            s = k + " "*maxlen
            print s[0:maxlen],
            printed += maxlen
            if printed > (72-maxlen):
                print
                printed = 0
        print "\n"
        print "Delimiters are space, tab, and newline.\n"
        desired_functions = [ 'abs', 'acos', 'acosh', 'arg', 'asin', 'asinh', 'atan', 'atan2', 'atanh', 'cbrt', 'ceil', 'char', 'chs', 'cosh', 'deg', 'depth', 'div', 'erf', 'erfc', 'expm', 'fact', 'floor', 'gcd', 'hypot', 'ip', 'j0', 'j1', 'jn', 'ld', 'ldb', 'lg', 'lgamma', 'lnp1', 'over', 'pick', 'pop', 'push', 'rad', 'rand', 'rdz', 'rint', 'rnd', 'rot', 'rl', 'rlb', 'sq', 'sqr', 'sr', 'srb', 'swap', 'tanh', 'y0', 'y1', 'yn', '%t']
        unimplemented = [ k for k in desired_functions if k not in self.commands_dict.keys()]
        print "unimplemented functions may include:", ' '.join(unimplemented)


    def list_constants(self):
        """
    Usage: constants

    Lists the constants available for use by name
        """
        for a,k in self.constants.iteritems():
            print "%s = %s" % (a, k.show(self.base, self.cfg["prec"], self.vector_mode, self.angle_mode))

    def warranty(self):
        """
    Usage: warranty

    Displays the license and warranty information
        """
        print license
    
    def todo(self):
        """
    Usage: todo

    Displays the things that still need to be fixed
        """
        print """
parse vector [2 3]
raise numbers to non-integer powers
raise complex numbers to a power
raise numbers to a complex power
sin/cos/tan of complex numbers seems to give the wrong answer
parsing of things that should break
    dup23
        """

    def quit(self):
        """
    Usage: quit

    Exits the program
        """
        sys.exit();

def ParseCommandLine():
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    descr = "Command line RPN calculator"
    parser = OptionParser(usage, description=descr)
    c,d,s,t,v = ("Check that commands have help info",
                 "Use default configuration in hc.py file only",
                 "Take input from stdin",
                 "Exit with status 1 if = or == are False",
                 "self.Display program version")
    parser.add_option("-c", "--run_checks", action="store_true", help=c)
    parser.add_option("-d", "--default_config", action="store_true", help=d)
    parser.add_option("-s", "--read_stdin", action="store_true", help=s)
    parser.add_option("-t", "--testing_mode", action="store_true", help=t)
    parser.add_option("-v", "--version", action="store_true", help=v)
    (options, args) = parser.parse_args(args=None, values=None)
    if options.run_checks:
        self.run_checks = True
    if options.default_config:
        self.use_default_config_only = True
        self.display.msg("Using default configuration only")
    if options.read_stdin:
        self.process_stdin = True
    if options.testing_mode:
        self.testing = True
    if options.version:
        self.display.msg("hcpy version 6 (17 Mar 2009)")
    return args

def main(argv):
    if len(argv) > 1:
        args = ParseCommandLine()
    finished = False
    status = None
    calculator = Calculator()
    try:
        calculator.run()
    except KeyboardInterrupt, e:
        pass
    except EOFError, e:
        pass
    print
    calculator.SaveConfiguration()
    if status == status_error:
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    main(sys.argv)
