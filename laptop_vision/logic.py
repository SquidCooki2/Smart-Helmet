"""Pure detection logic (no camera/ML dependencies) so it can be unit tested."""


def arm_extended(wrist, shoulder, margin=0.15, height_tol=0.15):
    """wrist/shoulder are (x, y) normalized coords. True if wrist is out to the side near shoulder height."""
    return abs(wrist[0] - shoulder[0]) > margin and abs(wrist[1] - shoulder[1]) < height_tol


def update_arm_counts(left_cnt, right_cnt, left_out, right_out):
    """Advance consecutive-frame counters. Both-out or neither-out resets the respective counters."""
    left_cnt = left_cnt + 1 if left_out and not right_out else 0
    right_cnt = right_cnt + 1 if right_out and not left_out else 0
    return left_cnt, right_cnt


def next_signal(state, left_cnt, right_cnt, frames_needed):
    if left_cnt > frames_needed:
        return "left"
    if right_cnt > frames_needed:
        return "right"
    if left_cnt == 0 and right_cnt == 0:
        return "off"
    return state


def area_growth(history, now, window):
    """history: iterable of (timestamp, area). Returns ratio newest/oldest within window, or None."""
    recent = [(t, a) for t, a in history if now - t <= window]
    if len(recent) < 2 or recent[0][1] <= 0:
        return None
    return recent[-1][1] / recent[0][1]


def should_alarm(growth, now, last_alarm, threshold, cooldown):
    return growth is not None and growth > threshold and now - last_alarm > cooldown
