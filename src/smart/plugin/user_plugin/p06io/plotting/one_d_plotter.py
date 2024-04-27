#!/usr/bin/env python3

__author__ = ["Jan Garrevoet"]


import gc

from matplotlib import pyplot
import matplotlib

# To add at a later date.
# matplotlib.rcParams["xtick.labelsize"]=5
# matplotlib.rcParams["ytick.labelsize"]=5
# plt.legend(fontsize=4)
# ax.set_xlim
# ax.set_ylim
# plt.ticklabel_format(style='plain')    # to prevent scientific notation.
# plt.xticks(x, labels, rotation='vertical') # tick label rotation

# Faster plotting simplifications
# import matplotlib.style as mplstyle
# mplstyle.use('fast')


###############
# OneDPlotter #
###############

class OneDPlotter(object):

    ############
    # __init__ #
    ############

    def __init__(self, output_backend="svg"):

        if output_backend == "svg":
            matplotlib.use("SVG")
        elif output_backend == "png":
            matplotlib.use("Agg")
            # Better performance and memory handling for large datasets
            matplotlib.rcParams["agg.path.chunksize"] = 10000
        else:
            raise ValueError("Unknown output backend.")

    #################
    # _close_figure #
    #################

    def _close_figure(self):
        """
        Closes the figure.
        """

        pyplot.clf()
        if hasattr(self, "_fig"):
            pyplot.close(self._fig)
        # Release memory again.
            del self._fig
        if hasattr(self, "_axes"):
            del self._axes

        gc.collect()

    ################
    # _init_figure #
    ################

    def _init_figure(self, options, labels, nb_datasets):
        self._options = options
        self._plot_options = {}

        if self._options is None:
            self._options = {}

        if "general" not in self._options:
            self._options["general"] = {}

        self._fig, self._axes = pyplot.subplots()

        self._init_labels(labels, nb_datasets)
        self._get_plot_options()

    #####################
    # _get_plot_options #
    #####################

    def _get_plot_options(self):
        """
        Determines the options that should be passed to the plotting function.
        """
        if "general" in self._options:
            if "colour" in self._options["general"]:
                self._plot_options["color"] = (
                    self._options["general"]["colour"]
                )

            if "linestyle" in self._options["general"]:
                self._plot_options["linestyle"] = (
                    self._options["general"]["linestyle"]
                )

            if "marker" in self._options["general"]:
                self._plot_options["marker"] = (
                    self._options["general"]["marker"]
                )

    ################
    # _init_labels #
    ################

    def _init_labels(self, labels, nb_datasets):
        """
        Initialises the labels used for labeling the datasets.
        """

        self._labels = labels

        if self._labels is None:
            self._options["general"]["legend"] = False
        else:
            if len(self._labels) == 0:
                self._options["general"]["legend"] = False
            # else:
            #     self._options["general"]["legend"] = True

        if not self._options["general"]["legend"]:
            self._labels = []
            for i in range(nb_datasets):
                self._labels.append("data{}".format(i))

    ################
    # _set_options #
    ################

    def _set_options(self):
        """
        Sets the options for the plot.
        """

        if self._options is not None:
            if "dpi" not in self._options:
                self._options["dpi"] = 300

            # X-axis
            if "x-axis" in self._options:
                if "label" in self._options["x-axis"]:
                    self._axes.set_xlabel(self._options["x-axis"]["label"])

                if "log" in self._options["x-axis"]:
                    if self._options["x-axis"]["log"]:
                        self._axes.semilogx()

                if "ticks" in self._options["x-axis"]:
                    if "offset" in self._options["x-axis"]["ticks"]:
                        self._axes.ticklabel_format(
                            axis="x",
                            useOffset=(
                                self._options["x-axis"]["ticks"]["offset"]
                            )
                        )

                    if "style" in self._options["x-axis"]["ticks"]:
                        self._axes.ticklabel_format(
                            axis="x",
                            style=self._options["x-axis"]["ticks"]["style"]
                        )

                    if "values" in self._options["x-axis"]["ticks"]:
                        self._axes.xaxis.set_ticks(
                            self._options["x-axis"]["ticks"]["values"]
                        )

            # Y-axis
            if "y-axis" in self._options:
                if "label" in self._options["y-axis"]:
                    self._axes.set_ylabel(self._options["y-axis"]["label"])

                if "log" in self._options["y-axis"]:
                    if self._options["y-axis"]["log"]:
                        self._axes.semilogy()

                if "ticks" in self._options["y-axis"]:
                    if "offset" in self._options["y-axis"]["ticks"]:
                        self._axes.ticklabel_format(
                            axis="y",
                            useOffset=(
                                self._options["y-axis"]["ticks"]["offset"]
                            )
                        )

                    if "style" in self._options["y-axis"]["ticks"]:
                        self._axes.ticklabel_format(
                            axis="y",
                            style=self._options["y-axis"]["ticks"]["style"]
                        )

                    if "values" in self._options["y-axis"]["ticks"]:
                        self._axes.yaxis.set_ticks(
                            self._options["y-axis"]["ticks"]["values"]
                        )

            if "general" in self._options:
                if "grid" in self._options["general"]:
                    if self._options["general"]["grid"]:
                        self._axes.grid()

                if "legend" in self._options["general"]:
                    if self._options["general"]["legend"]:
                        self._fig.legend()

                if "margins" in self._options["general"]:
                    if isinstance(self._options["general"]["margins"], float):
                        self._axes.margins(self._options["general"]["margins"])
                    elif isinstance(
                            self._options["general"]["margins"],
                            (tuple, list)):
                        self._axes.margins(
                            *self._options["general"]["margins"]
                        )

                if "padding" in self._options["general"]:
                    self._fig.subplots_adjust(
                        **self._options["general"]["padding"]
                    )

                if "title" in self._options["general"]:
                    self._axes.set_title(self._options["general"]["title"])

    ########
    # plot #
    ########

    def plot(
            self, filename: str, y_data: list, labels: list = None,
            options=None,
            x_data: list = None, saving: bool = True):
        """
        Creates a 1d plot using pyplot.

        Parameters
        ----------
        filename : str
            The filename where to save the data.

        y_data : list of numpy.ndarray
            The data to plot.

        labels : list of str, optional
            The labels corresponding to the provided data.
            When provided these will be used to populate the legend.

        options : dict, optional
            All possible options for plotting.

        x_data : nu
        """

        try:
            self._init_figure(options, labels, len(y_data))

            for i in range(len(y_data)):
                self._plot_options["label"] = self._labels[i]
                if x_data is None:
                    self._axes.plot(
                        y_data[i],
                        **self._plot_options
                    )
                else:
                    self._axes.plot(
                        x_data[i], y_data[i],
                        **self._plot_options
                    )

            self._set_options()

            self._fig.savefig(filename, dpi=self._options["dpi"])
        except Exception:
            raise
        finally:
            self._close_figure()

    ###########
    # scatter #
    ###########

    def scatter(
            self, filename: str, x_data: list, y_data: list,
            labels: list = None,
            options=None,
            saving: bool = True):
        """
        Creates a 1d plot using pyplot.

        Parameters
        ----------
        filename : str
            The filename where to save the data.

        y_data : list of numpy.ndarray
            The data to plot.

        labels : list of str, optional
            The labels corresponding to the provided data.
            When provided these will be used to populate the legend.

        options : dict, optional
            All possible options for plotting.

        x_data : nu
        """

        try:
            self._init_figure(options, labels, len(x_data))

            for i in range(len(x_data)):
                self._plot_options["label"] = self._labels[i]
                self._axes.scatter(x_data[i], y_data[i], **self._plot_options)

            self._set_options()

            self._fig.savefig(filename, dpi=self._options["dpi"])
        except Exception:
            raise
        finally:
            self._close_figure()
