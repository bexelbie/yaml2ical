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
import icalendar
import logging
import os
import os.path
import pytz


class Yaml2IcalCalendar(icalendar.Calendar):
    """A calendar in ics format."""

    def __init__(self, calname=None, caldescription=None):
        super(Yaml2IcalCalendar, self).__init__()
        self.add('prodid', '-//yaml2ical agendas//EN')
        self.add('version', '2.0')
        if calname is not None:
            self.add('X-WR-CALNAME', calname)
        if caldescription is not None:
            self.add('X-WR-CALDESC', caldescription)

    def add_meeting(self, meeting):
        """Add this meeting to the calendar."""

        for sch in meeting.schedules:
            # one Event per iCal file
            event = icalendar.Event()

            # NOTE(jotan): I think the summary field needs to be unique per
            # event in an ical file (at least, for it to work with
            # Google Calendar)

            event.add('summary', meeting.project)
            event.add('location', '#' + sch.irc)

            # add ical description
            project_descript = "Project:  %s" % (meeting.project)
            chair_descript = "Chair:  %s" % (meeting.chair)
            descript_descript = "Description:  %s" % (meeting.description)
            ical_descript = "\n".join((project_descript,
                                       chair_descript,
                                       descript_descript))
            # Add URLs, if present, to the description
            if 'agenda_url' in meeting.extras:
                ical_descript = "\n".join((ical_descript,
                                           "Agenda URL:  %s" %
                                           (meeting.extras['agenda_url'])))
            if 'project_url' in meeting.extras:
                ical_descript = "\n".join((ical_descript,
                                           "Project URL:  %s" %
                                           (meeting.extras['project_url'])))
            event.add('description', ical_descript)

            # get starting date
            # bex
            start_date = sch.start_date
            #next_meeting = sch.recurrence.next_occurrence(start_date, sch.day)
            next_meeting = sch.next_occurrence()
            next_meeting_date = datetime.datetime(next_meeting.year,
                                                  next_meeting.month,
                                                  next_meeting.day,
                                                  sch.time.hour,
                                                  sch.time.minute,
                                                  tzinfo=pytz.utc)
            event.add('dtstart', next_meeting_date)

            # add recurrence rule bex
            event.add('rrule', sch.recurrence_rule())

            event.add('duration', datetime.timedelta(minutes=sch.duration))

            # add event to calendar
            self.add_component(event)

    def write_to_disk(self, filename):
        # write ical files to disk
        with open(filename, 'wb') as ics:
            ics.write(self.to_ical())


def convert_meetings_to_ical(meetings, outputdir=None, outputfile=None,
                             calname=None, caldescription=None):
    """Converts a meeting list to iCal.

    :param meetings: list of meetings to convert
    :param outputdir: location to store iCal files (one file per meeting)
    :param outputfile: output iCal file (one single file for all meetings)

    """

    # convert meetings to a list of ical
    if outputdir:
        for m in meetings:
            cal = Yaml2IcalCalendar()
            cal.add_meeting(m)
            cal.write_to_disk(os.path.join(outputdir, m.outfile))

    # convert meetings into a single ical
    if outputfile:
        cal = Yaml2IcalCalendar(calname, caldescription)
        for m in meetings:
            cal.add_meeting(m)
        cal.write_to_disk(outputfile)

    # TODO(jotan): verify converted ical is valid
    logging.info('Wrote %d meetings to iCal' % (len(meetings)))
