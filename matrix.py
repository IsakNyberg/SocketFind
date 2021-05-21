from math import sqrt


class VectorSpace:
    def __add__(self, other):
        raise NotImplementedError("Addition not implemented")

    def __radd__(self, other):  # Vector Space addition is commutative
        return self + other

    def __mul__(self, other):
        raise NotImplementedError('Scaling not implemented')

    def __rmul__(self, other):  # Vector Space scaling is commutative
        return self * other

    def __neg__(self):
        return self * -1

    def __sub__(self, other):
        return self + -other

    def __rsub__(self, other):
        return other + -self

    def __eq__(self, other):
        raise NotImplementedError('Equality not implemented')

    def __abs__(self):
        raise NotImplementedError('Norm not implemented')


class Matrix(VectorSpace):  # TODO extract matrix and common to linalg module?
    """
    Matrix implementation. Index with M[i,j] (start at zero!)

    Supports addition (+), subtraction (-),
    negation (-m), scaling (*),
    matrix multiplication(@), powers (**).

    det(self) returns determinant (memoised).
    transpose(m) returns m transposed.
    row_switch(self, i, j) elementary row operation swap.
    row_mult(self, i, m) elementary row operation multiply.
    row_add(self, i, j, m) elementary row operation add.

    _value: list of values.
    n: number of rows.
    m: number of columns.
    """
    _IS_MATRIX = True
    _IS_VECTOR = False

    def __init__(self, rows):  # assumes input is list of lists!
        self._value = rows
        self.n = len(rows)
        # if self.n == 0:
        #     raise ValueError('Matrix with zero rows')
        self.m = len(rows[0])
        # if self.m == 0:
        #     raise ValueError('Matrix with zero columns')
        # for i, row in enumerate(self._value):
        #     if len(row) != self.m:
        #         raise ValueError('Matrix with unequal row lengths')
        self._det = None

    @property
    def size(self):
        return self.n, self.m

    @property
    def det(self):
        """
        Calculate and store determinant.
        :return: int
        """
        if self._det is None:  # kinda-sorta-memoised determinant
            v = self._value
            if self.n != self.m:
                self._det = 0
            elif self.n == 1:
                self._det = v[0][0]
            elif self.n == 2:
                self._det = (
                    v[0][0]*v[1][1] -
                    v[0][1]*v[1][0]
                )
            elif self.n == 3:
                # a(ei - fh) - b(di - fg) + c(dh - eg)
                self._det = (
                    v[0][0]*(v[1][1]*v[2][2] - v[1][2]*v[2][1]) -
                    v[0][1]*(v[1][0]*v[2][2] - v[1][2]*v[2][0]) + 
                    v[0][2]*(v[1][0]*v[2][1] - v[1][1]*v[2][0])
                )  # I would feel bad about doing this if it wasn't the best way
            else:
                raise NotImplementedError('High order det not implemented yet')
        return self._det

    def __repr__(self):
        res_parts = []
        for row in self._value:
            res_parts.append('\t'.join(map(str, row)))
        res = ')\n('.join(res_parts)
        return '(' + res + ')'

    def __getitem__(self, pos):
        """index row with M[int] or value with M[int,int]. Index from 0."""
        try:
            i, j = pos
            return self._value[i][j]
        except TypeError:  # pos not a tuple => requesting full row
            return self._value[pos]

    def __setitem__(self, pos, x):
        """index row with M[int] or value with M[int,int]. Index from 0."""
        try:
            i, j = pos
            self._value[i][j] = x
        except TypeError:  # pos not a tuple => requesting full row
            self._value[pos] = x

    def __iadd__(self, other):
        if self.size != other.size:
            raise ValueError('Different Sizes!')
        n, m = self.size
        self_value = self._value
        other_value = other._value
        for i in range(n):
            for j in range(m):
                self_value[i][j] += other_value[i][j]
        return self

    def __add__(self, other):
        if other == 0:  # allows sum()
            return self
        res = self.copy()
        res += other
        return res

    def __imul__(self, other):  # scalar multiplication only!
        n, m = self.size
        self_value = self._value
        for i in range(n):
            for j in range(m):
                self_value[i][j] *= other
        return self

    def __mul__(self, other):
        """Scalar multiplication."""  # TODO implement elementwise M*M?
        res = self.copy()
        res *= other
        return res

    def __matmul__(self, other):
        self_value = self._value  # avoid dots in expensive loops
        self_n, self_m = self.size
        res = []
        res_append = res.append
        v2 = other._value  # other._value is private you need at add a other.getvalue() v2 is not used, remove?
        other_n, other_m = other.size
        other_value = other._value  # other._value is private you need at add a other.getvalue()
        if self_m != other_n:
            raise ValueError(f'Incompatible Sizes {self_m}, {other_n}')
        if other._IS_VECTOR:  # other is vector => return vector  again other._IS_VECTOR is private
        # if isinstance(other, Vector):
            for i in range(self_n):
                value = 0
                for j in range(self_m):
                    value += self_value[i][j] * other_value[j]
                res_append(value)
            return Vector(res)
        else:  # other is matrix => return matrix
            for i in range(self_n):
                row = []
                row_append = row.append
                for j in range(other_m):
                    value = 0
                    for k in range(self_m):
                        value += self_value[i][k] * other_value[k][j]
                    row_append(value)
                res_append(row)
            res = Matrix(res)
            if None not in (self._det, other._det):
                res._det = self._det * other._det  # might as well
            return res

    def __pow__(self, other):
        res = self
        for x in range(other-1):
            res *= self
        return res

    def __eq__(self, other):
        try:
            return self._value == other.value
        except AttributeError:
            return False

    @staticmethod
    def transpose(m):
        return Matrix(list(zip(*m._value)))  # bro?

    def to_vector(self):
        """
        Converts single-column matrix into a vector.
        :return: Vector
        """
        if self.m != 1:
            return ValueError('Not a vector')
        return Vector(list(zip(*self._value)))
        # could be done with transpose but it makes matrix which takes too long
        # TODO is this a list of lists?

    def copy(self):  # TODO add det?
        return Matrix(self._value.copy())

    def row_switch(self, i, j):
        """
        Swap row positions.
        :param i: index of row 1
        :param j: index of row 2
        """
        self._value[i], self._value[j] = self._value[j], self._value[i]

    def row_mult(self, i, m):
        """
        Multiply a row by a scalar.
        :param i: index of row
        :param m: non-zero scalar
        """
        if m == 0:
            raise ValueError("m can't be zero!")
        self._value[i] = [m*x for x in self._value[i]]

    def row_add(self, i, j, m):
        """
        Add a row to another (with scaling).
        :param i: index of row to be changed
        :param j: index of row to add
        :param m: non-zero scalar
        :return:
        """
        if m == 0:
            raise ValueError("m can't be zero!")
        self._value[i] = [x+m*y for x, y in zip(self._value[i], self._value[j])]


