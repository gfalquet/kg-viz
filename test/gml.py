import networkx as nx

# Create a graph
G = nx.Graph()

# Add nodes with attributes
G.add_node(1, label="Node 1", color="red", size=10)
G.add_node(2, label="Node 2", color="blue", size=15)

# Add edges with attributes
G.add_edge(1, 2, weight=2.5, type="knows")
G.add_edge(1, 3, weight=1.0, type="works_with")

# Write to GraphML
nx.write_graphml(G, "my_graph.graphml")

# Read from GraphML
G2 = nx.read_graphml("my_graph.graphml")