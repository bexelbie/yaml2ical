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


WEEKDAYS = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6}


class WeeklyRecurrence(object):
    """Meetings occuring every week."""
    def __init__(self):
        pass

    def next_occurrence(self, start_date_time, day):
        """Return the date of the next meeting.

        :param ref_date: datetime object of meeting
        :param day: weekday the meeting is held on

        :returns: datetime object of the next meeting time
        """

        weekday = WEEKDAYS[day]
        days_ahead = weekday - start_date_time.weekday()
        if days_ahead < 0:  # target day already happened this week
            days_ahead += 7
        return start_date_time + datetime.timedelta(days_ahead)

    def rrule(self, next_date):
        return {'freq': 'weekly', 'dtstart': next_date}

    def __str__(self):
        return "Weekly"


class BiWeeklyRecurrence(object):
    """Meetings occuring on alternate weeks.

#    Can be either on odd weeks or on even weeks
#    """
#    def __init__(self, style='even'):
#        self.style = style

    def next_occurrence(self, start_date, day):
        """Calculate the next biweekly meeting.

        :param start_date: the current date
        :param day: scheduled day of the meeting
        :returns: datetime object of next meeting
        """
        return WeeklyRecurrence().next_occurrence(start_date, day)
        #nextweek_day = WeeklyRecurrence().next_occurrence(start_date, day)
        #if nextweek_day.isocalendar()[1] % 2:
        #    ## ISO week is odd
        #    if self.style == 'odd':
        #        return nextweek_day
        #else:
        #    ## ISO week is even
        #    if self.style == 'even':
        #        return nextweek_day
        # If week doesn't match rule, skip one week
        #return nextweek_day + datetime.timedelta(7)

    def rrule(self, next_date):
        return {'freq': 'weekly', 'interval': 2, 'dtstart': next_date}

    def __str__(self):
        return "Every two weeks (on %s weeks)" % self.style


supported_recurrences = {
    'weekly': WeeklyRecurrence(),
    'biweekly': BiWeeklyRecurrence(),
#    'biweekly-odd': BiWeeklyRecurrence(style='odd'),
#    'biweekly-even': BiWeeklyRecurrence(),
}
