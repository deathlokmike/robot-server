from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

from tests.get_valid_data import get_valid

if TYPE_CHECKING:
    from app.services.types import CleanerState


class Direction(Enum):
    forward = 0
    backward = 180
    left = 90
    right = 270


class LineException(Exception):
    pass


@dataclass
class Coordinate:
    x: np.double = np.double(0)
    y: np.double = np.double(0)

    def __iter__(self):
        return iter((self.x, self.y))


def get_direction(angle: float) -> Direction:
    if angle <= 45 or angle >= 316:
        return Direction.forward
    elif 46 <= angle <= 135:
        return Direction.left
    elif 136 <= angle <= 225:
        return Direction.backward
    return Direction.right


def handle_forward(state: "CleanerState", direction: Direction, offset: "Coordinate"):
    x = offset.x - state.distance_side * np.cos(
        np.radians(state.angle - direction.value)
    )
    y = offset.y + state.total * np.cos(np.radians(state.angle - direction.value))

    x_wall_side = offset.x
    y_wall_side = y + state.distance_side * np.sin(
        np.radians(state.angle - direction.value)
    )

    x_wall_front = x - state.distance_front * np.sin(
        np.radians(state.angle - direction.value)
    )
    y_wall_front = y + state.distance_front * np.cos(
        np.radians(state.angle - direction.value)
    )

    return (
        Coordinate(x, y),
        Coordinate(x_wall_side, y_wall_side),
        Coordinate(x_wall_front, y_wall_front),
    )


def handle_left(state: "CleanerState", direction: Direction, offset: "Coordinate"):
    x = offset.x - state.total * np.cos(np.radians(state.angle - direction.value))
    y = offset.y - state.distance_side * np.cos(
        np.radians(state.angle - direction.value)
    )

    x_wall_side = x - state.distance_side * np.sin(
        np.radians(state.angle - direction.value)
    )
    y_wall_side = offset.y

    x_wall_front = x - state.distance_front * np.cos(
        np.radians(state.angle - direction.value)
    )
    y_wall_front = y + state.distance_front * np.sin(
        np.radians(state.angle - direction.value)
    )

    return (
        Coordinate(x, y),
        Coordinate(x_wall_side, y_wall_side),
        Coordinate(x_wall_front, y_wall_front),
    )


def handle_backward(state: "CleanerState", direction: Direction, offset: "Coordinate"):
    x = offset.x + state.distance_side * np.cos(
        np.radians(state.angle - direction.value)
    )
    y = offset.y - state.total * np.cos(np.radians(state.angle - direction.value))

    x_wall_side = offset.x
    y_wall_side = y - state.distance_side * np.sin(
        np.radians(state.angle - direction.value)
    )

    x_wall_front = x + state.distance_front * np.sin(
        np.radians(state.angle - direction.value)
    )
    y_wall_front = y - state.distance_front * np.cos(
        np.radians(state.angle - direction.value)
    )

    return (
        Coordinate(x, y),
        Coordinate(x_wall_side, y_wall_side),
        Coordinate(x_wall_front, y_wall_front),
    )


def handle_right(state: "CleanerState", direction: Direction, offset: "Coordinate"):
    x = offset.x + state.total * np.cos(np.radians(state.angle - direction.value))
    y = offset.y + state.distance_side * np.cos(
        np.radians(state.angle - direction.value)
    )

    x_wall_side = x + state.distance_side * np.cos(
        np.radians(state.angle - direction.value)
    )
    y_wall_side = offset.y

    x_wall_front = x + state.distance_front * np.cos(
        np.radians(state.angle - direction.value)
    )
    y_wall_front = y - state.distance_front * np.sin(
        np.radians(state.angle - direction.value)
    )

    return (
        Coordinate(x, y),
        Coordinate(x_wall_side, y_wall_side),
        Coordinate(x_wall_front, y_wall_front),
    )


