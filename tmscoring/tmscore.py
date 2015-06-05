from __future__ import division

import math

import numpy as np

import iminuit

from Bio import PDB
from Bio import pairwise2


DTYPE = np.float64


class Aligning(object):
    def __init__(self, pdb_1, pdb_2, mode='index', chain_1='A', chain_2='A'):
        """
        pdb_1, pdb_2 are the file names for the PDB files.
        Chain

        """
        self.pdb1 = pdb_1
        self.pdb2 = pdb_2
        if mode == 'align':
            self._load_data_alignment(chain_1, chain_2)
        elif mode == 'index':
            self._load_data_index(chain_1, chain_2)
        else:
            raise ValueError('Unrecognised mode {}'.format(mode))

        # Estimate d0 as TMscore does.
        d0 = 1.24 * (self.N - 15)**(1.0/3.0) - 1.8
        self.d02 = d0 ** 2

        self._values = dict(dx=0, dy=0, dz=0, theta=0, phi=0, psi=0)

    def __call__(self, theta, phi, psi, dx, dy, dz):
        raise NotImplementedError('This method should be overriden by subclasses')

    def get_default_values(self):
        """
        Make a crude estimation of the alignment using the center of mass
        and general C->N orientation.
        """
        out = dict(dx=0, dy=0, dz=0, theta=0, phi=0, psi=0)
        dx, dy, dz, _ = np.mean(self.coord1 - self.coord2, axis=1)
        out['dx'] = dx
        out['dy'] = dy
        out['dz'] = dz

        # C->N vector
        vec1 = self.coord1[:-1, 1] - self.coord1[:-1, -1]
        vec2 = self.coord2[:-1, 1] - self.coord2[:-1, -1]
        vec1 /= np.linalg.norm(vec1)
        vec2 /= np.linalg.norm(vec2)

        # Find the rotation matrix that converts vec1 to vec2:
        # http://math.stackexchange.com/questions/180418/#476311
        v = np.cross(vec1, vec2)
        s = np.linalg.norm(v)
        c = vec1.dot(vec2)
        vx = np.array([[0, -v[2], v[1]],
                       [v[2], 0, -v[0]],
                       [-v[1], v[0], 0]], dtype=DTYPE)
        rotation_matrix = np.eye(3) + vx + vx.dot(vx) * (1 - c) / (s * s)

        # Recover the angles from the matrix as seen here:
        # http://nghiaho.com/?page_id=846
        out['theta'] = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        out['phi'] = math.atan2(-rotation_matrix[2, 0],
                                math.hypot(rotation_matrix[2, 1],
                                           rotation_matrix[2, 2]))
        out['psi'] = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])

        return out

    @staticmethod
    def get_matrix(theta, phi, psi, dx, dy, dz,
                   matrix=np.zeros((4, 4), dtype=DTYPE),
                   angles=np.zeros(3, dtype=DTYPE)):
        """
        Build the rotation-translation matrix.

        It has the form:

        [         | dx ]
        [    R    | dy ]
        [         | dz ]
        [ 0  0  0 | 1  ]
        """
        # NB!: matrix and angles by default are being overwritten on each call
        # thus, only created once.

        angles[0] = theta
        angles[1] = phi
        angles[2] = psi

        cx, cy, cz = np.cos(angles)
        sx, sy, sz = np.sin(angles)

        rotation = matrix[:3, :3]
        rotation.flat = (cx * cz - sx * cy * sz,
                         cx * sz + sx * cy * cz, sx * sy,
                         -sx * cz - cx * cy * sz,
                         -sx * sz + cx * cy * cz, cx * sy,
                         sy * sz,
                         -sy * cz, cy)

        # Translation component
        matrix[:3, 3] = dx, dy, dz
        matrix[3, 3] = 1.
        return matrix

    def optimise(self, restart=True):
        if restart:
            default = self.get_default_values()
        else:
            default = self.get_current_values()

        m = iminuit.Minuit(self, error_theta=0.1, error_phi=0.1, error_psi=0.1,
                           error_dx=1, error_dy=1, error_dz=1, print_level=0, pedantic=False,
                           **default)
        m.migrad()

        _values = m.values
        self._values = _values
        return _values, self.tmscore(**_values), self.rmsd(**_values)

    def get_current_values(self):
        return self._values

    def _tm(self, theta, phi, psi, dx, dy, dz):
        """
        Compute the minimisation target, not normalised.
        """
        matrix = self.get_matrix(theta, phi, psi, dx, dy, dz)
        coord = matrix.dot(self.coord2)
        dist = coord - self.coord1

        d_i2 = (dist * dist).sum(axis=0)

        tm = -(1 / (1 + (d_i2/self.d02))).sum()

        return tm

    def _rmsd(self, theta, phi, psi, dx, dy, dz):
        matrix = self.get_matrix(theta, phi, psi, dx, dy, dz)
        coord = matrix.dot(self.coord2)
        dist = coord - self.coord1
        return (dist * dist).sum()

    def tmscore(self, theta, phi, psi, dx, dy, dz):
        return -self._tm(theta, phi, psi, dx, dy, dz) / self.N

    def rmsd(self, theta, phi, psi, dx, dy, dz):
        return np.sqrt(self._rmsd(theta, phi, psi, dx, dy, dz) / self.N)

    def write(self, theta, phi, psi, dx, dy, dz, outputfile='out.pdb'):
        """
        Save the second PDB file aligned to the first.
        """
        # TODO: save both in a single PDB file as different molecules.

        matrix = self.get_matrix(theta, phi, psi, dx, dy, dz)

        out = open(outputfile, 'w')
        for line in open(self.pdb2):
            if not line.startswith('ATOM'):
                out.write(line)
                continue
            x = float(line[32:38])
            y = float(line[39:46])
            z = float(line[48:54])
            vec = np.array([x, y, z, 0])
            x, y, z, _ = matrix.dot(vec)

            line2 = ''.join((line[:30],
                             '{:>8.3f}{:>8.3f}{:>8.3f}'.format(x, y, z),
                             line[54:]))

            out.write(line2)
        out.close()

    def _load_data_alignment(self, chain1, chain2):
        """
        Extract the sequences from the PDB file, perform the alignment,
        and load the coordinates of the CA of the common residues.
        """
        parser = PDB.PDBParser(QUIET=True)
        ppb = PDB.PPBuilder()

        structure1 = parser.get_structure(chain1, self.pdb1)
        structure2 = parser.get_structure(chain2, self.pdb2)

        seq1 = str(ppb.build_peptides(structure1)[0].get_sequence())
        seq2 = str(ppb.build_peptides(structure2)[0].get_sequence())

        # Alignment parameters taken from PconsFold renumbering script.
        align = pairwise2.align.globalms(seq1, seq2, 2, -1, -0.5, -0.1)[0]
        indexes = set(i for i, (s1, s2) in enumerate(zip(align[0], align[1]))
                      if s1 != '-' and s2 != '-')
        coord1 = np.hstack([np.concatenate((r['CA'].get_coord(), (1,)))[:, None]
                            for i, r in enumerate(structure1.get_residues())
                            if i in indexes and 'CA' in r]).astype(DTYPE,
                                                                   copy=False)
        coord2 = np.hstack([np.concatenate((r['CA'].get_coord(), (1,)))[:, None]
                            for i, r in enumerate(structure2.get_residues())
                            if i in indexes and 'CA' in r]).astype(DTYPE,
                                                                   copy=False)

        self.coord1 = coord1
        self.coord2 = coord2
        self.N = len(seq1)

    def _load_data_index(self, chain1, chain2):
        """
        Load the coordinates of the CA of the common residues.
        """
        parser = PDB.PDBParser(QUIET=True)

        structure1 = parser.get_structure(chain1, self.pdb1)
        structure2 = parser.get_structure(chain2, self.pdb2)

        residues1 = list(structure1.get_residues())
        residues2 = list(structure2.get_residues())

        indexes1 = set(r.id[1] for r in residues1)
        indexes2 = set(r.id[1] for r in residues2)

        indexes = indexes1.intersection(indexes2)
        coord1 = np.hstack([np.concatenate((r['CA'].get_coord(), (1,)))[:, None]
                            for r in residues1
                            if r.id[1] in indexes and 'CA' in r]).astype(DTYPE,
                                                                   copy=False)
        coord2 = np.hstack([np.concatenate((r['CA'].get_coord(), (1,)))[:, None]
                            for r in residues2
                            if r.id[1] in indexes and 'CA' in r]).astype(DTYPE,
                                                                   copy=False)

        self.coord1 = coord1
        self.coord2 = coord2
        self.N = len(indexes1)


