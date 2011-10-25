'''
$Id: integer.py 1.22 2009/02/10 05:24:01 donp Exp $

Zn objects can be set to behave as a signed or unsigned n n-bit integer
in addition to a regular python integer.  The properties you can set
are:

    bits        Must be >= 0.  If 0, then the object behaves like a
                regular python integer.  If > 0, then the object
                behaves like an integer with that number of bits.

    signed      If true, behaves as a signed integer; otherwise
                behaves as an unsigned integer.  Since the normal unlimited
                precision python integers cannot have an unsigned
                characteristic, this only applies when bits is
                nonzero.

    C_division  If True, integer division behaves like it does in C;
                i.e., 3/8 == -3/8 == 3/-8 == 0.  If False, then the
                behavior is pythonic:  floor division.  This means
                -3/8 == 3/-8 == -1.

Four bit two's complement representation:
Uns binary 2's comp
15  1111   -1
14  1110   -2
13  1101   -3
12  1100   -4
11  1011   -5
10  1010   -6
 9  1001   -7
 8  1000   -8
 7  0111    7
 6  0110    6
 5  0101    5
 4  0100    4
 3  0011    3
 2  0010    2
 1  0001    1
 0  0000    0
'''

from debug import *
from mpmath import mpf, mpi
import socket

try: from pdb import xx  # pdb.set_trace is xx; easy to find for debugging
except: pass

def isint(x):
    return isinstance(x, int) or isinstance(x, long) or isinstance(x, Zn)

