import json
from typing import Any, Dict, List, Callable, Set
import AlgoTree as at
import random

class UttEval:
    def __init__(self, debug=False):
        self.debug = debug
        self.visited: Set[Any] = set()
        self.followed: Set[Any] = set()
        self.results: Dict[str, List[Any]] = dict()

        self.dispatch_table: Dict[str, Callable] = {
            "visit": self._visit,
            "follow": self._follow,
        }
        self.pred_fns: Dict[str, Callable] = {
            "eq?": lambda x, y: x == y,
            "true": lambda: True,
            "false": lambda: False,
            "is-leaf?": lambda node: len(node.children) == 0
        }
        self.follow_dirs: Dict[str, Callable] = {
            "up": lambda node: [node.parent] if node.parent else [],
            "down": lambda node: node.children,
            "sideways": lambda node: at.utils.siblings(node)
        }
        self.selectors: Dict[str, Callable] = {
            "all": lambda nodes, visited, followed: nodes,
            "none": lambda nodes, visited, followed: [],
            "rest": lambda nodes, visited, followed: [n for n in nodes if n not in followed],
            "rand": lambda nodes, visited, followed: [random.choice([n for n in nodes if n not in followed])] if nodes else []
        }
        self.select_orders: Dict[str, Callable] = {
            "id": lambda nodes: nodes,
            "reverse": lambda nodes: list(reversed(nodes)),
            "shuffle": lambda nodes: random.shuffle(nodes) or nodes
        }

    def eval(self, node: Any, order: List[Dict[str, Any]], visited: Set[Any], followed: Set[Any]) -> None:
        env = {
            "$node": node,
            "$num_children": len(node.children),
            "$parent": node.parent,
            "$root": node.root,
            "$depth": at.utils.depth(node),
            "$is_leaf": len(node.children) == 0,
            "$is_root": node.parent is None,
            "$order": order,
            "$results": self.results,
            "$visited": visited,
            "$followed": followed,
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
        sel = action.get('select', 'all')
        sel_order = action.get('select-order', 'id')
        sel_nodes = self.selectors[sel](nodes, env['$visited'], env['$followed'])
        ordered_nodes = self.select_orders[sel_order](sel_nodes)
        for node in ordered_nodes:
            if node not in env['$followed']:
                env['$followed'].add(node)
                self.eval(node, env['$order'], env['$visited'], env['$followed'])

    def _resolve_arg(self, arg: Any, env: Dict[str, Any]) -> Any:
        if isinstance(arg, str) and arg.startswith('$'):
            return env.get(arg[1:])
        return arg

    def __call__(self, node: Any, order: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        self.results = {}
        visited = set()
        followed = set()
        self.eval(node, order, visited, followed)
        return self.results