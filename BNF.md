# `dfs-tree-prog`

## Introduction

There are many ways to traverse a tree, e.g., pre-order, post-order, in-order,
level-order, etc. Here, we focus on a domain-specific language (DSL) that
allows for different kinds of recursive tree traversals defined by simple 
depth-first search (DFS) traversal orders. For binary trees, this is essentially
pre-order, in-order, and post-order traversals. For general trees, this is
a depth-first search (DFS) traversal with a way of selecting which children
of a node to visit before the current node is visited and which children to
visit after the current node is visited.

If a more general traversal order is needed, for instance, even allowing for
children to go up to the parent node, then we would suggest mapping the tree
to a graph and using a graph traversal algorithms. This DSL is specifically
designed for recursive tree traversals.

## DFS Traversal Grammar

Our grammar is a domain-specific language (DSL) that allows some order
to be described and executed in the context of its tree context.

### Computational Model

The computational model which evaluates the DSL is far from Turing complete. It
is not a general-purpose programming language, but rather a DSL for describing
recursive tree traversals. It is a declarative langauge that consists of a list
of actions to be executed each time a node is visited (which happens only
once, since we are doing a depth-first search on a tree). There is state that is
maintained in the form of a local environment for each node that situates it in
the context of the tree, so that basic logic and reporting can be done, e.g.,
there is a `$depth` variable that tells you the depth of the node in the tree.
Thus, we can do a depth-first search up to some depth, for instance, by
checking the value of `$depth` in a conditional traversal.

#### Environment Model

The environment model represents the context of a node in its tree. We populate
the node's local environment with some special values that represent the node
and relationships it has to other nodes in the tree.

To reference an environment variable, we use the `$` symbol followed by the
name of the variable. For example, `$node` is the node that the traversal
is currently pointing to. You can store values in the environment
with the `set!` action:

```json
{
    "set!": { "key": "value" }
}
```

When you set a value in the environment, you can reference it later in either
the current node or its descenndants.

These enviroment variables may be used as arguments to predicates that describe
the traversal order. When we arrive at a node, we also populate the environment
with some special values that represent the node and its relationships to other
nodes in the tree. These values are:

- `$node` is the node that the traversal order is being applied to.
- `$depth` is the depth of the node in the tree.
- `$num_children` is the number of children of the node.
- `$parent` is the parent of the node.
- `$sibling` is the sibling of the node.
- `$root` is the root of the tree.
- `$reports` is a global dictionary of reports that the nodes are added to. The
  results are keyed by the value of the `name` argument in the `report`
  action.

### DFS Traversal Order Grammar

The traversal order grammar defines a JSON array of dictionaries that describe
a (conditional) sequence of actions that are processed at each node encountered
during a depth-first search (DFS) traversal of a tree.

The traversal order description is given by the following BNF:

```bnf
<order>         ::= "[" "]" | "[" <action> ("," <action>)* "]"
<action>        ::= <report> | <cond> | <select>
<select>        ::= "{"
                        "\"select\"" ":" <selector> 
                        ("," "\"order\"" ":" <select_order>)?
                        ("," <args>)?
                    "}"
<report         ::= "{"
                        "\"report\"" ":" <key>                         
                    "}"
<cond>          ::= "{"
                        "\"cond\"" ":" "["
                            <cond_case>
                            ("," <cond_case>)*
                        "]"
                    "}"
<cond_case>     ::= "{"
                        "\"pred\"" ":" <pred_fn>
                        ("," <args>)? ","
                        "\"order\"" ":" <order>
                    "}"
<args>          ::= "\"args\"" ":" <posargs> | "\"kwargs\"" ":" <kwargs>
<posargs>       ::= "[" "]" | "[" <arg> ("," <arg>)* "]"
<arg>           ::= <value> | <env_var>
<kwargs>        ::= "{" "}" | "{" <kwarg> ("," <kwarg>)* "}"
<kwarg>         ::= <key> ":" <arg>
<env_var>       ::= "$" <key>
<pred_fn>       ::= "true" | "false" | "\"less?\"" | "\"eq?\""
<selector>      ::= "\"all\"" | "\"none\"" | "\"rest\"" | "\"sample\""
<select_order>  ::= "\"id\"" | "\"reverse\"" | "\"shuffle\""
<key>           ::= <str>
<value>         ::= "{}" | <str> | <int> | <float> | <boolean>
                | "[" <value> ("," <value>)* "]" 
                | "{" <key> ":" <value> ("," <key> ":" <value>)* "}"
```

