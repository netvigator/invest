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

import requests

from pytz           import timezone

from String.Find    import getRegExObj
from String.Get     import getTextWithinFinders
from Utils.Config   import getConfDict, getTupleOffCommaString

dConf       = getConfDict( 'invest.ini' )

tFunds      = getTupleOffCommaString( dConf['main']['funds'] )

dFunds      = dict.fromkeys( tFunds )

sETFpage    = dConf['source']['url']

tzEast      = timezone( 'US/Eastern' )

dtNow       = datetime.now( tz = tzEast )

oFindAsOfHead   = getRegExObj( dConf['source']['as_of_head']  )
oFindAsOfBeg    = getRegExObj( dConf['source']['beg_as_of']   )
oFindAsOfEnd    = getRegExObj( dConf['source']['end_as_of']   )

oFindAssetsHead = getRegExObj( dConf['source']['assets_head'] )
oFindAssetsBeg  = getRegExObj( dConf['source']['beg_assets']  )
oFindAssetsEnd  = getRegExObj( dConf['source']['end_assets']  )



def getTotalAssets( sSymbol ):
    #
    oR = requests.get( sETFpage % sSymbol.lower() )
    #
    tReturn = ( None, None )
    #
    if oR.status_code == 200:
        #
        sHTML = oR.text
        #
        
    sName = dSymbolsNames[ sSymbol ]
    #
    dFundInfo = investpy.get_etf_information(
            etf     = sName,
            country = 'united states',
            as_json = True )
    #
    return int( dFundInfo['Total Assets'] )


    

def getTotalAssetsDict():
    #
    for sSymbol in tFunds:
        #
        iTotalAssets = getTotalAssets( sSymbol )
        #
        dFunds[ sSymbol ] = iTotalAssets

getTotalAssetsDict()


if __name__ == "__main__":
    #
    from Utils.Result   import sayTestResult
    #
    lProblems = []
    #
    print( dFunds )
    print( getRecentMarketDate() )

    #
    #
    sayTestResult( lProblems )
