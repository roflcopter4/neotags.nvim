" ============================================================================
" File:        neotags.vim
" Author:      Christian Persson <c0r73x@gmail.com>
" Repository:  https://github.com/c0r73x/neotags.nvim
"              Released under the MIT license
" ============================================================================

" Options {{{
if exists('g:loaded_neotags')
    finish
endif

if !exists('g:neotags_file')
    let g:neotags_file = './tags'
endif

if !exists('g:neotags_events_update')
    let g:neotags_events_update = [
                \   'BufWritePost'
                \ ]
endif

if !exists('g:neotags_events_highlight')
    let g:neotags_events_highlight = [
                \   'BufEnter'
                \ ]
endif

if !exists('g:neotags_enabled')
    let g:neotags_enabled = 0
endif

if !exists('g:neotags_verbose')
    let g:neotags_verbose = 0
endif

if !exists('g:neotags_run_ctags')
    let g:neotags_run_ctags = 1
endif

if !exists('g:neotags_highlight')
    let g:neotags_highlight = 1
endif

if !exists('g:neotags_recursive')
    let g:neotags_recursive = 1
endif

if !exists('g:neotags_appendpath')
    let g:neotags_appendpath = 1
endif

if !exists('g:neotags_ctags_bin')
    let g:neotags_ctags_bin = 'ctags'
endif

if !exists('g:neotags_ctags_timeout')
    let g:neotags_ctags_timeout = 3
endif

if !exists('g:neotags_silent_timeout')
    let g:neotags_silent_timeout = 0
endif

if !exists('g:neotags_patternlength')
    let g:neotags_patternlength = 2048
endif

if !exists('g:neotags_ctags_args')
    let g:neotags_ctags_args = [
                \ '--fields=+l',
                \ '--c-kinds=+p',
                \ '--c++-kinds=+p',
                \ '--sort=no',
                \ '--extras=+q'
                \ ]
endif

" }}}
" C++ {{{1
if !exists('g:neotags#cpp#order')
	let g:neotags#cpp#order = 'cgstuedfpm'
endif

let g:neotags#cpp#c = {
            \   'group': 'cppTypeTag',
            \   'ignore': '(__anon[0-9a-f]+|[_\w]+::)'
            \ }

let g:neotags#cpp#g = g:neotags#cpp#c
let g:neotags#cpp#s = g:neotags#cpp#c
let g:neotags#cpp#t = g:neotags#cpp#c
let g:neotags#cpp#u = g:neotags#cpp#c

let g:neotags#cpp#m = {
            \   'group': 'cppMemberTag',
            \   'ignore': '(__anon[0-9a-f]+|[_\w]+::)'
            \ }

let g:neotags#cpp#e = {
            \   'group': 'cppEnumTag',
            \   'ignore': '^[_\w]+::'
            \ }

let g:neotags#cpp#d = {
            \   'group': 'cppPreProcTag'
            \ }

let g:neotags#cpp#f = {
            \   'group': 'cppFunctionTag',
            \   'ignore': '^(~|[_\w]+::)'
            \ }

let g:neotags#cpp#p = g:neotags#cpp#f
" 1}}}
" C {{{1
if !exists('g:neotags#c#order')
	let g:neotags#c#order = 'cgstuedfpm'
endif

let g:neotags#c#c = {
            \   'group': 'cTypeTag',
            \   'ignore': '(__anon[0-9a-f]+|[_\w]+::)'
            \ }

let g:neotags#c#m = {
            \   'group': 'cMemberTag',
            \   'ignore': '(__anon[0-9a-f]+|[_\w]+::)'
            \ }

let g:neotags#c#g = g:neotags#cpp#c
let g:neotags#c#s = g:neotags#cpp#c
let g:neotags#c#t = g:neotags#cpp#c
let g:neotags#c#u = g:neotags#cpp#c

let g:neotags#c#e = {
            \   'group': 'cEnumTag',
            \   'ignore': '^[_\w]+::'
            \ }

let g:neotags#c#d = {
            \   'group': 'cPreProcTag'
            \ }

let g:neotags#c#f = {
            \   'group': 'cFunctionTag',
            \   'ignore': '^(~|[_\w]+::)'
            \ }

let g:neotags#c#p = g:neotags#c#f
" 1}}}
" Python {{{1
if !exists('g:neotags#python#order')
	let g:neotags#python#order = 'mfc'
endif

let g:neotags#python#m = {
            \   'prefix': '\(\.\|\<def\s\+\)\@<=',
            \   'group': 'pythonMethodTag'
            \ }
let g:neotags#python#f = {
            \   'prefix': '\%(\<def\s\+\)\@<!\<',
            \   'group': 'pythonFunctionTag'
            \ }

let g:neotags#python#c = {
            \   'group': 'pythonClassTag'
            \ }
" 1}}}
" Ruby {{{1
if !exists('g:neotags#ruby#order')
	let g:neotags#ruby#order = 'mfc'
endif

let g:neotags#ruby#m = {
            \   'group': 'rubyModuleNameTag',
            \ }

let g:neotags#ruby#c = {
            \   'group': 'rubyClassNameTag',
            \ }

