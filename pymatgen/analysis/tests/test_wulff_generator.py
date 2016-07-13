# coding: utf-8
# !/usr/bin/env python

__author__ = 'Zihan Xu, Richard Tran, Balachandran Radhakrishnan'
__copyright__ = 'Copyright 2013, The Materials Virtual Lab'
__version__ = '0.1'
__maintainer__ = 'Zihan Xu'
__email__ = 'zix009@eng.ucsd.edu'
__date__ = 'May 05 2016'

from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.util.testing import PymatgenTest
from pymatgen.util.coord_utils import in_coord_list
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure
from pymatgen.analysis.wulff_generator import wulff_3d

import json
import os

class TestWulff(PymatgenTest):

    def setUp(self):

        module_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(module_dir, "surface_samples.json")) as data_file:
            surface_properties = json.load(data_file)

        surface_energies, miller_indices = {}, {}
        for mpid in surface_properties.keys():
            e_surf_list, miller_list = [], []
            for surface in surface_properties[mpid]["surfaces"]:
                e_surf_list.append(surface["surface_energy"])
                miller_list.append(surface["miller_index"])
            surface_energies[mpid] = e_surf_list
            miller_indices[mpid] = miller_list

        # In the case of a high anisotropy material
        # Nb: mp-8636
        latt_Nb = Lattice.cubic(2.992)
        # In the case of an fcc material
        # Ir: mp-101
        latt_Ir = Lattice.cubic(3.8312)
        # In the case of a hcp material
        # Ti: mp-72
        latt_Ti = Lattice.hexagonal(4.6000, 2.8200)

        self.ucell_Nb = Structure(latt_Nb, ["Nb", "Nb", "Nb", "Nb"],
                                  [[0, 0, 0], [0, 0.5, 0.5],
                                   [0.5, 0, 0.5], [0.5, 0.5, 0]])
        self.wulff_Nb = wulff_3d(latt_Nb, miller_indices["mp-8636"],
                                 surface_energies["mp-8636"])

        self.ucell_Ir = Structure(latt_Nb, ["Ir", "Ir", "Ir", "Ir"],
                                  [[0, 0, 0], [0, 0.5, 0.5],
                                   [0.5, 0, 0.5], [0.5, 0.5, 0]])
        self.wulff_Ir = wulff_3d(latt_Ir, miller_indices["mp-101"],
                                 surface_energies["mp-101"])

        self.ucell_Ti = Structure(latt_Ti, ["Ti", "Ti", "Ti"],
                                  [[0, 0, 0], [0.333333, 0.666667, 0.5],
                                   [0.666667, 0.333333, 0.5]])
        self.wulff_Ti = wulff_3d(latt_Ti, miller_indices["mp-72"],
                                 surface_energies["mp-72"])

        self.surface_properties = surface_properties

    def symm_check(self, ucell, wulff_vertices):
        """
        # Checks if the point group of the Wulff shape matches
        # the point group of its conventional unit cell

        Args:
            ucell (string): Unit cell that the Wulff shape is based on.
            wulff_vertices (list): List of all vertices on the Wulff
                shape. Use wulff.wulff_pt_list to obtain the list
                (see wulff_generator.py).

        return (bool)
        """

        space_group_analyzer = SpacegroupAnalyzer(ucell)
        symm_ops = space_group_analyzer.get_point_group_operations(cartesian=True)
        for point in wulff_vertices:
            for op in symm_ops:
                symm_point = op.operate(point)
                if in_coord_list(wulff_vertices, symm_point):
                    continue
                else:
                    return False
        return True

    def consistency_tests(self):

        # For a set of given values, these tests will
        # ensure that the general result given by the
        # algorithm does not change as the code is editted

        # For fcc Ir, make sure the (111) direction
        # is the most dominant facet on the Wulff shape

        fractional_areas = self.wulff_Ir.area_fraction_dict
        miller_list = [hkl for hkl in fractional_areas.keys()]
        area_list = [fractional_areas[hkl] for hkl in fractional_areas.keys()]
        self.assertEqual(miller_list[area_list.index(max(area_list))], (1,1,1))

        # Overall weighted surface energy of fcc Nb should be
        # equal to the energy of the (310) surface, ie. fcc Nb
        # is anisotropic, the (310) surface is so low in energy,
        # its the only facet that exists in the Wulff shape

        Nb_area_fraction_dict = self.wulff_Nb.area_fraction_dict
        for hkl in Nb_area_fraction_dict.keys():
            if hkl == (3,1,0):
                self.assertEqual(Nb_area_fraction_dict[hkl], 1)
            else:
                self.assertEqual(Nb_area_fraction_dict[hkl], 0)

        self.assertEqual(self.wulff_Nb.miller_energy_dict[(3,1,0)],
                         self.wulff_Be.weighted_surface_energy)


    def symmetry_test(self):

        # Maintains that all wulff shapes have the same point
        # groups as the conventional unit cell they were
        # derived from. This test should pass for all subsequent
        # updates of the surface_properties collection

        check_symmetry_Nb = self.symm_check(self.ucell_Nb,
                                         self.wulff_Nb.wulff_pt_list)
        check_symmetry_Ir = self.symm_check(self.ucell_Ir,
                                            self.wulff_Ir.wulff_pt_list)
        check_symmetry_Ti = self.symm_check(self.ucell_Ti,
                                            self.wulff_Ti.wulff_pt_list)
        self.assertTrue(check_symmetry_Nb)
        self.assertTrue(check_symmetry_Ir)
        self.assertTrue(check_symmetry_Ti)

    def test_get_azimuth_elev(self):
        azim, elev = self.wulff_Ir.get_azimuth_elev((0,0,1))
        self.assertEqual(azim, 0)
        self.assertEqual(elev, 90)
        azim, elev = self.wulff_Ir.get_azimuth_elev((1,1,1))
        self.assertAlmostEqual(azim, 45)

    def test_properties(self):

        wulff_shapes = {"mp-8636": self.wulff_Nb, "mp-72": self.wulff_Ti,
                        "mp-101": self.wulff_Ir}
        for mpid in wulff_shapes.keys():

            properties = self.surface_properties[mpid]
            wulff = wulff_shapes[mpid]
            self.assertEqual(round(wulff.weighted_surface_energy, 3),
                             round(properties[mpid]["weighted_surface_energy"], 3))
            self.assertEqual(round(wulff.shape_factor, 3),
                             round(properties[mpid]["shape_factor"], 3))
            self.assertEqual(round(wulff.anisotropy, 3),
                             round(properties[mpid]["surface_anisotropy"], 3))
