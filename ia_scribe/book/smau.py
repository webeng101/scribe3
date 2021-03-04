# State Machine Analisys Utility

from ia_scribe.book.states import book_state_machine
import networkx as nx
#import matplotlib.pyplot as plt

G = nx.DiGraph()

def convert_fysom_to_networkx(fysom_config):
    for n, edge in enumerate(fysom_config['events']):
        source = edge['src']
        destination = edge['dst']
        name = edge['name']
        unwrapped = []
        if type(source) is list:
            for s in source:
                unwrapped.append((s, destination, name))
        elif type(destination) is list:
            for d in destination:
                unwrapped.append((source, d, name))
        else:
            unwrapped.append((source, destination, name))

        #print 'unwrapped edges:', unwrapped
        for source, destination, name in unwrapped:
            G.add_edge(source, destination, name=name)
    return G

G = convert_fysom_to_networkx(book_state_machine)

available_next_actions = lambda y: [x[2]['name'] for x in G.out_edges(y, data=True) ]
available_next_states = lambda y: [x for x in G[y]]
path_to_success = lambda y : nx.shortest_path(G, y, 'uploaded')
path_to_success_corrections = lambda y : nx.shortest_path(G, y, 'corrected')
path_to_deletion = lambda y : nx.shortest_path(G, y, 'trash')
path_to_state = lambda x, y : nx.shortest_path(G, x, y)
has_path_to_state = lambda x, y : nx.has_path(G, x, y)


def _generate_lattice_pos(graph):
    ret = {}

def get_transition_plan(initial_state, final_state):
    return nx.shortest_path(G, initial_state, final_state)

'''
def plot_state_machine(G):

    # This code tries to plot the state machine and its transitions.
    # -----------------------------------------------------
    fixed_positions = {'uuid_assigned': [0, 0],
                       #'upload_started': [10, 0],
                       #'download_incomplete': [0, 10],
                       'deleted': [1, 1],
                       }
    pos = nx.layout.spring_layout(G, seed =0, k=.4,
                pos = fixed_positions,
                )
    #pos = _generate_lattice_pos(G)
    #pos = nx.spring_layout(G, k=0.45)
    pos_higher = {}
    y_off = 0.05  # offset on the y axis
    
    for k, v in pos.items():
        pos_higher[k] = (v[0], v[1]+y_off)
    
    plt.figure()
    
    nx.draw(G, pos, edge_color='black',width=1,linewidths=1,\
    node_size=200,node_color='blue',alpha=0.9,)
    
    nx.draw_networkx_labels(G, pos_higher, labels={node:node for node in G.nodes()})
    
    edge_labels = nx.get_edge_attributes(G,'name')
    
    nx.draw_networkx_edge_labels(G, pos, font_color='black', font_size='10', edge_labels=edge_labels)
    plt.axis('off')
    plt.show()
'''

def export(G, filename = 'state_machine.graphml'):
    nx.write_graphml(G,filename)

