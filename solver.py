from typing import Any

# again using Any here instead of Board to avoid circular import bull

# def print_2d_array_bool(arr: [[bool]]) -> None:
#     for row in arr:
#         for elm in row:
#             if elm:
#                 print('X', end='')
#             else:
#                 print('_', end='')
#         print()
#     print()
#
#
# def print_2d_array(arr: [[Any]]) -> None:
#     for row in arr:
#         for elm in row:
#             print(elm, end='')
#         print()
#     print()


def get_counts_board(b: Any) -> [[int]]:
    from meeleymine import full, Cell
    counts = full(len(b.real_board[0]), len(b.real_board), 0)
    for rid, row in enumerate(b.real_board):
        for cid, cell in enumerate(row):
            c = b.count_mines(rid, cid)
            if b.real_board[rid][cid] == Cell.MINE:
                c += 1
            counts[rid][cid] = c
    return counts


def all_true(arr: [[bool]]) -> True:
    for row in arr:
        for elm in row:
            if not elm:
                return False
    return True


def get_unvisited(visited: [[bool]]) -> (int, int):
    for rid, row in enumerate(visited):
        for cid, elm in enumerate(row):
            if not elm:
                return rid, cid
    return -1, -1


def can_have_mine(b: Any, arr: [[int]], coord: (int, int)) -> bool:
    from meeleymine import Board
    # check if the cell is out of bounds
    if not b.in_bounds(coord):
        return False

    # check if any of the neighbors of (row, col)
    # supports (row, col) to have a mine
    neighbors = Board.neighbors.copy()
    neighbors.append((0, 0))
    row, col = coord
    for n_r, n_c in neighbors:
        if b.in_bounds((n_r + row, n_c + col)):
            if arr[n_r + row][n_c + col] - 1 < 0:
                return False

    # if (row, col) is valid to have a mine
    for n_r, n_c in neighbors:
        if b.in_bounds((n_r + row, n_c + col)):
            arr[n_r + row][n_c + col] -= 1

    return True


def is_done(arr, visited):
    done = True
    # if mine is assigned to the cells satisfying the input grid
    # then return True
    for rid, row in enumerate(arr):
        for cid, elm in enumerate(row):
            done = done and arr[rid][cid] == 0 and visited[rid][cid]
    return done


# https://www.geeksforgeeks.org/minesweeper-solver/
def solve_mine_sweeper(
        b: Any,
        arr: [[int]],
        grid: [[bool]],
        visited: [[bool]]) -> bool:
    done = is_done(arr, visited)
    if done:
        return True

    # If all the cells are visited
        # else return False
    # find an unvisited cell (row, col) and mark as visited
    row, col = get_unvisited(visited)
    if row == -1 and col == -1:
        return False

    visited[row][col] = True
    # if a mine can be assigned to the position (row, col) then perform the
    # following steps:
    if can_have_mine(b, arr, (row, col)):
        # - mark grid[row][col] as True
        grid[row][col] = True
        # - Decrease the number of mine of the neighboring cells of (row,
        #   col) in arr by 1 (done in can_have_mine call)
        # - Recursively call solve_mine_sweeper() with (row, col) having a mine
        #   and if it returns true, then a solution exists. Return true for
        #   current recursive call
        if solve_mine_sweeper(b, arr, grid, visited):
            return True
        # - Otherwise, reset the position (row, col) i.e. mark grid[row][col]
        grid[row][col] = False
        #   as False and increase the number of mine of the neighboring cells
        #   of (row,col) in arr by 1 from
        from meeleymine import Board
        neighbors = Board.neighbors.copy()
        neighbors.append((0, 0))
        for n_r, n_c in neighbors:
            if b.in_bounds((n_r + row, n_c + col)):
                arr[n_r + row][n_c + col] += 1
    # if the function  solve_mine_sweeper with (row,col) having no mine,
    # returns true, then it means a solution exists. Return true from the
    # current recursive call
    if solve_mine_sweeper(b, arr, grid, visited):
        return True
    # If the recursive call in the step above returns False, that means the
    # solution doesn't exist. Therefore, return false from the current
    # recursive call
    return False


def solvable(b: Any) -> bool:
    from meeleymine import full
    counts = get_counts_board(b)
    # print_2d_array(counts)

    grid = full(len(b.real_board[0]), len(b.real_board), False)
    visited = full(len(b.real_board[0]), len(b.real_board), False)
    return solve_mine_sweeper(b, counts, grid, visited)

    # print_2d_array_bool(grid)
    # print_2d_array_bool(visited)


def main() -> None:
    from meeleymine import Board, Difficulty
    from load_config import load_config
    b = Board(9, 9, 0.123, Difficulty.CUSTOM, load_config(), None)
    b.populate()
    print(solvable(b))


if __name__ == '__main__':
    main()
