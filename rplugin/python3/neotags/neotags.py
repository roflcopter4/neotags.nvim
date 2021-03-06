#!/usr/bin/env pypy3
# ============================================================================
# File:        neotags.py
# Author:      Christian Persson <c0r73x@gmail.com>
# Repository:  https://github.com/c0r73x/neotags.nvim
#              Released under the MIT license
# ============================================================================
# NOTE: Psutil import moved to Neotags._kill() to allow the script to run
# without the module (and therefore essentially without the kill function,
# beggers can't be choosers). Psutil is not and will never be available on
# cygwin, which makes this plugin unusable there without this change.
import gzip
import hashlib
# import mmap
import os
import re
import subprocess
import time
from sys import platform
from neovim.api.nvim import NvimError
from tempfile import mkstemp

SUFFIX = '.gz'


class Neotags(object):

    def __init__(self, vim):
        self.__vim = vim
        self.__prefix = '\C\<'
        self.__suffix = '\>'
        self.__current_file = ''
        self.__initialized = False
        self.__is_running = False

        self.__groups = {}
        self.__cmd_cache = {}
        self.__md5_cache = {}
        self.__tmp_cache = {}

        self.__ignore = []
        self.__ignored_tags = []
        self.__notin = []
        self.__seen = []
        self.__start_time = []
        self.__backup = []

        self.__directory = None
        self.__find_tool = None
        self.__neotags_bin = None
        self.__noRecurseDirs = None
        self.__settingsFile = None
        self.__slurp = None
        self.__tagfile = None

        self.__globtime = time.time()
        self.__hlbuf = 1

    def __void(self, *args):
        return

    def init(self):
        if (self.__initialized):
            return
        self.__backup = [self._debug_echo, self._debug_start, self._debug_end]

        if (not self.__vim.vars['neotags_verbose']):
            self._debug_start = self.__void
            self._debug_echo = self.__void
            self._debug_end = self.__void

        self.__notin = self.__vim.vars['neotags_global_notin']
        self.__ignore = self.__vim.vars['neotags_ignore']
        self.__current_file = self.__vim.api.eval("expand('%:p:p')")
        self.__to_escape = re.compile(r'[.*^$/\\~\[\]]')

        self.__ctov = self.__vim.vars['neotags_ft_conv']
        self.__vtoc = {y: x for x, y in self.__ctov.items()}

        # self.__match_pattern = r'syntax match %s /%s\%%(%s\)%s/ containedin=ALLBUT,%s'
        self.__match_pattern = r'syntax match %s /%s\%%(%s\)%s/'
        # self.__keyword_pattern = r'syntax keyword %s %s containedin=ALLBUT,%s'
        self.__keyword_pattern = r'syntax keyword %s %s'
        self.__exists_buffer = {}
        self.__regex_buffer = {}

        self.__directory = self.__vim.vars['neotags_directory']
        self.__find_tool = self.__vim.vars['neotags_find_tool']
        self.__ignored_tags = self.__vim.vars['neotags_ignored_tags']
        self.__noRecurseDirs = self.__vim.vars['neotags_norecurse_dirs']
        self.__settingsFile = self.__vim.vars['neotags_settings_file']

        self.__neotags_bin = self._get_binary()

        if (self.__vim.vars['neotags_enabled']):
            evupd = ','.join(self.__vim.vars['neotags_events_update'])
            evhl = ','.join(self.__vim.vars['neotags_events_highlight'])
            evre = ','.join(self.__vim.vars['neotags_events_rehighlight'])

            self.__patternlength = self.__vim.vars['neotags_patternlength']

            self.__vim.command(
                'autocmd %s * call NeotagsUpdate()' % evupd,
                async=True
            )
            self.__vim.command(
                'autocmd %s * call NeotagsHighlight()' % evhl,
                async=True
            )
            self.__vim.command(
                'autocmd %s * call NeotagsRehighlight()' % evre,
                async=True
            )

            if (self.__vim.vars['loaded_neotags']):
                self.highlight(False)

        self.__initialized = True

    def toggle(self):
        """Toggle state of the plugin."""
        if (not self.__vim.vars['neotags_enabled']):
            self.__vim.vars['neotags_enabled'] = 1
            self._inform_echo("Re-enabling neotags.")
            self.update(force=True)
        else:
            self.__vim.vars['neotags_enabled'] = 0
            self._inform_echo("Disabling neotags.")
            self.__seen = []
            self.__md5_cache = {}
            self.__cmd_cache = {}
            self.update()

    def toggle_C_bin(self):
        if self.__neotags_bin is None:
            self.__neotags_bin = self._get_binary(loud=True)
            if self.__neotags_bin is not None:
                self._inform_echo("Switching to use C binary.")
        else:
            self.__neotags_bin = None
            self.__vim.vars['neotags_use_binary'] = 0
            self._inform_echo("Switching to use python code.")

    def toggle_verbosity(self):
        if self._debug_echo == self.__void:
            self._inform_echo('Switching to verbose output.')
            self._debug_echo = self.__backup[0]
            self._debug_start = self.__backup[1]
            self._debug_end = self.__backup[2]
            self.__vim.vars['neotags_verbose'] = 1
        else:
            self._inform_echo('Switching off verbose output.')
            self._debug_start = self._debug_echo = self._debug_end = self.__void
            self.__vim.vars['neotags_verbose'] = 0

    def update(self, force=False):
        """Update tags file, tags cache, and highlighting."""
        ft = self.__vim.api.eval('&ft')
        if (not self.__vim.vars['neotags_enabled']):
            self._debug_echo('Update called when plugin disabled...', False)
            self._clear(ft)
            return

        if (ft == '' or ft in self.__ignore):
            return

        if (self.__is_running):
            return
        self.__is_running = True

        self._update(ft)

        self.__is_running = False
        self.highlight(False)

    def highlight(self, clear):
        """Analyze the tags data and format it for nvim's regex engine."""
        self.__globtime = time.time()
        self.__exists_buffer = {}
        ft = self.__vim.api.eval('&ft')
        force = clear

        if (clear):
            self._clear(ft)
        if (not self.__vim.vars['neotags_enabled']):
            self._clear(ft)
            return
        if (not self.__vim.vars['neotags_highlight']):
            self._clear(ft)
            return

        if (ft == '' or ft in self.__ignore):
            return

        if (self.__is_running):
            return
        self.__is_running = True

        self._debug_start()
        file = self.__vim.api.eval("expand('%:p:p')")

        if self.__vim.current.buffer.number not in self.__seen \
                or ft not in self.__groups or force:
            self._debug_echo("Forcing an update!")
            self._update(ft)
            force = True

        order = self._tags_order(ft)
        groups = self.__groups[ft]

        if groups is None:
            self._debug_echo("Skipping file", False)
            self.__is_running = False
            return

        if not order:
            order = groups.keys()

        for key in order:
            hlgroup = self._exists(key, '.group', None)
            fgroup = self._exists(key, '.filter.group', None)

            if hlgroup is not None and key in groups:
                prefix = self._exists(key, '.prefix', self.__prefix)
                suffix = self._exists(key, '.suffix', self.__suffix)
                notin = self._exists(key, '.notin', [])

                if not self._highlight(key, file, ft, hlgroup, groups[key],
                                       prefix, suffix, notin, force):
                    break

                # self._debug_echo('applied syntax for %s' % key)

            fkey = key + '_filter'
            if fgroup is not None and fkey in groups:
                prefix = self._exists(key, '.filter.prefix', self.__prefix)
                suffix = self._exists(key, '.filter.suffix', self.__suffix)
                notin = self._exists(key, '.filter.notin', [])

                if not self._highlight(fkey, file, ft, fgroup, groups[fkey],
                                       prefix, suffix, notin, force):
                    break

                # self._debug_echo('applied syntax for %s' % fkey)

        self._debug_end('applied syntax for %s' % ft)

        self.__hlbuf = self.__vim.current.buffer.number

        self.__current_file = file
        self.__is_running = False

