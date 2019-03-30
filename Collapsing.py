import networkx as nx


class Collapser:

    def __init__(self, mops, node_to_collapse_on):
        self.mops = mops
        self.node_to_collapse_on = node_to_collapse_on
        self.collapsed_graph = nx.quotient_graph(mops.slots, self.is_neighbor, node_data=self.label_nodes)

    def is_neighbor(self, u, v):
        return (u in self.mops.abstractions.predecessors(
            self.node_to_collapse_on) or u == self.node_to_collapse_on) and v in self.mops.abstractions.predecessors(
            self.node_to_collapse_on)

    def label_nodes(self, B):
        label = None
        for u in B:
            label = {self.mops.attribute_label: self.mops.get_frame_label(u)}
            if u == self.node_to_collapse_on:
                return label

        return label

    def get_collapsed_edge_labels(self, G):
        labels = dict()
        for u, v, k in G.edges:
            labels[(u, v)] = list(self.collapsed_graph.edges[u, v, k].values())[0].get(self.mops.attribute_label)

        return labels

    def draw(self, image_dir):
        self.mops.draw_graph(self.collapsed_graph,
                             nx.fruchterman_reingold_layout(self.collapsed_graph),
                             image_dir + "/collapsed_graph.png",
                             size=50,
                             node_labels=nx.get_node_attributes(self.collapsed_graph, self.mops.attribute_label),
                             edge_labels=self.get_collapsed_edge_labels(self.collapsed_graph))
