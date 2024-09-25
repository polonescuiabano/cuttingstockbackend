#!python3
import copy
from time import perf_counter
from more_itertools import distinct_permutations
from app.settings import solverSettings
from app.solver.data.Job import Job, QNS, NS, INS
from app.solver.data.Result import Result, SolverType, ResultEntry
from app.solver.utils import create_result_entry, sort_entries, find_best_solution
import logging
from time import perf_counter

# Configure o logging
logging.basicConfig(level=logging.DEBUG)  # Altere para INFO ou ERROR conforme necessário
logger = logging.getLogger(__name__)

def solve(job: Job) -> Result:
    logger.debug("Iniciando a solução para o trabalho: %s", job)

    start_time = perf_counter()
    
    layout: tuple[ResultEntry, ...]
    solver_type: SolverType

    # Log do número de combinações
    n_combinations = job.n_combinations()
    logger.debug("Número de combinações: %d", n_combinations)
    
    if n_combinations <= solverSettings.bruteforce_max_combinations:
        logger.info("Usando solução por força bruta.")
        layout = _solve_bruteforce(job)
        solver_type = SolverType.bruteforce
    elif job.n_entries() <= solverSettings.solver_n_max:
        logger.info("Usando solução FFD.")
        layout = _solve_FFD(job)
        solver_type = SolverType.FFD
    elif job.n_entries() <= solverSettings.gapfill_max:
        logger.info("Usando solução gapfill.")
        layout = _solve_gapfill(job)
        solver_type = SolverType.gapfill
    else:
        logger.error("Entrada muito grande: %d combinações", n_combinations)
        raise OverflowError("Input too large")

    time_us = int((perf_counter() - start_time) * 1000 * 1000)
    logger.debug("Tempo de solução: %d microssegundos", time_us)

    result = Result(job=job, solver_type=solver_type, time_us=time_us, layout=layout)
    logger.debug("Resultado da solução: %s", result)

    return result


def _solve_bruteforce(job: Job) -> tuple[ResultEntry, ...]:
    minimal_trimmings = float('inf')
    best_results: set[tuple[ResultEntry, ...]] = set()

    required_orderings = list(distinct_permutations(job.iterate_required()))
    for stock_ordering in distinct_permutations(job.iterate_stocks()):
        for required_ordering in required_orderings:
            result = _group_into_lengths(stock_ordering, required_ordering, job.cut_width)
            if result is None:
                continue
            trimmings = sum(lt.trimming for lt in result)
            if trimmings < minimal_trimmings:
                minimal_trimmings = trimmings
                best_results = {sort_entries(result)}
            elif trimmings == minimal_trimmings:
                best_results.add(sort_entries(result))

    assert best_results, "No valid solution found"
    return find_best_solution(best_results)


def _group_into_lengths(stocks: tuple[INS, ...], sizes: tuple[QNS, ...], cut_width: int) -> tuple[ResultEntry, ...] | None:
    available = sorted(stocks, key=lambda x: x.length, reverse=True)  # Ordena por comprimento decrescente
    required = {size: size.quantity for size in sizes}  # Dicionário de quantidades restantes
    result: list[ResultEntry] = []

    while any(quantity > 0 for quantity in required.values()):
        best_stock = None
        best_cuts = []
        best_trimming = float('inf')

        for stock in available:
            cut_sum = 0
            current_cuts = []
            current_required = required.copy()  # Copia das quantidades restantes

            for size in sorted(current_required.keys(), key=lambda x: x.length, reverse=True):
                while current_required[size] > 0 and (cut_sum + size.length + cut_width) <= stock.length:
                    current_cuts.append(size)  # Adiciona a medida diretamente
                    cut_sum += size.length + cut_width
                    current_required[size] -= 1  # Reduz a quantidade disponível

            trimming = stock.length - cut_sum + cut_width
            if current_cuts and trimming < best_trimming:
                best_trimming = trimming
                best_stock = stock
                best_cuts = current_cuts.copy()

        if best_stock and best_cuts:
            result.append(create_result_entry(best_stock, best_cuts, cut_width))
            # Atualiza as quantidades restantes
            for size in best_cuts:
                required[size] -= 1

    # Verifica se todas as quantidades foram utilizadas
    if all(quantity == 0 for quantity in required.values()):
        return tuple(result)
    
    return None

def _solve_FFD(job: Job) -> tuple[ResultEntry, ...]:
    minimal_trimmings = float('inf')
    best_results: set[tuple[ResultEntry, ...]] = set()

    stock_orderings = list(distinct_permutations(job.iterate_stocks()))
    required_orderings = list(distinct_permutations(job.iterate_required()))

    for stock_ordering in stock_orderings:
        for required_ordering in required_orderings:
            result = _group_into_lengths(stock_ordering, required_ordering, job.cut_width)
            if result is None:
                continue

            trimmings = sum(lt.trimming for lt in result)
            if trimmings < minimal_trimmings:
                minimal_trimmings = trimmings
                best_results = {sort_entries(result)}
            elif trimmings == minimal_trimmings:
                best_results.add(sort_entries(result))

    assert best_results, "No valid solution found"
    return find_best_solution(best_results)

def _solve_gapfill(job: Job) -> tuple[ResultEntry, ...]:
    minimal_trimmings = float('inf')
    best_results: set[tuple[ResultEntry, ...]] = set()

    stock_orderings = list(distinct_permutations(job.iterate_stocks()))
    required_orderings = list(distinct_permutations(job.iterate_required()))

    for stock_ordering in stock_orderings:
        for required_ordering in required_orderings:
            result = _group_into_lengths(stock_ordering, required_ordering, job.cut_width)
            if result is None:
                continue

            trimmings = sum(lt.trimming for lt in result)
            if trimmings < minimal_trimmings:
                minimal_trimmings = trimmings
                best_results = {sort_entries(result)}
            elif trimmings == minimal_trimmings:
                best_results.add(sort_entries(result))

    assert best_results, "No valid solution found"
    return find_best_solution(best_results)


