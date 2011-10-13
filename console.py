import fcntl, termios, struct, os, sys

def size():
    def ioctl_GWINSZ(fd):
        try:
            wsz = fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234')
            cr = struct.unpack('hh', wsz)
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (env['LINES'], env['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])

def get_tty():
    return os.readlink("/proc/self/fd/0")

def set_title(tstring, showtty=True):
    if showtty:
        tty = "%s: " % get_tty()[5:]
    else:
        tty = ''
    sys.stdout.write("\x1b]2;%s%s\x07" % (tty, tstring))

