'''
$Id: convert.py 1.8 2009/02/09 17:04:00 donp Exp $

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

from mpmath import *
from rational import Rational
from integer import Zn, isint
from julian import Julian

# Strings to identify types
INT = "z"
RAT = "q"
MPF = "r"
MPC = "c"
MPI = "i"
JUL = "t"

def Convert(x, arg_type, digits=0):
    '''Converts amongst the numerical types.  Some conversions lose
    information.  The digits argument controls the precision of a conversion
    of a real to a rational.
    '''
    e = SyntaxError("Unknown type")
    if arg_type == INT:
        if isint(x):                  return Zn(x)
        elif isinstance(x, Rational): return Zn(int(mpf(x.n)/mpf(x.d)))
        elif isinstance(x, mpf):      return Zn(int(x))
        elif isinstance(x, mpc):      return Zn(int(abs(x)))
        elif isinstance(x, mpi):      return Zn(int(x.mid))
        elif isinstance(x, Julian):   return Zn(int(x))
        else: raise e
    elif arg_type == RAT:
        if isint(x):                  return Rational(int(x), 1)
        elif isinstance(x, Rational): return x
        elif isinstance(x, mpf):      return Rational().frac(x, digits)
        elif isinstance(x, mpc):      return Rational().frac(abs(x), digits)
        elif isinstance(x, mpi):      return Rational(x.mid)
        elif isinstance(x, Julian):   return Rational().frac(x.to_mpf(), digits)
        else: raise e
    elif arg_type == MPF:
        if isint(x):                  return mpf(int(x))
        elif isinstance(x, Rational): return x.mpf()
        elif isinstance(x, mpf):      return x
        elif isinstance(x, mpc):      return abs(x)
        elif isinstance(x, mpi):      return x.mid
        elif isinstance(x, Julian):   return x.to_mpf()
        else: raise e
    elif arg_type == MPC:
        if isint(x):                  return mpc(int(x))
        elif isinstance(x, Rational): return x.mpc()
        elif isinstance(x, mpf):      return mpc(x, 0)
        elif isinstance(x, mpc):      return x
        elif isinstance(x, mpi):      return mpc(x.mid, 0)
        elif isinstance(x, Julian):   return mpc(x.to_mpf(), 0)
        else: raise e
    elif arg_type == MPI:
        if isint(x):                  return mpi(int(x))
        elif isinstance(x, Rational): return x.mpi()
        elif isinstance(x, mpf):      return mpi(x)
        elif isinstance(x, mpc):      return mpi(abs(x))
        elif isinstance(x, mpi):      return x
        elif isinstance(x, Julian):
            if isinstance(x.value, mpf):  return mpi(x.value)
            else:                         return x.value
        else: raise e
    elif arg_type == JUL:
        if isint(x):                  return Julian(int(x))
        elif isinstance(x, Rational): return Julian(mpf(x.n)/mpf(x.d))
        elif isinstance(x, mpf):      return Julian(x)
        elif isinstance(x, mpc):      return Julian(abs(x))
        elif isinstance(x, mpi):      return Julian(x)
        elif isinstance(x, Julian):   return x
        else: raise e
    else:
        raise SyntaxError("Unknown type")

if __name__ == "__main__":
    # Unit tests
    def TestConvert():
        n = 1
        number_types = (
            Zn(n),
            Rational(n, n),
            mpf(n),
            mpc(n, n),
            mpi(n),
            Julian(n),
        )
        results = (
            (INT, Zn),
            (RAT, Rational),
            (MPF, mpf),
            (MPC, mpc),
            (MPI, mpi),
            (JUL, Julian)
        )
        for number in number_types:
            for typename, type in results:
                assert isinstance(Convert(number, typename), type)
    TestConvert()
    exit(0)
