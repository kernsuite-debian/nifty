# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright(C) 2013-2019 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

from ..field import Field
from ..multi_field import MultiField
from .operator import Operator


class Adder(Operator):
    """Adds a fixed field.

    Parameters
    ----------
    field : Field or MultiField
        The field by which the input is shifted.
    """
    def __init__(self, field):
        if not isinstance(field, (Field, MultiField)):
            raise TypeError
        self._field = field
        self._domain = self._target = field.domain

    def apply(self, x):
        self._check_input(x)
        return x + self._field