A traversal order is a list of actions that are applied to a node in the tree.
The actions are applied in order. The actions are defined in the `action`
production. The `action` production is a dictionary with the following keys:

- `order` is a list of actions that are applied to a node in the tree.
- `report` is an action predicate -- if the node satisfies the predicate,
   the node is added to a result list.
- `cond` is a conditional traversal -- if the node satisfies the predicate,
   the traversal order it is associated with is applied.
- `select` is a selector that determines which nodes are selected for
   traversal. `all` selects all nodes, `none` selects no nodes, `rest`
   selects all nodes not previously selected, and any other selector that
   is defined in the `selector` dispatch table. Note that the `select`
   action is not a predicate, but a selector that determines which children
   of the node are selected for traversal. The `select` action accepts optional
   arguments, `order`, `args`, and `kwargs`. The `order` may be used to specify
   the order in which the selected nodes are traversed to override the default
   order of the selector. The `args` and `kwargs` keys are used to pass
   arguments to the selector.

Some special environment variables that are automatically added to the
environment of the node are:

- `$node` is the node that the traversal order is being applied to.
- `$depth` is the depth of the node in the tree.
- `$num_children` is the number of children of the node.
- `$parent` is the parent of the node.
- `$root` is the root of the tree.
- `$results` is a global dictionary of results that the nodes are added to. The
  results are keyed by the value of the `result-name` argument in the `visit`
  action.

## Examples

Here is a simple pre-order traversal of all nodes in the tree:

```json
[ { "report": "pre-order" }, { "select": "all" } ]
```

We can omit the `select` action, since `all` is the default selector:

```json
[ { "report": "pre-order" } ]
```

If we wanted to do a post-order traversal, we could apply the `report` action
after the children have been visited:

```json
[ { "select": "all" }, { "report": "post-order" } ]
```

The `report` action is a special kind of operation that adds the node to a
a global dictionary of results. The results are keyed by the value of the
`name` argument in the `report` action. The default value of the `name`
argument is `default`, so that if no `name` argument is provided, the node
is added to the `default` key in the results dictionary.
If no `report` action is triggered, the node is not added to any results.

If we wanted to only go to a depth of up to 2, we could use a conditional
traversal:

```json
[
    {
        "cond": [
            { "pred" : "less?", "args" : ["$depth", 3],
              "then": [
                    { "report": "shallower-than-3" },
                    { "select": "all" }
                ]
            }
        ]
    }
]
```

We can remove the outer '[' and ']' since there is only one conditional action.
We can also remove the `[` and `]` that follows the `cond` key, since there is
only one conditional case.


```json
{
    "cond": {
        "pred" : "less?", "args" : ["$depth", 3],
        "then": [ { "report": "shallower-than-3" },
                  { "select": "all" } ]
    }
}
```

Suppose we want to update the payloads to include a count of the number of
ancestors of the node. We can use a payload map to do this:

```json
[ { "payload-map": "num-ancestors", "args": ["$node"] } ]
```

We didn't specify a `report` action in this case, since we only wanted to update
the payload of the nodes. We can also use a conditional traversal to only update
payloads that satisfy certain conditions:

```json
{
    "cond": {
        "pred" : "less?", "args" : ["$depth", 3],
        "then": { "payload-map": "num-ancestors", "args": ["$node"] }
    }
}
```

We see that we removed the `[` and `]` that follows the `then` key, since there
is only one action to be taken if the condition is satisfied.

In fact if we have a single `pred`, then we can remove the outer `cond` key
and just have the `pred` key:

```json
{
    "pred" : "less?", "args" : ["$depth", 3],
    "then": { "payload-map": "num-ancestors", "args": ["$node"] }
}
```

These are all just syntactic sugar for the same thing. Since we imagine that
this will often be used on the command line or as JSON POST requests, we
thought a bit of syntactic sugar would be helpful.
