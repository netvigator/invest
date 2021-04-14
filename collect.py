#!/home/rick/.virtualenvs/invest/bin/python
# -*- coding: utf-8 -*-
#
# invest functions collect
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# The GNU General Public License is available from:
#   The Free Software Foundation, Inc.
#   51 Franklin Street, Fifth Floor
#   Boston MA 02110-1301 USA
#
#   http://www.gnu.org/licenses/
#
# Copyright 2021 Rick Graves
#
'''
https://www.etfchannel.com/symbol/spyd/
<td align="left" bgcolor="#FAFAFA" style="border-bottom: 1px solid #EEEEEE"><font 
face="Arial" size="2" color="#555555">Total Net Assets:</font></td>
<td colspan="2" align="left" bgcolor="#FFFFFF" style="border-bottom: 1px solid #EFEFEF"><font 
face="Arial" size="2" color="#222222">$3,093,790,540</font></td>
</tr>
'''
from datetime       import datetime, timedelta
from os             import rename
from os.path        import join, expanduser

import requests
from cloudscraper   import create_scraper

from pytz           import timezone

from File.Del       import DeleteIfExists
from File.Spec      import getNameNoPathNoExt
from File.Test      import isFileThere
from File.Write     import openAppendClose, QuickDump
from Object.Get     import ValueContainer
from String.Find    import getRegExObj
from Time.Convert   import getIsoDateTimeFromObj
from Time.Output    import getNowIsoDateTimeFileNameSafe
from String.Get     import getTextWithinFinders as getTextIn
from Utils.Config   import getConfDict, getTupleOffCommaString

class FundsOutOfOrderError( Exception ): pass
class NoNewUpdateYetError(  Exception ): pass

dConf           = getConfDict( 'invest.ini' )

sFunds          = dConf['main']['funds']
tFunds          = getTupleOffCommaString( sFunds )

dAssets         = dict.fromkeys( tFunds )
dTimes          = dict.fromkeys( tFunds )

sAssetsPage     = dConf['assets']['url']

tzEast          = timezone( 'US/Eastern' )

dtNow           = datetime.now( tz = tzEast )

oFindAsOfHead   = getRegExObj( dConf['assets']['as_of_head' ] )
oFindNextHead   = getRegExObj( dConf['assets']['next_head'  ] )
oFindAsOfBeg    = getRegExObj( dConf['assets']['beg_as_of'  ] )
oFindAsOfEnd    = getRegExObj( dConf['assets']['end_as_of'  ] )

oFindAssetsLine = getRegExObj( dConf['assets']['assets_desc'] )
oFindAssetsNext = getRegExObj( dConf['assets']['next_desc'  ] )
oFindAssetsBeg  = getRegExObj( dConf['assets']['beg_assets' ] )
oFindAssetsEnd  = getRegExObj( dConf['assets']['end_assets' ] )

sName           = dConf['credentials']['name' ]
sEmail          = dConf['credentials']['email']
sLogInURL       = dConf['credentials']['url'  ]


sFlowsPage      = dConf['flows']['url'        ]
sTickersField   = dConf['flows']['ticker_box' ]
sBegDateField   = dConf['flows']['beg_date'   ]
sEndDateField   = dConf['flows']['end_date'   ]

oFlowsHead      = getRegExObj( dConf['flows']['flows_head'] )
oFlowsEnd       = getRegExObj( dConf['flows']['flows_end' ] )
oSymbolBeg      = getRegExObj( dConf['flows']['symbol_beg'] )
sSymbolEnd      =              dConf['flows']['symbol_end']
oFlowBeg        = getRegExObj( dConf['flows']['flow_beg'  ] )
oFlowEnd        = getRegExObj( dConf['flows']['flow_end'  ] )






sAssetsFile     = dConf['main']['assets_file']
sFlowsFile      = dConf['main']['flows_file' ]
sFileDir        = expanduser(
                  dConf['main']['directory'  ] )


def _getTimeDeltaFromString( sUpdated ):
    #
    lParts = sUpdated.strip().split( ',' )
    #
    kwargs = {}
    #
    for sPart in lParts:
        #
        lSubParts = sPart.split( ' ' )
        #
        kwarg = lSubParts[ -1 ]
        #
        if kwarg in ( 'minutes', 'hours' ):
            #
            kwargs[ kwarg ] = int( lSubParts[ -2 ] )
            #
        #
    #
    return timedelta( **kwargs )



