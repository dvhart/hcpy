'''
$Id: number.py 1.24 2009/02/10 23:19:16 donp Exp $

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

import re
from mpmath import mpf, mpc, mpi, inf
from rational import Rational
from integer import Zn, isint, ipaddr
from julian import Julian
from string import strip
from si import suffixes_ln
import socket

try: from pdb import xx
except: pass

# Number recognition regular expressions
integer = re.compile("^[+-]?\d+$")

cre=r'''
    %s                          # Match at beginning
    ([+-])%s                    # Optional leading sign
    %s                          # Placeholder for imaginary unit
    (\d+\.\d+|\d+\.?|\.\d+)     # Required digits and opt. decimal point
    (e[+-]?\d+)?                # Optional exponent
    %s                          # Match at end
'''
# Pure imaginary, xi or ix
I1 = cre % ("^", "?", "", "i$")
I2 = cre % ("^", "?", "i", "$")

# Reals
R = cre % ("^", "?", "", "$")

# True complex numbers:  x+iy or x+yi
C1 = (cre % ("^", "?", "", "")) + (cre % ("", "", "", "[ij]$"))
C2 = (cre % ("^", "?", "", "")) + (cre % ("", "", "[ij]", "$"))

# Degenerate complex numbers:  1-i, 3.7+i
num = r"([+-]?)(\d+\.\d+|\d+\.?|\.\d+)(e[+-]?\d+)?"
C3 = r"^%s([+-][ij])$" % num

# True complex numbers:  (x,y)
C4 = r"^\(%s(,)%s\)$" % (num, num)
del num

# Regular expressions
imag1 =    re.compile(I1, re.X | re.I)
imag2 =    re.compile(I2, re.X | re.I)
real =     re.compile(R,  re.X | re.I)
complex1 = re.compile(C1, re.X | re.I)
complex2 = re.compile(C2, re.X | re.I)
complex3 = re.compile(C3, re.X | re.I)
complex4 = re.compile(C4, re.X | re.I)

# Rationals:  "a/b", and "axb/c" forms are allowed where a and b are
# integers and x is one or more of the following characters: '+- '.
# b and c are always positive; a may be positive or negative.
Ra = r'''
    ^   # Mixed fraction
    ([-+])?             # Optional sign
    (\d+)               # Integer
    [-+ ]+              # Separation character
    (\d+)               # Numerator
    /                   # Fraction separator
    (\d+)               # Denominator
    $
    |                   # Or
    ^   # Canonical fraction
    ([-+]?\d+)          # Integer a with optional sign
    /                   # Fraction separator
    (\d+)               # Denominator
    $
