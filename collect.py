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

import json

import investpy

from Time           import _sFormatDateEu, _sFormatISOdate
from Time.Convert   import getIsoDateFromOther
from Utils.Config   import getConfDict, getTupleOffCommaString

dConf   = getConfDict( 'invest.ini' )

tFunds  = getTupleOffCommaString( dConf['main']['funds'] )

dFunds  = dict.fromkeys( tFunds )

def getNameOffSymbol( sSymbol ):
    #
    dInfo = investpy.search_etfs( by = 'symbol', value = sSymbol )
    #
    sName = dInfo['name'][0]
    #
    return sName


tSymbolsNames = tuple( ( 
    ( sSymbol, getNameOffSymbol( sSymbol ) )
    for sSymbol in tFunds ) )

dSymbolsNames = dict( tSymbolsNames )


def getTotalAssets( sSymbol ):
    #
    sName = dSymbolsNames[ sSymbol ]
    #
    dFundInfo = investpy.get_etf_information(
            etf     = sName,
            country = 'united states',
            as_json = True )
    #
    return int( dFundInfo['Total Assets'] )


    

def getRecentMarketDate():
    #
    sRecent = investpy.etfs.get_etf_recent_data(
                etf     = dSymbolsNames[ tFunds[0] ],
                country = 'united states',
                as_json = True )
    #
    dRecent = json.loads( sRecent )
    #
    sRecentDateUSA = dRecent['recent'][-1]['date']
    #
    sRecentDateISO = getIsoDateFromOther(
                        sRecentDateUSA,
                        _sFormatDateEu,
                        _sFormatISOdate )
    #
    return sRecentDateISO    


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
