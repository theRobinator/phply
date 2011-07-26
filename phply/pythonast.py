import phpast as php
import ast as py

unary_ops = {
    '~': py.Invert,
    '!': py.Not,
    '+': py.UAdd,
    '-': py.USub,
}

bool_ops = {
    '&&': py.And,
    '||': py.Or,
    'and': py.And,
    'or': py.Or,
}

cmp_ops = {
    '!=': py.NotEq,
    '!==': py.NotEq,
    '<>': py.NotEq,
    '<': py.Lt,
    '<=': py.LtE,
    '==': py.Eq,
    '===': py.Eq,
    '>': py.Gt,
    '>=': py.GtE,
}

binary_ops = {
    '+': py.Add,
    '-': py.Sub,
    '*': py.Mult,
    '/': py.Div,
    '%': py.Mod,
    '<<': py.LShift,
    '>>': py.RShift,
    '|': py.BitOr,
    '&': py.BitAnd,
    '^': py.BitXor,
}

casts = {
    'double': 'float',
    'string': 'str',
    'array': 'list',
}

def to_stmt(pynode):
    if not isinstance(pynode, py.stmt):
        pynode = py.Expr(pynode,
                         lineno=pynode.lineno,
                         col_offset=pynode.col_offset)
    return pynode

def flatten(l):
    for item in l:
        if isinstance(item, list):
            for item2 in item:
                yield item2
        else:
            yield item

# TODO: handle define at compile time
class Scope(object):
    def __init__(self, name):
        self.name = name
        self.statics = {}

