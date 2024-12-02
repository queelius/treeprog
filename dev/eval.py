# Define the dispatcher and environment classes
class Dispatcher:
    def __init__(self):
        self.registry = {}

    def register(self, name, func, expected_args=None):
        self.registry[name] = (func, expected_args)

    def get(self, name):
        return self.registry.get(name)

class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def set(self, key, value):
        self.vars[key] = value

    def get(self, key):
        if key in self.vars:
            return self.vars[key]
        elif self.parent:
            return self.parent.get(key)
        else:
            return None

    def extend(self):
        return Environment(self)

class SimplifiedTreeTraversal:
    def __init__(self, dispatchers=None):
        self.dispatcher = dispatchers if dispatchers is not None else {
            'visit': Dispatcher(),
            'payload-map': Dispatcher(),
            'follow': Dispatcher()
        }
        self.max_results = float("inf")

    def eval(self, node, program=None, depth=0, env=None):
        if program is None:
            return {}

        if env is None:
            env = Environment()

        results = {}

        for action in program:
            if "visit" in action:
                self.eval_visit_action(action, node, results, depth, env)
            elif "payload-map" in action:
                node = self.eval_payload_map_action(action, node, env)
            elif "cond" in action:
                cond_results = self.eval_cond_action(action, node, depth, env)
                self.merge_results(results, cond_results)
            elif "follow" in action:
                follow_results = self.eval_follow_action(action, node, depth, env, program)
                self.merge_results(results, follow_results)
            else:
                raise ValueError(f"Invalid action in program: {action}")

            if any(len(res) >= self.max_results for res in results.values()):
                return results

        return results

    def eval_visit_action(self, action, node, results, depth, env):
        visit_func_name = action["visit"]
        result_name = action.get("result-name", visit_func_name)
        visit_func, _ = self.dispatcher['visit'].get(visit_func_name)
        if visit_func(node, env):
            if result_name not in results:
                results[result_name] = []
            results[result_name].append((node, depth))
            print(f"Visited node with value: {node['value']} at depth {depth}")

    def eval_payload_map_action(self, action, node, env):
        map_func_name = action["payload-map"]
        map_func, _ = self.dispatcher['payload-map'].get(map_func_name)
        new_node = map_func(node, env)
        print(f"Payload updated for node with value: {node['value']}")
        return new_node

    def eval_cond_action(self, action, node, depth, env):
        for cond in action["cond"]:
            pred_func, _ = self.dispatcher['visit'].get(cond["pred"])
            if pred_func(node, env):
                print(f"Condition met for node with value: {node['value']}")
                return self.eval(node, cond["order"], depth, env)
        return {}

    def eval_follow_action(self, action, node, depth, env, program):
        follow_func, _ = self.dispatcher['follow'].get(action["follow"])
        next_nodes = follow_func(node, env)
        follow_results = {}
        for next_node in next_nodes:
            sub_results = self.eval(next_node, program, depth + 1, env)
            self.merge_results(follow_results, sub_results)
        return follow_results

    def merge_results(self, results, new_results):
        for key, value in new_results.items():
            if key not in results:
                results[key] = value
            else:
                results[key].extend(value)

# Example dispatchers
def some_predicate(node, env):
    return True

def another_predicate(node, env):
    return node.get('value', None) == 'target'

def some_func(node, env):
    node['payload'] = 'updated'
    return node

def update_payload1(node, env):
    node['payload'] = 'branch1'
    return node

def update_payload2(node, env):
    node['payload'] = 'branch2'
    return node

def update_payload3(node, env):
    node['payload'] = 'branch3'
    return node

def follow_down(node, env):
    return node.get('children', [])

# Register functions with dispatchers
dispatchers = {
    'visit': Dispatcher(),
    'payload-map': Dispatcher(),
    'follow': Dispatcher()
}

dispatchers['visit'].register('some_predicate', some_predicate)
dispatchers['visit'].register('another_predicate', another_predicate)
dispatchers['payload-map'].register('some_func', some_func)
dispatchers['payload-map'].register('update_payload1', update_payload1)
dispatchers['payload-map'].register('update_payload2', update_payload2)
dispatchers['payload-map'].register('update_payload3', update_payload3)
dispatchers['follow'].register('down', follow_down)

# More complex sample node structure
complex_tree = {
    'value': 'root',
    'children': [
        {'value': 'child1', 'children': [
            {'value': 'grandchild1', 'children': [
                {'value': 'great-grandchild1', 'children': []},
                {'value': 'great-grandchild2', 'children': []}
            ]},
            {'value': 'grandchild2', 'children': []}
        ]},
        {'value': 'child2', 'children': [
            {'value': 'grandchild3', 'children': []},
            {'value': 'grandchild4', 'children': [
                {'value': 'target', 'children': []}
            ]}
        ]},
        {'value': 'child3', 'children': [
            {'value': 'grandchild5', 'children': []}
        ]}
    ]
}

# Updated sample program to evaluate
complex_program = [
    { "visit": "some_predicate", "result-name": "pre-order" },
    { "payload-map": "some_func" },
    { "cond": [
        { "pred": "some_predicate", "order": [
            { "visit": "another_predicate", "result-name": "branch1" },
            { "payload-map": "update_payload1" },
            { "follow": "down" }
        ]},
        { "pred": "another_predicate", "order": [
            { "visit": "some_predicate", "result-name": "branch2" },
            { "payload-map": "update_payload2" },
            { "follow": "down" }
        ]},
        { "pred": "some_predicate", "order": [
            { "visit": "some_predicate", "result-name": "branch3" },
            { "payload-map": "update_payload3" },
            { "follow": "down" }
        ]}
    ]}
]

# Evaluate the complex program on the complex tree
tree_traversal = SimplifiedTreeTraversal(dispatchers=dispatchers)
results = tree_traversal.eval(complex_tree, complex_program)

# Convert results to DataFrame
import pandas as pd
results_list = []
for result_name, nodes in results.items():
    for node, depth in nodes:
        results_list.append({
            'result_name': result_name,
            'node_value': node['value'],
            'payload': node.get('payload', None),
            'depth': depth
        })

results_df = pd.DataFrame(results_list)

# Display DataFrame to user
import ace_tools as tools
tools.display_dataframe_to_user(name="Traversal Results", dataframe=results_df)
results_df
