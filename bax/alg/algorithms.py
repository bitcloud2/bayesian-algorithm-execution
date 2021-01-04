"""
Algorithms for BAX.
"""

from argparse import Namespace
import copy
import numpy as np
from abc import ABC, abstractmethod
import heapq
import random
import time

from ..util.misc_util import dict_to_namespace
from ..util.graph import Vertex, backtrack_indices


class Algorithm(ABC):
    """Base class for a BAX Algorithm"""

    def __init__(self, params=None, verbose=True):
        """
        Parameters
        ----------
        params : Namespace_or_dict
            Namespace or dict of parameters for the algorithm.
        verbose : bool
            If True, print description string.
        """
        self.set_params(params)
        if verbose:
            self.print_str()
        super().__init__()

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        params = dict_to_namespace(params)

        # Set self.params
        self.params = Namespace()
        self.params.name = getattr(params, "name", "Algorithm")

    def run_algorithm_on_f(self, f):
        """
        Run the algorithm by sequentially querying function f. Return the execution path
        and output.
        """
        # Initialize execution path
        exe_path = Namespace(x=[], y=[])

        # Step through algorithm
        x = self.get_next_x(exe_path)
        while x is not None:
            y = f(x)
            exe_path.x.append(x)
            exe_path.y.append(y)
            x = self.get_next_x(exe_path)

        # Compute output from exe_path, and return both
        output = self.get_output_from_exe_path(exe_path)
        return exe_path, output

    def get_next_x(self, exe_path):
        """
        Given the current execution path, return the next x in the execution path. If
        the algorithm is complete, return None.
        """
        len_path = len(exe_path.x)
        if len_path == len(self.params.x_path):
            next_x = None
        else:
            next_x = self.params.x_path[len_path]
        return next_x

    def print_str(self):
        """Print a description string."""
        print("*[INFO] " + str(self))

    def set_print_params(self):
        """Set self.print_params."""
        self.print_params = copy.deepcopy(self.params)

    def __str__(self):
        self.set_print_params()
        return f"{self.params.name} with params={self.print_params}"

    @abstractmethod
    def get_output_from_exe_path(self, exe_path):
        pass


class LinearScan(Algorithm):
    """
    Algorithm that scans over a grid on a one dimensional domain, and as output returns
    function values at each point on grid.
    """

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        super().set_params(params)
        params = dict_to_namespace(params)

        self.params.name = getattr(params, "name", "LinearScan")
        self.params.x_path = getattr(params, "x_path", [])

    def get_output_from_exe_path(self, exe_path):
        """Given an execution path, return algorithm output."""
        return exe_path.y

    def set_print_params(self):
        """Set self.print_params."""
        self.print_params = copy.deepcopy(self.params)
        delattr(self.print_params, "x_path")


class LinearScanRandGap(LinearScan):
    """
    Algorithm that scans over a grid (with randomly drawn gap size between gridpoints)
    on a one dimensional domain, and as output returns function values at each point on
    grid.
    """

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        super().set_params(params)
        params = dict_to_namespace(params)

        self.params.name = getattr(params, "name", "LinearScanRandGap")
        self.params.x_path_orig = copy.deepcopy(self.params.x_path)

    def run_algorithm_on_f(self, f):
        """
        Run the algorithm by sequentially querying function f. Return the execution path
        and output.
        """
        x_path = copy.deepcopy(self.params.x_path_orig)
        n_grid = len(x_path)
        rand_factor = 0.2
        min_gap = np.ceil((1 - rand_factor) * n_grid)
        max_gap = np.ceil((1 + rand_factor) * n_grid)
        new_n_grid = np.random.randint(min_gap, max_gap)
        min_x_path = np.min(x_path)
        max_x_path = np.max(x_path)
        new_x_path = [[x] for x in np.linspace(min_x_path, max_x_path, new_n_grid)]
        self.params.x_path = new_x_path

        return super().run_algorithm_on_f(f)

    def set_print_params(self):
        """Set self.print_params."""
        self.print_params = copy.deepcopy(self.params)
        delattr(self.print_params, "x_path")
        delattr(self.print_params, "x_path_orig")


class AverageOutputs(Algorithm):
    """
    Algorithm that computes the average of function outputs for a set of input points.
    """

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        super().set_params(params)
        params = dict_to_namespace(params)

        self.params.name = getattr(params, "name", "AverageOutputs")
        self.params.x_path = getattr(params, "x_path", [])

    def get_output_from_exe_path(self, exe_path):
        """Given an execution path, return algorithm output."""
        return np.mean(exe_path.y)

    def set_print_params(self):
        """Set self.print_params."""
        self.print_params = copy.deepcopy(self.params)
        delattr(self.print_params, "x_path")


class SortOutputs(Algorithm):
    """
    Algorithm that sorts function outputs for a set of input points.
    """

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        super().set_params(params)
        params = dict_to_namespace(params)

        self.params.name = getattr(params, "name", "SortOutputs")
        self.params.x_path = getattr(params, "x_path", [])

    def get_output_from_exe_path(self, exe_path):
        """Given an execution path, return algorithm output."""
        return np.argsort(exe_path.y)

    def set_print_params(self):
        """Set self.print_params."""
        self.print_params = copy.deepcopy(self.params)
        delattr(self.print_params, "x_path")