def _dumpHtmlOnError( sSymbol, sMsg, sHTML ):
    #
    sErrorFile = 'error_%s_%s.html' % (
            sSymbol, getNowIsoDateTimeFileNameSafe() )
    #
    print( r'%s, fetched HTML is in \tmp\%s' %
            ( sMsg, sErrorFile ) )
    #
    QuickDump( sHTML, sErrorFile, bSayBytes = False )



def _getTotalAssets( sSymbol, sTestHTML = None ):
    #
    if sTestHTML is None:
        #
        oR = requests.get( sAssetsPage % sSymbol.lower() )
        #
    else:
        #
        oR = ValueContainer()
        #
        oR.status_code  = 200
        oR.text         = sTestHTML
        #
    #
    tReturn = ( None, None )
    #
    if oR.status_code == 200:
        #
        sHTML   = oR.text
        #
        sTable  = getTextIn( sHTML,  oFindAsOfHead,   oFindNextHead   )
        #
        if sTable:
            #
            sUpdated = getTextIn( sTable, oFindAsOfBeg, oFindAsOfEnd )
            #
            if sUpdated is None:
                #
                sMsg = 'did not find as of date'
                #
                _dumpHtmlOnError( sSymbol, sMsg, sHTML )
                #
                raise NoNewUpdateYetError( sMsg )
                #
            else:
                #
                sUpdated = sUpdated.strip()
                #
            #
            sAsOf = getIsoDateTimeFromObj(
                dtNow - _getTimeDeltaFromString( sUpdated ) )[:16]
            #
            sLine   = getTextIn( sTable, oFindAssetsLine, oFindAssetsNext )
            #
            sAssets = getTextIn( sLine,  oFindAssetsBeg,  oFindAssetsEnd  )
            #
            iAssets = int( sAssets.replace( ',', '' ) )
            #
            tReturn = iAssets, sAsOf
            #
        else:
            #
            # registration required to continue
            #
            _dumpHtmlOnError( sSymbol, 'did not fetch table', sHTML )
            #
        #
    #
    return tReturn




def _getTotalAssetsDict():
    #
    dPayLoad = { 'name' : sName,
                 'email': sEmail,
                 'abcw' : 'a',
                 'cid'  : "91301" }
    #
    oLogin  = requests.post( sLogInURL, data = dPayLoad )
    #
    if oLogin.status_code == 200:
        #
        for sSymbol in tFunds:
            #
            tTotalAssets = _getTotalAssets( sSymbol )
            #
            iTotalAssets, sAsOf = tTotalAssets
            #
            dAssets[ sSymbol ] = iTotalAssets
            dTimes[  sSymbol ] = sAsOf
            #
        #
    else:
        #
        print( oLogin.text )
        #




def _getNewHeaderLine( tFunds = tFunds ):
    #
    lHeader = [ 'date time' ]
    lHeader.extend( tFunds )
    #
    return ','.join( lHeader )




def _getCsvHeaderAndLast( sFileDir, sFileName ):
    #
    sHeaderLine = sLastLine = None
    #
    if isFileThere( sFileDir, sFileName ):
        #
        # print( '%s is there' % sFileName )
        #
        with open( join( sFileDir, sFileName ) ) as oFile:
            #
            for sLine in oFile:
                #
                sHeaderLine = sLine.strip()
                #
                break
                #
            #
            for sLine in oFile:
                #
                pass
                #
            #
            sLastLine = sLine.strip()
            #
        #
    else:
        #
        print( '%s is NOT there' % sFileName )
        #
        sHeaderLineNew = _getNewHeaderLine()
        #
        openAppendClose( sHeaderLineNew, sFileDir, sFileName )
        #
        sHeaderLine = sHeaderLineNew
        #
    #
    return sHeaderLine, sLastLine


sHeaderLine, sLastLine = _getCsvHeaderAndLast( sFileDir, sAssetsFile )


