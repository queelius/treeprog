import json
from typing import Any, Dict, List, Callable, Set
import AlgoTree as at
from . import utils
import random
from pprint import pprint

class UttEval:
    def __init__(self, debug=False):
        self.debug = debug
        self.visited: Set[Any] = set()
        self.followed: Set[Any] = set()
        self.results: Dict[str, List[Any]] = dict()

        self.dispatch_table: Dict[str, Callable] = {
            "visit": self._visit,
            "follow": self._follow,
            "cond": self._cond,
            "payload-map": self._payload_map,
            "set!": self._set
        }
        self.pred_fns: Dict[str, Callable] = {
            "eq?": lambda x, y: x == y,
            "true": lambda: True,
            "false": lambda: False,
            "is-leaf?": lambda node: len(node.children) == 0,
            "less?": lambda x, y: x < y,
        }
        self.follow_dirs: Dict[str, Callable] = {
            "all": lambda node: at.utils.all_nodes(node),

            "none": lambda node: [],

            "up": lambda node: [node.parent] if node.parent else [],
            "parent": lambda node: [node.parent] if node.parent else [],

            "down": lambda node: node.children,
            "children": lambda node: node.children,

            "sideways": lambda node: at.utils.siblings(node),
            "siblings": lambda node: at.utils.siblings(node),

            "ancestors": lambda node: at.utils.ancestors(node),
            
            "descendants": lambda node: at.utils.descendants(node),

            "sample": lambda node, k: random.sample(at.utils.all_nodes(node), k)
        }

        # lambda nodes, visited, followed: expression
        self.selectors: Dict[str, Callable] = {
            "all": lambda nodes, _, __: nodes,
            "none": lambda _, __, ___: [],
            "rest": utils.rest_sel,
            "sample": utils.sample_sel,
            "first": lambda nodes, _, __: [nodes[0]],
            "last": lambda nodes, _, __: [nodes[-1]],
            "nth": lambda nodes, visited, followed, n: [nodes[n]],
            "slice": utils.slice_sel
        }
        self.select_orders: Dict[str, Callable] = {
            "id": lambda nodes: nodes,
            "reverse": lambda nodes: list(reversed(nodes)),
            "shuffle": lambda nodes: random.shuffle(nodes) or nodes,
            "sort": lambda nodes, key: sorted(nodes, key=key),
            "payload": lambda nodes: sorted(nodes, key=lambda n: n.payload),
            "name": lambda nodes: sorted(nodes, key=lambda n: n.name),
            "depth": lambda nodes: sorted(nodes, key=lambda n: at.utils.depth(n)),
            "num_children": lambda nodes: sorted(nodes, key=lambda n: len(n.children)),
            "num_descendants": lambda nodes: sorted(nodes, key=lambda n: len(at.utils.descendants(n))),
            "num_ancestors": lambda nodes: sorted(nodes, key=lambda n: len(at.utils.ancestors(n))),
            "num_siblings": lambda nodes: sorted(nodes, key=lambda n: len(at.utils.siblings(n))),
        }   

    def eval(self, node: Any, order: List[Dict[str, Any]], visited: Set[Any], followed: Set[Any]) -> None:
        env = {
            "$node": node,
            "$num_children": len(node.children),
            "$parent": node.parent,
            "$root": node.root,
            "$depth": at.utils.depth(node),
            "$is_leaf": len(node.children) == 0,
            "$order": order,
            "$results": self.results,
            "$visited": visited,
            "$followed": followed,
            "$payload": node.payload,
            "$siblings": at.utils.siblings(node),
            "$children": node.children,
            "$ancestors": at.utils.ancestors(node),
            "$descendants": at.utils.descendants(node)
        }

        if self.debug:
            print(f"Node: {node}")
            print(f"Env: {env}")
            print(f"Order: {order}")

        for action in order:
            if self.debug:
                print(f"Action: {action}")
            action_type = next(iter(action))
            self.dispatch_table[action_type](action, env)

            if self.debug:
                print(f"Visited: {visited}")
                print(f"Followed: {followed}")

            #if node in visited:
            #    break # stop processing further actions if the node has been visited


    def _visit(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        node = env['$node']
        if node in env['$visited']:
            return
        env['$visited'].add(node)
        pred = action['visit']
        args = action.get('args', [])
        kwargs = action.get('kwargs', {})
        result_name = action.get('result-name')
        if self.pred_fns[pred](*[self._resolve_arg(arg, env) for arg in args],
                               **{k: self._resolve_arg(v, env) for k, v in kwargs.items()}):
            if result_name:
                if result_name not in self.results:
                    self.results[result_name] = []
                self.results[result_name].append(node)

    def _follow(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        dir = action['follow']
        nodes = self.follow_dirs[dir](env['$node'])
        
        select_spec = action.get('select', 'all')
        select_order_spec = action.get('select-order', 'id')
        
        sel_nodes = self._apply_select(select_spec, nodes, env)
        ordered_nodes = self._apply_select_order(select_order_spec, sel_nodes)
        
        for node in ordered_nodes:
            if node not in env['$followed']:
                env['$followed'].add(node)
                self.eval(node, env['$order'], env['$visited'], env['$followed'])

    def _apply_select(self, select_spec: Any, nodes: List[Any], env: Dict[str, Any]) -> List[Any]:
        if isinstance(select_spec, str):
            return self.selectors[select_spec](nodes, env['$visited'], env['$followed'])
        elif isinstance(select_spec, dict):
            selector = self.selectors[select_spec['name']]
            args = select_spec.get('args', [])
            kwargs = select_spec.get('kwargs', {})
            return selector(nodes, env['$visited'], env['$followed'], 
                            *[self._resolve_arg(arg, env) for arg in args],
                            **{k: self._resolve_arg(v, env) for k, v in kwargs.items()})
        else:
            raise ValueError(f"Invalid select specification: {select_spec}")

    def _apply_select_order(self, select_order_spec: Any, nodes: List[Any]) -> List[Any]:
        if isinstance(select_order_spec, str):
            return self.select_orders[select_order_spec](nodes)
        elif isinstance(select_order_spec, dict):
            order_func = self.select_orders[select_order_spec['name']]
            args = select_order_spec.get('args', [])
            kwargs = select_order_spec.get('kwargs', {})
            return order_func(nodes, *args, **kwargs)
        else:
            raise ValueError(f"Invalid select-order specification: {select_order_spec}")

    def _cond(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        for case in action['cond']:
            pred = case['pred']
            args = case.get('args', [])
            kwargs = case.get('kwargs', {})

            some_args = [self._resolve_arg(arg, env) for arg in args]
            some_kwargs = {k: self._resolve_arg(v, env) for k, v in kwargs.items()}

            if self.debug:
                print(f"args: {args}")
                print(f"resolved args: {some_args}")
                print(f"kwargs: {kwargs}")
                print(f"resolved Kwargs: {some_kwargs}")
            if self.pred_fns[pred](*some_args, **some_kwargs):
                if self.debug:
                    print(f"Pred: {pred} passed")
                    print(f"Processnig order for case: {case['order']}")

                for action in case['order']:
                    if self.debug:
                        print(f"Action: {action}")
                    action_type = next(iter(action))
                    self.dispatch_table[action_type](action, env)
                break

    def _payload_map(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        # Implement payload mapping logic here
        pass

    def _set(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        for key, value in action['set!'].items():
            env[key] = self._resolve_arg(value, env)

    def _resolve_arg(self, arg: Any, env: Dict[str, Any]) -> Any:
        if isinstance(arg, str) and arg.startswith('$'):
            return env.get(arg)
        return arg

    def __call__(self, node: Any, order: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        self.results = {}
        visited = set()
        followed = set()
        self.eval(node, order, visited, followed)
        return self.results