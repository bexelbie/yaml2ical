# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime
from io import StringIO
import os
import os.path
import yaml
import pytz
from dateutil import rrule
import collections



#from yaml2ical.recurrence import supported_recurrences

DATES = {
    'Monday': datetime.datetime(1900, 1, 1).date(),
    'Tuesday': datetime.datetime(1900, 1, 2).date(),
    'Wednesday': datetime.datetime(1900, 1, 3).date(),
    'Thursday': datetime.datetime(1900, 1, 4).date(),
    'Friday': datetime.datetime(1900, 1, 5).date(),
    'Saturday': datetime.datetime(1900, 1, 6).date(),
    'Sunday': datetime.datetime(1900, 1, 7).date(),
}
ONE_WEEK = datetime.timedelta(weeks=1)
WEEKDAYS = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6}


class Schedule(object):
    """A meeting schedule."""

    def __init__(self, meeting, sched_yaml):
        """Initialize schedule from yaml."""

        self.project = meeting.project
        self.filefrom = meeting.filefrom
        # mandatory: time, day, irc, freq
        try:
            self.utc = sched_yaml['time']
            self.time = datetime.datetime.strptime(sched_yaml['time'], '%H%M')
            # Sanitize the Day
            self.day = sched_yaml['day'].lower().capitalize()
            self.irc = sched_yaml['irc']
            self.freq = sched_yaml['frequency']
            self.freq_interval = supported_frequencies[sched_yaml['frequency']]
        except KeyError as e:
            print("Invalid YAML meeting schedule definition - missing "
                  "attribute '{0}'".format(e.args[0]))
            raise

        # optional: start_date defaults to the current date if not present
        if 'start_date' in sched_yaml:
            try:
                self.start_date = datetime.datetime.strptime(
                    str(sched_yaml['start_date']), '%Y%m%d')
            except ValueError:
                raise ValueError("Could not parse 'start_date' (%s) in %s" %
                                (sched_yaml['start_date'], self.filefrom))
        else:
            self.start_date = datetime.datetime.utcnow()

        # optional: duration
        if 'duration' in sched_yaml:
            try:
                self.duration = int(sched_yaml['duration'])
            except ValueError:
                raise ValueError("Could not parse 'duration' (%s) in %s" %
                                (sched_yaml['duration'], self.filefrom))
        else:
            self.duration = 60

        if self.day not in DATES.keys():
            raise ValueError("'%s' is not a valid day of the week")

        # NOTE(tonyb): We need to do this datetime shenanigans is so we can
        #              deal with meetings that start on day1 and end on day2.
        self.meeting_start = datetime.datetime.combine(DATES[self.day],
                                                       self.time.time())
        self.meeting_end = (self.meeting_start +
                            datetime.timedelta(minutes=self.duration))
        if self.day == 'Sunday' and self.meeting_end.strftime("%a") == 'Mon':
            self.meeting_start = self.meeting_start - ONE_WEEK
            self.meeting_end = self.meeting_end - ONE_WEEK

    def conflicts(self, other):
        """Checks for conflicting schedules."""
        alternating = set(['biweekly-odd', 'biweekly-even'])
        # NOTE(tonyb): .meeting_start also includes the day of the week. So no
        #              need to check .day explictly
        return ((self.irc == other.irc) and
                ((self.meeting_start < other.meeting_end) and
                 (other.meeting_start < self.meeting_end)) and
                (set([self.freq, other.freq]) != alternating))

    def next_occurrence(self):
        """Return the datetime of the next meeting.

        :returns: datetime object of the next meeting time
        """

        weekday = WEEKDAYS[self.day]
        days_ahead = weekday - self.start_date.weekday()
        if days_ahead < 0:  # target day already happened this week
            days_ahead += 7
        next_meeting =  self.start_date + datetime.timedelta(days_ahead)
        return datetime.datetime(next_meeting.year,
                                 next_meeting.month,
                                 next_meeting.day,
                                 self.time.hour,
                                 self.time.minute,
                                 tzinfo=pytz.utc)

    def recurrence_rule(self):
        return {'freq': 'weekly', 'interval': self.freq_interval}

