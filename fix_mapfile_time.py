#!/usr/bin/env python

"""
DESCRIPTION:
    Given a mapfile with a remote wms connection, look up the connection
    and update the wms_timeextent metadata attribute appropriately since it
    appears the time extent doesn't cascade.

"""

"""
This section not in docstring so skipped in help

-----

EXIT STATUS

    TODO: List exit codes
    1 is definitely a failure.
    0 might be success
-----

AUTHOR

    Jason Brown <JBrown@edac.unm.edu>
-----

LICENSE

Copyright (c) 2013, Jason Brown
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of the FreeBSD Project.


2-clause "Simplified BSD License".

-----

VERSION

    $Id$
-----

NON-CORE REQUIREMENTS
    - lxml
    - mapscript
-----
"""

# TO EDIT:
#    run pep8
#    run pylint

# pylint -- name convention
#pylint: disable-msg=C0103

# CORE
import argparse
import logging
import os
import sys
import time
import traceback
import types
import urllib2

# NON CORE
import mapscript
from mapscript import MapServerError
from lxml import etree

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s')

INFO  = logging.info
WARN  = logging.warning
DEBUG = logging.debug
ERR   = logging.error


#----------------------------------------------------------------------------
def updateWMStimeExtent(layer):
    """
    Side Effect: layer is mutated.
    """

    MDKEY = 'wms_timeextent'

    ## pylint: disable-msg=C0301
    # http://neowms.sci.gsfc.nasa.gov/wms/wms?

    # OK, FGDC has a caldate element that we can get in a pretty format
    #  and wms sends iso 8601 req isodate.
    #
    getCapabilities = "%(URL)sSERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities" % {
        'URL': layer.connection,
    }
    ## pylint: disable-msg=C0301

    # FGDC = capabilitiesTree.xpath( # "//Layer[Name='%s']/MetadataURL[@type='FGDC']/OnlineResource" %
    # layer.name )

    capabilitiesXml = urllib2.urlopen(getCapabilities)  # type fd
    capabilitiesTree = etree.parse(capabilitiesXml)
    capabilitiesXml.close()

    try:
        strTimeExtent = capabilitiesTree.xpath(
			"//Layer[Name='%s']/ancestor-or-self::Layer/Extent[@name='time']/text()" % layer.name
        )[0]
        # Form: '2000-02-18,2000-03-06,2000-03-22,2000-04- ....'
        strTimeExtent = strTimeExtent.replace('-', '')  # purge '-'
        #dates = strTimeExtent.split(',')
        # TODO:  This dies.  We get capabilities format wms time
        #   http://mapserver.org/ogc/wms_time.html.
        #layer.setMetaData(MDKEY, dates)
        layer.setMetaData(MDKEY, strTimeExtent)
        import IPython
        IPython.embed()

    except:
        # TODO: We ought to give better info to the client and
        # let them know things are down right now
        #
        # we serve an empty date
        ERR("Unable to locate dates in capabilities document at: %s" %
            layer.connection)
        raise

#----------------------------------------------------------------------------


#----------------------------------------------------------------------------
def process(fileName, layerName, outFile=None, outFolder=None):
    """
    Given a file that exists, let's look it up and spit out a new mapfile
    updated properly.

    fileName  : (STRING) /full/path/to/file
    layerName : (STRING) mapfile layer name

    MUTUALLY EXCLUSIVE, but one required :
        outFile   : (STRING) /full/path/to/outputfile
        outFolder : (STRING) /full/path/to/outputfolder -- file will be saved
                            as outFolder/fileName
    """

    assert (outFile or outFolder)
    assert (not(outFile and outFolder))

    # Whatever it is, make sure we know our output file's name
    if outFolder:
        outFile = os.path.join(outFolder, os.path.basename(fileName))

    original = mapscript.mapObj(fileName)
    layer = original.getLayerByName(layerName)

    if layer == types.NoneType:
        WARN('Unable to locate %(layerName) in file %(filepath)s' % locals())
        return

    try:
        # Function calling function, sloppy, but this way it's easy to plug in
        # multiple proc steps
        updateWMStimeExtent(layer)
    except MapServerError:
        WARN('Unable to locate time metadata in layer %(layerName) ' +
             'within file %(filepath)s' % locals())

    original.save(outFile)
#----------------------------------------------------------------------------


##############################################################################
def main(args):
    """
    Given a list of filenames, process updates
    """

    # Look up the type of args, close the verified file handle we were passed
    # in, and begin data processing

    folder = None
    outfile = None

    destination = args.DEST[0]
    if os.path.isdir(destination):
        DEBUG('Output is to folder %s' % destination)
        folder = destination
    else:
        DEBUG('Output is to file %s' % destination)
        outfile = destination

    for handle in args.SOURCE:
        handle.close()  # we know it exists b/c it's filetype
        process(handle.name, args.LAYER[0], outfile, folder)

##############################################################################

##############################################################################
if __name__ == '__main__':
    try:
        start_time = time.time()

        parser = argparse.ArgumentParser(
            description=__doc__.strip()
        )

        parser.add_argument('--version', action='version', version='$Id$')

        parser.add_argument(
            '-v', '--verbose', action='store_true', default=False,
            help='Verbose Output')

        parser.add_argument(
            'LAYER', nargs=1,
            help='Layer name to process (e.g. MOD13A2_E_NDVI)'
        )

        parser.add_argument(
            'SOURCE', nargs='+', default=sys.stdin,
            type=argparse.FileType('r'),
            help="Input mapfile(s) (e.g. /tmp/some/mapfile.map)" +
                 " [.../tmp/some/mapfile2.map ]"
        )

        # gross reserved word as an argument
        parser.add_argument(
            'DEST', nargs=1, default=sys.stdout,
            help='Output mapfile (e.g. /tmp/some/newMapfile.map) or DIRECTORY'
        )

        parsed = parser.parse_args()

        # If we have more than 1 SRC, DEST must be a folder
        if len(parsed.SOURCE) > 1:
            if not os.path.isdir(parsed.DEST[0]):
                parser.print_usage()
                sys.exit(os.EX_USAGE)

        if parsed.verbose:
            INFO(time.asctime())

        main(parsed)

        if parsed.verbose:
            INFO(time.asctime())
            INFO('TOTAL TIME IN SECONDS: %s' % (time.time() - start_time))

        sys.exit(os.EX_OK)
    except KeyboardInterrupt, e:  # Ctrl-C
        raise e
    except SystemExit, e:  # sys.exit()
        raise e
    except Exception, e:
        print 'ERROR, UNEXPECTED EXCEPTION'
        print str(e)
        traceback.print_exc()
        sys.exit(1)

##############################################################################
