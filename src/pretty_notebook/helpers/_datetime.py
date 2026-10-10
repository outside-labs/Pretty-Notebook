"""Datetime conversion helpers."""
import datetime


def _convert_datetime(dt: str | int | float, as_mtime=False, as_date=False, as_time=False):
	"""Convert filesystem and API datetimes to stable representations."""
	if as_mtime:
		return datetime.datetime.fromtimestamp(dt, tz=datetime.timezone.utc)

	if dt == 'now':
		if as_time:
			return datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S')
		elif as_date:
			return datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')

		return datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')

	try:
		parsed = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
	except (AttributeError, TypeError, ValueError) as error:
		raise ValueError(f'Unable to parse datetime: {dt!r}') from error

	if parsed.tzinfo is None:
		parsed = parsed.replace(tzinfo=datetime.timezone.utc)

	return parsed.astimezone(datetime.timezone.utc)
