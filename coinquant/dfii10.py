"""Point-in-time ALFRED DFII10 input for the single promoted model."""
import csv
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
from html.parser import HTMLParser
from io import StringIO
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor
from time import monotonic
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from zipfile import BadZipFile, ZipFile
from io import BytesIO

from .types import Blocked, Unknown

URL='https://alfred.stlouisfed.org/series/downloaddata?seid=DFII10'
_EASTERN=[]


def eastern():
    """America/New_York with daylight saving; never a fixed UTC offset."""
    if not _EASTERN:
        try:_EASTERN.append(ZoneInfo('America/New_York'))
        except ZoneInfoNotFoundError:
            raise Blocked('IANA time zone data unavailable; install the tzdata package '
                          '(python -m pip install tzdata), required on Windows') from None
    return _EASTERN[0]


class _Dates(HTMLParser):
    def __init__(self):
        super().__init__();self.inside=False;self.values=[]

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='select' and attrs.get('id')=='form_selected_vintage_dates':self.inside=True
        if tag=='option' and self.inside:
            try:self.values.append(date.fromisoformat(attrs['value']))
            except (KeyError,ValueError):pass

    def handle_endtag(self,tag):
        if tag=='select':self.inside=False


def available(vintage):
    # A dated vintage is not a proven intraday release time.
    end=datetime.combine(vintage,time.max,eastern())
    return int((end.astimezone(timezone.utc)+timedelta(hours=48)).timestamp()*1000)


def eligible(row,call):
    if row['missing_reason']:return False
    observed=date.fromisoformat(row['latest_observation_date'])
    if (datetime.fromtimestamp(call/1000,timezone.utc).date()-observed).days>7:
        return False
    if row['latest_value_available_ms']>=call or row['prior20_value_available_ms']>=call:
        raise Unknown('DFII10 vintage is not yet available')
    latest,prior=D(row['latest_value']),D(row['prior20_value'])
    if not latest.is_finite() or not prior.is_finite():raise Unknown('invalid DFII10 input')
    return latest<=prior-D('.25')


class Source:
    # After a failed fetch the next attempt waits; each poll must not repeat it.
    RETRY_MS=60000

    def __init__(self):
        self.cached=None;self.fetched_at=0;self.failed_at=None

    def snapshot(self,now,budget=60):
        """Both requests share `budget` seconds, normally the session's remainder."""
        if self.cached is not None and self.fetched_at<=now<self.fetched_at+900000:
            return self.cached
        if self.failed_at is not None and self.failed_at<=now<self.failed_at+self.RETRY_MS:
            raise Unknown('ALFRED point-in-time DFII10 unavailable; retry deferred')
        headers={'User-Agent':'coinquant-personal/1.0','Accept':'text/html,application/zip'}
        opener=build_opener(HTTPCookieProcessor())
        started=monotonic()
        def timeout(limit):
            left=min(limit,budget-(monotonic()-started))
            if left<=0:raise TimeoutError('DFII10 read budget exhausted')
            return left
        try:
            with opener.open(Request(URL,headers=headers),timeout=timeout(25)) as response:
                page=response.read(2_000_001)
            if len(page)>2_000_000:raise ValueError('ALFRED form too large')
            parser=_Dates();parser.feed(page.decode('utf-8'))
            dates=sorted(set(v for v in parser.values if available(v)<now))[-100:]
            if len(dates)<21:raise ValueError('insufficient historical vintages')
            body=urlencode([('form[units]','lin'),('form[obs_start_date]',str(dates[0]-timedelta(days=7))),
                            ('form[obs_end_date]',str(dates[-1])),('form[entered_vintage_dates]',''),
                            ('form[file_type]','3'),('form[file_format]','csv'),
                            ('form[download_data]','Download data')]+[
                                ('form[selected_vintage_dates][]',str(v)) for v in dates]).encode()
            with opener.open(Request(URL,data=body,headers=headers,method='POST'),timeout=timeout(35)) as response:
                raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError('ALFRED response too large')
            with ZipFile(BytesIO(raw)) as archive:
                names=[n for n in archive.namelist() if n.endswith('.csv')]
                if len(names)!=1 or archive.getinfo(names[0]).file_size>4_000_000:
                    raise ValueError('invalid ALFRED archive')
                rows=list(csv.reader(StringIO(archive.read(names[0]).decode('utf-8-sig'))))
            if not rows or rows[0]!=['observation_date']+[f'DFII10_{v:%Y%m%d}' for v in dates]:
                raise ValueError('ALFRED vintage columns changed')
            updates={}
            for values in rows[1:]:
                if len(values)!=len(rows[0]):raise ValueError('ALFRED observation width changed')
                observed=date.fromisoformat(values[0])
                if observed>dates[-1]:raise ValueError('future observation')
                for vintage,value in zip(dates,values[1:]):
                    if value:
                        if observed>vintage:raise ValueError('future vintage observation')
                        number=D(value)
                        if not number.is_finite():raise ValueError('invalid DFII10 value')
                        updates[observed]=(number,vintage)
            observations=sorted(updates)
            latest=observations[-1] if observations else None
            prior=observations[-21] if len(observations)>=21 else None
            reason=('insufficient_20_prior_observations' if prior is None else
                    'stale_observation_over_7_calendar_days' if
                    (datetime.fromtimestamp(now/1000,timezone.utc).date()-latest).days>7 else None)
            digest=sha256(raw).hexdigest()
            cache=Path.home()/'.local'/'state'/'coinquant'/'dfii10'
            cache.mkdir(parents=True, exist_ok=True, mode=0o700)
            stored=cache/f'{digest}.zip'
            if not stored.exists():
                stored.write_bytes(raw)
            row=dict(latest_value=str(updates[latest][0]) if latest else None,
                     prior20_value=str(updates[prior][0]) if prior else None,
                     latest_observation_date=str(latest) if latest else None,
                     prior20_observation_date=str(prior) if prior else None,
                     latest_value_available_ms=available(updates[latest][1]) if latest else None,
                     prior20_value_available_ms=available(updates[prior][1]) if prior else None,
                     asof_vintage_date=str(dates[-1]),missing_reason=reason,
                     response_sha256=digest)
            self.cached=row;self.fetched_at=now;self.failed_at=None
            return row
        except (OSError,ValueError,KeyError,IndexError,UnicodeError,BadZipFile) as exc:
            self.failed_at=now
            raise Unknown('ALFRED point-in-time DFII10 unavailable') from exc