def _getNewFundsAdded( sHeaderLine ):
    #
    return ( sHeaderLine and
             len( sHeaderLine.split(',') ) - ( len( tFunds ) + 1 ) )


iNewFundsAdded = _getNewFundsAdded( sHeaderLine )


def _checkFundsInOrder( sHeaderLinePrior ):
    #
    sHeaderLineNew   = _getNewHeaderLine()
    #
    lHeaderLinePrior = sHeaderLinePrior.split(',')
    lHeaderLineNew   = sHeaderLineNew.split(',')
    #
    for i in range(len(lHeaderLinePrior)):
        #
        if i > 0 and lHeaderLinePrior[i] != lHeaderLineNew[i]:
            #
            raise FundsOutOfOrderError('Funds are suddenly out of order!')
            #
        #
    #



def _getNewFileAddNewFunds( tFundsUpdate, iNewFundsAdded, sFileDir, sFileName ):
    #
    sNewFile = '%s.new' % getNameNoPathNoExt( sFileName )
    #
    DeleteIfExists( sFileDir, sNewFile )
    #
    oNewFile = open( join( sFileDir, sNewFile ), 'w' )
    #
    sAppendLine = '%s\n'
    #
    with open( join( sFileDir, sFileName ) ) as oFile:
        #
        for sLine in oFile:
            #
            sHeaderLinePrior = sLine
            #
            break
            #
        #
        # _checkFundsInOrder( sHeaderLinePrior ) already checked
        #
        iWantLen = 1 + len( tFunds )
        #
        oNewFile.write( sAppendLine % _getNewHeaderLine( tFundsUpdate ) )
        #
        lMoreZeros = ['0'] * iNewFundsAdded
        #
        for sLine in oFile:
            #
            lLine = sLine.strip().split(',')
            #
            lLine.extend( lMoreZeros )
            #
            oNewFile.write( sAppendLine % ','.join( lLine ) )
            #
        #
    #
    oNewFile.close()
    #
    sBackFile = '%s.bak' % getNameNoPathNoExt( sFileName )
    #
    DeleteIfExists( sFileDir, sBackFile )
    #
    rename( join( sFileDir, sFileName ), join( sFileDir, sBackFile ) )
    #
    rename( join( sFileDir, sNewFile  ), join( sFileDir, sFileName ) )
    #


# _updateMaybe( tFunds, dFlows, sDateYesterday, sFileDir, sFlowsFile )

def _updateMaybe( tFunds, dValues, sTimeStamp, sFileDir, sFileName ):
    #
    #
    sHeaderLine, sLastLine  = _getCsvHeaderAndLast( sFileDir, sFileName )
    #
    _checkFundsInOrder( sHeaderLine )
    #
    iNewFundsAdded    = _getNewFundsAdded( sHeaderLine )
    #
    if iNewFundsAdded:
        #
        _getNewFileAddNewFunds( tFunds, iNewFundsAdded, sFileDir, sFileName )
        #
    #
    bGotNewAssetNumbs = sLastLine is None or sTimeStamp[:10] > sLastLine[:10]
    #
    if bGotNewAssetNumbs:
        #
        lAssets = [ str( dValues[ sFund ] ) for sFund in tFunds ]
        #
        lAssets[ 0 : 0 ]    = [ sTimeStamp ]
        #
        openAppendClose( ','.join( lAssets ), sFileDir, sFileName )


def updateAssetsFileMaybe():
    #
    try:
        #
        _getTotalAssetsDict()
        #
        sAsOf = max( dTimes.values() )
        #
        _updateMaybe( tFunds, dAssets, sAsOf, sFileDir, sAssetsFile )
        #
    except NoNewUpdateYetError:
        #
        pass
        #


def _getFlowsDictFromHTML( sHTML ):
    #
    dFlows      = dict.fromkeys( tFunds )
    #
    sTable      = getTextIn( sHTML, oFlowsHead, oFlowsEnd )
    #
    # QuickDump( sTable, 'ETF_flows_table.html', bSayBytes = False )
    #
    lParts = oSymbolBeg.split( sTable )
    #
    for i, sRow in enumerate( lParts ):
        #
        if i: # skip the one with zero for the index
            #
            iEndSymbol  = sRow.find( sSymbolEnd )
            #
            sFund       = sRow[ : iEndSymbol ]
            #
            fFlow       = float(
                    getTextIn( sRow,   oFlowBeg,   oFlowEnd   ) )
            #
            dFlows[ sFund ] = fFlow
            #
        #
    #
    return dFlows



 




