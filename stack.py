'''
$Id: stack.py 1.17 2009/02/09 17:04:00 donp Exp $

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
from convert import *
from debug import *

# Exceptions for the Stack class
class CalcException(Exception):          pass
class StackIsEmpty(CalcException):       pass
class NotEnoughArguments(CalcException): pass
class FunctionFailed(CalcException):     pass

class Stack(object):
    '''This object provides a stack and is intended to be used as an RPN
    calculator.  The minimum functionality is present, however.  You, the
    user, will need to handle the persistence of the stack (should you wish
    it).

    Besides providing the stack and the usual stack functions, the only
    major functionality is the machinery to apply unary and binary
    functions to the elements on the stack.  You pass in the function
    you want to execute with along with optional indicators of the type(s)
    that the argument(s) must be converted to.

    There are five numerical types supported:  integers, Rational objects,
    and the three types from the mpmath module:  mpf (reals), mpc (complex
    numbers), and mpi (interval numbers).

    Note that python floats are NOT supported, as this calculator engine is
    intended to support arbitrary precision arithmetic.  However, there's
    nothing to prevent you from storing any objects (floats, strings, etc.)
    on the stack; you'll just get exceptions if you try calling the typical
    numerical functions on them.
    '''
    def __init__(self):
        '''The stack is implemented as a list; the top of the stack is the
        last element.
        '''
        self.stack = []

    def unary(self, function, arg_type=None):
        '''Apply the function to the object on the top of the stack and
        replace the top of the stack with the result.  arg_type is used to
        change the stack element to the indicated type before calling the
        function.
        '''
        if not self.stack:
            raise NotEnoughArguments("%s" % fln())
        try:
            x = self.stack[-1]
            if arg_type:
                x = Convert(x, arg_type)
            result = function(x)
            self.stack[-1] = result
        except Exception, e:
            raise FunctionFailed("%s" % fln() + str(e))

    def binary(self, function, arg1_type=None, arg2_type=None):
        '''Apply the function to the two objects on the top of the stack
        and replace the two top of stack objects with the result.  Note
        that the next-to-top element of the stack is the first argument
        of the function call -- this is consistent with e.g. typical
        HP RPN calculators.  The arg_types are used to change the type
        of the object before the function call.
        '''
        if len(self.stack) < 2:
            raise NotEnoughArguments("%s" % fln())
        try:
            x = self.stack[-1]
            if arg1_type: x = Convert(x, arg1_type)
            y = self.stack[-2]
            if arg2_type: y = Convert(y, arg2_type)
            result = function(y, x)
            del self.stack[-2:]
            self.stack.append(result)
        except Exception, e:
            raise FunctionFailed("%s" % fln() + str(e))

    def swap(self):
        if len(self.stack) < 2:
            raise NotEnoughArguments("%s" % fln())
        self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

    def size(self):
        return len(self.stack)

    def push(self, x):
        self.stack.append(x)

    def pop(self):
        if self.stack:
            return self.stack.pop(-1)
        else:
            raise StackIsEmpty("%s" % fln() + "Stack is empty (tried to pop)")

    def roll(self):
        if self.stack:
            if len(self.stack) == 1:
                return
            self.stack = [self.stack.pop(-1)] + self.stack
        else:
            raise StackIsEmpty("%s" % fln() + "Stack is empty (tried to roll)")

    def clear_stack(self):
        self.stack = []

    def __setitem__(self, i, value):
        # i = 0 is top of stack
        if len(self.stack) == 0:
            raise StackIsEmpty("%s" % fln() + "Stack is empty (tried to set item %d)" % i)
        if i < 0 or i >= len(self.stack) - 1:
            raise IndexError("%s" % fln() + "Stack size is %d" % len(self.stack))
        self.stack[len(self.stack) - 1 - i] = value

    def __getitem__(self, i):
        # i = 0 is top of stack
        n = len(self.stack)
        if n == 0:
            raise StackIsEmpty("%s" % fln() + "Stack is empty (tried to get item %d)" % i)
        if i < 0 or i >= n:
            raise IndexError("%s" % fln() + "Stack size is smaller than %d" % (n+1))
        return self.stack[n - 1 - i]

    def _string(self, func, size=0):
        '''Used to pretty print the stack.  func should be a function that
        will format a number.  If size is nonzero, only display that many
        items.  Note:  we make a copy of the stack so we can't possibly
        mess it up.
        '''
        s, fmt = self.stack[:], "%2d: %s"
        if not size or size > len(s): size = max(1, len(s))
        s.reverse()
        s = s[:size]
        s.reverse()
        size -= 1
        m = []
        for i in xrange(len(s)):
            m.append(fmt % (size - i, func(s[i])))
        s = '\n'.join(m)
        # Special treatment for the first four registers:  name them x, y,
        # z, t (as is done for HP calculators).
        if 0:
            s = s.replace(" 0: ", " x: ")
            s = s.replace(" 1: ", " y: ")
            s = s.replace(" 2: ", " z: ")
            s = s.replace(" 3: ", " t: ")
        return s

    def __str__(self):
        s = ""
        if self.stack: s = self._string(str)
        return s

    def __repr__(self):
        s = ""
        if self.stack: s = self._string(repr)
        return s

if __name__ == "__main__":
    # Unit tests
    def add(x, y):
        try: return x + y
        except: return y + x
    def StackManipulation():
        e = Stack()
        e.push(3)
        e.push(2)
        e.push(88)
        e[0] = 1  # Tests __setitem__
        e.swap()
        assert e[0] == 2 and e[1] == 1 and e[2] == 3
        e.roll()
        assert e[0] == 1 and e[1] == 3 and e[2] == 2
        e.pop()
        assert e[0] == 3 and e[1] == 2 and e.size() == 2
        x = e.pop()
        assert e[0] == 2 and e.size() == 1 and x == 3
        e.clear_stack()
        assert e.size() == 0
    def UnaryFunctions():
        e = Stack()
        c = mpc(2, -3)
        e.push(c)
        e.unary(sin)
        assert e[0] == sin(c)
    def BinaryFunctions():
        e = Stack()
        e.push(2)
        e.push(1)
        e.binary(add)
        assert e[0] == 3 and e.size() == 1
        e.clear_stack()
        e.push(Rational(3, 8))
        e.push(Rational(3, 8))
        e.binary(add)
        assert e[0] == Rational(3, 4)
    StackManipulation()
    UnaryFunctions()
    BinaryFunctions()
    exit(0)