class OptRightScan(Algorithm):
    """
    A simple minimization algorithm that, starting from some initial point, optimizes by
    scanning to the right until function starts to increase.
    """

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        super().set_params(params)
        params = dict_to_namespace(params)

        self.params.name = getattr(params, "name", "OptRightScan")
        self.params.init_x = getattr(params, "init_x", [4.0])
        self.params.x_grid_gap = getattr(params, "x_grid_gap", 0.1)
        self.params.conv_thresh = getattr(params, "conv_thresh", 0.2)
        self.params.max_iter = getattr(params, "max_iter", 100)

    def get_next_x(self, exe_path):
        """
        Given the current execution path, return the next x in the execution path. If
        the algorithm is complete, return None.
        """
        len_path = len(exe_path.x)
        if len_path == 0:
            next_x = self.params.init_x
        else:
            next_x = [exe_path.x[-1][0] + self.params.x_grid_gap]

        if len_path >= 2:
            conv_max_val = np.min(exe_path.y[:-1]) + self.params.conv_thresh
            if exe_path.y[-1] > conv_max_val:
                next_x = None

        # Algorithm also has max number of steps
        if len_path > self.params.max_iter:
            next_x = None

        return next_x

    def get_output_from_exe_path(self, exe_path):
        """Given an execution path, return algorithm output."""
        return exe_path.x[-1]


class Dijkstras(Algorithm):
    """Implments the shortest path or minimum cost algorithm using the Vertex
    class.

    """

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        super().set_params(params)
        params = dict_to_namespace(params)

        self.params.name = getattr(params, "name", "Dijkstras")
        self.params.start = getattr(params, "start", None)
        self.params.goal = getattr(params, "goal", None)
        self.params.vertices = getattr(params, "vertices", None)
        self.params.cost_func = getattr(params, "cost_func", lambda u, v: 0)
        self.params.true_cost = getattr(params, "true_cost", lambda u, v: 0)

    def run_algorithm_on_f(self, f):
        np.random.seed()  # prevent parallel processes from sharing random state

        def dijkstras(start: Vertex, goal: Vertex):
            explored = [False for _ in range(len(self.params.vertices))]
            min_cost = [float("inf") for _ in range(len(self.params.vertices))]
            prev = [None for _ in range(len(self.params.vertices))]
            to_explore = [(0, start)]  # initialize priority queue
            i = 0
            while len(to_explore) > 0:
                best_cost, current = heapq.heappop(to_explore)
                if explored[current.index]:
                    # the same node could appear in the pqueue multiple times with different costs
                    continue
                explored[current.index] = True
                i += 1
                if current.index == goal.index:
                    print(
                        f"Found goal after expanding {i} vertices with estimated cost {best_cost}"
                    )
                    best_path = [
                        self.params.vertices[i]
                        for i in backtrack_indices(current.index, prev)
                    ]

                    def true_cost_of_path(path):
                        cost = 0
                        for i in range(len(path) - 1):
                            cost += self.params.true_cost(path[i], path[i + 1])[0]
                        print("true cost", cost)

                    true_cost_of_path(best_path)
                    return best_cost, best_path

                for neighbor in current.neighbors:
                    step_cost = distance(current, neighbor)
                    if (not explored[neighbor.index]) and (
                        best_cost + step_cost < min_cost[neighbor.index]
                    ):
                        heapq.heappush(
                            to_explore, (best_cost + step_cost, neighbor)
                        )  # push by cost
                        min_cost[neighbor.index] = best_cost + step_cost
                        prev[neighbor.index] = current.index

            print("No path exists to goal")
            return float("inf"), []

        exe_path = Namespace(x=[], y=[])

        def distance(u: Vertex, v: Vertex):
            cost, xs, ys = self.params.cost_func(u, v, f)

            exe_path.x.extend(xs)
            exe_path.y.extend(ys)
            assert cost >= 0
            return cost

        min_cost = dijkstras(self.params.start, self.params.goal)

        return exe_path, min_cost

    def get_output_from_exe_path(self, exe_path):
        raise RuntimeError("Can't return output from execution path for Dijkstras")


class Noop(Algorithm):
    """"Dummy noop algorithm for debugging parallel code"""

    def set_params(self, params):
        """Set self.params, the parameters for the algorithm."""
        super().set_params(params)
        params = dict_to_namespace(params)

    def run_algorithm_on_f(self, f):
        np.random.seed()  # must reseed each time or else child process will have the same state as parent, resulting in the same randomness
        output = 0
        exe_path = Namespace(x=[], y=[])
        wait_time = random.randint(1, 5)
        rand = np.random.rand(1)
        print(f"Got {rand}. Going to wait for {wait_time} seconds")
        time.sleep(wait_time)
        print(f"Finished waiting for {wait_time} seconds")
        return exe_path, output

    def get_output_from_exe_path(self, exe_path):
        raise RuntimeError("Can't return output from execution path for Noop")
