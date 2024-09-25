import math
from math import factorial, prod
from typing import Iterator, Optional

from pydantic import BaseModel, ConfigDict, PositiveInt, NonNegativeInt, model_validator


class NS(BaseModel):
    """
    "named size", wraps length + name
    """

    quantity: Optional[int]=0
    model_config = ConfigDict(validate_assignment=True)

    length: PositiveInt
    name: Optional[str] = None

    def __lt__(self, other):
        return self.length < self.length

    def __hash__(self) -> int:
        return hash((self.length, self.name))

    def __str__(self):
        return f"{self.name}: l={self.length}" if self.name else f"l={self.length}"

    def __repr__(self):
        return f"NS(length={self.length}, name={self.name})" if self.name else f"NS(length={self.length})"


class INS(NS):
    """
    "inventory named size", wraps length + name + quantity
    """
    quantity: Optional[PositiveInt] = None

    def __str__(self):
        return f"{self.name}: l={self.length}, q={self.quantity}" if self.name else f"l={self.length}, q={self.quantity}"

    def __repr__(self):
        return f"INS(length={self.length}, name={self.name}, quantity={self.quantity})"
    
    def as_base(self) -> NS:
        return NS(length=self.length, name=self.name)


class QNS(NS):
    """
    "quantity + named size", adds quantity
    """
    quantity: int

    def __str__(self):
        return f"{self.name}: l={self.length}, n={self.quantity}"

    def __repr__(self):
        return f"QNS(length={self.length}, name={self.name}, quantity={self.quantity})"

    def as_base(self) -> NS:
        return NS(length=self.length, name=self.name)


class Job(BaseModel):
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    cut_width: NonNegativeInt = 0
    stocks: tuple[INS, ...]  # Use INS para stocks
    required: tuple[QNS, ...]

    def iterate_required(self) -> Iterator[QNS]:
        """Yields all lengths times amount, sorted descending."""
        for target in sorted(self.required, reverse=True):
            for _ in range(target.quantity):
                print(f"Yielding required size: {target.length} (quantity: {target.quantity})")
                yield target  # Remover a conversão para NS



    def iterate_stocks(self) -> Iterator[NS]:
        """Yields all lengths times amount (including unwrapped infinite stocks); sorted descending."""
        for target in sorted(self.stocks, reverse=True):
            if all(req.length > target.length for req in self.required):
                continue
            iterations = target.quantity if target.quantity else math.ceil(
                (self.sum_of_required() * 2) / target.length)
            for _ in range(iterations):
                yield target.as_base()

    def sum_of_required(self):
        """Calculates the total length of required items."""
        return sum([(target.length + self.cut_width) * target.quantity for target in self.required])

    def n_entries(self) -> int:
        """Number of possible combinations of target sizes."""
        return sum([target.quantity for target in self.required])

    def n_combinations(self) -> float | int:
        """Number of possible combinations for job; returns infinite if too large."""
        return self.n_combinations_required() * self.n_combinations_stocks()

    def n_combinations_required(self) -> float | int:
        n_targets = sum([target.quantity for target in self.required])
        if n_targets > 100:
            return math.inf
        return int(factorial(n_targets) / prod([factorial(n.quantity) for n in self.required]))

    def n_combinations_stocks(self) -> float | int:
        """Number of possible combinations of target sizes; returns infinite if too large."""
        n_stocks = len([target for target in self.iterate_stocks()])
        if n_stocks > 100:
            return math.inf
        return int(factorial(n_stocks) / prod([factorial(n.quantity if n.quantity else math.ceil(
            (self.sum_of_required() * 2) / n.length)) for n in self.stocks]))

    @model_validator(mode='after')
    def assert_valid(self) -> 'Job':
        print("Validating job...")
        if len(self.stocks) <= 0:
            raise ValueError("Job has no stocks")
        if len(self.required) <= 0:
            raise ValueError("Job has no required sizes")

        if any(all(target.length > stock.length for stock in self.stocks) for target in self.required):
            raise ValueError("Job has target sizes longer than the stock")

        if self.sum_of_required() > sum([stock.length for stock in self.iterate_stocks()]):
            raise ValueError("Job has more targets than the stock available")
        
        print("Validation passed.")

        return self


    def __eq__(self, other):
        return (
                self.stocks == other.stocks
                and self.cut_width == other.cut_width
                and self.required == other.required
        )

    def __hash__(self) -> int:
        return hash((str(sorted(self.stocks)), self.cut_width, str(sorted(self.required))))
    

