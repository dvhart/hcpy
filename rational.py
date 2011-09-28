'''
$Id: rational.py 1.24 2009/02/10 18:45:57 donp Exp $

Provide rational numbers that interoperate with mpmath objects.

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

from mpmath import mpf, mpc, mpi, eps, mp, pi
from integer import Zn, isint

try: from pdb import xx  # pdb.set_trace is xx; easy to find for debugging
except: pass

def gcd(a, b):
    '''Determine the greatest common divisor of integers u and v.
    Euclid's algorithm from Knuth, vol 2, pg 320.
    '''
    if not isint(a) or not isint(b):
        raise ValueError("Arguments must be integers")
    a, b = int(a), int(b)
    if a == 0:  return b
    if b == 0:  return a
    while b != 0:
        a, b = b, a % b
    return a

class Rational(object):
    mixed = False  # If set to true, str() returns mixed form
    def __init__(self, a=0, b=1):
        if b == 1:
            if isinstance(a, mpf):
                r = self.frac(a)
                self.n, self.d = r.n, r.d
                return
            else:
                try:
                    # C++ copy constructor behavior
                    self.n = a.numer()
                    self.d = a.denom()
                    return
                except:
                    pass
        if b == 0:
            raise ZeroDivisionError("Denominator is zero")
        else:
            g = gcd(a, b)
            self.n = int(a)//g
            self.d = int(b)//g

    def __abs__(self):
        return Rational(abs(self.n), abs(self.d))

    def __pos__(self):
        return Rational(self)

    def __neg__(self):
        return Rational(-self.n, self.d)

    def __radd__(self, other):
        return self.__add__(other)

    def __add__(self, other):
        if isinstance(other, Rational):
            y = Rational(self.n*other.d + other.n*self.d, self.d*other.d)
            if y.d == 1:
                return y.n
            else:
                return y
        elif isinstance(other, float):
            raise ValueError("float addition not supported")
        else:
            assert isinstance(other, int) or isinstance(other, mpf) or \
                   isinstance(other, mpc) or isinstance(other, mpi)
            n = other*self.d + self.n
            if isinstance(n, int):
                y = Rational(n, self.d)
                if y.d == 1:
                    return y.n
                else:
                    return y
            else:
                return n/self.d

    def __rsub__(self, other):
        return -self.__sub__(other)

    def __sub__(self, other):
        if isinstance(other, Rational):
            return Rational(self.n*other.d - other.n*self.d, self.d*other.d)
        elif isinstance(other, float):
            raise ValueError("float subtraction not supported")
        else:
            assert isinstance(other, int) or isinstance(other, mpf) or \
                   isinstance(other, mpc) or isinstance(other, mpi)
            n = self.n - other*self.d
            if isinstance(n, int):
                y = Rational(n, self.d)
                if y.d == 1:
                    return y.n
                else:
                    return y
            else:
                return n/self.d

    def __rmul__(self, other):
        return self.__mul__(other)

    def __mul__(self, other):
        if isinstance(other, Rational):
            return Rational(self.n*other.n, self.d*other.d)
        elif isinstance(other, float):
            raise ValueError("float multiplication not supported")
        else:
            assert isinstance(other, int) or isinstance(other, mpf) or \
                   isinstance(other, mpc) or isinstance(other, mpi)
            n = other*self.n
            if isinstance(n, int):
                y = Rational(n, self.d)
                if y.d == 1:
                    return y.n
                else:
                    return y
            else:
                return n/self.d

    def __rdiv__(self, other):
        one = Rational(1)
        return one/(self*(one/other))

    def __div__(self, other):
        if other == 0:
            raise ZeroDivisionError("Divisor is zero")
        if isinstance(other, Rational):
            return Rational(self.n*other.d, self.d*other.n)
        elif isinstance(other, int):
            return Rational(self.n, self.d*other)
        elif isinstance(other, float):
            raise ValueError("float division not supported")
        else:
            assert isinstance(other, mpf) or \
                   isinstance(other, mpc) or \
                   isinstance(other, mpi)
            return (self.n/other)/self.d

    def _mixed(self):
        sign = ""
        if (self.n < 0 and self.d > 0) or (self.n > 0 and self.d < 0):
            sign = "-"
        whole, remainder = divmod(abs(self.n), abs(self.d))
        if  whole == 0:
            if remainder == 0: 
                return "0"
            else:
                return(sign + "%s/%s" % (remainder, self.d))
        else:
            if remainder == 0:
                return sign + str(whole)
            else:
                return(sign + "%s %s/%s" % (whole, remainder, self.d))

    def __str__(self):
        if Rational.mixed:
            return self._mixed()
        else:
            return "%d/%d" % (self.n, self.d)

    def __repr__(self):
        return "Rational(%d, %d)" % (self.n, self.d)

    def __float__(self):
        return float(self.n)/self.d

    def __getattr__(self, key):
        '''This function is necessary when a Rational gets compared to an
        mpf.  The mpf comparison routine looks for the _mpf_ attribute; if
        it finds it, then it knows it has an mpf.  We fake it out by doing
        an mpf conversion at the point the information is needed.  Thus,
        the comparison will be done with the proper number of digits; this
        wouldn't necessarily be true if we cached the _mpf_ data earlier.
        '''
        if key == "_mpf_":
            return (mpf(self.n)/mpf(self.d))._mpf_
        else:
            raise AttributeError("'%s' not an attribute" % key)

    def __cmp__(self, other):
        if other == None:
            return -1
        if isinstance(other, Rational):
            if (self.n == other.n) and (self.d == other.d):
                return 0
            else:
                if self.mpf() < other.mpf(): return -1
                else: return 1
        elif isinstance(other, mpf):
            a, b = self.mpf(), other.mpf()
            if a < b: return -1
            elif a > b: return 1
            else: return 0
        elif isinstance(other, int):
            a, b = self.mpf(), mpf(other)
            if a < b: return -1
            elif a > b: return 1
            else: return 0
        else:
            raise ValueError("Second argument is unsupported type")

    def mpf(self):
        return mpf(self.n)/mpf(self.d)

    def mpc(self):
        return mpc(mpf(self.n)/mpf(self.d), 0)

    def mpi(self):
        n = mpf(self.n)/mpf(self.d)
        return mpi(n, n)

    def denom(self):
        return self.d

    def numer(self):
        return self.n

    def frac(self, x, digits=0, max_iterations=0):
        '''Converts an mpf to a Rational approximation and returns a
        Rational object.  The iteration goal is to return a rational
        approximation whose difference from x is less than 1/10**mp.dps;
        i.e., the approximation as good as the current number of digits
        used in the mpmath library.
        
        x will be converted to an mpf type.  This routine is converted from
        a C routine I downloaded from NETLIB on Tue Nov 11 18:08:26 1997
        from NIST Guide to Available Math Software, source for module FRAC
        from package C.

        digits sets the precision of the conversion at 10**(-digits).  If
        it is 0, then mp.dps is used.
 
        Set max_iterations to a postive nonzero value to limit the number
        of iterations.
 
        See http://gams.nist.gov/,
        http://gams.nist.gov/serve.cgi/Package/C/,
        http://www.netlib.org/c/frac (location of actual source)
        '''
        if isinstance(x, mpc) or isinstance(x, complex):
            x = abs(x)
        elif isinstance(x, mpi):
            x = x.mid
        elif isinstance(x, int) or isinstance(x, long):
            x = mpf(x)
        elif isinstance(x, Zn):
            x = mpf(int(x))
        else:
            if not isinstance(x, mpf):
                # Note we explicitly do not handle floats
                raise SyntaxError("Unsupported type")
        # Handle a special case that results in no convergence.
        if x == mpf("1")/mpf("2"):
            return Rational(1, 2)
        digits_increase = 2
        if digits == 0:
            digits = mp.dps
        error = mpf(10)**(-digits)
        # We'll increase the precision to ensure the error is greater
        # than the minimal fractional digits.
        mp.dps += digits_increase
        sign = 1
        if x < 0:
            sign = -1
            x = abs(x)
        if x == 0:
            mp.dps -= digits_increase
            return Rational(0, 1)
        d, D, n, r, epsilon, iterations = 1, 1, int(x), mpf(1), mpf(0), 0
        N = n + 1
        one = True
        while True:
            iterations += 1
            if max_iterations and iterations > max_iterations:
                raise Exception("Too many iterations")
            if not one:
                if r > 1.0:
                    N += n*int(r)
                    D += d*int(r)
                    n += N
                    d += D
                else:
                    r = 1.0/r
            else:
                one = False
            r = 0.0
            if x*d != n:
                r = (N - x*D)/(x*d - n)
                if r <= 1.0:
                    t = N
                    N = n
                    n = t
                    t = D
                    D = d
                    d = t
            epsilon = abs(1.0 - n/(x*d))
            if epsilon <= error:
                mp.dps -= digits_increase
                return Rational(sign*n, d)
            if r != 0.0:
                continue
            m = 10.0
            while m*epsilon < 1.0:
                m *= 10.0
            epsilon = (1.0/m)*(int(0.5 + m*epsilon))
            if r == 0.0:
                mp.dps -= digits_increase
                raise Exception("Error in frac() routine")

if __name__ == "__main__":
    # Test code

    def gcd_tests():
        assert(gcd(8, 12) == 4)
        assert(gcd(8L, 12) == 4)
        assert(gcd(8, 12L) == 4)
        assert(gcd(8L, 12L) == 4)

    def generalTests():
        three = Rational(3)
        assert(str(three) == "3/1") 
        third = Rational(1,3)
        assert(str(third) == "1/3") 
        fifth = Rational(1,5)
        assert(str(fifth) == "1/5") 
        assert(str(third + fifth) == "8/15") 
        assert(str(third*fifth) == "1/15") 
        assert(str(third-fifth) == "2/15") 
        assert(str(fifth/third) == "3/5") 
        assert(float(fifth) == 0.2) 
        assert(float(third) == 1/3.) 
        assert(third.numer() == 1)
        assert(third.denom() == 3)
        new_third = Rational(third)  # Show we support init from ourselves
        assert(str(new_third) == "1/3") 

    def mixedTests():
        badPi = Rational(22,7)
        Rational.mixed = True
        assert(str(badPi) == "3 1/7") 
        proper_fraction = Rational(3,5)
        assert(str(proper_fraction) == "3/5") 
        whole_num  =  Rational(8,2)
        assert(str(whole_num) == "4") 
        zero  =  Rational(0,1)
        assert(str(zero) == "0") 

    def errorTests():
        try:
            r = Rational(5, 0)
            raise Exception("Fail: didn't detect zero denominator.")
        except ZeroDivisionError, detail:
            pass

    def no_diff(a, b):
        return abs(a) - abs(b) <= eps

    def mpfTests(): # Test with mpf's
        onep2 = mpf("1.2")
        third = Rational(1,3)
        # add
        assert no_diff(onep2 + third, onep2 + 1/mpf(3))
        # radd
        assert no_diff(third + onep2, onep2 + 1/mpf(3))
        # sub
        assert no_diff(onep2 - third, onep2 - 1/mpf(3))
        # rsub
        assert no_diff(third - onep2, -onep2 + 1/mpf(3)) 
        # mul
        assert no_diff(onep2 * third, onep2 * 1/mpf(3))
        # rmul
        assert no_diff(third * onep2, onep2 * 1/mpf(3))
        # div
        assert no_diff(onep2 / third, onep2 /(1/mpf(3)))
        # rdiv
        assert no_diff(third / onep2, (1/mpf(3)) / onep2)

    def mpcTests(): # Test with mpc's
        onep2 = mpc("1.2", "88")
        third = Rational(1,3)
        # add
        assert no_diff(onep2 + third, onep2 + 1/mpc(3))
        # radd
        assert no_diff(third + onep2, onep2 + 1/mpc(3))
        # sub
        assert no_diff(onep2 - third, onep2 - 1/mpc(3))
        # rsub
        assert no_diff(third - onep2, -onep2 + 1/mpc(3))
        # mul
        assert no_diff(onep2 * third, onep2 * 1/mpc(3))
        # rmul
        assert no_diff(third * onep2, onep2 * 1/mpc(3))
        # div
        assert no_diff(onep2 / third, onep2 /(1/mpc(3)))
        # rdiv
        assert no_diff(third / onep2, (1/mpc(3)) / onep2)

    def no_idiff(a, b):
        if not no_diff(a.mid, b.mid):
            return False
        if not no_diff(a.delta, b.delta):
            return False
        return True

    def mpiTests(): # Test with mpi's
        onep2 = mpi("1", "2")
        third = Rational(1,3)
        # add
        assert no_idiff(onep2 + third, onep2 + 1/mpi(3))
        # radd
        assert no_idiff(third + onep2, onep2 + 1/mpi(3))
        # sub
        assert no_idiff(onep2 - third, onep2 - 1/mpi(3))
        # rsub
        assert no_idiff(third - onep2, -onep2 + 1/mpi(3))
        # mul
        assert no_idiff(onep2 * third, onep2 * 1/mpi(3))
        # rmul
        assert no_idiff(third * onep2, onep2 * 1/mpi(3))
        # div
        assert no_idiff(onep2 / third, onep2 /(1/mpi(3)))
        # rdiv
        assert no_idiff(third / onep2, (1/mpi(3)) / onep2)

    def integerTests():
        one = 1
        third = Rational(1,3)
        # add
        assert (one + third) == (Rational(4,3))
        # radd
        assert (third + one) == (Rational(4,3))
        # sub
        assert (one - third) == (Rational(2,3))
        # rsub
        assert (third - one) == (Rational(-2,3))
        # mul
        assert (one * third) == (Rational(1,3))
        # rmul
        assert (third * one) == (Rational(1,3))
        # div
        assert (one / third) == (Rational(3,1))
        # rdiv
        assert (third / one) == (Rational(1,3))

    def comparisonTest():
        one = 1
        oned = mpf(1)
        third = Rational(1,3)
        # < and <=
        assert third < one
        assert third < oned
        assert third <= one
        assert third <= oned
        assert third <= third
        assert third <= third
        # > and >=
        assert one   >  third
        assert oned  >  third
        assert one   >= third
        assert oned  >= third
        assert third >= third
        assert third >= third
        # == and !=
        assert third != one
        assert one   != third
        assert third != oned
        assert oned  != third
        assert third == Rational(1, 3)
        assert not (third != Rational(1, 3))

    def fracTest():
        '''I experimentally determined that factor = 3.1 for the loop
        shown up to 1000 digits (but it only goes to 100 for speed).
        '''
        factor = mpf(3.1)
        for digits in xrange(5, 100, 5):
            mp.dps = digits
            r = Rational()
            approx = r.frac(pi)
            num = mpf(approx.n)/approx.d
            #assert abs(pi - num) < factor*mpf(10)**(-digits)
            if abs(pi - num) > factor*mpf(10)**(-digits):
                print "digits", digits, 
                a = str(abs(pi - num))
                print a[:6], a[-6:]
    generalTests()
    mixedTests()
    errorTests()
    mpfTests()
    mpcTests()
    mpiTests()
    comparisonTest()
    fracTest()
    exit(0)