'''
rational = re.compile(Ra, re.X | re.I)

ip = re.compile(r"^(\d{1,3})[.](\d{1,3})[.](\d{1,3})[.](\d{1,3})")
ip6 = re.compile(r"""^(([0-9a-f]{1,4}:){1,1}(:[0-9a-f]{1,4}){1,6})$|
^(([0-9a-f]{1,4}:){1,2}(:[0-9a-f]{1,4}){1,5})$|
^(([0-9a-f]{1,4}:){1,3}(:[0-9a-f]{1,4}){1,4})$|
^(([0-9a-f]{1,4}:){1,4}(:[0-9a-f]{1,4}){1,3})$|
^(([0-9a-f]{1,4}:){1,5}(:[0-9a-f]{1,4}){1,2})$|
^(([0-9a-f]{1,4}:){1,6}(:[0-9a-f]{1,4}){1,1})$""")
ip6 = re.compile(r"""
    ^((([0-9a-f]{1,4}:){1,6})(:[0-9a-f]{1,4}){1,1})$|
    ^((([0-9a-f]{1,4}:){1,5})(:[0-9a-f]{1,4}){1,2})$|
    ^((([0-9a-f]{1,4}:){1,4})(:[0-9a-f]{1,4}){1,3})$|
    ^((([0-9a-f]{1,4}:){1,3})(:[0-9a-f]{1,4}){1,4})$|
    ^((([0-9a-f]{1,4}:){1,2})(:[0-9a-f]{1,4}){1,5})$|
    ^((([0-9a-f]{1,4}:){1,1})(:[0-9a-f]{1,4}){1,6})$|
    ^((([0-9a-f]{1,4}:){7,7})([0-9a-f]{1,4}))$|
    ^((([0-9a-f]{1,4}:){1,7}|:):)$|
    ^(:(:[0-9a-f]{1,4}){1,7})$|
    ^(((([0-9a-f]{1,4}:){6})(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}))$|
    ^((([0-9a-f]{1,4}:){5}[0-9a-f]{1,4}:(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}))$|
    ^(([0-9a-f]{1,4}:){5}:[0-9a-f]{1,4}:(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})$|
    ^(([0-9a-f]{1,4}:){1,1}(:[0-9a-f]{1,4}){1,4}:(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})$|
    ^(([0-9a-f]{1,4}:){1,2}(:[0-9a-f]{1,4}){1,3}:(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})$|
    ^(([0-9a-f]{1,4}:){1,3}(:[0-9a-f]{1,4}){1,2}:(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})$|
    ^(([0-9a-f]{1,4}:){1,4}(:[0-9a-f]{1,4}){1,1}:(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})$|
    ^((([0-9a-f]{1,4}:){1,5}|:):(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})$|
    ^(:(:[0-9a-f]{1,4}){1,5}:(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3})$
""", re.X | re.I)

vector = re.compile(r"\[\s*([.0])")

class Number(object):
    '''Used to generate a number object from a string.
    '''

    # If the following class variable is nonzero, then integers are
    # being restricted to a said number of bits.
    bits = 0

    # If signed is True, then integer arithmetic is signed; otherwise,
    # arithmetic is unsigned.
    signed = True

    def __init__(self):
        pass

    def __call__(self, s):
        assert len(s) > 0
        suffix = 1
        if s != "now" and s != "today":
            if len(s) > 1 and s[:2] != "0x":
                if s[-1] in suffixes_ln:
                    exponent = suffixes_ln[s[-1]]
                    if exponent >= 0:
                        suffix = Zn(10**exponent)
                    else:
                        suffix = mpf("1e" + str(exponent))
                    s = s[:-1]
        for func in (self.ip, self.j, self.i, self.q, self.v, self.r, self.c):
            x = func(s)
            if x != None:
                if suffix == 1:
                    return x
                if isint(x):
                    if isint(suffix): return Zn(suffix*x)
                    else:             return suffix*mpf(int(x))
                elif isinstance(x, Rational):
                    if isint(suffix): return Rational(suffix*x.n, x.d)
                    else:             return suffix*x.mpf()
                elif isinstance(x, mpf) or \
                     isinstance(x, mpc) or \
                     isinstance(x, mpi):
                    if isint(suffix): return mpf(int(suffix))*x
                    else:             return suffix*x
                else:
                    return None
        return None

    def j(self, s):
        '''Check to see if it's a Julian date/time form.  We only allow
        two forms:  'dS[y[:...]]' where S is a string for the month or
        '.+:.+' (regexp syntax) where it contains a colon and means a
        time today.  'now' and 'today' are also allowed.
        '''
        if s == "now" or s == "today" or ":" in s:
            return Julian(s)
        sl = s.lower()
        for month in Julian.month_names:
            if month.lower() in sl:
                return Julian(s)
        return None

    def i(self, s):
        # Handle special cases like 0x, 0o, and 0b
        try:
            value = 0
            match = False
            if len(s) > 2:
                if s[:2] == "0x":
                    value = int(s[2:], 16)
                    match = True
                elif s[:2] == "0o":
                    value = int(s[2:], 8)
                    match = True
                elif s[:2] == "0b":
                    value = int(s[2:], 2)
                    match = True
            if integer.match(s):
                return Zn(int(s))
            if match:
                return Zn(value)
        except ValueError:
            pass
        except Exception:
            raise
        return None

    def A(self, s):
        # is this is an array

        return None

    def V(self, s):
        # is this is a vector
        return None

    def ip(self, s):
        def unpack(s):
            v = '0x'
            for i in range(len(s)):
                v += '%02x' % ord(s[i])
            return int(v,16)
        cidr = None
        if '/' in s:
            sparts = s.split('/')
            s = sparts[0]
            cidr = sparts[1]
        try:
            mo = ip.match(s)
            if cidr is None:
                cidr = 32
            if mo:
                dquad = [ int(i) for i in mo.groups() if i ]
                if max(dquad) > 255:
                    return None
                ps = socket.inet_pton(socket.AF_INET, s)
                return ipaddr(unpack(ps), cidr)
            else:
                if cidr is None:
                    cidr = 128
                if ip6.match(s):
                    ps = socket.inet_pton(socket.AF_INET6, s)
                    return ipaddr(unpack(ps), cidr)
        except Exception, e:
            print e
            pass
        return None

    def q(self, s):
        mo = rational.match(s)
        if mo:
            g = [i for i in mo.groups() if i]
            sign = ""
            if g[0] == "+":
                del g[0]
            elif g[0] == "-":
                sign = "-"
                del g[0]
            try:
                num = [int(i) for i in g]
            except:
                raise Exception("Bug:  rational match on non-integer")
            if not num:
                return None
            elif len(num) == 2:
                w, n, d = 0, num[0], num[1]
            elif len(num) == 3:
                w, n, d = num
            else:
                msg = "Program bug\nUnexpected number of matches on\n"
                msg += "'%s'" % s
                raise Exception(msg)
            n = int(sign + str(w*d + n))
            return Rational(n, d)
        else:
            return None

    def r(self, s):
        # Handle infinities
        if s == "inf": return inf
        if s == "-inf": return -inf
        # If the number begins with "E" or 'e', prepend a 1
        if s[0] == "E" or s[0] == "e":
            s = "1" + s
        mo = real.match(s)
        if mo:
            num = [i for i in mo.groups() if i]
            if not num:
                return None
            else:
                try:
                    return mpf(''.join(num))
                except:
                    return None
        else:
            return None

    def c(self, s):
        s = s.lower()
        s = s.replace("j", "i")
        if "i" not in s and "(" not in s:
            return None
        if s == "i" or s == "+i":
            return mpc(0, 1)
        if s == "-i":
            return mpc(0, -1)
        mo = complex3.match(s)
        if mo:
            n = ''.join([i for i in mo.groups() if i])
            try:
                ending = n[-2:]
                if ending == "+i":
                    return mpc(mpf(n[:-2]), 1)
                elif ending == "-i":
                    return mpc(mpf(n[:-2]), -1)
                else:
                    raise Exception("Program bug:  unexpected complex number")
            except:
                pass
        for expression in (imag1, imag2):
            mo = expression.match(s)
            if mo:
                num = [i for i in mo.groups() if i]
                if num:
                    try:
                        return mpc(0, mpf(''.join(num)))
                    except:
                        return None
                else:
                    return None
        for expression in (complex1, complex2):
            mo = expression.match(s)
            if mo:
                try:
                    g = mo.groups()
                    r = mpf(''.join([i for i in g[:3] if i]))
                    i = mpf(''.join([i for i in g[3:] if i]))
                    return mpc(r, i)
                except:
                    return None
        mo = complex4.match(s)
        if mo:
            try:
                s = "".join([i for i in mo.groups() if i])
                r, i = [mpf(i) for i in s.split(",")]
                return mpc(r, i)
            except:
                return None

    def v(self, s):
        '''Interval numbers:  allowed forms are
            1. 'a +- b'
            2. 'a (b%)'  % sign is optional
            3. '[a, b]'
        In 1, a is the midpoint of the interval and b is the half-width.
        In 2, a is the midpoint of the interval and b is the half-width.
        In 3, the interval is indicated directly.
        '''
        e = ValueError("Improperly formed interval number '%s'" %s)
        s = s.replace(" ", "")
        if "+-" in s:
            n = [mpf(strip(i)) for i in s.split("+-")]
            return mpi(n[0] - n[1], n[0] + n[1])
        elif "(" in s:
            if s[0] == "(":  # Don't confuse with a complex number (x,y)
                return None
            if ")" not in s:
                raise e
            s = s.replace(")", "")
            percent = False
            if "%" in s:
                if s[-1] != "%":
                    raise e
                percent = True
                s = s.replace("%", "")
            a, p = [mpf(strip(i)) for i in s.split("(")]
            d = p
            if percent:
                d = a*p/mpf(100)
            return mpi(a - d, a + d)
        elif "," in s:
            if "[" not in s: raise e
            if "]" not in s: raise e
            s = s.replace("[", "")
            s = s.replace("]", "")
            n = [mpf(strip(i)) for i in s.split(",")]
            return mpi(n[0], n[1])
        else:
            return None

if __name__ == "__main__":
    # Test cases
    nums = {
        # Integers
        Zn(0) : (
            "0", "+0", "-0", "000", "+000", "-000",
            ),
        Zn(1) : (
            "1", "+1", "01", "+01", "001", "+001",
            ),
        Zn(-1) : (
            "-1", "-01", "-001",
            ),
        Zn(124) : (
            "124", "+124", "0124", "+0124", "000124", "+000124",
            ),
        Zn(-123) : (
            "-123", "-000123",
            ),

        # Reals
        mpf(0) : (
            "0.0", "+0.0", "-0.0",
            "000.000", "+000.000", "-000.000",
            ),
        mpf(1) : (
            "1.", "+1.", "1.0", "+1.0",
            "1.0e0", "+1.0e0",
            "1.0E0", "+1.0E0",
            ),
        mpf(-2) : (
            "-2.", "-2.0", "-2.0e0", "-2.0000E000",
            ),
        mpf("-2.3") : (
            "-2.3", "-2.30", "-2.3000", "-2.3e0", "-2300e-3", "-0.0023e3",
            "-.23E1",
            ),
        mpf("2.345e-7") : (
            "2.345e-7", "2345e-10", "0.00000002345E+1", "0.0000002345",
            ),

        # Pure imaginaries
        mpc(0, 1) : (
            "i", "+i", "1i", "+1i", "+i1",
            "1.i", "+1.i", "+i1.",
            "1.0i", "+1.0i", "+i1.0",
            "1.00i", "+1.00i", "+i1.00",
            ),
        mpc(0, -1) : (
            "-i", "-i", "-1i", "-i1",
            "-1.i", "-1.i", "-i1.",
            "-1.0i", "-1.0i", "-i1.0",
            "-1.00i", "-1.00i", "-i1.00",
            ),
        mpc(0, 3) : (
            "3i", "+3i", "3.i", "+3.i", "3.0i", "+3.0i", "3.0e0i", "+3.0e0i",
            "I3", "+I3", "I3.", "+I3.", "I3.0", "+I3.0", "I3.0e0", "+I3.0e0",
            "3.000i", "i3.000", "3.000E0i", "i3.000E0",
            "3.000e-0J", "J3.000e-0", "3.000e+0J", "J3.000e+0",
            ),
        mpc(0, -8) : (
            "-8i", "-8.i", "-8.0i", "-8.0e0i",
            "-j8", "-j8.", "-j8.0", "-j8.0E0",
            ),
        mpc(0, mpf("-0.123")) : (
            "-.123i", "-.123j", "-0.123i", "-1.23e-1i",
            ),

        # Complex numbers
        mpc(1, -1) : (
            "1-1i", "1-1.i", "1.-1i", "1.-1.i",
            "1-j1", "1-j1.", "1.-j1", "1.-j1.",
            "1.00-1.00I", "1.00-I1.00", "1000e-3-100000e-5I",
            "1.00-J1.00", "1000E-3-J100000E-5",
            ),
        mpc(1, 1) : (
            "1+1i", "1+1.i", "1.+1i", "1.+1.i",
            "1+i", "1.0+i", "1.000+i",
            ),
        mpc("4.9", -1) : (
            "4.9-1i", "4.9-1.i", "49e-1-1i",
            "4.9-i", "49e-1-i",
            ),
        mpc("-7", -1) : (
            "-7-1i", "-7-1.i", "-70e-1-1i",
            "-7-i", "-70e-1-i",
            ),
        mpc(mpf("11.549e-59"), mpf("-8.31e89")) : (
            "11.549e-59-8.31e89I", "1.1549e-58-J831e87",
            ),
        mpc(1, 2): (
            "(1,2)", "(1.,2.)", "(1.0,2.0)", "(1.000,2.000)",
        ),

        # Rational numbers
        Rational(3, 8) : (
            "3/8", "6/16", "0 12/32", "0-15/40", "0+18/48",
            ),
        Rational(-3, 7) : (
            "-3/7", "-6/14", "-0 12/28", "-0-15/35", "-0+18/42",
            ),
        Rational(3, -7) : (
            "-3/7", "-6/14", "-0 12/28", "-0-15/35", "-0+18/42",
            ),
    }
    # Because of a bug in mpi == and != tests, we have to test them
    # differently.
    mpi_tests = {
        # Interval numbers
        mpi(1, 3) : (
            "[1, 3]", "[1.0, 3]", "[1, 3.0]", "[1.0, 3.0]",
            "[1,3]", "[1.0,3]", "[1,3.0]", "[1.0,3.0]",
            "[   1,     3]", "[   1.0,3]", "[     1,     3.0]",
            "1.5 +- 0.5", "1.5+-0.5", "1.5+-      0.5", "1.5     +-0.5",
            "1.5      +-      0.5", "15e-1 +- 500e-3",
            "1.5(33.33333333333333333333%)", "1.5  (33.33333333333333333333%)",
            "1.5    (     33.33333333333333333333%)",
            "1.5    (     33.33333333333333333333     % )",
            "1.5(     33.33333333333333333333    %  )",
            "1.5(33.33333333333333333333    %  )",
            ),
    }

    n = Number()
    status = 0
    for number in nums:
        for numstr in nums[number]:
            num = n(numstr)
            if num != number:
                print("Error for '%s'" % numstr)
                print("  Should be %s" % str(number))
                print("  Got       %s" % str(num))
                status += 1
    for number in mpi_tests:
        for numstr in mpi_tests[number]:
            num = n(numstr)
            if (num.a != number.a) and (num.b != number.b):
                print("Error for '%s'" % numstr)
                print("  Should be %s" % str(number))
                print("  Got       %s" % str(num))
                status += 1
    exit(status)
