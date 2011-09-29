'''
$Id: cmddecod.py 1.8 2009/02/09 17:01:58 donp Exp $

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

class CommandDecodeError(Exception): pass

class CommandDecode:
    '''This class can be used to identify that a command is from a set
    of commands.  The class will try to complete the command if a
    whole command is not typed in.  Run this file as a script to
    get an interactive demo.

    Here's an example of its use.  cmd_dict is a dictionary of all
    the commands you want recognized (the commands are the keys).

    # We'll initialize so that the command's case is ignored
    ignore_case = 1
    id_cmd = CommandDecode(cmd_dict, ignore_case)
    while not finished:
        user_string = GetUserString()
        command = id_cmd.identify_cmd(user_string)
        # command is a list containing 0 elements (no command
        # matched), one element (unique match), or multiple elements
        # (non-unique match.
        if not command:
            print "\"%s\" not recognized" % user_string
        elif len(command) == 1:
            print "\"%s\" is unique command '%s'" % (user_string, command[0])
            finished = ExecuteCommand(command[0])
        else:
            print "\"%s\" is ambiguous" % user_string
            print "It matched the following commands:"
            for cmd in command:
                print "  ", cmd

    This shows that the identify_cmd() method will return None if the
    user's string is not recognized, a single string if it is recognized
    as a unique command, and a list if it matched more than one possible
    command.
    '''
    def __init__(self, commands, ignore_case = 0):
        import string
        self.ignore_case = ignore_case
        self.commands    = commands
        if len(commands) < 1:
            raise CommandDecodeError("dictionary must have > 0 elements")
        if type(commands) != type({}):
            raise CommandDecodeError("must pass in dictionary")
        # Build index dictionary; each key is the first letter of the
        # command and each element is a list of commands that have that
        # first letter.
        self.index = {}
        for cmd in self.commands.keys():
            first_char = cmd[0]
            if self.ignore_case:
                first_char = string.lower(first_char)
            if first_char not in self.index.keys():
                self.index[first_char] = []
            self.index[first_char].append(cmd)
        self.first_char_list = self.index.keys()
    def identify_cmd(self, user_string):
        import re, string
        if type(user_string) != type(""):
            raise CommandDecodeError("must pass in a string")
        st = string.strip(user_string)
        if len(st) < 1:
            return None
        if self.ignore_case:
            st = string.lower(st)
        if self.commands.has_key(st):
            return user_string
        first_char = st[0]
        if first_char not in self.first_char_list:
            return None
        possible_commands = self.index[first_char]
        try:
            if self.ignore_case:
                regexp = re.compile("^" + st, re.I)
            else:
                regexp = re.compile("^" + st)
        except:
            return None
        matches = []
        for cmd in possible_commands:
            if regexp.match(cmd):
                matches.append(cmd)
        if len(matches) == 0:
            return None
        if len(matches) == 1:
            return matches[0]
        return matches

if __name__ == "__main__":
    # Test the class; use some typical UNIX program names.
    d = { "ar" : "", "awk" : "", "banner" : "", "basename" : "", "bc" : "",
          "cal" : "", "cat" : "", "cc" : "", "chmod" : "", "cksum" : "",
          "clear" : "", "cmp" : "", "compress" : "", "cp" : "", "cpio" : "",
          "crypt" : "", "ctags" : "", "cut" : "", "date" : "", "dc" : "",
          "dd" : "", "df" : "", "diff" : "", "dirname" : "", "du" : "",
          "echo" : "", "ed" : "", "egrep" : "", "env" : "", "ex" : "",
          "expand" : "", "expr" : "", "false" : "", "fgrep" : "", "file" : "",
          "find" : "", "fmt" : "", "fold" : "", "getopt" : "", "grep" : "",
          "gzip" : "", "head" : "", "id" : "", "join" : "", "kill" : "",
          "ksh" : "", "ln" : "", "logname" : "", "ls" : "", "m4" : "",
          "mailx" : "", "make" : "", "man" : "", "mkdir" : "", "more" : "",
          "mt" : "", "mv" : "", "nl" : "", "nm" : "", "od" : "", "paste" : "",
          "patch" : "", "perl" : "", "pg" : "", "pr" : "", "printf" : "",
          "ps" : "", "pwd" : "", "rev" : "", "rm" : "", "rmdir" : "",
          "rsh" : "", "sed" : "", "sh" : "", "sleep" : "", "sort" : "",
          "spell" : "", "split" : "", "strings" : "", "strip" : "",
          "stty" : "", "sum" : "", "sync" : "", "tail" : "", "tar" : "",
          "tee" : "", "test" : "", "touch" : "", "tr" : "", "true" : "",
          "tsort" : "", "tty" : "", "uname" : "", "uncompress" : "",
          "unexpand" : "", "uniq" : "", "uudecode" : "", "uuencode" : "",
          "vi" : "", "wc" : "", "which" : "", "who" : "", "xargs" : "",
          "zcat" : "",
          "Y" : ""
        }

    ignore_case = 1
    c = CommandDecode(d, ignore_case)
    print "Enter some commands, 'q' to quit:"
    cmd = raw_input()
    while cmd != "q":
        x = c.identify_cmd(cmd)
        if not x:
            print "'%s' unrecognized" % cmd
        elif isinstance(x, type("")):
            print "'%s' was an exact match to '%s'" % (cmd, x)
        else:
            x.sort()
            print "'%s' is ambiguous:  %s" % (cmd, `x`)
        cmd = raw_input()