##############################################################################
    # Projects

    def setBase(self, args):
        try:
            with open(self.__settingsFile, 'r') as fp:
                projects = [i.rstrip for i in fp]
        except FileNotFoundError:
            projects = []

        with open(self.__settingsFile, 'a') as fp:
            for arg in args:
                path = os.path.realpath(arg)
                if os.path.exists(path):
                    if path not in projects:
                        fp.write(path + '\n')
                        self._inform_echo("Saved directory '%s' as a project"
                                          " base." % path)
                    else:
                        self._inform_echo("Error: directory '%s' does not"
                                          " exist." % path)
                else:
                    self._inform_echo("Error: directory '%s' is already saved"
                                      " as a project base." % path)

    def removeBase(self, args):
        try:
            with open(self.__settingsFile, 'r') as fp:
                projects = [i.rstrip() for i in fp]
        except FileNotFoundError:
            return
        path = os.path.realpath(args[0])

        if path in projects:
            projects.remove(path)
            self._inform_echo(
                "Removed directory '%s' from project list." % path
            )
            with open(self.__settingsFile, 'w') as fp:
                for path in projects:
                    fp.write(path + '\n')
        else:
            self._inform_echo("Error: directory '%s' is not a known project"
                              " base." % path)

##############################################################################
    # Private

    def _update(self, ft):
        self.__seen.append(self.__vim.current.buffer.number)
        self._run_ctags()
        self.__groups[ft] = self._parseTags(ft)

    def _highlight(self, key, file, ft, hlgroup, group, prefix, suffix, notin, force):
        self._debug_start()
        highlights, number = self._getbufferhl()

        self._debug_echo("Highlighting for buffer %s" % number)
        if number in self.__md5_cache:
            highlights = self.__md5_cache[number]
        else:
            self.__md5_cache[number] = highlights = {}

        current = []
        cmds = []
        hlkey = '_Neotags_%s_%s' % (key.replace('#', '_'), hlgroup)

        # self._debug_echo(str(group))

        md5 = hashlib.md5()
        strgrp = ''.join(group).encode('utf8')

        for i in range(0, len(strgrp), 128):
            md5.update(strgrp[i:i + 128])

        md5hash = md5.hexdigest()

        if not force  \
            and (hlkey in highlights and md5hash == highlights[hlkey]) \
            or (number != self.__hlbuf and number in self.__cmd_cache
                and hlkey in self.__cmd_cache[number]):
            try:
                cmds = self.__cmd_cache[number][hlkey]
            except KeyError:
                self._error('Key error in _highlight()!')
                return True
            self._debug_echo("Updating from cache" % cmds)
        else:
            cmds.append('silent! syntax clear %s' % hlkey)

            for i in range(0, len(group), self.__patternlength):
                current = group[i:i + self.__patternlength]

                if prefix == self.__prefix and suffix == self.__suffix:
                    cmds.append(self.__keyword_pattern %
                                (hlkey, ' '.join(current)))
                else:
                    cmds.append(self.__match_pattern %
                                (hlkey, prefix, '\|'.join(current), suffix))

                # if prefix == self.__prefix and suffix == self.__suffix:
                #     cmds.append(self.__keyword_pattern % (
                #         hlkey,
                #         ' '.join(current),
                #         ','.join(self.__notin + notin)
                #     ))
                # else:
                #     cmds.append(self.__match_pattern % (
                #         hlkey,
                #         prefix,
                #         '\|'.join(current),
                #         suffix,
                #         ','.join(self.__notin + notin)
                #     ))

            if ft != self.__vim.api.eval('&ft'):
                self._debug_end('filetype changed aborting highlight')
                return False

            self.__md5_cache[number][hlkey] = md5hash
            cmds.append('hi link %s %s' % (hlkey, hlgroup))

        full_cmd = ' | '.join(cmds)
        # self._debug_echo("Sending command %s" % full_cmd)

        self.__vim.command(full_cmd, async=True)

        try:
            self.__cmd_cache[number][hlkey] = cmds
        except KeyError:
            self.__cmd_cache[number] = {}
            self.__cmd_cache[number][hlkey] = cmds

        self._debug_end('Updated highlight for %s' % hlkey)
        return True

    def _parseTags(self, ft):
        self._get_file()
        comp_file = self.__tagfile + SUFFIX

        self._debug_start()
        self._debug_echo("Using tags file %s" % comp_file)

        if not os.path.exists(comp_file):
            self._debug_echo("Tags file does not exist. Running ctags.")
            self._run_ctags()
        else:
            self._debug_echo('updating vim-tagfile', False)
            with gzip.open(comp_file, 'rt', encoding='utf8', errors='replace') as File:
                self.update_vim_tagfile(comp_file, File)

        self._debug_end("Finished updating file list")

        files = [self.__tagfile]

        if files is None:
            self._error("echom 'No tag files found!'")
            return

        # Slurp the whole content of the current buffer
        self._debug_start()
        self.__slurp = ' '.join(self.__vim.current.buffer)
        self._debug_end("Finished updating slurp")

        if self.__neotags_bin is None:
            self._debug_echo("Using python code to analyze tags.", False)
            return self._getTags(files, ft)
        else:
            self._debug_echo("Using C binary to analyze tags.", False)
            return self._bin_getTags(files, ft)

