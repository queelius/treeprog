import random

def rest_sel(nodes, visited, followed):
    """
    return [n for n in nodes if n not in followed and n not in visited]

    Args:
        nodes: List of nodes to select from.
        visited: Set of nodes that have been visited.
        followed: Set of nodes that have been followed.

    Returns:
        List of nodes that have not been visited or followed at the current node.
    """
    return [n for n in nodes if n not in followed and n not in visited]

def sample_sel(nodes, visited, followed, n):
    """
    Sample without replacment up to `n` random nodes from the list of nodes that have not been visited or followed.

    Args:
        nodes: List of nodes to select from.
        visited: Set of nodes that have been visited.
        followed: Set of nodes that have been followed.
        n: Maximum number of nodes to select.   

    Returns:
        List of up to `n` nodes sampled from `nodes`.
    """
    candidates = [node for node in nodes if node not in visited and node not in followed]
    n = min(n, len(candidates))
    return random.sample(candidates, n)

def slice_sel(nodes, visited, followed, start=0, end=-1, by=1):
    """
    Slice the list of nodes that have not been visited or followed.

    Args:
        nodes: List of nodes to select from.
        visited: Set of nodes that have been visited.
        followed: Set of nodes that have been followed.
        start: Start index of the slice.
        end: End index of the slice.
        by: Step size of the slice.

    Returns:
        List of nodes sliced from `nodes`.
    """
    # first, we need to filter out the nodes that have been visited or followed
    candidates = [node for node in nodes if node not in visited and node not in followed]
    return candidates[start:end:by]
