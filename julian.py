'''
$Id: julian.py 1.15 2009/02/11 02:39:22 donp Exp $

Provides a Julian object which behaves as either an mpf or mpi number.
It represents astronomical Julian days and can be arithmetically combined
with integers, reals, etc.

The representation is based on the algorithms given in "Astronomical
Algorithms", 2nd ed., by Jean Meeus, Willman-Bell, Inc., 1998.
'''

from mpmath import mpf, mpi, mpc, mp, ctx_iv
from rational import Rational
from integer import Zn
from time import localtime, strftime
from types import StringTypes
from debug import *
from mpformat import mpFormat, inf

try: from pdb import xx
except: pass

class Julian(object):
    '''Convert a date/time specification to a Julian day object
    represented by an mpmath mpf number.  A date is interpreted as the
    Julian calendar if it is on or before 4Oct1582 and the Gregorian
    calendar if the date is on or after 15Oct1582.  A date between
    those two dates is an error if be_strict is True.
    '''

    # The following class variable is used to offset the time from the
    # conventional astronomical Julian day, which is a pure integer
    # for noon of the day it represents.  This only affects the
    # displayed date/time, as the internal representation used is
    # always the astronomical Julian day.  Example:  if you want the
    # displayed date/time to represent the conventional day beginning
    # at midnight, set the offset to -12 hours, which needs to be
    # -0.5, as the units are (Julian) days.
    day_offset = mpf(0.0)

    # The following lowercase strings are used to identify the month and
    # translated it to an integer between 1 and 12 inclusive.  Hopefully,
    # I've isolated the routines well enough that you, the user, can modify
    # the code as needed to make things work with nearly any calendar.
    month_names = {
        "Jan" : 1, "Feb" : 2, "Mar" : 3, "Apr" : 4, "May" : 5, "Jun" : 6,
        "Jul" : 7, "Aug" : 8, "Sep" : 9, "Oct" : 10, "Nov" : 11, "Dec" : 12,
    }
    name_months = dict([[val, key] for key, val in month_names.items()])

    # This is a bit of a hack, but it is intended to allow the
    # calculator to communicate how Julian dates expressed as interval
    # numbers are supposed to be represented as strings.
    interval_representation = "a"

    # If be_strict is True, there are dates that are illegal and will
    # result in an exception.
    be_strict = False

    # ---------------------------------------------------------------
    # Class variables below here are private
    fp = mpFormat()

    def __init__(self, s="now"):
        '''Initialization can be done with numerous different objects.
        The basic need is for an mpf or mpi object that represents the
        standard astronomical Julian day.  mpi objects are allowed so
        as to model uncertainty in a date.

        string:
            "h:[m[:s]]"
                Hour, minute, second format that represents a time
                today.
            "dd.dd[m[y]]"
                dd.ddd is a real number representing the day number
                (integer part) and the time as a decimal fraction.
                m is a string representing the month; the number of
                characters are in the class variable month_name_size.
                y, if present, represents the year; if not present, the
                current year is taken; y must be an integer.
            "d[m[y]][:hh[:mm[:ss]]]"
                d is an integer between 1 and 31 representing the day.
                m is a string representing the month; the number of
                characters are in the class variable month_name_size.
                y, if present, represents the year; if not present, the
                current year is taken; y must be an integer.  hh and
                mm are the integer hour and minute and must be
                integers between 0 and 59. ss is a real number of
                seconds >= 0 and < 60.
            "today"
                Represents an integer that represents the current
                integral Julian date.
            "now"
                Represents the current Julian date that represents the
                current date and time.
            NOTE:  both "today" and "now" use the python time
            library's strftime and localtime functions to get the
            date/time information.
        integer:
            Is converted to an mpf.
        rational:
            Is converted to an mpf.
        mpf:
            Represents an astronomical Julian date and, by virtue of
            the decimal fractional part, a specific time on that date.
            A fractional part of 0 represents noon on the particular
            Julian date; the class variable Julian.day_offset is first
            subtracted from the number s to get the astronomical date
            and time.
        mpi:
            Same as an mpf, but allows the representation of a time
            interval.
        '''
        if isinstance(s, int) or \
           isinstance(s, long) or \
           isinstance(s, Zn):
            self.value = mpf(int(s))
        elif isinstance(s, Rational):
            self.value = mpf(s.n)/mpf(s.d)
        elif isinstance(s, mpf):
            self.value = s
        elif isinstance(s, ctx_iv.ivmpf):
            self.value = s
        elif isinstance(s, StringTypes):
            y, M, d, h, m, s = self._convert_string(s.strip())
            self.value = self._to_julian(y, M, d, h, m, s)
        else:
            raise ValueError("%sUnrecognized type for Julian day" % fln())

    def _convert_string(self, s):
        '''The forms we allow are 'today', 'now', or the following two:
        1.  d.d[m[y]] where m is a month name and y is an integer year.
        2.  d[m[y]][:h[:m[:s]]] where d is an integer, m is a month name,
            and y is an integer year.  h and m are integers for the hour
            and minutes and s can be a floating point string.
        3.  :h[:m[:s]] Note the first colon is mandatory.
        '''
        def form1(s):
            day, M, y = "", "", ""
            for month in Julian.month_names:
                if month.lower() in s:
                    M = Julian.month_names[month]
                    fields = s.split(month.lower())
                    if len(fields) == 1:
                        day = fields[0]
                        break
                    elif len(fields) == 2:
                        day, y = fields
                        break
                    else:
                        raise Exception("")
            if M == "" and y == "":
                y, M = [int(i) for i in strftime("%Y %m").split()]
            elif y == "":
                y = int(strftime("%Y"))
            if y:
                y = int(y)
            if day == "":
                day = s
            day = mpf(day)
            d = int(day)
            fractional_part = day - d
            h, m, s = self._to_hms(fractional_part)
            return self._check(y, M, d, h, m, s)
        def form2(date, time):
            y, M, d, h, m, s = form1(date)
            # Now parse the time
            h, m, s = 0, 0, 0
            try:
                fields = time.split(":")
                if len(fields) == 1:
                    # Hour only
                    h = int(fields[0])
                elif len(fields) == 2:
                    # Hour and minute
                    h = int(fields[0])
                    m = int(fields[1])
                elif len(fields) == 3:
                    # Hour, minute, and seconds
                    h = int(fields[0])
                    m = int(fields[1])
                    s = mpf(fields[2])
                else:
                    raise SyntaxError("")
            except:
                raise ValueError("'%s' is a bad h:m:s specification" % time)
            msg = ""
            if not (0 <= h < 24): msg = "Bad hour specification"
            if not (0 <= m < 60): msg = "Bad minute specification"
            if not (0 <= s < 60): msg = "Bad second specification"
            if msg:
                raise ValueError("%s" % fln() + msg)
            return self._check(y, M, d, h, m, s)
        def form3(st):
            assert st[0] == ":" and len(st) > 1
            d, M, y, h, m, s = [int(i) for i in
                strftime("%d %m %Y %H %M %S", localtime()).split()]
            h, m, s = 0, 0, 0
            fields = [i for i in st[1:].split(":") if i]
            if not (1 <= len(fields) <= 3):
                raise ValueError("%s'%s' is a bad time specification" % (fln(), st))
            if len(fields) == 1:
                h = int(fields[0])
            elif len(fields) == 2:
                h, m = [int(i) for i in fields]
            elif len(fields) == 3:
                h, m = [int(i) for i in fields[:2]]
                s = mpf(fields[2])
            return self._check(y, M, d, h, m, s)
        s = s.lower()
        if s == "today" or s == "now":
            return self._convert_now(s)
        loc = s.find(":")
        try:
            if loc != -1:
                if loc == 0:
                    y, M, d, h, m, s = form3(s)
                else:
                    date = s[:loc]
                    time = s[loc+1:]
                    y, M, d, h, m, s = form2(date, time)
            else:
                y, M, d, h, m, s = form1(s)
            return y, M, d, h, m, s
        except ValueError:
            raise
        except:
            raise ValueError("%sCould not convert '%s'" % (fln(), s))

    def _convert_now(self, now):
        d, M, y, h, m, s = [int(i) for i in
            strftime("%d %m %Y %H %M %S", localtime()).split()]
        if now == "today":
            return y, M, d, 0, 0, mpf("0")
        elif now == "now":
            return y, M, d, h, m, mpf(s)
        else:
            raise Exception("%sProgram bug:  bad string" % fln())

    def _to_hms(self, fractional_part_of_day):
        'Return hours, minutes, seconds'
        assert 0 <= fractional_part_of_day < 1
        if 0: # Old method
            second = 24*3600*fractional_part_of_day
            fractional_seconds = second - int(second)
            second = int(second)
            minute, second = divmod(second, 60)
            hour, minute = divmod(minute, 60)
            second += fractional_seconds
        else: # New method.  See comments in _to_date()
            hours = mpf("24")*fractional_part_of_day
            # Round this value to the nearest microhour
            onemillion = mpf("1e6")
            hours += mpf("5e-6")
            hours *= onemillion
            hours = int(hours)/onemillion
            h = int(hours)
            minutes = mpf("60")*(hours - h)
            m = int(minutes)
            s = mpf("60")*(minutes - m)
            # We'll truncate to the nearest tenth of a second
            s = int(10*s)/mpf("10")
        msg = ""
        if not (0 <= s < 60):
            msg = "Program bug in calculation of seconds"
        if not (0 <= m < 60):
            msg = "Program bug in calculation of minutes"
        if not (0 <= h < 24):
            msg = "Program bug in calculation of hours"
        if msg:
            raise ValueError("%s" % fln() + msg)
        return h, m, s

    def _check(self, year, month, day, hour, minute, second):
        '''Check the arguments and return them all as integers, except
        for seconds.
        '''
        try:
            msg = ""
            if int(year) != year: msg = "Year needs to be an integer"
            if int(month) != month: msg = "Month needs to be an integer"
            if int(month) < 1 or int(month) > 12: msg = "Bad month"

            # If day is an mpf, then we must have the time being 0
            if isinstance(day, mpf):
                if hour != 0 or minute != 0 or second != 0:
                    msg = "hr, min, sec must be 0 if day is real number"
                fractional_part = day - int(day)
                day = int(day)
                hour, minute, second = self._to_hms(fractional_part)
            else:
                if int(day) != day: msg = "Day needs to be an integer"
            if int(hour) != hour: msg = "Hour needs to be an integer"
            if int(minute) != minute: msg = "Minute needs to be an integer"
            if not isinstance(second, int) and \
               not isinstance(second, long) and \
               not isinstance(second, Zn) and \
               not isinstance(second, mpf):
                msg = "Second not of proper type"
            M, d, h, m = [int(i) for i in (month, day, hour, minute)]
            biggest_day = self._days_in_month(M, year)
            if d < 1 or d > biggest_day: msg = "Bad day"
            if h < 0 or h > 23: msg = "Bad hour"
            if m < 0 or m > 59: msg = "Bad minute"
            if second < 0 or second >= 60: msg = "Bad second"
            if year == 1582 and month == 10:
                if d > 4 and d < 15:
                    if Julian.be_strict:
                        msg = "Illegal date for Gregorian and Julian calendars"
                    else:
                        # Set to one or the other
                        if d <= 9: d = 4
                        else: d = 15
            if msg:
                raise ValueError("%s" % fln() + msg)
            return year, M, d, h, m, mpf(second)
        except ValueError:
            raise
        except:
            raise Exception("%sBad date/time" % fln())

    def _to_julian(self, year, month, day, hour=0, minute=0, second=0):
        'Algorithm is on page 61 of Meeus'
        Y, M, D, h, m, s = self._check(year, month, day, hour, minute, second)
        # Add the time to D; D will become a real number
        D += (mpf(h) + mpf(m)/mpf(60) + mpf(s)/mpf(3600))/mpf(24)
        if M == 1 or M == 2:
            Y -= 1
            M += 12
        A = Y//100
        B = 2 - A + A//4
        if Y <= 1582:
            # Set B = 0 if we're in the Julian calendar
            if Y == 1582:
                if M < 10 or (M == 10 and D < 5):
                    B = 0
            else:
                B = 0
        jd = int(mpf("365.25")*(Y + 4716)) + int(mpf(30.6001)*(M + 1)) + \
             D + B - mpf("1524.5")
        return jd

    def _is_leap_year(self, y):
        '''Rule is on page 62 of Meeus.  In the Julian calendar, a
        year is a leap year if it is divisible by 4.
        '''
        if not (isinstance(y, int) or isinstance(y, long) or isinstance(y, Zn)):
            raise ValueError("%sYear must be an integer" % fln())
        if y <= 1582:
            return (y % 4 == 0)
        else:
            # For Gregorian calendar
            if (y % 400 == 0) or ((y % 4 == 0) and (y % 100 != 0)):
                return True
            return False

    def _days_in_month(self, month, year):
        '''Assumes month and year are integers.
        '''
        if month == 2:
            if self._is_leap_year(year): return 29
            else: return 28
        elif month in (4, 6, 9, 11): return 30
        elif month in (1, 3, 5, 7, 8, 10, 12): return 31
        else: raise ValueError("%sBad month" % fln())

    def _to_date(self, jd):
        'Algorithm on page 63 of Meeus.'
        if not isinstance(jd, mpf):
            raise ValueError("%sJulian day must be a real number" % fln())
        if jd < 0:
            raise ValueError("%sJulian day cannot be negative" % fln())
        jd += mpf("0.5")
        Z = int(jd)
        F = jd - Z
        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - mpf("1867216.25"))/mpf("36524.25"))
            A = Z + 1 + alpha - alpha//4
        B = A + 1524
        C = int((B - mpf("122.1"))/mpf("365.25"))
        D = int(mpf("365.25")*C)
        E = int((B - D)/mpf("30.6001"))
        D = B - D - int(mpf("30.6001")*E) + F
        if E < 14:
            M = E - 1
        else:
            M = E - 13
        if M > 2:
            y = C - 4716
        else:
            y = C - 4715
        d = int(D)
        fractional_part = D - d
        # Note:  a test case of ":22" for jd = 2454871.4166666665
        # showed a problem with roundoff, in that the decimal hours
        # calculate to 21.99999 99960 to 10 places.  This value
        # results in the following tuple being returned:
        # (2009, 2, 8, 21, 59, mpf('59.999986588954926')).  Because of
        # this test case, I decided to round hours to the nearest
        # microhour by adding 5e-7, etc. in _to_hms().
        h, m, s = self._to_hms(fractional_part)
        return y, M, d, h, m, s

    def _st(self, val):
        assert isinstance(val, mpf)
        Julian.fp.digits(1)  # We'll display to the nearest tenth second
        if val < 0:
            return "Julian(%s)" % Julian.fp.fix(val)
        y, M, d, h, m, s = self._to_date(val)
        try:
            t = "%d%s%d" % (d, Julian.name_months[M], y)
            t += ":%02d:%02d" % (h, m)
            if s != 0:
                t += ":" + Julian.fp.fix(s).strip()
            return t
        except:
            msg = "%sDate representation cannot be calculated\n" + \
                  "Try increasing the precision with `prec`."
            raise ValueError(msg % fln())

    def _units(self, val):
        '''Return a string representing val as a number of common time units.
        For example, if val == 1, this is 1 day, so '1 day' would be returned.
        '''
        y = mpf("365.25")
        w = mpf("7")
        mo = y/12
        s = mpf("86400")
        m = mpf("1440")
        h = mpf("24")
        Julian.fp.digits(3)
        f = Julian.fp.sig
        if 0 <= val <= 1/m:
            return f(s*val) + " seconds"
        elif 1/m < val <= 1/h:
            return f(m*val) + " minutes"
        elif 1/h < val <= 1:
            return f(h*val) + " hours"
        elif 1 < val <= w:
            return f(val)   + " days"
        elif w < val <= mo:
            return f(val/w) + " weeks"
        elif mo < val <= y:
            return f(val/mo) + " months"
        else:
            return f(val/y) + " years"

    def __str__(self):
        if self.value == inf: return "Julian(inf)"
        if self.value == -inf: return "Julian(-inf)"
        val = self.value - Julian.day_offset
        if isinstance(val, ctx_iv.ivmpf):
            if Julian.interval_representation == "a":
                a = self._st(val.mid)
                b = self._units(val.delta/mpf("2"))
                return a + " +-" + b
            elif Julian.interval_representation == "b":
                a = self._st(val.mid)
                p = mpf("100")*val.delta/(mpf("2")*val.mid)
                Julian.fp.digits(3)
                b = Julian.fp.sig(p).strip()
                return a + " (" + b + "%)"
            elif Julian.interval_representation == "c":
                s = " <<" + self._st(val.a) + ", " + \
                     self._st(val.b) + ">>"
                return s
            else:
                raise Exception("%sBad Julian.interval_representation" % fln())
        else:
            return " " + self._st(val)

    def __repr__(self):
        return "Julian(" + repr(self.value) + ")"

    def _convert_to_mpf_or_mpi(self, n):
        if isinstance(n, int) or isinstance(n, long) or isinstance(n, Zn):
            return mpf(n)
        elif isinstance(n, Rational):
            return n.mpf()
        elif isinstance(n, mpc):
            return abs(n)
        elif isinstance(n, mpf) or isinstance(n, ctx_iv.ivmpf):
            return n
        elif isinstance(n, Julian):
            return n.value
        else:
            raise ValueError("%sBad type for operation with date/time" % fln())

    def __add__(self, other):
        return Julian(self.value + self._convert_to_mpf_or_mpi(other))
    def __sub__(self, other):
        return Julian(self.value - self._convert_to_mpf_or_mpi(other))
    def __mul__(self, other):
        return Julian(self.value * self._convert_to_mpf_or_mpi(other))
    def __div__(self, other):
        return Julian(self.value / self._convert_to_mpf_or_mpi(other))

    def __radd__(self, other):
        return Julian(self._convert_to_mpf_or_mpi(other) + self.value)
    def __rsub__(self, other):
        return Julian(self._convert_to_mpf_or_mpi(other) - self.value)
    def __rmul__(self, other):
        return Julian(self._convert_to_mpf_or_mpi(other) * self.value)
    def __rdiv__(self, other):
        raise Exception("%sMeaningless to divide by date/time" % fln())

    def __int__(self):
        if isinstance(self.value, mpf):
            return int(self.value)
        elif isinstance(self.value, ctx_iv.ivmpf):
            return int(self.value.mid)
        else:
            raise Exception("%sProgram bug:  unknown type" % fln())

    __long__ = __int__

    def to_mpf(self):
        if isinstance(self.value, mpf):
            return self.value
        elif isinstance(self.value, ctx_iv.ivmpf):
            return self.value.mid
        else:
            raise Exception("%sProgram bug:  unknown type" % fln())

