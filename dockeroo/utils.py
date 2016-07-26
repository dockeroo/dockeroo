
# -*- coding: utf-8 -*-
# 
# Copyright (c) 2016, Giacomo Cariello. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from builtins import range
from builtins import object

from collections import defaultdict
from decorator import decorate
from datetime import datetime, timedelta, tzinfo
import errno
from functools import update_wrapper
import logging
import os
import random
import re
import string


TRUE_SET = {'true', 'on', 'yes', '1'}
FALSE_SET = {'false', 'off', 'no', '0'}


class FixedOffset(tzinfo):

    def __init__(self, offset=None, name=None):
        if offset is not None:
            self.__offset = timedelta(minutes=offset)
        if name is not None:
            self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

    @classmethod
    def fixed_timezone(cls, offset):
        if isinstance(offset, timedelta):
            offset = offset.seconds // 60
        sign = '-' if offset < 0 else '+'
        hhmm = '%02d:%02d' % divmod(abs(offset), 60)
        name = sign + hhmm
        return cls(offset, name)

class NonExistentOption(object):
    pass

class OptionGroup(object):
    def __init__(self, repository, group):
        self.repository = repository
        self.group = group

    def _key(self, key):
        return "{}_{}".format(self.group, key) if self.group is not None else key

    def __getitem__(self, key):
        ret = self.get(key, NonExistentOption)
        if ret is NonExistentOption:
            raise KeyError
        return ret

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.delete(key)

    def __iter__(self):
        for key in self.repository._group_keys[self.group]:
            yield key

    def get(self, key, default=None):
        return self.repository.options.get(self._key(key), default)

    def get_as_bool(self, key, default=None):
        return string_as_bool(self.get(key, default))

    def has(self, key):
        return bool(self._key(key) in self.repository.options)

    def set(self, key, value):
        self.repository.options[self._key(key)] = value
        self.repository._group_keys[self.group].add(key)

    def setdefault(self, key, value):
        self.repository.options.setdefault(self._key(key), value)
        self.repository._group_keys[self.group].add(key)

    def delete(self, key):
        del self.repository.options[self._key(key)]
        self.repository._group_keys[self.group].discard(key)
        if not self.repository._group_keys[self.group]:
            del self.repository._group_keys[self.group]

    def copy(self):
        return dict([(k, self[k]) for k in self])

class OptionRepository(object):
    def __init__(self, options):
        self.options = options
        self._groups = dict()
        self._group_keys = defaultdict(set)
        for option in self.options.keys():
            split = option.split('_', 1)
            if len(split) > 1:
                self._group_keys[split[0]].add(split[1])
            else:
                self._group_keys[None].add(split[0])

    def __iter__(self):
        return iter(self._group_keys)

    def __getitem__(self, group):
        if group in self._group_keys:
            if group not in self._groups:
                self._groups[group] = OptionGroup(self, group)
            return self._groups[group]
        else:
            raise KeyError

    def get(self, key, default=None):
        return self[None].get(key, default)

    def get_as_bool(self, key, default=None):
        return self[None].get_as_bool(key, default)

    def set(self, key, value):
        return self[None].set(key, value)

    def setdefault(self, key, value):
        return self[None].setdefault(key, value)

    def delete(self, key):
        return self[None].delete(key)

def merge(a, b):
    def merge(a, b):
        for i in range(max(len(a), len(b))):
            if i < len(b):
                yield b[i]
            else:
                yield a[i]
    return list(merge(a, b))

def random_name(self, size=8):
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(size))

def quote(s):
    return '"{}"'.format(s.replace('"', '\\"'))

def resolve_loglevel(level):
    if not level:
        return None
    if level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        return getattr(logging, level)
    else:
        try:
            return int(level)
        except ValueError:
            raise UserError('''Invalid log level "{}"'''.format(level))

def resolve_verbosity(verbosity):
    try:
        return int(verbosity)
    except ValueError:
        raise UserError('''Invalid verbosity "{}"'''.format(verbosity))

datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r' ?(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?'
)

def parse_datetime(value):
    match = datetime_re.match(value)
    if match:
        kw = match.groupdict()
        if kw['microsecond']:
            kw['microsecond'] = kw['microsecond'].ljust(6, '0')
        tzinfo = kw.pop('tzinfo')
        if tzinfo == 'Z':
            tzinfo = utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = FixedOffset.fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime(**kw)

def reify(f):
    def _reify(f, *args, **kwargs):
        if not hasattr(f, '_cache'):
            setattr(f, '_cache', f(*args, **kwargs))
        return f._cache
    return decorate(f, _reify)

def string_as_bool(s):
        if not isinstance(s, basestring):
            return bool(s)
        s = s.strip().lower()
        if s in TRUE_SET:
            return True
        elif s in FALSE_SET:
            return False
        else:
            raise UserError('''Invalid string "{}", must be boolean'''.format(s))

def uniq(seq):
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