class Meeting(object):
    """An online meeting."""

    def __init__(self, data):
        """Initialize meeting from meeting yaml description."""

        yaml_obj = yaml.safe_load(data)

        try:
            self.chair = yaml_obj['chair']
            self.description = yaml_obj['description']
            self.project = yaml_obj['project']
        except KeyError as e:
            print("Invalid YAML meeting definition - missing "
                  "attribute '{0}'".format(e.args[0]))
            raise

        # Find any extra values the user has provided that they might
        # want to have access to in their templates.
        self.extras = {}
        self.extras.update(yaml_obj)
        for k in ['chair', 'description', 'project', 'schedule']:
            if k in self.extras:
                del self.extras[k]

        try:
            self.filefrom = os.path.basename(data.name)
            self.outfile = os.path.splitext(self.filefrom)[0] + '.ics'
        except AttributeError:
            self.filefrom = "stdin"
            self.outfile = "stdin.ics"

        self.schedules = []
        for sch in yaml_obj['schedule']:
            s = Schedule(self, sch)
            self.schedules.append(s)

    @classmethod
    def fromfile(cls, yaml_file):
        f = open(yaml_file, 'r')
        return cls(f)

    @classmethod
    def fromstring(cls, yaml_string):
        s = StringIO(yaml_string)
        return cls(s)


def load_meetings(yaml_source):
    """Build YAML object and load meeting data

    :param yaml_source: source data to load, which can be a directory or
                        stream.
    :returns: list of meeting objects
    """
    meetings = []
    # Determine what the yaml_source is. Files must have .yaml extension
    # to be considered valid.
    if os.path.isdir(yaml_source):
        for root, dirs, files in os.walk(yaml_source):
            for f in files:
                # Build the entire file path and append to the list of yaml
                # meetings
                if os.path.splitext(f)[1] == '.yaml':
                    yaml_file = os.path.join(root, f)
                    meetings.append(Meeting.fromfile(yaml_file))
    elif (os.path.isfile(yaml_source) and
          os.path.splitext(yaml_source)[1] == '.yaml'):
        meetings.append(Meeting.fromfile(yaml_source))
    elif isinstance(yaml_source, str):
        return [Meeting.fromstring(yaml_source)]

    if not meetings:
        # If we don't have a .yaml file, a directory of .yaml files, or any
        # YAML data fail out here.
        raise ValueError("No .yaml file, directory containing .yaml files, "
                         "or YAML data found.")
    else:
        return meetings


class MeetingConflictError(Exception):
    pass

class MeetingInstance(object):
    """A meeting instance."""

    def __init__(self, project, start, duration):
        self.project = project
        self.start = start
        self.end = start + datetime.timedelta(minutes=duration)

def check_for_meeting_conflicts(meetings):
    """Check if a list of meetings have conflicts.

    :param meetings: list of Meeting objects

    """
    # Get all recurrences for the next year
    start = datetime.datetime.now(pytz.utc)
    end = start + datetime.timedelta(days=365)

    allinstances = collections.defaultdict(list)
    for i in range(len(meetings)):
        for schedule in meetings[i].schedules:
            rr = rrule.rrule(rrule.WEEKLY,
                     dtstart = schedule.next_occurrence(),
                     interval = schedule.freq_interval)
            occurrences = rr.between(start, end, inc=True)
            for occurrence_start in occurrences:
               allinstances[schedule.irc].append(MeetingInstance(meetings[i].project,
                                                 occurrence_start,
                                                 schedule.duration))

    for irc_channel in allinstances:
        for i in range(len(allinstances[irc_channel])):
            for j in range(i+1, len(allinstances[irc_channel])):
                # This conflict check allows meetings to share exact start/stop times
                # i.e. 11-11:30 and 11:30-12 do not conflict
                if ((allinstances[irc_channel][i].start < allinstances[irc_channel][j].end) and
                   (allinstances[irc_channel][i].end > allinstances[irc_channel][j].start)):
                    error = "Conflict: %s and %s" % (allinstances[irc_channel][i].project,
                                                     allinstances[irc_channel][j].project)
                    raise MeetingConflictError(error)

supported_frequencies = {
    'weekly': 1,
    'biweekly': 2,
}
