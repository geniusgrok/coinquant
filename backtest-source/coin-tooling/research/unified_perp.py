from datetime import datetime, timezone
from decimal import Decimal as D
import bisect, hashlib, json
DAY=86400000
class PriorFX:
    """Existing peer fixing: only calendar dates strictly before today are used."""
    def __init__(self, path):
        raw = path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        rates = json.loads(raw)['rates']
        self.days = sorted(rates)
        self.rates = [D(str(rates[day]['CNY'])) for day in self.days]

    def __call__(self, stamp):
        day = datetime.fromtimestamp(stamp / 1000, timezone.utc).date().isoformat()
        index = bisect.bisect_left(self.days, day) - 1
        return self.rates[index] if index >= 0 else D('6.9615')

    def changes(self, start, end):
        return range((start // DAY + 1) * DAY, end + 1, DAY)