class Zn(object):
    # These characters are used in the str representation of Zn objects
    # Example:  a 4-bit signed value of -2 is given as '-2<4s>'.
    left  = "<"
    right = ">"
    space = ""  # Put a space between the number and its designator

    # These variables are private
    num_bits = 0
    is_signed = True
    use_C_division = False
    base = 0
    high_unsigned = 0
    high_signed = 0

    # This variable is used to hold 0, 1, or 2.  These settings have
    # to do with the subtleties of negating 2's complement numbers.
    # See the comments in the __neg__ method.
    negate_zero = 0

    def __init__(self, value=0, proto=None):
        self.n = 0
        if proto is not None:
            self.num_bits = proto.num_bits
            self.is_signed = proto.is_signed
        elif isinstance(value, Zn):
            self.num_bits = value.num_bits
            self.is_signed = value.is_signed
        else:
            self.num_bits = Zn.num_bits
            self.is_signed = Zn.is_signed
        if self.num_bits > 0:
            self.base = 2**self.num_bits
        if type(value) == str:
            self._set_from_string(value)
        elif isinstance(value, int) or isinstance(value, long):
            self.value = value
        elif isinstance(value, Zn):
            self.value = value.value
        else:
            raise TypeError("%sCan't set integer from value '%s'" % \
                (fln(), str(value)))
        self._update()

    def _set_from_string(self, value):
        '''We set our value from a string.  This can be either a
        regular string for an integer or long or a string gotten from
        our str() method.  In the second case, the value will be made
        to fit in the current representation, regardless of how many
        bits or whether it was signed or unsigned when str'd.  Note
        that the left character must match our current setting or an
        exception will be raised.
        '''
        assert type(value) == type("")
        try:
            if Zn.left in value:
                self.value = int(value.split(Zn.left)[0])
            else:
                self.value = int(value)
        except:
            msg = "%sCan't set integer from '%s'"
            raise ValueError(msg % (fln(), value))


    # Properties
    def get_C_division(self):
        return Zn.use_C_division

    def set_C_division(self, use_C_division):
        if use_C_division != True and use_C_division != False:
            msg = "%suse_C_division class variable must be True or False"
            raise ValueError(msg % fln())
        Zn.use_C_division = use_C_division

    C_division = property(get_C_division, set_C_division, \
        doc="Set to True for C type integer division")

    def get_bits(self):
        return self.num_bits

    def set_bits(self, bits):
        if not isinstance(bits, int) and \
           not isinstance(bits, long) and \
           not isinstance(bits, Zn):
            msg = "%sNumber of bits must be an integer"
            raise ValueError(msg % fln())
        if bits < 0:
            msg = "%sNumber of bits in integer must be >= 0"
            raise ValueError(msg % fln())
        if bits != self.num_bits:
            self.num_bits = bits
            self.num_bits = bits
            if bits == 0:
                self.base = 0 # Will cause 0 div if we use for % calc
            else:
                self.base = 2**bits
            self._update()

    bits = property(get_bits, set_bits, \
        doc="Number of bits in integer (0 for unlimited)")

    def get_signed(self):
        return self.is_signed

    def set_signed(self, signed):
        if signed != True and signed != False:
            raise ValueError("%ssigned must be True or False" % fln())
        self.is_signed = signed
        self._update()

    signed = property(get_signed, set_signed, doc="Signed if True")

    def set_value(self, value):
        if isinstance(value, int) or isinstance(value, long):
            self.n = value
        elif isinstance(value, Zn):
            self.n = value.n
        else:
            try:
                self.n = int(value)
            except:
                raise TypeError("%sCan't set integer from '%s'" % \
                    (fln(), str(value)))
        self._update()

    def get_value(self):
        return self.n

    value = property(get_value, set_value, doc="Integer's value")

    def set_negate_zero(self, value):
        msg = "%svalue must be 0, 1, or 2"
        if not isinstance(value, int) and not isinstance(value, long):
            raise ValueError(msg % fln())
        if value < 0 or value > 2:
            raise ValueError(msg % fln())
        Zn.negate_zero = value
        self._update()

    def get_negate_zero(self):
        return Zn.negate_zero

    negative_zero = property(get_negate_zero, set_negate_zero, \
        doc="If true, -Zn(0) == Zn(-(2**(n-1)))")

    def _update(self):
        "The object's state has changed."
        if self.num_bits != 0:
            assert self.base == 2**self.num_bits
        if self.num_bits == 0:
            self.is_signed = True
        else:
            if self.is_signed:
                self.n &= (self.base - 1)  # Mask off the desired bits
                # If high bit is on, then convert to negative in 2's
                # complement
                if self.n & 2**(self.num_bits - 1):
                    self.n -= self.base
            else:
                self.n &= (self.base-1)
        # Check our invariants
        if self.num_bits == 0:
            assert self.is_signed == True
        else:
            if self.is_signed:
                assert -(self.base >> 1) <= self.n < (self.base >> 1)
            else:
                assert 0 <= self.n < self.base

    def _auto_cast(self, y):
        '''y must be a Zn object for us to interoperate with.  We can
        convert regular integers.
        '''
        if isint(y):
            p = Zn()
            p.is_signed = y.is_signed and self.is_signed
            p.num_bits = max(y.num_bits, self.num_bits)
            y1 = Zn(y, proto=p)
            x1 = Zn(self, proto=p)
            return y1, x1
        elif isinstance(y, mpf):
            return y, mpf(self.value)
        elif isinstance(y, mpc):
            return y, mpc(self.value, 0)
        elif isinstance(y, Julian):
            return y, Julian(self.value)
        elif isinstance(y, ctx_iv.ivmpf):
            return y, mpi(self.value)
        elif isinstance(y, Rational):
            return y, Rational(self.value, 1)
        else:
            return y, self.value

    def __hex__(self):
        self._update()
        t = ""
        if self.num_bits != 0:
            t = self._suffix()
        sign = ""
        num_hex_digits, r = divmod(self.num_bits, 4)
        if r != 0: num_hex_digits += 1
        v = self.n
        if v < 0:
            sign = " "
            if self.is_signed and self.num_bits != 0:
                v = self.n
                v &= (self.base - 1)  # Mask off the desired bits
                v |= (2**(self.bits - 1))
        s = hex(v)[2:]
        if s[-1] == "L": s = s[:-1]     # Remove "L"
        if self.num_bits != 0:
            while len(s) < num_hex_digits:
                s = "0" + s
        if self.num_bits != 0:  assert len(s) == num_hex_digits
        return "%s0x%s%s" % (sign, s, t)

    def __oct__(self):
        self._update()
        t = ""
        if self.num_bits != 0:
            t = self._suffix()
        sign = ""
        num_oct_digits, r = divmod(self.num_bits, 3)
        if r != 0: num_oct_digits += 1
        v = self.n
        if v < 0:
            sign = " "
            if self.is_signed and self.num_bits != 0:
                v = self.n
                v &= (self.base - 1)  # Mask off the desired bits
                v |= (2**(self.bits - 1))
        s = oct(v)[1:]
        if s[0] == "o":  s = s[1:]  # Remove leading 'o' if present
        if self.num_bits != 0:
            while len(s) < num_oct_digits:
                s = "0" + s
        if self.num_bits != 0:  assert len(s) == num_oct_digits
        return "%s0o%s%s" % (sign, s, t)

    def bin(self):
        'Binary representation'
        self._update()
        t = ""
        if self.num_bits != 0:
            t = self._suffix()
        sign = ""
        v = self.n
        if v < 0:
            sign = " "
            if self.is_signed and self.num_bits != 0:
                v = self.n
                v &= (self.base - 1)  # Mask off the desired bits
                v |= (2**(self.bits - 1))
        s = bin(v)[2:]
        while len(s) > 1 and s[0] == "0":  # Remove leading 0's
            s = s[1:]
        if s[-1] == "L": s = s[:-1]     # Remove "L"
        if self.num_bits != 0:
            while len(s) > self.num_bits:  # Trim leading 0's to get num bits
                assert s[0] == "0", "s = '%s'" % s
                s = s[1:]
        if self.num_bits == 0:
            while len(s) > 1 and s[0] == "0":  # Remove leading 0's
                s = s[1:]
        else:
            if len(s) > self.num_bits:
                s = s[len(s) - self.num_bits:]
            else:
                # Add leading zeros if length is not == num bits
                while len(s) < self.num_bits:
                    s = "0" + s
        if self.num_bits != 0:
            assert len(s) == self.num_bits, "s='%s'  %d bits" % (s, self.num_bits)
        return "%s0b%s%s" % (sign, s, t)

    def roman(self):
        self._update()
        sign = " "
        v = self.n
        if v < 0:
            sign = "-"
        v = abs(v)
        s = []
        if v > 3999:
            return str(self)
        while v >= 1000:
            s.append('M')
            v -= 1000
        if v >= 900:
            s.append('CM')
            v -= 900
        if v >= 500:
            s.append('D')
            v -= 500
        if v >= 400:
            s.append('CD')
            v -= 400
        while v >= 100:
            s.append('C')
            v -= 100
        if v >= 90:
            s.append('XC')
            v -= 90
        if v >= 50:
            s.append('L')
            v -= 50
        if v >= 40:
            s.append('XL')
            v -= 40
        while v >= 10:
            s.append('X')
            v -= 10
        if v >= 9:
            s.append('IX')
            v -= 9
        if v >= 5:
            s.append('V')
            v -= 5
        if v >= 4:
            s.append('IV')
            v -= 4
        while v >= 1:
            s.append('I')
            v -= 1
        return "%s%s" % (sign, ''.join(s))

    def __int__(self):
        return self.n

    def __long__(self):
        return self.n

    def __float__(self):
        return mpf(self.n)

    def __complex__(self):
        return mpc(self.n, 0)

    def _suffix(self):
        fmt = Zn.space + Zn.left + "%s%d" + Zn.right
        if self.is_signed:
            return fmt % ("s", self.num_bits)
        else:
            return fmt % ("u", self.num_bits)

    def __str__(self):
        self._update()
        if self.num_bits == 0:
            s = str(self.value)
        else:
            t = self._suffix()
            if self.is_signed:
                s = str(self.value) + t
            else:
                if self.n < 0:
                    s = str(self.base + self.n)
                else:
                    s = str(self.value)
                s += t
        return s

    def __repr__(self):
        if debug():
            if self.signed:
                s = 's'
            else:
                s = 'u'
            return "Zn(%d<%c%d>)"%(self.n, s, self.bits)
        return "Zn(%d)" % self.n

    def _sgn(self, x):
        if x >= 0: return 1
        return -1

    def __abs__(self):
        'See comments under __neg__ for some subleties.'
        msg = "%sCan't take the absolute value of the most negative number"
        if self.is_signed == True and self.n == -(self.base >> 1):
            raise ValueError(msg % fln())
        return Zn(abs(self.n))

    def __neg__(self):
        '''Dealing with the subtleties of 2's complement arithmetic.
        For further details, see
        http://en.wikipedia.org/wiki/Two%27s_complement_arithmetic.

        The negate_zero flag allows three different behaviors with
        regards to negating zero.  I'll use 4-bit integer arithmetic
        to illustrate things.

            0   Normal 2's complement arithmetic.  -Zn(-8) == Zn(-8).
            1   -Zn(-8) == Zn(0), -Zn(0) == Zn(0).
            2   -Zn(-8) == Zn(0), -Zn(0) == Zn(-8).

        In 2's complement arithmetic, the negative of a number is
        gotten by inverting the bits and adding one.  This is handy
        from a hardware perspective because it's fast, but it does
        leave us with a "special" number:  the most negative number.
        It's special because it is its own negative.  This causes a
        problem if you wish to calculate its absolute value, since it
        doesn't exist (in an n-bit signed 2's complement system, the
        values represented go from -2**n to (2**n)-1; 2**n, the
        absolute value of -2**n, can't be represented.  Thus, the only
        logical way to handle abs(-2**n) is to raise an exception.

        Here are the bit representations:
             U        S           S   U
             7  0111  7    1111  -1  15
             6  0110  6    1110  -2  14
             5  0101  5    1101  -3  13
             4  0100  4    1100  -4  12
             3  0011  3    1011  -5  11
             2  0010  2    1010  -6  10
             1  0001  1    1001  -7   9
             0  0000  0    1000  -8   8
        The S are the signed numbers and the U are the unsigned
        numbers.

        The other two situations are provided should the user prefer
        to see that behavior.  All three behaviors are a bit
        counterintuitive, but negate_zero == 1 is probably closest to
        common experience in that -0 == 0.  negate_zero == 2 is
        perhaps logically more satisfying in that all bit patterns are
        now paired together and switch between each other on negation.

        This behavior is now obvious to me, but it wasn't obvious when
        I first wrote __neg__; I simply returned Zn(-self.value).  I
        was playing around with 64 bit integers.  In the calculator, I
        set int64, then entered -1 into x.  I changed to uint64 and
        this changed to 18446744073709551615<u64>.  I divided by 2 and
        cast it back to an I to get 9223372036854775808<u64>.
        Changing this to an int64 yielded -9223372036854775808<s64>.
        This is when I noticed chs was idempotent on this number.  At
        first I thought it was a bug and marked it down to
        investigate.  I reproduced the behavior on 4-bit integers and
        then understood what was going on.  I wish I had read the
        wikipedia article first, as it would have saved me a bunch of
        time.  :^)  For your final lesson in 2's complement arithmetic,
        predict what -9223372036854775808<s64> squared is.

        This also indicates a lesson I learned in a software course:
        always test at the boundaries.  I intuitively knew to mess
        around with numbers like 2**(n-1) and flip between the signed
        an unsigned values and see what happened.
        '''
        if self.n == 0 and Zn.negate_zero and self.is_signed:
            return Zn(-(self.base >> 1))
        return Zn(-self.n)

    def __coerce__(self, other):
        # hmmmmm.... the types we can encounter
        if isint_native(other):
            return self, Zn(other)
        ot = type(other)
        if ot == mpc:
            return mpc(self.value, 0), other
        if ot == mpf:
            return mpf(self.value), other
        if isint_native(other):
            return self, Zn(other)
        print "Zn could not coerce type '%s'"%str(ot)
        return None

    def __add__(self, y):
        y1, x1 = self._auto_cast(y)
        if isinstance(y1, Zn) and isinstance(x1, Zn):
            return Zn(x1.value + y1.value, proto=x1)
        return x1 + y1

    def __iadd__(self, y):
        z = self._check_type(y)
        if z:
            self.value += z.value
            return self
        return self.value + y

    def __radd__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value + z.value)
        return self.value + y

    def __sub__(self, y):
        y1, x1 = self._auto_cast(y)
        if isinstance(y1, Zn) and isinstance(x1, Zn):
            return Zn(x1.value - y1.value, proto=x1)
        return x1 - y1

    def __isub__(self, y):
        z = self._check_type(y)
        if z:
            self.value -= z.value
            return self
        return self.value - y

    def __rsub__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(-self.value + z.value)
        return -self.value + y

    def __mul__(self, y):
        y1, x1 = self._auto_cast(y)
        if isinstance(y1, Zn) and isinstance(x1, Zn):
            return Zn(x1.value * y1.value, proto=x1)
        return x1 * y1

    def __imul__(self, y):
        y1, x1 = self._auto_cast(y)
        if z:
            self.value *= z.value
            return self
        return self.value * y
        self.is_signed = x1.is_signed
        self.num_bits = x1.num_bits
        self.value = x1.value
        return self

    def __rmul__(self, y):
        y1, x1 = self._auto_cast(y)
        if isinstance(y1, Zn) and isinstance(x1, Zn):
            return Zn(x1.value * y1.value, proto=x1)
        return x1 * y1

    def __div__(self, y):
        y1, x1 = self._auto_cast(y)
        if Zn.use_C_division:
            if x1.is_signed == True:
                sign = x1._sgn(x1.n)*x1._sgn(y1.n)
                if x1.num_bits != 0:
                    assert -(x1.base >> 1) <= x1.n < (x1.base >> 1)
                    assert -(x1.base >> 1) <= y1.n    < (x1.base >> 1)
                    m = x1.base >> 1
                    return Zn(sign*((abs(x1.value) % m)//(abs(y1.value) % m)), proto=x1)
                else:
                    return Zn(sign*(abs(x1.value)//abs(y1.value)), proto=x1)
            else:
                if x1.num_bits != 0:
                    assert 0 <= x1.n < x1.base
                    assert 0 <= y1.n    < x1.base
                return Zn(x1.n//y1.n, proto=x1)
        else:
            return Zn(x1.value//y1.value, proto=x1)

    def __idiv__(self, y):
        y1, x1 = self._auto_cast(y)
        if not isinstance(y1, Zn) or not isinstance(x1, Zn):
            raise TypeError("Invalid types to integer __idiv__")
        if Zn.use_C_division:
            sign_x = x1._sgn(x1.value)
            sign_y = x1._sgn(y1.value)
            x1.value = sign_x*sign_y*(abs(x1.value)//abs(y1.value))
        else:
            x1.value //= y1.value
        self.is_signed = x1.is_signed
        self.num_bits = x1.num_bits
        self.value = x1.value
        return self

    def __rdiv__(self, y):
        z = self._check_type(y)
        if z:
            return z.__div__(self)
        return y / self.value

    __floordiv__ = __div__
    __ifloordiv__ = __idiv__
    __rfloordiv__ = __rdiv__

    def __mod__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value % z.value)
        return self.value % y

    def __imod__(self, y):
        z = self._check_type(y)
        if z:
            self.value %= z.value
            return self
        return self.value % y

    def __rmod__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(z.value % self.value)
        return z % self.value

    def __cmp__(self, y):
        if isinstance(y, Zn):
            if self.value < y.value:  return -1
            if self.value == y.value: return 0
            else:                     return 1
        elif isinstance(y, int) or isinstance(y, long):
            if self.value < y:  return -1
            if self.value == y: return 0
            else:               return 1
        elif isinstance(y, mpf):
            if mpf(self.value) < y:  return -1
            if mpf(self.value) == y: return 0
            else:                    return 1
        else:
            return -1

    def __and__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value & z.value)
        return self.value & y

    def __iand__(self, y):
        z = self._check_type(y)
        if z:
            self.value &= z.value
            return self
        return self.value & y

    def __rand__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(z.value & self.value)
        return y & self.value

    def __or__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value | y.value)
        return self.value | y

    def __ior__(self, y):
        z = self._check_type(y)
        if z:
            self.value |= z.value
            return self
        return self.value | y

    def __ror__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(z.value | self.value)
        return y | self.value

    def __xor__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value ^ z.value)
        return self.value ^ y

    def __ixor__(self, y):
        z = self._check_type(y)
        if z:
            self.value ^= z.value
            return self
        return self.value ^ y

    def __rxor__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(z.value ^ self.value)
        return y ^ self.value

    def __lshift__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value << z.value)
        return self.value << y

    def __ilshift__(self, y):
        z = self._check_type(y)
        if z:
            self.value <<= z.value
            return self
        return self.value << y

    def __rlshift__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(z.value << self.value)
        return y << self.value

    def __rshift__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value >> z.value)
        return self.value >> y

    def __irshift__(self, y):
        z = self._check_type(y)
        if z:
            self.value >>= z.value
            return self
        return self.value >> y

    def __rrshift__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(z.value << self.value)
        return y >> self.value

    def __invert__(self):
        return Zn(~self.value)

    def __truediv__(self, y):
        if isinstance(y, Zn): y = mpf(y.value)
        return self.value / y

    def __pow__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value ** z.value)
        return self.value ** y

