import copy


class GraphNode:
    def __init__(self, node_index, node_id):
        self.index = node_index
        self.node_id = node_id
        self.in_links = set()
        self.out_counts = 0

    def __repr__(self):
        return "Node={index=%s, id=%s, in=%s, out=%s}" % \
               (self.index, self.node_id, repr(self.in_links), self.out_counts)


class Graph:
    def __init__(self):
        self._node_map = {}
        self._node_list = []

    def __repr__(self):
        return "Graph=%s" % repr(self._node_list)

    def __iter__(self):
        return self._node_map.items().__iter__()

    def __len__(self):
        return len(self._node_list)

    def __getitem__(self, idx) -> GraphNode:
        return self._node_list[idx]

    def get_node_by_id(self, node_id):
        return self._node_map[node_id]


    def add_node(self, node_id):
        if node_id in self._node_map:
            return self._node_map[node_id]
        else:
            node_index = len(self._node_list)
            node = GraphNode(node_index, node_id)
            self._node_map[node_id] = node
            self._node_list.append(node)

            return node

    def add_link(self, source_id, target_id):
        # Ignore self references
        if source_id != target_id:
            source_node = self._node_map[source_id]
            target_node = self.add_node(target_id)

            # Ignore repeated connections
            source_index = source_node.index
            if source_index not in target_node.in_links:
                source_node.out_counts += 1
                target_node.in_links.add(source_index)

    def add_links(self, links):
        for source_id, target_id in links:
            self.add_node(source_id)
            self.add_node(target_id)
            self.add_link(source_id, target_id)

    def add_node_with_refs(self, node_id, *node_refs):
        node = self.add_node(node_id)
        for page_ref in node_refs:
            self.add_link(node_id, page_ref)

        return node


class PageRank:
    def __init__(self, _graph: Graph):
        self._graph = copy.copy(_graph)
        self._apply_sink_linking()

    def __repr__(self):
        return "PageRank{%s}" % (repr(self._graph))

    def _apply_sink_linking(self):
        number_of_nodes = len(self._graph)
        for source_id, source_node in self._graph:
            if source_node.out_counts == 0:
                source_node.out_counts = number_of_nodes
                self._add_link_to_all_nodes(source_node.index)

    def _add_link_to_all_nodes(self, source_index):
        for target_id, target_node in self._graph:
            target_node.in_links.add(source_index)

    def _out_count(self, index):
        return self._graph[index].out_counts

    def calculate(self, damping=0.85, epsilon=1.0e-5):
        page_count = len(self._graph)
        damping_per_page = (1 - damping) / page_count

        # Prepare for calculation
        ranks = [(1 / len(self._graph))] * page_count
        next_ranks = [0] * page_count
        delta = 1.0
        iteration_count = 0

        while delta > epsilon:
            # Calculate next rank values...
            for _, page in self._graph:
                next_ranks[page.index] = damping_per_page + \
                                         damping * sum(ranks[idx] / self._out_count(idx) for idx in page.in_links)

            # Calculate the delta between the current rank values and the next rank values...
            delta = sum(abs(next_rank - ranks[idx]) for idx, next_rank in enumerate(next_ranks))

            # Next iteration...
            ranks = next_ranks
            iteration_count += 1

        # List pages sorted by rank desc
        page_ranks = list((self._graph[idx].node_id, rank) for idx, rank in enumerate(ranks))
        page_ranks.sort(reverse=True, key=lambda x: x[1])

        return page_ranks, iteration_count


if __name__ == '__main__':
    connections = [('A', 'B'), ('A', 'D'), ('D', 'B'), ('E', 'B'), ('B', 'C'), ]
    print('Connections:', connections)

    graph = Graph()
    graph.add_links(connections)

    page_rank = PageRank(graph)
    print(page_rank.calculate(epsilon=1.0e-3))
