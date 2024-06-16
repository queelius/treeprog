from collections import deque
from typing import Any, Callable, List, Dict, Union
import random

def tuple_order(
        node: Any,
        order: List[Dict[str, Any]],
        max_depth: int = float("inf"),
        max_results: int = float("inf"),
        max_visited: int = float("inf"),
        **kwargs) -> List[Tuple[Any, int]]:
    """
    Generalized tree traversal order specified as a list of dictionaries.
    
    The DSL for traversal order is given by the following BNF:
    
    <tuple-order> ::= <order>*
    <order> ::= {queue=<queue-type>} | {visit=<pred-func>} | {dir=up} | {dir=down, select=<select-type>, child-order=<child-order-type>}
    <queue-type> ::= lifo | fifo
    <pred-func> ::= true | false | <regex-on-node-name> | <python-function>
    <select-type> ::= all | left | right | random-subset | slice[<index-slice>] | <python-function>
    <child-order-type> ::= left-to-right | right-to-left | random | <python-function>
    <index-slice> ::= <int> | <int>:<int>
    
    If visit=<pred-func>, there must be a keyword argument matching the key
    <pred-func> which maps to a function of type:
    
        [node] -> bool
    
    If select=<python-function>, there must be a keyword argument matching
    the key <python-function> which maps to a function of type:
    
        [children] -> [selected-children]
    
    If child-order=<python-function>, there must be a keyword argument matching
    the key <custom-order> which maps to a function of type:
    
        [children] -> [permutation-of-children]
    
    We can have multiple custom selectors and custom orders in the same order.
    """
    if not isinstance(order, list) or not all(isinstance(o, dict) for o in order):
        raise ValueError("Order must be a list of dictionaries")

    kwargs = self.populate_defaults(kwargs)

    queue_type = order[0].get("queue")
    if queue_type not in {"lifo", "fifo"}:
        raise ValueError(f"Invalid queue type: {queue_type}")

    if queue_type == "lifo":
        nodes = [(node, 0, iter(order[1:]))]
        next_node = lambda nodes: nodes.pop()
    elif queue_type == "fifo":
        nodes = deque([(node, 0, iter(order[1:]))])
        next_node = lambda nodes: nodes.popleft()

    visited = []
    results = []

    def select_children(children, sel):
        if sel == "all":
            return children
        elif sel == "none":
            return []
        elif sel == "left":
            return children[:len(children)//2]
        elif sel == "right":
            return children[len(children)//2:]
        elif sel.startswith("slice[") and sel.endswith("]"):
            slice_str = sel.split("[")[1].split("]")[0]
            if ":" in slice_str:
                start, end = map(int, slice_str.split(":"))
                return children[start:end]
            else:
                return children[int(slice_str)]
        elif sel == "random-subset":
            random.shuffle(children)
            length = random.randint(0, len(children))
            return children[:length]
        elif callable(sel):
            return sel(children)
        else:
            raise ValueError(f"Invalid select: {sel}")

    def order_children(children, order):
        if order == "left-to-right":
            return children
        elif order == "right-to-left":
            return list(reversed(children))
        elif order == "random":
            random.shuffle(children)
            return children
        elif callable(order):
            return order(children)
        else:
            raise ValueError(f"Invalid child-order: {order}")

    while nodes:
        node, depth, order_iter = next_node(nodes)
        if depth > max_depth or node in visited:
            continue

        action = next(order_iter, None)
        while action:
            if "visit" in action:
                visit_pred = action["visit"]
                visit_func = kwargs.get(visit_pred, lambda n: True)
                visited.append(node)
                if visit_func(node):
                    results.append((node, depth))
                    if len(results) >= max_results:
                        return results
                if len(visited) >= max_visited:
                    return results
            elif "dir" in action:
                dir = action["dir"]
                if dir == "down" and hasattr(node, "children"):
                    children = list(node.children)
                    sel = next(order_iter)
                    if "select" not in sel:
                        raise ValueError(f"Expected 'select' action after 'dir=down', got: {sel}")
                    sel = sel["select"]
                    children = select_children(children, sel)
                    child_order = next(order_iter)
                    if "child-order" not in child_order:
                        raise ValueError(f"Expected 'child-order' action after 'select', got: {child_order}")
                    child_order = child_order["child-order"]
                    children = order_children(children, child_order)
                    nodes.extend((child, depth + 1, iter(order[1:])) for child in children)
                elif dir == "up" and hasattr(node, "parent") and node.parent is not None:
                    nodes.append((node.parent, depth + 1, iter(order[1:])))
            else:
                raise ValueError(f"Invalid action in order: {action}")
            action = next(order_iter, None)

    return results