def process_states(states: list["CleanerState"]):
    robot_cords: list[Coordinate] = []
    walls: list[list[Coordinate]] = [[], []]
    previous_direction = Direction.forward
    offset = Coordinate()
    corner_offset = 0.0
    k = 0
    for state in states:
        direction = get_direction(state.angle)
        if direction != previous_direction:
            if (
                previous_direction == Direction.forward and direction == Direction.left
            ) or (
                previous_direction == Direction.backward
                and direction == Direction.right
            ):
                _, y = zip(*walls[k + 1])
                y_offset = np.median(np.array(y))
                sign = -1 if direction == Direction.left else 1
                x_offset = walls[k][-1].x + sign * corner_offset
                offset = Coordinate(x_offset, y_offset)
            elif (
                previous_direction == Direction.left and direction == Direction.backward
            ) or (
                previous_direction == Direction.right and direction == Direction.forward
            ):
                x, _ = zip(*walls[k + 1])
                x_offset = np.median(np.array(x))
                sign = -1 if direction == Direction.backward else 1
                y_offset = walls[k][-1].y + sign * corner_offset
                offset = Coordinate(x_offset, y_offset)

            k += 1
            walls.append([])
            previous_direction = direction

        if state.is_corner:
            corner_offset = state.distance_side * np.cos(
                np.radians(state.angle - direction.value)
            )

        if direction == Direction.forward:
            pos, wall_side, wall_front = handle_forward(state, direction, offset)
        elif direction == Direction.left:
            pos, wall_side, wall_front = handle_left(state, direction, offset)
        elif direction == Direction.backward:
            pos, wall_side, wall_front = handle_backward(state, direction, offset)
        else:
            pos, wall_side, wall_front = handle_right(state, direction, offset)

        walls[k].append(wall_side)
        walls[k + 1].append(wall_front)
        robot_cords.append(pos)

    return robot_cords, walls


def fit_line(points):
    x, y = zip(*points)
    if np.ptp(x) < 100:
        return None, np.mean(x)
    m, b = np.polyfit(x, y, 1)
    return m, b


def build_perp_line(reference_m, ref_point):
    if reference_m is None:
        return 0, ref_point[1]
    if abs(reference_m) < 1e-6:
        return None, ref_point[0]
    perp_m = -1 / reference_m
    b = ref_point[1] - perp_m * ref_point[0]
    return perp_m, b


def intersection(line1, line2):
    m1, b1 = line1
    m2, b2 = line2
    if m1 is None:
        x = b1
        if m2 is None:
            raise LineException
        y = m2 * x + b2
        return (x, y)
    if m2 is None:
        x = b2
        y = m1 * x + b1
        return (x, y)
    if abs(m1 - m2) < 1e-6:
        raise LineException
    x = (b2 - b1) / (m1 - m2)
    y = m1 * x + b1
    return (x, y)


def plot_map(robot_cords, walls):
    fig, ax = plt.subplots()
    intersections = []
    fitted_lines = []

    for wall in walls:
        fitted_lines.append(fit_line(wall))

    for i in range(len(fitted_lines) - 1):
        line_i = fitted_lines[i]
        wall_i1 = walls[i + 1]
        avg_point = (
            np.mean([pt.x for pt in wall_i1]),
            np.mean([pt.y for pt in wall_i1]),
        )
        perp_line = build_perp_line(line_i[0], avg_point)
        try:
            pt_intersect = intersection(line_i, perp_line)
        except LineException:
            continue
        intersections.append(pt_intersect)

    wall_segments = []
    for i, line in enumerate(fitted_lines):
        m, b = line
        if i == 0:
            wall0 = walls[0]
            xs = [pt.x for pt in wall0]
            ys = [pt.y for pt in wall0]
            pt_start = (min(xs), min(ys))
        else:
            pt_start = intersections[i - 1]

        if i < len(intersections):
            pt_end = intersections[i]
        else:
            wall_last = walls[i]
            xs = [pt.x for pt in wall_last]
            ys = [pt.y for pt in wall_last]
            pt_end = (max(xs), max(ys))
        wall_segments.append((pt_start, pt_end))

    # for i, wall in enumerate(walls):
    #     wall_x, wall_y = zip(*wall)
    #     colors = ["red", "green", "purple", "orange", "cyan"]
    #     ax.scatter(wall_x, wall_y, c=colors[i % len(colors)], label=f"Wall {i + 1}")

    for i, (pt_start, pt_end) in enumerate(wall_segments):
        xs = [pt_start[0], pt_end[0]]
        ys = [pt_start[1], pt_end[1]]
        ax.plot(xs, ys, c="k", linewidth=2)

    robot_x, robot_y = zip(*robot_cords)
    ax.scatter(robot_x, robot_y, c="blue", label="Robot")
    ax.legend()
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Map")
    plt.axis("equal")
    plt.grid()
    plt.show()


def main():
    states = get_valid()
    robot_cords, walls = process_states(states)
    plot_map(robot_cords, walls)


if __name__ == "__main__":
    main()
