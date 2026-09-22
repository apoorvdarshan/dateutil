import sys
from datetime import datetime

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st

from dateutil import tz

# 32-bit time_t range is 1901-12-13 20:45:52 UTC .. 2038-01-19 03:14:07 UTC.
# fromtimestamp() is local, so a west-of-UTC TZ (CI uses America/New_York)
# made the naive min_value earlier than that window. Hypothesis then attaches
# tz.UTC, and dateutil's 32-bit tzfile reader reports LMT while the system
# zone reports EST (seen on pypy-3.8 / macOS).
EPOCHALYPSE = datetime(2038, 1, 18)
NEGATIVE_EPOCHALYPSE = datetime(1901, 12, 14)


@pytest.mark.gettz
@pytest.mark.skipif(
    sys.version_info < (3, 6), reason="Not supported on Python 2"
)
@pytest.mark.parametrize("gettz_arg", [None, ""])
# TODO: Remove bounds when GH #590 is resolved
@given(
    dt=st.datetimes(
        min_value=NEGATIVE_EPOCHALYPSE,
        max_value=EPOCHALYPSE,
        timezones=st.just(tz.UTC),
    )
)
@example(dt=datetime(2005, 10, 30, 1, 15))  # Ambiguous in US time zones
@example(dt=datetime(1901, 12, 14, 18, 19, 3))  # Very old
def test_gettz_returns_local(gettz_arg, dt):
    act_tz = tz.gettz(gettz_arg)
    if isinstance(act_tz, tz.tzlocal):
        return

    dt_act = dt.astimezone(act_tz)
    dt_exp = dt.astimezone()

    assert dt_act.astimezone(tz.UTC) == dt_exp.astimezone(tz.UTC)
    assert dt_act.tzname() == dt_exp.tzname()
    assert dt_act.utcoffset() == dt_exp.utcoffset()

    # According to PEP 495, if the value of fold would change the return value
    # of utcoffset(), comparisons with the datetime always return false, so we
    # must handle the case of ambiguous and imaginary datetimes here for the
    # property to remain valid.
    if (
        tz.enfold(dt_act, fold=0).utcoffset()
        == tz.enfold(dt_act, fold=1).utcoffset()
    ):
        assert dt_act == dt_exp
    else:
        assert (
            tz.enfold(dt, fold=0).astimezone().utcoffset()
            != tz.enfold(dt, fold=1).astimezone().utcoffset()
        )
        assert dt_act != dt_exp