class Vector(Matrix):  # these are saved as horizontal but treated as vertical.
    """
    Subclass of Matrix for single-column matrices. Index with M[i,j] (start at zero!)

    length(self) returns euclidean norm (memoised).
    dot(self, other) returns dot product.
    cross(self, other) return cross product.
    project(self, basis) return projection onto basis.

    _value: list of values.
    n: int, number of entries.
    m: int, 1.
    """
    # I'm pretty sure it should be a subclass of VectorSpace. All properties of a Matrix is NOT inherited

    _IS_VECTOR = True

    def __init__(self, values):
        self._value = values
        self.n = len(self._value)
        if self.n == 0:
            raise ValueError('Vector of size zero')
        self.m = 1
        self._length = None

    def __repr__(self):
        return '(' + (', '.join(str(x) for x in self._value)) + ')'  # add rounding

    def __getitem__(self, pos):
        return self._value[pos]

    def __setitem__(self, pos, x):
        self._value[pos] = x

    def __iadd__(self, other):
        if self.n != other.n:
            raise ValueError(f'Vectors of Different Sizes {self}, {other}')
        self_value = self._value
        other_value = other.to_list()
        for i in range(self.n):
            self_value[i] += other_value[i]
        return self

    def __imul__(self, other):  # scalar multiplication only!
        self_value = self._value
        for i in range(self.n):
            self_value[i] *= other
        return self

    def __matmul__(self, other):  # v@m = m, m@v = v, v@v = int
        if other._IS_VECTOR:
            return self.dot(other)  # v dot w = v^t matmul w
        else:  # doesn't account for v matmul w with len(v)=len(w)=1 TODO
            return self.to_matrix() @ other

    @property
    def length_squared(self):  # calculate length squared is cheaper than length
        """
        Returns the square euclidean norm of vector.
        :return: int
        """
        return sum([c**2 for c in self._value])

    @property
    def length(self):  # another semi-memoised expensive function
        """
        Returns euclidean norm of vector.
        :return: int
        """
        if self._length is None:
            self._length = sqrt(self.length_squared)
        return self._length

    @property
    def unit(self):
        return self * (1/self.length)

    def to_matrix(self):
        """Converts Vector to Matrix."""
        return Matrix(list(zip(self._value)))
        # TODO is this a list of lists?

    def to_list(self):
        return self._value

    def copy(self):
        return Vector(self._value.copy())

    def orthant(self):
        # do you mean quadrant?
        res = 0
        for n in self._value:
            res *= 2
            if n > 0:
                res += 1
        return res

    def dot(self, other):
        """
        Dot Product.
        :param other: Vector
        :return: self·other
        """
        #if not isinstance(other, Vector):
        #    raise TypeError('Incompatible type: {}'.format(type(other)))
        try:
            #turned = Matrix.transpose(self.to_matrix())
            turned = Matrix([self._value])
            return (turned@other)._value[0]  # matrix only has one element
        except AttributeError:
            raise TypeError('Incompatible type: {}'.format(type(other)))

    def cross(self, other):
        """
        Cross Product. Only defined for 3 dimensional vectors.
        :param other: Vector
        :return: self⨯other
        """
        if not isinstance(other, Vector):
            raise TypeError('Incompatible type: {}'.format(type(other)))
        if not (self.n == other.n == 3):  # Also exists for 7 dimensions... implement?
            raise ValueError('Incompatible Sizes')

        a1, a2, a3 = self._value
        b1, b2, b3 = other._value

        s1 = a2 * b3 - a3 * b2
        s2 = a3 * b1 - a1 * b3
        s3 = a1 * b2 - a2 * b1

        return Vector([s1, s2, s3])

    def project(self, basis):
        """
        Return projection of vector in given basis.
        :param basis: iterable of Vectors
        :return: Vector
        """
        res = Vector([0, 0, 0])
        for base in basis:
            res += (self.dot(base)/base.dot(base)) * base  # inefficient TODO
        return res

    def limit(self, lim):
        for i in range(self.n):
            self._value[i] = max(min(lim, self._value[i]), -lim)

    def limit_zero(self, lim):
        for i in range(self.n):
            self._value[i] = max(min(lim, self._value[i]), 0)