class TMscoring(Aligning):
    """
    Use this if you want to minimise for TM score
    """
    def __call__(self, theta, phi, psi, dx, dy, dz):
        return self._tm(theta, phi, psi, dx, dy, dz)

    @staticmethod
    def default_errordef():
        return 0.01

class RMSDscoring(Aligning):
    """
    Use this if you want to minimise for RMSD.
    """
    def __call__(self, theta, phi, psi, dx, dy, dz):
        return self._rmsd(theta, phi, psi, dx, dy, dz)

    @staticmethod
    def default_errordef():
        return 0.05

def get_tm(pdb1, pdb2):
    tm_sc = TMscoring(pdb1, pdb2)
    return tm_sc.optimise()[1]

def get_rmsd(pdb1, pdb2):
    rmsd_sc = RMSDscoring(pdb1, pdb2)
    return rmsd_sc.optimise()[2]


if __name__ == '__main__':
    import os
    import time

    pdb1 = 'tests/pdb1.pdb'
    pdb2 = 'tests/pdb2.pdb'
    sc = TMscoring(pdb1, pdb1)
    assert sc.tmscore(0, 0, 0, 0, 0, 0) == 1

    t0 = time.time()

    print '----'
    sc = TMscoring(pdb1, pdb2, mode='index')
    sc(2, 1, -1, 0, 0, 0)

    m = iminuit.Minuit(sc,
                       error_theta=0.1, error_phi=0.1, error_psi=0.1,
                       error_dx=1, error_dy=1, error_dz=1,
                       print_level=0,
                       **sc.get_default_values())

    m.migrad()
    print '**', time.time() - t0, '**'

    print m.values
    print 'TM-score =', sc.tmscore(**m.values)
    print 'RMSD =', sc.rmsd(**m.values)

    sc.write(**m.values)
    print sc.get_matrix(**m.values)

    t0 = time.time()
    os.system('TMscore {} {} | grep TM-score | grep d0'.format(pdb1, pdb2))
    print '*-*', time.time() - t0, '*-*'

    os.system('TMscore {} {} | tail -n 20 | head -n 14'.format(pdb1, pdb2))
