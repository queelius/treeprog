from typing import Any, Callable, List, Dict, Tuple, Optional, Union
import random
from collections import deque
from pprint import pprint

class lifo_queue:
    """
    LIFO queue (stack) implementation using a deque.
    """
    def __init__(self):
        self._stack = deque()

    def push(self, item):
        self._stack.append(item)

    def pop(self):
        if not self.is_empty():
            return self._stack.pop()
        else:
            raise IndexError("pop from empty stack")

    def is_empty(self):
        return len(self._stack) == 0        

class fifo_queue:
    def __init__(self):
        self._queue = deque()

    def push(self, item):
        self._queue.append(item)

    def pop(self):
        if not self.is_empty():
            return self._queue.popleft()
        else:
            raise IndexError("pop from empty queue")
        
    def is_empty(self):
        return len(self._queue) == 0

class pqueue:
    """
    Priority queue implementation using a list.
    """
    def __init__(self, key=lambda x: x):
        self.queue = []
        self.key = key

    def push(self, item):
        self.queue.append(item)
        self.queue.sort(key=self.key)

    def pop(self):
        return self.queue.pop(0)

    def is_empty(self):
        return len(self.queue) == 0

class Dispatcher:
    def __init__(self):
        self.funcs = {}
        self._default = None
        self.register_defaults()

    def register_defaults(self):
        pass

    def register(self, name, func):
        if name in self.funcs:
            raise ValueError(f"Function name already registered: {name}")
        self.funcs[name] = func

    def unregister(self, name):
        if name not in self.funcs:
            raise ValueError(f"Function name not registered: {name}")
        del self.funcs[name]

    @property
    def default(self, name):
        if self._default is not None:
            return self.funcs[self.default]
        elif len(self.funcs) > 0:
            return self.funcs[next(iter(self.funcs))]
        else:
            return None
        
    @default.setter
    def default(self, name):
        if name not in self.funcs:
            raise ValueError(f"Function name not registered: {name}")
        self._default = name

    def __contains__(self, name):
        return name in self.funcs
    
    def __iter__(self):
        return iter(self.funcs)
    
    def __len__(self):
        return len(self.funcs)
    
    def dispatch(self, name: Optional[str] = None, *args, **kwargs):

        if name is None:
            return self.default(*args, **kwargs)
        elif name in self.funcs:
            return self.funcs[name](*args, **kwargs)
    
    def __call__(self, name: Optional[str] = None, *args, **kwargs):
        return self.dispatch(name, *args, **kwargs)
    
    def get(self, name, default=None):
        return self.funcs.get(name, None)
    
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
        self.register('lifo', lifo_queue)
        self.register('fifo', fifo_queue)
        self.register('pq', pqueue)

class TreeTraversal:
    """
    Tree-traveral algorithm that allows for custom traversal orders and actions.
    """

    def __init__(self,
                 order: Optional[List[Dict[str, Any]]] = None,
                 max_depth: int = float("inf"),
                 max_results: int = float("inf"),
                 max_visited: int = float("inf"),
                 debug: bool = False):

        if not isinstance(order, list) or not all(isinstance(o, dict) for o in order):
            raise ValueError("`order` must be a list of dictionaries")
        
        self.order = order
        self.max_depth = max_depth
        self.max_results = max_results
        self.max_visited = max_visited
        self.debug = debug

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
        queue = None
        if queue_type is None:
            queue = lifo_queue()
        else:
            idx += 1
            if queue_type in self.dispatcher['queue']:
                queue_dispatcher = self.dispatcher['queue']
                kwargs = self.order[idx].get("kwargs", {})
                args = self.order[idx].get("args", [])
                queue = queue_dispatcher(*args, **kwargs)
            elif hasattr(queue_type, 'push') and hasattr(queue_type, 'pop'):
                queue = queue_type
            else:
                raise ValueError(f"Invalid queue type: {queue_type}")
            
        if self.debug:
            print(f"Queue: {queue}, type: {type(queue)}")
        
        initial = (node, 0, iter(self.order[idx:]))
        if self.debug:
            print(f"Initial node: {node}")

        queue.push(initial)
        visited = []

        max_depth = self.max_depth
        if 'max_depth' in kwargs:
            max_depth = kwargs['max_depth']
            #del kwargs['max_depth']

        max_results = self.max_results
        if 'max_results' in kwargs:
            max_results = kwargs['max_results']
            #del kwargs['max_results']

        max_visited = self.max_visited
        if 'max_visited' in kwargs:
            max_visited = kwargs['max_visited']
            #del kwargs['max_visited']

        order = self.order
        if 'order' in kwargs:
            order = kwargs['order']
            #del kwargs['order']

        if self.debug:
            print(f"max_depth: {max_depth}")
            print(f"max_results: {max_results}")
            print(f"max_visited: {max_visited}")
            print(f"order: {order}")
            print("-" * 40)

        while queue:
            node, depth, order_iter = queue.pop()

            if self.debug:
                print("processing node:")
                print("- at node:", node)
                print("- depth:", depth)
                print("- order_iter:", order_iter)

            if depth > max_depth or node in visited:
                continue

            results = [] # {}
            action = next(order_iter, None)
            selected_nodes = []
            while action:
                if self.debug:
                    print(f"action: {action}")

                if "visit" in action:
                    if self.debug:
                        print(f"visiting node: {node}")
                    visit_func_name = action["visit"]
                    if self.debug:
                        print(f"visit_func_name: {visit_func_name}")
                    visit_func = self.dispatcher['visit'].get(visit_func_name, lambda node: False)
                    if self.debug:
                        print(f"visit_func: {visit_func}")
                    visited.append(node)
                    if self.debug:
                        print(f"visited: {visited}")
                    if visit_func(node):
                        results.append((node, depth))
                        print(f"results: {results}")
                        if len(results) >= max_results:
                            if self.debug:
                                print("max_results reached")
                            return results
                    if len(visited) >= max_visited:
                        return results
                elif "dir" in action:
                    if self.debug:
                        print(f"following dir: {action['dir']}")
                    dir = action["dir"]
                    follow = self.dispatcher['follower'].get(dir, lambda node: [])
                    if self.debug:
                        print(f"follow: {follow}")
                    next_nodes = follow(node)
                    if self.debug:
                        print("next_nodes:")
                        for n in next_nodes:
                            print("- ", n)
            
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

