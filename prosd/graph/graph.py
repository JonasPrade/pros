# from prosd import models, db
import networkx
import matplotlib.pyplot as plt

class GraphBasic:
    """
    provides basic methods for a routable graph for transportion cases
    """

    def shortest_path(self, graph, source, target):
        route = networkx.shortest_path(G=graph, source=source, target=target)
        return route

    def show_path_on_map(self, graph, nodes_pos):
        """
        shows the path of an shortest_path on a map based on the graph
        :param graph:
        :param path:
        :return:
        """
        networkx.draw_networkx(G=graph, pos=nodes_pos)
        plt.show()