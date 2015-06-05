from __future__ import division
import tmscoring

import numpy as np
from numpy.testing import assert_almost_equal, TestCase


class TestAligningBase(TestCase):
    def test_matrix(self):
        align_object = tmscoring.Aligning('pdb1.pdb', 'pdb2.pdb')
        np.random.seed(124)
        for _ in xrange(100):
            theta, phi, psi = 2 * np.pi * np.random.random(3)
            dx, dy, dz = 10 * np.random.random(3)

            matrix = align_object.get_matrix(theta, phi, psi, dx, dy, dz)
            rotation = matrix[:3, :3]
            assert_almost_equal(1, np.linalg.det(rotation), 6)
            assert_almost_equal(1, np.linalg.det(matrix), 6)

    def test_tm_valuex(self):
        align_object = tmscoring.Aligning('pdb1.pdb', 'pdb2.pdb')
        np.random.seed(124)
        for _ in xrange(100):
            theta, phi, psi = 2 * np.pi * np.random.random(3)
            dx, dy, dz = 10 * np.random.random(3)

            tm = align_object._tm(theta, phi, psi, dx, dy, dz)

            assert 0 <= -tm / align_object.N <= 1

    def test_load_data_alignment(self):
        align_object = tmscoring.Aligning('pdb1.pdb', 'pdb2.pdb', mode='align')
        assert align_object.coord1.shape[0] == 4
        assert align_object.coord2.shape[0] == 4
        assert align_object.coord1.shape == align_object.coord2.shape

    def test_load_data_index(self):
        align_object = tmscoring.Aligning('pdb1.pdb', 'pdb2.pdb', mode='index')
        assert align_object.coord1.shape[0] == 4
        assert align_object.coord2.shape[0] == 4
        assert align_object.coord1.shape == align_object.coord2.shape