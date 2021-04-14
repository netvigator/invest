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

from pytz           import timezone

from File.Del       import DeleteIfExists
from File.Spec      import getNameNoPathNoExt
from File.Test      import isFileThere
from File.Write     import openAppendClose, QuickDump
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

sETFpage        = dConf['source']['url']

tzEast          = timezone( 'US/Eastern' )

dtNow           = datetime.now( tz = tzEast )

oFindAsOfHead   = getRegExObj( dConf['source']['as_of_head' ] )
oFindNextHead   = getRegExObj( dConf['source']['next_head'  ] )
oFindAsOfBeg    = getRegExObj( dConf['source']['beg_as_of'  ] )
oFindAsOfEnd    = getRegExObj( dConf['source']['end_as_of'  ] )

oFindAssetsLine = getRegExObj( dConf['source']['assets_desc'] )
oFindAssetsNext = getRegExObj( dConf['source']['next_desc'  ] )
oFindAssetsBeg  = getRegExObj( dConf['source']['beg_assets' ] )
oFindAssetsEnd  = getRegExObj( dConf['source']['end_assets' ] )

sName           = dConf['credentials']['name' ]
sEmail          = dConf['credentials']['email']
sLogInURL       = dConf['credentials']['url'  ]

sFileName       = dConf['main']['name'      ]
sFileDir        = expanduser(
                  dConf['main']['directory' ] )


def _getTimeDeltaFromString( sUpdated ):
    #
    lParts = sUpdated.split( ',' )
    #
    kwargs = {}
    #
    for sPart in lParts:
        #
        lSubParts = sPart.split( ' ' )
        #
        kwarg = '%s%s' % ( lSubParts[ -1 ],
                     '' if lSubParts[ -1 ].endswith('s') else 's' )
        #
        kwargs[ kwarg ] = int( lSubParts[ -2 ] )
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



def _getTotalAssets( sSymbol ):
    #
    oR = requests.get( sETFpage % sSymbol.lower() )
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


sHeaderLine, sLastLine = _getCsvHeaderAndLast( sFileDir, sFileName )


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



def _updateFileMaybe(
            tFunds      = tFunds,
            dAssets     = dAssets,
            dTimes      = dTimes,
            sFileDir    = sFileDir,
            sFileName   = sFileName ):
    #
    #
    sAsOf                   = max( dTimes.values() )
    #
    sHeaderLine, sLastLine  = _getCsvHeaderAndLast( sFileDir, sFileName )
    #
    _checkFundsInOrder( sHeaderLine )
    #
    iNewFundsAdded          = _getNewFundsAdded( sHeaderLine )
    #
    if iNewFundsAdded:
        #
        _getNewFileAddNewFunds( tFunds, iNewFundsAdded, sFileDir, sFileName )
        #
    #
    bGotNewAssetNumbs       = sAsOf[:10] > sLastLine[:10]
    #
    if bGotNewAssetNumbs:
        #
        lAssets = [ str( dAssets[ sFund ] ) for sFund in tFunds ]
        #
        lAssets[ 0 : 0 ]    = [ str( sAsOf ) ]
        #
        openAppendClose( ','.join( lAssets ), sFileDir, sFileName )


def updateFileMaybe():
    #
    try:
        #
        _getTotalAssetsDict()
        #
        _updateFileMaybe( tFunds, dAssets, dTimes, sFileDir, sFileName )
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
    lProblems = []
    #
    sFileName   = 'ETF_assets_test.csv'
    sFileDir    = r'/tmp'
    #
    tFunds      = ( 'SPYD','VYM','VPU','DIV' )
    #
    sHeaderNew  = _getNewHeaderLine( tFunds )
    #
    DeleteIfExists( sFileDir, sFileName )
    #
    openAppendClose( sHeaderNew, sFileDir, sFileName )
    #
    openAppendClose(
        '2021-04-07 10:05,3099349198,44862202189,5992208674,223246125',
        sFileDir, sFileName )
    openAppendClose(
        '2021-04-08 10:05,3158729570,44856763862,5980514616,222101274',
        sFileDir, sFileName )
    #
    sLastNew = '2021-04-09 10:05,3137735969,44808488311,5975887363,222330244'
    #
    openAppendClose( sLastNew, sFileDir, sFileName )
    #
    iLineCount = getLineCount( sFileDir, sFileName )
    #
    if iLineCount != 4:
        #
        lProblems.append( 'expecting 4 lines, instead got %s' % iLineCount )
        #
    #
    #
    sHeaderLine, sLastLine = _getCsvHeaderAndLast( sFileDir, sFileName )
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
    dTimes      = dict.fromkeys( tFunds, '2021-04-09 10:05' )
    #
    _updateFileMaybe( tFunds, dAssets, dTimes, sFileDir, sFileName )
    #
    iLineCount = getLineCount( sFileDir, sFileName )
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
    dTimes      = dict.fromkeys( tFunds, '2021-04-12 10:05' )
    #
    _updateFileMaybe( tFunds, dAssets, dTimes, sFileDir, sFileName )
    #
    iLineCount = getLineCount( sFileDir, sFileName )
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
    _getNewFileAddNewFunds( lFunds, iNewFundsAdded, sFileDir, sFileName )
    #
    iLineCount = getLineCount( sFileDir, sFileName )
    #
    if iLineCount != 5:
        #
        lProblems.append(
            'after adding a new fund, expecting 5 lines, instead got %s'
            % iLineCount )
        #
    #
    sBackFile = '%s.bak' % getNameNoPathNoExt( sFileName )
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
    # print( dAssets )
    # print( dTimes )
    #
    sayTestResult( lProblems )
