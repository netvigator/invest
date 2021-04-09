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
from os.path        import join
import requests

from pytz           import timezone

from File.Spec      import getNameNoPathNoExt
from File.Test      import isFileThere
from File.Write     import openAppendClose, QuickDump
from String.Find    import getRegExObj
from Time.Convert   import getIsoDateTimeFromObj
from Time.Output    import getNowIsoDateTimeFileNameSafe
from String.Get     import getTextWithinFinders as getTextIn
from Utils.Config   import getConfDict, getTupleOffCommaString

class FundsOutOfOrderError( Exception ): pass

dConf           = getConfDict( 'invest.ini' )

tFunds          = getTupleOffCommaString( dConf['main']['funds'] )

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
sFileDir        = dConf['main']['directory' ]


def getTimeDeltaFromString( sUpdated ):
    #
    lParts = sUpdated.split( ',' )
    #
    kwargs = {}
    #
    for sPart in lParts:
        #
        lSubParts = sPart.split( ' ' )
        #
        kwargs[ lSubParts[ -1 ] ] = int( lSubParts[ -2 ] )
        #
    #
    return timedelta( **kwargs )


def getTotalAssets( sSymbol ):
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
            sUpdated = getTextIn( sTable, oFindAsOfBeg, oFindAsOfEnd ).strip()
            #
            sAsOf = getIsoDateTimeFromObj(
                dtNow - getTimeDeltaFromString( sUpdated ) )[:16]
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
            sErrorFile = 'error_%s_%s.html' % (
                    sSymbol, getNowIsoDateTimeFileNameSafe() )
            #
            print( 'did not fetch table, '
                  r'what was fetched is in \tmp\%s' % sErrorFile )
            #
            QuickDump( sHTML, sErrorFile, bSayBytes = False )
            #
        #
    #
    return tReturn




def getTotalAssetsDict():
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
            tTotalAssets = getTotalAssets( sSymbol )
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


# getTotalAssetsDict()

def getNewHeaderLine( tFunds = tFunds ):
    #
    lHeader = [ 'date time' ]
    lHeader.extend( tFunds )
    #
    return ','.join( lHeader )


def getCsvHeaderLast( sFileDir, sFileName ):
    #
    sHeaderLine = sLastLine = None
    #
    if isFileThere( sFileDir, sFileName ):
        #
        print( '%s is there' % sFileName )
        #
        with open( join( sFileDir, sFileName ) ) as oFile:
            #
            for sLine in oFile:
                #
                sHeaderLine = sLine
                #
                break
                #
            #
            for sLine in oFile:
                #
                sLastLine = sLine
                #
            #
        #
    else:
        #
        print( '%s is NOT there' % sFileName )
        #
        sHeaderLineNew = getNewHeaderLine()
        #
        openAppendClose( sHeaderLineNew, sFileDir, sFileName )
        #
        sHeaderLine = sHeaderLineNew
        #
    #
    return sHeaderLine, sLastLine


sHeaderLine, sLastLine = getCsvHeaderLast( sFileDir, sFileName )

print( 'header line:', sHeaderLine.strip() )
print( 'last   line:', sLastLine.strip()  )


def getNewFundsAdded( sHeaderLine ):
    #
    return ( sHeaderLine and
             len( sHeaderLine.split(',') ) - ( len( tFunds ) + 1 ) )


iNewFundsAdded = getNewFundsAdded( sHeaderLine )


def checkFundsInOrder( sHeaderLinePrior ):
    #
    sHeaderLineNew   = getNewHeaderLine()
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



def getNewFileAddNewFunds( iNewFundsAdded ):
    #
    sNewFile = '%s.new' % getNameNoPathNoExt( sFileName )
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
        checkFundsInOrder( sHeaderLinePrior )
        #
        iWantLen = 1 + len( tFunds )
        #
        sNewFile.write( sAppendLine % getNewHeaderLine() )
        #
        lMoreZeros = [0] * iNewFundsAdded
        #
        for sLine in oFile:
            #
            lLine = sLine.split(',')
            #
            lLine.extend( lMoreZeros )
            #
            sNewFile.write( sAppendLine % ','.join( lLine ) )
            #
        #
    #
    oNewFile.close()


'''
lAssets = [ str( dAssets[ sFund ] ) for sFund in tFunds ]

sAsOf   = max( dTimes.values() )
#
lAssets[ 0 : 0 ] = [ str( sAsOf ) ]

openAppendClose( ','.join( lAssets ), sFileDir, sFileName )

'''

if __name__ == "__main__":
    #
    from Utils.Result   import sayTestResult
    #
    lProblems = []
    #
    #
    lFunds = list( tFunds )
    #
    lFunds.reverse()
    #
    sHeaderLinePrior = getNewHeaderLine( lFunds )
    #
    try:
        checkFundsInOrder( sHeaderLinePrior )
    except FundsOutOfOrderError:
        pass
    else:
        #
        lProblems.append(
            'checkFundsInOrder() should raise FundsOutOfOrderError' )
        #
    #
    iNewFundsAdded = getNewFundsAdded( sHeaderLine )
    #
    if iNewFundsAdded != 0:
        #
        print( 'iNewFundsAdded 0:', iNewFundsAdded )
        lProblems.append(
            'getNewFundsAdded( sHeaderLine ) returned something' )
        #
    #
    lFunds.append( 'GOOG' )
    #
    sHeaderLineNew = getNewHeaderLine( lFunds )
    #
    iNewFundsAdded = getNewFundsAdded( sHeaderLineNew )
    #
    if iNewFundsAdded != 1:
        #
        print( 'iNewFundsAdded 1:', iNewFundsAdded )
        lProblems.append(
            'getNewFundsAdded( sHeaderLine ) should return 1' )
        #
    #
    #print( dAssets )
    #print( dTimes )
    #
    sayTestResult( lProblems )