class ipaddr(Zn):
    def __init__(self, value=0, cidr=None, ipvn=None, prototype=None):
        Zn.__init__(self)
        self.is_signed = False
        self.cidr = None
        if prototype is not None:
            self.ipvn = prototype.ipvn
            self.cidr = prototype.cidr
        else:
            if isinstance(value, ipaddr):
                self.ipvn = value.ipvn
                self.cidr = value.cidr
                value = value.value
            else:
                value = int(value)
            if ipvn is None:
                if value < 0xffffffff:
                    self.ipvn = 'ipv4'
                else:
                    self.ipvn = 'ipv6'
            else:
                self.ipvn = ipvn
            if isinstance(cidr, str):
                cidr = int(cidr)
            if cidr is not None:
                if cidr < 0:
                    raise ValueError("CIDR must not be negative")
                if self.ipvn == 'ipv4' and cidr > 32:
                    raise ValueError("CIDR for a IPv4 address cannot be greater than 32")
                elif self.ipvn == 'ipv6' and cidr > 128:
                    raise ValueError("CIDR for a IPv6 address cannot be greater than 128")
            self.cidr = cidr
        if self.ipvn == 'ipv4':
            self.bits = 32
        if self.ipvn == 'ipv6':
            self.bits = 128
        self.value = value
        self._update()

    def __str__(self):
        'IP address representation'
        cidr = ''
        if self.cidr is not None:
            cidr = '/%d'%self.cidr
        if self.ipvn == 'ipv6':
            pack = lambda n: n>0 and pack(n>>8)+chr(n&0xff) or ''
            v = pack(self.value)
            # ipv6 address?
            if len(v) < 16:
                v = '\x00'*(16-len(v))+v
            return ' %s%s' % (socket.inet_ntop(socket.AF_INET6, v), cidr)
        else:
            v = self.value
            v = [ (v >> 24) & 0xff, (v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff ]
            v = [ '%u'%c for c in v ]
            return ' %s%s' % ('.'.join(v), cidr)

    def __repr__(self):
        return "ipaddr(%x/%d)" % (self.n, self.cidr)

    def _check_type(self, v):
        if not isint(v):
            raise TypeError("Operations on IP addresses are limited to integers")
        if self.ipvn == 'ipv6' or v.ipvn == 'ipv6':
            ipvn = 'ipv6'
        else:
            ipvn = 'ipv4'
        return v, ipaddr(0, max(self.cidr, v.cidr), ipvn)

    def __add__(self, y):
        y = self._check_type(y)
        return ipaddr(self.value + y.value, self.cidr)

    def __iadd__(self, y):
        y = self._check_type(y)
        self.value += y.value
        return self

    def __sub__(self, y):
        y = self._check_type(y)
        return ipaddr(self.value - y.value, self.cidr)

    def __isub__(self, y):
        y = self._check_type(y)
        self.value -= y.value
        return self

    def __mul__(self, y):
        y = self._check_type(y)
        return ipaddr(self.value*y.value, self.cidr)


if __name__ == "__main__":
    # Run unit tests
    # Signed:    0  1  2  3  4  5  6  7  -8  -7  -6  -5  -4  -3  -2  -1
    # Unsigned:  0  1  2  3  4  5  6  7   8   9  10  11  12  13  14  15
    def sgn(x):
        if x < 0: return -1
        return 1
    def TestSignedPythonArithmetic(n, step=1):
        Zn().bits = n
        Zn().signed = True
        Zn().C_division = False
        m = 2**n >> 1
        it = xrange(-m, m, step)
        for i in it:
            for j in it:
                x, y = Zn(i), Zn(j)
                assert x+y == Zn((i+j))
                assert x-y == Zn((i-j))
                assert x*y == Zn((i*j))
                try: assert x//y == Zn(i//j)
                except ZeroDivisionError: pass
    def TestUnsignedPythonArithmetic(n, step=1):
        Zn().bits = n
        Zn().signed = False
        Zn().C_division = False
        b = 2**n
        it = xrange(0, b, step)
        for i in it:
            for j in it:
                x, y = Zn(i), Zn(j)
                assert x+y == Zn((i+j) % b)
                assert x-y == Zn((i-j) % b)
                assert x*y == Zn((i*j) % b)
                try: assert x/y == Zn((i//j) % b)
                except ZeroDivisionError: pass
    def TestSignedCArithmetic(n, step=1):
        Zn().bits = n
        Zn().signed = True
        Zn().C_division = True
        m = 2**n >> 1
        it = xrange(-m, m, step)
        for i in it:
            for j in it:
                x, y = Zn(i), Zn(j)
                assert x+y == Zn(i+j)
                assert x-y == Zn(i-j)
                assert x*y == Zn(i*j)
                try:
                    sign = sgn(i)*sgn(j)
                    assert x//y == Zn(sign*((abs(i) % m)//(abs(j) % m)))
                except ZeroDivisionError: pass
    def TestUnsignedCArithmetic(n, step=1):
        Zn().bits = n
        Zn().signed = False
        Zn().C_division = True
        it = xrange(0, 2**n, step)
        for i in it:
            for j in it:
                x, y = Zn(i), Zn(j)
                assert x+y == Zn(i+j)
                assert x-y == Zn(i-j)
                assert x*y == Zn(i*j)
                try:
                    assert x//y == Zn(i//j)
                except ZeroDivisionError: pass
    def BitTwiddling():
        Zn().bits = 4
        def twiddle(x, y, signed):
            u, v = Zn(x), Zn(y)
            u.signed = signed
            assert u & v == Zn(x & y)
            assert u | v == Zn(x | y)
            assert u ^ v == Zn(x ^ y)
            assert u << v == (Zn((x << y) % (Zn.high_unsigned - 1)))
            assert u >> v == Zn(x >> y)
            if y: assert u % v == Zn(x % y)
            assert ~u == Zn(~x)
            w = Zn(u.value); w &= v;  assert w == Zn(x & y)
            w = Zn(u.value); w |= v;  assert w == Zn(x | y)
            w = Zn(u.value); w ^= v;  assert w == Zn(x ^ y)
            w = Zn(u.value); w <<= v; assert w == Zn((x << y) % (Zn.high_unsigned - 1))
            w = Zn(u.value); w >>= v; assert w == Zn(x >> y)
        n = Zn.high_unsigned
        for i in xrange(n):
            for j in xrange(n):
                twiddle(i, j, True)
                twiddle(i, j, False)
        n = Zn.high_signed
        for i in xrange(-n, n):
            for j in xrange(-n, n):
                twiddle(i, j, True)
                twiddle(i, j, False)
    def Disallowed():
        '''Note that using lambda functions for the arithmetic operations
        doesn't work correctly -- e.g., 3 + Zn is allowed.
        '''
        def plus(x, y):
            return x + y
        x = Zn(1)
        oplist = (
            (lambda x, y: x + y,  "+"),
            (lambda x, y: x - y,  "-"),
            (lambda x, y: x * y,  "*"),
            (lambda x, y: x / y,  "/"),
            (lambda x, y: x // y, "//"),
            (lambda x, y: x % y,  "%"),
            (lambda x, y: x & y,  "&"),
            (lambda x, y: x | y,  "|"),
            (lambda x, y: x ^ y,  "^"),
            (lambda x, y: x << y, "<<"),
            (lambda x, y: x >> y, ">>"),
        )
        t = 3
        for op, opname in oplist:
            for arg in (t, long(t), float(t), complex(t, t)):
                try: y = op(arg, x); assert False, opname
                except TypeError: pass
                if arg != t and arg != long(t):
                    try: y = op(x, arg); assert False, opname
                    except TypeError: pass
    def TestChangingNumberOfBits():
        # Test signed
        results = (
            (15, -1, -1, -1),
            (14, -2, -2, -2),
            (13, -3, -3,  1),
            (12, -4, -4,  0),
            (11, -5,  3, -1),
            (10, -6,  2, -2),
            ( 9, -7,  1,  1),
            ( 8, -8,  0,  0),
            ( 7,  7, -1, -1),
            ( 6,  6, -2, -2),
            ( 5,  5, -3,  1),
            ( 4,  4, -4,  0),
            ( 3,  3,  3, -1),
            ( 2,  2,  2, -2),
            ( 1,  1,  1,  1),
            ( 0,  0,  0,  0),
        )
        x = Zn()
        x.bits = 4
        x.signed = True
        for item in results:
            i, compl, bits3, bits2 = item
            x.bits = 4
            x.value = i
            assert x.n == compl
            x.bits = 3
            assert x.n == bits3
            x.bits = 2
            assert x.n == bits2
        # Test unsigned
        results = (
            (15,  7,  3),
            (14,  6,  2),
            (13,  5,  1),
            (12,  4,  0),
            (11,  3,  3),
            (10,  2,  2),
            ( 9,  1,  1),
            ( 8,  0,  0),
            ( 7,  7,  3),
            ( 6,  6,  2),
            ( 5,  5,  1),
            ( 4,  4,  0),
            ( 3,  3,  3),
            ( 2,  2,  2),
            ( 1,  1,  1),
            ( 0,  0,  0),
        )
        x = Zn()
        x.bits = 4
        x.signed = False
        for item in results:
            i, bits3, bits2 = item
            x.bits = 4
            x.value = i
            assert x.n == i
            x.bits = 3
            assert x.n == bits3
            x.bits = 2
            assert x.n == bits2
    for n in xrange(1, 6):
        TestSignedPythonArithmetic(n)
        TestUnsignedPythonArithmetic(n)
        TestSignedCArithmetic(n)
        TestUnsignedCArithmetic(n)
    BitTwiddling()
    Disallowed()
    TestChangingNumberOfBits()
    exit(0)
