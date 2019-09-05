
"""
The script checks the validity of the YAML configuration file.

Example usage:

    $ python checks.py [file_name].yaml

    $ python checks.py good_config.yaml
    No loops.

    $ python checks.py bad_config.yaml
    Loop(s) found.
    Processor to Analysis to Acquirer

"""

import sys

import networkx as nx
import yaml


def check_if_connections_acyclic(path_to_yaml):
    """
    Check if connections in the YAML configuration file do not form a loop.

    Print 'No loops.' if the connections are acyclic.
    Print 'Loop(s) found.' followed by the loop path if loops are found.

    :param path_to_yaml: Path to the YAML file.
    :type path_to_yaml: str

    :return: Whether the connections are acyclic.
    :rtype: bool

    """
    with open(path_to_yaml) as f:
        raw = yaml.safe_load(f)['connections']

    # Need to keep only module names
    connections = {}
    for key, values in raw.items():
        new_key = key.split('.')[0]
        new_values = [value.split('.')[0] for value in values]
        connections[new_key] = new_values

    g = nx.DiGraph(connections)
    dag = nx.is_directed_acyclic_graph(g)

    if dag:
        print('No loops.')
        return True

    print('Loop(s) found.')
    loops = nx.algorithms.cycles.simple_cycles(g)
    for loop in loops:
        print(*loop, sep=' to ')
    return False


if __name__ == '__main__':
    check_if_connections_acyclic(sys.argv[1])
