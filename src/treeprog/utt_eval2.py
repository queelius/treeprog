import json
from typing import Any, Dict, List, Callable, Set
from typing import Any, Dict, List, Callable
import AlgoTree as at
import random

class UttEval:
    def __init__(self, debug = False):
        self.debug = debug
        self.visited: Set[Any] = set()
        self.results: Dict[str, List[Any]] = dict()

        self.dispatch_table: Dict[str, Callable] = {
            "visit": self._visit,
            #"payload-map": self._payload_map,
            #"cond": self._cond,
            "follow": self._follow,
            #"set!": self._set
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
            "all": lambda nodes: nodes,
            "none": lambda _: [],
            "rest": lambda nodes: nodes[1:], # incorrect, we need to keep track
                                             # of how many nodes in the current
                                             # order we've previously selected
            "rand": lambda nodes: random.choice(nodes) if nodes else []
        }
        self.select_orders: Dict[str, Callable] = {
            "id": lambda nodes: nodes,
            "reverse": lambda nodes: list(reversed(nodes)),
            "shuffle": lambda nodes: random.shuffle(nodes) or nodes
        }
        #self.payload_fns: Dict[str, Callable] = {
        #    "id": lambda x: x,
        #    "proj": lambda x, key: x.get(key) if isinstance(x, dict) else getattr(x, key, None),
        #    "rename": lambda x, old_key, new_key: {new_key if k == old_key else k: v for k, v in x.items()} if isinstance(x, dict) else x
        #}

    def eval(self, node: Any, order: List[Dict[str, Any]]) -> None:
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
            "$visited": self.visited,
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
        # check if $node has already been visited. visited is a set of nodes
        if env['$node'] in self.visited:
            return
        self.visited.add(env['$node'])
        pred = action['visit']
        args = action.get('args', [])
        kwargs = action.get('kwargs', {})
        result_name = action.get('result-name')
        if self.pred_fns[pred](*[self._resolve_arg(arg, env) for arg in args],
                               **{k: self._resolve_arg(v, env) for k, v in kwargs.items()}):
            if result_name:
                if result_name not in self.results:
                    self.results[result_name] = []
                self.results[result_name].append(env['$node'])

    def _follow(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        dir = action['follow']
        nodes = self.follow_dirs[dir](env['$node'])
        sel = action.get('select', 'all')
        sel_order = action.get('select-order', 'id')
        sel_nodes = self.selectors[sel](nodes)
        ordered_nodes = self.select_orders[sel_order](sel_nodes)
        for node in ordered_nodes:
            if env['$node'] in self.visited:
                continue
            self.eval(node, env['$order'])

    def _resolve_arg(self, arg: Any, env: Dict[str, Any]) -> Any:
        if isinstance(arg, str) and arg.startswith('$'):
            return env.get(arg[1:])
        return arg

    def __call__(self, node: Any, order: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        self.results: Dict[str, List[Any]] = {}
        self.visited: Set[Any] = set()
        self.eval(node, order)
        return self.results

    # def _set(self, action: Dict[str, Any]) -> None:
    #     for key, value in action['set!'].items():
    #         self.environment[key] = self._resolve_arg(value)

    # def _payload_map(self, action: Dict[str, Any]) -> None:
    #     fn = action['payload-map']
    #     args = action.get('args', [])
    #     kwargs = action.get('kwargs', {})
    #     node = self.environment['$node']
    #     new_payload = self.payload_fns[fn](node, *[self._resolve_arg(arg) for arg in args], **{k: self._resolve_arg(v) for k, v in kwargs.items()})
    #     if hasattr(node, 'payload'):
    #         node.payload = new_payload
    #     elif isinstance(node, dict):
    #         node.update(new_payload)

    # def _cond(self, action: Dict[str, Any]) -> None:
    #     cases = action['cond']
    #     for case in cases:
    #         case_pred = case['pred']
    #         case_args = case.get('args', [])
    #         case_kwargs = case.get('kwargs', {})
    #         if self.pred_fns[case_pred](*[self._resolve_arg(arg) for arg in case_args], **{k: self._resolve_arg(v) for k, v in case_kwargs.items()}):
    #             self.eval(self.environment['$node'], case['order'])
    #             break