class PHP2Python(object):
    def __init__(self):
        self.scope_stack = []

    def get_static(self, name):
        for scope in reversed(self.scope_stack):
            v = scope.statics.get(name)
            if v:
                return v
        return False

    def add_static(self, name):
        if len(self.scope_stack) == 0:
            return
        static_name = "static_" + "_".join([scope.name for scope in self.scope_stack] + [name])
        self.scope_stack[-1].statics[name] = static_name

    def from_phpast(self, node):
    if node is None:
            return py.Name('None', py.Load(**pos(node)), **pos(node))

    if isinstance(node, basestring):
        return py.Str(node, **pos(node))

        if isinstance(node, (int, float, long)):
        return py.Num(node, **pos(node))

    if isinstance(node, php.Array):
        if node.nodes:
            if node.nodes[0].key is not None:
                keys = []
                values = []
                for elem in node.nodes:
                        keys.append(self.from_phpast(elem.key))
                        values.append(self.from_phpast(elem.value))
                    ds = py.Dict(keys, values, **pos(node))
            else:
                    ds = py.List([self.from_phpast(x.value) for x in node.nodes],
                               py.Load(**pos(node)),
                               **pos(node))
        else:
                ds = py.List([], py.Load(**pos(node)), **pos(node))
            return py.Call(py.Name('PHPArray', py.Load(**pos(node)), **pos(node)),
                           [ds],
                           [], None, None, **pos(node))

    if isinstance(node, php.InlineHTML):
        args = [py.Str(node.data, **pos(node))]
        return py.Call(py.Name('inline_html',
                               py.Load(**pos(node)),
                               **pos(node)),
                       args, [], None, None,
                       **pos(node))

    if isinstance(node, php.Echo):
        return py.Call(py.Name('echo', py.Load(**pos(node)),
                               **pos(node)),
                           map(self.from_phpast, node.nodes),
                       [], None, None,
                       **pos(node))

    if isinstance(node, php.Print):
            return py.Print(None, [self.from_phpast(node.node)], True, **pos(node))

    if isinstance(node, php.Exit):
        args = []
        if node.expr is not None:
                args.append(self.from_phpast(node.expr))
            return py.Raise(py.Call(py.Name('SystemExit', py.Load(**pos(node)),
                                        **pos(node)),
                                args, [], None, None, **pos(node)),
                        None, None, **pos(node))

    if isinstance(node, php.Return):
            if len(self.scope_stack) > 0:
                # return from function
        if node.node is None:
            return py.Return(None, **pos(node))
        else:
                    return py.Return(self.from_phpast(node.node), **pos(node))
            else:
                # return from script
                args = [self.from_phpast(node.node)]
                return py.Raise(py.Call(py.Name('_GlobalReturn', py.Load(**pos(node)),
                                                **pos(node)),
                                        args, [], None, None, **pos(node)),
                                None, None, **pos(node))

    if isinstance(node, php.Break):
        assert node.node is None, 'level on break not supported'
        return py.Break(**pos(node))

    if isinstance(node, php.Continue):
        assert node.node is None, 'level on continue not supported'
        return py.Continue(**pos(node))

    if isinstance(node, php.Silence):
            return self.from_phpast(node.expr)

    if isinstance(node, php.Block):
            return self.from_phpast(php.If(1, node, [], None, lineno=node.lineno))

    if isinstance(node, php.Unset):
            return py.Delete(map(self.from_phpast, node.nodes), **pos(node))

    if isinstance(node, php.IsSet) and len(node.nodes) == 1:
        if isinstance(node.nodes[0], php.ArrayOffset):
                return py.Compare(self.from_phpast(node.nodes[0].expr),
                              [py.In(**pos(node))],
                                  [self.from_phpast(node.nodes[0].node)],
                              **pos(node))
        if isinstance(node.nodes[0], php.ObjectProperty):
            return py.Call(py.Name('hasattr', py.Load(**pos(node)),
                                   **pos(node)),
                               [self.from_phpast(node.nodes[0].node),
                                self.from_phpast(node.nodes[0].name)],
                           [], None, None, **pos(node))
        if isinstance(node.nodes[0], php.Variable):
                variable_name = node.nodes[0].name[1:]
                static_name = self.get_static(variable_name)
                if static_name:
                    variable_name = static_name

                globs = py.Call(py.Name('globals', py.Load(**pos(node)),
                                        **pos(node)),
                                [], [], None, None, **pos(node))

                locs = py.Call(py.Name('locals', py.Load(**pos(node)),
                                        **pos(node)),
                                [], [], None, None, **pos(node))

                return py.Compare(py.Str(static_name, **pos(node)),
                              [py.In(**pos(node))],
                                  [py.Call(py.Name('all_vars', py.Load(**pos(node)),
                                               **pos(node)),
                                           [globs, locs], [], None, None, **pos(node))],
                              **pos(node))
            return py.Compare(self.from_phpast(node.nodes[0]),
                          [py.IsNot(**pos(node))],
                          [py.Name('None', py.Load(**pos(node)), **pos(node))],
                          **pos(node))

    if isinstance(node, php.Empty):
            return self.from_phpast(php.UnaryOp('!',
                                       php.BinaryOp('&&',
                                                    php.IsSet([node.expr],
                                                              lineno=node.lineno),
                                                    node.expr,
                                                    lineno=node.lineno),
                                       lineno=node.lineno))

    if isinstance(node, php.Assignment):
        if (isinstance(node.node, php.ArrayOffset)
            and node.node.expr is None):
                return py.Call(py.Attribute(self.from_phpast(node.node.node),
                                        'append', py.Load(**pos(node)),
                                        **pos(node)),
                               [self.from_phpast(node.expr)],
                           [], None, None, **pos(node))
            # need to unpack nested assignments
            targets = [store(self.from_phpast(node.node))]
            while isinstance(node.expr, php.Assignment):
                node = node.expr
                targets.append(store(self.from_phpast(node.node)))
            return py.Assign(targets,
                             self.from_phpast(node.expr),
                         **pos(node))

    if isinstance(node, php.ListAssignment):
            return py.Assign([py.Tuple(map(store, map(self.from_phpast, node.nodes)),
                                   py.Store(**pos(node)),
                                   **pos(node))],
                             self.from_phpast(node.expr),
                          **pos(node))

    if isinstance(node, php.AssignOp):
            return self.from_phpast(php.Assignment(node.left,
                                          php.BinaryOp(node.op[:-1],
                                                       node.left,
                                                       node.right,
                                                       lineno=node.lineno),
                                          False,
                                          lineno=node.lineno))

    if isinstance(node, (php.PreIncDecOp, php.PostIncDecOp)):
            return self.from_phpast(php.Assignment(node.expr,
                                          php.BinaryOp(node.op[0],
                                                       node.expr,
                                                       1,
                                                       lineno=node.lineno),
                                          False,
                                          lineno=node.lineno))

    if isinstance(node, php.ArrayOffset):
            return py.Subscript(self.from_phpast(node.node),
                                py.Index(self.from_phpast(node.expr), **pos(node)),
                            py.Load(**pos(node)),
                            **pos(node))

    if isinstance(node, php.ObjectProperty):
        if isinstance(node.name, php.Variable):
            return py.Call(py.Name('getattr', py.Load(**pos(node)),
                                   **pos(node)),
                               [self.from_phpast(node.node),
                                self.from_phpast(node.name)],
                           [], None, None, **pos(node))            
            return py.Attribute(self.from_phpast(node.node),
                            node.name,
                            py.Load(**pos(node)),
                            **pos(node))

    if isinstance(node, php.Constant):
        name = node.name
        if name.lower() == 'true': name = 'True'
        if name.lower() == 'false': name = 'False'
        if name.lower() == 'null': name = 'None'
        return py.Name(name, py.Load(**pos(node)), **pos(node))

    if isinstance(node, php.Variable):
        name = node.name[1:]
            static_name = self.get_static(name)
            if static_name:
                name = static_name
        if name == 'this': name = 'self'
        return py.Name(name, py.Load(**pos(node)), **pos(node))

    if isinstance(node, php.Global):
            return py.Global([self.from_phpast(var).id for var in node.nodes], **pos(node))

    if isinstance(node, php.Include):
        once = py.Name('True' if node.once else 'False',
                       py.Load(**pos(node)),
                       **pos(node))
        return py.Call(py.Name('include', py.Load(**pos(node)),
                               **pos(node)),
                           [self.from_phpast(node.expr), once],
                       [], None, None, **pos(node))

    if isinstance(node, php.Require):
        once = py.Name('True' if node.once else 'False',
                       py.Load(**pos(node)),
                       **pos(node))
        return py.Call(py.Name('require', py.Load(**pos(node)),
                               **pos(node)),
                           [self.from_phpast(node.expr), once],
                       [], None, None, **pos(node))

    if isinstance(node, php.UnaryOp):
        op = unary_ops.get(node.op)
        assert op is not None, "unknown unary operator: '%s'" % node.op
        op = op(**pos(node))
            return py.UnaryOp(op, self.from_phpast(node.expr), **pos(node))

    if isinstance(node, php.BinaryOp):
        if node.op == '.':
            pattern, pieces = build_format(node.left, node.right)
            if pieces:
                return py.BinOp(py.Str(pattern, **pos(node)),
                                py.Mod(**pos(node)),
                                    py.Tuple(map(self.from_phpast, pieces),
                                         py.Load(**pos(node)),
                                         **pos(node)),
                                **pos(node))
            else:
                return py.Str(pattern % (), **pos(node))
        if node.op in bool_ops:
            op = bool_ops[node.op](**pos(node))
                return py.BoolOp(op, [self.from_phpast(node.left),
                                      self.from_phpast(node.right)], **pos(node))
        if node.op in cmp_ops:
            op = cmp_ops[node.op](**pos(node))
                return py.Compare(self.from_phpast(node.left), [op],
                                  [self.from_phpast(node.right)],
                              **pos(node))
        op = binary_ops.get(node.op)
        assert op is not None, "unknown binary operator: '%s'" % node.op
        op = op(**pos(node))
            return py.BinOp(self.from_phpast(node.left),
                        op,
                            self.from_phpast(node.right),
                        **pos(node))

    if isinstance(node, php.TernaryOp):
            return py.IfExp(self.from_phpast(node.expr),
                            self.from_phpast(node.iftrue),
                            self.from_phpast(node.iffalse),
                        **pos(node))

    if isinstance(node, php.Cast):
        return py.Call(py.Name(casts.get(node.type, node.type),
                               py.Load(**pos(node)),
                               **pos(node)),
                           [self.from_phpast(node.expr)],
                       [], None, None, **pos(node))

    if isinstance(node, php.If):
        orelse = []
        if node.else_:
                for else_ in map(self.from_phpast, deblock(node.else_.node)):
                orelse.append(to_stmt(else_))
        for elseif in reversed(node.elseifs):
                orelse = [py.If(self.from_phpast(elseif.expr),
                                map(to_stmt, map(self.from_phpast, deblock(elseif.node))),
                            orelse, **pos(node))]
            return py.If(self.from_phpast(node.expr),
                         map(to_stmt, map(self.from_phpast, deblock(node.node))),
                     orelse, **pos(node))

    if isinstance(node, php.For):
        assert node.test is None or len(node.test) == 1, \
            'only a single test is supported in for-loops'
            return self.from_phpast(php.Block((node.start or [])
                                     + [php.While(node.test[0] if node.test else 1,
                                                  php.Block(deblock(node.node)
                                                            + (node.count or []),
                                                            lineno=node.lineno),
                                                  lineno=node.lineno)],
                                     lineno=node.lineno))

    if isinstance(node, php.Foreach):
            expr = self.from_phpast(node.expr)

        if node.keyvar is None:
            target = py.Name(node.valvar.name[1:], py.Store(**pos(node)),
                             **pos(node))
        else:
            target = py.Tuple([py.Name(node.keyvar.name[1:],
                                           py.Store(**pos(node)),
                                           **pos(node)),
                               py.Name(node.valvar.name[1:],
                                           py.Store(**pos(node)),
                                           **pos(node))],
                              py.Store(**pos(node)), **pos(node))
                # call iteritems on expr
                expr = py.Call(py.Attribute(expr,
                                            "iteritems",
                                            py.Load(**pos(node)),
                                            **pos(node)),
                               [], {}, None, None, **pos(node))


            return py.For(target, expr,
                          map(to_stmt, map(self.from_phpast, deblock(node.node))),
                      [], **pos(node))

    if isinstance(node, php.While):
            return py.While(self.from_phpast(node.expr),
                            map(to_stmt, map(self.from_phpast, deblock(node.node))),
                        [], **pos(node))

    if isinstance(node, php.DoWhile):
        condition = php.If(php.UnaryOp('!', node.expr, lineno=node.lineno),
                           php.Break(None, lineno=node.lineno),
                           [], None, lineno=node.lineno)
            return self.from_phpast(php.While(1,
                                     php.Block(deblock(node.node)
                                               + [condition],
                                               lineno=node.lineno),
                                     lineno=node.lineno))

    if isinstance(node, php.Try):
            return py.TryExcept(map(to_stmt, map(self.from_phpast, node.nodes)),
                            [py.ExceptHandler(py.Name(catch.class_,
                                                      py.Load(**pos(node)),
                                                      **pos(node)),
                                                  store(self.from_phpast(catch.var)),
                                                  map(to_stmt, map(self.from_phpast, catch.nodes)),
                                              **pos(node))
                             for catch in node.catches],
                            [],
                            **pos(node))

    if isinstance(node, php.Throw):
            return py.Raise(self.from_phpast(node.node), None, None, **pos(node))

    if isinstance(node, php.Function):
        args = []
        defaults = []
        for param in node.params:
            args.append(py.Name(param.name[1:],
                                py.Param(**pos(node)),
                                **pos(node)))
            if param.default is not None:
                    defaults.append(self.from_phpast(param.default))
            self.scope_stack.append(Scope(node.name))
            body = map(to_stmt, map(self.from_phpast, node.nodes))
        if not body: body = [py.Pass(**pos(node))]
            rv = py.FunctionDef(node.name,
                                py.arguments(args, '_varargs', None, defaults),
                              body, [], **pos(node))
            self.scope_stack.pop(-1)
            return rv

    if isinstance(node, php.Method):
        args = []
        defaults = []
        decorator_list = []
        if 'static' in node.modifiers:
            decorator_list.append(py.Name('classmethod',
                                          py.Load(**pos(node)),
                                          **pos(node)))
            args.append(py.Name('cls', py.Param(**pos(node)), **pos(node)))
        else:
            args.append(py.Name('self', py.Param(**pos(node)), **pos(node)))
        for param in node.params:
            args.append(py.Name(param.name[1:],
                                py.Param(**pos(node)),
                                **pos(node)))
            if param.default is not None:
                    defaults.append(self.from_phpast(param.default))
            self.scope_stack.append(Scope(node.name))
            body = map(to_stmt, map(self.from_phpast, node.nodes))
        if not body: body = [py.Pass(**pos(node))]
            rv = py.FunctionDef(node.name,
                                py.arguments(args, '_varargs', None, defaults),
                              body, decorator_list, **pos(node))
            self.scope_stack.pop(-1)
            return rv

        if isinstance(node, php.Static):
            assert len(node.nodes) == 1, "can't handle more than 1 static"
            node = node.nodes[0]
            self.add_static(node.name[1:])
            name = node.name
            initial = node.initial
            lineno = node.lineno
            node = php.Block([
                    php.Global([php.Variable(name, lineno=lineno)],
                               lineno = lineno),
                    php.If(
                        php.UnaryOp("!",
                                    php.IsSet([php.Variable(name, lineno=lineno)],
                                              lineno=lineno),
                                    lineno=lineno),
                        php.Assignment(
                            php.Variable(name, lineno=lineno),
                            initial,
                            False, lineno=lineno),
                        [],
                        None,
                        lineno=node.lineno)
                    ],lineno = lineno)
            return self.from_phpast(node)

    if isinstance(node, php.Class):
        name = node.name
        bases = []
            extends = []
            if node.extends:
                extends += [node.extends]
            if node.implements:
                extends += node.implements
            extends = extends or ['object']
            for superclass in extends:
                bases.append(py.Name(superclass, py.Load(**pos(node)), **pos(node)))
            body = map(to_stmt, flatten(map(self.from_phpast, node.nodes)))
        for stmt in body:
            if (isinstance(stmt, py.FunctionDef)
                and stmt.name in (name, '__construct')):
                stmt.name = '__init__'
        if not body: body = [py.Pass(**pos(node))]
        return py.ClassDef(name, bases, body, [], **pos(node))

        if isinstance(node, php.Interface):
            return self.from_phpast(php.Class(node.name, None, "object", [], [], lineno=node.lineno))

    if isinstance(node, (php.ClassConstants, php.ClassVariables)):
            statements = []
            for child in node.nodes:
                if isinstance(child, php.ClassConstant):
                    name = php.Constant(child.name, lineno=child.lineno)
        else:
                    name = php.Variable(child.name, lineno=child.lineno)
                initial = child.initial
        if initial is None:
                    initial = php.Constant('None', lineno=child.lineno)
                statements.append(py.Assign([store(self.from_phpast(name))],
                                            self.from_phpast(initial),
                                            **pos(child)))
            return statements

    if isinstance(node, (php.FunctionCall, php.New)):
            if node.name == "func_get_args":
                return py.Name('_varargs', py.Load(**pos(node)), **pos(node))
            elif node.name == "func_get_arg":
                return py.Subscript(py.Name('_varargs', py.Load(**pos(node)), **pos(node)),
                                    py.Index(self.from_phpast(node.params[0]), **pos(node)),
                                    py.Load(**pos(node)),
                                    **pos(node))
            elif node.name == "func_num_args":
                return py.Call(py.Name('len', py.Load(**pos(node)),
                                       **pos(node)),
                               [py.Name('_varargs', py.Load(**pos(node)), **pos(node))],
                               [], None, None, **pos(node))
        if isinstance(node.name, basestring):
            name = py.Name(node.name, py.Load(**pos(node)), **pos(node))
        else:
            name = py.Subscript(py.Call(py.Name('vars', py.Load(**pos(node)),
                                                **pos(node)),
                                        [], [], None, None, **pos(node)),
                                    py.Index(self.from_phpast(node.name), **pos(node)),
                                py.Load(**pos(node)),
                                **pos(node))
            args, kwargs = self.build_args(node.params)
        return py.Call(name, args, kwargs, None, None, **pos(node))

    if isinstance(node, php.MethodCall):
            args, kwargs = self.build_args(node.params)
            return py.Call(py.Attribute(self.from_phpast(node.node),
                                    node.name,
                                    py.Load(**pos(node)),
                                    **pos(node)),
                       args, kwargs, None, None, **pos(node))

    if isinstance(node, php.StaticMethodCall):
        class_ = node.class_
        if class_ == 'self': class_ = 'cls' 
            args, kwargs = self.build_args(node.params)
        return py.Call(py.Attribute(py.Name(class_, py.Load(**pos(node)),
                                            **pos(node)),
                                    node.name,
                                    py.Load(**pos(node)),
                                    **pos(node)),
                       args, kwargs, None, None, **pos(node))

    if isinstance(node, php.StaticProperty):
        class_ = node.node
        name = node.name
            if class_ == "self": class_ = "cls"
        if isinstance(name, php.Variable):
                name = name.name
            name = name[1:]
        return py.Attribute(py.Name(class_, py.Load(**pos(node)),
                                    **pos(node)),
                            name,
                            py.Load(**pos(node)),
                            **pos(node))        

        if isinstance(node, php.MagicConstant):
            return py.Call(py.Name('MAGIC', py.Load(**pos(node)), **pos(node)),
                           [py.Str(str(node.name), **pos(node))], [], None, None, **pos(node))

    return py.Call(py.Name('XXX', py.Load(**pos(node)), **pos(node)),
                   [py.Str(str(node), **pos(node))],
                   [], None, None, **pos(node))

    def build_args(self, params):
        args = []
        kwargs = []
        for param in params:
            node = self.from_phpast(param.node)
            if isinstance(node, py.Assign):
                kwargs.append(py.keyword(node.targets[0].id, node.value))
            else:
                args.append(node)
        return args, kwargs


def pos(node):
    return {'lineno': getattr(node, 'lineno', 0), 'col_offset': 0}

def store(name):
    name.ctx = py.Store(**pos(name))
    return name

def deblock(node):
    if isinstance(node, php.Block):
        return node.nodes
    else:
        return [node]

def build_format(left, right):
    if isinstance(left, basestring):
        pattern, pieces = left.replace('%', '%%'), []
    elif isinstance(left, php.BinaryOp) and left.op == '.':
        pattern, pieces = build_format(left.left, left.right)
    else:
        pattern, pieces = '%s', [left]
    if isinstance(right, basestring):
        pattern += right.replace('%', '%%')
    else:
        pattern += '%s'
        pieces.append(right)
    return pattern, pieces
