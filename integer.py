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

hexdigits = {
    "0" : "0000", "1" : "0001", "2" : "0010", "3" : "0011", "4" : "0100",
    "5" : "0101", "6" : "0110", "7" : "0111", "8" : "1000", "9" : "1001",
    "a" : "1010", "b" : "1011", "c" : "1100", "d" : "1101", "e" : "1110",
    "f" : "1111"}

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

    def __init__(self, value=0):
        self.n = 0
        self.my_num_bits = Zn.num_bits
        self.my_is_signed = Zn.is_signed
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
        return Zn.num_bits

    def set_bits(self, bits):
        if not isinstance(bits, int) and \
           not isinstance(bits, long) and \
           not isinstance(bits, Zn):
            msg = "%sNumber of bits must be an integer"
            raise ValueError(msg % fln())
        if bits < 0:
            msg = "%sNumber of bits in integer must be >= 0"
            raise ValueError(msg % fln())
        if bits != self.my_num_bits:
            Zn.num_bits = bits
            self.my_num_bits = bits
            if bits == 0:
                Zn.base = 0 # Will cause 0 div if we use for % calc
            else:
                Zn.base = 2**bits
            self._update()

    bits = property(get_bits, set_bits, \
        doc="Number of bits in integer (0 for unlimited)")

    def get_signed(self):
        return Zn.is_signed

    def set_signed(self, signed):
        if signed != True and signed != False:
            raise ValueError("%ssigned must be True or False" % fln())
        Zn.is_signed = signed
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
        if Zn.num_bits != 0:
            assert Zn.base == 2**Zn.num_bits
        self.my_num_bits  = Zn.num_bits
        self.my_is_signed = Zn.is_signed
        if Zn.num_bits == 0:
            Zn.is_signed = True
            self.my_is_signed = True
        else:
            if Zn.is_signed:
                self.n &= (Zn.base - 1)  # Mask off the desired bits
                # If high bit is on, then convert to negative in 2's
                # complement
                if self.n & 2**(Zn.num_bits - 1):
                    self.n -= Zn.base
            else:
                self.n %= Zn.base
        # Check our invariants
        if Zn.num_bits == 0:
            assert Zn.is_signed == True
        else:
            if Zn.is_signed:
                assert -(Zn.base >> 1) <= self.n < (Zn.base >> 1)
            else:
                assert 0 <= self.n < Zn.base
        assert self.my_num_bits  == Zn.num_bits
        assert self.my_is_signed == Zn.is_signed

    def _check_type(self, y):
        '''y must be a Zn object for us to interoperate with.  We can
        convert regular integers.
        '''
        if isinstance(y, int) or isinstance(y, long):
            y = Zn(y)
        elif not isinstance(y, Zn):
            return False
        if y.bits != Zn.num_bits:
            y._update()
        if self.bits != Zn.num_bits:
            self._update()
        return y

    def __hex__(self):
        self._update()
        t = ""
        if Zn.num_bits != 0:
            t = self._suffix()
        sign = ""
        if self.n < 0: sign = "-"
        num_hex_digits, r = divmod(Zn.num_bits, 4)
        if r != 0: num_hex_digits += 1
        s = hex(abs(self.n))[2:]        # Remove 0x
        if s[-1] == "L": s = s[:-1]     # Remove "L"
        if Zn.num_bits != 0:
            while len(s) < num_hex_digits:
                s = "0" + s
        if Zn.num_bits != 0:  assert len(s) == num_hex_digits
        return sign + "0x" + s + t

    def __oct__(self):
        self._update()
        t = ""
        if Zn.num_bits != 0:
            t = self._suffix()
        sign = ""
        if self.n < 0: sign = "-"
        num_oct_digits, r = divmod(Zn.num_bits, 3)
        if r != 0: num_oct_digits += 1
        s = oct(abs(self.n))[1:]    # Remove leading zero
        if s[0] == "o":  s = s[1:]  # Remove leading 'o' if present
        if Zn.num_bits != 0:
            while len(s) < num_oct_digits:
                s = "0" + s
        if Zn.num_bits != 0:  assert len(s) == num_oct_digits
        return sign + "0o" + s + t

    def bin(self):
        'Binary representation'
        self._update()
        t = ""
        if Zn.num_bits != 0:
            t = self._suffix()
        sign = ""
        if self.n < 0: sign = "-"
        h = hex(abs(self.n))[2:]
        while len(h) > 1 and h[0] == "0":  # Remove leading 0's
            h = h[1:]
        s = ""
        for digit in h:
            if digit != "L":
                s += hexdigits[digit]
        if Zn.num_bits != 0:
            while len(s) > Zn.num_bits:  # Trim leading 0's to get num bits
                assert s[0] == "0", "s = '%s'" % s
                s = s[1:]
        if Zn.num_bits == 0:
            while len(s) > 1 and s[0] == "0":  # Remove leading 0's
                s = s[1:]
        else:
            if len(s) > Zn.num_bits:
                s = s[len(s) - Zn.num_bits:]
            else:
                # Add leading zeros if length is not == num bits
                while len(s) < Zn.num_bits:
                    s = "0" + s
        if Zn.num_bits != 0:
            assert len(s) == Zn.num_bits, "s='%s'  %d bits" % (s, Zn.num_bits)
        return sign + "0b" + s + t

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
        if Zn.is_signed:
            return fmt % ("s", Zn.num_bits)
        else:
            return fmt % ("u", Zn.num_bits)

    def __str__(self):
        self._update()
        if Zn.num_bits == 0:
            s = str(self.value)
        else:
            t = self._suffix()
            if Zn.is_signed:
                s = str(self.value) + t
            else:
                if self.n < 0:
                    s = str(Zn.base + self.n)
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
        if Zn.is_signed == True and self.n == -(Zn.base >> 1):
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
        if self.n == 0 and Zn.negate_zero and Zn.is_signed:
            return Zn(-(Zn.base >> 1))
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
        z = self._check_type(y)
        if z:
            return Zn(self.value + z.value)
        return self.value + y

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
        z = self._check_type(y)
        if z:
            return Zn(self.value - z.value)
        return self.value - y

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
        z = self._check_type(y)
        if z:
            return Zn(self.value * z.value)
        return self.value * y

    def __imul__(self, y):
        z = self._check_type(y)
        if z:
            self.value *= z.value
            return self
        return self.value * y

    def __rmul__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value * z.value)
        return self.value * y

    def __div__(self, y):
        y = self._check_type(y)
        if Zn.use_C_division:
            if Zn.is_signed == True:
                sign = self._sgn(self.n)*self._sgn(y.n)
                if Zn.num_bits != 0:
                    assert -(Zn.base >> 1) <= self.n < (Zn.base >> 1)
                    assert -(Zn.base >> 1) <= y.n    < (Zn.base >> 1)
                    m = Zn.base >> 1
                    return Zn(sign*((abs(self.value) % m)//(abs(y.value) % m)))
                else:
                    return Zn(sign*(abs(self.value)//abs(y.value)))
            else:
                if Zn.num_bits != 0:
                    assert 0 <= self.n < Zn.base
                    assert 0 <= y.n    < Zn.base
                return Zn(self.n//y.n)
        else:
            return Zn(self.value//y.value)

    def __idiv__(self, y):
        y = self._check_type(y)
        if Zn.use_C_division:
            sign_x = self._sgn(self.value)
            sign_y = self._sgn(y.value)
            self.value = sign_x*sign_y*(abs(self.value)//abs(y.value))
        else:
            self.value //= y.value
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
        if isinstance(y, Zn): y = y.value
        return mpf(self.value) / mpf(y)

    def __pow__(self, y):
        z = self._check_type(y)
        if z:
            return Zn(self.value ** z.value)
        return self.value ** y

class ipaddr(Zn):
    def __init__(self, value=0, cidr=None):
        Zn.__init__(self, value)
        self.my_is_signed = False
        if isinstance(value, ipaddr):
            self.is_ipv4 = value.is_ipv4
            self.is_ipv6 = value.is_ipv6
        else:
            if self.value > 0xffffffff:
                self.is_ipv4 = False
                self.is_ipv6 = True
                self.my_num_bits = 128
            elif self.value > 0:
                self.is_ipv4 = True
                self.is_ipv6 = False
                self.my_num_bits = 32
            else:
                self.is_ipv4 = True
                self.is_ipv6 = True
                self.my_num_bits = 128
        if isinstance(cidr, str):
            cidr = int(cidr)
        if cidr is not None:
            if cidr < 0:
                raise ValueError("CIDR must not be negative")
            if self.is_ipv4 and cidr > 32:
                raise ValueError("CIDR for a IPv4 address cannot be greater than 32")
            elif self.is_ipv6 and cidr > 128:
                raise ValueError("CIDR for a IPv6 address cannot be greater than 128")
        self.cidr = cidr

    def __str__(self):
        'IP address representation'
        pack = lambda n: n>0 and pack(n>>8)+chr(n&0xff) or ''

        cidr = ''
        if self.cidr is not None:
            cidr = '/%d'%self.cidr
        v = pack(self.value)
        if self.value == 0:
            return '::'
        if self.is_ipv6:
            # ipv6 address?
            if len(v) < 16:
                v = '\x00'*(16-len(v))+v
            return socket.inet_ntop(socket.AF_INET6, v)+cidr
        else:
            if len(v) < 4:
                v = '\x00'*(4-len(v))+v
            return socket.inet_ntop(socket.AF_INET, v)+cidr

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
