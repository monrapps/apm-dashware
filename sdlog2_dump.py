#!/usr/bin/env python

from __future__ import print_function
from sdlog2parser import SDLog2Parser

"""
Dump binary log generated by PX4's sdlog2 or APM as CSV or GPX

Based on https://github.com/PX4/Firmware/blob/master/Tools/sdlog2/sdlog2_dump.py
Modified by Jesse Crocker to generate GPX, and work with logs that dont have a TIME message.
"""

__author__ = "Anton Babushkin"
__version__ = "1.3"

from optparse import OptionParser
import logging

def _main():
    usage = "usage: %prog <log.bin>"
    parser = OptionParser(usage=usage,
                          description="Convert .bin log to CSV")
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
                      help="Turn on debug logging")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                      help="turn off all logging")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False,
                      help="Use plain debug output instead of CSV.")
    parser.add_option("-e", "--recover", action="store_true", dest="recover",
                      default=False,
                      help="Recover from Errors")
    parser.add_option("-D", "--delimiter", action="store", dest="delimiter",
                      default=",",
                      help="CSV delimiter, default is \",\"")
    parser.add_option("-n", "--null", action="store", dest="csv_null",
                      default="",
                      help="Use value as placeholder for empty values in CSV. Default is empty.")
    parser.add_option("-m", "--message",
                      action="append",
                      dest="messages",
                      default=[],
                      metavar="message[.field,field2,field3]",
                      help="Dump only messages of specified type, and only specified fields..")
    parser.add_option("-f", "--output_file", action="store", dest="output_file",
                      default=None,
                      metavar="FILE",
                      help="Write to FILE instead of stdout")
    parser.add_option("-o", "--output",
                      dest="format",
                      default="csv",
                      help="Output format, default is csv",
                      choices=['csv', 'gpx', 'none'])
    (options, args) = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if options.debug else
    (logging.ERROR if options.quiet else logging.INFO))

    if len(args) == 0:
        logging.error("Error, must specify at least 1 log")
        sys.exit(-1)

    msg_filter = []
    for m in options.messages:
        a = m.split('.')
        show_fields = "*"
        if len(a) > 1:
            show_fields = a[1].split(",")
        msg_filter.append((a[0], show_fields))

    for filename in args:
        parser = SDLog2Parser()
        parser.setCSVDelimiter(options.delimiter)
        parser.setCSVNull(options.csv_null)
        parser.setMsgFilter(msg_filter)
        parser.setDebugOut(options.verbose)
        parser.setCorrectErrors(options.recover)
        (columns, rows) = parser.process(filename)

        output_file = None
        if options.output_file:
            output_file = open(options.output_file, 'w')

        if options.format == "csv":
            #csv header
            if output_file is not None:
                print(options.delimiter.join(columns), file=output_file)
            else:
                print(options.delimiter.join(columns))

            #csv value rows
            for row in rows:
                values = []
                for full_label in columns:
                    v = None
                    if full_label in row:
                        v = row[full_label]

                    if full_label == "GLOBAL_TimeMS":
                        for col, val in row.items():
                            if "TimeMS" in col and col != "GPS_TimeMS":
                                v = val

                    if v is None:
                        v = options.csv_null
                    else:
                        v = str(v)
                    values.append(v)

                if output_file is not None:
                    print(options.delimiter.join(values), file=output_file)
                else:
                    print(options.delimiter.join(values))
        elif options.format == "gpx":
            import gpxpy
            import gpxpy.gpx
            from datetime import datetime
            from datetime import timedelta

            gpx = gpxpy.gpx.GPX()

            gpx_track = gpxpy.gpx.GPXTrack()
            gpx.tracks.append(gpx_track)
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)

            gps_epoch =  datetime(1980, 1, 6, 0, 0, 0)
            for row in rows:
                if 'GPS_TimeMS' in row:
                    epoch_delta = timedelta(days=int(row['GPS_Week'])*7,
                                            milliseconds=int(row['GPS_TimeMS']))
                    time = gps_epoch + epoch_delta
                    point = gpxpy.gpx.GPXTrackPoint(row['GPS_Lat'], row['GPS_Lng'],
                                                                      elevation=row['GPS_Alt'],
                                                                      time=time)
                    if 'GPS_HDop' in row:
                        point.horizontal_dilution = float(row['GPS_HDop'])
                    if 'GPS_Spd' in row:
                        point.speed = float(row['GPS_Spd'])

                    gpx_segment.points.append(point)

            if output_file is not None:
                print(gpx.to_xml(), file=output_file)
            else:
                print(gpx.to_xml())

        if output_file is not None:
            output_file.close()


if __name__ == "__main__":
    _main()
