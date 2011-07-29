#!/home/phunt/phpphp/pypy/bin/pypy
import sys
import ast
import pprint
import readline
import traceback
import os
try:
    import collections
    collections.OrderedDict
except:
    import ordereddict as collections

sys.path.insert(0, "/home/phunt/phpphp/phply")

from phply import pythonast, phplex
from phply import phpparse

import hphp_rpc

import ast

class PHPArray(collections.OrderedDict):
    def __init__(self, items):
        if not callable(getattr(items, "keys", None)):
            items = enumerate(items)
        collections.OrderedDict.__init__(self, items)
    def append(self, item):
        self[max(self.keys())] = item

class _GlobalReturn(Exception):
    def __init__(self, value=None):
        self.value = value

class ReflectionExtension(object):
    def __init__(self, name):
        self.name = name
    def getVersion(self):
        return "1.3.9"

PHP_VERSION_ID = 50300

class PHPPHPi(object):
    def __init__(self, script_name):
        self.loaded_files = set()
        self.include_stack = []
        self.globals = self.get_globals()
        self._server["SCRIPT_NAME"] = script_name
    def echo(self, *objs):
        for obj in objs:
            sys.stdout.write(str(obj))

    def inline_html(self, obj):
        sys.stdout.write(obj)

    def XXX(self, obj):
        print 'Not implemented:\n ', obj

    def MAGIC(self, name):
        if name == "__FILE__":
            return self.include_stack[-1]

    def define(self, name, value):
        self.globals[name] = value

    def include(self, filename, once):
        filename = os.path.abspath(filename)
        if not (once and filename in self.loaded_files):
            self.include_stack.append(filename)
            print "=== executing", filename, "==="
            try:
                self.exec_file(filename)
            except IOError:
                raise

            self.include_stack.pop(-1)
            if len(self.include_stack) > 0:
                print "=== executing", self.include_stack[-1], "==="

        self.loaded_files.add(filename)

    def array_pop(self, arr):
        return arr.popitem()[1]

    require = include

    def all_vars(self, d1, d2):
        d3 = {}
        d3.update(d1)
        d3.update(d2)
        return d3

    def get_globals(self):
        rpc = hphp_rpc.HphpRpc()

        self._server = os.environ.copy()

        g = {"echo": self.echo,
             "inline_html": self.inline_html,
             "XXX": self.XXX,
             "require": self.require,
             "include": self.include,
             "_SERVER": self._server,
             "realpath": os.path.abspath,
             "dirname": os.path.dirname,
             "MAGIC" : self.MAGIC,
             "GLOBALS" : {},
             "_GlobalReturn": _GlobalReturn,
             "define": self.define,
             "all_vars": self.all_vars,
             "PHPArray": PHPArray,
             "array_pop": self.array_pop,
             "_INSTANCEOF": isinstance,
             "_ENV": os.environ.copy(),
             "ReflectionExtension": ReflectionExtension,
             "PHP_VERSION_ID": PHP_VERSION_ID}

        for function in rpc.get_defined_functions()["internal"]:
            if function not in g:
                g[function] = getattr(rpc, function)

        return g

    def ast_dump(self, code):
        print 'AST dump:'
        print ' ', ast.dump(code, include_attributes=True)

    def src_dump(self, code):
        import unparse
        print "src dump:"
        unparse.Unparser(code)

    def php_eval(self, nodes, filename="<string>"):
        body = []
        for node in nodes:
            stmt = pythonast.to_stmt(pythonast.PHP2Python().from_phpast(node))
            body.append(stmt)
        code = ast.Module(body)
        #self.ast_dump(code)
        try:
            return eval(compile(code, filename, mode='exec'), self.globals)
        except _GlobalReturn, g:
            return g.value
        # TODO: strip non-php files from traceback

    def parse_string(self, s, filename):
        lexer = phplex.lexer
        lexer.lineno = 1
        phpparse.current_filename = filename
        s += "\n?>"
        return phpparse.parser.parse(s, lexer=lexer)

    def exec_string(self, s, filename):
        return self.php_eval(self.parse_string(s, filename), filename)

    def exec_file(self, filename):
        with open(filename) as f:
            source = f.read()
        self.exec_string(source, filename)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[sys.argv.index("--file")+1]
        PHPPHPi(filename).include(filename, False)
    else:
        PHPPHPi("<stdin>").exec_string(sys.stdin.read(), "<stdin>")
