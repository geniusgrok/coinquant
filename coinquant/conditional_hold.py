"""Research-only permission to retain a filled SX60 opportunity after expiry."""

from .multiscale import DAY, published_daily_key


def expiry_permission(original, now, model_states, daily_states, last_checked=None):
    """Return (permission, reason), without changing the entry or protection.

    model_states contains every completed four-hour opportunity snapshot. This
    history distinguishes expiry from an intervening invalidation even when
    the current snapshot is None or has since acquired another identity.
    """
    if original is None or original.expires is None or now < original.expires:
        return False, 'not_original_expiry'
    for end, state in model_states.items():
        if end <= original.identity or end > now:
            continue
        if end < original.expires and (state is None or state.identity != original.identity):
            return False, 'invalidated_before_expiry'
        if end >= original.expires and state is not None and state.identity != original.identity:
            return False, 'intervening_opportunity'
    visible = daily_states.get(published_daily_key(now))
    if visible is None or visible.available_at > now or visible.score is None:
        return False, 'score_unavailable'
    if visible.score <= 0:
        return False, 'score_nonpositive'
    if last_checked is not None:
        for published, state in daily_states.items():
            if last_checked < published <= now and (state.score is None or state.score <= 0):
                return False, 'offline_score_invalidated'
    return True, 'expiry_positive_score'