def _getFlowsDict():
    #
    dFlows      = dict.fromkeys( tFunds )
    #
    dtYesterday = dtNow - timedelta( days = 1 ) 
    #
    sDateYesterday = getIsoDateTimeFromObj( dtYesterday )[ : 10 ]
    #
    dPayLoad = {
            sTickersField : sFunds,
            sBegDateField : sDateYesterday,
            sEndDateField : sDateYesterday }
    #
    oScraper    = create_scraper( browser='chrome' )
    #
    oGetFlows   = oScraper.post( sFlowsPage, data = dPayLoad )
    #
    if oGetFlows.status_code == 200:
        #
        dFlows = _getFlowsDictFromHTML( oGetFlows.text )
        #
    else:
        #
        print( 'oGetFlows.status_code:', str( oGetFlows.status_code ) )
        #
        QuickDump( oGetFlows.text, 'ETF_flows.html', bSayBytes = False )
        #
    #
    return dFlows, sDateYesterday



def _updateFlowsMaybe( tFunds, dFlows, sDateYesterday, sFileDir, sFlowsFile ):
    #
    pass


def updateFlowsFileMaybe():
    #
    try:
        #
        dFlows, sDateYesterday = _getFlowsDict()
        #
        #print( 'dFlows:', dFlows )
        #print( 'yesterday:', sDateYesterday )
        _updateMaybe( tFunds, dFlows, sDateYesterday, sFileDir, sFlowsFile )
        #
    except NoNewUpdateYetError:
        #
        pass
        #



