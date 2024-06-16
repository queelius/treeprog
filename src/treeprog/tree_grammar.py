from collections import deque
from typing import Any, Callable, List, Dict, Tuple
import random
from collections import deque

class lifo(deque):
    def __init__(self):
        super().__init__()

    def push(self, item):
        self.append(item)

    def pop(self):
        return self.pop()

class fifo(deque):
    def __init__(self):
        super().__init__()

    def push(self, item):
        self.append(item)

    def pop(self):
        return self.popleft()

class pqueue:
    def __init__(self, key=lambda x: x):
        self.queue = []
        self.key = key

    def push(self, item):
        self.queue.append(item)
        self.queue.sort(key=self.key)

    def pop(self):
        return self.queue.pop(0)

class Dispatcher:
    def __init__(self):
        self.funcs = {}
        self.register_defaults()

    def register_defaults(self):
        pass

    def register(self, name, func):
        if name in self.funcs:
            raise ValueError(f"Function name already registered: {name}")
        self.funcs[name] = func

    def dispatch(self, name, *args, **kwargs):
        if name not in self.funcs:
            raise ValueError(f"Invalid function name: {name}")
        return self.funcs[name](*args, **kwargs)
    
    def __call__(self, name, *args, **kwargs):
        return self.dispatch(name, *args, **kwargs)
    
    def __getitem__(self, name):
        return self.funcs[name]
    
    def __setitem__(self, name, func):
        self.register(name, func)


class VisitDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()

    def register_defaults(self):
        self.register('all', lambda _: True)
        self.register('none', lambda _: False)
        self.register('is-leaf', lambda node: not hasattr(node, 'children') or len(node.children) == 0)
        self.register('is-root', lambda node: not hasattr(node, 'parent') or node.parent is None)
        self.register('is-not-root', lambda node: hasattr(node, 'parent') and node.parent is not None)
        self.register('is-internal-node', lambda node: hasattr(node, 'children') and len(node.children) > 0)
        self.register('flip', lambda _: random.choice([True, False]))

class SelectorDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()

    def register_defaults(self):
        self.register('all', lambda nodes: nodes)
        self.register('none', lambda _: [])
        self.register('left', lambda nodes: nodes[:len(nodes) // 2])
        self.register('right', lambda nodes: nodes[len(nodes) // 2:])
        self.register('random', lambda nodes: random.sample(nodes, random.randint(0, len(nodes))))

class OrderDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()

    def register_defaults(self):
        self.register('identity', lambda nodes: nodes)
        self.register('reverse', lambda nodes: reversed(nodes))
        self.register('shuffle', lambda nodes: random.shuffle(nodes))

class FollowerDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()

    def register_defaults(self):
        self.register('down', lambda node: node.children if hasattr(node, 'children') else [])
        self.register('up', lambda node: [node.parent] if hasattr(node, 'parent') and node.parent is not None else [])
        self.register('sideways', lambda node: [sibling for sibling in node.parent.children if sibling != node] if hasattr(node, 'parent') and node.parent is not None else [])

class QueueDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()

    def register_defaults(self):
        self.register('lifo', lifo)
        self.register('fifo', fifo)
        self.register('pq', pqueue)

class TreeTraversal:
    """
    Tree-traveral algorithm that allows for custom traversal orders and actions.

    The DSL for traversal order is given by the following BNF:
    
    <tuple-order> ::= [<order> (, <order>)*]
    <order> ::= <queue> |  | {"dir": "up"} | {dir=down, select=<select-type>, child-order=<child-order-type>}
    <queue> ::= {"queue": <queue-type>(, args=[<args>])?(, kwargs={)}
    <queue-type> ::= lifo | fifo
    <pred-func> ::= true | false | <regex-on-node-name> | <python-function>
    <select-type> ::= all | left | right | random-subset | slice[<index-slice>] | <python-function>
    <node-order> ::= {"node-order": <node-order-type> <kwargs>*}
    <node-order-type> ::= "left-to-right" | "right-to-left" | "random" | <python-function>
    <index-slice> ::= <int> | <int>:<int>
    <kwargs> ::= (, <key>: <value>)*
    <value> ::= <int> | <string> | <python-function>
    <key> ::= <string>

    
    If visit=<pred-func>, there must be a keyword argument matching the key
    <pred-func> which} maps to a function of type:
    
        [node] -> bool
    
    If select=<python-function>, there must be a keyword argument matching
    the key <python-function> which maps to a function of type:
    
        [nodes] -> [selected-nodes]
    
    If child-order=<python-function>, there must be a keyword argument matching
    the key <custom-order> which maps to a function of type:
    
        [nodes] -> [permutations(nodes)]
    
    We can have multiple custom selectors and custom orders in the same order.
    """

    def __init__(self,
                 order: List[Dict[str, Any]] | None = None,
                 max_depth: int = float("inf"),
                 max_results: int = float("inf"),
                 max_visited: int = float("inf")):

        if not isinstance(order, list) or not all(isinstance(o, dict) for o in order):
            raise ValueError("`order` must be a list of dictionaries")
        
        self.order = order
        self.max_depth = max_depth
        self.max_results = max_results
        self.max_visited = max_visited

        self.dispatcher = {
            'queue': QueueDispatcher(),
            'visit': VisitDispatcher(),
            'selector': SelectorDispatcher(),
            'order': OrderDispatcher(),
            'follower': FollowerDispatcher()
        }

    def set_dispatcher(self, type: str, dispatcher: Dispatcher):
        if type not in self.dispatcher:
            raise ValueError(f"Invalid dispatcher type: {type}")
        self.dispatcher[type] = dispatcher

    def register(self, type: str, name: str, func: Callable):
        if type not in self.dispatcher:
            raise ValueError(f"Invalid dispatcher type: {type}")
        if name in self.dispatcher[type]:
            raise ValueError(f"Function name already registered: {name}")
        if not callable(func):
            raise ValueError(f"Expected a callable function, got: {func}")
        self.dispatcher[type][name] = func

    def __call__(
            self,
            node: Any,
            **kwargs) -> List[Tuple[Any, int]]:

        idx = 0
        queue_type = self.order[idx].get("queue", None)
        if queue_type is None:
            queue = lifo()
        else:
            idx += 1
            if queue_type in self.dispatcher['queue']:
                queue_dispatcher = self.dispatcher['queue']
                kwargs = self.order[0].get("kwargs", {})
                args = self.order[0].get("args", [])
                queue = queue_dispatcher(*args, **kwargs)
            elif hasattr(queue_type, 'push') and hasattr(queue_type, 'pop'):
                queue = queue_type
            else:
                raise ValueError(f"Invalid queue type: {queue_type}")
        
        queue.push((node, 0, iter(self.order[1:])))
        visited = []

        max_depth = self.max_depth
        if 'max_depth' in kwargs:
            max_depth = kwargs['max_depth']
            del kwargs['max_depth']

        max_results = self.max_results
        if 'max_results' in kwargs:
            max_results = kwargs['max_results']
            del kwargs['max_results']

        max_visited = self.max_visited
        if 'max_visited' in kwargs:
            max_visited = kwargs['max_visited']
            del kwargs['max_visited']

        order = self.order
        if 'order' in kwargs:
            order = kwargs['order']
            del kwargs['order']

        while queue:
            node, depth, order_iter = queue.pop()
            if depth > max_depth or node in visited:
                continue

            results = {}
            action = next(order_iter, None)
            selected_nodes = []
            while action:
                if "visit" in action:
                    visit_func_name = action["visit"]
                    visit_func = self.dispatcher['visit'].get(visit_func_name, lambda node: False)
                    visited.append(node)
                    if visit_func(node):
                        results.append((node, depth))
                        if len(results) >= max_results:
                            return results
                    if len(visited) >= max_visited:
                        return results
                elif "dir" in action:
                    dir = action["dir"]
                    follow = self.dispatcher['follower'].get(dir, lambda node: [])
                    next_nodes = follow(node)
            
                    sel_action = next(order_iter)
                    if "select" not in sel_action:
                        raise ValueError(f"Expected 'select' action after 'dir={dir}', got: {sel_action}")
                    elif isinstance(sel_action['select'], str):
                        if sel_action['select'] == 'rest':
                            sel = lambda nodes: [n for n in nodes if n not in selected_nodes]
                        elif sel_action in self.dispatcher['selector']:
                            sel = self.dispatcher['selector'][sel_action["select"]]
                        else:
                            raise ValueError(f"Invalid selector: {sel_action['select']}")
                    elif callable(sel_action['select']):
                        sel = sel_action['select']
                    else:
                        raise ValueError(f"Invalid selector: {sel_action['select']}")
                    selected = sel(next_nodes)
                    selected_nodes.extend(selected)

                    sel_order_action = next(order_iter)
                    if "selected-order" not in sel_order_action:
                        raise ValueError(f"Expected 'selected-order' action after 'select', got: {sel_order_action}")
                    elif isinstance(sel_order_action, str):
                        if sel_order_action["selected-order"] in self.dispatcher['selected-order']:
                            sel_order = self.dispatcher['selected-order'][sel_order_action["selected-order"]]
                        else:
                            raise ValueError(f"Invalid selected-order: {sel_order_action['selected-order']}")
                    elif callable(sel_order_action["selected-order"]):
                        sel_order = sel_order_action["selected-order"]
                    else:
                        raise ValueError(f"Invalid selected-order: {sel_order_action['selected-order']}")
                    next_nodes = sel_order(next_nodes)

                    queue.extend((next_node, depth + 1, iter(order[1:])) for next_node in next_nodes)
                else:
                    raise ValueError(f"Invalid action in order: {action}")
                action = next(order_iter, None)

        return results

