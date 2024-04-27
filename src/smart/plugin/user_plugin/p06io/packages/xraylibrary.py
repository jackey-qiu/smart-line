from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import sys

import xraylib as _xraylib

if sys.version_info < (3, ):
    PYTHON_VERSION = 2
else:
    PYTHON_VERSION = 3


###########
# Xraylib #
###########

class Xraylib(object):
    '''
    Wrapper around xraylib for ease of use.
    '''

    ############
    # __init__ #
    ############

    def __init__(self):
        pass

    ################
    # _get_element #
    ################

    def _get_element(self, element):
        '''
        Checks if the element needs to be converted from str to int.

        Parameters
        ----------
        element : str or int
            Element

        Returns
        -------
        int
            Element number
        '''

        if isinstance(element, int):
            ret_val = element

        else:
            if PYTHON_VERSION == 2:
                if isinstance(element, unicode):    # noqa F821
                    ret_val = _xraylib.SymbolToAtomicNumber(
                        element.encode("utf-8")
                    )
                else:
                    raise TypeError(
                        'The provided element is not a string or int. type: {}'
                        .format(type(element))
                    )
            else:
                if isinstance(element, str):
                    ret_val = _xraylib.SymbolToAtomicNumber(element)
                else:
                    raise TypeError(
                        'The provided element is not a string or int.'
                    )

        if ret_val == 0:
            raise ValueError('Unknown element.')

        return ret_val

    #############
    # _get_line #
    #############

    def _get_line(self, line, notation):
        if notation.lower() == 'siegbahn':
            if line.lower() == 'ka':
                ret_val = _xraylib.KA_LINE
            elif line.lower() == 'ka1':
                ret_val = _xraylib.KA1_LINE
            elif line.lower() == 'ka2':
                ret_val = _xraylib.KA2_LINE
            elif line.lower() == 'ka3':
                ret_val = _xraylib.KA3_LINE
            elif line.lower() == 'kb':
                ret_val = _xraylib.KB_LINE
            elif line.lower() == 'kb1':
                ret_val = _xraylib.KB1_LINE
            elif line.lower() == 'kb2':
                ret_val = _xraylib.KB2_LINE
            elif line.lower() == 'kb3':
                ret_val = _xraylib.KB3_LINE
            elif line.lower() == 'la':
                ret_val = _xraylib.LA_LINE
            elif line.lower() == 'la1':
                ret_val = _xraylib.LA1_LINE
            elif line.lower() == 'la2':
                ret_val = _xraylib.LA2_LINE
            elif line.lower() == 'lb':
                ret_val = _xraylib.LB_LINE
            elif line.lower() == 'lb1':
                ret_val = _xraylib.LB1_LINE
            elif line.lower() == 'lb2':
                ret_val = _xraylib.LB2_LINE
            else:
                raise ValueError('Line not defined.')

        if notation.lower() == 'iupac':
            if line.lower() == 'kl1':
                ret_val = _xraylib.KL1_LINE
            elif line.lower() == 'kl2':
                ret_val = _xraylib.KL2_LINE
            elif line.lower() == 'kl3':
                ret_val = _xraylib.KL3_LINE
            elif line.lower() == 'km1':
                ret_val = _xraylib.KM1_LINE
            elif line.lower() == 'km2':
                ret_val = _xraylib.KM2_LINE
            elif line.lower() == 'km3':
                ret_val = _xraylib.KM3_LINE
            elif line.lower() == 'km4':
                ret_val = _xraylib.KM4_LINE
            elif line.lower() == 'km5':
                ret_val = _xraylib.KM5_LINE
            else:
                raise ValueError('Line not defined.')

        return ret_val

    #######################
    # get_absorption_edge #
    #######################

    def get_absorption_edge(
            self,
            element,
            line='Ka',
            notation='Siegbahn'):
        """
        Returns the absorption edge.

        Parameters
        ----------
        element : str or int
            The element in question.
            Can be provided as a string: e.g. "Fe"
            or as an integer: e.g. 26

        line : str, optional
            The line of interest.
            Default is Ka1.

        notation : str, optional
            Siegbahn or IUPAC.
            Default is Siegbahn.

        Returns
        -------
        float
            The absorption edge.
        """

        element = self._get_element(element)

        if line.lower().startswith("k"):
            line = 'Ka'
        elif line.lower().startswith("l"):
            line = 'La'

        line = self._get_line(line, notation)
        return _xraylib.EdgeEnergy(element, line) * 1000

    #####################
    # get_atomic_weight #
    #####################

    def get_atomic_weight(self, element):
        """
        Returns the absorption edge.

        Parameters
        ----------
        element : str or int
            The element in question.
            Can be provided as a string: e.g. "Fe"
            or as an integer: e.g. 26

        Returns
        -------
        float
            The atomic weight.
        """

        element = self._get_element(element)
        return _xraylib.AtomicWeight(element)

    ###############
    # get_density #
    ###############

    def get_density(self, element):
        """
        Returns the density of an element.

        Parameters
        ----------
        element : str or int
            The element in question.
            Can be provided as a string: e.g. "Fe"
            or as an integer: e.g. 26

        Returns
        -------
        float
            The density in g/cm^3.
        """
        element = self._get_element(element)

        return _xraylib.ElementDensity(element)

    ########################
    # get_fluo_line_energy #
    ########################

    def get_fluo_line_energy(
            self,
            element,
            line='Ka1',
            notation='Siegbahn'):
        '''
        Returns the energy of the fluorescence line.

        Parameters
        ----------
        element : str or int
            The element in question.
            Can be provided as a string: e.g. "Fe"
            or as an integer: e.g. 26

        line : str, optional
            The line of interest.
            Default is Ka1.

        notation : str, optional
            Siegbahn or IUPAC.
            Default is Siegbahn.

        Returns
        -------
        float
            The fluorescence line energy in eV.
        '''

        element = self._get_element(element)
        line = self._get_line(line, notation)
        return _xraylib.LineEnergy(element, line) * 1000

    #######################################
    # get_total_attenuation_cross_section #
    #######################################

    def get_total_attenuation_cross_section(self, element, energy):
        '''
        Returns the total attenuation cross section.

        Parameters
        ----------
        element : str or int
            The element in question.
            Can be provided as a string: e.g. "Fe"
            or as an integer: e.g. 26

        energy : float
            The energy in eV

        Returns
        -------
        float
            The total attenuation cross section in cm^2/g.
        '''

        element = self._get_element(element)
        return _xraylib.CS_Total(element, energy / 1000.0)
