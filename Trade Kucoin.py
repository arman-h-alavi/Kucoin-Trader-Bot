# -*- coding: utf-8 -*-
"""
Created on Sun Aug 28 05:08:03 2022

@author: Armando
"""

from kucoin_futures.client import Market, Trade, User
from tvDatafeed import TvDatafeed, Interval
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import copy
import traceback

################################ Connecting to API ####################################
tv = TvDatafeed()

# Importing API settings
with open('Futures API.txt', 'r') as f:
    api = f.read()
    
api.split('\n')
api_list = [j.split(':') for j in api.split('\n')]

api_key = api_list[2][1].strip()
api_secret = api_list[3][1].strip()
api_passphrase = api_list[1][1].strip()

# Initiating API instances
market = Market(url='https://api-futures.kucoin.com')
trade = Trade(key=api_key, secret=api_secret, passphrase=api_passphrase, is_sandbox=False, url='https://api-futures.kucoin.com')
user = User(api_key, api_secret, api_passphrase)


################################ Functions ####################################

class NoData(Exception):
    def __init__(self, msg='No data found'):
        self.msg=msg
        super().__init__(self.msg)

def ATR(DF,n):
    "function to calculate True Range and Average True Range"
    df = DF.copy()
    df['H-L']=abs(df['High']-df['Low'])
    df['H-PC']=abs(df['High']-df['Close'].shift(1))
    df['L-PC']=abs(df['Low']-df['Close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    df2 = df.drop(['H-L','H-PC','L-PC'],axis=1)
    return df2['ATR']

def RSI(DF,n):
    "function to calculate RSI"
    df = DF.copy()
    df['delta']=df['Close'] - df['Close'].shift(1)
    df['gain']=np.where(df['delta']>=0,df['delta'],0)
    df['loss']=np.where(df['delta']<0,abs(df['delta']),0)
    avg_gain = []
    avg_loss = []
    gain = df['gain'].tolist()
    loss = df['loss'].tolist()
    for i in range(len(df)):
        if i < n:
            avg_gain.append(np.NaN)
            avg_loss.append(np.NaN)
        elif i == n:
            avg_gain.append(df['gain'].rolling(n).mean().tolist()[n])
            avg_loss.append(df['loss'].rolling(n).mean().tolist()[n])
        elif i > n:
            avg_gain.append(((n-1)*avg_gain[i-1] + gain[i])/n)
            avg_loss.append(((n-1)*avg_loss[i-1] + loss[i])/n)
    df['avg_gain']=np.array(avg_gain)
    df['avg_loss']=np.array(avg_loss)
    df['RS'] = df['avg_gain']/df['avg_loss']
    df['RSI'] = 100 - (100/(1+df['RS']))
    return df['RSI']

def ATR_RollMinMax(DF):
    "function to calculate ATR and Rolling max/min price"
    df = copy.deepcopy(DF)
    df["ATR"] = ATR(df,14)
    df["roll_max_cp"] = df["High"].rolling(20).max()
    df["roll_min_cp"] = df["Low"].rolling(20).min()
    df["roll_max_vol"] = df["Volume"].rolling(10).max()
    df["RSI"] = RSI(df,14)
    df.dropna(inplace=True)
    return df

def trade_signal(DF, side):
    "function to generate signal"
    df = copy.deepcopy(DF)
    signal = ""
    
    """ Column name to indices: ['High']=[1], ['Low']=[2], ['Close']=[3], ['Volume']=[4], ['ATR']=[5],
    ['roll_max_cp']=[6], ['roll_min_cp']=[7], ['roll_max_vol']=[8], ['RSI']=[9] """
    if side == "":
        if df.iloc[-2, 1]>=df.iloc[-2, 6] and df.iloc[-2, 9] < 70: #and df.iloc[-2, 4]>1.5*df.iloc[-3, 8]:
            signal = "Buy"
        elif df.iloc[-2, 2]<=df.iloc[-2, 7] and df.iloc[-2, 9] > 30: #and df.iloc[-2, 4]>1.5*df.iloc[-3, 8]:
            signal = "Sell"
    
    elif side == "long":
        if df.iloc[-2, 3]<df.iloc[-3, 3] - (2 * df.iloc[-3, 5]):
            if df.iloc[-2, 2]<=df.iloc[-2, 7] and df.iloc[-2, 4]>1.5*df.iloc[-3, 8]:
                signal = "Close_Sell"
            else:
                signal = "Close"
        elif df.iloc[-2, 2]<=df.iloc[-2, 7] and df.iloc[-2, 4]>1.5*df.iloc[-3, 8]:
            signal = "Close_Sell"
                        
    elif side == "short":
        if df.iloc[-2, 3]>df.iloc[-3, 3] + (2 * df.iloc[-3, 5]):
            if df.iloc[-2, 1]>=df.iloc[-2, 6] and df.iloc[-2, 4]>1.5*df.iloc[-3, 8]:
                signal = "Close_Buy"
            else:
                signal = "Close"
        elif df.iloc[-2, 1]>=df.iloc[-2, 6] and df.iloc[-2, 4]>1.5*df.iloc[-3, 8]:
            signal = "Close_Buy"
    return signal

def main():
    try:
        symbols = tickers
        drop = []
        main_start = time.time()
        attempt = 0
        while len(symbols)!=0 and time.time() < main_start + 1200:  #Retry for 20 mins if any exception occured
            symbols = [j for j in symbols if j not in drop]
            if len(symbols)!=0:
            
                print('----- Attempt {} -----'.format(attempt))
                
                if attempt > 0 and attempt <= 2:
                    print("Waiting for 15sec...")
                    time.sleep(15)
                elif attempt > 2 and attempt <= 4:
                    print("Waiting for 30sec...")
                    time.sleep(30)
                elif attempt > 4:
                    print("Waiting for 60sec...")
                    time.sleep(60)
                
                try:
                    open_pos = pd.DataFrame(trade.get_all_position())
                    acc_overview = user.get_account_overview('USDT')
                    available_balance = acc_overview['availableBalance']
                    print("Available Balance:", available_balance)
                    remaining_position = len(tickers) - len(open_pos)
                    
                    if len(open_pos) == 0 and available_balance < 1:
                        print("\n Account balance is less than 1 USDT \n")
                        
                    if remaining_position != 0:
                        trade_balance = available_balance / remaining_position
                    else:
                        trade_balance = 0
                
                    for s in symbols:
                        try:
                            # Calculating lot size
                            symbol_multiplier = multiplier[s]
                            #Importing symbol ohlc data
                            x = s.rstrip('M')
                            ohlc = tv.get_hist(symbol=x, exchange='kucoin', interval=Interval.in_1_hour, n_bars=200)
                            ohlc.drop('symbol', axis=1, inplace=True)
                            ohlc.columns=['Open', 'High', 'Low', 'Close', 'Volume']
    
                            if ohlc.index[-1] < datetime.now()-timedelta(hours=1):
                                print("The recieved data for {} was not up-to-date, retrying...".format(s), '\n')
                                raise NoData
                                
                            if len(ohlc) == 0:
                                print("No data fetched for {}".format(s), '\n')
                                raise NoData
                                
                            mark_price = market.get_current_mark_price(s)['value']    
                            lot = int(trade_balance / (mark_price * symbol_multiplier))
                            
                            # Getting current position side
                            side = ""
                            if len(open_pos) > 0:
                                current_pos = open_pos[open_pos['symbol'] == s]
                                if len(current_pos) > 0:
                                    if (current_pos['currentQty'] > 0).bool():
                                        side = 'long'
                                    elif (current_pos['currentQty'] < 0).bool():
                                        side = 'short'
                            
                            signal = trade_signal(ATR_RollMinMax(ohlc),side)
                            lvr = '1'
                            
                            
                            # Placing order
                            if signal in ["Buy", "Sell"]:
                                while lot != 0:
                                    try:
                                        if signal == "Buy":
                                            time.sleep(5)       #Avoiding 429 "too many requests"
                                            trade.create_market_order(symbol=s, side='buy', lever=lvr, size=lot)
                                            print("New long position initiated for", s)
                                            
                                        elif signal == "Sell":
                                            time.sleep(5)       #Avoiding 429 "too many requests"
                                            trade.create_market_order(symbol=s, side='sell', lever=lvr, size=lot)
                                            print("New short position initiated for", s)   
                                        break
                                    
                                    except Exception as e:
                                        if "300003" in str(e):
                                            print("Insufficient balance for {}, reducing 1 lot...".format(s))
                                            lot -= 1
                                        elif '429' in str(e):
                                            print("Too many requests for {}! (Buy/Sell) - Retrying after 10 sec...".format(s))
                                            time.sleep(10)
                                        else:
                                            print("\nFollowing error encountered in Buy/Sell section: {}\nexiting the loop...".format(e))
                                            raise e
                                if lot == 0:
                                    print("Lot is 0 for {}".format(s))
                                
                            elif signal in ["Close_Buy", "Close_Sell", "Close"]:
                                time.sleep(5)       #Avoiding 429 "too many requests"
                                trade.create_market_order(symbol=s, side='buy', lever=lvr, size=lot, closeOrder=True)
                                
                                if signal == "Close":
                                    print("All positions closed for", s)
                                
                                else:                                
                                    # Calculating lot again
                                    time.sleep(5)       #Avoiding 429 "too many requests"
                                    open_pos = pd.DataFrame(trade.get_all_position())
                                    acc_overview = user.get_account_overview('USDT')
                                    available_balance = acc_overview['availableBalance']
                                    remaining_position = len(tickers) - len(open_pos)
                                    if remaining_position != 0:
                                        trade_balance = available_balance / remaining_position
                                    else:
                                        trade_balance = 0   
                                    mark_price = market.get_current_mark_price(s)['value']                                    
                                    lot = int(trade_balance / (mark_price * symbol_multiplier))
                                    
                                    while lot != 0:
                                        try:
                                            if signal == "Close_Buy":
                                                time.sleep(5)       #Avoiding 429 "too many requests"
                                                trade.create_market_order(symbol=s, side='buy', lever=lvr, size=lot)
                                                print("Existing Short position closed for", s)
                                                print("New long position initiated for", s)
                                                
                                            elif signal == "Close_Sell":
                                                time.sleep(5)       #Avoiding 429 "too many requests"
                                                trade.create_market_order(symbol=s, side='sell', lever=lvr, size=lot)
                                                print("Existing long position closed for", s)
                                                print("New short position initiated for", s)
                                            break
                                        
                                        except Exception as e:
                                            if "300003" in str(e):
                                                print("Insufficient balance for {}, reducing 1 lot...".format(s))
                                                lot -= 1
                                            elif '429' in str(e):
                                                print("Too many requests for {}! (Close-Buy / Close-Sell) - Retrying after 10 sec...".format(s))
                                                time.sleep(10)
                                            else:
                                                print("\nFollowing error encountered in Close-Buy / Close-Sell section: {}\nexiting the loop...".format(e))
                                                raise e
                                    if lot == 0:
                                        print("Lot is 0 for {}".format(s))
                                        
                            drop.append(s)
                        
                        except NoData:
                            continue
                        
                        except Exception as e:
                            if '429' in str(e):
                                print("{line}\n{traceback}{line}".format(traceback = traceback.format_exc(), line = 50*'='))
                                print("Too many requests for {}! - Retrying after 11sec...\n".format(s))
                                time.sleep(11)
                                continue
                            else:
                                print('\nFollowing error encountered:', e)
                                print("{line}\n{traceback}{line}".format(traceback = traceback.format_exc(), line = 50*'='))
                                print('Retrying for {}...'.format(s), '\n')
                                continue
                    
                except Exception as e:
                    print("This error occured in outer loop:\n{}\nRetrying after 30 secs...".format(e))
                    time.sleep(30)
                    continue
                
                finally:
                    attempt += 1
        
    except Exception as e:
        print("Following error encountered: \n{}\nskipping this iteration...".format(e))
        
        
################################ Main Program ####################################

# Symbols to trade
tickers = ['SOLUSDTM', 'WAVESUSDTM', 'LUNCUSDTM']

# Initiating dict of symbol multiplier
multiplier = {}
for s in tickers:
    multiplier[s] = market.get_contract_detail(s)['multiplier']
    
i = 0
while i == 0:
    try:
        start = input("Enter the start time in this format -> Y/m/d H:M\n")
        if start:
            starttime = datetime.timestamp(datetime.strptime(start, "%Y/%m/%d %H:%M"))
            delta = starttime - time.time()
            time.sleep(delta)
        else:
            starttime = time.time()
        i = 1
    except KeyboardInterrupt:
        print("Exiting program...")
        exit()
    except:
        print("Input format was incorrect, try again:")

while True:
    try:
        print("passthrough at ",time.strftime('%Y-%m-%d  %H:%M:%S', time.localtime(time.time())))
        main()
        print("Waiting for 1 hour... \n")
        time.sleep(3600 - ((time.time() - starttime) % 3600)) # 60 minute interval between each new execution
        
    except KeyboardInterrupt:
        x = input('What is your command? ')
        if x == 'close':
            open_pos = pd.DataFrame(trade.get_all_position())
            if len(open_pos) > 0:
                for s in open_pos['symbol']:
                    print("closing all positions for",s)
                    time.sleep(3)       #Avoiding 429 "too many requests"
                    order = trade.create_market_order(symbol=s, side='sell', lever='1', size='1', closeOrder=True)
            
            else:
                print("There were no open positions")
                
            
            exit()
            
        elif x == 'exit':
            print('Exiting wihtout closing positions...')
            
            open_pos = pd.DataFrame(trade.get_all_position())
            if len(open_pos) > 0:
                print("Open positions are: ")
                print(*open_pos['symbol'], sep='\n')
                
            else:
                print("There are no open positions")
            
            exit()
            
        else:
            continue
            