# =============================================================================
    # Yes C binary

    def _bin_getTags(self, files, ft):
        filetypes = ft.lower().split('.')
        languages = ft.lower().split('.')

        lang = self._vim_to_ctags(languages)[0]
        try:
            order = self.__vim.api.eval('neotags#%s#order' % ft)
        except NvimError:
            return

        groups = {
            "%s#%s" % (ft, kind): []
            for kind in [chr(i) for i in order.encode('ascii')]
        }

        if filetypes is None:
            return groups

        File = files[0] + SUFFIX

        self._debug_start()
        if (os.stat(File).st_size == 0):
            return

        proc = subprocess.Popen((self.__neotags_bin,
                                 File,
                                 lang,
                                 order,
                                 str(len(self.__slurp)),
                                 str(len(self.__ignored_tags)),
                                 str(len(self.__ctov) * 2),
                                 ':'.join(self.__ignored_tags) + ':',
                                 ':'.join([i for sub in self.__ctov.items()
                                           for i in sub]) + ':'
                                 ),
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        out, err = proc.communicate(input=self.__slurp.encode('utf-8'))

        self._debug_end('done reading %s' % File)
        out = out.decode().split('\n')

        for s in out:
            self._debug_echo("OUT: %s" % s, False)
        err = err.decode().split('\n')
        for s in err:
            self._debug_echo("ERR: %s" % s, False)

        for i in range(0, len(out) - 1, 2):
            key = "%s#%s" % (ft, out[i].rstrip('\r'))
            try:
                groups[key].append(out[i + 1].rstrip('\r'))
            except KeyError:
                groups[key] = [out[i + 1].rstrip('\r')]

        return groups

# =============================================================================
    # No C binary

    def _getTags(self, files, ft):
        filetypes = ft.lower().split('.')
        languages = ft.lower().split('.')
        groups = {}

        if filetypes is None:
            return groups

        lang = '|'.join(self._vim_to_ctags(filetypes))
        pattern = re.compile(
            b'(?:^|\n)(?P<name>[^\t]+)\t(?P<file>[^\t]+)\t\/(?P<cmd>.+)\/;"\t(?P<kind>\w)\tlanguage:(?P<lang>'
            + bytes(lang, 'utf8') + b'(?:\w+)?)', re.IGNORECASE
        )

        File = files[0] + SUFFIX
        self._debug_start()
        if (os.stat(File).st_size == 0):
            return

        try:
            # with gzip.open(File, 'r', errors='replace', encoding=None) as fp:
            with gzip.open(File, 'r') as fp:
                # mf = mmap.mmap(fp.fileno(), 0,  access=mmap.ACCESS_READ)
                mf = fp.read()
                for match in pattern.finditer(mf):
                    self._parseLine(match, groups, languages)
                # mf.close()
        except IOError as e:
            self._error("could not read %s: %s" % (File, e))
            return

        self._debug_end('done reading %s' % File)

        order = self._tags_order(ft)
        if not order:
            order = list(groups.keys())
        clean = reversed(order)

        self._debug_start()
        self._debug_echo(':'.join([i for sub in self.__ctov.items()
                                   for i in sub]) + ':')

        for a in list(clean):
            if a not in groups:
                continue
            for b in list(order):
                if b not in groups or a == b:
                    continue
                groups[a] = [x for x in groups[a] if x not in groups[b]]

        self._debug_end('done cleaning groups')

        return groups

    def _parseLine(self, match, groups, languages):
        entry = {x: ''.join(map(chr, y)) for x, y in match.groupdict().items()}

        entry['lang'] = self._ctags_to_vim(entry['lang'], languages)

        kind = entry['lang'] + '#' + entry['kind']
        ignore = self._regexp(kind, '.ignore')

        if ignore and ignore.search(entry['name']):
            return

        fgroup = self._regexp(kind, '.filter.pattern')

        name = self.__to_escape.sub(r'\\\g<0>', entry['name'])
        if fgroup is not None and fgroup.search(name):
            name = fgroup.sub('', name)
            kind = entry['lang'] + '#' + entry['kind'] + '_filter'

        if kind in groups:
            if name not in groups[kind]:
                if self._check_tags(name):
                    groups[kind].append(name)
        else:
            if self._check_tags(name):
                groups[kind] = [name]

    def _check_tags(self, tag):
        """Reject tags that do not appear in the current buffer."""
        return (self.__slurp.find(tag) > 0) and tag not in self.__ignored_tags

# =============================================================================

    def _tags_order(self, ft):
        orderlist = []
        filetypes = ft.lower().split('.')

        for filetype in filetypes:
            order = self._exists(filetype, '#order', None)

            if order:
                orderlist += [(filetype + '#') + s for s in list(order)]

        return orderlist

    def _run_ctags(self):
        ctags_args = self.__vim.vars['neotags_ctags_args']
        self._debug_start()

        recurse, path = self._get_file()
        ctags_args.append('-f "%s"' % self.__tagfile)
        ctags_binary = None

        if recurse:
            if self.__find_tool:
                ctags_args.append('-L-')
                ctags_binary = "%s %s | %s" % (
                    self.__find_tool, path, self.__vim.vars['neotags_ctags_bin']
                )
                self._debug_echo("Using %s to find files recursively in dir '%s'"
                                 % (self.__find_tool, path))
            else:
                ctags_args.append('-R')
                ctags_args.append('"%s"' % path)
                ctags_binary = self.__vim.vars['neotags_ctags_bin']
                self._debug_echo("Running ctags on dir '%s'" % path)

        else:
            self._debug_echo(
                "Not running ctags recursively for dir '%s'" % path
            )
            File = os.path.realpath(self.__vim.api.eval("expand('%:p')"))
            ctags_args.append('"%s"' % File)
            ctags_binary = self.__vim.vars['neotags_ctags_bin']
            self._debug_echo("Running ctags on file '%s'" % File)

        full_command = '%s %s' % (ctags_binary, ' '.join(ctags_args))
        self._debug_echo(full_command)

        try:
            proc = subprocess.Popen(full_command, shell=True,
                                    stderr=subprocess.PIPE)

            proc.wait(self.__vim.vars['neotags_ctags_timeout'])
            err = proc.communicate()[1]
            if err:
                self._error('Ctags completed with errors')
                for e in err.decode('ascii').split('\n'):
                    self._error(e)
            else:
                self._debug_echo('Ctags completed successfully')

            # tagfiles = self.__vim.api.eval('&tags').split(",")
            self._debug_start()

            try:
                with open(self.__tagfile, errors='replace') as src:
                    with gzip.open(self.__tagfile + SUFFIX, 'wb', 9) as dst:
                        dst.write(src.buffer.read())
                    src.seek(0)
                    self.update_vim_tagfile(self.__tagfile + SUFFIX, src)

                os.unlink(self.__tagfile)

            except IOError as err:
                self._error("Unexpected IO Error -> '%s'" % err)

            self._debug_end('Finished compressing file.')

        except FileNotFoundError as error:
            self._error('failed to run Ctags %s' % error)

        except subprocess.TimeoutExpired:
            try:
                self._kill(proc.pid)
            except ImportError:
                proc.kill()

            if self.__vim.vars['neotags_silent_timeout'] == 0:
                self.__vim.command(
                    "echom 'Ctags process timed out!'",
                    async=True
                )
        finally:
            self._debug_end("Finished running ctags")

    def _exists(self, kind, var, default):
        Buffer = kind + var

        if Buffer not in self.__exists_buffer:
            if self.__vim.funcs.exists("neotags#%s" % Buffer):
                self.__exists_buffer[Buffer] = self.__vim.api.eval(
                    'neotags#%s' % Buffer
                )
            else:
                self.__exists_buffer[Buffer] = default

        return self.__exists_buffer[Buffer]

    def _getbufferhl(self):
        number = self.__vim.current.buffer.number

        if number in self.__md5_cache.keys():
            highlights = self.__md5_cache[number]
        else:
            self.__md5_cache[number] = highlights = {}

        return highlights, number

    def _clear(self, ft):
        if ft is None:
            self._debug_echo('Clear called with null ft')
            return

        highlights, _ = self._getbufferhl()
        cmds = []
        order = self._tags_order(ft)

        for key in order:
            hlgroup = self._exists(key, '.group', None)
            hlkey = '_Neotags_%s_%s' % (key.replace('#', '_'), hlgroup)
            cmds.append('silent! syntax clear %s' % hlkey)

        self._debug_echo(str(cmds), False)


        self.__vim.command(' | '.join(cmds), async=True)

    def _regexp(self, kind, var):
        Buffer = kind + var

        if Buffer in self.__regex_buffer:
            return self.__regex_buffer[Buffer]

        string = self._exists(kind, var, None)

        if string is not None:
            regexp = re.compile(r'%s' % string)
            self.__regex_buffer[Buffer] = regexp
            return regexp

        return None

    def _debug_start(self):
        self.__start_time.append(time.time())

    def _debug_echo(self, message, pop=True):
        if pop:
            elapsed = time.time() - self.__start_time[-1]
            self.__vim.command(
                'echom "%s (%.2fs)"' %
                (self.__to_escape.sub(r'\\\g<0>', message).replace('"', r'\"'),
                 elapsed)
            )
        else:
            self._inform_echo(message)

    def _debug_end(self, message):
        self._debug_echo(message)
        self.__start_time.pop()
        # self._debug_echo("Total elapsed: " + str(time.time() - self.__globtime), False)

    def _inform_echo(self, message):
        self.__vim.command(
            'echom "%s"' %
            self.__to_escape.sub(r'\\\g<0>', message).replace('"', r'\"')
        )

    def _error(self, message):
        if message:
            message = message.replace('\\', '\\\\').replace('"', '\\"')
            self.__vim.command(
               'echohl ErrorMsg | echom "%s" | echohl None' % message
            )

    def _kill(self, proc_pid):
        import psutil
        process = psutil.Process(proc_pid)
        for proc in process.children():
            proc.kill()
        process.kill()

    def _ctags_to_vim(self, lang, languages):
        lang = lang.strip('\\')
        if lang in self.__ctov and self.__ctov[lang] in languages:
            return self.__ctov[lang]

        return lang.lower()

    def _vim_to_ctags(self, languages):
        for i, lang in enumerate(languages):

            if lang in self.__vtoc:
                languages[i] = self.__vtoc[lang]
                languages[i] = languages[i].strip('\\')

            languages[i] = re.escape(languages[i])

        return languages

    def _get_file(self):
        File = os.path.realpath(self.__vim.api.eval("expand('%:p')"))
        path = os.path.dirname(File)
        projects = []

        self._debug_start()

        recurse = (self.__vim.vars['neotags_recursive']
                   and path not in self.__noRecurseDirs)

        if recurse:
            try:
                with open(self.__settingsFile, 'r') as fp:
                    projects = [i.rstrip() for i in fp]
            except FileNotFoundError:
                with open(self.__settingsFile, 'x') as fp:
                    fp.write('')
                projects = []

            for proj_path in projects:
                if os.path.commonpath([path, proj_path]) == proj_path:
                    path = proj_path
                    break

            path = os.path.realpath(path)
            self._path_replace(path)

        else:
            self._path_replace(File)

        self.__vim.command('let g:neotags_file = "%s"'
                           % self.__tagfile, async=True)
        self._debug_end("File is '%s'" % self.__tagfile)

        return recurse, path

    def _path_replace(self, path):
        if (platform == 'win32'):
            # For some reason replace wouldn't work here. I have no idea why.
            path = re.sub(':', '__', path)
            sep_char = '\\'
        else:
            sep_char = '/'

        self.__tagfile = "%s/%s.tags" % (self.__directory,
                                         path.replace(sep_char, '__'))

    def _get_binary(self, loud=False):
        binary = self.__vim.vars['neotags_bin']

        if platform == 'win32' and binary.find('.exe') < 0:
            binary += '.exe'

        if os.path.exists(binary):
            self.__vim.vars['neotags_use_binary'] = 1
        else:
            self.__vim.vars['neotags_use_binary'] = 0
            binary = None
            if loud:
                self._inform_echo("Binary '%s' doesn't exist. Cannot enable."
                                  % self.__neotags_bin, False)
            else:
                self._debug_echo("Binary '%s' doesn't exist."
                                 % self.__neotags_bin, False)

        return binary

    def update_vim_tagfile(self, tagfile, open_file):
        try:
            if tagfile not in self.__tmp_cache:
                self.__tmp_cache[tagfile] = {}
                fd, name = mkstemp()
                tmpfile = os.fdopen(fd, errors='replace', mode='w')

                self._write_file(open_file, tmpfile, tagfile)

                self.__tmp_cache[tagfile]['fp'] = tmpfile
                self.__tmp_cache[tagfile]['name'] = name

            else:
                tmpfile = self.__tmp_cache[tagfile]['fp']
                name = self.__tmp_cache[tagfile]['name']
                tmpfile.seek(0)
                tmpfile.truncate(0)
                tmpfile.flush()
                self._write_file(open_file, tmpfile, tagfile)

            tmpfile.flush()
            self.__tmp_cache[tagfile]['mtime'] = os.path.getmtime(tagfile)
            self.__vim.command('set tags+=%s' % name, async=True)

        except IOError as err:
            self._error("something horrible happened -> %s" % err)

    def _write_file(self, File, tmp, name):
        tmp.write(File.read())
