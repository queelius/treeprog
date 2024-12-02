import json
from typing import Any, Dict, List, Callable, Set
import AlgoTree as at
from . import utils
import random
# import the lib for deque
from collections import deque
from pprint import pprint

import random

def myrest(nodes, followed):
    return [n for n in nodes if n not in followed]

def mysample(nodes, followed, n):
    candidates = [node for node in nodes if node not in followed]
    return random.sample(candidates, min(n, len(candidates)))

def myslice(nodes, followed, start=0, end=-1, by=1):
    candidates = [node for node in nodes if node not in followed]
    return candidates[start:end:by]

class UttEval:
    def __init__(self, debug=False):
        self.debug = debug
        self.results = {}

        self.pred_fns: Dict[str, Callable] = {
            "eq?": lambda x, y: x == y,
            "true": lambda: True,
            "false": lambda: False,
            "is-leaf?": lambda node: len(node.children) == 0,
            "less?": lambda x, y: x < y,
        }
        self.follow_dirs: Dict[str, Callable] = {
            "up": lambda node: [node.parent] if node.parent else [],
            "down": lambda node: node.children,
            "sideways": lambda node: at.utils.siblings(node),
            "ancestors": lambda node: at.utils.ancestors(node),
            "descendants": lambda node: at.utils.descendants(node),
            "siblings": lambda node: at.utils.siblings(node),
            "children": lambda node: node.children,
            "parent": lambda node: [node.parent] if node.parent else [],
            "all": lambda node: at.utils.all_nodes(node)
        }
        self.selectors: Dict[str, Callable] = {
            "all": lambda nodes, _: nodes,
            "none": lambda _, __: [],
            "rest": myrest,
            "sample": mysample,
            "first": lambda nodes, _: [nodes[0]],
            "last": lambda nodes, followed: [nodes[-1]],
            "nth": lambda nodes, followed, n: [nodes[n]],
            "slice": myslice
        }
        self.select_orders: Dict[str, Callable] = {
            "id": lambda nodes: nodes,
            "reverse": lambda nodes: list(reversed(nodes)),
            "shuffle": lambda nodes: random.shuffle(nodes) or nodes,
            "sort": lambda nodes, key: sorted(nodes, key=key)
        }

    def _create_env(self, node) -> Dict[str, Any]:
        return {
            "$node": node,
            "$num_children": len(node.children),
            "$parent": node.parent,
            "$root": node.root,
            "$depth": at.utils.depth(node),
            "$is_leaf": len(node.children) == 0,
            "$results": self.results,
            "$followed": [],
            "$payload": node.payload,
            #"$siblings": at.utils.siblings(node),
            "$children": node.children,
            #"$ancestors": at.utils.ancestors(node),
            #"$descendants": at.utils.descendants(node)
        }


    def eval(self, node: Any, order: List[Dict[str, Any]]) -> None:

        visited = set() # can only visit a node once
        stack = deque()
        # add the root node to the stack
        stack.append(node)
        self.results = dict()

        # while stack is not empty
        while stack:
            # pop the node from the stack, so that it is a LIFO
            node = stack.pop()
            #print(f"Node: {node}")
            env = self._create_env(node)

            for action in order:
                action_type = next(iter(action))
                #print(f"Action: {action}")
                
                if action_type == "follow":
                    nodes = self._follow(action, env)
                    # extend the stack with the nodes
                    stack.extend(nodes)
                    

                elif action_type == "visit":
                    if node in visited:
                        continue
                    visited.add(node)
                    #print(f"Visited: {visited}")
                    self._visit(action, env)

                elif action_type == "cond":
                    self._cond(action, env)

                elif action_type == "payload-map":
                    self._payload_map(action, env)

                elif action_type == "set!":
                    self._set(action, env)

    def _visit(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        pred = action['visit']
        args = action.get('args', [])
        kwargs = action.get('kwargs', {})
        result_name = action.get('result-name')
        if self.pred_fns[pred](*[self._resolve_arg(arg, env) for arg in args],
                               **{k: self._resolve_arg(v, env) for k, v in kwargs.items()}):
            if result_name:
                if result_name not in self.results:
                    #print("result_name", result_name, "not in results, creating it")
                    self.results[result_name] = []
                    #print("results", self.results)
                self.results[result_name].append(env['$node'])
                #print(self.results)

    def _follow(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        dir = action['follow']
        nodes = self.follow_dirs[dir](env['$node'])
        select_spec = action.get('select', 'all')
        select_order_spec = action.get('select-order', 'id')
        sel_nodes = self._apply_select(select_spec, nodes, env)
        return self._apply_select_order(select_order_spec, sel_nodes)

    def _apply_select(self, select_spec: Any, nodes: List[Any], env: Dict[str, Any]) -> List[Any]:
        if isinstance(select_spec, str):
            return self.selectors[select_spec](nodes, env['$followed'])
        elif isinstance(select_spec, dict):
            selector = self.selectors[select_spec['name']]
            args = select_spec.get('args', [])
            kwargs = select_spec.get('kwargs', {})
            return selector(nodes, env['$followed'], 
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
        pass

    def _payload_map(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        pass

    def _set(self, action: Dict[str, Any], env: Dict[str, Any]) -> None:
        for key, value in action['set!'].items():
            env[key] = self._resolve_arg(value, env)

    def _resolve_arg(self, arg: Any, env: Dict[str, Any]) -> Any:
        if isinstance(arg, str) and arg.startswith('$'):
            return env.get(arg)
        return arg

    def __call__(self, node: Any, order: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        self.eval(node, order)
        return self.results
