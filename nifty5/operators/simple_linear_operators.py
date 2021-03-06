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

from ..domain_tuple import DomainTuple
from ..domains.unstructured_domain import UnstructuredDomain
from ..field import Field
from ..multi_domain import MultiDomain
from ..multi_field import MultiField
from .endomorphic_operator import EndomorphicOperator
from .linear_operator import LinearOperator


class VdotOperator(LinearOperator):
    """Operator computing the scalar product of its input with a given Field.

    Parameters
    ----------
    field : Field or MultiField
        The field used to build the scalar product with the operator input
    """
    def __init__(self, field):
        self._field = field
        self._domain = field.domain
        self._target = DomainTuple.scalar_domain()
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_mode(mode)
        if mode == self.TIMES:
            return Field.scalar(self._field.vdot(x))
        return self._field*x.local_data[()]


class ConjugationOperator(EndomorphicOperator):
    """Operator computing the complex conjugate of its input.

    Parameters
    ----------
    domain: Domain, tuple of domains or DomainTuple
        domain of the input field

    """
    def __init__(self, domain):
        self._domain = DomainTuple.make(domain)
        self._capability = self._all_ops

    def apply(self, x, mode):
        self._check_input(x, mode)
        return x.conjugate()


class WeightApplier(EndomorphicOperator):
    """Operator multiplying its input by a given power of dvol.

    Parameters
    ----------
    domain: Domain, tuple of domains or DomainTuple
        domain of the input field
    spaces: list or tuple of int
        indices of subdomains for which the weights shall be applied
    power: int
        the power of to be used for the volume factors

    """
    def __init__(self, domain, spaces, power):
        from .. import utilities
        self._domain = DomainTuple.make(domain)
        if spaces is None:
            self._spaces = None
        else:
            self._spaces = utilities.parse_spaces(spaces, len(self._domain))
        self._power = int(power)
        self._capability = self._all_ops

    def apply(self, x, mode):
        self._check_input(x, mode)
        power = self._power if (mode & 3) else -self._power
        return x.weight(power, spaces=self._spaces)


class Realizer(EndomorphicOperator):
    """Operator returning the real component of its input.

    Parameters
    ----------
    domain: Domain, tuple of domains or DomainTuple
        domain of the input field

    """
    def __init__(self, domain):
        self._domain = DomainTuple.make(domain)
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        return x.real


class FieldAdapter(LinearOperator):
    """Operator for conversion between Fields and MultiFields.

    Parameters
    ----------
    tgt : Domain, tuple of Domain, DomainTuple, dict or MultiDomain:
        If this is a Domain, tuple of Domain or DomainTuple, this will be the
        operator's target, and its domain will be a MultiDomain consisting of
        its domain with the supplied `name`
        If this is a dict or MultiDomain, everything except for `name` will
        be stripped out of it, and the result will be the operator's target.
        Its domain will then be the DomainTuple corresponding to the single
        entry in the operator's domain.

    name : String
        The relevant key of the MultiDomain.
    """

    def __init__(self, tgt, name):
        from ..sugar import makeDomain
        tmp = makeDomain(tgt)
        if isinstance(tmp, DomainTuple):
            self._target = tmp
            self._domain = MultiDomain.make({name: tmp})
        else:
            self._domain = tmp[name]
            self._target = MultiDomain.make({name: tmp[name]})
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        if isinstance(x, MultiField):
            return x.values()[0]
        else:
            return MultiField(self._tgt(mode), (x,))

    def __repr__(self):
        return 'FieldAdapter'


class _SlowFieldAdapter(LinearOperator):
    """Operator for conversion between Fields and MultiFields.
    The operator is built so that the MultiDomain is always the target.
    Its domain is `tgt[name]`

    Parameters
    ----------
    dom : dict or MultiDomain:
        the operator's dom

    name : String
        The relevant key of the MultiDomain.
    """

    def __init__(self, dom, name):
        from ..sugar import makeDomain
        tmp = makeDomain(dom)
        if not isinstance(tmp, MultiDomain):
            raise TypeError("MultiDomain expected")
        self._name = str(name)
        self._domain = tmp
        self._target = tmp[name]
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        if isinstance(x, MultiField):
            return x[self._name]
        else:
            return MultiField.from_dict({self._name: x},
                                        domain=self._tgt(mode))

    def __repr__(self):
        return '_SlowFieldAdapter'


