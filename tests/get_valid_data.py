from app.services.database import RobotDatabase
from app.services.types import RobotState


def get_valid() -> list[RobotState]:
    db = RobotDatabase()
    states = db.get_by_mac("FC:E8:C0:7C:21:8C")
    states_valid: list[RobotState] = []
    tolerance = 1.0

    prev_state: RobotState | None = None
    total = 0

    for i in range(1, len(states)):
        if states[i].distance_hall == 0:
            if states[i].distance_front > 300 or states[i].distance_side > 300:
                continue
            sequence_length = min(3, len(states) - i)
            group = states[i : i + min(sequence_length, i)]
            is_similiar = all(
                abs(group[j].distance_front - group[j + 1].distance_front) <= tolerance
                and abs(group[j].distance_side - group[j + 1].distance_side)
                <= tolerance
                for j in range(len(group) - 1)
            )

            if is_similiar:
                corner_state = group[0]
                corner_state.is_corner = True
                corner_state.total = (
                    total
                    + states_valid[-1].distance_front
                    - corner_state.distance_front
                )
                if not states_valid[-1].is_corner:
                    states_valid.append(corner_state)
                i = i + sequence_length
            continue

        if not prev_state:
            prev_state = states[i]
            continue

        total += states[i].distance_hall
        total = round(total, 2)

        if abs(states[i].angle - prev_state.angle) >= 50:
            total = 0

        if (
            abs(
                states[i].distance_front
                + states[i].distance_hall
                - prev_state.distance_front
            )
            <= 100
        ):
            states[i].total = total
            states_valid.append(states[i])
        prev_state = states[i]

    return states_valid
