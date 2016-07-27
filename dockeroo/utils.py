
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


from collections import defaultdict
from datetime import datetime, timedelta, tzinfo
import logging
import random
import re
import string

from builtins import range # pylint: disable=redefined-builtin
from builtins import object # pylint: disable=redefined-builtin
from decorator import decorate
from past.builtins import basestring # pylint: disable=redefined-builtin
from zc.buildout import UserError


TRUE_SET = {'true', 'on', 'yes', '1'}
FALSE_SET = {'false', 'off', 'no', '0'}


class ExternalProcessError(RuntimeError):

    def __init__(self, msg, process):
        full_msg = "{} ({})".format(msg, process.returncode)
        err = ' '.join(process.stderr.read().splitlines())
        if err:
            full_msg = "{}: {}".format(full_msg, err)
        super(ExternalProcessError, self).__init__(full_msg)


class FixedOffset(tzinfo):

    def __init__(self, offset=None, name=None):
        super(FixedOffset, self).__init__()
        if offset is not None:
            self.__offset = timedelta(minutes=offset)
        if name is not None:
            self.__name = name

    def utcoffset(self, dt): # pylint: disable=unused-argument
        return self.__offset

    def tzname(self, dt): # pylint: disable=unused-argument
        return self.__name

    def dst(self, dt): # pylint: disable=unused-argument
        return timedelta(0)

    @classmethod
    def fixed_timezone(cls, offset):
        if isinstance(offset, timedelta):
            offset = offset.seconds // 60
        sign = '-' if offset < 0 else '+'
        hhmm = '%02d:%02d' % divmod(abs(offset), 60)
        name = sign + hhmm
        return cls(offset, name)

class NonExistentOption(object): # pylint: disable=too-few-public-methods
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
        for key in self.repository.group_keys[self.group]:
            yield key

    def get(self, key, default=None):
        return self.repository.options.get(self._key(key), default)

    def get_as_bool(self, key, default=None):
        return string_as_bool(self.get(key, default))

    def has(self, key):
        return bool(self._key(key) in self.repository.options)

    def set(self, key, value):
        self.repository.options[self._key(key)] = value
        self.repository.group_keys[self.group].add(key)

    def setdefault(self, key, value):
        self.repository.options.setdefault(self._key(key), value)
        self.repository.group_keys[self.group].add(key)

    def delete(self, key):
        del self.repository.options[self._key(key)]
        self.repository.group_keys[self.group].discard(key)
        if not self.repository.group_keys[self.group]:
            del self.repository.group_keys[self.group]

    def copy(self):
        return dict([(k, self[k]) for k in self])

class OptionRepository(object):
    def __init__(self, options):
        self.options = options
        self.groups = dict()
        self.group_keys = defaultdict(set)
        for option in self.options.keys():
            split = option.split('_', 1)
            if len(split) > 1:
                self.group_keys[split[0]].add(split[1])
            else:
                self.group_keys[None].add(split[0])

    def __iter__(self):
        return iter(self.group_keys)

    def __getitem__(self, group):
        if group in self.group_keys:
            if group not in self.groups:
                self.groups[group] = OptionGroup(self, group)
            return self.groups[group]
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

def merge(lst1, lst2):
    def _merge(lst1, lst2):
        for i in range(max(len(lst1), len(lst2))):
            if i < len(lst2):
                yield lst2[i]
            else:
                yield lst1[i]
    return list(_merge(lst1, lst2))

def random_name(size=8):
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + \
                                                string.digits) for _ in range(size))

def quote(strobj):
    return '"{}"'.format(strobj.replace('"', '\\"'))

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

DATETIME_RE = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r' ?(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?'
)

def parse_datetime(value):
    match = DATETIME_RE.match(value)
    if match:
        kwargs = match.groupdict()
        if kwargs['microsecond']:
            kwargs['microsecond'] = kwargs['microsecond'].ljust(6, '0')
        tzobj = kwargs.pop('tzinfo')
        if tzobj == 'Z':
            tzobj = FixedOffset.fixed_timezone(0)
        elif tzobj is not None:
            offset_mins = int(tzobj[-2:]) if len(tzobj) > 3 else 0
            offset = 60 * int(tzobj[1:3]) + offset_mins
            if tzobj[0] == '-':
                offset = -offset
            tzobj = FixedOffset.fixed_timezone(offset)
        kwargs = {k: int(v) for k, v in kwargs.items() if v is not None}
        kwargs['tzinfo'] = tzobj
        return datetime(**kwargs)

def reify(func):
    def _reify(func, *args, **kwargs):
        if not hasattr(func, '_cache'):
            setattr(func, '_cache', func(*args, **kwargs))
        return getattr(func, '_cache')
    return decorate(func, _reify)

def listify(func):
    def _listify(func, *args, **kwargs):
        return list(func(*args, **kwargs))
    return decorate(func, _listify)

def string_as_bool(obj):
    if not isinstance(obj, basestring):
        return bool(obj)
    obj = obj.strip().lower()
    if obj in TRUE_SET:
        return True
    elif obj in FALSE_SET:
        return False
    else:
        raise UserError('''Invalid string "{}", must be boolean'''.format(obj))

def uniq(seq):
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]