if __name__ == "__main__":
    def TestNumericalInit():
        j = Julian(0)
        data = (
            # Test vectors from Meeus pg 62
            ( 1957, 10,           4, 19, 26, 24, mpf("2436116.31")),
            (  333,  1,          27, 12,  0,  0, mpf("1842713.0")),
            ( 2000,  1,  mpf("1.5"),  0,  0,  0, mpf("2451545.0")),
            ( 1999,  1,  mpf("1.0"),  0,  0,  0, mpf("2451179.5")),
            ( 1988,  6, mpf("19.5"),  0,  0,  0, mpf("2447332.0")),
            ( 1600,  1,  mpf("1.0"),  0,  0,  0, mpf("2305447.5")),
            ( 1600, 12, mpf("31.0"),  0,  0,  0, mpf("2305812.5")),
            (-123,  12, mpf("31.0"),  0,  0,  0, mpf("1676496.5")),
            (-122,   1,  mpf("1.0"),  0,  0,  0, mpf("1676497.5")),
            (-1000,  2, mpf("29.0"),  0,  0,  0, mpf("1355866.5")),
            (-4712,  1,  mpf("1.5"),  0,  0,  0, mpf("0.0")),
        )
        for item in data:
            y, M, d, h, m, s, jd = item
            assert j._to_julian(y, M, d, h, m, s) == jd
            y1, M1, d1, h1, m1, s1 = j._to_date(jd)
            if isinstance(d, mpf):
                D = d1 + (mpf(h1) + mpf(m1)/60 + mpf(s1)/3600)/mpf(24)
                assert (y, M, d) == (y1, M1, D)
            else:
                # Note this comparison is just to the nearest second
                assert (y, M, d, h, m, s) == (y1, M1, d1, h1, m1, int(s1))
    def TestStringInit():
        data = (
            # Test points from Meeus pg 62
            ("4Oct1957:19:26:24", mpf("2436116.31")),
            ("27Jan333:12",       mpf("1842713.0")),
            ("1.5jan2000",        mpf("2451545.0")),
            ("1.0jan1999",        mpf("2451179.5")),
            ("19.5JUN1988",       mpf("2447332.0")),
            ("1.0jan1600",        mpf("2305447.5")),
            ("31.0Dec1600",       mpf("2305812.5")),
            ("31.0Dec-123",       mpf("1676496.5")),
            ("1.0jan-122",        mpf("1676497.5")),
            ("29Feb-1000",        mpf("1355866.5")),
            ("1.5Jan-4712",       mpf("0.0")),
        )
        for s, jd in data:
            assert Julian(s).value == jd
        # Test the :h:m:s forms
        Julian.day_offset = mpf("0")
        fields = str(Julian(":2")).split(":")
        assert fields[1] == "02"; assert fields[2] == "00"
        fields = str(Julian(":22")).split(":")
        assert fields[1] == "22"; assert fields[2] == "00"
        fields = str(Julian(":22:45")).split(":")
        assert fields[1] == "22"; assert fields[2] == "45"
        fields = str(Julian(":22:45:12.3")).split(":")
        assert fields[1] == "22"; assert fields[2] == "45"
        assert fields[3] == "12.3"
    def TestStringRepresentations():
        # Test string representations (note leading spaces)
        Julian.day_offset = mpf("0")
        Julian.interval_representation = "c"
        j1, j2 = mpf("2451545.0"), mpf("2451545.5")
        assert str(Julian(j1)) == " 1Jan2000:12:00"
        assert str(Julian(mpi(j1, j2))) == " <<1Jan2000:12:00, 2Jan2000:00:00>>"
        Julian.day_offset = mpf("0.5")
        assert str(Julian(j1)) == " 1Jan2000:00:00"
        assert str(Julian(mpi(j1, j2))) == " <<1Jan2000:00:00, 1Jan2000:12:00>>"
    def TestArithmetic():
        Julian.day_offset = mpf("0")
        j = mpf("2451545.0")
        assert str(Julian(j)) == " 1Jan2000:12:00"
        assert str(Julian(j) + mpf("1")) == " 2Jan2000:12:00"
        assert str(Julian(j) - mpf("1")) == " 31Dec1999:12:00"
        assert str(Julian(j)*2) == " 8Feb8712:12:00"
        assert str(Julian(j)/2) == " 26Dec-1357:00:00"
        assert str(mpf("1") + Julian(j)) == " 2Jan2000:12:00"
        assert str(mpf("0") - Julian(-j)) == " 1Jan2000:12:00"
        assert str(2*Julian(j)) == " 8Feb8712:12:00"
    TestNumericalInit()
    TestStringInit()
    TestStringRepresentations()
    TestArithmetic()
#yy