let g:neotags#ruby#f = {
            \   'group': 'rubyMethodNameTag',
            \ }

let g:neotags#ruby#F = g:neotags#ruby#f
" 1}}}
" Shell {{{1
if !exists('g:neotags#sh#order')
	let g:neotags#sh#order = 'f'
endif

let g:neotags#sh#f = {
            \   'group': 'shFunctionTag',
            \   'suffix': '\(\w\|\s*()|()\)\@!'
            \ }
" 1}}}
" Java {{{1
if !exists('g:neotags#java#order')
	let g:neotags#java#order = 'cim'
endif

let g:neotags#java#c = {
            \   'group': 'javaClassTag'
            \ }

let g:neotags#java#i = {
            \   'group': 'javaInterfaceTag'
            \ }

let g:neotags#java#m = {
            \   'group': 'javaMethodTag'
            \ }
" 1}}}
" javascript {{{1
let g:neotags#javascript#order = 'cCfmpo'

let g:neotags#javascript#c = {
            \   'group': 'javascriptClassTag',
            \   'notin': [
            \       'jsx.*',
            \       'javascriptTemplate'
            \   ]
            \ }

let g:neotags#javascript#C = {
            \   'group': 'javascriptConstantTag',
            \   'notin': [
            \       'jsx.*',
            \       'javascriptTemplate'
            \   ]
            \ }

let g:neotags#javascript#f = {
            \   'group': 'javascriptFunctionTag',
            \   'notin': [
            \       'jsx.*',
            \       'javascriptTemplate',
            \       'javascriptConditional',
            \       'javascriptRepeat'
            \   ]
            \ }

let g:neotags#javascript#m = {
            \   'group': 'javascriptMethodTag',
            \   'notin': [
            \       'jsx.*',
            \       'javascriptTemplate',
            \       'javascriptConditional',
            \       'javascriptRepeat'
            \   ]
            \ }

let g:neotags#javascript#o = {
            \   'group': 'javascriptObjectTag',
            \   'notin': [
            \       'jsx.*',
            \       'javascriptTemplate',
            \       'javascriptConditional',
            \       'javascriptRepeat'
            \   ]
            \ }

let g:neotags#javascript#p = {
            \   'group': 'javascriptPropTag',
            \   'notin': [
            \       'jsx.*',
            \       'javascriptTemplate',
            \       'javascriptConditional',
            \       'javascriptRepeat'
            \   ]
            \ }
" 1}}}
" vim {{{1
if !exists('g:neotags#vim#order')
	let g:neotags#vim#order = 'acf'
endif

let g:neotags#vim#a = {
            \   'group': 'vimAutoGroupTag'
            \ }

let g:neotags#vim#c = {
            \   'group': 'vimCommandTag',
            \   'prefix': '\(\(^\|\s\):\?\)\@<=',
            \   'suffix': '\(!\?\(\s\|$\)\)\@='
            \ }

let g:neotags#vim#f = {
            \   'group': 'vimFuncNameTag',
            \   'prefix': '\C\%(\<s:\|<[sS][iI][dD]>\)\@<!\<',
            \   'filter': {
            \       'pattern': '(?i)(<sid>\w|\bs:\w)',
            \       'group': 'vimScriptFuncNameTag',
            \       'prefix': '\C\%(\<s:\|<[sS][iI][dD]>\)',
            \   }
            \ }

" 1}}}
" perl {{{1
if !exists('g:neotags#perl#order')
	let g:neotags#perl#order = 's'
endif

let g:neotags#perl#s = {
            \   'group': 'perlFunctionTag',
            \   'prefix': '\%(\<sub\s\*\)\@<!\%(>\|\s\|&\|^\)\@<=\<',
            \ }
" 1}}}
" php {{{1
if !exists('g:neotags#php#order')
	let g:neotags#php#order = 'fc'
endif

let g:neotags#php#f = {
            \   'group': 'phpFunctionsTag',
            \   'suffix': '(\@='
            \ }

let g:neotags#php#c = {
            \   'group': 'phpClassesTag'
            \ }
" 1}}}

highlight def link rubyModuleNameTag Type
highlight def link rubyClassNameTag Type
highlight def link rubyMethodNameTag Function

highlight def link PythonMethodTag pythonFunction
highlight def link PythonClassTag pythonFunction

highlight def link cEnumTag Identifier
highlight def link cFunctionTag Function
highlight def link cMemberTag Identifier

highlight def link cppEnumTag Identifier
highlight def link cppFunctionTag Function
highlight def link cppMemberTag Identifier

highlight def link shFunctionTag Operator
highlight def link perlFunctionTag Operator

highlight def link javaClassTag Identifier
highlight def link javaMethodTag Function
highlight def link javaInterfaceTag Identifier

highlight def link javascriptFunctionTag Identifier

highlight def link vimAutoGroupTag vimAutoEvent

let g:loaded_neotags = 1

augroup NeoTags
    autocmd VimEnter * call NeotagsInit()
augroup END

command! NeotagsToggle call NeotagsToggle()

" vim:fdm=marker