def ducktape(left, right, name):
    """Convenience function creating an operator that converts between a
    DomainTuple and a MultiDomain.

    Parameters
    ----------
    left : None, Operator, or Domainoid
        Something describing the new operator's target domain.
        If `left` is an `Operator`, its domain is used as `left`.

    right : None, Operator, or Domainoid
        Something describing the new operator's input domain.
        If `right` is an `Operator`, its target is used as `right`.

    name : string
        The component of the `MultiDomain` that will be extracted/inserted

    Notes
    -----
    - one of the involved domains must be a `DomainTuple`, the other a
      `MultiDomain`.
    - `left` and `right` must not be both `None`, but one of them can (and
      probably should) be `None`. In this case, the missing information is
      inferred.

    Returns
    -------
    FieldAdapter or _SlowFieldAdapter
        an adapter operator converting between the two (possibly
        partially inferred) domains.
    """
    from ..sugar import makeDomain
    from .operator import Operator
    if isinstance(right, Operator):
        right = right.target
    elif right is not None:
        right = makeDomain(right)
    if isinstance(left, Operator):
        left = left.domain
    elif left is not None:
        left = makeDomain(left)
    if left is None:  # need to infer left from right
        if isinstance(right, MultiDomain):
            left = right[name]
        else:
            left = MultiDomain.make({name: right})
    elif right is None:  # need to infer right from left
        if isinstance(left, MultiDomain):
            right = left[name]
        else:
            right = MultiDomain.make({name: left})
    lmulti = isinstance(left, MultiDomain)
    rmulti = isinstance(right, MultiDomain)
    if lmulti+rmulti != 1:
        raise ValueError("need exactly one MultiDomain")
    if lmulti:
        if len(left) == 1:
            return FieldAdapter(left, name)
        else:
            return _SlowFieldAdapter(left, name).adjoint
    if rmulti:
        if len(right) == 1:
            return FieldAdapter(left, name)
        else:
            return _SlowFieldAdapter(right, name)
    raise ValueError("must not arrive here")


class GeometryRemover(LinearOperator):
    """Operator which transforms between a structured and an unstructured
    domain.

    Parameters
    ----------
    domain: Domain, tuple of Domain, or DomainTuple:
        the full input domain of the operator.
    space: int, optional
        The index of the subdomain on which the operator should act.
        If None, it acts on all spaces.

    Notes
    -----
    The operator will convert every sub-domain of its input domain to an
    UnstructuredDomain with the same shape. No weighting by volume factors
    is carried out.
    """

    def __init__(self, domain, space=None):
        self._domain = DomainTuple.make(domain)
        if space is not None:
            tgt = [dom for dom in self._domain]
            tgt[space] = UnstructuredDomain(self._domain[space].shape)
        else:
            tgt = [UnstructuredDomain(dom.shape) for dom in self._domain]
        self._target = DomainTuple.make(tgt)
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        return x.cast_domain(self._tgt(mode))


class NullOperator(LinearOperator):
    """Operator corresponding to a matrix of all zeros.

    Parameters
    ----------
    domain : DomainTuple or MultiDomain
        input domain
    target : DomainTuple or MultiDomain
        output domain
    """

    def __init__(self, domain, target):
        from ..sugar import makeDomain
        self._domain = makeDomain(domain)
        self._target = makeDomain(target)
        self._capability = self.TIMES | self.ADJOINT_TIMES

    @staticmethod
    def _nullfield(dom):
        if isinstance(dom, DomainTuple):
            return Field(dom, 0)
        else:
            return MultiField.full(dom, 0)

    def apply(self, x, mode):
        self._check_input(x, mode)
        return self._nullfield(self._tgt(mode))


class _PartialExtractor(LinearOperator):
    def __init__(self, domain, target):
        if not isinstance(domain, MultiDomain):
            raise TypeError("MultiDomain expected")
        if not isinstance(target, MultiDomain):
            raise TypeError("MultiDomain expected")
        self._domain = domain
        self._target = target
        for key in self._target.keys():
            if not (self._domain[key] is not self._target[key]):
                raise ValueError("domain mismatch")
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        if mode == self.TIMES:
            return x.extract(self._target)
        return MultiField.from_dict({key: x[key] for key in x.domain.keys()})
