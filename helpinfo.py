'''
$Id: helpinfo.py 1.26 2009/02/11 19:15:28 donp Exp $

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

helpinfo = {
"rat"    : '''Toggle the use of rational numbers.''',
"reset"  : '''Delete registers and stack and reset configuration to default.''',
"round"  : '''Round y to the nearest x.''',
"e"      : '''Edit the value of the x register.''',
"!"      : '''By itself:  show helper scripts that can be executed.  With script name appended:  execute script.''',
"%"      : '''Compute y mod x.  Uses abs for complex numbers.''',
"%ch"    : '''Percent change:  100*(x - y)/y''',
"&"      : '''Logical AND of x and y.''',
"*"      : '''Multiply x and y.''',
"**"     : '''Calculate y**x (y to the power x).''',
"+"      : '''Add x and y. ''',
"-"      : '''Subtract x and y. ''',
"."      : '''Print the stack.''',
"/"      : '''Divide y by x.''',
"//"     : '''Integer divide y by x.''',
"0bessel": '''Zeroth-order Besself function of x.''',
"1/x"    : '''Reciprocal of x.''',
"1bessel": '''First-order Besself function of x.''',
"2V"     : '''Convert to interval number [y, x].''',
"2deg"   : '''Convert x from radians to degrees.''',
"2hms"   : '''Convert x in decimal hours to hours.MMSS.sss.''',
"2hr"    : '''Convert x in hours.MMSSss to decimal hours.''',
"2rad"   : '''Convert x from degrees to radians.''',
"<<"     : '''Left shift of y by x bits.''',
"="      : '''Returns True if x's and y's displayed strings are equal (causes an exit(1) if not equal and -t option used).  IMPORTANT:  note equality is defined as the format strings of the two numbers being equal in the current display mode. = is a "weaker" equality than ==.''',
"=="     : '''Returns x == y (causes an exit(1) if not equal and -t option used).  The comparison is made to full precision for all number types.''',
"!="     : '''Returns x != y (causes an exit(1) if not equal and -t option used).  The comparison is made to full precision for all number types.''',
">="     : '''Returns x >= y (causes an exit(1) if not equal and -t option used).  The comparison is made to full precision for all number types.''',
"<="     : '''Returns x <= y (causes an exit(1) if not equal and -t option used).  The comparison is made to full precision for all number types.''',
"<"      : '''Returns x < y (causes an exit(1) if not equal and -t option used).  The comparison is made to full precision for all number types.''',
">"      : '''Returns x > y (causes an exit(1) if not equal and -t option used).  The comparison is made to full precision for all number types.''',
">>"     : '''Right shift of y by x bits.  When followed by a file name, turns on logging to that file.  Use '>>>' to append to an existing file.''',
">>."    : '''Turn off all logging.''',
"?"      : '''Help.  Include a command for details on that command.''',
"C"      : '''Change x to complex. ''',
"I"      : '''Change x to integer.  Information may be lost.  Complex -> mag.''',
"Q"      : '''Change x to rational; the precision of the conversion will be 10^(-digits) where digits is the number of significant digits in the current display mode.  Information may be lost.  Complex -> mag.''',
"QQ"     : '''Change x to rational but convert at full floating point precision.  Complex -> mag.''',
"R"      : '''Change x to real.  Information may be lost.  Complex -> mag.''',
"T"      : '''Change x to date/time.  Information may be lost.  Complex -> mag.''',
"V"      : '''Change x to an interval number.  Complex -> mag.''',
"^"      : '''Logical XOR of x and y.''',
"abs"    : '''Take the absolute value of x.''',
"acos"   : '''Arc cosine of x.''',
"acosh"  : '''Arc hyperbolic cosine of x.''',
"acot"   : '''Arc cotangent of x.''',
"acoth"  : '''Arc hyperbolic cotangent of x. ''',
"acsc"   : '''Arc cosecant of x. ''',
"acsch"  : '''Arc hyperbolic cosecant of x. ''',
"and"    : '''Logical AND of x and y.''',
"apart"  : '''Convert Rational to y=numer and x=denom.''',
"arg"    : '''Take the argument of the complex number and display it in the current angular mode.''',
"asec"   : '''Arc secant of x. ''',
"asech"  : '''Arc hyperbolic secant of x. ''',
"asin"   : '''Arc sine of x. ''',
"asinh"  : '''Arc hyperbolic sine of x. ''',
"atan"   : '''Arc tangent of x. ''',
"atan2"  : '''Arc tangent of y/x; returns a number -pi < x <= pi.  Gets the quadrant correct.''',
"atanh"  : '''Arc hyperbolic tangent of x. ''',
"bin"    : '''Display integers in binary.''',
"brief"  : '''Display large numbers so that they fit on one line.''',
"ceil"   : '''Calculate the ceil of x (smallest integer >= x).''',
"cfg"    : '''Show configuration information.''',
"chop"   : '''Convert real or complex number to exactly as displayed. ''',
"chs"    : '''Change the sign of x. ''',
"clrg"   : '''Clear the storage registers.''',
"clst"   : '''Clear the stack.''',
"comb"   : '''Number of combinations of y things taken n at a time. ''',
"comma"  : '''Toggles comma decoration on and off for floating point numbers.''',
"conj"   : '''Complex conjugate of x.''',
"cos"    : '''Cosine of x.''',
"cosh"   : '''Hyperbolic cosine of x.''',
"cot"    : '''Cotangent of x. ''',
"coth"   : '''Hyperbolic cotangent of x.''',
"csc"    : '''Cosecant (1/cos) of x. ''',
"csch"   : '''Hyperbolic cosecant (1/cosh) of x. ''',
"debug"  : '''Toggle debug printing of file:line numbers in caught exceptions.''',
"dec"    : '''Display integers in decimal.''',
"deg"    : '''Set the angle calculation mode to degrees.''',
"del"    : '''Delete x and drop the stack.''',
"denom"  : '''Take the denominator of x.''',
"digits" : '''Set the number of digits to display.''',
"down"   : '''Toggle downcasting on and off.  If it is on, a result will be downcast to a simpler type.  For example, if int(x) == x, then it is converted to an integer.  Be aware that this can cause surprises.  For example, if prec is set to 15 and you execute 'pi 1e100 *', you'll see an integer result because int(1e100*pi) == 1e100*pi.''',
"ec"     : '''Edit the current configuration.  Warning:  do not edit the mp.dps term.  If you wish to change the precision, edit the prec dictionary entry.''',
"eng"    : '''Engineering display mode.''',
"engsi"  : '''Engineering display mode with SI prefixes. ''',
"enter"  : '''Push a copy of x onto the stack.''',
"eps"    : '''Put the smallest sensible real number in x.''',
"er"     : '''Edit the current storage registers.''',
"es"     : '''Edit the current stack.''',
"exp"    : '''Exponential of x.''',
"fact"   : '''Factorial function.''',
"fix"    : '''Fixed display mode (fixed number of decimal places).''',
"floor"  : '''Calculate the floor of x (largest integer <= x).''',
"fp"     : '''Take the fractional part of x.''',
"gamma"  : '''Gamma function of x.''',
"hex"    : '''Display integers in hexadecimal.''',
"hypot"  : '''Calculate sqrt(x**2 + y**2).''',
"im"     : '''Take the imaginary part of x.''',
"in"     : '''Returns 'x in y'; y must be an interval number.  If the -t option was used and x is not in y, the program exits with a status of 1.''',
"int"    : '''Set integer arithmetic to signed 2's complement.  May be followed by a number that indicates the size of the integers in bits.  If no number is present, the normal arbitrary-sized integers are used.  This n-bit integer arithmetic is closed, meaning n-bit integer operations will always result in another n-bit integer; this, of course, is for arithmetic and bit-twiddling operations.  Transcendental functions of these integers will return reals or complex numbers.  Note there are subtleties with these n-bit signed integers; see the comments on the Zn.__neg__ method in integer.py.  Example:  set 4-bit signed integers and take enter -8; then execute chs.  If it's not what you expect, definitely read the indicated comments.''',
"inv"    : '''Reciprocal of x.''',
"invn"   : '''Calculate the inverse normal CDF.  Argument must be > 0 and < 1.  Will fail for extreme arguments (e.g., 1e-100) because the root-finding method fails.''',
"ip"     : '''Take the integer part of x.''',
"iva"    : '''Interval number display form of a +- b.  See also ivb and ivc.''',
"ivb"    : '''Interval number display form of a (b%).  See also iva and ivc.''',
"ivc"    : '''Interval number display form of <a, b>.  See also iva and ivb. ''',
"lastx"  : '''Restore the last x value.''',
"ln"     : '''Natural logarithm of x.''',
"ln2"    : '''Base 2 logarithm of x. ''',
"log"    : '''Base 10 logarithm of x.''',
"log10"  : '''Base 10 logarithm of x.''',
"log2"   : '''Base 2 logarithm of x''',
"lshift" : '''Left shift of y by x bits.''',
"mid"    : '''Replace x (an mpi number) with the interval's midpoint.''',
"mixed"  : '''Toggle between mixed and improper fractions.''',
"mod"    : '''Calculations are done with modulus x.  Any real modulus can be used.  Set the modulus to 1 to disable.''',
"nbessel": '''nth-order Besself function of x (put n in y).''',
"ncdf"   : '''Calculate the normal cdf of x.''',
"none"   : '''Display with standard mpmath format.''',
"numer"  : '''Take the numerator of x.''',
"oct"    : '''Display integers in octal.''',
"off"    : '''Turn output display off.''',
"on"     : '''Turn output display on.''',
"or"     : '''Logical OR of x and y.''',
"perm"   : '''Number of permutations of y things taken x at a time.''',
"phi"    : '''Returns the golden ratio, (1 + sqrt(5))/2.''',
"pi"     : '''Put pi into x.''',
"polar"  : '''Display complex numbers in polar form.''',
"polar"  : '''Display complex numbers in polar form.''',
"pow"    : '''Calculate y**x (y to the power x).''',
"prec"   : '''Set the number of digits to calculate with.''',
"prr"    : '''Print the registers.''',
"prst"   : '''Print the stack.''',
"quit"   : '''Exit the program.''',
"rad"    : '''Set the angle calculation mode to radians.''',
"rand"   : '''Returns a uniformly-distributed random number in [0, 1).''',
"re"     : '''Take the real part of x.''',
"rect"   : '''Display complex numbers in rectangular form.''',
"rect"   : '''Display complex numbers in rectangular form.''',
"roll"   : '''Roll the stack down.''',
"rshift" : '''Right shift of y by x bits.''',
"sci"    : '''Scientific display mode.''',
"sec"    : '''Secant of x.''',
"sech"   : '''Hyperbolic secant of x. ''',
"show"   : '''Show the full precision of x.''',
"sig"    : '''Significant figures display mode.''',
"sin"    : '''Sine of x.''',
"sinh"   : '''Hyperbolic sine of x. ''',
"sqrt"   : '''Square root of x.''',
"square" : '''Square x.''',
"stack"  : '''Set the number of stack levels visible.''',
"tan"    : '''Tangent of x.''',
"tanh"   : '''Hyperbolic tangent of x. ''',
"uint"   : '''Set integer arithmetic to unsigned arithmetic with integers of n bits.  n must be given following 'uint' with no intervening space.  See help on int command for more details.''',
"width"  : '''Set the line width to x.''',
"xch"    : '''Interchange x and y.''',
"xor"    : '''Logical XOR of x and y.''',
"zeta"   : '''Zeta function of x.''',
"|"      : '''Logical OR of x and y.''',
"~"      : '''Logical negation of x.''',
}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print '''Usage:  %s name1 ...
Find commands that don't have a help entry yet.
''' % sys.argv[0]
        exit(0)
    for name in sys.argv[1:]:
        if name not in helpinfo:
            print name