if __name__ == "__main__":
    #
    from difflib        import ndiff
    #
    from File.Info      import getLineCount
    from Utils.Result   import sayTestResult
    #
    from __init__       import EXAMPLE_FLOW_PAGE, EXAMPLE_ASSETS_PAGE
    #
    lProblems = []
    #
    sAssetsTest   = 'ETF_assets_test.csv'
    sFileDir    = r'/tmp'
    #
    tFunds      = ( 'SPYD','VYM','VPU','DIV' )
    #
    sHeaderNew  = _getNewHeaderLine( tFunds )
    #
    DeleteIfExists( sFileDir, sAssetsTest )
    #
    openAppendClose( sHeaderNew, sFileDir, sAssetsTest )
    #
    openAppendClose(
        '2021-04-07 10:05,3099349198,44862202189,5992208674,223246125',
        sFileDir, sAssetsTest )
    openAppendClose(
        '2021-04-08 10:05,3158729570,44856763862,5980514616,222101274',
        sFileDir, sAssetsTest )
    #
    sLastNew = '2021-04-09 10:05,3137735969,44808488311,5975887363,222330244'
    #
    openAppendClose( sLastNew, sFileDir, sAssetsTest )
    #
    iLineCount = getLineCount( sFileDir, sAssetsTest )
    #
    if iLineCount != 4:
        #
        lProblems.append( 'expecting 4 lines, instead got %s' % iLineCount )
        #
    #
    #
    sHeaderLine, sLastLine = _getCsvHeaderAndLast( sFileDir, sAssetsTest )
    #
    if sHeaderNew != sHeaderLine:
        #
        print( 'sHeaderNew :', sHeaderNew  )
        print( 'sHeaderLine:', sHeaderLine )
        print( [ li for li in
                 ndiff( sHeaderNew, sHeaderLine )
                 if li[0] != ' '] )
        #
        lProblems.append( '_getCsvHeaderAndLast() sHeaderNew != sHeaderLine' )
        #
    #
    if sLastNew != sLastLine:
        #
        print( 'sLastNew :', sLastNew  )
        print( 'sLastLine:', sLastLine )
        lProblems.append( '_getCsvHeaderAndLast() sLastNew != sLastLine' )
        #
    #
    #
    lFunds = list( tFunds )
    #
    lFunds.reverse()
    #
    sHeaderLinePrior = _getNewHeaderLine( lFunds )
    #
    try:
        _checkFundsInOrder( sHeaderLinePrior )
    except FundsOutOfOrderError:
        pass
    else:
        #
        lProblems.append(
            '_checkFundsInOrder() should raise FundsOutOfOrderError' )
        #
    #
    iNewFundsAdded = _getNewFundsAdded( sHeaderLine )
    #
    if iNewFundsAdded != 0:
        #
        print( 'iNewFundsAdded 0:', iNewFundsAdded )
        lProblems.append(
            '_getNewFundsAdded( sHeaderLine ) returned something' )
        #
    #
    # this info repeats the last line
    #
    dAssets     = dict( SPYD =  3137735969,
                        VYM  = 44808488311,
                        VPU  =  5992208674,
                        DIV  =   222330244 )
    #
    sAsOf = '2021-04-09 10:05'
    #
    _updateMaybe( tFunds, dAssets, sAsOf, sFileDir, sAssetsTest )
    #
    iLineCount = getLineCount( sFileDir, sAssetsTest )
    #
    if iLineCount != 4:
        #
        lProblems.append(
            'after re-adding the same last line, '
            'expecting 4 lines, instead got %s'
            % iLineCount )
        #
    #
    dAssets     = dict( SPYD =  3137735988,
                        VYM  = 44808488348,
                        VPU  =  5992208888,
                        DIV  =   222330288 )
    #
    sAsOf = '2021-04-12 10:05'
    #
    _updateMaybe( tFunds, dAssets, sAsOf, sFileDir, sAssetsTest )
    #
    iLineCount = getLineCount( sFileDir, sAssetsTest )
    #
    if iLineCount != 5:
        #
        lProblems.append(
            'added new last line for next trading day, '
            'expecting 5 lines, instead got %s'
            % iLineCount )
        #
    #
    #
    #
    #
    lFunds.append( 'GOOG' )
    #
    sHeaderLineNew = _getNewHeaderLine( lFunds )
    #
    iNewFundsAdded = _getNewFundsAdded( sHeaderLineNew )
    #
    if iNewFundsAdded != 1:
        #
        print( 'iNewFundsAdded 1:', iNewFundsAdded )
        lProblems.append(
            '_getNewFundsAdded( sHeaderLine ) should return 1' )
        #
    #
    _getNewFileAddNewFunds( lFunds, iNewFundsAdded, sFileDir, sAssetsTest )
    #
    iLineCount = getLineCount( sFileDir, sAssetsTest )
    #
    if iLineCount != 5:
        #
        lProblems.append(
            'after adding a new fund, expecting 5 lines, instead got %s'
            % iLineCount )
        #
    #
    sBackFile = '%s.bak' % getNameNoPathNoExt( sAssetsTest )
    #
    iLineCount = getLineCount( sFileDir, sBackFile )
    #
    if iLineCount != 5:
        #
        lProblems.append(
            'bak file should have original line count, '
            'expecting 5 lines, instead got %s'
            % iLineCount )
        #
    #
    tReturn = _getTotalAssets( 'SPYD', sTestHTML = EXAMPLE_ASSETS_PAGE )
    #
    sUpdated = ' 7 hours, 2 minutes '
    #
    s7hours2minutesAgo = getIsoDateTimeFromObj(
                dtNow - _getTimeDeltaFromString( sUpdated ) )[:16]
    #
    if tReturn != ( 3162766801, s7hours2minutesAgo ):
        #
        lProblems.append( '_getTotalAssets() and EXAMPLE_ASSETS_PAGE' )
        #
        print( tReturn[1] )
        print( s7hours2minutesAgo )
        #
        print( [ li for li in
                    ndiff( tReturn[1], s7hours2minutesAgo )
                    if li[0] != ' '] )
        #
    #
    '''
    print( oFlowBeg )
    print( oFlowEnd )
    '''
    dFlows = _getFlowsDictFromHTML( EXAMPLE_FLOW_PAGE )
    #
    dExpect = {'SPYD': 15.66, 'VYM': 38.45, 'VPU': 10.67, 'DIV': 1.79}
    #
    if dFlows != dExpect:
        #
        lProblems.append( '_getFlowsDictFromHTML' )
        #
    #
    #
    sayTestResult( lProblems )
